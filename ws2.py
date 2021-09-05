'''# Title change
# bulk discount vs single px (or capture Save) + mispricing
# +Descrption and more attributes from product page, detection on specific things
# Twitter bot publishing what's new or whatever
# Ignore mixed cases. Do I ever care? Maybe just filter them from diff?
# ws-stats: avg/median px per category, num wines per cat + quintile etc
#
# use arsenic async driver?
'''

import time
from datetime import datetime

import threading
import concurrent.futures
import asyncio

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
bsParser = 'html.parser'
domain = ''.join(reversed(["iety","soc","e","win","the"]))
headers = ["Code", "Name","Type","Alcohol","Px","Px Unit","Bulk Px","Bulk Unit","URL"]
products = ["Red%20Wine","White%20Wine","Champagne","Sparkling%20Wine","Sherry","Rose%20Wine","Port","Whisky","Brandy","Madeira","Other%20Spirits","Other%20Fortified","Aperitifs","Liqueurs","Mixed%20Cases"]
urlmask = 'https://www.'+domain+'.com/searchProducts.aspx?q=&hPP=15&idx=products&p={PNUM}&dFR%5Btype%5D%5B0%5D={PRODUCT}&is_v=1'
phantomPath = '../../phantomjs-2.1.1-macosx/bin/phantomjs'  # NOTE: Can/should replace phantomJS with headless Chrome/FF


#
productCatalogue = []
productCatalogueLock = threading.Lock()

# Returns a BeautifulSoup object for the given URL
def get_page(url):
    #print(f"Fetching {url}")
    driver = webdriver.PhantomJS(phantomPath) 
    driver.get(url) 
    aisHits = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ais-hits')))
    pageSource = driver.page_source
    bs = BeautifulSoup(pageSource, bsParser)  
    driver.close() 
    return bs 

# Returns a line representing a .csv row for the given BeautifulSoup object
def parse_page(bs):

    lines = []

    # Each search result is enclosed in <article> tag
    itemList = bs.findAll('article', {'class':'hit'})
    for item in itemList:
        
        # todo revise and capture stock status?
        if item.find('div', {'class':'out-stock'}):
            continue

        pid = item.get("data-pid")
        pname = item.find('div', {'class':'product-name'})
        #pdesc = item.find('p', {'class':'product-description'}).getText()
        
        priceTag = item.find('div', {'class':'product-price-pnl'}) 
        px = priceTag.find('div', {'class':'product-price-price'}).getText().partition(" a ") 
        pxAmt = px[0].strip()
        pxUnit = px[2].strip() if "save" not in px[2].lower() else px[2].lower().partition("save")[0]

        bulkPxTag = priceTag.find('div', {'class':'product-price-bulkprice'})
    
        if bulkPxTag is not None:
            bulkPx = bulkPxTag.getText().partition(" a ")
            bulkPxAmt = bulkPx[0].strip()
            bulkPxUnit = bulkPx[2].strip() if "Save " not in bulkPx[2] else bulkPx[2].partition("Save")[0]

        style = alc = ""

        atts = item.find('div', {'class':'product-attributes'}).ul.children 
        for att in atts:
            if "Style" in att.getText():
                style = att.span.getText()
            if "Alcohol" in att.getText():
                alc = att.span.getText()
        
        cleanName = pname.a.getText().replace('"', '')
        line = [pid, f'"{cleanName}"' , style, alc, 
            pxAmt, pxUnit, 
            bulkPxAmt if bulkPxTag is not None else '', 
            bulkPxUnit if bulkPxTag is not None else '',
            pname.a.get("href")]

        lines.append(','.join(line))
    
    return lines

# Wraps fetch and parse and synchronises on catalogue update
def fetch_and_update(product, page, pageCount):        
    print(f"Fetching page {page+1} of {pageCount}")
    bs = get_page(urlmask.format(PNUM=page,PRODUCT=product))
    lines = parse_page(bs) 
    with productCatalogueLock:
        productCatalogue.extend(lines)

async def non_blocking_loop(loop, executor, product, pageCount):

    done, pending = await asyncio.wait(
        fs=[loop.run_in_executor(executor, fetch_and_update, *[product, page, pageCount]) for page in range(1, pageCount)],
        return_when=asyncio.ALL_COMPLETED
    )

    results = [task.result() for task in done]



# Iterate over each product type
for product in products:

    print("Running for ", product)
    
    # Get the first page
    url = urlmask.format(PNUM="0",PRODUCT=product)  
    bs = get_page(url)

    # Figure out how many pages we have
    # span.id=stats-productCount > div class=ais-body ais-stats--body > span class=facet-count .text = (number of items)
    pages = bs.find('span', {'id':'stats-productCount'}).find('span',{'class','facet-count'}).getText().strip("()")
    pageCount = int(pages) // 15
    if int(pages) % 15 > 0:
        pageCount = pageCount + 1

    # Parse the first page and store results
    results = parse_page(bs)
    productCatalogue.extend(results)

    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    loop.run_until_complete(non_blocking_loop(loop, executor, product, pageCount))

    # Iterate over the remaining pages on separate threads. 
    #with ThreadPoolExecutor(max_workers=4) as executor:
    #    for p in range(1, pageCount):  # NB: the WS URL page number is 0 based
    #        executor.submit(fetch_and_update, product, p, pageCount)


# Write to file
csvfile = datetime.now().strftime("%Y%m%d.txt")
print("Downloading inventory to ", csvfile)

with open(csvfile, 'w') as f:
    print(','.join(headers), file=f)
    for line in productCatalogue:
        print(line, file=f)
    

print("done")

#