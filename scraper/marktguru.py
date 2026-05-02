import requests

MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

def hole_alle_angebote(plz="72555"):
    alle = []
    offset = 0
    limit = 50
    while True:
        response = requests.get(MARKTGURU_URL, params={
            "as": "web",
            "limit": limit,
            "offset": offset,
            "q": "",
            "zipCode": plz
        }, headers=HEADERS)
        ergebnisse = response.json().get("results", [])
        alle.extend(ergebnisse)
        if len(ergebnisse) < limit:
            break
        offset += limit
    return alle