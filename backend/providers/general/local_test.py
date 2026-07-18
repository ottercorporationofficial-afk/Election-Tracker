"""
Local test provider
--------------------
Reads a snapshot straight from a local JSON file instead of calling
civicapi over the network. Use this to test that vote-change detection,
batch totals, and map colors actually update -- without a live civicapi
call overwriting your edits every few seconds via your frontend's polling.

Just edit backend/data/test_snapshot.json between requests to /latest,
and every hit will re-read whatever is currently in that file.
"""

import json
from pathlib import Path

TEST_FILE = Path(__file__).resolve().parent.parent / "data" / "test_snapshot.json"


def fetch_race(race_id):
    with open(TEST_FILE) as f:
        return json.load(f)
