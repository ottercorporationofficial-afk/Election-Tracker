"""
Local test county provider
---------------------------
Same idea as providers/local_test.py, but shaped like a real per-county
provider (fetch_county, not fetch_race) so you can test the FULL
county_providers path -- multiple counties merging into one race,
candidate-name aliasing, FIPS attachment, the works -- before you've
written a single real scraper.

Each county's provider_config just points at its own local JSON file:

    "el_paso": {
        "fips": "08041",
        "provider": "local_test_county",
        "provider_config": {"file": "el_paso.json"}
    }

Edit backend/data/test_counties/<file>.json directly to simulate that
county reporting new results.
"""

import json
from pathlib import Path

TEST_COUNTIES_DIR = Path(__file__).resolve().parent.parent / "data" / "test_counties"


def fetch_county(county_key, provider_config):
    file_path = TEST_COUNTIES_DIR / provider_config["file"]

    with open(file_path) as f:
        return json.load(f)
