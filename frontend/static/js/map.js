const width = 975;
const height = 610;

const svg = d3.select("#map")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`);

const path = d3.geoPath();

// --------------------
// State configuration
// --------------------

const stateFips = "08"; // Colorado

const stateConfig = {
    "08": {
        rotation: -6
    }
};

// --------------------
// Candidate colors
// --------------------

const candidateColors = {
    "Victor Marx": "#d73027",
    "Barb Kirkmeyer": "#4575b4",
    "Scott Bottoms": "#fdae61"
};

// --------------------
// Globals
// --------------------

let g;

// --------------------
// Initial Load
// --------------------

Promise.all([
    d3.json("/data/counties-10m.json"),
    fetch(`${API}/latest`).then(r => r.json())
]).then(([us, electionData]) => {

    const counties = topojson.feature(us, us.objects.counties);

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

    const rotation = stateConfig[stateFips]?.rotation || 0;

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

    // Live updates every 5 seconds
    setInterval(updateMap, 5000);

});

// --------------------
// Custom Tooltip
// --------------------

const tooltip = d3.select("body")
    .append("div")
    .attr("class", "map-tooltip");

const tooltipNode = tooltip.node();

// Pull a per-candidate vote breakdown out of a county object.
// Adjust this if your /latest data names the field differently.
function getCountyCandidates(county) {

    if (Array.isArray(county.candidates))
        return county.candidates;

    if (county.candidates && typeof county.candidates === "object") {
        return Object.entries(county.candidates).map(([name, c]) => ({
            name,
            votes: c.votes
        }));
    }

    // Fallback: only the leader is known for this county
    return [{ name: county.leader.name, votes: county.leader.votes }];

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

    return `
        <div class="map-tooltip-title">${county.name}</div>
        <div class="map-tooltip-rows">${rows}</div>
        <div class="map-tooltip-footer">${county.reporting.new}% of votes in</div>
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
// Draw Map
// --------------------

function drawMap(stateCounties, electionData) {

    const countyResults = {};

    for (const countyName in electionData.counties) {

        const county = electionData.counties[countyName];

        if (county.fips)
            countyResults[county.fips] = county;
    }

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

// --------------------
// Live Updates
// --------------------

async function updateMap() {

    const response = await fetch(`${API}/latest`);
    const electionData = await response.json();

    const countyResults = {};

    for (const countyName in electionData.counties) {

        const county = electionData.counties[countyName];

        if (county.fips)
            countyResults[county.fips] = county;
    }

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