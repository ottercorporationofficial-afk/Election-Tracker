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

def save_comparison(comparison):
    Path("data/changes").mkdir(parents=True,exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = Path("data/changes") / f"{filename}.json"
    with open(filepath, 'w') as f:
        json.dump(comparison,f,indent=4)


def load_latest_comparison():
    changes_folder = Path("data/changes")

    files = sorted(
        changes_folder.glob("*.json"),
        reverse=True
    )

    if not files:
        return None

    with open(files[0], "r") as f:
        return json.load(f)

def load_comparisons():
    changes_folder = Path("data/changes")

    comparisons = []

    for file in changes_folder.glob("*.json"):
        with open(file, "r") as f:
            comparison = json.load(f)
            comparisons.append(comparison)



    return comparisons




