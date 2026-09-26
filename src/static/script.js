// --------------------- # Page Elements and Trace State # ---------------------------------- //

const traceForm = document.getElementById("trace-form");
const traceButton = document.getElementById("trace-button");
const targetInput = document.getElementById("target-input");
const hopList = document.getElementById("hop-list");
const statusText = document.getElementById("trace-status");
const stateLabel = document.getElementById("trace-state");
const fitButton = document.getElementById("fit-route");
const state = { source: null, hops: [], selected: null, follow: true,
    segments: [], animationFrame: null, timeout: null };
const MAX_MAP_ZOOM = 9; // Keep geolocation at city/region scale.
const SEGMENT_DURATION = 1600; // Visual travel time, independent of measured RTT.
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const playbackStatus = document.getElementById("playback-status");

// --------------------- # Hop Colors # ---------------------------------- //

function hopColor(number) {
    // Golden-angle spacing gives successive hops distinct, stable colors.
    return `hsl(${Math.round((number - 1) * 137.508) % 360}, 65%, 40%)`;
}
// --------------------- # Map Setup and Route Layers # ---------------------------------- //

const map = L.map("map", { zoomControl: false, maxZoom: MAX_MAP_ZOOM }).setView([20, 0], 2);
L.control.zoom({ position: "bottomleft" }).addTo(map);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
}).addTo(map);
const routeLines = L.layerGroup().addTo(map);
const locationLeaders = L.layerGroup().addTo(map);
const markerLayer = L.layerGroup().addTo(map);

// --------------------- # Trace Status and Reset # ---------------------------------- //

function setStatus(message, label, isError = false) {
    statusText.textContent = message;
    stateLabel.textContent = label;
    stateLabel.classList.toggle("error", isError);
    stateLabel.classList.toggle("live", label === "Tracing");
}

function resetTrace() {
    cancelAnimationFrame(state.animationFrame);
    state.animationFrame = null;
    state.segments = [];
    playbackStatus.hidden = true;
    markerLayer.clearLayers();
    routeLines.clearLayers();
    locationLeaders.clearLayers();
    state.hops = [];
    state.selected = null;
    state.follow = true;
    document.getElementById("hop-inspector").hidden = true;
    hopList.replaceChildren();
    document.getElementById("empty-state").hidden = false;
    updateSummary();
    map.setView([20, 0], 2);
}

function finishTrace(message, failed = false, label = failed ? "Error" : "Finished") {
    clearTimeout(state.timeout);
    state.timeout = null;
    // Closing explicitly prevents EventSource from reconnecting and starting another trace.
    state.source?.close();
    state.source = null;
    traceButton.disabled = false;
    targetInput.readOnly = false;
    traceButton.textContent = "Trace route ↗";
    setStatus(message, label, failed);
}

// --------------------- # Start Trace and Receive Live SSE Events # ---------------------------------- //

function startTrace(event) {
    event.preventDefault();
    if (state.source) return;
    const target = targetInput.value.trim();
    if (!target) {
        setStatus("Enter a website or IPv4 address.", "Error", true);
        targetInput.focus();
        return;
    }
    resetTrace();
    traceButton.disabled = true;
    targetInput.readOnly = true;
    traceButton.textContent = "Tracing…";
    setStatus(`Tracing ${target} · waiting for hops…`, "Tracing");
    try {
        const source = new EventSource(`/trace?target=${encodeURIComponent(target)}`);
        state.source = source;
        // Last-resort UI deadline if a proxy/server never sends a terminal event.
        state.timeout = setTimeout(() => {
            if (state.source === source) finishTrace("Trace timed out after 45 seconds. Partial hops are preserved.", true, "Timed out");
        }, 45000);
        source.onmessage = (message) => {
            if (state.source !== source) return;
            try {
                addHop(JSON.parse(message.data));
            } catch (error) {
                finishTrace("Received invalid hop data. Please try again.", true);
            }
        };
        source.addEventListener("hop-update", event => {
            if (state.source !== source) return;
            try { updateHop(JSON.parse(event.data)); }
            catch (_) { finishTrace("Received invalid enrichment data. Please try again.", true); }
        });
        source.addEventListener("complete", event => {
            if (state.source !== source) return;
            try {
                const result = JSON.parse(event.data);
                const labels = { success: "Reached", timeout: "Timed out", unresponsive: "Stopped", hop_limit: "Hop limit", incomplete: "Incomplete", error: "Error" };
                finishTrace(result.message, result.status === "error" || result.status === "timeout", labels[result.status] || "Finished");
            } catch (_) { finishTrace("Could not read the trace outcome.", true); }
        });
        source.addEventListener("trace-error", (event) => {
            if (state.source !== source) return;
            let message = "The trace failed. Please try again.";
            try { message = JSON.parse(event.data).message || message; } catch (_) { /* Use the fallback. */ }
            finishTrace(message, true);
        });
        source.onerror = () => {
            if (state.source === source) finishTrace("Connection lost. Your received hops are preserved; try a new trace.", true);
        };
    } catch (error) {
        finishTrace("Unable to start the live connection. Please try again.", true);
    }
}

// --------------------- # Hop Coordinates and Descriptions # ---------------------------------- //

function realCoordinates(hop) {
    const { latitude, longitude } = hop;
    return Number.isFinite(latitude) && Number.isFinite(longitude)
        && Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180
        ? L.latLng(latitude, longitude) : null;
}

function hopDescription(hop, mapped) {
    if (!hop.IP) return "No response";
    if (hop.asn === "Private") return "Private network · not mapped";
    return mapped ? [hop.city, hop.region, hop.country].filter(Boolean).join(", ") || "Approximate location" : "Location unavailable";
}

// --------------------- # Hop Details and Popup Content # ---------------------------------- //

function textElement(tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;
    element.className = className;
    return element;
}

function popupContent(hop) {
    const content = document.createElement("div");
    content.append(textElement("strong", `Hop ${hop.number}`));
    if (!hop.IP) {
        content.append(textElement("p", "No reply arrived before the probe timeout. Routers normally reply when a probe’s TTL expires, but a firewall, ICMP filtering, rate limiting, packet loss, or a router configured not to reply can prevent that response. This trace cannot determine the exact cause; it does not prove the router or website is down."));
    } else if (hop.asn === "Private" || hop.asn === "Special") {
        content.append(textElement("p", "This is a non-public network address. It has no reliable public map location."));
    } else if (!realCoordinates(hop)) {
        content.append(textElement("p", hop.enrichment_status === "timeout" ? "Location/network lookup exceeded its 4-second limit. The router replied, but enrichment timed out." : "The router replied, but its location is pending or unavailable from the location provider."));
    }
    // Network names are external data: textContent keeps them from becoming HTML.
    for (const [label, value] of Object.entries({
        IP: hop.IP, Hostname: hop.hostname, ASN: hop.asn, Organization: hop.organization,
        City: hop.city, Region: hop.region, Country: hop.country,
        "Average RTT (ms)": hop.AvgLatency,
        "Real latitude": hop.latitude, "Real longitude": hop.longitude
    })) content.append(textElement("div", `${label}: ${value ?? "N/A"}`));
    return content;
}

// --------------------- # Add Live Hops and Update Enrichment # ---------------------------------- //

function addHop(hop) {
    if (!hop || !Number.isInteger(hop.number) || hop.number < 1) throw new Error("Invalid hop");
    const real = realCoordinates(hop);
    const entry = { hop, real, display: real, marker: null, button: null };
    const row = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hop-item";
    button.style.setProperty("--hop-color", hopColor(hop.number));
    button.setAttribute("aria-pressed", "false");
    button.append(textElement("span", hop.number, "hop-number"));
    const details = textElement("span", "", "hop-details");
    details.append(textElement("strong", hop.IP || "No response"));
    details.append(textElement("span", hop.organization || "Unknown network"));
    details.append(textElement("small", hopDescription(hop, !!real)));
    button.append(details, textElement("span", Number.isFinite(hop.AvgLatency) ? `${hop.AvgLatency} ms` : "—", "latency"));
    button.addEventListener("click", () => selectHop(entry, true));
    entry.button = button;
    row.append(button);
    hopList.append(row);
    attachMarker(entry);
    const previous = state.hops.filter(item => item.real).at(-1);
    state.hops.push(entry);
    if (real && previous) createSegment(previous, entry);
    document.getElementById("empty-state").hidden = true;
    updateSummary();
    if (state.follow) fitRoute();
    renderRoute();
    startRouteAnimation();
}

function attachMarker(entry) {
    if (entry.real) {
        const icon = L.divIcon({ className: "route-node", html: String(entry.hop.number), iconSize: [30, 30], iconAnchor: [15, 15] });
        entry.marker = L.marker(entry.real, { icon, title: `Hop ${entry.hop.number}`, riseOnHover: true })
            .addTo(markerLayer).bindPopup(popupContent(entry.hop), { autoPan: false });
        entry.marker.getElement().style.setProperty("--hop-color", hopColor(entry.hop.number));
        entry.marker.on("click", () => selectHop(entry, false));
    }
}

function updateHop(hop) {
    const entry = state.hops.find(item => item.hop.number === hop.number);
    if (!entry) return;
    entry.hop = hop;
    entry.real = realCoordinates(hop);
    entry.display = entry.real;
    const details = entry.button.querySelector(".hop-details");
    details.children[1].textContent = hop.organization || "Unknown network";
    details.children[2].textContent = hopDescription(hop, !!entry.real);
    if (entry.real && !entry.marker) {
        attachMarker(entry);
        const index = state.hops.indexOf(entry);
        const previous = state.hops.slice(0, index).filter(item => item.real).at(-1);
        if (previous) createSegment(previous, entry);
    }
    updateSummary();
    if (state.follow) fitRoute();
    renderRoute();
    startRouteAnimation();
    if (state.selected === entry) {
        entry.marker?.getElement()?.classList.add("selected");
        showHopDetails(entry);
    }
}

// --------------------- # Hop Selection and Sidebar Interaction # ---------------------------------- //

function showHopDetails(entry) {
    const inspector = document.getElementById("hop-inspector");
    document.getElementById("hop-inspector-content").replaceChildren(popupContent(entry.hop));
    inspector.hidden = false;
}

function updateSummary() {
    const mapped = state.hops.filter(entry => entry.real).length;
    document.getElementById("hop-count").textContent = `${state.hops.length} hops · ${mapped} mapped`;
    fitButton.disabled = mapped === 0;
}

function selectHop(entry, fromPanel) {
    state.follow = false;
    state.selected = entry;
    showHopDetails(entry);
    for (const item of state.hops) {
        const selected = item === entry;
        item.button.classList.toggle("selected", selected);
        item.button.setAttribute("aria-pressed", String(selected));
        item.marker?.getElement()?.classList.toggle("selected", selected);
    }
    if (entry.marker) {
        if (fromPanel) map.panTo(entry.display);
        entry.marker.openPopup();
    } else map.closePopup();
    if (!fromPanel) entry.button.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// --------------------- # Map Bounds and Overlapping Hop Positions # ---------------------------------- //

function fitRoute() {
    const points = state.hops.filter(entry => entry.real).map(entry => entry.real);
    if (!points.length) return;
    map.fitBounds(L.latLngBounds(points), {
        paddingTopLeft: [60, 60],
        paddingBottomRight: [60, 60],
        maxZoom: 8, animate: false
    });
}

function renderRoute() {
    locationLeaders.clearLayers();
    const placed = [];
    for (const entry of state.hops) {
        if (!entry.real) continue;
        const origin = map.project(entry.real);
        let point = origin;
        // Spread nearby markers in screen pixels; the original geolocation stays untouched.
        // Recalculate on zoom so the numbers remain separated at every scale.
        let attempt = 0;
        while (placed.some(other => point.distanceTo(other) < 36)) {
            attempt += 1;
            const angle = attempt * 2.39996;
            const radius = 22 * Math.sqrt(attempt);
            point = origin.add(L.point(Math.cos(angle) * radius, Math.sin(angle) * radius));
        }
        placed.push(point);
        entry.display = map.unproject(point);
        entry.marker.setLatLng(entry.display);
        if (point.distanceTo(origin) > 1) {
            L.polyline([entry.real, entry.display], { color: "#64748b", weight: 1, opacity: 0.6, interactive: false }).addTo(locationLeaders);
        }
    }
    // Reproject existing segments after zoom without restarting their animation.
    for (const segment of state.segments) drawSegment(segment);
}

// --------------------- # Route Lines and Drawing Animation # ---------------------------------- //

function createSegment(from, to) {
    const gap = to.hop.number - from.hop.number > 1;
    const outline = L.polyline([], { color: "#fff", weight: 7, opacity: 0.85, interactive: false }).addTo(routeLines);
    const line = L.polyline([], {
        color: hopColor(to.hop.number), weight: 3, opacity: 1,
        dashArray: gap ? "5, 8" : null, interactive: false
    }).addTo(routeLines);
    state.segments.push({ from, to, outline, line, progress: 0, startedAt: null });
}

function drawSegment(segment) {
    if (segment.progress === 0) {
        segment.outline.setLatLngs([]);
        segment.line.setLatLngs([]);
        return;
    }
    const start = map.project(segment.from.display);
    const end = map.project(segment.to.display);
    // Interpolate in map pixels so the growing tip follows the displayed line.
    const tip = start.add(end.subtract(start).multiplyBy(segment.progress));
    const coordinates = [segment.from.display, map.unproject(tip)];
    segment.outline.setLatLngs(coordinates);
    segment.line.setLatLngs(coordinates);
}

function startRouteAnimation() {
    if (state.animationFrame !== null || !state.segments.some(segment => segment.progress < 1)) return;
    playbackStatus.hidden = false;
    state.animationFrame = requestAnimationFrame(animateRoute);
}

function animateRoute(now) {
    state.animationFrame = null;
    const segment = state.segments.find(item => item.progress < 1);
    if (!segment) {
        playbackStatus.hidden = true;
        return;
    }
    if (reducedMotion.matches) {
        for (const item of state.segments) {
            item.progress = 1;
            drawSegment(item);
        }
        playbackStatus.hidden = true;
        return;
    }
    if (segment.startedAt === null) segment.startedAt = now;
    const elapsed = Math.min((now - segment.startedAt) / SEGMENT_DURATION, 1);
    segment.progress = elapsed * elapsed * (3 - 2 * elapsed);
    drawSegment(segment);
    state.animationFrame = requestAnimationFrame(animateRoute);
}

// --------------------- # Page and Map Event Listeners # ---------------------------------- //

traceForm.addEventListener("submit", startTrace);
fitButton.addEventListener("click", () => { state.follow = true; fitRoute(); });
map.on("zoomend", renderRoute);
map.on("dragstart", () => { state.follow = false; });

map.on("resize", () => { if (state.follow) fitRoute(); });

document.getElementById("close-hop-inspector").addEventListener("click", () => { document.getElementById("hop-inspector").hidden = true; });
