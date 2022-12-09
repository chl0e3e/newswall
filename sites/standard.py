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

class Standard:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.standard.co.uk/"
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.helper.sync_log(message, exception=exception)

    def start(self):
        while True:
            try:
                self.helper.log("Setting up chromedriver")
                self.setup_chromedriver()
                self.xdotool.activate()
                self.xdotool.size("100%", "100%")
            except Exception as e:
                exception_str = traceback.format_exc()
                self.helper.log("Failed during setup", exception=exception_str)
                self.stop()
                time.sleep(30)
                continue

            self.log("Fetching Standard")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "frameInner")))

            def check_newsletter():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, ".tp-container-inner > iframe")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer 1 found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, ".close-btn").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer 1")
            
            def check_cookie_disclaimer_2():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='SP Consent Message']")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer 2 found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='Agree']").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer 2")

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

                self.driver.execute_script("document.querySelector('header').remove()")

                articles = self.driver.find_elements(By.CSS_SELECTOR, ".article, .hero-article")

                for article in articles:
                    article_data = {}
                    article_link_element = article.find_element(By.CSS_SELECTOR, ".title")
                    article_data["url"] = article_link_element.get_attribute("href")
                    article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        article_screenshot_paths = self.helper.get_image_path(article_id)
                        save_element_image(article, article_screenshot_paths["path"])
                        article_data["screenshot_url"] = article_screenshot_paths["url"]
                        article_data["screenshot_path"] = article_screenshot_paths["path"]

                        article_data["title"] = article.find_element(By.CSS_SELECTOR, ".title").get_attribute("innerText")
                        try:
                            article_capsule_link = article.find_element(By.CSS_SELECTOR, ".capsule")
                            article_data["section"] = article_capsule_link.get_attribute("innerText")
                            article_data["section_url"] = article_capsule_link.get_attribute("href")
                        except:
                            article_data["section"] = None
                            article_data["section_url"] = None
                        try:
                            article_data["lead"] = article.find_element(By.CSS_SELECTOR, ".lead").get_attribute("innerText")
                        except:
                            article_data["lead"] = None
                        try:
                            article_author_link = article.find_element(By.CSS_SELECTOR, "[class*='ArticleAuthor'] a")
                            article_data["author"] = article_author_link.get_attribute("innerText")
                            article_data["author_url"] = article_author_link.get_attribute("href")
                        except:
                            article_data["author"] = None
                            article_data["author_url"] = None

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(self.helper.interval_page_ready())
                time.sleep(2)
                check_cookie_disclaimer_2()
                time.sleep(2)
                check_newsletter()
                time.sleep(5)
                #wait_for_page_ready(self.helper.interval_page_ready())
                self.helper.scroll_down_page()
                save_articles()
            except Exception as e:
                self.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.log("Shutting down")
            finally:
                self.stop()
            
            sleep_interval = self.helper.interval()
            self.log("Sleeping for %d seconds" % sleep_interval)
            time.sleep(sleep_interval)
        
        self.log("Exited main loop")
    
    def stop(self):
        self.helper.kill_9_browser_and_driver()
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
