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
"""

RACES = {

    "co_governor_primary": {
        "source": "civicapi",
        "race_id": 84287
    },

    # AZ Governor Republican Primary 2026 -- currently just Maricopa; add
    # more AZ counties here as you wire up their sites/providers.
    # IMPORTANT: "contest_name" below is a PLACEHOLDER. Run this on a
    # machine with internet access to find the exact string Maricopa uses:
    #
    #   curl -s "<url below>" | cut -f3 | sort -u | grep -i governor
    #
    # then replace "REP Governor" with whatever that prints, exactly
    # (spacing/punctuation matters -- compare.py/maricopa.py match on it
    # verbatim).
    "az_governor_republican_primary_2026": {
        "source": "county_providers",
        "counties": {
            "maricopa": {
                "name": "Maricopa",
                "fips": "04013",
                "provider": "maricopa",
                "provider_config": {
                    "url": "https://elections.maricopa.gov/asset/jcr:09208b40-0ea0-43a2-9831-c555996eabf2/Primary+2026+Zero+for+Web+(1).txt",
                    "contest_name": "REP Governor"
                }
            }
        }
    },

    # TEST-ONLY twin of the race above -- same fips/geography, but reads a
    # local file instead of hitting Maricopa's live URL. Point your AZ
    # page's map at data-race="az_governor_test" while testing, edit
    # backend/data/test_counties/az_governor_test.json, and refresh to see
    # the live map itself update -- not just the raw JSON.
    "az_governor_test": {
        "source": "county_providers",
        "counties": {
            "maricopa": {
                "name": "Maricopa",
                "fips": "04013",
                "provider": "local_test_county",
                "provider_config": {"file": "az_governor_test.json"}
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
