

async function loadHistory() {

    const response = await fetch("/history");
    const history = await response.json();

    const historyContainer = document.getElementById("history");

    historyContainer.innerHTML = "";



    if (history.length > 0) {

        const latestComparison = history[history.length - 1];

        const timestamp = new Date(latestComparison.timestamp);

        const diffMinutes = Math.floor(
            (Date.now() - timestamp.getTime()) / 60000
        );

        const updated = document.getElementById("last-updated");

        if (diffMinutes <= 0) {
            updated.textContent = "Last Updated: Just now";
        }
        else if (diffMinutes === 1) {
            updated.textContent = "Last Updated: 1 minute ago";
        }
        else {
            updated.textContent = `Last Updated: ${diffMinutes} minutes ago`;
        }
    }

    // Newest first
    history.reverse();

    for (const comparison of history) {

        const timestamp = comparison.timestamp
            ? new Date(comparison.timestamp).toLocaleString()
            : "";

        for (const countyName in comparison.counties) {

            const county = comparison.counties[countyName];

            const reporting = county.reporting;
            const batch = county.batch;
            const candidates = county.candidates;

            if (Object.values(candidates).every(c => c.change === 0)) {
                continue;
            }

            let html = `
                <div class="county-card">

                    <div class="timestamp">
                        ${timestamp}
                    </div>

                    <div class="county-header">

                        <div class="county-name">
                            ${countyName.replaceAll("_", " ").toUpperCase()}
                        </div>

                        <div class="reporting">
                            ${reporting.old}% → ${reporting.new}%
                        </div>

                    </div>

                    <div class="batch">

                        <div>
                            <strong>Batch Total:</strong>
                            ${batch.total.toLocaleString()}
                        </div>

                        <div>
                            <strong>Winner:</strong>
                            ${batch.winner}
                        </div>

                        <div>
                            <strong>Margin:</strong>
                            +${batch.margin_votes}
                            (${(batch.margin_percent * 100).toFixed(1)}%)
                        </div>

                    </div>
            `;

            for (const candidateName in candidates) {

                const candidate = candidates[candidateName];

                html += `
                    <div class="candidate">

                        <span>${candidateName}</span>

                        <span>${candidate.votes.toLocaleString()} votes</span>

                        <span>${candidate.change >= 0 ? "+" : ""}${candidate.change}</span>

                        <span>${(candidate.batch_percent * 100).toFixed(1)}%</span>

                    </div>
                `;
            }

            html += `
                </div>
            `;

            historyContainer.innerHTML += html;
        }
    }
}

async function refresh() {

    await loadHistory();

}

refresh();

setInterval(refresh, 5000);