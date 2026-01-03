import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3
from urllib.parse import urljoin, urlparse
from collections import deque
# settings

BASEDOMAIN = "elclon.com.uy"
STARTURL = "https://www.elclon.com.uy/"
DB_PATH = "elclon.db"

VISITED = set() # to know which pages we already visited
TOVISIT = deque([STARTURL]) # to know which pages we still need to visit, we add deque
# to make the process faster. when i added pop it has no reason to exist when we are collecting products

# helpers

def isproductpage(soup):
    return soup.find("div", id="fichaProducto") is not None
# detect if the current page is the product page
def cleanprice(text):
    try:
        # remove points, currency symbols and spaces
        text = text.replace("$", "").replace(".", "").strip()
        return int(text)
    except ValueError:
        return 0

def isvalidurl(url):
    #filter URLs to ensure that:
    # belong to the elclon.com.uy domain
    # are not images, js, css, or social networks
    parsed = urlparse(url)

    if parsed.netloc and BASEDOMAIN not in parsed.netloc:
        # to follow only elclon domain links quiting subdomains like social networks, etc
        return False

    excluded_extensions = ['.jpg', '.png', '.jpeg', '.pdf', '.css', '.js']
    # avoid static files or system links
    if any(url.endswith(ext) for ext in excluded_extensions):
        return False

    return True

# product ddata extraction

def extractproductdata(soup, url):
    fichaprod = soup.find("div", id="fichaProducto")
    if not fichaprod:
        return None
    # extract product data if we already know it is a product
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
        "images": "|".join(images)# join here to make it easier to save in the database
    }

# database

def saveproductandprice(product):
    # save product if it is not already in the database, and if exists save the price log
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # first of all check if the product already exists
    cur.execute(
        "SELECT id FROM products WHERE url = ?",
        (product["url"],)
    )
    row = cur.fetchone()

    # if not exists we create it
    if row is None:
        cur.execute(
            """
            INSERT INTO products (url, name, description, images)
            VALUES (?, ?, ?, ?)
            """,
            (
                product["url"],
                product["name"],
                product["description"],
                product["images"]
            )
        )
        product_id = cur.lastrowid
    else:
        product_id = row[0]

    # finally insert the price
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        """
        INSERT INTO price_log (product_id, price, createdin)
        VALUES (?, ?, ?)
        """,
        (
            product_id,
            product["price"],
            scraped_at
        )
    )

    conn.commit()
    conn.close()

# crawler

def runcrawler():
    print(f"starting crawler on {STARTURL}")

    while TOVISIT:
        current_url = TOVISIT.popleft() 

        if current_url in VISITED:
            continue

        print(f"processing: {current_url} | pending: {len(TOVISIT)}")

        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code != 200:
                VISITED.add(current_url)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # 1 individual product page
            if isproductpage(soup):
                product = extractproductdata(soup, current_url)
                if product:
                    saveproductandprice(product)
                    print(f"[+] saved: {product['name']}")

            # 2 discover new links
            for link in soup.find_all("a", href=True): # finds '<a>' tags that have an 'href' attribute to discover new urlz
                raw_url = link["href"]
                full_url = urljoin(current_url, raw_url)

                if (
                    full_url not in VISITED
                    and full_url not in TOVISIT
                    and isvalidurl(full_url)
                ):
                    TOVISIT.append(full_url)

            VISITED.add(current_url)

        except Exception as e:
            print(f"error on {current_url}: {e}")
            VISITED.add(current_url)
