from datetime import datetime
import json

with open("data/county_fips.json", "r") as f:
    COUNTY_FIPS = json.load(f)


def compare_snapshots(old, new):
    # No previous snapshot exists
    if old is None:
        return {
            "timestamp": datetime.now().isoformat(),
            "counties": {},
            "has_changes": False,
            "has_counties": True,
            "first_run": True
        }

    if not old.get("region_results"):

        old_votes = {}
        new_votes = {}

        results = {
            "candidates": {}
        }

        has_changes = False


        for candidate in old["candidates"]:
            old_votes[candidate["name"]] = candidate["votes"]

        for candidate in new["candidates"]:
            new_votes[candidate["name"]] = candidate["votes"]

        batch_total = 0

        for candidate in new_votes:
            vote_change = new_votes[candidate] - old_votes.get(candidate, 0)

            batch_total += vote_change

            if vote_change != 0:
                has_changes = True

            results["candidates"][candidate] = {
                "change": vote_change,
                "votes": new_votes[candidate]
            }


        batch = batch_sort(results,batch_total)


        results["batch"] = {
            "total": batch_total,
            **batch
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "has_changes": has_changes,
            "has_counties": False,
            "first_run": False
        }

    has_changes = False
    time_stamp = datetime.now().isoformat()

    comparison = {
        "timestamp": time_stamp,
        "counties": {},
        "has_changes": False,
        "has_counties": True,
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

        county_data["name"] = county.replace("_", " ").title()
        county_data["fips"] = COUNTY_FIPS.get(county)

        print("ADDING:", county, county_data["fips"])
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

        # ---------------- Current County Leader ----------------

        sorted_candidates = sorted(
            new_county["candidates"],
            key=lambda c: c["votes"],
            reverse=True
        )

        leader = sorted_candidates[0]
        runner_up = sorted_candidates[1]

        total_votes = sum(c["votes"] for c in new_county["candidates"])

        county_data["leader"] = {
            "name": leader["name"],
            "votes": leader["votes"],
            "margin_votes": leader["votes"] - runner_up["votes"],
            "margin_percent": (
                (leader["votes"] - runner_up["votes"]) / total_votes
                if total_votes else 0
            )
        }

        # ---------------- Batch Sorting ----------------

        batch = batch_sort(county_data, batch_total)

        county_data["batch"] = {
            "total": batch_total,
            **batch,
        }

    comparison["has_changes"] = has_changes


    return comparison


def batch_sort(data, batch_total):
    candidates = data["candidates"]

    candidates_sorted = sorted(
        candidates.items(),
        key=lambda item: item[1]["change"],
        reverse=True
    )

    if len(candidates_sorted) < 2:
        return {
            "winner": candidates_sorted[0][0] if candidates_sorted else None,
            "margin_votes": 0,
            "margin_percent": 0,
        }

    leader_name, leader_data = candidates_sorted[0]
    _, second_data = candidates_sorted[1]

    batch_margin_votes = leader_data["change"] - second_data["change"]

    batch_margin_percent = (
        batch_margin_votes / batch_total if batch_total else 0
    )

    for candidate_data in candidates.values():
        candidate_data["batch_percent"] = (
            candidate_data["change"] / batch_total
            if batch_total else 0
        )

    return {
        "winner": leader_name,
        "margin_votes": batch_margin_votes,
        "margin_percent": batch_margin_percent,
    }