import storage
from datetime import datetime



def compare_snapshots(old, new):
    # No previous snapshot exists
    if old is None:
        return {
            "timestamp": datetime.now().isoformat(),
            "counties": {},
            "has_changes": False,
            "first_run": True
        }


    has_changes = False
    time_stamp = datetime.now().isoformat()

    comparison = {
        "timestamp": time_stamp,
        "counties": {},
        "has_changes": False
    }

    region_results = old["region_results"]

    for county in region_results:

        old_votes = {}
        new_votes = {}

        old_county = old["region_results"][county]
        new_county = new["region_results"][county]

        # Create a shortcut so we don't keep typing the long lookup
        comparison["counties"][county] = {}
        county_data = comparison["counties"][county]

        # ---------------- Reporting ----------------

        old_reporting = old_county["percent_reporting"]
        new_reporting = new_county["percent_reporting"]

        county_data["reporting"] = {
            "old": old_reporting,
            "new": new_reporting,
            "change": new_reporting - old_reporting
        }

        if new_reporting != old_reporting:
            has_changes = True

        # ---------------- Candidates ----------------

        county_data["candidates"] = {}

        for candidate in old_county["candidates"]:
            old_votes[candidate["name"]] = candidate["votes"]

        for candidate in new_county["candidates"]:
            new_votes[candidate["name"]] = candidate["votes"]

        for candidate in old_votes:

            vote_change = new_votes[candidate] - old_votes[candidate]

            if vote_change != 0:
                has_changes = True

            county_data["candidates"][candidate] = {
                "change": vote_change,
                "votes": new_votes[candidate]
            }

        # ---------------- Batch Total ----------------

        batch_total = 0

        for candidate_data in county_data["candidates"].values():
            batch_total += candidate_data["change"]


        # ---------------- Batch Sorting ----------------

        candidates_sorted = sorted(
            county_data["candidates"].items(),
            key=lambda item: item[1]["change"],
            reverse=True
        )

        leader_name, leader_data = candidates_sorted[0]
        second_name, second_data = candidates_sorted[1]

        batch_margin_votes = leader_data["change"] - second_data["change"]

        if batch_total != 0:
            batch_margin_percent = batch_margin_votes / batch_total
        else:
            batch_margin_percent = 0

        for candidate, candidate_data in county_data["candidates"].items():
            candidate_data["batch_percent"] = (
                candidate_data["change"] / batch_total
                if batch_total != 0
                else 0
            )

        county_data["batch"] = {
            "total": batch_total,
            "winner": leader_name,
            "margin_votes": batch_margin_votes,
            "margin_percent": batch_margin_percent
        }

    comparison["has_changes"] = has_changes


    return comparison