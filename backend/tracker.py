from api import get_race
import compare
import storage


def get_latest_update(race_id):
    new = get_race(race_id)
    old = storage.load_snapshot()

    if old is None:
        storage.save_snapshot(new)
        return {
            "first_run": True,
            "has_changes": False
        }

    comparison = compare.compare_snapshots(old, new)

    if comparison["has_changes"]:
        storage.save_snapshot(new)
        storage.save_archive_snapshot(new)
        storage.save_comparison(comparison)

    # ALWAYS return the newest comparison
    return comparison