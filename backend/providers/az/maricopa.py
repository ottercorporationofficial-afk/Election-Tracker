"""
Maricopa County (AZ) provider
------------------------------
Maricopa publishes results as a tab-delimited .txt file (not JSON, not a
scrape-friendly HTML page) covering EVERY contest and EVERY precinct in
the county at once. This provider downloads that file, filters down to
one specific contest, and aggregates all of that contest's precincts into
a single county-level result -- matching what compare.py expects.

provider_config:
    {
        "url": "https://elections.maricopa.gov/asset/.../Primary+2026....txt",
        "contest_name": "DEM US Rep Dist CD-1"
    }

`contest_name` must match the ContestName column exactly as Maricopa
writes it (case-sensitive, exact spacing). The file's URL changes every
election -- update it in registry.py when Maricopa posts a new one.

IMPORTANT ARCHIVING NOTE: once an election is canvassed, Maricopa
eventually replaces this file/URL with the next election's file. Before
that happens, mark this race "archived": true in registry.py so the
system stops trying to re-fetch a URL that no longer exists and instead
serves the last snapshot you successfully saved, forever. See tracker.py.
"""

import csv
import io
import time
import requests

# Maricopa's CandidateAffiliation column uses short codes; map them to the
# full party names PARTY_COLORS (in map.js) expects.
PARTY_NAMES = {
    "DEM": "Democrat",
    "REP": "Republican",
    "LIB": "Libertarian",
    "GRN": "Green",
    "IND": "Independent",
}

# The results file is large (every contest, every precinct in the county)
# and only actually changes when Maricopa posts an update -- not every
# few seconds. Without a cache, every poll from every open tab re-downloads
# and re-parses the whole file, which is what was making the page slow.
# Bump CACHE_SECONDS down if you need fresher data during a fast-moving
# election night; there's no reason to go below Maricopa's own update
# cadence (they post daily updates, not live-streaming ones).
CACHE_SECONDS = 60

_cache = {}  # url -> (fetched_at, raw_text)


def _get_raw_text(url):

    cached = _cache.get(url)

    if cached and (time.time() - cached[0]) < CACHE_SECONDS:
        return cached[1]

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    _cache[url] = (time.time(), response.text)

    return response.text


def fetch_county(county_key, provider_config):
    text = _get_raw_text(provider_config["url"])

    return _normalize(text, provider_config["contest_name"])


def _normalize(text, contest_name):

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")

    candidate_votes = {}   # name -> total votes across all precincts
    candidate_party = {}   # name -> party (full name)
    precincts_seen = {}    # precinct id -> (registered, turnout)

    for row in reader:

        if row["ContestName"] != contest_name:
            continue

        name = row["CandidateName"].strip()
        votes = int(row["Votes"] or 0)

        candidate_votes[name] = candidate_votes.get(name, 0) + votes

        if name not in candidate_party:
            raw_party = (row.get("CandidateAffiliation") or "").strip()
            candidate_party[name] = PARTY_NAMES.get(raw_party, raw_party or None)

        # Each precinct repeats once per candidate row for this contest --
        # only count it once toward reporting totals.
        precinct_id = row["PrecinctId"]

        if precinct_id not in precincts_seen:
            precincts_seen[precinct_id] = (
                int(row["PrecinctRegistered"] or 0),
                int(row["PrecinctTurnout"] or 0)
            )

    total_registered = sum(registered for registered, turnout in precincts_seen.values())
    total_turnout = sum(turnout for registered, turnout in precincts_seen.values())

    percent_reporting = (
        round(100 * total_turnout / total_registered, 2)
        if total_registered else None
    )

    candidates = [
        {
            "name": name,
            "votes": votes,
            "party": candidate_party.get(name)
        }
        for name, votes in candidate_votes.items()
    ]

    return {
        "name": None,  # filled in from registry.py
        "percent_reporting": percent_reporting,
        "candidates": candidates
    }
