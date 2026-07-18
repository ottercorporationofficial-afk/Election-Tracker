// --------------------
// Races per state
// --------------------
//
// Add one entry here for every race page you create within a state.
// The landing page (state-landing.js) reads this to render a clickable
// list -- nothing else needs to change when you add a new race.
//
// "path" should match the route you add in server.py for that race's
// page, and "raceKey" should match the key in backend/registry.py.

const STATE_RACES = {

    arizona: [
        {
            path: "/arizona/governor-primary",
            raceKey: "az_governor_republican_primary_2026",
            name: "Governor — Republican Primary 2026"
        }
        // Add more AZ races here as you start tracking them, e.g.:
        // { path: "/arizona/cd1-special", raceKey: "az_cd1_special_2026", name: "CD-1 Special Election" }
    ],

    colorado: [
        {
            path: "/colorado/governor-primary",
            raceKey: "co_governor_primary",
            name: "Governor Primary 2026"
        }
    ]

};
