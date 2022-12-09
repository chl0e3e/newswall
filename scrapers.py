#!/usr/bin/env python3
import os
import uuid
import datetime
import base64
import threading
import json
import time
import sys
import random
import argparse
import psutil
from multiprocessing import Process

from pymongo import MongoClient # sync mongodb

import uc

from xdotool import XdotoolWrapper

from xvfbwrapper import Xvfb

from buildutil import get_build_var, get_build_folder, get_config_path, get_build_root

chromedriver_path = get_build_var("chromedriver")
chrome_path = get_build_var("chrome")
config_path = get_config_path()
profiles_folder = get_build_folder("profiles")
images_folder = get_build_folder("images")

verbose = False

class Helper:
    def __init__(self, id, name, sync_mongodb_database, mode, disable_xvfb):
        self.id = id
        self.name = name
        self.uc = None
        self.sync_mongodb_database = sync_mongodb_database
        self.page_scroll_interval = 0.5
        self.mode = mode
        self.disable_xvfb = disable_xvfb
    
    def interval(self):
        return random.randrange(0, 3600)
    
    def interval_page_ready(self):
        return random.randrange(30, 120)
    
    def interval_page_scroll(self):
        return 0.25

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

    def stop(self):
        if not self.disable_xvfb:
            try:
                self.vdisplay.stop()
            except:
                pass

        if self.mode == "multiprocessing":
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            for child in children:
                self.log("Killing pid %d" % child.pid)
                try:
                    os.kill(child.pid, 9)
                except:
                    pass
            return

        if getattr(self, "driver") == None:
            return

        if self.driver == None:
            return

        if self.driver.browser_pid != None:
            try:
                os.kill(self.driver.browser_pid, 9)
            except:
                pass

        if self.driver.service != None and self.driver.service.process != None:
            try:
                os.kill(self.driver.service.process.pid, 9)
            except:
                pass
        try:
            self.driver.quit()
        except:
            pass

    def scroll_down_page(self, scrolls=1):
        self.log("Scrolling down the page")
        page_height = self.driver.execute_script("return document.body.scrollHeight")
        browser_height = self.driver.get_window_size()["height"]
        document_height = self.driver.execute_script("var body = document.body, html = document.documentElement; return Math.max( body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight );")
        last_scroll_y = 0
        scroll_y = 0
        scroll_attempts_failed = 0
        scroll_attempts_failed_override = 0
        #self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
        while True:
            if scroll_attempts_failed == 5:
                self.log("Scrolling stopped, %d %d %d %d" % (scroll_y, page_height, document_height, browser_height))
                break
            if scroll_attempts_failed_override == 20:
                self.log("Scrolling aborted after 100 attempts (too slow?)")
                break
            self.xdotool.activate()
            for i in range(scrolls): self.xdotool.scroll_down()
            time.sleep(self.interval_page_scroll())
            scroll_y = self.driver.execute_script("return window.scrollY")
            #self.log("scroll_y: %d" % (scroll_y))
            window_height = self.driver.execute_script("return window.innerHeight")
            if last_scroll_y == scroll_y:
                scroll_attempts_failed_override += 1
                continue
            else:
                scroll_attempts_failed_override = 0

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
        options.add_argument("--disable-breakpad")
        options.add_argument("--noerrdialogs")
        options.add_argument("--disable-crash-reporter")
        if headless:
            options.headless = True
            options.add_argument("--headless")

        if not self.disable_xvfb:
            self.vdisplay = Xvfb(width=1920, height=1080)
            self.vdisplay.start()
            display = (":%d" % self.vdisplay.new_display)
        elif "DISPLAY" in os.environ:
            display = os.environ["DISPLAY"]
        else:
            display = ":0"

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
    spec = importlib.util.spec_from_file_location(name, path)
    site = importlib.util.module_from_spec(spec)
    sys.modules[name] = site
    spec.loader.exec_module(site)
    return site

def args_parser():
    parser = argparse.ArgumentParser(
                    prog = "newswall Scrapers",
                    description = "This program starts threads for scrapers and provides functions for reporting them to a MongoDB instance.",
                    epilog = "Text at the bottom of help")

    parser.add_argument("config_path", action="store", type=str, default=config_path, help="Path to the configuration file to load and use")
    parser.add_argument("-m", "--mode", dest="mode", action="store", type=str, default="multiprocessing", help="Run the scrapers in a different mode (single = single site mode, threading = threaded mode, multiprocessing = multiprocessing mode)")
    parser.add_argument("-s", "--site", dest="site", action="store", type=str, default="", help="Site to run and scrape (single-site mode only)")
    parser.add_argument("-x", "--disable-xvfb", dest="disable_xvfb", action="store_true", default=False, help="Disable headless Xvfb and use DISPLAY from script environment")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=True)

    return parser

def main():
    parser = args_parser()
    args = parser.parse_args()

    if args.mode != "single" and args.mode != "multiprocessing" and args.mode != "threading":
        parser.print_help()
        return

    print("Attempting to load configuration file")
    config_file = None
    with open(args.config_path) as f:
        config_file = json.load(f)
    if config_file == None:
        print("Failed to load configuration file from %s" % config_path)
        sys.exit(1)
    print("Loaded configuration file from %s" % config_path)

    if not "database_url" in config_file:
        print("Configuration does not contain a MongoDB database URL")
        sys.exit(2)

    if not "database_name" in config_file:
        print("Configuration does not contain a MongoDB database name")
        sys.exit(3)

    print("Attempting to connect to MongoDB synchronously")
    sync_mongodb_client = MongoClient(config_file["database_url"])
    sync_mongodb_database = sync_mongodb_client[config_file["database_name"]]

    def log(line):
        log_line = {"date": datetime.datetime.utcnow(), "source": "scrapers", "text": line}

        log_id = sync_mongodb_database["log"].insert_one(log_line).inserted_id
        log_line["_id"] = log_id
        
        if args.verbose:
            print("[%s] [%s] %s" % (log_line["source"], log_line["date"], line))

    info = sync_mongodb_client.server_info()
    log("Application connected to MongoDB (%s) synchronously" % (info["version"]))
    
    sites = config_file["sites"].items()
    log("Loaded %d sites" % (len(sites)))

    if len(sites) == 0:
        log("No scrapers configured, aborting.")
        sys.exit(4)

    threads = []
    processes = []
    for site_id, site_config in sites:
        if args.mode == "single" and site_id != args.site:
            continue

        if not "name" in site_config:
            log("Configuration for site '%s' does not contain a name" % (site_id))
            continue

        if not "enabled" in site_config:
            log("Configuration for site '%s' does not have an 'enabled' property" % (site_id))
            continue

        if not "path" in site_config:
            log("Configuration for site '%s' does not have a valid path" % (site_id))
            continue
        
        if not "class" in site_config:
            log("Configuration for site '%s' does not specify what class to start" % (site_id))
            continue

        if not site_config["enabled"] and args.mode != "single":
            log("Site '%s' is disabled" % (site_id))
            continue
        
        if not ".py" in site_config["path"]:
            site_config["path"] = site_config["path"] + ".py"

        site_path = os.path.join(get_build_root(), site_config["path"])
        if not os.path.exists(site_path):
            log("Site '%s' cannot be found at %s" % (site_id, site_path))
            continue
        log("Importing '%s' @ '%s'" % (site_id, site_path))
        module = import_site(site_path)

        module_class = getattr(module, site_config["class"])
        module_helper = Helper(site_id, site_config["name"], sync_mongodb_database, args.mode, args.disable_xvfb)
        module_obj = module_class(module_helper)

        def delayed_start():
            delayed_start_secs = module_helper.interval()
            log("Delaying start for %s by %d seconds" % (site_id, delayed_start_secs))
            time.sleep(delayed_start_secs)
            module_obj.start()

        if args.mode == "threading":
            thread = threading.Thread(target=delayed_start, args=[])
            threads.append(thread)
            thread.start()
        elif args.mode == "multiprocessing":
            process = Process(target=delayed_start, args=())
            processes.append(process)
            process.start()
        else:
            module_obj.start()

    if args.mode == "threading":
        if len(threads) == 0:
            log("No scrapers started, aborting.")
            sys.exit(5)

        log("All site threads started")
        for thread in threads:
            thread.join()
    elif args.mode == "multiprocessing":
        if len(processes) == 0:
            log("No scrapers started, aborting.")
            sys.exit(5)

        log("All site threads started")
        for process in processes:
            process.join()
    
    log("Shutting down synchronous MongoDB client")
    sync_mongodb_client.close()

if __name__ == "__main__":
    main()