

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
        else if (diffMinutes < 60) {
            updated.textContent = `Last Updated: ${diffMinutes} minutes ago`;
        }
        else {
            const diffHours = Math.floor(diffMinutes / 60);

            if (diffHours === 1) {
                updated.textContent = "Last Updated: 1 hour ago";
            }
            else {
                updated.textContent = `Last Updated: ${diffHours} hours ago`;
            }
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



// --------------------
// Statewide Panel
// --------------------

function candidateColor(name) {

    // candidateColors comes from map.js, which loads before this script
    // and shares the same global scope.
    if (typeof candidateColors !== "undefined" && candidateColors[name]) {
        return candidateColors[name];
    }

    return "#888888";

}

function computeStatewideTotals(counties) {

    const totals = {};
    const reportingValues = [];

    for (const countyName in counties) {

        const county = counties[countyName];

        if (typeof county.reporting?.new === "number") {
            reportingValues.push(county.reporting.new);
        }

        for (const candidateName in county.candidates) {

            const candidate = county.candidates[candidateName];

            if (!(candidateName in totals)) {
                totals[candidateName] = 0;
            }

            totals[candidateName] += candidate.votes;
        }
    }

    // Simple unweighted average across counties. Swap for a
    // votes-weighted average if that's a better fit for your data.
    const reportingAvg = reportingValues.length
        ? reportingValues.reduce((a, b) => a + b, 0) / reportingValues.length
        : 0;

    return { totals, reportingAvg };

}

function renderStatewide(totals, reportingAvg) {

    const container = document.getElementById("statewide");

    const grandTotal = Object.values(totals).reduce((a, b) => a + b, 0);

    const sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]);

    let html = "";

    for (const [name, votes] of sorted) {

        const pct = grandTotal > 0 ? (votes / grandTotal) * 100 : 0;
        const color = candidateColor(name);

        html += `
            <div class="statewide-candidate">

                <div class="statewide-header">

                    <span class="candidate-color" style="background:${color}"></span>

                    <span class="statewide-name">
                        ${name}
                    </span>

                </div>

                <div class="statewide-votes">
                    ${votes.toLocaleString()} votes
                </div>

                <div class="statewide-percent">
                    ${pct.toFixed(1)}%
                </div>

                <div class="progress">
                    <div class="progress-fill" style="width:${pct.toFixed(1)}%; background:${color}"></div>
                </div>

            </div>
        `;
    }

    html += `
        <hr>

        <div class="reporting-box">

            <strong>Reporting</strong>

            <span>${Math.round(reportingAvg)}%</span>

        </div>
    `;

    container.innerHTML = html;

    const headerReporting = document.getElementById("header-reporting");

    if (headerReporting) {
        headerReporting.textContent = `${Math.round(reportingAvg)}% reporting`;
    }

}

async function loadStatewide() {

    const response = await fetch("/latest");
    const data = await response.json();

    // First run returns no county data yet — nothing to render.
    if (!data.counties) {
        return;
    }

    const { totals, reportingAvg } = computeStatewideTotals(data.counties);

    renderStatewide(totals, reportingAvg);

}

async function refresh() {

    await loadStatewide();
    await loadHistory();

}

refresh();

setInterval(refresh, 5000);