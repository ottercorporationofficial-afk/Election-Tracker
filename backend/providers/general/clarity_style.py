"""
"Clarity-style" provider
------------------------
Template for the county API type you said covers "most of them" -- many
counties run the same election-night-reporting platform (JSON endpoint
per county/precinct), just with different election IDs and county codes.
One normalize() function here handles all counties on this platform; only
the per-county config (in registry.py) changes.

This is a TEMPLATE. The actual endpoint URL, JSON field names, and
candidate-list path below are placeholders -- swap them for the real
platform's structure once you have a sample response to look at. The
important part is the *shape this function returns*, not these specific
field names.
"""

import requests


def fetch_county(county_key, provider_config):
    """
    provider_config comes from registry.py, e.g.:
        {
            "election_id": "2026-primary-co",
            "county_code": "041"
        }

    Returns one county's canonical dict:
        {
            "name": str,
            "fips": str,              # filled in by the aggregator from
                                       # the registry, not required here
            "percent_reporting": float | None,
            "candidates": [
                {"name": str, "votes": int, "party": str | None, "color": None}
            ]
        }
    """

    # TODO: replace with the platform's real endpoint pattern
    url = (
        f"https://results.example-clarity-platform.com/"
        f"{provider_config['election_id']}/county/{provider_config['county_code']}.json"
    )

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    raw = response.json()

    return _normalize(raw)


def _normalize(raw):

    # TODO: adjust these lookups to match the real payload structure.
    # This is the ONLY function that needs to change if the platform's
    # JSON shape is different than guessed here -- fetch_county() and
    # everything downstream stays the same.

    candidates = [
        {
            "name": c["candidateName"],
            "votes": int(c["voteCount"]),
            "party": c.get("partyAbbreviation"),
            "color": None  # this platform doesn't provide one
        }
        for c in raw.get("candidates", [])
    ]

    return {
        "name": raw.get("countyName"),
        "percent_reporting": raw.get("percentReporting"),
        "candidates": candidates
    }
