/* NEEDLE GAUGE WIDGET */
//
// Renders a semicircle gauge with a rotating needle, driven entirely by
// the manually-set "needle" value from the admin panel (never computed
// from vote counts). Reads it from the same /latest response the map
// and statewide panel already use.
//
// Usage: <div id="needle-widget"></div>
// then call initNeedle(raceKey) once the page loads.
//
// Sized via #needle-widget's max-width (set below) -- adjust that one
// value to make the gauge bigger/smaller, everything else scales with it
// since it's all viewBox-relative.

function initNeedle(raceKey) {

    const container = document.getElementById("needle-widget");

    if (!container) return;

    container.style.maxWidth = "420px";
    container.style.margin = "0 auto";

    function buildWidgetHtml() {
        container.innerHTML = `
            <svg viewBox="0 0 300 170" width="100%">
                <path d="M 20 160 A 130 130 0 0 1 280 160" fill="none" stroke="#262b36" stroke-width="24" stroke-linecap="round"></path>
                <line id="needle-pointer" x1="150" y1="160" x2="150" y2="50" stroke="#e8eaed" stroke-width="4" stroke-linecap="round" style="transition: transform 0.6s ease;"></line>
                <circle cx="150" cy="160" r="8" fill="#e8eaed"></circle>
            </svg>
            <div id="needle-labels" style="display:flex; justify-content:space-between; padding: 0 10px;">
                <span id="needle-label-left" style="font-weight:700;"></span>
                <span id="needle-label-right" style="font-weight:700;"></span>
            </div>
            <div id="needle-caption" style="text-align:center; color:var(--muted,#8b93a3); font-size:0.85rem; margin-top:4px;"></div>
        `;
    }

    buildWidgetHtml();

    async function refresh() {

        const response = await fetch(`/latest?race=${encodeURIComponent(raceKey)}`);

        if (!response.ok) {
            console.warn("[needle] /latest request failed:", response.status);
            return;
        }

        const data = await response.json();
        render(data);
    }

    function render(data) {

        const needle = data.needle;

        if (!needle) {
            container.style.display = "none";
            return;
        }

        container.style.display = "";

        // Self-heal: if needle-widget still exists but something else
        // wiped out its children, rebuild our own DOM before touching it.
        if (!document.getElementById("needle-pointer")) {
            buildWidgetHtml();
        }

        const value = Math.max(0, Math.min(100, needle.value));

        // 0 -> -90deg (fully left/away from candidate), 100 -> +90deg
        // (fully toward candidate), 50 -> straight up (toss-up)
        const angle = (value / 100) * 180 - 90;

        // Real candidate color, same resolution logic map.js/app.js use --
        // computed fresh from the data this widget already fetched, so it
        // never depends on another script's timing.
        const candidateColors = (typeof resolveCandidateColors === "function")
            ? resolveCandidateColors(data, {})
            : {};
        const pointerColor = candidateColors[needle.candidate] || "#5da2ff";

        document.getElementById("needle-pointer").style.transform = `rotate(${angle}deg)`;
        document.getElementById("needle-pointer").style.transformOrigin = "150px 160px";
        document.getElementById("needle-pointer").setAttribute("stroke", pointerColor);

        document.getElementById("needle-label-left").textContent =
            value < 50 ? `${needle.candidate} ${(100 - value).toFixed(0)}%` : "";
        document.getElementById("needle-label-right").textContent =
            value >= 50 ? `${needle.candidate} ${value.toFixed(0)}%` : "";
        document.getElementById("needle-caption").textContent =
            value === 50 ? "Toss-up" : `Leaning ${needle.candidate}`;
    }

    refresh();
    setInterval(refresh, 5000);
}
