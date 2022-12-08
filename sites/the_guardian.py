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

class TheGuardian:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.theguardian.com/uk"
    
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

            self.log("Fetching The Guardian")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.CLASS_NAME, "facia-page")))
            
            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='Iframe title']")
                    if consent_elements != None and len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='Yes, I’m happy']").click()
                        self.driver.switch_to.default_content()
                except:
                    self.log("Failed to find cookie disclaimer")

            def check_cookie_disclaimer_2():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='The Guardian consent message']")
                    if consent_elements != None and len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='Yes, I’m happy']").click()
                        self.driver.switch_to.default_content()
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
                
                try:
                    self.driver.execute_script("document.querySelector('.site-message--banner').remove()")
                except:
                    self.helper.log("Failed to remove banner")
                    pass
                
                articles = self.driver.find_elements(By.CSS_SELECTOR, ".fc-item")

                for article in articles:
                    article_data = {}
                    article_link_element = None
                    try:
                        article_link_element = article.find_element(By.CSS_SELECTOR, ".fc-item__link")
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

                        article_data["headline"] = article_link_element.find_element(By.CSS_SELECTOR, ".fc-item__headline").get_attribute("innerText")

                        try:
                            article_data["kicker"] = article_link_element.find_element(By.CSS_SELECTOR, ".fc-item__kicker").get_attribute("innerText")
                            article_data["title"] = "%s / %s" % (article_data["kicker"], article_data["headline"])
                        except:
                            article_data["kicker"] = None
                            article_data["title"] = article_data["headline"]

                        try:
                            article_data["standfirst"] = article.find_element(By.CSS_SELECTOR, ".fc-item__standfirst").get_attribute("innerText").strip()
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
                time.sleep(1)
                check_cookie_disclaimer()
                check_cookie_disclaimer_2()
                time.sleep(5)
                #wait_for_page_ready(self.helper.interval_page_ready())
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
