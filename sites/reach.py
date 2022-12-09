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

class Reach:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.urls = {
            "https://www.mylondon.news/": "MyLondon",
            "https://www.manchestereveningnews.co.uk/": "Manchester Evening News",
            "https://www.staffordshire-live.co.uk/": "Staffordshire Live",
            "https://www.birminghammail.co.uk/": "Birmingham Mail",
            "https://www.hulldailymail.co.uk/": "Hull Live"
        }
    
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

            self.log("Fetching Reach sites")

            def navigate(url):
                self.log("Navigating to page: %s" % (url))
                self.driver.get(url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.CLASS_NAME, "mod-pancakes")))

            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "#qc-cmp2-main [mode='primary']")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        consent_elements[0].click()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer")

            def check_google_login_popup():
                try:
                    login_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='Sign in with Google Dialogue']")
                    if len(login_elements) > 0:
                        self.log("Google sign in popup found")
                        self.driver.switch_to.frame(login_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "#close").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find Google sign in popup")

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

            def save_articles(site_url, site_name):
                self.log("Saving articles")

                self.driver.execute_script("document.querySelector('header').remove()")

                articles = self.driver.find_elements(By.CSS_SELECTOR, ".teaser")

                for article in articles:
                    article_data = {}
                    try:
                        article_link_element = article.find_element(By.CSS_SELECTOR, ".headline")
                    except:
                        continue
                    article_data["url"] = article_link_element.get_attribute("href")
                    article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        article_screenshot_paths = self.helper.get_image_path(article_id)
                        save_element_image(article, article_screenshot_paths["path"])
                        article_data["screenshot_url"] = article_screenshot_paths["url"]
                        article_data["screenshot_path"] = article_screenshot_paths["path"]

                        article_data["title"] = article_link_element.get_attribute("innerText")
                        article_data["site_url"] = site_url
                        article_data["site_name"] = site_name
                        try:
                            article_data["description"] = article.find_element(By.CSS_SELECTOR, ".description").get_attribute("innerText")
                        except:
                            article_data["description"] = None
                        try:
                            article_data["comments"] = article.find_element(By.CSS_SELECTOR, ".vf-comments-count").get_attribute("innerText")
                        except:
                            article_data["comments"] = None
                        try:
                            article_label_element = article.find_element(By.CSS_SELECTOR, ".label")
                            article_data["section"] = article_label_element.get_attribute("innerText")
                            article_data["section_url"] = article_label_element.get_attribute("href")
                        except:
                            article_data["section"] = None
                            article_data["section_url"] = None

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                for url, name in self.urls.items():
                    self.log ("Fetching %s" % url)
                    navigate(url)
                    wait_for_page_ready(self.helper.interval_page_ready())
                    check_google_login_popup()
                    check_cookie_disclaimer()
                    self.helper.scroll_down_page()
                    save_articles(url, name)
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
