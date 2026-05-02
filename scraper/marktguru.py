import requests

MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
HEADERS = {
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE="
}

SYNC_KATEGORIEN = [
    "obst", "gemüse", "fleisch", "wurst", "fisch",
    "milch", "käse", "joghurt", "eier", "butter",
    "brot", "getränke", "saft", "snacks", "tiefkühl",
    "öl", "reis", "nudeln", "konserven", "süßigkeiten",
]

def hole_alle_angebote(plz="72555"):
    alle = []
    gesehen = set()

    for kategorie in SYNC_KATEGORIEN:
        offset = 0
        while True:
            response = requests.get(MARKTGURU_URL, params={
                "as": "web",
                "limit": 50,
                "offset": offset,
                "q": kategorie,
                "zipCode": plz
            }, headers=HEADERS)
            ergebnisse = response.json().get("results") or []

            for angebot in ergebnisse:
                uid = (
                    angebot.get("product", {}).get("name", ""),
                    angebot.get("advertisers", [{}])[0].get("name", ""),
                    angebot.get("validityDates", [{}])[0].get("from", ""),
                )
                if uid not in gesehen:
                    gesehen.add(uid)
                    alle.append(angebot)

            if len(ergebnisse) < 50:
                break
            offset += 50

    return alle
