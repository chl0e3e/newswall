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

class TheDailyMail:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.dailymail.co.uk/"
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.helper.sync_log(message, exception=exception)

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

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        article_screenshot_paths = self.helper.get_image_path(article_id)
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

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(5)
                time.sleep(2)
                check_cookie_disclaimer()
                self.helper.scroll_down_page()
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
