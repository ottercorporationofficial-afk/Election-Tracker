import requests

BASE_URL = "https://civicapi.org/api/v2/race"


def get_race(race_id):
    url = f"{BASE_URL}/{race_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
