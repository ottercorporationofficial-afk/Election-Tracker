from api import get_race
import compare
import storage


def get_latest_update(race_id):
    new = get_race(race_id)
    old = storage.load_snapshot()

    # First run
    if old == {}:
        storage.save_snapshot(new)
        return {
            "status": "first_run"
        }

    comparison = compare.compare_snapshots(old, new)

    if comparison["has_changes"]:
        storage.save_snapshot(new)
        storage.save_archive_snapshot(new)

    return comparison