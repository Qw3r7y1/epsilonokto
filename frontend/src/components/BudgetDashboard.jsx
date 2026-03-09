import { useState, useEffect, useCallback } from "react";

const API_BASE = "/api/vs/v1";

const ENTRY_TYPES = ["spend", "revenue", "refund", "allocation"];

const CATEGORIES = [
  "claude_api",
  "serpapi",
  "hosting",
  "ads",
  "domain",
  "tools",
  "stripe_fees",
  "content",
  "other",
];

const PODS = [
  "affiliate",
  "digital_product",
  "lead_gen",
  "micro_saas",
  "trend_media",
];

const ENTRY_COLORS = {
  spend: "#E57373",
  revenue: "#81C784",
  refund: "#FFB74D",
  allocation: "#64B5F6",
};

function formatUSD(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function UtilizationBar({ pct }) {
  const color = pct > 90 ? "#E57373" : pct > 70 ? "#FFB74D" : "#81C784";
  return (
    <div
      style={{
        background: "#0B1D0F",
        borderRadius: 6,
        height: 10,
        width: "100%",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${Math.min(pct, 100)}%`,
          height: "100%",
          background: color,
          borderRadius: 6,
          transition: "width 0.5s ease",
        }}
      />
    </div>
  );
}

export default function BudgetDashboard() {
  const [budget, setBudget] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");

  // Ledger form state
  const [form, setForm] = useState({
    experiment_id: "",
    entry_type: "spend",
    amount_usd: "",
    category: "claude_api",
    description: "",
    agent_name: "",
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [budgetRes, govRes, ledgerRes, expRes] = await Promise.all([
        fetch(`${API_BASE}/governance/budget`),
        fetch(`${API_BASE}/governance/status`),
        fetch(`${API_BASE}/governance/ledger?limit=50`),
        fetch(`${API_BASE}/experiments`),
      ]);

      if (!budgetRes.ok || !govRes.ok || !ledgerRes.ok || !expRes.ok) {
        throw new Error("Failed to fetch data from API");
      }

      setBudget(await budgetRes.json());
      setGovernance(await govRes.json());
      setLedger(await ledgerRes.json());
      setExperiments(await expRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        entry_type: form.entry_type,
        amount_usd: parseFloat(form.amount_usd),
        category: form.category,
        description: form.description,
        experiment_id: form.experiment_id || null,
        agent_name: form.agent_name || null,
      };
      const res = await fetch(`${API_BASE}/governance/ledger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || "Failed to create entry");
      }
      setForm({
        experiment_id: "",
        entry_type: "spend",
        amount_usd: "",
        category: "claude_api",
        description: "",
        agent_name: "",
      });
      await fetchAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const cardStyle = {
    background: "#0B1D0F",
    borderRadius: 12,
    padding: "20px 24px",
    border: "1px solid #2D6A4F",
  };

  const labelStyle = {
    fontFamily: "'Space Mono', monospace",
    fontSize: 10,
    letterSpacing: 2,
    color: "#52B788",
    textTransform: "uppercase",
    marginBottom: 4,
  };

  const bigNumStyle = {
    fontFamily: "'Space Mono', monospace",
    fontSize: 26,
    fontWeight: 700,
  };

  const inputStyle = {
    width: "100%",
    padding: "10px 12px",
    background: "#0B1D0F",
    border: "1px solid #2D6A4F",
    borderRadius: 8,
    color: "#E8F5E9",
    fontFamily: "'DM Sans', sans-serif",
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
  };

  const selectStyle = {
    ...inputStyle,
    appearance: "none",
    cursor: "pointer",
  };

  if (loading) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "80px 20px",
          color: "#52B788",
          fontSize: 14,
          fontFamily: "'Space Mono', monospace",
        }}
      >
        Loading budget data...
      </div>
    );
  }

  if (error && !budget) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "80px 20px",
          color: "#E57373",
          fontSize: 14,
        }}
      >
        <p style={{ marginBottom: 12 }}>
          Could not connect to Venture Studio API
        </p>
        <p style={{ fontSize: 12, color: "#95D5B2" }}>{error}</p>
        <button
          onClick={fetchAll}
          style={{
            marginTop: 16,
            padding: "8px 20px",
            background: "#2D6A4F",
            border: "none",
            borderRadius: 8,
            color: "#E8F5E9",
            cursor: "pointer",
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Section Nav */}
      <div
        style={{
          display: "flex",
          gap: 4,
          marginBottom: 24,
        }}
      >
        {[
          { id: "overview", label: "Overview" },
          { id: "new-entry", label: "New Entry" },
          { id: "ledger", label: "Ledger" },
          { id: "governance", label: "Governance" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 11,
              letterSpacing: 1,
              textTransform: "uppercase",
              padding: "8px 16px",
              border: `1px solid ${activeSection === tab.id ? "#52B788" : "#2D6A4F"}`,
              borderRadius: 8,
              cursor: "pointer",
              background: activeSection === tab.id ? "#2D6A4F" : "transparent",
              color: activeSection === tab.id ? "#D8F3DC" : "#52B788",
              transition: "all 0.2s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div
          style={{
            background: "#3E1010",
            border: "1px solid #E57373",
            borderRadius: 8,
            padding: "10px 16px",
            marginBottom: 16,
            color: "#E57373",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {/* ── Overview Section ────────────────────────────────── */}
      {activeSection === "overview" && budget && (
        <div style={{ animation: "fadeIn 0.3s ease" }}>
          {/* Summary Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div style={cardStyle}>
              <div style={labelStyle}>Total Spend</div>
              <div style={{ ...bigNumStyle, color: "#E57373" }}>
                {formatUSD(budget.total_spend)}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Total Revenue</div>
              <div style={{ ...bigNumStyle, color: "#81C784" }}>
                {formatUSD(budget.total_revenue)}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Net P&L</div>
              <div
                style={{
                  ...bigNumStyle,
                  color: budget.net >= 0 ? "#81C784" : "#E57373",
                }}
              >
                {formatUSD(budget.net)}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Daily Spend</div>
              <div style={{ ...bigNumStyle, color: "#FFB74D" }}>
                {formatUSD(budget.daily_spend)}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "#74C69D",
                  marginTop: 4,
                  fontFamily: "'Space Mono', monospace",
                }}
              >
                of {formatUSD(budget.daily_limit)} limit
              </div>
            </div>
          </div>

          {/* Utilization Bar */}
          <div style={{ ...cardStyle, marginBottom: 24 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 8,
              }}
            >
              <span style={labelStyle}>Daily Budget Utilization</span>
              <span
                style={{
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 14,
                  fontWeight: 700,
                  color:
                    budget.budget_utilization_pct > 90
                      ? "#E57373"
                      : budget.budget_utilization_pct > 70
                        ? "#FFB74D"
                        : "#81C784",
                }}
              >
                {budget.budget_utilization_pct.toFixed(1)}%
              </span>
            </div>
            <UtilizationBar pct={budget.budget_utilization_pct} />
          </div>

          {/* Experiments Budget Table */}
          {experiments.length > 0 && (
            <div style={cardStyle}>
              <div style={{ ...labelStyle, marginBottom: 12 }}>
                Experiment Budgets
              </div>
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 13,
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid #2D6A4F",
                        color: "#74C69D",
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 10,
                        letterSpacing: 1.5,
                        textTransform: "uppercase",
                      }}
                    >
                      <th style={{ textAlign: "left", padding: "8px 8px 8px 0" }}>
                        Experiment
                      </th>
                      <th style={{ textAlign: "left", padding: 8 }}>Pod</th>
                      <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                      <th style={{ textAlign: "right", padding: 8 }}>
                        Allocated
                      </th>
                      <th style={{ textAlign: "right", padding: 8 }}>Spent</th>
                      <th style={{ textAlign: "right", padding: "8px 0 8px 8px" }}>
                        Revenue
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments.map((exp) => (
                      <tr
                        key={exp.id}
                        style={{ borderBottom: "1px solid #1B4332" }}
                      >
                        <td
                          style={{
                            padding: "10px 8px 10px 0",
                            color: "#D8F3DC",
                            fontWeight: 500,
                            maxWidth: 200,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {exp.title}
                        </td>
                        <td style={{ padding: 8, color: "#95D5B2" }}>
                          {exp.pod}
                        </td>
                        <td style={{ padding: 8 }}>
                          <span
                            style={{
                              background: "#1B4332",
                              padding: "2px 8px",
                              borderRadius: 12,
                              fontSize: 11,
                              color: "#74C69D",
                              fontFamily: "'Space Mono', monospace",
                            }}
                          >
                            {exp.status}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: 8,
                            textAlign: "right",
                            fontFamily: "'Space Mono', monospace",
                            color: "#64B5F6",
                          }}
                        >
                          {formatUSD(exp.budget_allocated)}
                        </td>
                        <td
                          style={{
                            padding: 8,
                            textAlign: "right",
                            fontFamily: "'Space Mono', monospace",
                            color: "#E57373",
                          }}
                        >
                          {formatUSD(exp.budget_spent)}
                        </td>
                        <td
                          style={{
                            padding: "10px 0 10px 8px",
                            textAlign: "right",
                            fontFamily: "'Space Mono', monospace",
                            color: "#81C784",
                          }}
                        >
                          {formatUSD(exp.revenue_total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── New Ledger Entry Form ───────────────────────────── */}
      {activeSection === "new-entry" && (
        <div style={{ ...cardStyle, animation: "fadeIn 0.3s ease" }}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>
            Record Budget Entry
          </div>
          <form onSubmit={handleSubmit}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 16,
                marginBottom: 16,
              }}
            >
              {/* Entry Type */}
              <div>
                <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                  Entry Type
                </label>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {ENTRY_TYPES.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setForm({ ...form, entry_type: t })}
                      style={{
                        padding: "6px 14px",
                        borderRadius: 20,
                        border: `1px solid ${ENTRY_COLORS[t]}`,
                        background:
                          form.entry_type === t ? ENTRY_COLORS[t] + "33" : "transparent",
                        color: ENTRY_COLORS[t],
                        cursor: "pointer",
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 11,
                        letterSpacing: 0.5,
                        textTransform: "uppercase",
                        transition: "all 0.2s",
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Amount */}
              <div>
                <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                  Amount (USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={form.amount_usd}
                  onChange={(e) =>
                    setForm({ ...form, amount_usd: e.target.value })
                  }
                  placeholder="0.00"
                  style={inputStyle}
                />
              </div>

              {/* Category */}
              <div>
                <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                  Category
                </label>
                <select
                  value={form.category}
                  onChange={(e) =>
                    setForm({ ...form, category: e.target.value })
                  }
                  style={selectStyle}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </div>

              {/* Experiment */}
              <div>
                <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                  Experiment (optional)
                </label>
                <select
                  value={form.experiment_id}
                  onChange={(e) =>
                    setForm({ ...form, experiment_id: e.target.value })
                  }
                  style={selectStyle}
                >
                  <option value="">-- None --</option>
                  {experiments.map((exp) => (
                    <option key={exp.id} value={exp.id}>
                      {exp.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Description */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                Description
              </label>
              <input
                type="text"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder="e.g. Claude API calls for niche scoring"
                style={inputStyle}
              />
            </div>

            {/* Agent Name */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ ...labelStyle, display: "block", marginBottom: 6 }}>
                Agent Name (optional)
              </label>
              <input
                type="text"
                value={form.agent_name}
                onChange={(e) =>
                  setForm({ ...form, agent_name: e.target.value })
                }
                placeholder="e.g. scout-agent"
                style={inputStyle}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: "12px 32px",
                background: submitting
                  ? "#2D6A4F"
                  : "linear-gradient(135deg, #2D6A4F, #40916C)",
                border: "none",
                borderRadius: 8,
                color: "#E8F5E9",
                fontFamily: "'Space Mono', monospace",
                fontSize: 13,
                letterSpacing: 1,
                cursor: submitting ? "not-allowed" : "pointer",
                transition: "all 0.2s",
                opacity: submitting ? 0.6 : 1,
              }}
            >
              {submitting ? "Submitting..." : "Record Entry"}
            </button>
          </form>
        </div>
      )}

      {/* ── Ledger Section ──────────────────────────────────── */}
      {activeSection === "ledger" && (
        <div style={{ ...cardStyle, animation: "fadeIn 0.3s ease" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 16,
            }}
          >
            <div style={labelStyle}>Recent Ledger Entries</div>
            <button
              onClick={fetchAll}
              style={{
                padding: "4px 12px",
                background: "transparent",
                border: "1px solid #2D6A4F",
                borderRadius: 6,
                color: "#52B788",
                cursor: "pointer",
                fontFamily: "'Space Mono', monospace",
                fontSize: 10,
              }}
            >
              Refresh
            </button>
          </div>

          {ledger.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px 20px",
                color: "#52B788",
                fontSize: 14,
              }}
            >
              No ledger entries yet. Use "New Entry" to record your first budget
              entry.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid #2D6A4F",
                      color: "#74C69D",
                      fontFamily: "'Space Mono', monospace",
                      fontSize: 10,
                      letterSpacing: 1.5,
                      textTransform: "uppercase",
                    }}
                  >
                    <th style={{ textAlign: "left", padding: "8px 8px 8px 0" }}>
                      Date
                    </th>
                    <th style={{ textAlign: "left", padding: 8 }}>Type</th>
                    <th style={{ textAlign: "right", padding: 8 }}>Amount</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Category</th>
                    <th style={{ textAlign: "left", padding: 8 }}>
                      Description
                    </th>
                    <th style={{ textAlign: "left", padding: "8px 0 8px 8px" }}>
                      Agent
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((entry) => (
                    <tr
                      key={entry.id}
                      style={{ borderBottom: "1px solid #1B4332" }}
                    >
                      <td
                        style={{
                          padding: "10px 8px 10px 0",
                          color: "#95D5B2",
                          whiteSpace: "nowrap",
                          fontSize: 12,
                        }}
                      >
                        {formatDate(entry.created_at)}
                      </td>
                      <td style={{ padding: 8 }}>
                        <span
                          style={{
                            background: (ENTRY_COLORS[entry.entry_type] || "#52B788") + "22",
                            border: `1px solid ${ENTRY_COLORS[entry.entry_type] || "#52B788"}`,
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 10,
                            color: ENTRY_COLORS[entry.entry_type] || "#52B788",
                            fontFamily: "'Space Mono', monospace",
                            textTransform: "uppercase",
                            letterSpacing: 0.5,
                          }}
                        >
                          {entry.entry_type}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: 8,
                          textAlign: "right",
                          fontFamily: "'Space Mono', monospace",
                          fontWeight: 600,
                          color: ENTRY_COLORS[entry.entry_type] || "#D8F3DC",
                        }}
                      >
                        {formatUSD(entry.amount_usd)}
                      </td>
                      <td
                        style={{
                          padding: 8,
                          color: "#B7E4C7",
                        }}
                      >
                        {entry.category.replace(/_/g, " ")}
                      </td>
                      <td
                        style={{
                          padding: 8,
                          color: "#95D5B2",
                          maxWidth: 200,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {entry.description || "—"}
                      </td>
                      <td
                        style={{
                          padding: "10px 0 10px 8px",
                          color: "#74C69D",
                          fontSize: 12,
                          fontFamily: "'Space Mono', monospace",
                        }}
                      >
                        {entry.agent_name || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Governance Section ──────────────────────────────── */}
      {activeSection === "governance" && governance && (
        <div style={{ animation: "fadeIn 0.3s ease" }}>
          {/* Kill Switch */}
          <div
            style={{
              ...cardStyle,
              marginBottom: 16,
              borderColor: governance.kill_switch ? "#E57373" : "#2D6A4F",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div style={labelStyle}>Kill Switch</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    color: governance.kill_switch ? "#E57373" : "#81C784",
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  {governance.kill_switch ? "ACTIVE — All agents halted" : "OFF — System running normally"}
                </div>
              </div>
              <div
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: governance.kill_switch ? "#E57373" : "#81C784",
                  boxShadow: `0 0 12px ${governance.kill_switch ? "#E57373" : "#81C784"}44`,
                }}
              />
            </div>
          </div>

          {/* Governance Limits */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <div style={cardStyle}>
              <div style={labelStyle}>Active Pod</div>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: "#D8F3DC",
                  textTransform: "capitalize",
                }}
              >
                {governance.active_pod.replace(/_/g, " ")}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Daily Spend Limit</div>
              <div style={{ ...bigNumStyle, fontSize: 20, color: "#FFB74D" }}>
                {formatUSD(governance.max_daily_spend)}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Per-Experiment Limit</div>
              <div style={{ ...bigNumStyle, fontSize: 20, color: "#64B5F6" }}>
                {formatUSD(governance.max_experiment_spend)}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Max Concurrent</div>
              <div style={{ ...bigNumStyle, fontSize: 20, color: "#D8F3DC" }}>
                {governance.max_concurrent_experiments}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={labelStyle}>Circuit Breaker</div>
              <div style={{ ...bigNumStyle, fontSize: 20, color: "#E57373" }}>
                {governance.circuit_breaker_threshold} failures
              </div>
            </div>
          </div>

          {/* Agent Status */}
          {governance.agents_enabled && Object.keys(governance.agents_enabled).length > 0 && (
            <div style={cardStyle}>
              <div style={{ ...labelStyle, marginBottom: 12 }}>
                Agent Status
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                  gap: 8,
                }}
              >
                {Object.entries(governance.agents_enabled).map(
                  ([name, enabled]) => (
                    <div
                      key={name}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 12px",
                        background: "#1B4332",
                        borderRadius: 8,
                      }}
                    >
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: enabled ? "#81C784" : "#E57373",
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          fontSize: 12,
                          color: enabled ? "#B7E4C7" : "#E57373",
                          fontFamily: "'Space Mono', monospace",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {name}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
