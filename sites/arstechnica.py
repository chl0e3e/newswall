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

class ArsTechnica:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://arstechnica.com/"
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.helper.sync_log(message, exception=exception)

    def start(self):
        self.setup_chromedriver()
        self.xdotool.activate()
        self.xdotool.size(1920, 1080)

        while self.driver != None:
            self.log("Fetching Ars Technica")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "main")))
            
            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")
                    if consent_elements != None and len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        consent_elements[0].click()
                except:
                    self.log("Failed to find cookie disclaimer")

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
                
                articles = self.driver.find_elements(By.CSS_SELECTOR, "li.article")

                for article in articles:
                    article_data = {}
                    article_link_element = None
                    try:
                        article_link_element = article.find_element(By.CSS_SELECTOR, "h2 > a")
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
                        article_data["excerpt"] = article.find_element(By.CSS_SELECTOR, ".excerpt").get_attribute("innerText")
                        article_data["date"] = int(article.find_element(By.CSS_SELECTOR, "time").get_attribute("data-time"))
                        article_data["comment_count"] = int(article.find_element(By.CSS_SELECTOR, ".comment-count-number").get_attribute("innerText"))
                        
                        article_byline_element = article.find_element(By.CSS_SELECTOR, ".byline > a")
                        article_data["author"] = article_byline_element.get_attribute("innerText").strip()
                        article_data["author_url"] = article_byline_element.get_attribute("href")

                        report = self.helper.sync_report(article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(5)
                time.sleep(1)
                check_cookie_disclaimer()
                #wait_for_page_ready(5)
                #self.helper.scroll_down_page()
                save_articles()
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
