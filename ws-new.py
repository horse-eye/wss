from datetime import datetime
from util import timed, pf

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Title change
# Country, region?
# bulk discount vs single px (or capture Save) + mispricing
# +Descrption and more attributes from product page, detection on specific things
# Twitter bot publishing what's new or whatever
# Ignore mixed cases. Do I ever care? Maybe just filter them from diff?
# ws-stats: avg/median px per category, num wines per cat + quintile etc

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
    csvfile = datetime.now().strftime("%Y%m%d.txt")
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
            root = bs.find('div', {'class','product-listing--isList'})

            # Iterate over the pages
            for p in range(1, pageCount):

                print(f"Parsing page {p} of {pageCount}")

                # Each search result is enclosed in div.product-tile__container
                itemList = root.findAll('div', {'class':'product-tile__container'})
                
                print( len(itemList))
                #quit()

                for item in itemList:
                    
                    # todo: revisit
                    #if item.find('div', {'class':'out-stock'}):
                    #    continue

                    #
                    pdescTag = item.find('div',{'class':'product-tile__description'})

                    pidTag = pdescTag.find('div', {'class':'product-tile__price', 'class':'bottomLine'})  
                    pid = pidTag.div.get("data-yotpo-product-id")

                    porigin = pdescTag.find('span', {'class':'product-tile__origin'}).getText().strip()

                    purlTag = pdescTag.find('a', {'class':'product-tile__link'})
                    purl = purlTag.get("href")
                    pname = purlTag.h2.getText().strip()
                    
                    priceTags = item.findAll('div', {'class':'product-tile__price','class':'product-tile__price--per-bottle'}) 
                    px = priceTag.find('div', {'class':'product-price-price'}).getText().partition(" a ") 
                    pxAmt = px[0].strip()
                    pxUnit = px[2].strip() if "save" not in px[2].lower() else px[2].lower().partition("save")[0]

                    bulkPxTag = priceTag.find('div', {'class':'product-price-bulkprice'})
                
                    if bulkPxTag is not None:
                        bulkPx = bulkPxTag.getText().partition(" a ")
                        bulkPxAmt = bulkPx[0].strip()
                        bulkPxUnit = bulkPx[2].strip() if "Save " not in bulkPx[2] else bulkPx[2].partition("Save")[0]

                    print(purl, pname, pid, porigin)
                    quit()

                    style = alc = ""

                    atts = item.find('div', {'class':'product-attributes'}).ul.children 
                    for att in atts:
                        if "Style" in att.getText():
                            style = att.span.getText()
                        if "Alcohol" in att.getText():
                            alc = att.span.getText()
                    
                    cleanName = pname.a.getText().replace('"', '')

                    print(pid, f'"{cleanName}"' , style, alc, 
                        pxAmt, pxUnit, 
                        bulkPxAmt if bulkPxTag is not None else '', 
                        bulkPxUnit if bulkPxTag is not None else '',
                        purl, 
                        sep = ',',
                        file=f)

                # Fetch the next page
                url = urlmask.format(PNUM=p,PRODUCT=product)  
                driver.get(url) 
                aisHits = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ais-hits')))

                pageSource = driver.page_source
                bs = BeautifulSoup(pageSource, bsParser)    

    print("done")

    driver.close()

#

download_inventory()