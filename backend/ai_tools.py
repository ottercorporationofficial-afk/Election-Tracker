"""
AI tools
--------
Function declarations + implementations the chatbot can call to read REAL,
CURRENT election data -- reusing the exact same tracker.py/registry.py
pipeline the map and statewide panel already use. The model never sees
raw vote data unless it explicitly calls one of these; it can't make up
numbers convincingly because it has no numbers until it asks for them.
"""

from backend.tracker import get_cached_update
from backend.registry import RACES


def list_races():
    """
    All races currently tracked, with their race_key (what the other
    tools need) and which state/source they're from.
    """
    return {
        "races": [
            {
                "race_key": key,
                "state": config.get("state"),
                "source": config.get("source"),
                "archived": config.get("archived", False)
            }
            for key, config in RACES.items()
        ]
    }


def get_race_summary(race_key):
    """
    Statewide totals, leader, and reporting percentage for one race.
    Deliberately summarized (not the full per-county payload) to keep
    this fast and cheap to call -- use get_county_result for one
    specific county's detail.
    """

    if race_key not in RACES:
        return {"error": f"Unknown race_key '{race_key}'. Call list_races to see valid options."}

    result = get_cached_update(race_key)

    if "error" in result:
        return result

    summary = {
        "race_key": race_key,
        "projected_winner": result.get("projected_winner"),
        "archived": result.get("archived", False),
        "stale": result.get("stale", False),
        "first_run": result.get("first_run", False),
    }

    if result.get("has_counties"):

        totals = {}
        reporting_values = []

        for county in result.get("counties", {}).values():

            for name, c in county.get("candidates", {}).items():
                totals[name] = totals.get(name, 0) + c.get("votes", 0)

            reporting = county.get("reporting", {}).get("new")

            if reporting is not None:
                reporting_values.append(reporting)

        summary["statewide_totals"] = sorted(
            [{"name": n, "votes": v} for n, v in totals.items()],
            key=lambda x: -x["votes"]
        )
        summary["avg_reporting_percent"] = (
            round(sum(reporting_values) / len(reporting_values), 1)
            if reporting_values else None
        )
        summary["county_count"] = len(result.get("counties", {}))

    else:
        results = result.get("results", {})
        summary["statewide_totals"] = sorted(
            [
                {"name": n, "votes": c.get("votes", 0)}
                for n, c in results.get("candidates", {}).items()
            ],
            key=lambda x: -x["votes"]
        )

    return summary


def get_county_result(race_key, county_name):
    """
    Full detail for one specific county within a race: per-candidate
    votes, leader, reporting percentage. Matches county_name against
    either the internal key or the display name, case-insensitively.
    """

    if race_key not in RACES:
        return {"error": f"Unknown race_key '{race_key}'. Call list_races to see valid options."}

    result = get_cached_update(race_key)

    if "error" in result:
        return result

    if not result.get("has_counties"):
        return {"error": f"Race '{race_key}' doesn't have county-level results (it's a statewide-only race)."}

    counties = result.get("counties", {})
    needle = county_name.strip().lower()

    for key, county in counties.items():
        if key.lower() == needle or county.get("name", "").lower() == needle:
            return county

    available = [c.get("name", key) for key, c in counties.items()]
    return {
        "error": f"No county matching '{county_name}' found in race '{race_key}'.",
        "available_counties": available
    }


def get_all_counties(race_key):
    """
    Per-candidate vote counts for EVERY county in a race, in one call --
    for questions like "which counties does X do best in" or "where is Y
    closest" that would otherwise require calling get_county_result once
    per county (64 separate calls for Colorado, for example -- way more
    than the chat loop's turn cap allows).
    """

    if race_key not in RACES:
        return {"error": f"Unknown race_key '{race_key}'. Call list_races to see valid options."}

    result = get_cached_update(race_key)

    if "error" in result:
        return result

    if not result.get("has_counties"):
        return {"error": f"Race '{race_key}' doesn't have county-level results (it's a statewide-only race)."}

    counties = []

    for key, county in result.get("counties", {}).items():
        counties.append({
            "county": county.get("name", key),
            "reporting_percent": county.get("reporting", {}).get("new"),
            "candidates": [
                {"name": name, "votes": c.get("votes", 0)}
                for name, c in county.get("candidates", {}).items()
            ]
        })

    return {"race_key": race_key, "counties": counties}


# --------------------
# Tool declarations (Gemini function-calling schema)
# --------------------

TOOLS = [
    {
        "type": "function",
        "name": "list_races",
        "description": "Lists every election race currently tracked, with the race_key identifier needed by the other tools.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "type": "function",
        "name": "get_race_summary",
        "description": (
            "Gets current statewide vote totals, the projected winner (if one has been "
            "called), and average reporting percentage for one race. Call list_races "
            "first if you don't already know the exact race_key."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "race_key": {
                    "type": "string",
                    "description": "The race identifier, e.g. 'co_governor_primary'."
                }
            },
            "required": ["race_key"]
        }
    },
    {
        "type": "function",
        "name": "get_county_result",
        "description": "Gets detailed current results for ONE specific, named county within a race. Use get_all_counties instead if the question requires comparing or ranking across many/all counties (e.g. 'which counties does X do best in').",
        "parameters": {
            "type": "object",
            "properties": {
                "race_key": {
                    "type": "string",
                    "description": "The race identifier."
                },
                "county_name": {
                    "type": "string",
                    "description": "The county's name, e.g. 'Maricopa' or 'El Paso'."
                }
            },
            "required": ["race_key", "county_name"]
        }
    },
    {
        "type": "function",
        "name": "get_all_counties",
        "description": (
            "Gets per-candidate vote counts for EVERY county in a race in a single call. "
            "Use this (not repeated get_county_result calls) for any question requiring "
            "comparison or ranking across counties -- e.g. 'which counties does X lead in "
            "by the most', 'where is the race closest', 'X's strongest counties'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "race_key": {
                    "type": "string",
                    "description": "The race identifier."
                }
            },
            "required": ["race_key"]
        }
    }
]

TOOL_FUNCTIONS = {
    "list_races": lambda **kwargs: list_races(),
    "get_race_summary": lambda **kwargs: get_race_summary(kwargs["race_key"]),
    "get_county_result": lambda **kwargs: get_county_result(kwargs["race_key"], kwargs["county_name"]),
    "get_all_counties": lambda **kwargs: get_all_counties(kwargs["race_key"]),
}
