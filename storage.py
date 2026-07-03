import json


def save_snapshot(snapshot):
    with open('data/latest.json', 'w') as f:
        json.dump(snapshot, f, indent=4)
        f.close()
