from api import get_race
import compare
import storage


def get_latest_update(race_id):
    new = get_race(race_id)
    old = storage.load_snapshot()

    # First run
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
        return comparison

    # No new batch, return the last saved comparison instead
    latest = storage.load_latest_comparison()

    if latest is not None:
        return latest

    # Fallback if there are somehow no saved comparisons
    return comparison