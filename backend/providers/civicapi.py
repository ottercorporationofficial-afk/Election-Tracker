"""
civicapi provider
-----------------
Wraps the existing civicapi.org integration. This is the easy case: civicapi
already returns data in (almost exactly) the canonical shape compare.py
expects -- top-level `candidates` with name/votes/party/color, and
`region_results` keyed by county slug with fips/percent_reporting/candidates.

So this provider is nearly a pass-through. It exists as its own module (a)
so civicapi is treated as just one provider among many rather than a
special-cased default, and (b) so if civicapi's shape ever drifts, this is
the one place to patch it back into canonical form.
"""

from backend.api import get_race


def fetch_race(race_id):
    """
    Fetch a full race (statewide + all counties, if any) from civicapi.
    Returns data already in canonical snapshot shape:

        {
          "candidates": [{"name", "votes", "party", "color"}, ...],
          "region_results": {
              "<slug>": {
                  "name", "fips", "percent_reporting",
                  "candidates": [{"name", "votes", "party", "color"}, ...]
              },
              ...
          }
        }

    (or just the top-level "candidates" key, with no "region_results", for
    a race that doesn't have counties -- civicapi omits that key itself in
    that case, which is already what compare.py expects.)
    """

    return get_race(race_id)
