// --------------------
// Race Registry
// --------------------
//
// Add one entry here for every race page you create. Every page that
// includes this script (see colorado.html for the pattern) will pick
// up the new link automatically — nothing else needs to change.

const RACES = [
    { path: "/colorado", name: "Colorado" },
    { path: "/arizona", name: "Arizona"},
    // { path: "/texas", name: "Texas" },
];

// --------------------
// Render
// --------------------

(function renderNav() {

    const nav = document.querySelector(".top-nav");

    if (!nav) {
        return;
    }

    const currentPath = window.location.pathname;

    nav.innerHTML = RACES.map(race => {

        const isActive = race.path === currentPath;

        return `<a href="${race.path}" class="top-nav-link${isActive ? " active" : ""}">${race.name}</a>`;

    }).join("");

})();
