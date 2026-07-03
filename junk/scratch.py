import requests
import json

race_id = 84287

url = f"https://civicapi.org/api/v2/race/{race_id}"

response = requests.get(url)

data = response.json()

print(json.dumps(data, indent=4))