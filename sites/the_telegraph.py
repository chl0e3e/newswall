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

class TheTelegraph:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.telegraph.co.uk/"
    
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
                if self.driver != None:
                    self.driver.quit()
                    self.driver = None
                time.sleep(30)
                continue

            self.log("Fetching The Telegraph")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "main-content")))

            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='SP Consent Message']")
                    if consent_elements != None and len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='Accept']").click()
                        self.driver.switch_to.default_content()
                except:
                    self.log("Failed to find cookie disclaimer")
            
            def check_subscribe_modal():
                try:
                    close_modal_button = self.driver.find_element(By.CSS_SELECTOR, ".martech-modal-component__close")
                    if close_modal_button != None:
                        self.log("Subscribe modal found")
                        close_modal_button.click()
                except:
                    self.log("Failed to find subscribe modal")

            def save_element_image(element, file, sibling_check=False):
                location = element.location_once_scrolled_into_view
                png = self.driver.get_screenshot_as_png() # saves screenshot of entire page

                im = Image.open(BytesIO(png)) # uses PIL library to open image in memory

                left = location['x']
                top = location['y']
                
                size = self.driver.execute_script("var element = arguments[0]; var b = window.getComputedStyle(element); return [b.width, b.height]", element)
                width = int(float(size[0].replace("px", "")))
                height = int(float(size[1].replace("px", "")))

                if sibling_check:
                    try:
                        next_sibling = self.driver.execute_script("return arguments[0].nextElementSibling", element)
                        if next_sibling != None and "package__image" in next_sibling.get_attribute("class"):
                            next_sibling_location = next_sibling.location_once_scrolled_into_view
                            next_sibling_size = self.driver.execute_script("var element = arguments[0]; var b = window.getComputedStyle(element); return [b.width, b.height]", next_sibling)
                            next_sibling_width = int(float(next_sibling_size[0].replace("px", "")))
                            next_sibling_height = int(float(next_sibling_size[1].replace("px", "")))

                            width = (next_sibling_location["x"] - left) + next_sibling_width
                            height = (next_sibling_location["y"] - top) + next_sibling_height
                    except Exception as e:
                        self.log("Failed to get sibling image: %s" % (str(e)))

                right = left + width
                bottom = top + height

                im = im.crop((left, top, right, bottom))
                im.save(file)

            def save_articles():
                self.log("Saving articles")

                packages = self.driver.find_elements(By.CSS_SELECTOR, ".package")
                for package in packages:
                    package_heading = package.find_element(By.CSS_SELECTOR, ".package__heading").get_attribute("innerText")

                    cards = package.find_elements(By.CSS_SELECTOR, ".card")
                    for card in cards:
                        article_link_element = card.find_element(By.CSS_SELECTOR, ".list-headline__link")
                        article_url = article_link_element.get_attribute("href")
                        article_id = hashlib.sha256(article_url.encode("ascii")).hexdigest()
                        article_data = {}

                        article_db_obj = self.helper.sync_find_if_exists(article_id)
                        if article_db_obj == None:
                            article_screenshot_paths = self.helper.get_image_path(article_id)
                            save_element_image(card, article_screenshot_paths["path"], sibling_check=True)
                            article_data["screenshot_url"] = article_screenshot_paths["url"]
                            article_data["screenshot_path"] = article_screenshot_paths["path"]

                            article_headline_spans = article_link_element.find_elements(By.CSS_SELECTOR, ".list-headline__text > span")
                            if len(article_headline_spans) == 1:
                                article_data["kicker"] = None
                                article_data["headline"] = article_headline_spans[0].get_attribute("innerText")
                                article_data["title"] = article_data["headline"]
                            else:
                                article_data["kicker"] = article_headline_spans[0].get_attribute("innerText")
                                article_data["headline"] = article_headline_spans[1].get_attribute("innerText")
                                article_data["title"] = "%s: %s" % (article_data["kicker"], article_data["headline"])

                            article_data["section"] = package_heading
                            article_data["url"] = article_url
                            try:
                                card_meta = card.find_element(By.CSS_SELECTOR, ".card-meta")
                                card_meta_text = card_meta.get_attribute("innerText")
                                article_data["standfirst"] = card_meta_text if card_meta_text != "" else None
                            except:
                                pass
                            report = self.helper.sync_report(article_id, article_data)
                            self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                        else:
                            self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                            self.log("Inserted presence into %s" % article_id)
                
                article_lists = self.driver.find_elements(By.CSS_SELECTOR, ".article-list")
                last_article_list_heading_url = None
                last_article_list_heading_text = None

                for article_list in article_lists:
                    article_list_heading_url = None
                    article_list_heading_text = None

                    try:
                        article_list_heading_link = article_list.find_element(By.CSS_SELECTOR, ".article-list__heading-link")
                        article_list_heading_url = article_list_heading_link.get_attribute("href")
                        article_list_heading_text = article_list_heading_link.get_attribute("innerText")
                        last_article_list_heading_text = article_list_heading_text
                        last_article_list_heading_url = article_list_heading_url
                    except:
                        try:
                            article_list_heading_url = None
                            article_list_heading_text = article_list.find_element(By.CSS_SELECTOR, ".article-list__heading").get_attribute("innerText")
                            last_article_list_heading_text = article_list_heading_text
                            last_article_list_heading_url = article_list_heading_url
                        except:
                            article_list_heading_url = last_article_list_heading_url
                            article_list_heading_text = last_article_list_heading_text

                    cards = article_list.find_elements(By.CSS_SELECTOR, ".card")
                    for card in cards:
                        article_link_element = card.find_element(By.CSS_SELECTOR, ".list-headline__link")
                        article_url = article_link_element.get_attribute("href")
                        article_id = hashlib.sha256(article_url.encode("ascii")).hexdigest()
                        article_data = {}

                        article_db_obj = self.helper.sync_find_if_exists(article_id)
                        if article_db_obj == None:
                            article_screenshot_paths = self.helper.get_image_path(article_id)
                            save_element_image(card, article_screenshot_paths["path"], sibling_check=False)
                            article_data["screenshot_url"] = article_screenshot_paths["url"]
                            article_data["screenshot_path"] = article_screenshot_paths["path"]

                            article_headline_spans = article_link_element.find_elements(By.CSS_SELECTOR, ".list-headline__text > span")
                            if len(article_headline_spans) == 1:
                                article_data["kicker"] = None
                                article_data["headline"] = article_headline_spans[0].get_attribute("innerText")
                                article_data["title"] = article_data["headline"]
                            else:
                                article_data["kicker"] = article_headline_spans[0].get_attribute("innerText")
                                article_data["headline"] = article_headline_spans[1].get_attribute("innerText")
                                article_data["title"] = "%s: %s" % (article_data["kicker"], article_data["headline"])

                            article_data["section"] = article_list_heading_text
                            article_data["section_url"] = article_list_heading_url
                            article_data["url"] = article_url
                            try:
                                card_standfirst = card.find_element(By.CSS_SELECTOR, ".e-standfirst")
                                card_standfirst_text = card_standfirst.get_attribute("innerText")
                                article_data["standfirst"] = card_standfirst_text if card_standfirst_text != "" else None
                            except:
                                article_data["standfirst"] = None
                            report = self.helper.sync_report(article_id, article_data)
                            self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                        else:
                            self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                            self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(self.helper.interval_page_ready())
                check_cookie_disclaimer()
                time.sleep(2)
                check_subscribe_modal()
                time.sleep(2)
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
