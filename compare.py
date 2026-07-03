
def compare_snapshots(old, new):
    has_changes = False

    region_results = old["region_results"]

    comparison = {
        "counties": {},
        "has_changes": False
    }

    for county in region_results:

        old_votes = {}
        new_votes = {}


        old_county = old["region_results"][county]
        new_county = new["region_results"][county]

        old_reporting = old_county["percent_reporting"]
        new_reporting = new_county["percent_reporting"]

        # Create this county's entry once
        comparison["counties"][county] = {}

        comparison["counties"][county]["reporting"] = {
            "old": old_reporting,
            "new": new_reporting,
            "change": new_reporting - old_reporting
        }

        comparison["counties"][county]["candidates"] = {}

        if new_reporting != old_reporting:
            has_changes = True


        # Build old vote dictionary
        for candidate in old_county["candidates"]:
            old_votes[candidate["name"]] = candidate["votes"]

        # Build new vote dictionary
        for candidate in new_county["candidates"]:
            new_votes[candidate["name"]] = candidate["votes"]

        # Compare
        for candidate in old_votes:
            vote_change = new_votes[candidate] - old_votes[candidate]

            comparison["counties"][county]["candidates"][candidate] = {
                "change": vote_change,
                "votes": new_votes[candidate]
            }

    return comparison