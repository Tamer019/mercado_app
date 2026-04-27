import requests
from datetime import datetime, timedelta

PLZ = "72555"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

response = requests.get(
    "https://api.marktguru.de/api/v1/offers/search",
    params={"as": "web", "limit": 50, "offset": 0, "q": "mango", "zipCode": PLZ},
    headers=HEADERS
)

angebote = response.json().get("results", [])

print(f"{len(angebote)} Angebote gefunden\n")
for a in angebote:
    dates = a.get("validityDates", [{}])
    von = dates[0].get("from", "")[:10] if dates else ""
    bis = dates[0].get("to", "")[:10] if dates else ""
    print(f"{a['advertisers'][0]['name']:15} | {von} → {bis} | {a.get('price')}€")