
# from twisted.internet import asyncioreactor
# asyncioreactor.install()

import sys
from twisted.internet import asyncioreactor

asyncioreactor.install()
import os
import json
import asyncio
from scrapy import Spider
from scrapy.http import Request
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import time
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy import signals
from pydispatch import dispatcher
from bs4 import BeautifulSoup
import re
from playwright.async_api import expect


from playwright.sync_api import sync_playwright, TimeoutError
import time
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

           
            
def extract_collections(soup):
    """Extract collections from the parsed HTML soup."""
    collections_section = soup.find("div", class_="category-contentWrapper-IOu")

    if collections_section:
        collections_list = collections_section.find("ul")
        if collections_list:
            collections = [
                [
                    "https://www.crestviewcollection.com" + item.get('href'),
                    item.text.strip()
                ]
                for item in collections_list.find_all("a")
            ]
            return collections
    return []

def scrape_category_data(page, category_name, category_url):
    """Navigate to a category page and extract collection data."""
    page.goto(category_url)
    try:
        page.wait_for_selector("div.category-contentWrapper-IOu", state="visible", timeout=10000)
        time.sleep(10)
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'lxml')
        collections = extract_collections(soup)
        
        return [
            {
                "Category_name": category_name,
                "Collection_name": collection[1],
                "Collection_link": collection[0]
            }
            for collection in collections
        ]
    except TimeoutError:
        print(f"TimeoutError: Failed to load collections for {category_name} at {category_url}")
        return []

def menu_scraper():
    categories = [
        ["Accessories", "https://www.crestviewcollection.com/products/accessories"],
        ["Furniture", "https://www.crestviewcollection.com/products/furniture"],
        ["Lighting", "https://www.crestviewcollection.com/products/lighting"],
        ["Wall Decor", "https://www.crestviewcollection.com/products/wall-decor"]
    ]
    all_collections = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for category_name, category_url in categories:
            collections = scrape_category_data(page, category_name, category_url)
            all_collections.extend(collections)

        with open('utilities/category-collection.json', 'w', encoding='utf-8') as f:
            json.dump(all_collections, f, ensure_ascii=False, indent=4)

        print("Data saved to 'utilities/category-collection.json'")
        browser.close()


def scrape_all_collection_products(page, category_name, collection_name, collection_link):
    """Navigate to a collection page and extract collection products."""
    print(f"Scraping products for collection: {collection_name}")
    page.goto(collection_link)
    time.sleep(8)
    try:
        page.wait_for_selector("article.category-root-ZTk", state="visible", timeout=10000)
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'lxml')
        page_number = 1
        products = []

        current_page_products = soup.find_all("a", class_="item-images--uD")
        current_page_products = [item.get("href") for item in current_page_products]
        products.extend(current_page_products)

        page_buttons = soup.find_all('button', class_="tile-root-NN0")
        if page_buttons:
            total_pages = int(page_buttons[-2].text.strip())
        else:
            total_pages = 1

        while page_number < total_pages:
            page_number += 1
            page.goto(f"{collection_link}?page={page_number}")
            time.sleep(8)
            page.wait_for_selector("article.category-root-ZTk", state="visible", timeout=10000)
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'lxml')
            current_page_products = soup.find_all("a", class_="item-images--uD")
            current_page_products = [item.get("href") for item in current_page_products]
            products.extend(current_page_products)
                    # Determine the total number of pages
            page_buttons = soup.find_all('button', class_="tile-root-NN0")
            if page_buttons:
                total_pages = int(page_buttons[-2].text.strip())

        return [
            {
                "category_name": category_name,
                "collection_name": collection_name,
                "product_link": "https://www.crestviewcollection.com" + product
            }
            for product in products
        ]

    except PlaywrightTimeoutError:
        print(f"TimeoutError: Failed to load products for {collection_name} at {collection_link}")
        return []


def collections_scraper():
    """Scrape products for all collections listed in the category-collection.json file."""
    all_collections_data = []
    output_dir = 'utilities'
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            with open(os.path.join(output_dir, 'category-collection.json'), 'r', encoding='utf-8') as file:
                collections_links_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading JSON file: {e}")
            return
        
        for collection in collections_links_data:
            category_name = collection.get("Category_name")
            collection_name = collection.get("Collection_name")
            collection_link = collection.get("Collection_link")


            if category_name and collection_name and collection_link:
                collections_data = scrape_all_collection_products(page, category_name, collection_name, collection_link)
                all_collections_data.extend(collections_data)

        # Save all collected data to a JSON file
        output_file = os.path.join(output_dir, 'products-links.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_collections_data, f, ensure_ascii=False, indent=4)

        print(f"Data saved to '{output_file}'")
        browser.close()

    



class ProductSpider(scrapy.Spider):
    name = "product_spider"
    
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 100000,
        },
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
        'CONCURRENT_REQUESTS': 1,
        'LOG_LEVEL': 'INFO',
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
        'HTTPERROR_ALLOW_ALL': True,
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
                        'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                        'Chrome/115.0.0.0 Safari/537.36',
            'Accept-Language': 'en',
        },
    }
    
    def start_requests(self):
        """Initial request handler."""
        self.logger.info("Spider started. Preparing to scrape products.")
        os.makedirs('output', exist_ok=True)
        self.scraped_data = []
        scraped_links = set()
        self.output_file = open('output/products-data.json', 'a', encoding='utf-8')
        if os.path.exists('output/products-data.json'):
            self.logger.info("Loading existing scraped data.")
            with open('output/products-data.json', 'r', encoding='utf-8') as f:
                    try:
                        self.scraped_data = json.load(f)
                        scraped_links = {(item['Product Link'], item["Collection"], item['Category']) for item in self.scraped_data}
                    except json.JSONDecodeError:
                        self.logger.warning("Encountered JSONDecodeError while loading existing data. Skipping line.")
                        pass 
        scraped_product_links = {item['Product Link'] for item in self.scraped_data}
        try:
            with open('utilities/products-links.json', 'r', encoding='utf-8') as file:
                products = json.load(file)
            self.logger.info(f"Loaded {len(products)} products to scrape.")
        except Exception as e:
            self.logger.error(f"Failed to load products-links.json: {e}")
            return
        for product in products:
            product_link = product['product_link']
            category_name = product['category_name']
            collection_name = product['collection_name']
            product_key = (product_link, collection_name, category_name)
            if product_key not in scraped_links:
                if product_link in scraped_product_links:
                    scraped_product = next((item for item in self.scraped_data if item['Product Link'] == product_link), None)
                    if scraped_product:
                        if collection_name not in scraped_product['Collection'] or category_name not in scraped_product['Category']:
                            new_product_data = scraped_product.copy()
                            new_product_data['Collection'] = collection_name
                            new_product_data['Category'] = category_name
                            self.scraped_data.append(new_product_data)
                            with open('output/products-data.json', 'w', encoding='utf-8') as f:
                                json.dump(self.scraped_data, f, ensure_ascii=False, indent=4)
                            self.logger.info(f"Updated product with new collection or category: {product_link}")
                    else:
                        self.logger.warning(f"Product link found in scraped_product_links but not in scraped_data: {product_link}")
                else:
                    
                    yield scrapy.Request(
                        url=product_link,
                        meta={
                            'playwright': True,
                            'playwright_include_page': True,
                            'product': product
                        },
                        callback=self.parse,
                        errback=self.handle_error
                    )
            else:
                self.logger.info(f"Skipping already scraped product: {product_link} under category: {category_name}")
    
    async def parse(self, response):
        """Parse the product page using BeautifulSoup and extract details."""
        self.logger.info(f"Parsing product: {response.url}")
        try:
            product = response.meta['product']
            page = response.meta['playwright_page'] 
            time.sleep(7)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            category_name = product['category_name']
            collection_name = product['collection_name']
            product_link = product['product_link']
            
            product_name = soup.find("h2", class_ = "productFullDetail-productName-Qe1 mb-[1.5rem] leading-none lg_leading-0")
            if product_name:
                product_name = product_name.get_text()

            sku = soup.find('p', class_ = "productFullDetail-productSku-vjY productFullDetail-productSku-vjY")
            if sku:
                sku = sku.text.strip().replace("SKU", "").replace(' ', "")


            product_images = []
            imgs = soup.find("div", class_="carousel-thumbnailList-Zyp")

            if imgs:
                img_tags = imgs.find_all('img')
                if img_tags:
                    for img in img_tags:
                        src = img.get("src")
                        if src:
                            product_images.append("https://www.crestviewcollection.com" + src)
                else:
                    product_images = f"https://www.crestviewcollection.com/media/catalog/product/C/V/{sku}.jpg"
            else:
                product_images = f"https://www.crestviewcollection.com/media/catalog/product/C/V/{sku}.jpg"




            description = soup.find("div", class_ = "richContent-root-Ddk")

            if description:
                description = description.text.strip()

            detail_section = soup.find('section', class_='productFullDetail-additionalInfo-Euh')
            product_info = {}

            if detail_section:
                spans = detail_section.find_all('span')
                for i in range(0, len(spans), 2):
                    key = spans[i].text.strip()
                    value = spans[i + 1].text.strip()
                    product_info[key] = value

            dimension_list = soup.find('div', class_='customAttributes-root-MXb')
            if dimension_list:
                dimension_items = dimension_list.find_all('li')
                if dimension_items:
                    for item in dimension_items:
                        key = item.find('div', class_='price-label-fXs').get_text(strip=True)
                        value = item.find('div').get_text(strip=True)
                        product_info[key] = value

            custom_attributes = soup.find_all('div', class_='customAttributes-root-MXb')
            if len(custom_attributes) > 1:
                design_list = custom_attributes[1]
                if design_list:
                    design_items = design_list.find_all('li')
                    for item in design_items:
                        key = item.find('div', class_=['text-label-daH', 'select-label-F5C', 'multiselect-label-eUb']).get_text(strip=True)
                        value = item.find('div', class_=['text-content-Mcy', 'select-content-fTr', 'multiselect-content-Dtn']).get_text(strip=True)
                        product_info[key] = value
            else:
                self.logger.info("Warning: Design list section not found on the page")



            if sku:

                new_product_data =  {
                    'Category': category_name,
                    'Collection': collection_name,
                    'Product Link': product_link,
                    'Product Title': product_name,
                    'SKU': sku,
                    "Description": description,
                    'Product Details ': product_info,
                    "Product Images": product_images
                }
                
                self.scraped_data.append(new_product_data)
                
                with open('output/products-data.json', 'w', encoding='utf-8') as f:
                    json.dump(self.scraped_data, f, ensure_ascii=False, indent=4)
                self.logger.info(f"Successfully scraped product: {product_link}")
            
        except Exception as e:
            self.logger.error(f"Error parsing {response.url}: {e}")
        finally:
            await page.close()
    
    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(repr(failure))
    
    def closed(self, reason):
        self.output_file.close()
        self.logger.info("Spider closed: %s", reason)
    


           
    
    
    
#   -----------------------------------------------------------Run------------------------------------------------------------------------

def run_spiders():

    # output_dir = 'utilities'
    # os.makedirs(output_dir, exist_ok=True)

    # menu_scraper()
    # collections_scraper()

    process = CrawlerProcess()

    def run_product_spider():
        process.crawl(ProductSpider)

    process.crawl(ProductSpider)
    process.start()


run_spiders()
