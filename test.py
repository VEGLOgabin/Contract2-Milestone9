import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError
import time
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError



with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.crestviewcollection.com/products/accessories/candle-holders-hurricanes/adair-candleholder-cvczhn037l")
    time.sleep(8)
    page.wait_for_selector("img.carousel-currentImage-UIT.image-loaded-QS8", state="visible", timeout=10000)
    html_content = page.content()
    soup = BeautifulSoup(html_content, 'lxml')
    with open("product.html", "w", encoding="utf-8") as file:
        file.write(soup.prettify())
        
        
        
        
# /bin/python3.13 /home/admin1/Musique/UPWORK/Contract2-Milestone9/crestview_crawler.py
