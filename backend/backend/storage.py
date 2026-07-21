import json
from pathlib import Path
from datetime import datetime

# Anchored to this file's location, not the process's working directory --
# so it doesn't matter whether you launch uvicorn from the project root or
# from inside backend/, snapshots always land in the same place.
DATA_DIR = Path(__file__).resolve().parent / "data"

# Every race gets its own subfolder under data/races/<STATE>/<cycle>/<race_key>,
# keyed off "state" and "cycle" in that race's registry.py entry -- e.g.
#
#   "az_governor_republican_primary_2026": {
#       "state": "az",
#       "cycle": "2026-primaries",
#       ...
#   }
#
# produces: data/races/AZ/2026-primaries/az_governor_republican_primary_2026/
#
# Races missing "state" or "cycle" still work (fall back to "UNKNOWN" /
# "uncategorized" instead of crashing) -- but won't land in the folder
# structure you're expecting until you add those fields.

def _race_dir(race_key):

    from backend.registry import RACES  # imported here, not at module load, to avoid any import-order issues

    config = RACES.get(race_key, {})
    state = (config.get("state") or "unknown").upper()
    cycle = config.get("cycle") or "uncategorized"

    path = DATA_DIR / "races" / state / cycle / race_key
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
