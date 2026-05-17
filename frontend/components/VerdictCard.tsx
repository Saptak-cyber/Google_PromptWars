"use client";
import { VerdictResult } from "@/lib/api";
import { useState } from "react";

const VERDICT_CONFIG = {
  ACCEPT: { color: "#4ade80", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.25)", icon: "✓", label: "ACCEPT" },
  NEGOTIATE: { color: "#fbbf24", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.25)", icon: "◈", label: "NEGOTIATE" },
  REJECT: { color: "#fb7185", bg: "rgba(244,63,94,0.08)", border: "rgba(244,63,94,0.25)", icon: "✕", label: "REJECT" },
};

const RISK_CONFIG = {
  Critical: { color: "#fb7185", bg: "rgba(244,63,94,0.12)", border: "rgba(244,63,94,0.3)" },
  High: { color: "#f87171", bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.3)" },
  Medium: { color: "#fbbf24", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)" },
  Low: { color: "#4ade80", bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.3)" },
};

interface Props {
  verdict: VerdictResult;
}

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderTop: "1px solid var(--border)" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%", display: "flex", justifyContent: "space-between",
          alignItems: "center", padding: "0.875rem 0",
          background: "none", border: "none", cursor: "pointer",
          color: "var(--text-primary)", fontWeight: 600, fontSize: "0.875rem",
          fontFamily: "var(--font-sans)",
        }}
      >
        {title}
        <span style={{ color: "var(--text-muted)", transition: "transform 0.2s", display: "inline-block", transform: open ? "rotate(180deg)" : "none" }}>
          ▾
        </span>
      </button>
      {open && <div style={{ paddingBottom: "1rem" }}>{children}</div>}
    </div>
  );
}

function List({ items, color }: { items: string[]; color: string }) {
  return (
    <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
      {items.map((item, i) => (
        <li key={i} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
          <span style={{ color, flexShrink: 0, marginTop: 2 }}>›</span>
          <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function VerdictCard({ verdict }: Props) {
  const vc = VERDICT_CONFIG[verdict.verdict] || VERDICT_CONFIG.NEGOTIATE;
  const rc = RISK_CONFIG[verdict.risk_label] || RISK_CONFIG.Medium;

  // Risk score gauge
  const gaugePercent = (verdict.risk_score / 10) * 100;
  const gaugeColor = verdict.risk_score >= 7 ? "#f87171" : verdict.risk_score >= 4 ? "#fbbf24" : "#4ade80";

  return (
    <div style={{
      background: "var(--surface)",
      border: `1px solid ${vc.border}`,
      borderRadius: "var(--radius-xl)",
      padding: "1.75rem",
      animation: "fadeIn 0.5s ease",
      boxShadow: `0 0 40px ${vc.bg}`,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {/* Verdict badge */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "0.6rem",
          padding: "0.5rem 1.25rem",
          background: vc.bg,
          border: `1px solid ${vc.border}`,
          borderRadius: "var(--radius-md)",
        }}>
          <span style={{ fontSize: "1.1rem", fontWeight: 900, color: vc.color }}>{vc.icon}</span>
          <span style={{ fontWeight: 800, fontSize: "1rem", color: vc.color, letterSpacing: "0.08em" }}>
            {vc.label}
          </span>
        </div>

        {/* Risk label */}
        <span style={{
          padding: "0.35rem 0.875rem",
          background: rc.bg,
          border: `1px solid ${rc.border}`,
          borderRadius: 999,
          fontSize: "0.8rem",
          fontWeight: 700,
          color: rc.color,
        }}>
          {verdict.risk_label} Risk
        </span>

        {/* Risk score gauge */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 4 }}>RISK SCORE</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 800, color: gaugeColor, lineHeight: 1 }}>
              {verdict.risk_score.toFixed(1)}<span style={{ fontSize: "0.8rem", fontWeight: 400, color: "var(--text-muted)" }}>/10</span>
            </div>
          </div>
          <div style={{ position: "relative", width: 48, height: 48 }}>
            <svg viewBox="0 0 48 48" style={{ transform: "rotate(-90deg)" }}>
              <circle cx="24" cy="24" r="20" fill="none" stroke="var(--bg-800)" strokeWidth="5" />
              <circle
                cx="24" cy="24" r="20"
                fill="none"
                stroke={gaugeColor}
                strokeWidth="5"
                strokeDasharray={`${2 * Math.PI * 20}`}
                strokeDashoffset={`${2 * Math.PI * 20 * (1 - gaugePercent / 100)}`}
                strokeLinecap="round"
                style={{ transition: "stroke-dashoffset 1s ease, stroke 0.5s" }}
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Plain English summary — most prominent */}
      <div style={{
        background: "var(--bg-900)",
        borderRadius: "var(--radius-md)",
        padding: "1.25rem",
        marginBottom: "1.25rem",
        borderLeft: `3px solid ${vc.color}`,
      }}>
        <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: 8, letterSpacing: "0.05em" }}>
          PLAIN ENGLISH SUMMARY
        </p>
        <p style={{ fontSize: "0.95rem", lineHeight: 1.75, color: "var(--text-primary)" }}>
          {verdict.plain_english}
        </p>
      </div>

      {/* Bottom line */}
      <div style={{
        padding: "0.875rem 1.25rem",
        background: `${vc.bg}`,
        border: `1px solid ${vc.border}`,
        borderRadius: "var(--radius-md)",
        marginBottom: "1.25rem",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.75rem",
      }}>
        <span style={{ fontSize: "1rem", flexShrink: 0 }}>💡</span>
        <p style={{ fontSize: "0.9rem", fontWeight: 600, color: vc.color, lineHeight: 1.5 }}>
          {verdict.bottom_line}
        </p>
      </div>

      {/* Collapsible sections */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {verdict.prosecution?.flagged_issues?.length > 0 && (
          <Section title="⚔️ Prosecution — Key Issues">
            <List items={verdict.prosecution.flagged_issues} color="var(--red-400)" />
          </Section>
        )}

        {verdict.defense?.user_benefits?.length > 0 && (
          <Section title="🛡️ Defense — User Benefits" defaultOpen={false}>
            <List items={verdict.defense.user_benefits} color="var(--blue-400)" />
          </Section>
        )}

        {verdict.negotiate_suggestions?.length > 0 && (
          <Section title="📝 Negotiation Suggestions">
            <List items={verdict.negotiate_suggestions} color="var(--gold-400)" />
          </Section>
        )}

        {verdict.prosecution_valid_points?.length > 0 && (
          <Section title="⚖️ Judge's Analysis" defaultOpen={false}>
            <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--red-400)", marginBottom: 6 }}>
              PROSECUTION VALID POINTS
            </p>
            <List items={verdict.prosecution_valid_points} color="var(--red-400)" />
            {verdict.defense_valid_points?.length > 0 && (
              <>
                <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--blue-400)", margin: "1rem 0 6px" }}>
                  DEFENSE VALID POINTS
                </p>
                <List items={verdict.defense_valid_points} color="var(--blue-400)" />
              </>
            )}
          </Section>
        )}
      </div>
    </div>
  );
}
