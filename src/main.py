#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import time
from selenium.webdriver.firefox.webdriver import WebDriver
import requests
from bs4 import BeautifulSoup
import re
import csv

ROOT_URL = "https://www.tokopedia.com/p/handphone-tablet/handphone?page={}"
UA = 'Mozilla/5.0'
PRODUCTS = []

def load_content(driver: Firefox):
    print("Loading Content")
    actions = ActionChains(driver)
    actions.send_keys(Keys.SPACE).perform()
    time.sleep(1)
    for _ in range(8):
        actions.send_keys(Keys.SPACE).perform()
        time.sleep(0.3)
    time.sleep(1)

def get_links(driver: WebDriver):
    elems = driver.find_elements_by_xpath("//*[@href]")
    elems = set(elems)
    for i, elem in enumerate(elems):
        link = elem.get_attribute('href')
        # ta.tokopedia.com links are ads
        if "?whid=0" in link:  # Format for valid non-ad product
            parse_page(link)
            time.sleep(0.1)  # To not get blacklisted

def get_merchant(title: str) -> str:
    return title.split("tokopedia.com/")[1].split('/')[0]

def parse_page(link: str):
    headers = {
        'User-Agent': UA 
    }
    res = requests.get(link, timeout=15, headers=headers)

    parser = BeautifulSoup(res.text, 'html.parser')
    # Get title
    title = parser.find("h1", class_="css-t9du53").get_text()
    # Get description
    desc = parser.find("div", attrs={"data-testid": "lblPDPDescriptionProduk"}).get_text(strip=True, separator=" ")
    # Get Image link
    image_link = parser.find('div', class_="css-1y5a13").find("img")["src"]
    # Get price
    price = parser.find("div", attrs={"data-testid": "lblPDPDetailProductPrice"}).get_text()
    # Rating
    rating = parser.find("meta", attrs={"itemprop": "ratingValue"})["content"]
    # Merchant
    merchant = get_merchant(link)
    # Get how much sold
    sold = int(re.findall("itemSoldPaymentVerified\":\"(\d+)", res.text)[0])
    print("Title: {}, Price: {}, Merchant: {}, Sold: {}".format(title, price, merchant, sold))
    PRODUCTS.append(({
            "ProductName":title,
            "ProductDesc":"{}".format(desc),  # Escape comma literal
            "ImageLink":image_link,
            "ProductPrice":price,
            "ProductRating":rating,
            "ProductMerchant":merchant
        }, sold, link)
    )

def main():
    opt = Options()
    opt.add_argument("--headless")
    opt.add_argument("--safe-mode")

    profile = webdriver.FirefoxProfile()
    profile.set_preference('general.useragent.override', UA)

    driver = webdriver.Firefox(
        executable_path = Path.cwd().joinpath('src', 'drivers', 'geckodriver').as_posix(),
        log_path = "/tmp/selenium.logs",
        options = opt,
        service_log_path = "/tmp/slogs.logs",
        firefox_profile=profile
    )
    for page in range(1, 6):
        url = ROOT_URL.format(page)
        print("Getting page {}".format(url))
        driver.get(url)
        load_content(driver)
        get_links(driver)

    driver.quit()

    PRODUCTS.sort(key=lambda x: x[1], reverse=True)  # Sort by items sold from top to bottom

    with open('results.csv', 'w', newline='') as fh:
        field_names = ["ProductName", "ProductDesc", "ImageLink", "ProductPrice", "ProductRating", "ProductMerchant"]
        writer = csv.DictWriter(fh, fieldnames=field_names)
        writer.writeheader()
        for prod in PRODUCTS[:101]:  # Get top 100
            # print(prod[0]['ProductName'], prod[1], prod[2])  # Debugging
            writer.writerow(prod[0])

if __name__ == '__main__':
    main()