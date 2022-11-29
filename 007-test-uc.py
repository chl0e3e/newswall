#!/usr/bin/env python3
import sys
import os

print("getting build vars")
from buildutil import get_build_var
chromedriver_path = get_build_var("chromedriver")
chrome_path = get_build_var("chrome")

print("importing uc")
import uc

print("creating driver instance")
driver = uc.Chrome(driver_executable_path=chromedriver_path, browser_executable_path=chrome_path, use_subprocess=False)

print("getting nowsecure page")
driver.get('https://nowsecure.nl')

print("waiting for presence of '.lead'")
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
try:
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "lead")))
except:
    driver.quit()
    print("failed waiting for lead element")
    sys.exit(1)

print("finding '.lead' elements")
try:
    elements = driver.find_elements(By.CLASS_NAME, 'lead')

    print("")
    print("%d elements found:" % (len(elements)))
    i=0
    for element in elements:
        print("[%d] %s" % (i, element.text))
        i = i + 1
except:
    driver.quit()
    print("failed getting lead element")
    sys.exit(2)