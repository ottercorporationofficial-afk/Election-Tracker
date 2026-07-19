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
    { path: "/chat", name: "Otter AI"}
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

    const links = RACES.map(race => {

        const isActive = race.path === currentPath;

        return `<a href="${race.path}" class="top-nav-link${isActive ? " active" : ""}">${race.name}</a>`;

    });

    // Purely a client-side convenience: reaching /admin at all already
    // required passing Basic Auth (admin.html sets this flag on load).
    // This just decides whether to SHOW a link -- it grants no actual
    // access by itself, since /admin still requires the real password
    // to load anything.
    if (localStorage.getItem("otter_admin_logged_in") === "true") {

        const isActive = currentPath === "/admin";

        links.push(
            `<a href="/admin" class="top-nav-link${isActive ? " active" : ""}">Admin</a>`
        );

        links.push(
            `<a href="#" class="top-nav-link" onclick="localStorage.removeItem('otter_admin_logged_in'); location.reload(); return false;">Log out</a>`
        );
    }

    nav.innerHTML = links.join("");

})();
