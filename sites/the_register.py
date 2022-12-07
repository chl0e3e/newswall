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

class TheRegister:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.theregister.com/"
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
            self.log("Fetching The Register")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "page")))
            
            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[value='Accept All Cookies']")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        consent_elements[0].click()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer")

            def scroll_down_page():
                self.log("Scrolling down the page")
                page_height = self.driver.execute_script("return document.body.scrollHeight")
                browser_height = self.driver.get_window_size()["height"]
                last_scroll_y = 0
                scroll_y = 0
                scroll_attempts_failed = 0
                self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
                while True:
                    if scroll_attempts_failed == 5:
                        break
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
                location = element.location_once_scrolled_into_view
                png = self.driver.get_screenshot_as_png() # saves screenshot of entire page

                im = Image.open(BytesIO(png)) # uses PIL library to open image in memory

                left = location['x']
                top = location['y']
                
                size = self.driver.execute_script("var element = arguments[0]; return [element.offsetWidth, element.offsetHeight]", element)
                width = size[0]
                height = size[1]

                if width == 0 or height == 0:
                    return False

                right = left + width
                bottom = top + height

                im = im.crop((left, top, right, bottom))

                def trim(im):
                    bg = Image.new(im.mode, im.size, (255, 255, 255))
                    diff = ImageChops.difference(im, bg)
                    diff = ImageChops.add(diff, diff, 2.0, -100)
                    bbox = diff.getbbox()
                    if bbox:
                        return im.crop(bbox)
                    else:
                        return trim(im.convert('RGB'))
                
                trim(im).save(file)
                return True
                
            def save_articles():
                self.log("Saving articles")

                self.driver.execute_script("document.querySelector('#masthead').remove()")

                articles = self.driver.find_elements(By.CSS_SELECTOR, "article")

                for article in articles:
                    article_data = {}
                    article_link_element = article.find_element(By.CSS_SELECTOR, "a")
                    article_data["url"] = article_link_element.get_attribute("href")
                    article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        article_screenshot_paths = self.helper.get_image_path(article_id)
                        save_element_image(article, article_screenshot_paths["path"])
                        article_data["screenshot_url"] = article_screenshot_paths["url"]
                        article_data["screenshot_path"] = article_screenshot_paths["path"]
                        article_data["title"] = article_link_element.find_element(By.CSS_SELECTOR, "h4").get_attribute("innerText")
                        try:
                            article_data["standfirst"] = article.find_element(By.CSS_SELECTOR, ".standfirst").get_attribute("innerText")
                        except:
                            article_data["standfirst"] = None
                        try:
                            article_data["section"] = article.find_element(By.CSS_SELECTOR, ".section_name").get_attribute("innerText")
                        except:
                            article_data["section"] = None
                        try:
                            article_data["timestamp"] = article.find_element(By.CSS_SELECTOR, ".time_stamp").get_attribute("data-epoch")
                        except:
                            article_data["timestamp"] = None
                        try:
                            article_data["comments"] = article.find_element(By.CSS_SELECTOR, ".comment").get_attribute("innerText")
                        except:
                            article_data["comments"] = None

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(5)
                check_cookie_disclaimer()
                #wait_for_page_ready(5)
                scroll_down_page()
                save_articles()
            except Exception as e:
                self.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.log("Shutting down")
                self.stop()
            
            time.sleep(self.interval())
        
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