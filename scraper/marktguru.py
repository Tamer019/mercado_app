import requests

MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

def suche_angebote(suchbegriff, plz="72555"):
    response = requests.get(MARKTGURU_URL, params={
        "as": "web",
        "limit": 50,
        "offset": 0,
        "q": suchbegriff,
        "zipCode": plz
    }, headers=HEADERS)

    return response.json().get("results", [])