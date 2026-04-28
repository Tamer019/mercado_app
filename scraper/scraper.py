import requests
import sys
import os

sys.path.append(os.path.dirname(__file__))
from db_save import save_angebote

MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

def scrape(suchbegriff, plz="72555"):
    print(f"🔍 Suche nach '{suchbegriff}' für PLZ {plz}...")

    response = requests.get(MARKTGURU_URL, params={
        "as": "web",
        "limit": 50,
        "offset": 0,
        "q": suchbegriff,
        "zipCode": plz
    }, headers=HEADERS)

    angebote = response.json().get("results", [])
    print(f"📦 {len(angebote)} Angebote gefunden")

    save_angebote(angebote, plz)

if __name__ == "__main__":
    scrape("mango")
    scrape("banane")
    scrape("milch")
    scrape("chips")