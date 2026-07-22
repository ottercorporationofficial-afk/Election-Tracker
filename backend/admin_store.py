"""
Admin overrides store
----------------------
Holds the things you want to edit live, without a code change/redeploy:
candidate colors, display-name aliases, and projected winner, per race.

Backed by a plain JSON file (backend/data/admin_overrides.json) rather
than a database -- simple, and totally fine for single-admin editing.

This is intentionally separate from registry.py: registry.py is
structural (which provider, which URL) and needs a real deploy to change.
This file is editorial and needs to change live, on election night,
without touching code.
"""

import json
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent / "data" / "admin_overrides.json"

_DEFAULT_RACE_OVERRIDES = {
    "candidate_colors": {},
    "candidate_aliases": {},
    "projected_winner": None,
    "needle": None,  # {"candidate": "Name", "value": 0-100} or None to hide the needle
    "turnout_projections": {}  # {"county_key": total_votes, ...} -- per-county, empty dict means "use civicapi's own reporting % everywhere"
}


def _load():
    if not STORE_PATH.exists():
        return {}
    with open(STORE_PATH) as f:
        return json.load(f)


def _save(data):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_overrides(race_key):
    data = _load()
    return data.get(race_key, dict(_DEFAULT_RACE_OVERRIDES))


def set_candidate_color(race_key, candidate_name, color):
    data = _load()
    race = data.setdefault(race_key, dict(_DEFAULT_RACE_OVERRIDES))
    race.setdefault("candidate_colors", {})[candidate_name] = color
    _save(data)


def clear_candidate_color(race_key, candidate_name):
    data = _load()
    race = data.get(race_key)
    if race and candidate_name in race.get("candidate_colors", {}):
        del race["candidate_colors"][candidate_name]
        _save(data)


def set_candidate_alias(race_key, raw_name, display_name):
    data = _load()
    race = data.setdefault(race_key, dict(_DEFAULT_RACE_OVERRIDES))
    race.setdefault("candidate_aliases", {})[raw_name] = display_name
    _save(data)


def clear_candidate_alias(race_key, raw_name):
    data = _load()
    race = data.get(race_key)
    if race and raw_name in race.get("candidate_aliases", {}):
        del race["candidate_aliases"][raw_name]
        _save(data)


def set_projected_winner(race_key, winner_name_or_none):
    data = _load()
    race = data.setdefault(race_key, dict(_DEFAULT_RACE_OVERRIDES))
    race["projected_winner"] = winner_name_or_none
    _save(data)


def set_needle(race_key, candidate_name, value):
    """
    value: 0-100, how strongly the needle leans toward candidate_name.
    50 = dead even, 100 = fully candidate_name, 0 = fully the other side.
    Purely a manual editorial setting -- you decide the number, it's
    never computed from vote counts.
    """
    data = _load()
    race = data.setdefault(race_key, dict(_DEFAULT_RACE_OVERRIDES))
    race["needle"] = {"candidate": candidate_name, "value": value}
    _save(data)


def clear_needle(race_key):
    data = _load()
    race = data.get(race_key)
    if race:
        race["needle"] = None
        _save(data)


def set_county_turnout_projection(race_key, county_key, total_votes):
    """
    total_votes: your own manual estimate of total expected votes for
    ONE county. When set, that county's "% in" gets computed as (votes
    counted so far in that county / total_votes) instead of trusting
    civicapi's own reporting percentage for it. Every other county
    without an override keeps using civicapi's own number. Purely a
    manual editorial number, never derived automatically.
    """
    data = _load()
    race = data.setdefault(race_key, dict(_DEFAULT_RACE_OVERRIDES))
    race.setdefault("turnout_projections", {})[county_key] = total_votes
    _save(data)


def clear_county_turnout_projection(race_key, county_key):
    data = _load()
    race = data.get(race_key)
    if race and county_key in race.get("turnout_projections", {}):
        del race["turnout_projections"][county_key]
        _save(data)


def apply_overrides_to_comparison(comparison, race_key):
    """
    Applied to the FINAL comparison output, right before returning to the
    client -- NOT to the raw fetched data before storage/diffing. This
    matters for two reasons:

    1. Reset correctness: if overrides were baked in before storage.py
       saved the snapshot, "raw" color/name would actually be the OLD
       override, not the true original -- so clearing an override
       wouldn't visibly do anything until a totally fresh fetch happened.
       Keeping storage always holding true raw data means Reset instantly
       reflects the real fallback color.

    2. Diff correctness: if a candidate's name changed between two
       already-applied-override snapshots, compare.py would see two
       different names and think a new candidate appeared with 0 prior
       votes, rather than recognizing it as the same candidate renamed.
       Diffing on raw data avoids that entirely.
    """

    overrides = get_overrides(race_key)
    aliases = overrides.get("candidate_aliases", {})
    colors = overrides.get("candidate_colors", {})

    def resolve(name, color):
        return aliases.get(name, name), colors.get(name, color)

    # Top-level roster (list of dicts)
    for c in comparison.get("candidates", []):
        new_name, new_color = resolve(c.get("name"), c.get("color"))
        c["name"] = new_name
        c["color"] = new_color

    turnout_projections = overrides.get("turnout_projections", {})

    # Per-county candidates (dict keyed by name) + leader
    for county_key, county in comparison.get("counties", {}).items():

        renamed_candidates = {}

        for name, cand_data in county.get("candidates", {}).items():
            new_name, new_color = resolve(name, cand_data.get("color"))
            cand_data["color"] = new_color
            renamed_candidates[new_name] = cand_data

        county["candidates"] = renamed_candidates

        if "leader" in county:
            leader = county["leader"]
            new_name, new_color = resolve(leader.get("name"), leader.get("color"))
            leader["name"] = new_name
            leader["color"] = new_color

        if county.get("batch", {}).get("winner"):
            county["batch"]["winner"] = aliases.get(
                county["batch"]["winner"], county["batch"]["winner"]
            )

        # Custom turnout projection for this specific county overrides
        # civicapi's own reporting percentage -- computed as actual votes
        # counted in this county divided by your own estimate. Counties
        # without an override keep civicapi's number untouched. Applied
        # directly to reporting.new, so the map, tooltips, county list,
        # and the statewide average (which just averages every county's
        # reporting.new) all pick this up automatically, with no other
        # code needing to know this override exists.
        projection = turnout_projections.get(county_key)

        if projection and projection > 0:
            votes_in_county = sum(c.get("votes", 0) for c in county["candidates"].values())
            county.setdefault("reporting", {})["new"] = min(100, (votes_in_county / projection) * 100)

    # Statewide-only path (a race with no counties)
    if "results" in comparison:

        renamed_candidates = {}

        for name, cand_data in comparison["results"].get("candidates", {}).items():
            new_name, new_color = resolve(name, cand_data.get("color"))
            cand_data["color"] = new_color
            renamed_candidates[new_name] = cand_data

        comparison["results"]["candidates"] = renamed_candidates

        if comparison["results"].get("batch", {}).get("winner"):
            comparison["results"]["batch"]["winner"] = aliases.get(
                comparison["results"]["batch"]["winner"],
                comparison["results"]["batch"]["winner"]
            )

    return comparison
