from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from PIL import Image, ImageChops

from io import BytesIO
import base64
import os
import datetime
import time
import traceback
import hashlib

class Channel4:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.channel4.com/news/"
        self.page_scroll_interval = 0.05
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.helper.sync_log(message, exception=exception)

    def start(self):
        self.setup_chromedriver()
        self.xdotool.activate()
        self.xdotool.size(1920, 1080)

        while self.driver != None:
            self.log("Fetching Channel 4 News")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "site-body")))

            def check_cookie_disclaimer():
                self.xdotool.scroll_down()
                self.xdotool.scroll_down()
                self.xdotool.scroll_down()
                time.sleep(1)
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "#cookie-consent-banner button")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        consent_elements[0].click()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer")
            
            def scroll_down_page_and_save():
                # https://stackoverflow.com/a/46816183
                # sytech
                def element_completely_viewable(driver, elem):
                    elem_left_bound = elem.location.get('x')
                    elem_top_bound = elem.location.get('y')
                    elem_width = elem.size.get('width')
                    elem_height = elem.size.get('height')
                    elem_right_bound = elem_left_bound + elem_width
                    elem_lower_bound = elem_top_bound + elem_height

                    win_upper_bound = driver.execute_script('return window.pageYOffset')
                    win_left_bound = driver.execute_script('return window.pageXOffset')
                    win_width = driver.execute_script('return document.documentElement.clientWidth')
                    win_height = driver.execute_script('return document.documentElement.clientHeight')
                    win_right_bound = win_left_bound + win_width
                    win_lower_bound = win_upper_bound + win_height

                    return all((win_left_bound <= elem_left_bound,
                                win_right_bound >= elem_right_bound,
                                win_upper_bound <= elem_top_bound,
                                win_lower_bound >= elem_lower_bound)
                            )

                self.log("Scrolling down the page")
                page_height = self.driver.execute_script("return document.body.scrollHeight")
                browser_height = self.driver.get_window_size()["height"]
                last_scroll_y = 0
                scroll_y = 0
                scroll_attempts_failed = 0
                self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
                
                articles = self.driver.find_elements(By.CSS_SELECTOR, "ul.stream > li")
                articles_saved = []

                while True:
                    if scroll_attempts_failed == 10:
                        break
                    
                    for article in articles:
                        if element_completely_viewable(self.driver, article):
                            article_data = {}
                            article_link_element = article.find_element(By.CSS_SELECTOR, "a")
                            article_data["url"] = article_link_element.get_attribute("href")
                            article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                            if article_id in articles_saved:
                                continue
                            articles_saved.append(article_id)
                            print(article_data["url"])

                            article_db_obj = self.helper.sync_find_if_exists(article_id)
                            if article_db_obj == None:
                                article_screenshot_paths = self.helper.get_image_path(article_id)
                                save_element_image(article, article_screenshot_paths["path"])
                                article_data["screenshot_url"] = article_screenshot_paths["url"]
                                article_data["screenshot_path"] = article_screenshot_paths["path"]

                                article_data["title"] = article_link_element.find_element(By.CSS_SELECTOR, ".heading").get_attribute("innerText")
                                article_data["description"] = article.find_element(By.CSS_SELECTOR, ".description").get_attribute("innerText")

                                report = self.helper.sync_report(article_id, article_data)
                                self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                            else:
                                self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                                self.log("Inserted presence into %s" % article_id)

                    self.xdotool.scroll_down()
                    time.sleep(self.page_scroll_interval)
                    scroll_y = self.driver.execute_script("return window.scrollY")
                    self.log("scroll_y: %d" % (scroll_y))
                    if scroll_y == last_scroll_y and scroll_y > browser_height:
                        scroll_attempts_failed = scroll_attempts_failed + 1
                        continue
                    else:
                        scroll_attempts_failed = 0
                    last_scroll_y = scroll_y

            def save_element_image(element, file):
                im = Image.open(BytesIO(element.screenshot_as_png)) # uses PIL library to open image in memory
                im.save(file)
                return True

            try:
                navigate()
                wait_for_page_ready(5)
                check_cookie_disclaimer()
                scroll_down_page_and_save()
                time.sleep(3600)
            except Exception as e:
                self.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.log("Shutting down")
                self.stop()
            
            sleep_interval = self.helper.interval()
            self.log("Sleeping for %d seconds" % sleep_interval)
            time.sleep(sleep_interval)
        
        self.log("Exited main loop")
    
    def stop(self):
        if self.driver != None:
            self.driver.quit()
            self.driver = None
    
    def setup_chromedriver(self):
        self.log("Initialising a new Chrome instance")

        if self.driver != None:
            self.stop()
            
        xdotool, driver = self.helper.sync_uc()
        self.driver = driver
        self.xdotool = xdotool
