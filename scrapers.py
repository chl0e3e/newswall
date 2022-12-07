#!/usr/bin/env python3
import os
import uuid
import datetime
import base64
import threading
import json
import time

from pymongo import MongoClient # sync mongodb

import uc

from xdotool import XdotoolWrapper

from buildutil import get_build_var, get_build_folder, get_config_path, get_build_root

chromedriver_path = get_build_var("chromedriver")
chrome_path = get_build_var("chrome")
config_path = get_config_path()
profiles_folder = get_build_folder("profiles")
images_folder = get_build_folder("images")

class Helper:
    def __init__(self, id, name, sync_mongodb_database):
        self.id = id
        self.name = name
        self.uc = None
        self.sync_mongodb_database = sync_mongodb_database
        self.page_scroll_interval = 0.5
    
    def interval(self):
        return 30

    def get_image_path(self, id, ext="png"):
        site_images_folder = os.path.join(images_folder, self.id)
        if not os.path.exists(images_folder): os.mkdir(images_folder)
        if not os.path.exists(site_images_folder): os.mkdir(site_images_folder)
        image_filename = id + "." + ext
        image_path = os.path.join(site_images_folder, image_filename)
        return {
            "path": image_path,
            "url": "/images/" + self.id + "/" + image_filename
        }

    def scroll_down_page(self):
        self.log("Scrolling down the page")
        page_height = self.driver.execute_script("return document.body.scrollHeight")
        browser_height = self.driver.get_window_size()["height"]
        document_height = self.driver.execute_script("var body = document.body, html = document.documentElement; return Math.max( body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight );")
        last_scroll_y = 0
        scroll_y = 0
        scroll_attempts_failed = 0
        self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
        while True:
            if scroll_attempts_failed == 5:
                break
            self.xdotool.activate()
            self.xdotool.scroll_down()
            time.sleep(self.page_scroll_interval)
            scroll_y = self.driver.execute_script("return window.scrollY")
            self.log("scroll_y: %d" % (scroll_y))
            window_height = self.driver.execute_script("return window.innerHeight")
            if ((scroll_y + window_height) + 200) > document_height and scroll_y == last_scroll_y and scroll_y > browser_height:
                scroll_attempts_failed = scroll_attempts_failed + 1
                continue
            else:
                scroll_attempts_failed = 0
            last_scroll_y = scroll_y

    def sync_uc(self, headless=False):
        if self.uc != None:
            return self.uc

        options = uc.ChromeOptions()
        if headless:
            options.headless = True
            options.add_argument('--headless')

        # vdisplay = Xvfb(display=self.display_number)
        # vdisplay.start()

        display = "172.20.32.1:0.0"

        profile_dir = os.path.join(profiles_folder, self.id)
        driver = uc.Chrome(options=options,
            driver_executable_path=chromedriver_path,
            browser_executable_path=chrome_path,
            user_data_dir=profile_dir,
            log_level=10,
            display=display)
        self.ucs = driver

        # find the window ID for this window
        window_uuid = uuid.uuid4()
        window_uuid_str = str(window_uuid)
        self.sync_log("uuid: %s" % window_uuid_str)
        html_with_uuid_title = "<!DOCTYPE html><html><head><title>" + window_uuid_str + "</title></head><body></body></html>"
        self.sync_log("uuidhtml: %s" % html_with_uuid_title)
        window_uuid_url = "data:text/html;charset=utf-8;base64," + base64.b64encode(html_with_uuid_title.encode("ASCII")).decode('ASCII')
        self.sync_log("uuidurl: %s" % window_uuid_url)
        driver.get(window_uuid_url)
        self.sync_log("Navigated to window finder data URL")
        xdotool = XdotoolWrapper(display, window_uuid)
        self.sync_log("XdotoolWrapper created, window: %d" % (xdotool.window_id))

        self.driver = driver
        self.xdotool = xdotool

        return xdotool, driver

    def sync_find_if_exists(self, id):
        return self.sync_mongodb_database[self.id].find_one({"report_id": id})

    def sync_report(self, id, data):
        return self.sync_mongodb_database[self.id].insert_one({"report_id": id, "report_date": datetime.datetime.utcnow(), **data})
    
    def sync_insert_presence(self, db_id, date):
        return self.sync_mongodb_database[self.id].update_one({"_id": db_id}, {"$push": {"presence": date}})

    def log(self, message, exception=None):
        return self.sync_log(message, exception=exception)

    def sync_log(self, message, exception=None):
        log_line = {"date": datetime.datetime.utcnow(), "source": self.id, "text": message}
        if exception != None:
            log_line["exception"] = exception

        log_id = self.sync_mongodb_database["log"].insert_one(log_line).inserted_id
        log_line["_id"] = log_id
        
        print("[%s] [%s] %s" % (log_line["source"], log_line["date"], message))
        if exception != None:
            print(exception)
        return log_id

def import_site(path):
    import importlib.util
    import sys
    name = os.path.basename(os.path.splitext(path)[0])
    print("Importing %s from %s" % (name, path))
    spec = importlib.util.spec_from_file_location(name, path)
    site = importlib.util.module_from_spec(spec)
    sys.modules[name] = site
    print("module: " + str(site))
    spec.loader.exec_module(site)
    return site

if __name__ == "__main__":
    print("Attempting to connect to MongoDB synchronously")
    sync_mongodb_client = MongoClient("mongodb://localhost:27017/")
    sync_mongodb_database = sync_mongodb_client["newswall"]
    info = sync_mongodb_client.server_info()
    print("Application connected to MongoDB (%s) synchronously" % (info["version"]))

    print("Attempting to load configuration file")
    config_file = None
    with open(config_path) as f:
        config_file = json.load(f)
    if config_file == None:
        print("Failed to load configuration file from %s" % config_path)
    print("Loaded configuration file from %s" % config_path)
    
    sites = config_file["sites"].items()
    print("Loaded %d sites" % (len(sites)))

    threads = []
    for site_id, site_config in sites:
        if not "name" in site_config:
            print("Configuration for site '%s' does not contain a name" % (site_id))
            continue

        if not "enabled" in site_config:
            print("Configuration for site '%s' does not have an 'enabled' property" % (site_id))
            continue

        if not "path" in site_config:
            print("Configuration for site '%s' does not have a valid path" % (site_id))
            continue
        
        if not "class" in site_config:
            print("Configuration for site '%s' does not specify what class to start" % (site_id))
            continue

        if not site_config["enabled"]:
            print("Site '%s' is disabled" % (site_id))
            continue
        
        if not ".py" in site_config["path"]:
            site_config["path"] = site_config["path"] + ".py"

        site_path = os.path.join(get_build_root(), site_config["path"])
        if not os.path.exists(site_path):
            print("Site '%s' cannot be found at %s" % (site_id, site_path))
            continue
        module = import_site(site_path)

        module_class = getattr(module, site_config["class"])
        module_helper = Helper(site_id, site_config["name"], sync_mongodb_database)
        module_obj = module_class(module_helper)

        thread = threading.Thread(target=module_obj.start, args=[])
        threads.append(thread)
        thread.start()

    print("All site threads started")
    for thread in threads:
        thread.join()    
    
    print("Shutting down synchronous MongoDB client")
    sync_mongodb_client.close()