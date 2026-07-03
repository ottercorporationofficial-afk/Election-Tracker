from tracker import get_latest_update

RACE_ID = 84287

print("That's a little bit old that result, if you want to see something that good take a look at what happened:\n")

comparison = get_latest_update(RACE_ID)

if comparison.get("status") == "first_run":
    print("First run. Snapshot saved.")
    quit()

if not comparison["has_changes"]:
    print("No updates.")
    quit()

vote_changes = comparison["vote_changes"]
reporting_changes = comparison["reporting_changes"]

print("Comparing...\n")

for county, candidates in vote_changes.items():

    if all(change == 0 for change in candidates.values()):
        continue

    print(f"===== {county.upper()} =====")

    reporting = reporting_changes[county]

    print(
        f"Reporting: {reporting['old']}% → "
        f"{reporting['new']}% "
        f"({reporting['change']:+g}%)"
    )

    batch_total = sum(candidates.values())

    for candidate, change in candidates.items():
        percent = (
            f"{change / batch_total:.1%}"
            if batch_total != 0
            else "N/A"
        )

        print(f"{candidate:<20} {change:+d} ({percent})")

    candidates_sorted = sorted(
        candidates.items(),
        key=lambda item: item[1],
        reverse=True
    )

    leader_name, leader_votes = candidates_sorted[0]
    second_name, second_votes = candidates_sorted[1]

    batch_margin_votes = leader_votes - second_votes

    if batch_total != 0:
        batch_margin_percent = batch_margin_votes / batch_total
        margin = f"{leader_name} +{batch_margin_votes} ({batch_margin_percent:.1%})"
    else:
        margin = f"{leader_name} +{batch_margin_votes}"

    print(f"\nBatch Total: {batch_total} votes")
    print(f"Batch Margin: {margin}")
    print()