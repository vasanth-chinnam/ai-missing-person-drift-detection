/* ═══════════════════════════════════════════════════════════
   DriftGuard AI — Frontend Application
   ═══════════════════════════════════════════════════════════ */

const API = "http://localhost:5000/api";

// ── State ───────────────────────────────────────────────────
let gpsData = [];
let alertsData = [];
let statsData = {};
let personsData = [];
let geofenceData = {};
let map, heatLayer, markersLayer, geofenceCircle;
let liveIndex = 0;
let liveTimer = null;
let chartsInitialized = false;
let heatVisible = true;
let riskChart, vitalsChart, distChart, distroChart;

// ── Boot ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initRouter();
  fetchAll();
});

// ── Router ──────────────────────────────────────────────────
function initRouter() {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      navigateTo(page);
    });
  });
}

function navigateTo(page) {
  // Update nav
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navEl) navEl.classList.add("active");

  // Update pages
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) {
    pageEl.classList.remove("active");
    // force reflow for animation
    void pageEl.offsetWidth;
    pageEl.classList.add("active");
  }

  // Page-specific init
  if (page === "dashboard" && map) setTimeout(() => map.invalidateSize(), 100);
  if (page === "analytics" && !chartsInitialized && gpsData.length) initCharts();
}

// ── API Fetch ───────────────────────────────────────────────
async function fetchAll() {
  try {
    const [gpsRes, alertsRes, statsRes, personsRes, geoRes] = await Promise.all([
      fetch(`${API}/gps-data`),
      fetch(`${API}/alerts`),
      fetch(`${API}/stats`),
      fetch(`${API}/persons`),
      fetch(`${API}/geofence`),
    ]);
    gpsData = await gpsRes.json();
    alertsData = await alertsRes.json();
    statsData = await statsRes.json();
    personsData = await personsRes.json();
    geofenceData = await geoRes.json();

    renderStats();
    initMap();
    startLiveSimulation();
    renderAlertFeed();
    renderAlertsTable();
    renderPersons();
    loadGeofenceSettings();
    updateAlertBadge();
  } catch (err) {
    console.error("Failed to fetch data:", err);
  }
}

// ── Stats Cards ─────────────────────────────────────────────
function renderStats() {
  animateValue("val-total", statsData.totalPoints || 0);
  animateValue("val-risk", statsData.highRisk || 0);
  animateValue("val-drift", statsData.driftCount || 0);
  animateValue("val-persons", statsData.activePersons || 0);
}

function animateValue(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let current = 0;
  const step = Math.max(1, Math.floor(target / 30));
  const timer = setInterval(() => {
    current += step;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = current;
  }, 25);
}

// ── Map ─────────────────────────────────────────────────────
function initMap() {
  if (map) return;
  if (!gpsData.length) return;

  const center = [gpsData[0].latitude, gpsData[0].longitude];
  map = L.map("map", {
    center,
    zoom: 14,
    zoomControl: true,
    attributionControl: false,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
  }).addTo(map);

  // Heat layer
  const heatPoints = gpsData.map((p) => [p.latitude, p.longitude, p.risk / 100]);
  heatLayer = L.heatLayer(heatPoints, {
    radius: 25,
    blur: 20,
    maxZoom: 17,
    gradient: { 0.2: "#10b981", 0.5: "#f59e0b", 0.8: "#ef4444", 1.0: "#dc2626" },
  }).addTo(map);

  // Markers layer group
  markersLayer = L.layerGroup().addTo(map);

  // Geofence circle
  geofenceCircle = L.circle([geofenceData.lat, geofenceData.lon], {
    radius: geofenceData.radius,
    color: "#3b82f6",
    fillColor: "#3b82f6",
    fillOpacity: 0.06,
    weight: 1.5,
    dashArray: "8 4",
  }).addTo(map);

  // Toggle heat button
  document.getElementById("btn-toggle-heat").addEventListener("click", () => {
    heatVisible = !heatVisible;
    if (heatVisible) heatLayer.addTo(map);
    else map.removeLayer(heatLayer);
  });
}

// ── Live Simulation ─────────────────────────────────────────
function startLiveSimulation() {
  if (liveTimer) clearInterval(liveTimer);
  liveIndex = 0;
  updateLivePoint();
  liveTimer = setInterval(() => {
    liveIndex = (liveIndex + 1) % gpsData.length;
    updateLivePoint();
  }, 1500);
}

function updateLivePoint() {
  const point = gpsData[liveIndex];
  if (!point || !map) return;

  // Update marker
  markersLayer.clearLayers();

  const color = point.level === "critical" ? "#ef4444" : point.level === "warning" ? "#f59e0b" : "#10b981";

  const pulseIcon = L.divIcon({
    className: "custom-marker",
    html: `<div style="
      width: 18px; height: 18px; border-radius: 50%;
      background: ${color};
      box-shadow: 0 0 0 6px ${color}33, 0 0 20px ${color}66;
      animation: markerPulse 1.5s ease-in-out infinite;
    "></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

  L.marker([point.latitude, point.longitude], { icon: pulseIcon }).addTo(markersLayer);

  // Smooth pan
  map.panTo([point.latitude, point.longitude], { animate: true, duration: 0.8 });

  // Update gauge
  updateGauge(point.risk, point.level);
}

// ── Gauge ───────────────────────────────────────────────────
function updateGauge(risk, level) {
  const arc = document.getElementById("gauge-arc");
  const valEl = document.getElementById("gauge-value");
  const labelEl = document.getElementById("gauge-label");

  const maxDash = 251.3;
  const dashLen = (risk / 100) * maxDash;
  arc.setAttribute("stroke-dasharray", `${dashLen} ${maxDash}`);

  valEl.textContent = risk;

  labelEl.textContent = level === "critical" ? "HIGH RISK" : level === "warning" ? "WARNING" : "SAFE";
  labelEl.className = "gauge-label " + level;
}

// ── Alert Feed (Dashboard) ──────────────────────────────────
function renderAlertFeed() {
  const feed = document.getElementById("alert-feed");
  if (!alertsData.length) return;

  const recent = alertsData.slice(-8).reverse();
  feed.innerHTML = recent
    .map(
      (a) => `
    <div class="alert-item">
      <div class="alert-dot ${a.level}"></div>
      <div class="alert-item-content">
        <div class="alert-item-msg">${a.message}</div>
        <div class="alert-item-time">Risk: ${a.risk}/100 · ${formatTime(a.timestamp)}</div>
      </div>
    </div>
  `
    )
    .join("");
}

function updateAlertBadge() {
  const badge = document.getElementById("alert-badge");
  if (badge) badge.textContent = alertsData.length;
}

// ── Alerts Table ────────────────────────────────────────────
function renderAlertsTable(filter = "all") {
  const tbody = document.getElementById("alerts-tbody");
  let data = alertsData;
  if (filter !== "all") data = data.filter((a) => a.level === filter);

  tbody.innerHTML = data
    .map(
      (a) => `
    <tr>
      <td><span class="severity-badge ${a.level}">${a.level}</span></td>
      <td>${formatTime(a.timestamp)}</td>
      <td>${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}</td>
      <td><strong>${a.risk}</strong>/100</td>
      <td>${a.message}</td>
    </tr>
  `
    )
    .join("");

  if (!data.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No alerts found</td></tr>`;
  }
}

// Filter buttons
document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderAlertsTable(btn.dataset.filter);
  });
});

// ── Persons ─────────────────────────────────────────────────
function renderPersons() {
  const grid = document.getElementById("persons-grid");
  grid.innerHTML = personsData
    .map(
      (p) => `
    <div class="card person-card">
      <div class="person-avatar">${p.avatar}</div>
      <div class="person-info">
        <div class="person-name">${p.name}</div>
        <div class="person-meta">
          <span>Age: ${p.age}</span>
          <span>${p.condition}</span>
        </div>
      </div>
      <span class="person-status ${p.status}">${p.status}</span>
    </div>
  `
    )
    .join("");
}

// Modal
const modalOverlay = document.getElementById("modal-overlay");
document.getElementById("btn-add-person").addEventListener("click", () => {
  modalOverlay.classList.add("show");
});

document.getElementById("modal-close").addEventListener("click", () => {
  modalOverlay.classList.remove("show");
});

modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) modalOverlay.classList.remove("show");
});

document.getElementById("form-add-person").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("inp-name").value;
  const age = parseInt(document.getElementById("inp-age").value, 10);
  const condition = document.getElementById("inp-condition").value;

  try {
    const res = await fetch(`${API}/persons`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, age, condition }),
    });
    const person = await res.json();
    personsData.push(person);
    renderPersons();
    modalOverlay.classList.remove("show");
    e.target.reset();
    animateValue("val-persons", personsData.length);
  } catch (err) {
    console.error("Failed to add person:", err);
  }
});

// ── Charts ──────────────────────────────────────────────────
function initCharts() {
  if (chartsInitialized) return;
  chartsInitialized = true;

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } },
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748b", font: { family: "Inter", size: 10 }, maxTicksLimit: 12 },
        grid: { color: "rgba(255,255,255,0.04)" },
      },
      y: {
        ticks: { color: "#64748b", font: { family: "Inter", size: 10 } },
        grid: { color: "rgba(255,255,255,0.04)" },
      },
    },
  };

  const labels = gpsData.map((_, i) => i);

  // Risk over time
  riskChart = new Chart(document.getElementById("chart-risk"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Risk Score",
          data: gpsData.map((p) => p.risk),
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.1)",
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      ...chartDefaults,
      scales: {
        ...chartDefaults.scales,
        y: { ...chartDefaults.scales.y, min: 0, max: 100 },
      },
    },
  });

  // Speed & Heart Rate
  vitalsChart = new Chart(document.getElementById("chart-vitals"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Speed (km/h)",
          data: gpsData.map((p) => p.speed.toFixed(1)),
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59,130,246,0.1)",
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
          yAxisID: "y",
        },
        {
          label: "Heart Rate (bpm)",
          data: gpsData.map((p) => p.heartRate),
          borderColor: "#ec4899",
          backgroundColor: "rgba(236,72,153,0.1)",
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      ...chartDefaults,
      scales: {
        x: chartDefaults.scales.x,
        y: { ...chartDefaults.scales.y, position: "left" },
        y1: {
          ...chartDefaults.scales.y,
          position: "right",
          grid: { drawOnChartArea: false },
        },
      },
    },
  });

  // Distribution (doughnut)
  const safe = gpsData.filter((p) => p.level === "safe").length;
  const warn = gpsData.filter((p) => p.level === "warning").length;
  const crit = gpsData.filter((p) => p.level === "critical").length;

  distroChart = new Chart(document.getElementById("chart-distribution"), {
    type: "doughnut",
    data: {
      labels: ["Safe", "Warning", "Critical"],
      datasets: [
        {
          data: [safe, warn, crit],
          backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          borderWidth: 0,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#94a3b8", font: { family: "Inter", size: 11 }, padding: 16 },
        },
      },
    },
  });

  // Movement distance
  distChart = new Chart(document.getElementById("chart-distance"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Distance from Safe Zone (m)",
          data: gpsData.map((p) => p.distance),
          backgroundColor: gpsData.map((p) =>
            p.level === "critical"
              ? "rgba(239,68,68,0.6)"
              : p.level === "warning"
              ? "rgba(245,158,11,0.6)"
              : "rgba(16,185,129,0.4)"
          ),
          borderRadius: 3,
          borderSkipped: false,
        },
      ],
    },
    options: {
      ...chartDefaults,
      plugins: {
        ...chartDefaults.plugins,
        legend: { display: false },
      },
    },
  });
}

// ── Settings ────────────────────────────────────────────────
function loadGeofenceSettings() {
  document.getElementById("set-lat").value = geofenceData.lat;
  document.getElementById("set-lon").value = geofenceData.lon;
  document.getElementById("set-radius").value = geofenceData.radius;
  document.getElementById("radius-display").textContent = geofenceData.radius;
}

document.getElementById("set-radius").addEventListener("input", (e) => {
  document.getElementById("radius-display").textContent = e.target.value;
});

document.getElementById("btn-save-geofence").addEventListener("click", async () => {
  const lat = parseFloat(document.getElementById("set-lat").value);
  const lon = parseFloat(document.getElementById("set-lon").value);
  const radius = parseInt(document.getElementById("set-radius").value, 10);

  try {
    const res = await fetch(`${API}/geofence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, radius }),
    });
    geofenceData = await res.json();

    // Update circle on map
    if (geofenceCircle && map) {
      geofenceCircle.setLatLng([lat, lon]);
      geofenceCircle.setRadius(radius);
    }

    // Flash button
    const btn = document.getElementById("btn-save-geofence");
    btn.textContent = "✓ Saved!";
    setTimeout(() => (btn.textContent = "Save Geofence"), 2000);
  } catch (err) {
    console.error("Failed to save geofence:", err);
  }
});

// ── Utilities ───────────────────────────────────────────────
function formatTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// Inject marker pulse animation
const style = document.createElement("style");
style.textContent = `
  @keyframes markerPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.3); }
  }
`;
document.head.appendChild(style);
