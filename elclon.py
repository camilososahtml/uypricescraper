import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import os
import time
from urllib.parse import urljoin, urlparse

# settings
BASEDOMAIN = "elclon.com.uy"
STARTURL = "https://www.elclon.com.uy/"
CSVFILE = "products.csv"
VISITED = set()  #to remember what we already visited
TOVISIT = [STARTURL]  # queue url to visit

# help stuff

def isproductpage(soup):
    # detect if the current page is the product page
    return soup.find("div", id="fichaProducto") is not None

def cleanprice(text):
    try:
        # remove points, currency symbols and spaces
        text = text.replace("$", "").replace(".", "").strip()
        return int(text)
    except ValueError:
        return 0

def isvalidurl(url):
    
    #filter URLs to ensure that:
    #1 belong to the elclon.com.uy domain
    #2 are not images, js, css, or social networks

    parsed = urlparse(url)
    # to follow only elclon domain links quiting subdomains like social networks, etc
    if parsed.netloc and BASEDOMAIN not in parsed.netloc:
        return False
    
    # avoid static files or system links
    excluded_extensions = ['.jpg', '.png', '.jpeg', '.pdf', '.css', '.js']
    if any(url.endswith(ext) for ext in excluded_extensions):
        return False
        
    return True

# scraper central functions

def extractproductdata(soup, url):
    # extract product data if we already know it is a product
    fichaprod = soup.find("div", id="fichaProducto")
    if not fichaprod:
        return None

    nametag = fichaprod.find("h1", class_="tit")
    pricetag = fichaprod.find("span", class_="monto")

    if not nametag or not pricetag:
        return None

    desctag = fichaprod.find("div", class_="desc")
    description = desctag.get_text(strip=True) if desctag else ""

    images = []
    for img in fichaprod.find_all("img"):
        src = img.get("data-src-g") or img.get("src")
        if src:
            images.append(src)

    return {
        "url": url,
        "name": nametag.get_text(strip=True),
        "price": cleanprice(pricetag.get_text()),
        "description": description,
        "images": "|".join(images) # join here to make it easier to save in csv
    }

def savetocsv(product):
    # save a product individually (append mode)
    exists = os.path.exists(CSVFILE)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSVFILE, mode="a", newline="", encoding="utf-8") as f:
        fieldnames = ["date", "url", "name", "price", "description", "images"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "date": date,
            **product # product dictionary
        })

# CRAWLERS logic (new feature

def runcrawler():
    #principal function that does not receive inputs, it crawls the whole site
    #and saves the products it finds
    
    print(f"starting crawler on {STARTURL}")
    
    while TOVISIT:
        # take the first url from the queue
        current_url = TOVISIT.pop(0)
        
        # if we already visited it, go to the next
        if current_url in VISITED:
            continue
            
        print(f"processing: {current_url} | pending: {len(TOVISIT)}")
        
        try:
            response = requests.get(current_url, timeout=10) #timeout to wait for response and not take to long waiting
            if response.status_code != 200:
                VISITED.add(current_url)
                continue
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 1 check if it's a product page
            if isproductpage(soup):
                product = extractproductdata(soup, current_url)
                if product:
                    savetocsv(product)
                    print(f"   [+] product saved: {product['name']}")
            
            # 2 find all new links on this page and visit them
            # this rule follows the rule that open all links that appear
            for link in soup.find_all("a", href=True):
                raw_url = link['href']
                
                # make full url from relative links (/ofertas) to absolute urls (https://elclon...)
                full_url = urljoin(current_url, raw_url)
                
                # clean trash from code or querys
                full_url = full_url.split('#')[0] 

                if full_url not in VISITED and full_url not in TOVISIT and isvalidurl(full_url):
                    TOVISIT.append(full_url)
            
            # mark current as visited
            VISITED.add(current_url)
            
            # watch out small delays to not saturate the page
            time.sleep(0.1) 

        except Exception as mistake:
            print(f"Error  on {current_url}: {mistake}")  # exception handling
            VISITED.add(current_url)  # mark as visited