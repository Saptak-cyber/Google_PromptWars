"use client";
import { PipelineState, AgentStatus } from "@/hooks/useStreamingQuery";

interface Step {
  key: keyof PipelineState;
  label: string;
  icon: string;
  color?: string;
}

const STEPS: Step[] = [
  { key: "query_rewrite", label: "Query Rewrite", icon: "✏️" },
  { key: "retrieval",     label: "Retrieve Docs", icon: "🔍" },
  { key: "sufficiency",  label: "Check Sufficiency", icon: "📋" },
  { key: "prosecutor",   label: "Prosecutor", icon: "⚖️", color: "var(--red-400)" },
  { key: "advocate",     label: "Devil's Advocate", icon: "🛡️", color: "var(--blue-400)" },
  { key: "judge",        label: "Judge", icon: "🔨", color: "var(--gold-400)" },
  { key: "quality_check",label: "Quality Check", icon: "✅" },
];

interface Props {
  pipeline: PipelineState;
}

function StatusDot({ status, color }: { status: AgentStatus; color?: string }) {
  if (status === "active") {
    return (
      <span style={{
        width: 10, height: 10,
        borderRadius: "50%",
        background: color || "var(--brand-500)",
        display: "inline-block",
        flexShrink: 0,
        boxShadow: `0 0 8px ${color || "var(--brand-500)"}`,
        animation: "pulse 1.2s ease-in-out infinite",
      }} />
    );
  }
  if (status === "complete") {
    return <span style={{ color: "#4ade80", fontSize: "0.75rem", flexShrink: 0 }}>✓</span>;
  }
  return (
    <span style={{
      width: 10, height: 10,
      borderRadius: "50%",
      background: "var(--bg-700)",
      display: "inline-block",
      flexShrink: 0,
    }} />
  );
}

export function AgentStatusTracker({ pipeline }: Props) {
  return (
    <div style={{
      background: "var(--bg-900)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      padding: "1rem 1.25rem",
      display: "flex",
      flexWrap: "wrap",
      gap: "0.5rem",
      alignItems: "center",
    }}>
      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, marginRight: 4 }}>
        PIPELINE
      </span>
      {STEPS.map((step, i) => (
        <div key={step.key} style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          {i > 0 && (
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>›</span>
          )}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            padding: "0.25rem 0.6rem",
            borderRadius: 999,
            background: pipeline[step.key] === "active"
              ? `${step.color ? step.color.replace(")", ",0.12)").replace("var(","rgba(var(") : "rgba(99,102,241,0.12)"}`
              : pipeline[step.key] === "complete"
              ? "rgba(34,197,94,0.08)"
              : "transparent",
            border: pipeline[step.key] === "active"
              ? `1px solid ${step.color || "var(--brand-500)"}`
              : pipeline[step.key] === "complete"
              ? "1px solid rgba(34,197,94,0.3)"
              : "1px solid transparent",
            transition: "all 0.3s",
          }}>
            <StatusDot status={pipeline[step.key]} color={step.color} />
            <span style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: pipeline[step.key] === "active"
                ? (step.color || "var(--brand-400)")
                : pipeline[step.key] === "complete"
                ? "#4ade80"
                : "var(--text-muted)",
              transition: "color 0.3s",
            }}>
              {step.label}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
