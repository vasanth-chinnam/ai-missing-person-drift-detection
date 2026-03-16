import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, MapPin, Activity, Bell, Sun, Moon, Heart, Battery, Radio, Settings, X } from 'lucide-react';
import { MapContainer, TileLayer, Circle, CircleMarker, Polyline, Tooltip } from 'react-leaflet';
import { HeatmapLayer } from 'react-leaflet-heatmap-layer-v3';
import 'leaflet/dist/leaflet.css';
import './App.css';

const API_BASE = '/api';

const PERSON_NAMES = {
  P001: "Ravi Kumar",
  P002: "Anita Sharma",
  P003: "Mohan Rao",
};

const COLOR_MAP = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444'
};

export default function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState('P001');
  const [historyData, setHistoryData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [evalData, setEvalData] = useState(null);
  const [mapMode, setMapMode] = useState('live');
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [theme, setTheme] = useState('dark');
  const [wearableData, setWearableData] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [ownerPhone, setOwnerPhone] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [emergencyTriggered, setEmergencyTriggered] = useState(false);

  // Polling for live dashboard & history data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const dashRes = await axios.get(`${API_BASE}/dashboard`);
        if (!dashRes.data || typeof dashRes.data !== 'object' || !Array.isArray(dashRes.data.persons)) return;
        setDashboardData(dashRes.data);

        // Check for emergency (any person with 100% risk)
        const hasEmergency = dashRes.data.persons.some(p => p.risk_score >= 1.0);
        setEmergencyTriggered(hasEmergency);

        if (!dashRes.data.persons.find(p => p.person_id === selectedPersonId)) {
          const firstId = dashRes.data.persons[0]?.person_id;
          if (firstId) setSelectedPersonId(firstId);
        }
        if (selectedPersonId) {
          const histRes = await axios.get(`${API_BASE}/history/${selectedPersonId}`);
          if (histRes.data && typeof histRes.data === 'object') setHistoryData(histRes.data);
        }
        const alertsRes = await axios.get(`${API_BASE}/alerts`);
        setAlerts(alertsRes.data.alerts);
      } catch (err) {
        console.error("Data fetch error", err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [selectedPersonId]);

  // Poll wearable status
  useEffect(() => {
    const fetchWearable = async () => {
      try {
        const res = await axios.get(`${API_BASE}/wearable/status`);
        setWearableData(res.data.devices || []);
      } catch (err) {}
    };
    fetchWearable();
    const interval = setInterval(fetchWearable, 2000);
    return () => clearInterval(interval);
  }, []);

  // Heatmap data
  useEffect(() => {
    if (mapMode === 'heatmap' && selectedPersonId) {
      axios.get(`${API_BASE}/heatmap-data/${selectedPersonId}`)
        .then(res => setHeatmapPoints(res.data.heatmap_points || []))
        .catch(() => {});
    }
  }, [mapMode, selectedPersonId]);

  // Evaluation metrics
  useEffect(() => {
    axios.get(`${API_BASE}/evaluate`).then(res => setEvalData(res.data)).catch(() => {});
  }, []);

  // Load owner settings
  useEffect(() => {
    axios.get(`${API_BASE}/settings/owner`)
      .then(res => { setOwnerPhone(res.data.phone || ''); setOwnerEmail(res.data.email || ''); })
      .catch(() => {});
  }, []);

  const saveOwnerSettings = async () => {
    try {
      await axios.post(`${API_BASE}/settings/owner`, { phone: ownerPhone, email: ownerEmail });
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 3000);
    } catch (err) { console.error(err); }
  };

  if (!dashboardData) {
    return <div style={{ color: 'var(--text-primary)', padding: '20px' }}>Loading Data Stream...</div>;
  }
  const { persons, home, safe_zone_km } = dashboardData;
  if (!persons || !Array.isArray(persons)) {
    return <div style={{ color: 'var(--text-primary)', padding: '20px' }}>Waiting for valid data stream...</div>;
  }

  const highRiskCount = persons.filter(p => p?.risk_level === 'HIGH').length;
  const selectedPerson = persons.find(p => p?.person_id === selectedPersonId);
  const selectedWatch = wearableData.find(d => d.person_id === selectedPersonId && d.device_type === 'smartwatch');
  const selectedTracker = wearableData.find(d => d.person_id === selectedPersonId && d.device_type === 'gps_tracker');

  return (
    <div className={`dashboard-container ${theme === 'light' ? 'light-theme' : ''}`}>

      {/* Emergency Banner */}
      {emergencyTriggered && (
        <div className="emergency-banner">
          🚨 EMERGENCY ALERT SENT — A person has reached 100% risk! Owner notified via SMS/Email.
        </div>
      )}

      {/* Header */}
      <header className="dashboard-header">
        <div className="brand-title">
          <Shield className="brand-icon" size={24} />
          AI Drift Detection
        </div>
        <div className="header-status">
          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Toggle Theme">
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <button className="settings-btn" onClick={() => setShowSettings(true)} title="Owner Settings">
            <Settings size={20} />
          </button>
          <div><span className="pulse-dot"></span> Live Monitoring</div>
          <div>Persons tracked: <strong>{persons.length}</strong></div>
          <div>High risk: <strong style={{color: highRiskCount > 0 ? 'var(--accent-red)' : 'inherit'}}>{highRiskCount}</strong></div>
          <div>Updated: <strong>{new Date(dashboardData.updated_at).toLocaleTimeString()}</strong></div>
        </div>
      </header>

      {/* Owner Settings Modal */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Owner Emergency Contact</h3>
              <button className="modal-close" onClick={() => setShowSettings(false)}><X size={20} /></button>
            </div>
            <div className="modal-body">
              <label>Phone Number (for SMS alerts)</label>
              <input type="tel" value={ownerPhone} onChange={e => setOwnerPhone(e.target.value)} placeholder="+91XXXXXXXXXX" />
              <label>Email (for email alerts)</label>
              <input type="email" value={ownerEmail} onChange={e => setOwnerEmail(e.target.value)} placeholder="owner@example.com" />
              <button className="save-btn" onClick={saveOwnerSettings}>
                {settingsSaved ? '✓ Saved!' : 'Save Settings'}
              </button>
              <p className="modal-note">Emergency alerts are sent automatically when risk score reaches 100%.</p>
            </div>
          </div>
        </div>
      )}

      {/* Left Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-title">Monitored Persons</div>
        {persons.map(p => {
          const name = PERSON_NAMES[p.person_id] || p.person_id;
          const isActive = p.person_id === selectedPersonId;
          const color = COLOR_MAP[p.risk_level];
          return (
            <div key={p.person_id} className={`person-card ${isActive ? 'active' : ''}`} onClick={() => setSelectedPersonId(p.person_id)}>
              <div className="person-header">
                <span className="person-name">{name}</span>
                <span className={`status-badge status-${p.risk_level}`}>{p.risk_level}</span>
              </div>
              <div className="person-stats">
                <div className="stat-item">
                  <span className="stat-label">Distance</span>
                  <span className={`stat-value ${p.dist_km > safe_zone_km ? 'red' : 'green'}`}>{p.dist_km.toFixed(2)} km</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Speed</span>
                  <span className="stat-value">{p.speed ? p.speed.toFixed(1) : 0} km/h</span>
                </div>
              </div>
              <div className="risk-label"><span>Risk Score: {(p.risk_score * 100).toFixed(0)}%</span></div>
              <div className="risk-bar-container">
                <div className="risk-bar" style={{ width: `${p.risk_score * 100}%`, backgroundColor: color }}></div>
              </div>
            </div>
          );
        })}
      </aside>

      {/* Main Map Area */}
      <main className="main-area">
        <div className="map-controls">
          <button className={`control-btn ${mapMode === 'live' ? 'active' : ''}`} onClick={() => setMapMode('live')}>Live Track</button>
          <button className={`control-btn ${mapMode === 'heatmap' ? 'active' : ''}`} onClick={() => setMapMode('heatmap')}>Heatmap</button>
          {selectedPerson && (
            <a href={`https://www.google.com/maps/search/?api=1&query=${selectedPerson.latitude},${selectedPerson.longitude}`}
               target="_blank" rel="noreferrer" className="control-btn"
               style={{marginLeft: 'auto', backgroundColor: '#3b82f6', textDecoration: 'none'}}>
              <MapPin size={16} style={{display:'inline', marginRight:'4px'}}/> Open in Google Maps
            </a>
          )}
        </div>
        <MapContainer center={[home.lat, home.lon]} zoom={15} className="map-container" zoomControl={false}>
          <TileLayer url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png" attribution='&copy; CartoDB' />
          <Circle center={[home.lat, home.lon]} radius={safe_zone_km * 1000}
            pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.08, weight: 2, dashArray: '5, 10' }} />
          <CircleMarker center={[home.lat, home.lon]} radius={8} pathOptions={{ color: '#fff', fillColor: '#10b981', fillOpacity: 1 }}>
            <Tooltip permanent direction="top" className="custom-tooltip">Home</Tooltip>
          </CircleMarker>
          {historyData && historyData.path && mapMode === 'live' && (
            <Polyline positions={historyData.path.map(pt => [pt.latitude, pt.longitude])}
              pathOptions={{ color: COLOR_MAP[selectedPerson?.risk_level || 'LOW'], weight: 3, opacity: 0.6, dashArray: '10, 10' }} />
          )}
          {mapMode === 'heatmap' && heatmapPoints.length > 0 && (
            <HeatmapLayer fitBoundsOnLoad fitBoundsOnUpdate points={heatmapPoints}
              longitudeExtractor={m => m.longitude} latitudeExtractor={m => m.latitude}
              intensityExtractor={m => parseFloat(m.intensity || 1)} />
          )}
          {/* Unselected Persons */}
          {persons.filter(p => p.person_id !== selectedPersonId).map(p => (
            <CircleMarker key={`live-${p.person_id}`} center={[p.latitude, p.longitude]} radius={6}
              pathOptions={{ color: COLOR_MAP[p.risk_level], fillColor: COLOR_MAP[p.risk_level], fillOpacity: 1, weight: 1 }}>
              <Tooltip direction="right">
                <div style={{fontWeight:'bold'}}>{PERSON_NAMES[p.person_id] || p.person_id}</div>
              </Tooltip>
            </CircleMarker>
          ))}
          {/* Selected Person (Always on Top) */}
          {selectedPerson && (
            <CircleMarker key={`live-${selectedPerson.person_id}-sel`} center={[selectedPerson.latitude, selectedPerson.longitude]} radius={10}
              pathOptions={{ color: '#fff', fillColor: COLOR_MAP[selectedPerson.risk_level], fillOpacity: 1, weight: 3 }}>
              <Tooltip direction="right" permanent>
                <div style={{fontWeight:'bold'}}>{PERSON_NAMES[selectedPerson.person_id] || selectedPerson.person_id}</div>
              </Tooltip>
            </CircleMarker>
          )}
        </MapContainer>
      </main>

      {/* Right Sidebar */}
      <aside className="right-sidebar">
        {selectedPerson && (
          <div className="analytics-section">
            <div className="section-title">Risk Score Breakdown</div>
            <div className="chart-card">
              <BreakdownBar label="Distance from home" value={(selectedPerson.sub_scores?.distance || 0) * 100} color="#10b981" />
              <BreakdownBar label="Speed anomaly" value={(selectedPerson.sub_scores?.speed_anomaly || 0) * 100} color="#f59e0b" />
              <BreakdownBar label="Pattern deviation" value={(selectedPerson.sub_scores?.pattern_deviation || 0) * 100} color="#ef4444" />
              <BreakdownBar label="Time of day" value={(selectedPerson.sub_scores?.time_of_day || 0) * 100} color="#3b82f6" />
            </div>
          </div>
        )}

        {/* Wearable Devices */}
        <div className="analytics-section">
          <div className="section-title">Wearable Devices</div>
          <div className="wearable-grid">
            <div className="wearable-card">
              <div className="wearable-icon">⌚</div>
              <div className="wearable-title">SmartWatch</div>
              <div className="wearable-stats">
                <div className="wearable-stat"><Heart size={14} style={{color:'#ef4444'}} /><span>{selectedWatch?.heart_rate_bpm || '--'} bpm</span></div>
                <div className="wearable-stat"><Battery size={14} style={{color: (selectedWatch?.battery_pct||0)<20?'#ef4444':'#10b981'}} /><span>{selectedWatch?.battery_pct?.toFixed(0)||'--'}%</span></div>
                <div className="wearable-stat"><Activity size={14} style={{color:'#3b82f6'}} /><span>{selectedWatch?.steps||0} steps</span></div>
              </div>
              <div className={`wearable-status ${selectedWatch?.is_active?'active':'inactive'}`}>{selectedWatch?.is_active?'● Online':'○ Offline'}</div>
            </div>
            <div className="wearable-card">
              <div className="wearable-icon">📡</div>
              <div className="wearable-title">GPS Tracker</div>
              <div className="wearable-stats">
                <div className="wearable-stat"><Radio size={14} style={{color:'#8b5cf6'}} /><span>{selectedTracker?.signal_strength_pct||'--'}%</span></div>
                <div className="wearable-stat"><Battery size={14} style={{color: (selectedTracker?.battery_pct||0)<20?'#ef4444':'#10b981'}} /><span>{selectedTracker?.battery_pct?.toFixed(0)||'--'}%</span></div>
              </div>
              <div className={`wearable-status ${selectedTracker?.is_active?'active':'inactive'}`}>{selectedTracker?.is_active?'● Online':'○ Offline'}</div>
            </div>
          </div>
        </div>

        {evalData && (
          <div className="analytics-section">
            <div className="section-title">Model Evaluation</div>
            <div className="eval-grid">
              <div className="eval-card"><div className="eval-val">{(evalData.accuracy*100).toFixed(1)}%</div><div className="eval-title">Accuracy</div></div>
              <div className="eval-card"><div className="eval-val">{(evalData.precision*100).toFixed(1)}%</div><div className="eval-title">Precision</div></div>
              <div className="eval-card"><div className="eval-val">{(evalData.recall*100).toFixed(1)}%</div><div className="eval-title">Recall</div></div>
              <div className="eval-card"><div className="eval-val">{(evalData.f1_score*100).toFixed(1)}%</div><div className="eval-title">F1 Score</div></div>
            </div>
          </div>
        )}

        <div className="analytics-section mt-2">
          <div className="section-title">Alert Feed</div>
          <div className="alert-list">
            {alerts.length === 0 ? <div className="text-secondary text-sm">No recent alerts...</div> : null}
            {alerts.filter(a => a.risk_level !== 'LOW').map((alert, idx) => (
              <div key={idx} className={`alert-item ${alert.risk_level}`}>
                <div className="alert-header">{PERSON_NAMES[alert.person_id] || alert.person_id} – {alert.risk_level} RISK</div>
                <div className="alert-body">Person at {(alert.dist_km).toFixed(2)}km from home</div>
                <div className="alert-meta">{new Date(alert.timestamp).toLocaleTimeString()} - Alert recorded</div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

function BreakdownBar({ label, value, color }) {
  const cappedValue = Math.min(Math.max(value, 0), 100);
  return (
    <div className="breakdown-item">
      <span className="breakdown-label">{label}</span>
      <div className="breakdown-progress">
        <div className="breakdown-fill" style={{ width: `${cappedValue}%`, backgroundColor: color }}></div>
      </div>
      <span className="breakdown-value">{cappedValue.toFixed(0)}%</span>
    </div>
  );
}

const StatusIcon = ({ status }) => {
  const color = status === 'HIGH' ? 'var(--accent-red)' : status === 'MEDIUM' ? 'var(--accent-orange)' : 'var(--accent-green)';
  return <Activity size={16} style={{ color }} />;
};
