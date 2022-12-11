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

class AssociatedPress:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://apnews.com/"

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

        self.helper.log("Fetching Associated Press")

        def navigate():
            self.helper.log("Navigating to page: %s" % (self.url))
            self.driver.get(self.url)

        def wait_for_page_ready(interval):
            self.helper.log("Waiting for page")
            WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cnx-playspace-container")))
        
        def check_cookie_disclaimer():
            try:
                consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")
                if consent_elements != None and len(consent_elements) > 0:
                    self.helper.log("Cookie disclaimer found")
                    consent_elements[0].click()
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
            
            im.save(file)
            return True

        def save_articles():
            self.helper.log("Saving articles")

            self.driver.execute_script("document.querySelector('.Header').remove()")
            
            main_story = self.driver.find_elements(By.CSS_SELECTOR, "[data-key='main-story']")
            main_story_container = self.driver.execute_script("return arguments[0].children[0]", main_story[0])
            main_story_container_children = self.driver.execute_script("return arguments[0].children", main_story_container)
            i = 0

            for article in main_story_container_children:
                if i == 0:
                    article_data = {}
                    article_link_elements = article.find_elements(By.CSS_SELECTOR, "li > a")
                    article_link_elements.pop(0)
                    for article_link in article_link_elements:
                        article_data["url"] = article_link.get_attribute("href")
                        article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                        article_db_obj = self.helper.sync_find_if_exists(article_id)
                        if article_db_obj == None:
                            article_screenshot_paths = self.helper.get_image_path(article_id)
                            save_element_image(article, article_screenshot_paths["path"])
                            article_data["screenshot_url"] = article_screenshot_paths["url"]
                            article_data["screenshot_path"] = article_screenshot_paths["path"]
                            article_data["title"] = article_link.find_element(By.CSS_SELECTOR, "h4").get_attribute("innerText")
                        else:
                            self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                            self.helper.log("Inserted presence into %s" % article_id)

                article_data = {}
                article_link_element = None
                article_link_element = article.find_element(By.CSS_SELECTOR, "a")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["section"] = "Main Story"
                    article_data["title"] = article_link_element.find_element(By.CSS_SELECTOR, "h2, h3").get_attribute("innerText")
                    article_data["timestamp"] = article.find_element(By.CSS_SELECTOR, ".Timestamp").get_attribute("data-source")

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
                
                i += 1
            
            for i in range(4):
                for _ in range(10): self.xdotool.scroll_down()
                feed_card = self.driver.find_elements(By.CSS_SELECTOR, ".FeedCard")[0]
                feed_card_ss_element = self.driver.execute_script("return arguments[0].querySelector('.cnxOuter');", feed_card)
                feed_card_children = self.driver.execute_script("return arguments[0].querySelector('.cnxSideSlideCont').children;", feed_card)

                article_data = {}

                article_title_element = feed_card_children[i].find_element(By.CSS_SELECTOR, "h4")
                article_data["title"] = article_title_element.get_attribute("innerText")
                article_id = hashlib.sha256(article_data["title"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    while True:
                        if len(feed_card_children[i].find_elements(By.CSS_SELECTOR, ".currentCont")) > 0:
                            break
                        else:
                            time.sleep(1)

                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(feed_card_ss_element, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_title_element.click()
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "root")))
                    time.sleep(5)

                    article_data["url"] = self.driver.current_url
                    article_data["section"] = "Trending News"
                    self.driver.get(self.url)
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "root")))
                    self.driver.execute_script("document.querySelector('.Header').remove()")

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
            
            self.helper.scroll_down_page(4)

            articles = self.driver.find_elements(By.CSS_SELECTOR, ".hubPeekStory")

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

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, "h4").get_attribute("innerText")

                    try:
                        article_data["description"] = article.find_element(By.CSS_SELECTOR, "img").get_attribute("alt")
                    except:
                        pass

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
                    
            articles = self.driver.find_elements(By.CSS_SELECTOR, ".FeedCard[data-card-id][data-key]")
            for article in articles:
                article_data = {}
                article_link_element = article.find_element(By.CSS_SELECTOR, "a[data-key='card-headline']")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, "h2").get_attribute("innerText")
                    article_data["timestamp"] = article.find_element(By.CSS_SELECTOR, ".Timestamp").get_attribute("data-source")

                    article_data["description"] = article.find_element(By.CSS_SELECTOR, ".content > p").get_attribute("innerText").strip()
                    
                    try:
                        article_data["author"] = article.find_element(By.CSS_SELECTOR, "span[class*='bylines']").get_attribute("innerText")
                    except:
                        article_data["author"] = None

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)

                    
            articles = self.driver.find_elements(By.CSS_SELECTOR, "[data-card-index]")
            for article in articles:
                article_data = {}
                article_link_element = article.find_element(By.CSS_SELECTOR, "a.item-label-href")
                article_data["url"] = article_link_element.get_attribute("href")
                article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()
                
                if not "https://apnews.com" in article_data["url"]:
                    continue

                article_db_obj = self.helper.sync_find_if_exists(article_id)
                if article_db_obj == None:
                    article_screenshot_paths = self.helper.get_image_path(article_id)
                    save_element_image(article, article_screenshot_paths["path"])
                    article_data["screenshot_url"] = article_screenshot_paths["url"]
                    article_data["screenshot_path"] = article_screenshot_paths["path"]

                    article_data["title"] = article.find_element(By.CSS_SELECTOR, ".video-title").get_attribute("innerText")
                    try:
                        article_data["timestamp"] = article.find_element(By.CSS_SELECTOR, "dt").get_attribute("innerText")
                    except:
                        article_data["timestamp"] = None

                    try:
                        article_data["description"] = article.find_element(By.CSS_SELECTOR, ".video-description").get_attribute("innerText").strip()
                    except:
                        article_data["description"] = None

                    report = self.helper.sync_report(article_id, article_data)
                    self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                else:
                    self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                    self.helper.log("Inserted presence into %s" % article_id)
        try:
            navigate()
            wait_for_page_ready(self.helper.interval_page_ready())
            time.sleep(1)
            check_cookie_disclaimer()
            save_articles()
        except Exception as e:
            self.helper.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
            self.helper.log("Shutting down")
        finally:
            self.helper.stop()
    