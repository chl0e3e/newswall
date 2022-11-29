from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from PIL import Image
from io import BytesIO
import base64
import os
import datetime
import hashlib
import time
import traceback

__site__ = "the_daily_mail"
__site_name__ = "The Daily Mail"
__type__ = "TheDailyMail"

class TheDailyMail:
    def __init__(self, newswall):
        self.newswall = newswall
        self.driver = None
        self.url = "https://www.dailymail.co.uk/"
        self.page_scroll_interval = 0.05
        self.id = __site__
        self.name = __site_name__
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.newswall.sync_log(__site__, message, exception=exception)

    def start(self):
        self.setup_chromedriver()
        self.xdotool.activate()
        self.xdotool.size(1920, 1080)

        while self.driver != None:
            self.log("Fetching The Daily Mail")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "content")))
            
            def check_cookie_disclaimer():
                try:
                    consent_buttons = self.driver.find_elements(By.CSS_SELECTOR, "[data-project='mol-fe-cmp'] button")
                    consent_buttons[1].click()
                except Exception as e:
                    self.log("Failed to find cookie disclaimer", exception=traceback.format_exc())

            def scroll_down_page():
                self.log("Scrolling down the page")
                page_height = self.driver.execute_script("return document.body.scrollHeight")
                browser_height = self.driver.get_window_size()["height"]
                last_scroll_y = 0
                scroll_y = 0
                self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
                while True:
                    self.xdotool.scroll_down()
                    time.sleep(self.page_scroll_interval)
                    scroll_y = self.driver.execute_script("return window.scrollY")
                    self.log("scroll_y: %d" % (scroll_y))
                    if scroll_y == last_scroll_y and scroll_y > browser_height:
                        self.log("No more page to scroll")
                        break
                    last_scroll_y = scroll_y

            def save_element_image(element, file):
                location = element.location_once_scrolled_into_view
                png = self.driver.get_screenshot_as_png() # saves screenshot of entire page

                im = Image.open(BytesIO(png)) # uses PIL library to open image in memory

                left = location['x']
                top = location['y']
                
                size = self.driver.execute_script("var element = arguments[0]; var b = window.getComputedStyle(element); return [b.width, b.height]", element)
                width = int(float(size[0].replace("px", "")))
                height = int(float(size[1].replace("px", "")))

                right = left + width
                bottom = top + height

                im = im.crop((left, top, right, bottom))
                im.save(file)

            def save_articles():
                self.log("Saving articles")

                articles = self.driver.find_elements(By.CSS_SELECTOR, "[itemprop='itemListElement']")

                for article in articles:
                    article_data = {}
                    article_link_element = article.find_element(By.CSS_SELECTOR, "[itemprop='url']")
                    article_data["url"] = article_link_element.get_attribute("href")
                    article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                    article_db_obj = self.newswall.sync_find_if_exists(__site__, article_id)
                    if article_db_obj == None:
                        article_screenshot_paths = self.newswall.get_image_path(__site__, article_id)
                        save_element_image(article, article_screenshot_paths["path"])
                        article_data["screenshot_url"] = article_screenshot_paths["url"]
                        article_data["screenshot_path"] = article_screenshot_paths["path"]

                        article_data["title"] = self.driver.execute_script("return arguments[0].lastChild.wholeText;", article_link_element).strip()
                        try:
                            article_data["comments"] = article.find_element(By.CSS_SELECTOR, ".readerCommentNo").get_attribute("innerText")
                        except:
                            article_data["comments"] = "0"

                        try:
                            article_data["shares"] = article.find_element(By.CSS_SELECTOR, ".share-link > .linktext > .bold").get_attribute("innerText")
                        except:
                            try:
                                article_data["shares"] = article.find_element(By.CSS_SELECTOR, ".facebook > .linktext > .bold").get_attribute("innerText")
                            except:
                                article_data["shares"] = "0"

                        try:
                            article_data["videos"] = article.find_element(By.CSS_SELECTOR, ".videos-link > .linktext > .bold").get_attribute("innerText")
                        except:
                            article_data["videos"] = "0"

                        article_data["text"] = article.find_element(By.CSS_SELECTOR, "p").get_attribute("innerText")

                        report = self.newswall.sync_report(__site__, article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.newswall.sync_insert_presence(__site__, article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(5)
                time.sleep(2)
                check_cookie_disclaimer()
                #time.sleep(2)
                #check_subscribe_modal()
                #time.sleep(2)
                #scroll_down_page()
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
            
        xdotool, driver = self.newswall.sync_uc(__site__)
        self.driver = driver
        self.xdotool = xdotool
