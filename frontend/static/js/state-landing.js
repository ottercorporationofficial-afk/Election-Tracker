// --------------------
// State landing page renderer
// --------------------
// Reads which state this page is for from <body data-state="...">, looks
// it up in STATE_RACES (state_races.js, loaded before this script), and
// renders a clickable list into #race-list.

(function renderStateLanding() {

    const container = document.getElementById("race-list");

    if (!container) return;

    const state = document.body.dataset.state;
    const races = STATE_RACES[state] || [];

    if (races.length === 0) {
        container.innerHTML = `<p class="no-races">No races currently tracked for this state.</p>`;
        return;
    }

    container.innerHTML = races.map(race => `
        <a class="race-link" href="${race.path}">
            <span class="race-link-name">${race.name}</span>
            <span class="race-link-arrow">→</span>
        </a>
    `).join("");

})();
