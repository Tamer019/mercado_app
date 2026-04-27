import requests
import json

PLZ = "72555"

url = "https://api.marktguru.de/api/v1/offers/search"

params = {
    "as": "web",
    "limit": 10,
    "offset": 0,
    "q": "walnuss",
    "zipCode": PLZ
}

headers = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

response = requests.get(url, params=params, headers=headers)
daten = response.json()
angebote = daten.get("results", [])

# Erstes Angebot komplett anzeigen
print("Alle verfügbaren Felder vom ersten Angebot:\n")
print(json.dumps(angebote[0], indent=2, ensure_ascii=False))