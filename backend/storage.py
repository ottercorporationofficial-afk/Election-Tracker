import json
from pathlib import Path
from datetime import datetime

# Anchored to this file's location, not the process's working directory --
# so it doesn't matter whether you launch uvicorn from the project root or
# from inside backend/, snapshots always land in the same place.
DATA_DIR = Path(__file__).resolve().parent / "data"

# Every race gets its own subfolder under data/races, keyed by race_key
# from registry.py, so tracking multiple races at once doesn't clobber a
# single shared latest.json.

def _race_dir(race_key):
    path = DATA_DIR / "races" / race_key
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_snapshot(race_key, snapshot):
    with open(_race_dir(race_key) / "latest.json", 'w') as f:
        json.dump(snapshot, f, indent=4)

def save_archive_snapshot(race_key, snapshot):
    archive_dir = _race_dir(race_key) / "snapshots"
    archive_dir.mkdir(parents=True, exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = archive_dir / f"{filename}.json"

    with open(filepath, 'w') as f:
        json.dump(snapshot, f, indent=4)

def load_snapshot(race_key):
    snapshot_path = _race_dir(race_key) / "latest.json"

    if snapshot_path.exists():
        with open(snapshot_path) as f:
            return json.load(f)
    else:
        return None

def save_comparison(race_key, comparison):
    changes_dir = _race_dir(race_key) / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = changes_dir / f"{filename}.json"
    with open(filepath, 'w') as f:
        json.dump(comparison, f, indent=4)


def load_latest_comparison(race_key):
    changes_dir = _race_dir(race_key) / "changes"

    files = sorted(
        changes_dir.glob("*.json"),
        reverse=True
    )

    if not files:
        return None

    with open(files[0], "r") as f:
        return json.load(f)

def load_comparisons(race_key):
    changes_dir = _race_dir(race_key) / "changes"

    comparisons = []

    for file in changes_dir.glob("*.json"):
        with open(file, "r") as f:
            comparisons.append(json.load(f))

    return comparisons
