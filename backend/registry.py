"""
Race registry
-------------
One entry per race you're tracking. `source` tells fetch_race() (in
aggregator.py) how to get the data:

  - "civicapi"        -> single call to civicapi for the whole race
  - "county_providers" -> stitch together per-county results from
                          whatever provider each county uses

Adding a new civicapi race = one entry, no code changes.
Adding a new county-scraped race = one entry per county, using whichever
provider matches that county's site (most will reuse "clarity_style";
one-off sites get their own module like custom_example.py).

Optional per-race field:

  "projected_winner": "Candidate Name"

Set this by hand, once you (the editor) have decided to call the race --
never derived from vote counts automatically. Leave unset (or null) until
you're ready to call it. This shows up in the API response and the
statewide panel; it has no effect on the map/tooltips, which always show
raw current vote standings only.

Also optional, used by storage.py to decide where a race's saved data
lives on disk (data/races/<STATE>/<cycle>/<race_key>/):

  "state": "az"                 -> uppercased for the folder name (AZ)
  "cycle": "2026-primaries"     -> used as-is for the folder name

Races missing either field still work fine -- they just land under
UNKNOWN/uncategorized instead of a clean state/cycle folder.

Also optional -- ties a race's turnout projections (set in /admin) to a
SHARED group instead of being private to just that one race:

  "turnout_group": "az_republican_primary_2026"

Every race with the same turnout_group string shares one set of
per-county projections -- set Maricopa's estimate once under any race in
the group, and it applies to all of them (since they're all on the same
physical ballot, voted on by the same people, on the same day). Races
without this field just default to being their own private group of one.
"""

RACES = {

    "co_governor_primary": {
        "source": "civicapi",
        "race_id": 84287,
        "state": "co",
        "cycle": "2026-primaries"
    },

    # AZ Governor Republican Primary 2026 -- currently just Maricopa; add
    # AZ Governor Republican Primary 2026 -- switched to civicapi.
    # "state": "az" tells compare.py which per-state FIPS file to fall
    # back to (backend/data/counties/az.json) if civicapi's own county
    # data doesn't already include a fips field.
    "az_governor_republican_primary_2026": {
        "source": "civicapi",
        "race_id": 84359,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_republican_primary_2026"
    },

    "az_secretary_of_state_republican_2026": {
        "source": "civicapi",
        "race_id": 84412,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_republican_primary_2026"
    },

    "arizona_congressional_05_republican": {
        "source": "civicapi",
        "race_id": 84551,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_republican_primary_2026"

    },

    "arizona_congressional_01_democratic": {
        "source": "civicapi",
        "race_id": 84537,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_democratic_primary_2026"

    },

    "arizona_congressional_04_democratic": {
        "source": "civicapi",
        "race_id": 84547,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_democratic_primary_2026"

    },
    "arizona_attorney_general_republican": {
        "source": "civicapi",
        "race_id": 84329,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_republican_primary_2026"

    },
    "arizona_superintendent_republican": {
        "source": "civicapi",
        "race_id": 84534,
        "state": "az",
        "cycle": "2026-primaries",
        "turnout_group": "az_republican_primary_2026"

    },

    # TEST-ONLY twin of the race above -- same fips/geography, but reads a
    # local file instead of hitting Maricopa's live URL. Point your AZ
    # page's map at data-race="az_governor_test" while testing, edit
    # backend/data/test_counties/maricopa.json, and refresh to see
    # the live map itself update -- not just the raw JSON.
    "az_governor_test": {
        "source": "county_providers",
        "projected_winner": None,
        "counties": {
            "maricopa": {
                "name": "Maricopa",
                "fips": "04013",
                "provider": "local_test_county",
                "provider_config": {"file": "maricopa.json"}
            },
            "pima": {
                "name": "Pima",
                "fips": "04019",
                "provider": "local_test_county",
                "provider_config": {"file": "pima_test.json"}
            },
            "pinal":{
                "name": "Pinal",
                "fips": "04021",
                "provider": "local_test_county",
                "provider_config": {"file": "pinal.json"}

            },
            "gila": {
                "name": "Gila",
                "fips": "04007",
                "provider": "local_test_county",
                "provider_config": {"file": "gila.json"}
            },
            "yuma": {
                "name": "Yuma",
                "fips": "04027",
                "provider": "local_test_county",
                "provider_config": {"file": "yuma.json"}
            }
        }
    },

    # Test-only multi-county race: two local files standing in for two
    # different county sites, one of which (Jefferson) formats candidate
    # names differently on purpose ("Marx, Victor" vs "Victor Marx") so you
    # can see name_aliases actually merge them into one candidate.
    "test_county_race": {
        "source": "county_providers",
        "counties": {
            "el_paso": {
                "name": "El Paso",
                "fips": "08041",
                "provider": "local_test_county",
                "provider_config": {"file": "el_paso.json"}
            },
            "jefferson": {
                "name": "Jefferson",
                "fips": "08059",
                "provider": "local_test_county",
                "provider_config": {"file": "jefferson.json"}
            }
        },
        "name_aliases": {
            "Marx, Victor": "Victor Marx"
        }
    },


    # Test-only race: reads from backend/data/test_snapshot.json instead of
    # hitting civicapi live. Point your browser at /latest?race=test_race
    # while testing so your frontend polling never overwrites your edits
    # with real live data.
    "test_race": {
        "source": "local_test",
        "race_id": None
    },

    # Example of a race built entirely from county-level scraping instead
    # of civicapi. FIPS is declared here, per county, once -- not derived
    # at runtime from a name-matching lookup.
    "example_county_scraped_race": {
        "source": "county_providers",
        "counties": {
            "el_paso": {
                "name": "El Paso",
                "fips": "08041",
                "provider": "clarity_style",
                "provider_config": {
                    "election_id": "2026-primary-co",
                    "county_code": "041"
                }
            },
            "custom_x": {
                "name": "Custom County",
                "fips": "08099",
                "provider": "custom_example",
                "provider_config": {
                    "url": "https://weirdcounty.gov/elections/results.html"
                }
            }
        },
        # Optional: map alternate spellings/formats a provider might use
        # for a candidate's name back to one canonical name, so compare.py
        # doesn't treat "Bob Smith" from one county and "Smith, Bob" from
        # another as two different candidates.
        "name_aliases": {
            # "Smith, Bob": "Bob Smith",
        }
    }

}
