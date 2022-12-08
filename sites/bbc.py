from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from PIL import Image, ImageChops
from io import BytesIO
import datetime
import hashlib
import time
import traceback

class BBC:
    def __init__(self, helper):
        self.helper = helper
        self.driver = None
        self.url = "https://www.bbc.co.uk/news/"
        self.categories = {}

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

            self.helper.log("Fetching BBC")

            def navigate():
                self.helper.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.helper.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "orb-modules")))
            
            def check_cookie_disclaimer():
                try:
                    consent_buttons = self.driver.find_elements(By.CSS_SELECTOR, "#bbccookies-continue-button")
                    consent_buttons[0].click()
                except Exception as e:
                    exception_str = traceback.format_exc()
                    self.helper.log("Failed to find cookie disclaimer", exception=exception_str)
            
            def check_cookie_disclaimer_2():
                try:
                    consent_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".fc-cta-consent")
                    if len(consent_buttons) > 0:
                        consent_buttons[0].click()
                except Exception as e:
                    exception_str = traceback.format_exc()
                    self.helper.log("Failed to find cookie disclaimer 2", exception=exception_str)

            def save_element_image_2(element, file):
                if element.size['width'] > 0 or element.size['height'] > 0:
                    element.screenshot(file)
                    return True
                else:
                    return False

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
                    bg = Image.new(im.mode, im.size, (255,255,255))
                    diff = ImageChops.difference(im, bg)
                    diff = ImageChops.add(diff, diff, 2.0, -100)
                    bbox = diff.getbbox()
                    if bbox:
                        return im.crop(bbox)
                    else:
                        return trim(im.convert('RGB'))
                
                trim(im).save(file)
                return True

            def save_articles(category=None):

                self.helper.log("Saving articles for '%s'" % ("Front Page" if category == None else category))
                if category == None:
                    category_links = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label='news'] .nw-o-link")
                    categories = []
                    for category_link in category_links:
                        category_name = category_link.find_elements(By.CSS_SELECTOR, "span")[0].get_attribute("innerText")
                        category_url = category_link.get_attribute("href")
                        if not category_url in categories:
                            self.helper.log("Found category %s @ %s" % (category_name, category_url))
                            self.categories[category_name] = category_url
                            categories.append(category_url)
                else:
                    self.driver.get(self.categories[category])

                    wait_for_page_ready(self.helper.interval_page_ready())
                    time.sleep(10)
                    check_cookie_disclaimer()
                    check_cookie_disclaimer_2()

                promos = self.driver.find_elements(By.CSS_SELECTOR, ".gs-c-promo")

                for article in promos:
                    article_data = {}
                    try:
                        article_link_element = article.find_element(By.CSS_SELECTOR, ".gs-c-promo-heading")
                        if article_link_element.tag_name != "a":
                            continue
                        article_data["url"] = article_link_element.get_attribute("href")
                    except:
                        article_link_element = article.find_element(By.CSS_SELECTOR, "a")
                        article_data["url"] = article_link_element.get_attribute("href")

                    article_id = hashlib.sha256(article_data["url"].encode("ascii")).hexdigest()
                    self.helper.log("Saving article %s <%s>" % (article_id, article_data["url"]))

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        self.helper.log("Saving %s" % (article_data["url"]))

                        article_screenshot_paths = self.helper.get_image_path(article_id)
                        article_screenshot_saved = save_element_image(article, article_screenshot_paths["path"])
                        if article_screenshot_saved:
                            article_data["screenshot_url"] = article_screenshot_paths["url"]
                            article_data["screenshot_path"] = article_screenshot_paths["path"]
                        else:
                            self.helper.log("Failed to save article image %s" % (article_data["url"]))

                        try:
                            article_data["title"] = article.find_element(By.CSS_SELECTOR, ".gs-c-promo-heading__title").get_attribute("innerText")
                        except:
                            article_data["title"] = article_link_element.get_attribute("innerText")

                        try:
                            article_data["summary"] = article.find_element(By.CSS_SELECTOR, ".gs-c-promo-summary").get_attribute("innerText")
                        except:
                            article_data["summary"] = None

                        try:
                            article_data["datetime"] = article.find_element(By.CSS_SELECTOR, ".date").get_attribute("datetime")
                        except:
                            article_data["datetime"] = None

                        try:
                            section_link_element = article.find_element(By.CSS_SELECTOR, ".gs-c-section-link")
                            article_data["section"] = section_link_element.get_attribute("innerText").strip()
                            article_data["section_url"] = section_link_element.get_attribute("href")
                        except:
                            article_data["section"] = None
                            article_data["section_url"] = None

                        if category == None:
                            article_data["category"] = "Front Page"
                            article_data["category_url"] = self.url
                        else:
                            article_data["category"] = category
                            article_data["category_url"] = self.categories[category]

                        report = self.helper.sync_report(article_id, article_data)
                        self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.helper.log("Inserted presence into %s" % article_id)

                qas = self.driver.find_elements(By.CSS_SELECTOR, ".qa-post")

                for article in qas:
                    article_data = {}
                    article_title = article.find_element(By.CSS_SELECTOR, ".lx-stream-post__header-text").get_attribute("innerText")
                    try:
                        article_link_element = article.find_element(By.CSS_SELECTOR, ".qa-heading-link")
                        if article_link_element.tag_name != "a":
                            continue
                        article_data["url"] = article_link_element.get_attribute("href")
                    except:
                        article_data["url"] = self.categories[category]
                    article_id = hashlib.sha256(article_title.encode()).hexdigest()

                    article_db_obj = self.helper.sync_find_if_exists(article_id)
                    if article_db_obj == None:
                        self.helper.log("Saving %s" % (article_data["url"]))

                        article_screenshot_paths = self.helper.get_image_path(article_id)
                        article_screenshot_saved = save_element_image(article, article_screenshot_paths["path"])
                        if article_screenshot_saved:
                            article_data["screenshot_url"] = article_screenshot_paths["url"]
                            article_data["screenshot_path"] = article_screenshot_paths["path"]
                        else:
                            self.helper.log("Failed to save article image using first method %s" % (article_data["url"]))
                            article_screenshot_saved = save_element_image_2(article, article_screenshot_paths["path"])
                            if article_screenshot_saved:
                                article_data["screenshot_url"] = article_screenshot_paths["url"]
                                article_data["screenshot_path"] = article_screenshot_paths["path"]
                            else:
                                self.helper.log("Failed to save article image using second method %s" % (article_data["url"]))

                        article_data["title"] = article_title
                        
                        try:
                            article_data["summary"] = article.find_element(By.CSS_SELECTOR, ".qa-story-summary").get_attribute("innerText")
                        except:
                            article_data["summary"] = None

                        try:
                            article_data["datetime"] = article.find_element(By.CSS_SELECTOR, ".lx-stream-post__meta-time .qa-post-auto-meta").get_attribute("innerText")
                        except:
                            article_data["datetime"] = None

                        try:
                            article_data["contributor_name"] = article.find_element(By.CSS_SELECTOR, ".qa-contributor-name").get_attribute("innerText")
                        except:
                            article_data["contributor_name"] = None

                        try:
                            article_data["contributor_role"] = article.find_element(By.CSS_SELECTOR, ".qa-contributor-role").get_attribute("innerText")
                        except:
                            article_data["contributor_role"] = None

                        try:
                            section_link_element = article.find_element(By.CSS_SELECTOR, ".gs-c-section-link")
                            article_data["section"] = section_link_element.get_attribute("innerText").strip()
                            article_data["section_url"] = section_link_element.get_attribute("href")
                        except:
                            article_data["section"] = None
                            article_data["section_url"] = None

                        try:
                            article_data["body"] = article.find_element(By.CSS_SELECTOR, ".lx-stream-post-body").get_attribute("innerText")
                        except:
                            article_data["body"] = None

                        if category == None:
                            article_data["category"] = "Front Page"
                            article_data["category_url"] = self.url
                        else:
                            article_data["category"] = category
                            article_data["category_url"] = self.categories[category]

                        report = self.helper.sync_report(article_id, article_data)
                        self.helper.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.helper.sync_insert_presence(article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.helper.log("Inserted presence into %s" % article_id)
                
                if category == None:
                    for category_name, category_url in self.categories.items():
                        if category_name != "Home":
                            save_articles(category_name)

            try:
                navigate()
                    
                wait_for_page_ready(self.helper.interval_page_ready())
                time.sleep(10)
                check_cookie_disclaimer()
                check_cookie_disclaimer_2()
                #time.sleep(2)
                #check_subscribe_modal()
                #time.sleep(2)
                #scroll_down_page()
                save_articles()
            except Exception as e:
                self.helper.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.helper.log("Shutting down")
                self.stop()
            
            sleep_interval = self.helper.interval()
            self.log("Sleeping for %d seconds" % sleep_interval)
            time.sleep(sleep_interval)
        
        self.helper.log("Exited main loop")
    
    def stop(self):
        if self.driver != None:
            self.driver.quit()
            self.driver = None
    
    def setup_chromedriver(self):
        self.helper.log("Initialising a new Chrome instance")

        if self.driver != None:
            self.stop()
            
        xdotool, driver = self.helper.sync_uc()
        self.driver = driver
        self.xdotool = xdotool