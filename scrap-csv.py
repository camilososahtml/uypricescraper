import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import os


def scrapelclon(url):
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")
    idfichaprodu = soup.find("div", id="fichaProducto")
        # "fichaproducto" is the id in el clon for an individual product

    # individual product
    if idfichaprodu:
        nametag = idfichaprodu.find("h1", class_="tit")
        pricetag = idfichaprodu.find("span", class_="monto")

        if not nametag or not pricetag:
            return []

        return [{
            "name": nametag.get_text(strip=True),
            "price": clean_price(pricetag.get_text())
        }]

    # category page
    products = []

    productcards = soup.find_all("div", class_="info")

    for card in productcards:
        nametag2 = card.find("h2")
        pricetag2 = card.find("span", class_="monto")

        if not nametag2 or not pricetag2:
            continue

        products.append({
            "name": nametag2.get_text(strip=True),
            "price": clean_price(pricetag2.get_text())
        })

    return products


def clean_price(text):
    return int(text.replace(".", "").strip())


def save_csv(products, url, file="products.csv"):
    exists = os.path.exists(file)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "url", "name", "price"]
        )

        if not exists:
            writer.writeheader()

        for p in products:
            writer.writerow({
                "date": date,
                "url": url,
                "name": p["name"],
                "price": p["price"]
            })



url = "https://www.elclon.com.uy/bebe"
products = scrapelclon(url)
save_csv(products, url)
