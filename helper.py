import psutil
import uuid
import base64
import random
import time
import os
import datetime

import uc

from xvfbwrapper import Xvfb

from xdotool import XdotoolWrapper

from buildutil import get_build_var, get_build_folder, get_config_path, get_build_root

chromedriver_path = get_build_var("chromedriver")
chrome_path = get_build_var("chrome")
config_path = get_config_path()
profiles_folder = get_build_folder("profiles")
images_folder = get_build_folder("images")

class Helper:
    def __init__(self, id, name, sync_mongodb_database, sigkill_child_processes=False, disable_xvfb=False, start_detached=False):
        self.id = id
        self.name = name
        self.uc = None
        self.sync_mongodb_database = sync_mongodb_database
        self.page_scroll_interval = 0.5
        self.sigkill_child_processes = sigkill_child_processes
        self.disable_xvfb = disable_xvfb
        self.start_detached = start_detached
    
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

        if self.sigkill_child_processes:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            for child in children:
                self.log("Killing pid %d" % child.pid)
                try:
                    os.kill(child.pid, 9)
                except:
                    pass
            self.driver = None
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
            self.driver = None
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
        options = uc.ChromeOptions()
        options.add_argument("--disable-breakpad")
        options.add_argument("--noerrdialogs")
        options.add_argument("--disable-crash-reporter")
        #options.add_argument("--disable-software-rasterizer")
        #options.add_argument("--disable-gpu")
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
            service_log_path=self.id+".log",
            user_data_dir=profile_dir,
            display=display,
            use_subprocess=(not self.start_detached))

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