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

class Independent:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.independent.co.uk/"
    
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
                self.helper.stop()
                time.sleep(30)
                continue

            self.log("Fetching Independent")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "sectionContent")))

            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='SP Consent Message']")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='AGREE']").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer")

            def check_google_ad():
                try:
                    ad_frame_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='3rd party ad content']")
                    if len(ad_frame_elements) > 0:
                        self.log("Google ad found")
                        self.driver.switch_to.frame(ad_frame_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[role='button']").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find Google ad")

            def check_subscribe_modal():
                try:
                    for i in range(10):
                        self.xdotool.scroll_down()
                        time.sleep(0.5)
                    subscribe_modal = self.driver.find_elements(By.CSS_SELECTOR, ".tp-active iframe")
                    print(len(subscribe_modal))
                    if len(subscribe_modal) > 0:
                        self.driver.switch_to.frame(subscribe_modal[0])
                        self.driver.find_element(By.CSS_SELECTOR, ".pn-template__close").click()

                    self.driver.switch_to.default_content()
                    time.sleep(1)
                except:
                    self.log("Failed to close subscribe modal")

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

                articles = self.driver.find_elements(By.CSS_SELECTOR, ".article-default")

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

                        article_data["title"] = article_link_element.get_attribute("innerText")
                        article_capsule = article.find_element(By.CSS_SELECTOR, "a.capsule")
                        article_capsule_class = article_capsule.get_attribute("class")
                        if "live-blog" in article_capsule_class:
                            article_capsule = self.driver.execute_script("return arguments[0].nextSibling;", article_capsule)
                        article_data["section"] = article_capsule.get_attribute("innerText")
                        try:
                            article_data["section_url"] = article_capsule.get_attribute("href")
                        except:
                            article_data["section_url"] = None

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(self.helper.interval_page_ready())
                check_cookie_disclaimer()
                check_google_ad()
                check_subscribe_modal()
                self.helper.scroll_down_page()
                save_articles()
            except Exception as e:
                self.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.log("Shutting down")
            finally:
                self.helper.stop()
            
            sleep_interval = self.helper.interval()
            self.log("Sleeping for %d seconds" % sleep_interval)
            time.sleep(sleep_interval)
    
    def setup_chromedriver(self):
        self.log("Initialising a new Chrome instance")

        if self.driver != None:
            self.helper.stop()
            
        xdotool, driver = self.helper.sync_uc()
        self.driver = driver
        self.xdotool = xdotool
