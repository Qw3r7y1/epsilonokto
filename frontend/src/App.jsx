import { useState } from "react";
import Pipeline from "./components/Pipeline";
import BudgetDashboard from "./components/BudgetDashboard";

const VIEWS = [
  { id: "budget", label: "Budget Dashboard" },
  { id: "pipeline", label: "Pipeline" },
];

export default function App() {
  const [view, setView] = useState("budget");

  return (
    <div
      style={{
        fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        background: "#0B1D0F",
        color: "#E8F5E9",
        minHeight: "100vh",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap"
        rel="stylesheet"
      />

      {/* Top Nav Bar */}
      <div
        style={{
          background: "linear-gradient(135deg, #1B4332 0%, #2D6A4F 50%, #40916C 100%)",
          padding: "20px 32px",
          borderBottom: "2px solid #52B788",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 11,
              letterSpacing: 4,
              color: "#95D5B2",
              textTransform: "uppercase",
              marginBottom: 2,
            }}
          >
            Epsilon Okto
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, lineHeight: 1.2 }}>
            Venture Studio
          </h1>
        </div>

        <div style={{ display: "flex", gap: 4 }}>
          {VIEWS.map((v) => (
            <button
              key={v.id}
              onClick={() => setView(v.id)}
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 11,
                letterSpacing: 1,
                textTransform: "uppercase",
                padding: "8px 18px",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
                background: view === v.id ? "rgba(255,255,255,0.15)" : "transparent",
                color: view === v.id ? "#D8F3DC" : "#95D5B2",
                transition: "all 0.2s",
              }}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 1060, margin: "0 auto", padding: "24px 32px 48px" }}>
        {view === "budget" && <BudgetDashboard />}
        {view === "pipeline" && <Pipeline />}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { height: 6px; width: 6px; }
        ::-webkit-scrollbar-track { background: #0B1D0F; }
        ::-webkit-scrollbar-thumb { background: #2D6A4F; border-radius: 3px; }
      `}</style>
    </div>
  );
}
