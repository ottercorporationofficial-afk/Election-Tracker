from backend import compare
from backend import storage
from backend.aggregator import fetch_race
from backend.registry import RACES


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
        result = compare.compare_snapshots(old, old)
        result["archived"] = True
        return result

    try:
        new = fetch_race(race_key)
    except Exception as e:
        # Live source is unreachable -- e.g. the county replaced the results
        # URL, or a temporary network/site issue. Don't crash the API or
        # your frontend map: fall back to the last snapshot you DID
        # successfully save, and flag it as stale so you know to check.
        if old is None:
            raise  # nothing to fall back to, this is a genuine setup problem
        result = compare.compare_snapshots(old, old)
        result["stale"] = True
        result["fetch_error"] = str(e)
        return result

    if old is None:
        storage.save_snapshot(race_key, new)
        result = compare.compare_snapshots(new, new)
        result["first_run"] = True
        return result

    comparison = compare.compare_snapshots(old, new)

    if comparison["has_changes"]:
        storage.save_snapshot(race_key, new)
        storage.save_archive_snapshot(race_key, new)
        storage.save_comparison(race_key, comparison)

    # ALWAYS return the newest comparison
    return comparison
