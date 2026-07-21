import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

CSV_FILE = BASE_DIR / "data" / "State_County_and_City_FIPS.csv"
OUTPUT_DIR = BASE_DIR / "data" / "counties"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

states = {}

with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        state = row["State Code"].lower()
        state_abbr = row["State Code"].upper()

        state_fips = row["State FIPS Code"].zfill(2)

        full_fips = row["StCnty FIPS Code"].zfill(5)
        county_fips = full_fips[-3:]

        county_name = row["County Name"]

        slug = (
            county_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "")
        )

        states.setdefault(state, {})

        # Skip duplicate counties (one row per city)
        if full_fips not in states[state]:
            states[state][full_fips] = {
                "name": county_name,
                "slug": slug,
                "state": state_abbr,
                "state_fips": state_fips,
                "county_fips": county_fips
            }

for state, counties in states.items():
    output_file = OUTPUT_DIR / f"{state}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(counties, f, indent=2)

print(f"✅ Generated {len(states)} state files.")