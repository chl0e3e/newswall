from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from PIL import Image, ImageChops

from io import BytesIO
import datetime
import time
import traceback
import hashlib

class Metro:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.metro.co.uk/"

    def start(self):
        try:
            self.helper.log("Setting up chromedriver")
            self.xdotool, self.driver = self.helper.sync_uc()
            self.xdotool.activate()
            self.xdotool.size("100%", "100%")
        except Exception as e:
            exception_str = traceback.format_exc()
            self.helper.log("Failed during setup", exception=exception_str)
            self.helper.stop()
            return

        self.helper.log("Fetching Metro")

        def navigate():
            self.helper.log("Navigating to page: %s" % (self.url))
            self.driver.get(self.url)

        def wait_for_page_ready(interval):
            self.helper.log("Waiting for page")
            WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "pageBody")))

        def check_cookie_disclaimer():
            try:
                consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-project='mol-fe-cmp'] button")
                if len(consent_elements) > 0:
                    self.helper.log("Cookie disclaimer found")
                    consent_elements[1].click()
                    time.sleep(1)
            except:
                self.helper.log("Failed to find cookie disclaimer")

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

            def trim(im, depth=0):
                if depth == 3:
                    return im
                bg = Image.new(im.mode, im.size, (255, 255, 255))
                diff = ImageChops.difference(im, bg)
                diff = ImageChops.add(diff, diff, 2.0, -100)
                bbox = diff.getbbox()
                if bbox:
                    return im.crop(bbox)
                else:
                    return trim(im.convert('RGB'), depth+1)
            
            trim(im).save(file)
            return True

        def save_articles():
            self.helper.log("Saving articles")

            current_section = "Just In"
            current_section_url = self.url
            for article in self.driver.find_elements(By.CSS_SELECTOR, "[data-track='just-in/item']"):
                article_data = {}
                article_data["url"] = article.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, ".ji-text").get_attribute("innerText").strip()

                    article_data["section"] = current_section
                    article_data["section_url"] = current_section_url

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

            articles = self.driver.find_elements(By.CSS_SELECTOR, ".nf-item")

            current_section = "News Feed"
            current_section_url = self.url
            for article in articles:
                article_data = {}
                article_title_element = article.find_element(By.CSS_SELECTOR, ".nf-title")
                article_link_element = article_title_element.find_element(By.CSS_SELECTOR, "a")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article_title_element.get_attribute("innerText").strip()

                    article_data["section"] = current_section
                    article_data["section_url"] = current_section_url

                    try:
                        article_data["summary"] = article.find_element(By.CSS_SELECTOR, ".nf-excerpt").get_attribute("innerText")
                    except:
                        pass

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

            articles = self.driver.find_elements(By.CSS_SELECTOR, ".trending-main li")

            current_section = "What's Trending Now"
            current_section_url = self.url
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

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, "h3").get_attribute("innerText").strip()

                    article_data["section"] = current_section
                    article_data["section_url"] = current_section_url

                    try:
                        article_data["summary"] = article.find_element(By.CSS_SELECTOR, "[data-track*='excerpt']").get_attribute("innerText")
                    except:
                        pass

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

            articles = self.driver.find_elements(By.CSS_SELECTOR, ".top-stories-item, .top-stories-first-item")

            current_section = "Top Stories"
            current_section_url = self.url
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

                    article_data["title"] = None
                    try:
                        article_data["title"] = article.find_element(By.CSS_SELECTOR, "h3").get_attribute("innerText").strip()
                    except:
                        pass

                    article_data["section"] = current_section
                    article_data["section_url"] = current_section_url

                    try:
                        article_data["summary"] = article.find_element(By.CSS_SELECTOR, "[data-track*='excerpt']").get_attribute("innerText")
                    except:
                        pass

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
                    
            articles = self.driver.find_elements(By.CSS_SELECTOR, ".metro__post")

            current_section = "Top Stories"
            current_section_url = self.url
            for article in articles:
                article_data = {}
                article_title_element = article.find_element(By.CSS_SELECTOR, ".metro__post__title")
                article_link_element = article.find_element(By.CSS_SELECTOR, "a")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article_title_element.find_element(By.CSS_SELECTOR, ".metro__post__title__decoration").get_attribute("innerText").strip()

                    article_data["section"] = current_section
                    article_data["section_url"] = current_section_url

                    try:
                        article_data["summary"] = article.find_element(By.CSS_SELECTOR, ".metro__post__excerpt").get_attribute("innerText")
                    except:
                        pass

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
            
            articles = self.driver.find_elements(By.CSS_SELECTOR, ".ada-story-container")
            for article in articles:
                article_data = {}
                article_link_element = article.find_element(By.CSS_SELECTOR, ".ada-title")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, "h3").get_attribute("innerText").strip()

                    article_data["section"] = None
                    article_data["section_url"] = None
                    article_data["summary"] = None

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

            articles = self.driver.find_elements(By.CSS_SELECTOR, "a[data-postid]")
            for article in articles:
                article_data = {}
                article_data["url"] = article.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, "h2").get_attribute("innerText").strip()

                    article_data["section"] = None
                    article_data["section_url"] = None
                    article_data["summary"] = None

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

            articles = self.driver.find_elements(By.CSS_SELECTOR, ".metro-columnists-item")
            for article in articles:
                article_data = {}
                article_data["url"] = article.find_element(By.CSS_SELECTOR, ".metro-columnists-item-container").get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, ".metro-columnists-excerpt").get_attribute("innerText").strip()

                    article_data["section"] = "Columnists"
                    article_data["section_url"] = self.url
                    article_data["summary"] = None

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

        try:
            navigate()
            wait_for_page_ready(self.helper.interval_page_ready())
            time.sleep(2)
            check_cookie_disclaimer()
            self.helper.scroll_down_page()
            save_articles()
        except Exception as e:
            self.helper.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
            self.helper.log("Shutting down")
        finally:
            self.helper.stop()