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

class TechCrunch:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://techcrunch.com/"

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

        self.helper.log("Fetching TechCrunch")

        def navigate():
            self.helper.log("Navigating to page: %s" % (self.url))
            self.driver.get(self.url)

        def wait_for_page_ready(interval):
            self.helper.log("Waiting for page")
            WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#consent-page, #root")))
        
        def check_cookie_disclaimer():
            try:
                consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "#consent-page [value='agree']")
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
            self.helper.log("Saving articles")
            
            articles = self.driver.find_elements(By.CSS_SELECTOR, ".mini-view__item, .feature-island-main-block, article.post-block")

            for article in articles:
                article_data = {}
                article_link_element = None
                try:
                    article_link_element = article.find_element(By.CSS_SELECTOR, "h2>a, h3>a")
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
                    try:
                        article_time_element = article.find_element(By.CSS_SELECTOR, "time")
                        article_data["date"] = article_time_element.get_attribute("datetime")
                        article_data["date_human"] = article_time_element.get_attribute("innerText")
                    except:
                        article_data["date"] = None
                        article_data["date"] = None
                    
                    try:
                        article_byline_element = article.find_element(By.CSS_SELECTOR, "[class*='__byline'] a")
                        article_data["author"] = article_byline_element.get_attribute("innerText").strip()
                        article_data["author_url"] = article_byline_element.get_attribute("href")
                    except:
                        article_byline_element = article.find_element(By.CSS_SELECTOR, "[class*='byline__authors'] a")
                        article_data["author"] = article_byline_element.get_attribute("innerText").strip()
                        article_data["author_url"] = article_byline_element.get_attribute("href")

                    try:
                        article_category_element = article.find_element(By.CSS_SELECTOR, "a[class*='category__link']")
                        article_data["category"] = article_category_element.get_attribute("innerText").strip()
                        article_data["category_url"] = article_category_element.get_attribute("href")
                    except:
                        article_data["category"] = None
                        article_data["category_url"] = None

                    try:
                        article_data["summary"] = article.find_element(By.CSS_SELECTOR, ".post-block__content").get_attribute("innerText")
                    except:
                        article_data["summary"] = None

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
            #wait_for_page_ready(self.helper.interval_page_ready())
            #self.helper.scroll_down_page()
            save_articles()
        except Exception as e:
            self.helper.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
            self.helper.log("Shutting down")
        finally:
            self.helper.stop()
