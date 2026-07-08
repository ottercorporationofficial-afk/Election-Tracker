import compare
import storage
from tracker import get_latest_update

RACE_ID = 84325

print("That's a little bit old that result, if you want to see something that good take a look at what happened:\n")

comparison = get_latest_update(RACE_ID)

if comparison.get("first_run"):
    print("First run. Snapshot saved.")
    quit()


comparisons = storage.load_comparisons()



if not comparison["has_changes"]:
    print("No updates.")
    quit()


if not comparison["has_counties"]:
    print("this race doesn't have regions/counties")
    print("\n Election-Wide Results")

    results = comparison["results"]

    for candidate, data in results["candidates"].items():
        print(
            f"{candidate}: "
            f"+{data['change']} votes "
            f"({data['votes']} total)"
        )

    print()

    print(
        f"Batch Winner: {results['batch']['winner']}"
    )
    print(
        f"Margin: {results['batch']['margin_votes']} votes "
        f"({results['batch']['margin_percent']:.2%})"
    )
    quit()

print(f"Update Time: {comparison['timestamp']}\n")

for county_name, county_data in comparison["counties"].items():

    # Skip counties with no vote changes
    if all(candidate["change"] == 0 for candidate in county_data["candidates"].values()):
        continue

    print(f"===== {county_name.upper()} =====")

    reporting = county_data["reporting"]

    print(
        f"Reporting: {reporting['old']}% → "
        f"{reporting['new']}% "
        f"({reporting['change']:+g}%)"
    )

    print()

    for candidate_name, candidate_data in county_data["candidates"].items():

        print(
            f"{candidate_name:<20} "
            f"{candidate_data['change']:+d} "
            f"({candidate_data['batch_percent']:.1%})"
        )

    batch = county_data["batch"]

    print(f"\nBatch Total: {batch['total']} votes")
    print(
        f"Batch Margin: {batch['winner']} "
        f"+{batch['margin_votes']} "
        f"({batch['margin_percent']:.1%})"
    )
