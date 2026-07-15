"""
Aggregator
----------
The one place that knows about "sources." Everything downstream of
fetch_race() -- compare.py, storage.py, tracker.py, map.js -- only ever
sees the canonical snapshot shape, whether the data came from civicapi in
one call or from ten different county websites.
"""

import importlib

from backend.registry import RACES


def fetch_race(race_key):

    config = RACES[race_key]

    if config["source"] == "civicapi":
        from backend.providers import civicapi
        return civicapi.fetch_race(config["race_id"])

    if config["source"] == "local_test":
        from backend.providers import local_test
        return local_test.fetch_race(config.get("race_id"))

    if config["source"] == "county_providers":
        return _fetch_from_counties(config)

    raise ValueError(f"Unknown race source: {config['source']!r}")


def _fetch_from_counties(config):

    aliases = config.get("name_aliases", {})
    region_results = {}
    roster = {}  # canonical_name -> {"name", "party", "color"}

    for county_key, county_config in config["counties"].items():

        provider = importlib.import_module(f"backend.providers.{county_config['provider']}")

        county_data = provider.fetch_county(county_key, county_config["provider_config"])

        # Registry is the source of truth for name/fips, in case the
        # provider itself doesn't know or return them reliably.
        county_data["name"] = county_config.get("name", county_data.get("name"))
        county_data["fips"] = county_config["fips"]

        # Normalize candidate names through the alias map, and build up
        # the race-wide roster as we go.
        for candidate in county_data["candidates"]:

            canonical_name = aliases.get(candidate["name"], candidate["name"])
            candidate["name"] = canonical_name

            if canonical_name not in roster:
                roster[canonical_name] = {
                    "name": canonical_name,
                    "party": candidate.get("party"),
                    "color": candidate.get("color")
                }

        region_results[county_key] = county_data

    return {
        "candidates": list(roster.values()),
        "region_results": region_results
    }
