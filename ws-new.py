from os import listdir
from datetime import datetime

from util import timed, pf, plf
from ws_diff import diff_inventory

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# TODO
# Replace phantomJS with headless Chrome/FF
# Report discount/misprice at end of scrape? old vs new px in html
# Small number of missing styles - fill in from product page calls?
# Twitter bot publishing what's new or whatever
# ws-analytics: avg/median px per category, num wines per cat + quintile, px trends over time

# Constants
basedir = 'inventory/'
bsParser = 'html.parser'
domain = ''.join(reversed(["iety","soc","e","win","the"]))
headers = ["Code", "Name","Type","Alcohol","Px","Px Unit","Bulk Px","Bulk Unit","URL","Origin"]
phantomPath = '../../phantomjs-2.1.1-macosx/bin/phantomjs'  # NOTE: Can/should replace phantomJS with headless Chrome/FF
driver = webdriver.PhantomJS(phantomPath) 

# All except mixed cases, beer, non-drinks
# https://www.thewinesociety.com/search-results?page=1&producttype=17045,17047,17059,17061,17063,17047,17071,17077,17077,17079,17075,17062,17064,17060,17055,17054
products = ['17045,17047,17059,17061,17063,17047,17071,17077,17077,17079,17075,17062,17064,17060,17055,17054']
urlmask = 'https://www.thewinesociety.com/search-results?page={PNUM}&producttype={PRODUCT}'
productsPerPage = 60

# Some products have an old and a new price, e.g.
# <span class="product-pricing__price product-pricing__price--old"><span class="sr-only">Original price: </span>£8.95</span>
# <span class="product-pricing__price product-pricing__price--new"><span class="sr-only">Current price:</span>£8.00</span>
def getPriceNode(priceTag):
    prices = len(priceTag.findAll('span', {'class':'product-pricing__price'}))
    if prices > 1:
        _span = priceTag.find('span',{'class':'product-pricing__price--new'})
    else:
        _span = priceTag.span
    return _span

def mapStyle(text):

    if 'red-wine' in text:
        return 'Red Wine'
    if 'white-wine' in text:
        return 'White Wine'
    if 'sparkling' in text or 'champagne' in text:
        return 'Sparkling Wine'   
    if text == 'sweet-wines': 
        return 'Sweet Wine'  
    if text == 'rose' or 'rose-wine' in text: 
        return 'Rose Wine'
    if 'sherry' in text: 
        return 'Sherry'
    if text == 'other-spirits': 
        return 'Spirits'
    if text in ['port','spirits','brandy','whisky']:
        return text.capitalize()      
    return None          

# Attempt to determine the product type (red wine, white wine, etc) from image metadata
_imgtags = []
def getStyle(itemTag):

    imgTag = itemTag.find('img',{'class':'lazyload'}).get('data-srcset')
    segments = imgTag.split('/')
    style = segments[4]
    mapped = mapStyle(style)
    
    if mapped is not None:
        return mapped

    altTag = itemTag.find('div',{'class':'product-image__background'}).get('class')
    mapped = mapStyle(altTag[1])

    if mapped is None:    
        _imgtags.append( [imgTag, altTag[1] ] )
        pidTag = itemTag.find('div',{'class':'product-tile__description'}).find('div', {'class':'product-tile__price', 'class':'bottomLine'})  
        pid = pidTag.div.get("data-yotpo-product-id")
        pf(itemTag, f'debug/{pid}.html') # debug
    
    return mapped if mapped is not None else 'Unknown'

@timed
def download_inventory(dir):

    # Write to file
    csvfile = dir + datetime.now().strftime("%Y%m%d.csv")
    print("Downloading inventory to ", csvfile)

    with open(csvfile, 'w') as f:

        print(','.join(headers), file=f)

        # Iterate over each product type
        for product in products:

            print("Running for ", product)
            
            # Get the first page
            url = urlmask.format(PNUM="1",PRODUCT=product)  
            driver.get(url) 
            
            # Wait for product listing to load, then parse the page
            WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.CLASS_NAME, 'product-listing--isList')))
            pageSource = driver.page_source
            bs = BeautifulSoup(pageSource, bsParser)

            # Figure out how many pages we have
            # div class=result-count > h2 class=result-count-heading > .text = Showing 1 - 60 of X products
            hits = bs.find('div',{'class','result-count'}).find('h2', {'class':'result-count-heading'}).getText().replace("Showing 1 - 60 of ","").replace(" products","").strip()
            pageCount = int(hits) // productsPerPage
            if int(hits) % productsPerPage > 0:
                pageCount = pageCount + 1

            #print(hits, pageCount)

            # Iterate over the pages
            for p in range(1, pageCount+1):

                print(f"Parsing page {p} of {pageCount}")

                # Each search result is enclosed in div.product-tile__container
                root = bs.find('div', {'class','product-listing--isList'})
                itemList = root.findAll('div', {'class':'product-tile__container'})

                for item in itemList:
                    #
                    pdescTag = item.find('div',{'class':'product-tile__description'})

                    pidTag = pdescTag.find('div', {'class':'product-tile__price', 'class':'bottomLine'})  
                    pid = pidTag.div.get("data-yotpo-product-id")

                    #pf(item, f'debug/{pid}.html') # debug

                    poriginTag = pdescTag.find('span', {'class':'product-tile__origin'})
                    porigin = poriginTag.getText().strip() if poriginTag is not None else ''

                    purlTag = pdescTag.find('a', {'class':'product-tile__link'})
                    purl = purlTag.get("href")
                    pname = purlTag.h2.getText().strip()
                    
                    priceTags = item.findAll('div', {'class':'product-tile__price--per-bottle'}) 

                    # Out of stock , TODO: make more explicit? dump html and check if really
                    if len(priceTags) == 0:
                        continue

                    # Get bottle pricing
                    btlTag = priceTags[0]    
                    _span = getPriceNode(btlTag)
                    btlPx = _span.span.next_sibling.replace(',','').strip('£')
                    btlUnit = _span.next_sibling.strip()

                    #debug
                    if btlUnit is None or btlUnit == '':
                            pf(btlTag, f'debug/btlUnit-{pid}.html')

                    # Get bulk pricing
                    bulkUnit = bulkPx = ''
                    if(len(priceTags) > 1):
                        bulkTag = priceTags[1]
                        _span = getPriceNode(bulkTag)
                        bulkPx = _span.span.next_sibling.replace(',','').strip('£')
                        bulkUnit = _span.next_sibling.strip()   

                        # debug
                        if bulkUnit is None or bulkUnit == '':
                            pf(bulkTag, f'debug/bulkUnit-{pid}.html')

                    #debug
                    if(len(priceTags) > 2):
                        plf(priceTags, f'debug/multipx-{pid}.html')
                        print("WARNING - expected <= 2 prices, found ", len(priceTags) )

                    alc = ""
                    style = getStyle(item)

                    cleanName = pname.replace('"', '')

                    print(pid, f'"{cleanName}"' , style, alc, 
                        btlPx, btlUnit, 
                        bulkPx, 
                        bulkUnit,
                        purl,
                        porigin, 
                        sep = ',',
                        file=f)

                # Fetch the next page
                if p < pageCount:
                    url = urlmask.format(PNUM=p+1,PRODUCT=product)  
                    driver.get(url) 
                    WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.CLASS_NAME, 'product-listing--isList')))
                    pageSource = driver.page_source
                    bs = BeautifulSoup(pageSource, bsParser)    

    print("done")

    driver.close()

    plf(_imgtags, 'tags.csv')

    return csvfile

#

def get_last_inventory(dir):
    files = sorted([f for f in listdir(dir) if f.endswith('.csv')])
    latest = dir + max(files)
    return latest

# TODO: (bug) - rerunning would cause downloaded to be diffed with itself

previous = get_last_inventory(basedir)
current = download_inventory(basedir)

diff_inventory(previous, current)