import json
from pathlib import Path
from datetime import datetime

SNAPSHOT = Path("data/latest.json")


def save_snapshot(snapshot):
    with open(SNAPSHOT, 'w') as f:
        json.dump(snapshot, f, indent=4)

def save_archive_snapshot(snapshot):
    Path("data/snapshots").mkdir(parents=True,exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = Path("data/snapshots") / f"{filename}.json"

    with open(filepath, 'w') as f:
        json.dump(snapshot,f,indent=4)

def load_snapshot():
    if SNAPSHOT.exists():
        with open(SNAPSHOT) as f:
            return json.load(f)
    else:
        return None



