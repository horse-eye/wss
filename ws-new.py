from datetime import datetime
from util import timed, pf

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# TODO
# Style (red/white etc - missing. get from individual page? or process per product?)
# Report discount/misprice at end of scrape? old vs new px in html
# Any additional attributes from product page?
# Twitter bot publishing what's new or whatever
# ws-analytics: avg/median px per category, num wines per cat + quintile, px trends over time

# Constants
bsParser = 'html.parser'
domain = ''.join(reversed(["iety","soc","e","win","the"]))
headers = ["Code", "Name","Type","Alcohol","Px","Px Unit","Bulk Px","Bulk Unit","URL","Origin"]
#products = ["Red%20Wine","White%20Wine","Champagne","Sparkling%20Wine","Sherry","Rose%20Wine","Port","Whisky","Brandy","Madeira","Other%20Spirits","Other%20Fortified","Aperitifs","Liqueurs","Mixed%20Cases"]
#urlmask = 'https://www.'+domain+'.com/searchProducts.aspx?q=&hPP=15&idx=products&p={PNUM}&dFR%5Btype%5D%5B0%5D={PRODUCT}&is_v=1'
phantomPath = '../../phantomjs-2.1.1-macosx/bin/phantomjs'  # NOTE: Can/should replace phantomJS with headless Chrome/FF
driver = webdriver.PhantomJS(phantomPath) 


# All except mixed cases, beer, non-drinks
# https://www.thewinesociety.com/search-results?page=1&producttype=17045,17047,17059,17061,17063,17047,17071,17077,17077,17079,17075,17062,17064,17060,17055,17054
products = ['17045,17047,17059,17061,17063,17047,17071,17077,17077,17079,17075,17062,17064,17060,17055,17054']
urlmask = 'https://www.thewinesociety.com/search-results?page={PNUM}&producttype={PRODUCT}'
productsPerPage = 60

@timed
def download_inventory():

    # Write to file
    csvfile = datetime.now().strftime("%Y%m%d.csv")
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

                    pf(item, f'debug\{pid}.html')

                    #
                    pdescTag = item.find('div',{'class':'product-tile__description'})

                    pidTag = pdescTag.find('div', {'class':'product-tile__price', 'class':'bottomLine'})  
                    pid = pidTag.div.get("data-yotpo-product-id")

                    poriginTag = pdescTag.find('span', {'class':'product-tile__origin'})
                    porigin = poriginTag.getText().strip() if poriginTag is not None else ''

                    purlTag = pdescTag.find('a', {'class':'product-tile__link'})
                    purl = purlTag.get("href")
                    pname = purlTag.h2.getText().strip()
                    
                    priceTags = item.findAll('div', {'class':'product-tile__price--per-bottle'}) 

                    # Out of stock , tood: make more explicit?
                    if len(priceTags) == 0:
                        continue

                    # TODO: fix old vs new px/bulk px

                    btlTag = priceTags[0]
                    btlPx = btlTag.span.span.next_sibling.replace(',','').strip('£')
                    btlUnit = btlTag.span.next_sibling.strip()

                    bulkUnit = bulkPx = ''
                    if(len(priceTags) > 1):
                        bulkTag = priceTags[1]
                        bulkPx = bulkTag.span.span.next_sibling.replace(',','').strip('£')
                        bulkUnit = bulkTag.span.next_sibling.strip()   

                        if bulkUnit is None or bulkUnit == '':
                            pf(item, f'debug\bulkUnit-{pid}.html')

                    if(len(priceTags) > 2):
                        pf(item, f'debug\px-{pid}.html')
                        print("WARNING - expected <= 2 prices, found ", len(priceTags) )

                    style = alc = ""
                    '''
                    atts = item.find('div', {'class':'product-attributes'}).ul.children 
                    for att in atts:
                        if "Style" in att.getText():
                            style = att.span.getText()
                        if "Alcohol" in att.getText():
                            alc = att.span.getText()
                    '''

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

#

download_inventory()