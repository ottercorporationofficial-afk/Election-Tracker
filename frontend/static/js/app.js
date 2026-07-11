// --------------------
// Time Formatting
// --------------------

function timeAgo(isoTimestamp) {

    const diffMinutes = Math.floor(
        (Date.now() - new Date(isoTimestamp).getTime()) / 60000
    );

    if (diffMinutes <= 0) return "Just now";
    if (diffMinutes === 1) return "1 minute ago";
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;

    const diffHours = Math.floor(diffMinutes / 60);

    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
}

function updateLastUpdated(history) {

    if (history.length === 0) {
        return;
    }

    const latestComparison = history[history.length - 1];
    const updated = document.getElementById("last-updated");

    updated.textContent = `Last Updated: ${timeAgo(latestComparison.timestamp)}`;
}

const API =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://YOUR-RAILWAY-URL.up.railway.app";



// --------------------
// Live County Feed
// --------------------

// Tracks which county-cards are already on screen so a refresh only
// adds what's new instead of tearing down and rebuilding everything
// (which was restarting animations and flashing the whole feed).
const renderedCards = new Set();

function countyCardHtml(countyName, timestamp, county) {

    const reporting = county.reporting;
    const batch = county.batch;
    const candidates = county.candidates;

    let html = `
        <div class="county-card" data-county="${countyName}">

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

    html += `</div>`;

    return html;
}

function updateHistoryCards(history) {

    const historyContainer = document.getElementById("history");

    // History comes back oldest-first. Walking it in that order and
    // prepending only the entries we haven't rendered yet keeps
    // existing cards untouched while new ones land at the top.
    for (const comparison of history) {

        const timestamp = comparison.timestamp
            ? new Date(comparison.timestamp).toLocaleString()
            : "";

        for (const countyName in comparison.counties) {

            const county = comparison.counties[countyName];
            const candidates = county.candidates;

            if (Object.values(candidates).every(c => c.change === 0)) {
                continue;
            }

            const key = `${comparison.timestamp}|${countyName}`;

            if (renderedCards.has(key)) {
                continue;
            }

            renderedCards.add(key);

            const placeholder = historyContainer.querySelector("#no-updates-placeholder");

            if (placeholder) {
                placeholder.remove();
            }

            historyContainer.insertAdjacentHTML(
                "afterbegin",
                countyCardHtml(countyName, timestamp, county)
            );
        }
    }

    if (renderedCards.size === 0 && !historyContainer.querySelector("#no-updates-placeholder")) {
        historyContainer.innerHTML = `<div id="no-updates-placeholder" class="empty-feed">No updates yet.</div>`;
    }

    applyCountyFilter();
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

function statewideCandidateHtml(name) {

    const color = candidateColor(name);

    return `
        <div class="statewide-header">

            <span class="candidate-color" style="background:${color}"></span>

            <span class="statewide-name">
                ${name}
            </span>

        </div>

        <div class="statewide-votes"></div>

        <div class="statewide-percent"></div>

        <div class="progress">
            <div class="progress-fill" style="background:${color}"></div>
        </div>
    `;
}

// Builds the statewide panel's DOM structure the first time only.
// Every refresh after that just updates text/width on the existing
// elements in place, so progress bars transition smoothly instead of
// restarting their grow-in animation and cards no longer flash.
function ensureStatewideBuilt(container, candidateNames) {

    if (container.dataset.built === "true") {
        return;
    }

    let html = "";

    for (const name of candidateNames) {
        html += `<div class="statewide-candidate" data-candidate="${name}">${statewideCandidateHtml(name)}</div>`;
    }

    html += `
        <hr>

        <div class="reporting-box">

            <strong>Reporting</strong>

            <span></span>

        </div>
    `;

    container.innerHTML = html;
    container.dataset.built = "true";
}

function renderStatewide(totals, reportingAvg) {

    const container = document.getElementById("statewide");

    const grandTotal = Object.values(totals).reduce((a, b) => a + b, 0);
    const sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]);

    ensureStatewideBuilt(container, sorted.map(([name]) => name));

    const divider = container.querySelector("hr");

    // Create any brand-new candidates first (rare, but possible).
    for (const [name] of sorted) {

        if (!container.querySelector(`[data-candidate="${CSS.escape(name)}"]`)) {

            const el = document.createElement("div");
            el.className = "statewide-candidate";
            el.dataset.candidate = name;
            el.innerHTML = statewideCandidateHtml(name);
            container.insertBefore(el, divider);
        }
    }

    // Only touch DOM order if the standings actually changed — moving
    // a node, even back to the same spot, makes browsers restart its
    // CSS animations, which was replaying growBar on every refresh.
    const currentOrder = Array.from(container.querySelectorAll(".statewide-candidate"))
        .map(el => el.dataset.candidate);

    const desiredOrder = sorted.map(([name]) => name);

    const orderChanged = currentOrder.length !== desiredOrder.length ||
        currentOrder.some((name, i) => name !== desiredOrder[i]);

    if (orderChanged) {
        for (const name of desiredOrder) {
            const el = container.querySelector(`[data-candidate="${CSS.escape(name)}"]`);
            if (el) container.insertBefore(el, divider);
        }
    }

    for (const [name, votes] of sorted) {

        const el = container.querySelector(`[data-candidate="${CSS.escape(name)}"]`);

        if (!el) continue;

        const pct = grandTotal > 0 ? (votes / grandTotal) * 100 : 0;

        el.querySelector(".statewide-votes").textContent = `${votes.toLocaleString()} votes`;
        el.querySelector(".statewide-percent").textContent = `${pct.toFixed(1)}%`;
        el.querySelector(".progress-fill").style.width = `${pct.toFixed(1)}%`;
    }

    container.querySelector(".reporting-box span").textContent = `${Math.round(reportingAvg)}%`;

    const headerReporting = document.getElementById("header-reporting");

    if (headerReporting) {
        headerReporting.textContent = `${Math.round(reportingAvg)}% reporting`;
    }
}

// --------------------
// County Results List
// --------------------

let feedView = "batches";
let countySort = "alpha";
let cachedLatestData = null;
let countyLastUpdated = {};

function computeCountyLastUpdated(history) {

    const map = {};

    // Walking oldest-to-newest and overwriting as we go means each
    // county ends up mapped to its most recent *changed* entry.
    for (const comparison of history) {

        for (const countyName in comparison.counties) {

            const county = comparison.counties[countyName];

            const changed = Object.values(county.candidates)
                .some(c => c.change !== 0);

            if (changed) {
                map[countyName] = comparison.timestamp;
            }
        }
    }

    return map;
}

function renderCountyList() {

    const container = document.getElementById("county-list");

    if (!cachedLatestData?.counties) {
        return;
    }

    const counties = cachedLatestData.counties;

    const rows = Object.entries(counties).map(([countyName, county]) => {

        const total = Object.values(county.candidates)
            .reduce((sum, c) => sum + c.votes, 0);

        const leader = county.leader;
        const pct = total > 0 ? (leader.votes / total) * 100 : 0;

        return {
            key: countyName,
            displayName: countyName.replaceAll("_", " ").toUpperCase(),
            leaderName: leader.name,
            votes: leader.votes,
            pct,
            marginVotes: leader.margin_votes,
            marginPercent: leader.margin_percent * 100,
            color: candidateColor(leader.name),
            updated: countyLastUpdated[countyName] || null
        };
    });

    if (countySort === "alpha") {
        rows.sort((a, b) => a.displayName.localeCompare(b.displayName));
    }
    else {
        rows.sort((a, b) => {
            const aTime = a.updated ? new Date(a.updated).getTime() : 0;
            const bTime = b.updated ? new Date(b.updated).getTime() : 0;
            return bTime - aTime;
        });
    }

    container.innerHTML = rows.map(r => `
        <div class="county-result-row">

            <div class="county-result-name">
                ${r.displayName}
            </div>

            <div class="county-result-leader">
                <span class="candidate-color" style="background:${r.color}"></span>
                ${r.leaderName}
                <span class="county-result-margin" style="color:${r.color}">
                    +${r.marginVotes.toLocaleString()} (${r.marginPercent.toFixed(1)}%)
            </span>

            </div>

            <div class="county-result-votes">${r.votes.toLocaleString()} votes</div>

            <div class="county-result-pct">${r.pct.toFixed(1)}%</div>

            <div class="county-result-updated">
                ${r.updated ? timeAgo(r.updated) : "No changes yet"}
            </div>

        </div>
    `).join("");
}

function setFeedView(view) {

    feedView = view;

    document.getElementById("history").classList.toggle("hidden", view !== "batches");
    document.getElementById("county-list").classList.toggle("hidden", view !== "counties");
    document.getElementById("county-sort-toggle").classList.toggle("hidden", view !== "counties");
    document.getElementById("county-filter-select").classList.toggle("hidden", view !== "batches");

    if (view === "counties") {
        renderCountyList();
    }
}

document.getElementById("feed-view-select").addEventListener("change", (event) => {
    setFeedView(event.target.value);
});

document.getElementById("county-sort-toggle").addEventListener("click", () => {

    countySort = countySort === "alpha" ? "latest" : "alpha";

    document.getElementById("county-sort-toggle").textContent =
        countySort === "alpha" ? "Sort: A–Z" : "Sort: Latest";

    renderCountyList();
});

// --------------------
// County Filter (Batches view)
// --------------------

let countyFilter = "all";

// Adds any counties we haven't seen yet as options, without disturbing
// the person's current selection.
function populateCountyFilterOptions(counties) {

    const select = document.getElementById("county-filter-select");
    const existing = new Set(Array.from(select.options).map(o => o.value));

    const sortedNames = Object.keys(counties).sort((a, b) =>
        a.replaceAll("_", " ").localeCompare(b.replaceAll("_", " "))
    );

    for (const name of sortedNames) {

        if (existing.has(name)) {
            continue;
        }

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name.replaceAll("_", " ").toUpperCase();
        select.appendChild(option);
    }
}

function applyCountyFilter() {

    const historyContainer = document.getElementById("history");
    const cards = historyContainer.querySelectorAll(".county-card");

    let anyVisible = false;

    cards.forEach(card => {

        const matches = countyFilter === "all" || card.dataset.county === countyFilter;

        card.classList.toggle("hidden", !matches);

        if (matches) {
            anyVisible = true;
        }
    });

    let noMatchMsg = document.getElementById("county-filter-empty");

    if (!noMatchMsg) {
        noMatchMsg = document.createElement("div");
        noMatchMsg.id = "county-filter-empty";
        noMatchMsg.className = "empty-feed";
        noMatchMsg.textContent = "No batches for this county yet.";
        historyContainer.appendChild(noMatchMsg);
    }

    const showNoMatch = cards.length > 0 && countyFilter !== "all" && !anyVisible;

    noMatchMsg.classList.toggle("hidden", !showNoMatch);
}

document.getElementById("county-filter-select").addEventListener("change", (event) => {
    countyFilter = event.target.value;
    applyCountyFilter();
});

// --------------------
// Refresh Loop
// --------------------

async function refresh() {

    const [latestResponse, historyResponse] = await Promise.all([
        fetch(`${API}/latest`),
        fetch(`${API}/history`)
    ]);
    const latestData = await latestResponse.json();
    const history = await historyResponse.json();

    cachedLatestData = latestData;
    countyLastUpdated = computeCountyLastUpdated(history);

    updateLastUpdated(history);

    if (latestData.counties) {
        const { totals, reportingAvg } = computeStatewideTotals(latestData.counties);
        renderStatewide(totals, reportingAvg);
        populateCountyFilterOptions(latestData.counties);
    }

    // Batches feed stays up to date in the background regardless of
    // which view is showing, so switching views never needs a refetch.
    updateHistoryCards(history);

    if (feedView === "counties") {
        renderCountyList();
    }
}

refresh();

setInterval(refresh, 5000);
