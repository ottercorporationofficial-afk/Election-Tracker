async function loadElection() {

    const response = await fetch("/latest");
    const data = await response.json();

    const updates = document.getElementById("updates");

    updates.innerHTML = "";

    // Loop through each county
    for (const countyName in data.counties) {

        const county = data.counties[countyName];

        const reporting = county.reporting;
        const batch = county.batch;
        const candidates = county.candidates;

        // Skip counties with no vote changes
        if (Object.values(candidates).every(candidate => candidate.change === 0)) {
            continue;
        }

        // Start the county card
        let countyHTML = `
            <div class="county-card">

                <div class="county-header">

                    <div class="county-name">
                        ${countyName.replaceAll("_", " ").toUpperCase()}
                    </div>

                    <div class="reporting">
                        ${reporting.old}% → ${reporting.new}% (${reporting.change >= 0 ? "+" : ""}${reporting.change}%)
                    </div>

                </div>

                <div class="batch">
                    <div><strong>Batch Total:</strong> ${batch.total}</div>
                    <div><strong>Winner:</strong> ${batch.winner}</div>
                    <div>
                        <strong>Margin:</strong>
                        +${batch.margin_votes}
                        (${(batch.margin_percent * 100).toFixed(1)}%)
                    </div>
                </div>
        `;

        // Candidate rows
        for (const candidateName in candidates) {

            const candidateData = candidates[candidateName];

            countyHTML += `
                <div class="candidate">

                    <span>${candidateName}</span>

                    <span>${candidateData.votes.toLocaleString()} votes</span>

                    <span>${candidateData.change >= 0 ? "+" : ""}${candidateData.change}</span>

                    <span>${(candidateData.batch_percent * 100).toFixed(1)}%</span>

                </div>
            `;
        }

        countyHTML += `
            </div>
        `;

        updates.innerHTML += countyHTML;
    }

}

loadElection();