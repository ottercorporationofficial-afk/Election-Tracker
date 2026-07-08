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
    d3.json("/static/data/counties-10m.json"),
    fetch("/latest").then(r => r.json())
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
        .append("title")
        .text(d => {

            const county = countyResults[d.id];

            if (!county)
                return d.id;

            return `${county.name}
Leader: ${county.leader.name}
Votes: ${county.leader.votes}
Reporting: ${county.reporting.new}%`;

        });

}

// --------------------
// Live Updates
// --------------------

async function updateMap() {

    const response = await fetch("/latest");
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