import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AlertTriangle, Check, Database, Lock, RefreshCw, Upload, X } from "lucide-react";
import "./styles.css";

const rawBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const API_BASE = rawBase.startsWith("http") ? rawBase : `https://${rawBase}`;

function App() {
  const [summary, setSummary] = useState(null);
  const [activities, setActivities] = useState([]);
  const [batches, setBatches] = useState([]);
  const [sources, setSources] = useState([]);
  const [filters, setFilters] = useState({ status: "", source_type: "", flagged: "" });
  const [selectedSource, setSelectedSource] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    const [summaryRes, activitiesRes, batchesRes, sourcesRes] = await Promise.all([
      fetch(`${API_BASE}/api/summary/`),
      fetch(`${API_BASE}/api/activities/?${params}`),
      fetch(`${API_BASE}/api/batches/`),
      fetch(`${API_BASE}/api/sources/`),
    ]);
    const [summaryJson, activitiesJson, batchesJson, sourcesJson] = await Promise.all([
      summaryRes.json(),
      activitiesRes.json(),
      batchesRes.json(),
      sourcesRes.json(),
    ]);
    setSummary(summaryJson);
    setActivities(activitiesJson.results || activitiesJson);
    setBatches(batchesJson.results || batchesJson);
    setSources(sourcesJson.results || sourcesJson);
    setBusy(false);
  }

  useEffect(() => {
    load();
  }, [filters.status, filters.source_type, filters.flagged]);

  async function transition(id, action) {
    await fetch(`${API_BASE}/api/activities/${id}/${action}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "demo analyst" }),
    });
    load();
  }

  async function uploadFile(event) {
    event.preventDefault();
    if (!selectedSource || !selectedFile) return;
    const data = new FormData();
    data.append("source_id", selectedSource);
    data.append("file", selectedFile);
    setBusy(true);
    await fetch(`${API_BASE}/api/upload/`, { method: "POST", body: data });
    setSelectedFile(null);
    await load();
  }

  const totals = useMemo(() => {
    return summary?.scope_totals?.reduce((acc, row) => {
      acc[row.scope] = Number(row.co2e || 0);
      return acc;
    }, {}) || {};
  }, [summary]);

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">Breathe ESG ingestion prototype</p>
          <h1>{summary?.tenant || "Analyst review queue"}</h1>
        </div>
        <button className="iconButton" onClick={load} disabled={busy} title="Refresh data">
          <RefreshCw size={18} />
        </button>
      </header>

      <section className="metrics">
        <Metric label="Rows ingested" value={summary?.total_rows ?? "-"} />
        <Metric label="Flagged rows" value={summary?.flagged_rows ?? "-"} tone="warn" />
        <Metric label="Scope 1 kg CO2e" value={formatNumber(totals.scope_1)} />
        <Metric label="Scope 2 kg CO2e" value={formatNumber(totals.scope_2)} />
        <Metric label="Scope 3 kg CO2e" value={formatNumber(totals.scope_3)} />
      </section>

      <section className="workspace">
        <aside className="panel">
          <div className="panelTitle">
            <Database size={18} />
            Sources
          </div>
          {sources.map((source) => (
            <button
              key={source.id}
              className={filters.source_type === source.source_type ? "source active" : "source"}
              onClick={() =>
                setFilters((prev) => ({
                  ...prev,
                  source_type: prev.source_type === source.source_type ? "" : source.source_type,
                }))
              }
            >
              <span>{source.name}</span>
              <small>{source.ingestion_mode}</small>
            </button>
          ))}

          <form className="upload" onSubmit={uploadFile}>
            <label>
              Source
              <select value={selectedSource} onChange={(event) => setSelectedSource(event.target.value)}>
                <option value="">Select source</option>
                {sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.source_type}
                  </option>
                ))}
              </select>
            </label>
            <label>
              CSV file
              <input type="file" accept=".csv" onChange={(event) => setSelectedFile(event.target.files?.[0])} />
            </label>
            <button className="primary" type="submit" disabled={!selectedFile || !selectedSource || busy}>
              <Upload size={16} />
              Upload
            </button>
          </form>
        </aside>

        <section className="review">
          <div className="filters">
            <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="locked">Locked</option>
            </select>
            <select value={filters.flagged} onChange={(event) => setFilters({ ...filters, flagged: event.target.value })}>
              <option value="">All quality states</option>
              <option value="true">Flagged only</option>
              <option value="false">Clean only</option>
            </select>
          </div>

          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Activity</th>
                  <th>Quantity</th>
                  <th>CO2e</th>
                  <th>Status</th>
                  <th>Flags</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((activity) => (
                  <tr key={activity.id}>
                    <td>{labelSource(activity.source_type)}</td>
                    <td>
                      <strong>{activity.category}</strong>
                      <span>{activity.description}</span>
                    </td>
                    <td>
                      {formatNumber(activity.quantity)} {activity.unit}
                      <small>
                        from {formatNumber(activity.original_quantity)} {activity.original_unit}
                      </small>
                    </td>
                    <td>{formatNumber(activity.co2e_kg)} kg</td>
                    <td>
                      <span className={`pill ${activity.review_status}`}>{activity.review_status}</span>
                    </td>
                    <td>
                      {activity.quality_flags.length ? (
                        <div className="flags">
                          <AlertTriangle size={16} />
                          {activity.quality_flags.join("; ")}
                        </div>
                      ) : (
                        <span className="muted">Clear</span>
                      )}
                    </td>
                    <td>
                      <div className="actions">
                        <button title="Approve row" onClick={() => transition(activity.id, "approve")}>
                          <Check size={16} />
                        </button>
                        <button title="Reject row" onClick={() => transition(activity.id, "reject")}>
                          <X size={16} />
                        </button>
                        <button title="Lock approved row" onClick={() => transition(activity.id, "lock")}>
                          <Lock size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <section className="batches">
        <h2>Recent batches</h2>
        <div className="batchGrid">
          {batches.slice(0, 6).map((batch) => (
            <article key={batch.id} className="batch">
              <strong>{batch.filename}</strong>
              <span>{batch.source.name}</span>
              <small>
                {batch.row_count} rows, {batch.warning_count} warnings, {batch.failed_count} failed
              </small>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value, tone }) {
  return (
    <article className={`metric ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(Number(value));
}

function labelSource(source) {
  return { sap: "SAP", utility: "Utility", travel: "Travel" }[source] || source;
}

createRoot(document.getElementById("root")).render(<App />);
