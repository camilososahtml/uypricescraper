import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import os


# help stuff

def isproduct_page(soup):
    return soup.find("div", id="fichaProducto") is not None
# ficha producto is the id in el clon for an individual product page 

def cleanprice(text):
    return int(text.replace(".", "").strip())


# scrapers 

def scrapeproduct(url):
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    fichaprod = soup.find("div", id="fichaProducto")
    if not fichaprod:
        return None

    # nombre
    nametag = fichaprod.find("h1", class_="tit")
    # precio
    pricetag = fichaprod.find("span", class_="monto")

    if not nametag or not pricetag:
        return None

    # descripción
    desctag = fichaprod.find("div", class_="desc")
    description = desctag.get_text(strip=True) if desctag else ""

    # imágenes (prioriza data-src-g)
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
        "images": images
    }


def getprodfromcategory(url):
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    product_urls = []

    productcards = soup.find_all("div", class_="info")
    for card in productcards:
        link = card.find("a", class_="tit")
        if link and link.get("href"):
            product_urls.append(link["href"])

    return product_urls


# csv generator

def save_csv(products, file="products.csv"):
    exists = os.path.exists(file)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "url",
                "name",
                "price",
                "description",
                "images"
            ]
        )

        if not exists:
            writer.writeheader()

        for p in products:
            writer.writerow({
                "date": date,
                "url": p["url"],
                "name": p["name"],
                "price": p["price"],
                "description": p["description"],
                "images": "|".join(p["images"])
            })


# main url input and execution

url = "https://www.elclon.com.uy/alimentos/alimentos/bebidas-s-alcohol"

response = requests.get(url, timeout=15)
soup = BeautifulSoup(response.text, "html.parser")

products = []

if isproduct_page(soup):
    product = scrapeproduct(url)
    if product:
        products.append(product)
else:
    product_urls = getprodfromcategory(url)
    for purl in product_urls:
        product = scrapeproduct(purl)
        if product:
            products.append(product)

save_csv(products)