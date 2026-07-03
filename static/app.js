async function loadElection() {

    const response = await fetch("/latest");
    const data = await response.json();

    const updates = document.getElementById("updates");

    updates.innerHTML = "";

    // Loop through each county
    for (const county in data.vote_changes) {

        const candidates = data.vote_changes[county];
        const reporting = data.reporting_changes[county];

        // Skip counties with no vote changes
        if (Object.values(candidates).every(change => change === 0)) {
            continue;
        }

        // Start the county card
        let countyHTML = `
            <div class="county-card">

                <div class="county-header">

                    <div class="county-name">
                        ${county.replaceAll("_", " ").toUpperCase()}
                    </div>

                    <div class="reporting">
                        ${reporting.old}% → ${reporting.new}% (${reporting.change >= 0 ? "+" : ""}${reporting.change}%)
                    </div>

                </div>
        `;

        // Candidate rows
        for (const candidate in candidates) {

            const change = candidates[candidate];

            countyHTML += `
                <div class="candidate">

                    <span>${candidate}</span>

                    <span>${change >= 0 ? "+" : ""}${change}</span>

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