import { useState, useCallback } from "react";

const API_BASE = "/api/vs/v1";

// ── Pre-built initial investment template ────────────────────────────
// Covers a realistic Venture Studio seed with categories matching the
// existing BudgetLedger category taxonomy.

const INVESTMENT_CATEGORIES = [
  {
    id: "infra",
    label: "Infrastructure & Hosting",
    category: "hosting",
    items: [
      { name: "VPS / Cloud compute (3 months)", default: 150 },
      { name: "Domain registrations (5 domains)", default: 60 },
      { name: "Cloudflare R2 storage", default: 25 },
      { name: "Redis / DB managed hosting", default: 50 },
    ],
    color: "#64B5F6",
  },
  {
    id: "ai",
    label: "AI & API Credits",
    category: "claude_api",
    items: [
      { name: "Anthropic Claude API credits", default: 200 },
      { name: "SerpAPI search credits", default: 50 },
      { name: "OpenAI Whisper / TTS credits", default: 75 },
    ],
    color: "#CE93D8",
  },
  {
    id: "tools",
    label: "Tools & Subscriptions",
    category: "tools",
    items: [
      { name: "ElevenLabs voice plan", default: 99 },
      { name: "Sync Labs lip-sync credits", default: 100 },
      { name: "Analytics / monitoring", default: 30 },
      { name: "Dev tooling (CI/CD, testing)", default: 25 },
    ],
    color: "#FFB74D",
  },
  {
    id: "content",
    label: "Content & Creative",
    category: "content",
    items: [
      { name: "Landing page assets / design", default: 150 },
      { name: "Copywriting / content creation", default: 100 },
      { name: "Stock media / licenses", default: 50 },
    ],
    color: "#81C784",
  },
  {
    id: "ads",
    label: "Distribution & Ads",
    category: "ads",
    items: [
      { name: "Paid ad testing budget (Meta/Google)", default: 300 },
      { name: "Social media boosting", default: 100 },
      { name: "Influencer / partnership seeds", default: 150 },
    ],
    color: "#E57373",
  },
  {
    id: "fees",
    label: "Payments & Fees",
    category: "stripe_fees",
    items: [
      { name: "Stripe setup + reserves", default: 25 },
      { name: "Legal / compliance basics", default: 100 },
      { name: "Contingency buffer", default: 200 },
    ],
    color: "#90A4AE",
  },
];

function formatUSD(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function InitialInvestment({ onComplete }) {
  // Build initial amounts from defaults
  const buildInitial = () => {
    const amounts = {};
    INVESTMENT_CATEGORIES.forEach((cat) => {
      cat.items.forEach((item, i) => {
        amounts[`${cat.id}-${i}`] = item.default;
      });
    });
    return amounts;
  };

  const [amounts, setAmounts] = useState(buildInitial);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [expandedCat, setExpandedCat] = useState(null);

  const setAmount = (key, value) => {
    setAmounts((prev) => ({ ...prev, [key]: value }));
  };

  const getCategoryTotal = (cat) => {
    return cat.items.reduce((sum, _, i) => {
      return sum + (parseFloat(amounts[`${cat.id}-${i}`]) || 0);
    }, 0);
  };

  const grandTotal = INVESTMENT_CATEGORIES.reduce(
    (sum, cat) => sum + getCategoryTotal(cat),
    0,
  );

  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      // Create one allocation ledger entry per category
      const entries = INVESTMENT_CATEGORIES.map((cat) => {
        const total = getCategoryTotal(cat);
        const itemDetails = cat.items
          .map((item, i) => {
            const amt = parseFloat(amounts[`${cat.id}-${i}`]) || 0;
            return amt > 0 ? `${item.name}: $${amt}` : null;
          })
          .filter(Boolean)
          .join(", ");

        return {
          entry_type: "allocation",
          amount_usd: total,
          category: cat.category,
          description: `Initial investment — ${cat.label}: ${itemDetails}`,
          experiment_id: null,
          agent_name: null,
        };
      }).filter((e) => e.amount_usd > 0);

      for (const entry of entries) {
        const res = await fetch(`${API_BASE}/governance/ledger`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry),
        });
        if (!res.ok) {
          const detail = await res.json();
          throw new Error(detail.detail || "Failed to create ledger entry");
        }
      }

      setSubmitted(true);
      if (onComplete) onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }, [amounts, onComplete]);

  const resetToDefaults = () => {
    setAmounts(buildInitial());
    setSubmitted(false);
    setError(null);
  };

  const cardStyle = {
    background: "#0B1D0F",
    borderRadius: 12,
    border: "1px solid #2D6A4F",
    overflow: "hidden",
  };

  const labelStyle = {
    fontFamily: "'Space Mono', monospace",
    fontSize: 10,
    letterSpacing: 2,
    color: "#52B788",
    textTransform: "uppercase",
  };

  if (submitted) {
    return (
      <div style={{ animation: "fadeIn 0.3s ease" }}>
        <div
          style={{
            ...cardStyle,
            padding: "48px 32px",
            textAlign: "center",
            border: "1px solid #81C784",
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>&#x2705;</div>
          <h2
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 20,
              color: "#D8F3DC",
              margin: "0 0 8px 0",
            }}
          >
            Investment Recorded
          </h2>
          <p style={{ fontSize: 14, color: "#95D5B2", margin: "0 0 4px 0" }}>
            {formatUSD(grandTotal)} allocated across{" "}
            {INVESTMENT_CATEGORIES.filter((c) => getCategoryTotal(c) > 0).length}{" "}
            categories
          </p>
          <p style={{ fontSize: 12, color: "#74C69D", margin: "0 0 24px 0" }}>
            Entries created in the budget ledger as allocations.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
            <button
              onClick={resetToDefaults}
              style={{
                padding: "10px 24px",
                background: "transparent",
                border: "1px solid #2D6A4F",
                borderRadius: 8,
                color: "#95D5B2",
                cursor: "pointer",
                fontFamily: "'Space Mono', monospace",
                fontSize: 12,
              }}
            >
              Record Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ animation: "fadeIn 0.3s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 18,
            color: "#D8F3DC",
            margin: "0 0 6px 0",
          }}
        >
          Initial Investment Plan
        </h2>
        <p style={{ fontSize: 13, color: "#95D5B2", margin: 0, maxWidth: 600 }}>
          Configure your startup capital allocation. Adjust amounts per line
          item, then submit to record allocations in the budget ledger.
        </p>
      </div>

      {/* Grand Total Bar */}
      <div
        style={{
          ...cardStyle,
          padding: "20px 24px",
          marginBottom: 20,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <div style={labelStyle}>Total Investment</div>
          <div
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 32,
              fontWeight: 700,
              color: "#D8F3DC",
            }}
          >
            {formatUSD(grandTotal)}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          {INVESTMENT_CATEGORIES.map((cat) => {
            const catTotal = getCategoryTotal(cat);
            const pct = grandTotal > 0 ? ((catTotal / grandTotal) * 100).toFixed(0) : 0;
            return (
              <div
                key={cat.id}
                style={{
                  textAlign: "center",
                  minWidth: 70,
                }}
              >
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: 14,
                    fontWeight: 700,
                    color: cat.color,
                  }}
                >
                  {pct}%
                </div>
                <div
                  style={{
                    fontSize: 9,
                    color: "#74C69D",
                    textTransform: "uppercase",
                    letterSpacing: 0.5,
                    fontFamily: "'Space Mono', monospace",
                  }}
                >
                  {cat.id}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Allocation Bar Visual */}
      <div
        style={{
          display: "flex",
          height: 8,
          borderRadius: 4,
          overflow: "hidden",
          marginBottom: 24,
          background: "#1B4332",
        }}
      >
        {INVESTMENT_CATEGORIES.map((cat) => {
          const pct = grandTotal > 0 ? (getCategoryTotal(cat) / grandTotal) * 100 : 0;
          return (
            <div
              key={cat.id}
              style={{
                width: `${pct}%`,
                background: cat.color,
                transition: "width 0.3s ease",
              }}
            />
          );
        })}
      </div>

      {/* Category Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 24 }}>
        {INVESTMENT_CATEGORIES.map((cat) => {
          const isExpanded = expandedCat === cat.id;
          const catTotal = getCategoryTotal(cat);
          return (
            <div key={cat.id} style={cardStyle}>
              {/* Category Header */}
              <button
                onClick={() => setExpandedCat(isExpanded ? null : cat.id)}
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "16px 20px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  borderLeft: `4px solid ${cat.color}`,
                }}
              >
                <div style={{ textAlign: "left" }}>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: "#D8F3DC",
                      marginBottom: 2,
                    }}
                  >
                    {cat.label}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "#74C69D",
                      fontFamily: "'Space Mono', monospace",
                    }}
                  >
                    {cat.items.length} items &middot; category: {cat.category}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: 18,
                      fontWeight: 700,
                      color: cat.color,
                    }}
                  >
                    {formatUSD(catTotal)}
                  </div>
                  <span
                    style={{
                      color: "#52B788",
                      fontSize: 14,
                      transition: "transform 0.2s",
                      transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                      display: "inline-block",
                    }}
                  >
                    &#9660;
                  </span>
                </div>
              </button>

              {/* Expanded Line Items */}
              {isExpanded && (
                <div
                  style={{
                    padding: "0 20px 16px",
                    borderTop: "1px solid #1B4332",
                    animation: "fadeIn 0.2s ease",
                  }}
                >
                  {cat.items.map((item, i) => {
                    const key = `${cat.id}-${i}`;
                    return (
                      <div
                        key={key}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: "10px 0",
                          borderBottom:
                            i < cat.items.length - 1
                              ? "1px solid #1B4332"
                              : "none",
                          gap: 16,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 13,
                            color: "#B7E4C7",
                            flex: 1,
                          }}
                        >
                          {item.name}
                        </span>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <span
                            style={{
                              color: "#52B788",
                              fontSize: 14,
                              fontFamily: "'Space Mono', monospace",
                            }}
                          >
                            $
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="5"
                            value={amounts[key]}
                            onChange={(e) =>
                              setAmount(key, parseFloat(e.target.value) || 0)
                            }
                            style={{
                              width: 90,
                              padding: "6px 8px",
                              background: "#1B4332",
                              border: "1px solid #2D6A4F",
                              borderRadius: 6,
                              color: "#D8F3DC",
                              fontFamily: "'Space Mono', monospace",
                              fontSize: 14,
                              textAlign: "right",
                              outline: "none",
                              boxSizing: "border-box",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
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

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button
          onClick={handleSubmit}
          disabled={submitting || grandTotal === 0}
          style={{
            padding: "14px 36px",
            background:
              submitting || grandTotal === 0
                ? "#2D6A4F"
                : "linear-gradient(135deg, #2D6A4F, #40916C)",
            border: "none",
            borderRadius: 8,
            color: "#E8F5E9",
            fontFamily: "'Space Mono', monospace",
            fontSize: 14,
            letterSpacing: 1,
            cursor: submitting || grandTotal === 0 ? "not-allowed" : "pointer",
            opacity: submitting || grandTotal === 0 ? 0.5 : 1,
            transition: "all 0.2s",
          }}
        >
          {submitting
            ? "Recording..."
            : `Record ${formatUSD(grandTotal)} Investment`}
        </button>
        <button
          onClick={resetToDefaults}
          style={{
            padding: "14px 24px",
            background: "transparent",
            border: "1px solid #2D6A4F",
            borderRadius: 8,
            color: "#74C69D",
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
            cursor: "pointer",
            transition: "all 0.2s",
          }}
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
