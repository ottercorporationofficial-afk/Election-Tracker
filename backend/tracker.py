from backend import compare
from backend import storage
from backend import admin_store
from backend.aggregator import fetch_race
from backend.registry import RACES


def _finalize(result, race_key, config):
    # Applied to the OUTPUT only -- storage.py always keeps true raw data,
    # never anything with overrides baked in. See apply_overrides_to_comparison's
    # docstring for why that matters (reset correctness + diff correctness).
    result = admin_store.apply_overrides_to_comparison(result, race_key, turnout_group=config.get("turnout_group"))

    overrides = admin_store.get_overrides(race_key)

    override_winner = overrides.get("projected_winner")
    result["projected_winner"] = override_winner or config.get("projected_winner")

    result["needle"] = overrides.get("needle")  # {"candidate": ..., "value": 0-100} or None

    return result


def get_latest_update(race_key):

    config = RACES[race_key]
    old = storage.load_snapshot(race_key)

    # Archived races NEVER attempt a live fetch. Once you've flipped
    # "archived": true in registry.py for a race (after it's canvassed and
    # the source site is expected to stop hosting it), this always serves
    # whatever was last saved to storage -- forever, with no dependency on
    # the source site still existing.
    if config.get("archived"):
        if old is None:
            return {"error": f"No archived data saved for race '{race_key}'"}
        result = compare.compare_snapshots(old, old, state=config.get("state", "co"))
        result["archived"] = True
        return _finalize(result, race_key, config)

    try:
        new = fetch_race(race_key)
    except Exception as e:
        # Live source is unreachable -- e.g. the county replaced the results
        # URL, or a temporary network/site issue. Don't crash the API or
        # your frontend map: fall back to the last snapshot you DID
        # successfully save, and flag it as stale so you know to check.
        if old is None:
            raise  # nothing to fall back to, this is a genuine setup problem
        result = compare.compare_snapshots(old, old, state=config.get("state", "co"))
        result["stale"] = True
        result["fetch_error"] = str(e)
        return _finalize(result, race_key, config)

    if old is None:
        storage.save_snapshot(race_key, new)
        result = compare.compare_snapshots(new, new, state=config.get("state", "co"))
        result["first_run"] = True
        return _finalize(result, race_key, config)

    comparison = compare.compare_snapshots(old, new, state=config.get("state", "co"))

    if comparison["has_changes"]:
        storage.save_snapshot(race_key, new)
        storage.save_archive_snapshot(race_key, new)
        storage.save_comparison(race_key, comparison)

    return _finalize(comparison, race_key, config)


def get_cached_update(race_key):
    """
    Like get_latest_update, but NEVER attempts a live fetch -- just reads
    whatever was last successfully saved to storage and returns it in the
    same shape. Near-instant (a local file read + in-memory diff-against-
    self), instead of however long the actual live source takes to
    respond.

    Use this for latency-sensitive, read-heavy consumers that don't need
    to trigger their OWN fresh fetch -- like the chatbot -- since the
    site's normal 5-second polling loop (from any open page) is already
    keeping storage current independently. Falls back to an error if
    nothing has ever been successfully fetched yet for this race.
    """

    config = RACES[race_key]
    old = storage.load_snapshot(race_key)

    if old is None:
        return {"error": f"No data available yet for race '{race_key}' -- nothing has been fetched successfully so far."}

    result = compare.compare_snapshots(old, old, state=config.get("state", "co"))

    return _finalize(result, race_key, config)
