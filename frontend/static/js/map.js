// ============================================================
// Election map renderer
//
// Supports one map per page (the common case) or several maps
// on the same page at once. Each call to initElectionMap()
// creates a fully self-contained instance -- its own SVG,
// tooltip, and live-update timer -- so instances never
// interfere with each other.
// ============================================================

const DEFAULT_WIDTH = 975;
const DEFAULT_HEIGHT = 610;

// --------------------
// Color resolution
// --------------------
// Not every data source gives you a curated `color` per candidate the way
// civicapi did -- county sites you scrape yourself will often give you
// just a name (and maybe party), nothing else. Priority per candidate:
//
//   1. `candidateColorOverrides` in mapConfig below -- your manual pick.
//      This is the main tool to use once you're scraping county sites,
//      since there's no API-curated color to rely on. Set it once per
//      race when you wire up that race's scraper.
//   2. a `color` field, if your data source happens to include one
//      (civicapi does; a scraper you write might not)
//   3. PARTY_COLORS -- but ONLY if this candidate is the only one in the
//      race with that party. Two Republicans in a primary will NOT both
//      get red; they fall through to #4 instead, so a primary scraped
//      from a county site (name + party only, no color) still gets
//      visually distinct candidates without you doing anything extra.
//   4. DEFAULT_PALETTE, cycled alphabetically, as the final fallback.

const PARTY_COLORS = {
    "Republican": "#d73027",
    "Democrat": "#4575b4",
    "Independent": "#fdae61",
    "Libertarian": "#eec73a",
    "Green": "#1a9850"
};

const DEFAULT_PALETTE = [
    "#984ea3", // purple
    "#a6761d", // brown
    "#e7298a", // pink
    "#66c2a5", // teal
    "#fdae61", // orange
    "#1a9850"  // green
];

// --------------------
// Map configuration
// --------------------
// Add a new entry here for each map you want to support.
// Reference it by key (e.g. "colorado") wherever you initialize a map.
//
// `candidateColorOverrides` is where you hand-pick colors for a race --
// especially useful once you're scraping county sites yourself and don't
// have a curated `color` field coming through. Key by exact candidate
// name as it appears in your data.
//
//   candidateColorOverrides: {
//       "Victor Marx": "#d73027",
//       "Barb Kirkmeyer": "#4575b4",
//       "Scott Bottoms": "#fdae61"
//   }

const mapConfigs = {
    colorado: {
        fips: "08",
        rotation: -6,
        candidateColorOverrides: {}
    },
    arizona: {
        fips: "04",
        rotation: -7,
        candidateColorOverrides: {}
    }
};

// Pull every known candidate out of the election data. Prefers the
// top-level `candidates` list (authoritative, includes everyone even if
// they're not leading any county) and falls back to scanning counties for
// data shapes that don't have a top-level list.

function getAllCandidates(electionData) {

    if (Array.isArray(electionData.candidates))
        return electionData.candidates;

    const seen = new Map();

    for (const countyName in electionData.counties) {

        const county = electionData.counties[countyName];
        const candidates = Array.isArray(county.candidates)
            ? county.candidates
            : county.candidates && typeof county.candidates === "object"
                ? Object.entries(county.candidates).map(([name, c]) => ({ name, ...c }))
                : [county.leader];

        candidates.forEach(c => seen.set(c.name, c));

    }

    return Array.from(seen.values());

}

// Given the election data + a mapConfig, build the full name -> color
// lookup for this instance, following the priority chain described above.

function resolveCandidateColors(electionData, overrides = {}) {

    const candidates = getAllCandidates(electionData)
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name));

    // Count how many candidates share each party, so we know whether a
    // party color would actually be unambiguous for this race.
    const partyCounts = {};
    candidates.forEach(c => {
        if (c.party) partyCounts[c.party] = (partyCounts[c.party] || 0) + 1;
    });

    const resolved = {};
    let paletteIndex = 0;

    for (const candidate of candidates) {

        const partyIsUnique = candidate.party && partyCounts[candidate.party] === 1;

        if (overrides[candidate.name]) {
            resolved[candidate.name] = overrides[candidate.name];
        } else if (candidate.color) {
            resolved[candidate.name] = candidate.color;
        } else if (partyIsUnique && PARTY_COLORS[candidate.party]) {
            resolved[candidate.name] = PARTY_COLORS[candidate.party];
        } else {
            resolved[candidate.name] = DEFAULT_PALETTE[paletteIndex % DEFAULT_PALETTE.length];
            paletteIndex++;
        }

    }

    return resolved;

}

// --------------------
// Shared county topology (fetched once, reused by every instance)
// --------------------

let countiesPromise = null;

function loadCounties() {
    if (!countiesPromise) {
        countiesPromise = d3.json("/data/counties-10m.json")
            .then(us => topojson.feature(us, us.objects.counties));
    }
    return countiesPromise;
}

// --------------------
// Public entry point
// --------------------
// containerSelector: CSS selector for the element that should hold this map
//                     (e.g. "#map" or "#map-colorado")
// mapKey:            which entry in mapConfigs to render (e.g. "colorado")
// options.width / options.height: optional overrides for this instance

function initElectionMap(containerSelector, mapKey, options = {}) {

    const config = mapConfigs[mapKey];

    if (!config) {
        console.error(`initElectionMap: unknown map key "${mapKey}"`);
        return;
    }

    const width = options.width || DEFAULT_WIDTH;
    const height = options.height || DEFAULT_HEIGHT;
    const stateFips = config.fips;

    // Which backend race (registry.py key) this instance pulls data from.
    // Defaults to whatever /latest returns with no race param (your main
    // civicapi race), but lets you point a specific map instance at a
    // county-scraped race by passing options.race or a data-race attribute.
    const raceKey = options.race || null;
    const latestUrl = raceKey
        ? `${API}/latest?race=${encodeURIComponent(raceKey)}`
        : `${API}/latest`;

    // Resolved per-candidate colors for this instance. Starts empty and
    // gets (re)computed as data comes in, in case new candidates show up
    // between updates. Also published to window.raceColors, keyed by
    // race, so app.js (statewide panel / county list) can use the exact
    // same colors as the map without recomputing them -- safe even with
    // multiple maps on one page since each publishes under its own key.
    let candidateColors = {};

    window.raceColors = window.raceColors || {};
    const colorsKey = raceKey || "default";

    const container = d3.select(containerSelector);

    if (container.empty()) {
        console.error(`initElectionMap: no element matches "${containerSelector}"`);
        return;
    }

    const svg = container
        .append("svg")
        .attr("viewBox", `0 0 ${width} ${height}`);

    const path = d3.geoPath();

    // Each instance gets its own tooltip element so hover state
    // never leaks between maps on the same page.
    const tooltip = d3.select("body")
        .append("div")
        .attr("class", "map-tooltip");

    const tooltipNode = tooltip.node();

    let g;

    // --------------------
    // Tooltip helpers (scoped per instance so candidateColors is correct)
    // --------------------

    function getCountyCandidates(county) {

        if (Array.isArray(county.candidates))
            return county.candidates;

        if (county.candidates && typeof county.candidates === "object") {
            return Object.entries(county.candidates).map(([name, c]) => ({
                name,
                votes: c.votes,
                party: c.party,
                color: c.color
            }));
        }

        // Fallback: only the leader is known for this county
        return [{
            name: county.leader.name,
            votes: county.leader.votes,
            party: county.leader.party,
            color: county.leader.color
        }];

    }

    function tooltipHtml(county) {

        const candidates = getCountyCandidates(county)
            .slice()
            .sort((a, b) => b.votes - a.votes);

        const total = candidates.reduce((sum, c) => sum + c.votes, 0);
        const leaderName = candidates[0]?.name;

        const rows = candidates.map(c => {

            const pct = total > 0 ? (c.votes / total) * 100 : 0;
            const color = candidateColors[c.name] || "#888888";
            const isLeader = c.name === leaderName;

            return `
                <div class="map-tooltip-row">
                    <span class="map-tooltip-dot" style="background:${color}"></span>
                    <span class="map-tooltip-name">
                        ${c.name}${isLeader ? '<span class="map-tooltip-check">✓</span>' : ""}
                    </span>
                    <span class="map-tooltip-votes">${c.votes.toLocaleString()}</span>
                    <span class="map-tooltip-pct">${pct.toFixed(1)}%</span>
                </div>
            `;

        }).join("");

        const reportingText = county.reporting?.new != null
        ? `${county.reporting.new}% of votes in`
        : "Reporting % unavailable";

    return `
            <div class="map-tooltip-title">${county.name}</div>
            <div class="map-tooltip-rows">${rows}</div>
            <div class="map-tooltip-footer">${reportingText}</div>
        `;

    }

    function positionTooltip(event) {

        const offset = 16;
        const rect = tooltipNode.getBoundingClientRect();

        let left = event.clientX + offset;
        let top = event.clientY + offset;

        if (left + rect.width > window.innerWidth - 8)
            left = event.clientX - rect.width - offset;

        if (top + rect.height > window.innerHeight - 8)
            top = event.clientY - rect.height - offset;

        tooltip
            .style("left", `${left}px`)
            .style("top", `${top}px`);

    }

    // --------------------
    // Draw / update
    // --------------------

    function buildCountyResults(electionData) {

        const countyResults = {};

        for (const countyName in electionData.counties) {

            const county = electionData.counties[countyName];

            if (county.fips)
                countyResults[county.fips] = county;
        }

        return countyResults;

    }

    function drawMap(stateCounties, electionData) {

        const countyResults = buildCountyResults(electionData);

        g.selectAll("path")
            .data(stateCounties)
            .join("path")
            .attr("d", path)
            .attr("fill", d => {

                const county = countyResults[d.id];

                if (!county)
                    return "#d9d9d9";

                return candidateColors[county.leader.name] || "#888888";

            })
            .attr("stroke", "#333")
            .attr("stroke-width", 0.5)
            .attr("aria-label", d => {

                const county = countyResults[d.id];
                return county ? `${county.name}: ${county.leader.name} leads` : d.id;

            })
            .on("mouseenter", function (event, d) {

                g.selectAll("path")
                    .attr("stroke", "#333")
                    .attr("stroke-width", 0.5);

                d3.select(this)
                    .raise()
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 0.5);

                const county = countyResults[d.id];

                if (county) {
                    tooltip.html(tooltipHtml(county));
                    positionTooltip(event);
                    tooltip.classed("visible", true);
                }

            })
            .on("mousemove", function (event, d) {

                const county = countyResults[d.id];

                if (county)
                    positionTooltip(event);

            })
            .on("mouseleave", function () {

                d3.select(this)
                    .attr("stroke", "#333")
                    .attr("stroke-width", 0.5);

                tooltip.classed("visible", false);

            });

    }

    async function updateMap() {

        const response = await fetch(latestUrl);
        const electionData = await response.json();

        candidateColors = resolveCandidateColors(electionData, config.candidateColorOverrides);
        window.raceColors[colorsKey] = candidateColors;

        const countyResults = buildCountyResults(electionData);

        g.selectAll("path")
            .transition()
            .duration(500)
            .attr("fill", d => {

                const county = countyResults[d.id];

                if (!county)
                    return "#d9d9d9";

                return candidateColors[county.leader.name] || "#888888";

            });

    }

    // --------------------
    // Initial load
    // --------------------

    Promise.all([
        loadCounties(),
        fetch(latestUrl).then(r => r.json())
    ]).then(([counties, electionData]) => {

        const stateCounties = counties.features.filter(
            d => d.id.startsWith(stateFips)
        );

        // --------------------
        // Auto Center / Scale
        // --------------------

        const bounds = path.bounds({
            type: "FeatureCollection",
            features: stateCounties
        });

        const padding = 30;

        const dx = bounds[1][0] - bounds[0][0];
        const dy = bounds[1][1] - bounds[0][1];

        const scale = Math.min(
            (width - padding * 2) / dx,
            (height - padding * 2) / dy
        );

        const centerX = (bounds[0][0] + bounds[1][0]) / 2;
        const centerY = (bounds[0][1] + bounds[1][1]) / 2;

        const translateX = width / 2 - scale * centerX;
        const translateY = height / 2 - scale * centerY;

        const rotation = config.rotation || 0;

        candidateColors = resolveCandidateColors(electionData, config.candidateColorOverrides);
        window.raceColors[colorsKey] = candidateColors;

        g = svg.append("g")
            .attr(
                "transform",
                `
                translate(${translateX},${translateY})
                scale(${scale})
                rotate(${rotation} ${centerX} ${centerY})
                `
            );

        drawMap(stateCounties, electionData);

        // Live updates every 5 seconds, scoped to this instance
        setInterval(updateMap, 5000);

    });

}

// ============================================================
// Auto-init
// ============================================================
// Add data-election-map="<key>" to any container element and it will be
// picked up automatically on page load -- no per-page JS needed.
// Add data-race="<key>" too if this map should pull from a specific
// backend race (registry.py key) instead of the default.
//
//   Single map page:   <div id="map" data-election-map="colorado"></div>
//
//   County-scraped race:
//                       <div id="map" data-election-map="colorado" data-race="my_new_race"></div>
//
//   Multi map page:    <div id="map-co" data-election-map="colorado"></div>
//                       <div id="map-az" data-election-map="arizona"></div>
//
// If you'd rather call it manually (e.g. to pass custom width/height),
// use initElectionMap("#your-selector", "colorado", { width: 800, height: 500, race: "my_new_race" })
// and skip the data-election-map attribute on that element.

document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll("[data-election-map]").forEach(el => {

        const mapKey = el.getAttribute("data-election-map");
        const raceKey = el.getAttribute("data-race");

        if (!el.id) {
            console.error("initElectionMap: element with data-election-map needs an id", el);
            return;
        }

        initElectionMap(`#${el.id}`, mapKey, raceKey ? { race: raceKey } : {});

    });

});
