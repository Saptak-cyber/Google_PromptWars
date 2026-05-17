"use client";
import { AgentTokens } from "@/hooks/useStreamingQuery";

interface Props {
  tokens: AgentTokens;
  isStreaming: boolean;
}

function AgentPanel({
  title, icon, color, bgColor, borderColor, content, isActive,
}: {
  title: string; icon: string; color: string; bgColor: string;
  borderColor: string; content: string; isActive: boolean;
}) {
  return (
    <div style={{
      flex: 1,
      background: bgColor,
      border: `1px solid ${borderColor}`,
      borderRadius: "var(--radius-lg)",
      padding: "1.25rem",
      display: "flex",
      flexDirection: "column",
      gap: "0.75rem",
      minHeight: 240,
      transition: "border-color 0.3s, box-shadow 0.3s",
      boxShadow: isActive ? `0 0 24px ${bgColor}` : "none",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "1.25rem" }}>{icon}</span>
        <span style={{ fontWeight: 700, fontSize: "0.95rem", color }}>{title}</span>
        {isActive && (
          <span style={{
            marginLeft: "auto",
            width: 8, height: 8,
            borderRadius: "50%",
            background: color,
            boxShadow: `0 0 8px ${color}`,
            animation: "pulse 1s infinite",
          }} />
        )}
      </div>
      <div style={{
        flex: 1,
        fontSize: "0.875rem",
        lineHeight: "1.7",
        color: "var(--text-secondary)",
        overflowY: "auto",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}>
        {content || (
          <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            {isActive ? "Generating argument..." : "Waiting..."}
          </span>
        )}
        {isActive && content && (
          <span style={{
            display: "inline-block",
            width: 2, height: "1em",
            background: color,
            marginLeft: 2,
            animation: "pulse 0.8s infinite",
            verticalAlign: "text-bottom",
          }} />
        )}
      </div>
    </div>
  );
}

export function StreamingDebate({ tokens, isStreaming }: Props) {
  const prosecutorActive = isStreaming && tokens.prosecutor.length === 0;
  const advocateActive = isStreaming && tokens.advocate.length === 0;
  const judgeActive = isStreaming && (tokens.prosecutor.length > 0 || tokens.advocate.length > 0) && tokens.judge.length === 0;

  // Strip JSON from streamed text for display
  const clean = (text: string) => {
    try {
      const jsonStart = text.indexOf("{");
      if (jsonStart > 0) return text.slice(0, jsonStart).trim();
      const parsed = JSON.parse(text);
      return parsed.argument || text;
    } catch {
      return text;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Debate banner */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.75rem 1rem",
        background: "var(--bg-900)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border)",
      }}>
        <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text-muted)", letterSpacing: "0.05em" }}>
          ADVERSARIAL DEBATE
        </span>
        <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Two lawyers. One verdict.
        </span>
      </div>

      {/* Two debate columns */}
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <AgentPanel
          title="Prosecutor"
          icon="⚔️"
          color="var(--red-400)"
          bgColor="rgba(239,68,68,0.05)"
          borderColor="rgba(239,68,68,0.2)"
          content={clean(tokens.prosecutor)}
          isActive={prosecutorActive || (isStreaming && tokens.prosecutor.length > 0 && tokens.prosecutor[tokens.prosecutor.length-1] !== "\n")}
        />
        <AgentPanel
          title="Devil's Advocate"
          icon="🛡️"
          color="var(--blue-400)"
          bgColor="rgba(59,130,246,0.05)"
          borderColor="rgba(59,130,246,0.2)"
          content={clean(tokens.advocate)}
          isActive={advocateActive || (isStreaming && tokens.advocate.length > 0 && tokens.judge.length === 0)}
        />
      </div>

      {/* Judge panel — appears after both agents start */}
      {(tokens.judge.length > 0 || judgeActive) && (
        <div style={{ animation: "fadeIn 0.4s ease" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "0.75rem",
          }}>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, padding: "0 0.5rem" }}>
              JUDGE'S SYNTHESIS
            </span>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
          </div>
          <AgentPanel
            title="Judge"
            icon="⚖️"
            color="var(--gold-400)"
            bgColor="rgba(245,158,11,0.05)"
            borderColor="rgba(245,158,11,0.2)"
            content={clean(tokens.judge)}
            isActive={judgeActive || (isStreaming && tokens.judge.length > 0)}
          />
        </div>
      )}
    </div>
  );
}
