import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Title change
# bulk discount vs single px (or capture Save) + mispricing
# +Descrption and more attributes from product page, detection on specific things
# Twitter bot publishing what's new or whatever
# Ignore mixed cases. Do I ever care? Maybe just filter them from diff?
# ws-stats: avg/median px per category, num wines per cat + quintile etc

# Constants
bsParser = 'html.parser'
domain = ''.join(reversed(["iety","soc","e","win","the"]))
headers = ["Code", "Name","Type","Alcohol","Px","Px Unit","Bulk Px","Bulk Unit","URL"]
products = ["Red%20Wine","White%20Wine","Champagne","Sparkling%20Wine","Sherry","Rose%20Wine","Port","Whisky","Brandy","Madeira","Other%20Spirits","Other%20Fortified","Aperitifs","Liqueurs","Mixed%20Cases"]
urlmask = 'https://www.'+domain+'.com/searchProducts.aspx?q=&hPP=15&idx=products&p={PNUM}&dFR%5Btype%5D%5B0%5D={PRODUCT}&is_v=1'
phantomPath = '../../phantomjs-2.1.1-macosx/bin/phantomjs'  # NOTE: Can/should replace phantomJS with headless Chrome/FF
driver = webdriver.PhantomJS(phantomPath) 

# Alternate parsers for BS
#bs = BeautifulSoup(html, 'html5lib')
#bs = BeautifulSoup(html, 'lxml')

# Write to file
csvfile = datetime.now().strftime("%Y%m%d.txt")
print("Downloading inventory to ", csvfile)

with open(csvfile, 'w') as f:

    print(','.join(headers), file=f)

    # Iterate over each product type
    for product in products:

        print("Running for ", product)
        
        # Get the first page
        url = urlmask.format(PNUM="0",PRODUCT=product)  
        driver.get(url) 
        
        #time.sleep(2) # todo: replace with Wait, p.168 Web scraping with python
        aisHits = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.CLASS_NAME, 'ais-hits')))

        pageSource = driver.page_source
        bs = BeautifulSoup(pageSource, bsParser)

        # Figure out how many pages we have
        # span.id=stats-productCount > div class=ais-body ais-stats--body > span class=facet-count .text = (number of items)
        pages = bs.find('span', {'id':'stats-productCount'}).find('span',{'class','facet-count'}).getText().strip("()")
        pageCount = int(pages) // 15
        if int(pages) % 15 > 0:
            pageCount = pageCount + 1

        # Iterate over the pages
        for p in range(0, pageCount):

            print("Getting page ", p)

            # Each search result is enclosed in <article> tag
            itemList = bs.findAll('article', {'class':'hit'})

            for item in itemList:
                
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

                print(pid, f'"{cleanName}"' , style, alc, 
                    pxAmt, pxUnit, 
                    bulkPxAmt if bulkPxTag is not None else '', 
                    bulkPxUnit if bulkPxTag is not None else '',
                    pname.a.get("href"), 
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