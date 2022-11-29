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
import time
import traceback

__site__ = "the_sun"
__site_name__ = "The Sun"
__type__ = "TheSun"

class TheSun:
    def __init__(self, newswall):
        self.newswall = newswall
        self.driver = None
        self.url = "https://www.thesun.co.uk/"
        self.page_scroll_interval = 0.05
        self.id = __site__
        self.name = __site_name__
    
    def interval(self):
        return 30

    def log(self, message, exception=None):
        return self.newswall.sync_log(__site__, message, exception=exception)

    def start(self):
        self.setup_chromedriver()
        self.xdotool.activate()
        self.xdotool.size(1920, 1080)

        while self.driver != None:
            self.log("Fetching The Sun")

            def navigate():
                self.log("Navigating to page: %s" % (self.url))
                self.driver.get(self.url)

            def wait_for_page_ready(interval):
                self.log("Waiting for page")
                WebDriverWait(self.driver, interval).until(EC.presence_of_element_located((By.ID, "main-content")))

            def check_cookie_disclaimer():
                try:
                    consent_elements = self.driver.find_elements(By.CSS_SELECTOR, "[title='SP Consent Message']")
                    if len(consent_elements) > 0:
                        self.log("Cookie disclaimer found")
                        self.driver.switch_to.frame(consent_elements[0])
                        self.driver.find_element(By.CSS_SELECTOR, "[title='Fine By Me!']").click()
                        self.driver.switch_to.default_content()
                        time.sleep(1)
                except:
                    self.log("Failed to find cookie disclaimer")
            
            def scroll_down_page():
                self.log("Scrolling down the page")
                page_height = self.driver.execute_script("return document.body.scrollHeight")
                browser_height = self.driver.get_window_size()["height"]
                last_scroll_y = 0
                scroll_y = 0
                self.log("page_height: %d, browser_height: %d" % (page_height, browser_height))
                while True:
                    self.xdotool.scroll_down()
                    time.sleep(self.page_scroll_interval)
                    scroll_y = self.driver.execute_script("return window.scrollY")
                    self.log("scroll_y: %d" % (scroll_y))
                    if scroll_y == last_scroll_y and scroll_y > browser_height:
                        self.log("No more page to scroll")
                        break
                    last_scroll_y = scroll_y

            def save_element_image(element, file):
                location = element.location_once_scrolled_into_view
                png = self.driver.get_screenshot_as_png() # saves screenshot of entire page

                im = Image.open(BytesIO(png)) # uses PIL library to open image in memory

                left = location['x']
                top = location['y']
                
                size = self.driver.execute_script("var element = arguments[0]; var b = window.getComputedStyle(element); return [b.width, b.height]", element)
                width = int(float(size[0].replace("px", "")))
                height = int(float(size[1].replace("px", "")))

                right = left + width
                bottom = top + height

                im = im.crop((left, top, right, bottom))
                im.save(file)

            def save_articles():
                self.log("Saving articles")
                header = self.driver.find_element(By.CSS_SELECTOR, '#react-root > div > .sun-container > .theme-main:first-of-type')
                self.driver.execute_script("var element = arguments[0]; element.parentNode.removeChild(element);", header)

                articles = self.driver.find_elements(By.CSS_SELECTOR, "[data-id]")
                for article in articles:
                    article_id = article.get_attribute("data-id")

                    article_db_obj = self.newswall.sync_find_if_exists(__site__, article_id)
                    if article_db_obj == None:
                        article_data = {
                            "type": article.get_attribute("data-type")
                        }
                        
                        article_ss_element = article
                        if article_data["type"] == "small-teaser":
                            article_ss_element = article.find_element(By.XPATH, '..')

                        article_screenshot_paths = self.newswall.get_image_path(__site__, article_id)
                        save_element_image(article_ss_element, article_screenshot_paths["path"])
                        article_data["screenshot_url"] = article_screenshot_paths["url"]
                        article_data["screenshot_path"] = article_screenshot_paths["path"]

                        if article_data["type"] == "hero-splash-teaser":
                            article_data["url"] = article.find_element(By.CSS_SELECTOR, "a:first-of-type").get_attribute("href")
                            article_data["tagline"] = article.find_element(By.CSS_SELECTOR, ".splash-teaser-kicker").get_attribute("aria-label")
                            article_data["headline"] = article.find_element(By.CSS_SELECTOR, ".nk-headline-heading").get_attribute("innerText")
                            article_data["title"] = "%s: %s" % (article_data["tagline"], article_data["headline"])
                            section = article.find_element(By.CSS_SELECTOR, ".splash-section-name")
                            article_data["section_url"] = section.get_attribute("href")
                            article_data["section"] = section.find_element(By.TAG_NAME, "span").text
                        elif article_data["type"] == "small-teaser":
                            copy_link_element = article.find_element(By.CSS_SELECTOR, ".teaser__copy-container > a")
                            article_data["url"] = copy_link_element.get_attribute("href")
                            article_data["tagline"] = copy_link_element.find_element(By.CSS_SELECTOR, ".teaser__headline").get_attribute("innerText")
                            article_data["headline"] = copy_link_element.find_element(By.CSS_SELECTOR, ".teaser__subdeck").get_attribute("innerText").strip()
                            article_data["title"] = "%s: %s" % (article_data["tagline"], article_data["headline"])
                            section = article.find_element(By.CSS_SELECTOR, ".article-data__tag > a")
                            article_data["section"] = section.get_attribute("innerText")
                            article_data["section_url"] = section.get_attribute("href")
                        elif article_data["type"] == "large-teaser" or article_data["type"] == "large-side-teaser":
                            article_data["url"] = article.find_element(By.CSS_SELECTOR, "a:first-of-type").get_attribute("href")
                            article_data["tagline"] = article.find_element(By.CSS_SELECTOR, ".teaser__headline").get_attribute("innerText")
                            article_data["headline"] = article.find_element(By.CSS_SELECTOR, ".teaser__subdeck").get_attribute("innerText").strip()
                            article_data["title"] = "%s: %s" % (article_data["tagline"], article_data["headline"])
                            article_data["lead"] = article.find_element(By.CSS_SELECTOR, ".teaser__lead").get_attribute("innerText")
                            section = article.find_element(By.CSS_SELECTOR, ".article-data__tag > a")
                            article_data["section"] = section.get_attribute("innerText")
                            article_data["section_url"] = section.get_attribute("href")

                        try:
                            article.find_element(By.CSS_SELECTOR, ".teaser__item-play")
                            article_data["video"] = True
                        except:
                            article_data["video"] = False
                                
                        report = self.newswall.sync_report(__site__, article_id, article_data)
                        self.log("Inserted report %s: %s" % (article_id, report.inserted_id))
                    else:
                        self.newswall.sync_insert_presence(__site__, article_db_obj.get('_id'), datetime.datetime.utcnow())
                        self.log("Inserted presence into %s" % article_id)

            try:
                navigate()
                wait_for_page_ready(5)
                check_cookie_disclaimer()
                scroll_down_page()
                save_articles()
            except Exception as e:
                self.log("Failed waiting for site: %s" % (str(e)), exception=traceback.format_exc())
                self.log("Shutting down")
                self.stop()
            
            time.sleep(self.interval())
        
        self.log("Exited main loop")
    
    def stop(self):
        if self.driver != None:
            self.driver.quit()
            self.driver = None
    
    def setup_chromedriver(self):
        self.log("Initialising a new Chrome instance")

        if self.driver != None:
            self.stop()
            
        xdotool, driver = self.newswall.sync_uc(__site__)
        self.driver = driver
        self.xdotool = xdotool
