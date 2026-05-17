"use client";
import { useState, useRef, useEffect } from "react";
import { useStreamingQuery } from "@/hooks/useStreamingQuery";
import { AgentStatusTracker } from "@/components/AgentStatusTracker";
import { StreamingDebate } from "@/components/StreamingDebate";
import { VerdictCard } from "@/components/VerdictCard";
import { VerdictResult } from "@/lib/api";

const SUGGESTED_QUESTIONS = [
  "Find all auto-renewal and subscription trap clauses",
  "What liability am I waiving by agreeing to this?",
  "Are there any data collection or IP ownership clauses?",
  "What are the termination conditions and penalties?",
  "Identify any clauses that limit my right to sue",
];

interface ChatTurn {
  question: string;
  tokens: { prosecutor: string; advocate: string; judge: string };
  verdict: VerdictResult | null;
}

interface Props {
  docId?: string;
  docName?: string;
}

export function ConversationThread({ docId, docName }: Props) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [currentTurn, setCurrentTurn] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    sendQuery, abort, isStreaming,
    pipeline, tokens, verdict, error,
    conversationId, setConversationId,
  } = useStreamingQuery();

  // When a verdict arrives, save completed turn
  useEffect(() => {
    if (verdict && currentTurn !== null) {
      setTurns(prev => {
        const updated = [...prev];
        const idx = updated.findIndex(t => t.question === currentTurn);
        if (idx >= 0) {
          updated[idx] = { ...updated[idx], tokens: { ...tokens }, verdict };
        }
        return updated;
      });
      setCurrentTurn(null);
    }
  }, [verdict]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, isStreaming]);

  const handleSubmit = async (q: string) => {
    if (!q.trim() || isStreaming) return;
    const question_text = q.trim();
    setQuestion("");
    setCurrentTurn(question_text);

    // Add new turn placeholder
    setTurns(prev => [...prev, { question: question_text, tokens: { prosecutor: "", advocate: "", judge: "" }, verdict: null }]);

    await sendQuery(question_text, docId, conversationId || undefined);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: "1rem" }}>
      {/* Status tracker — always visible when streaming */}
      {isStreaming && (
        <div style={{ position: "sticky", top: 0, zIndex: 10 }}>
          <AgentStatusTracker pipeline={pipeline} />
        </div>
      )}

      {/* Conversation history */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "2rem",
        paddingBottom: "1rem",
      }}>
        {turns.length === 0 && !isStreaming && (
          <div style={{ textAlign: "center", padding: "3rem 0" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚖️</div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              {docName
                ? `Ask me anything about "${docName}"`
                : "Upload a document above, then ask a question"}
            </p>
            {docName && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "1.5rem", justifyContent: "center" }}>
                {SUGGESTED_QUESTIONS.map((sq) => (
                  <button
                    key={sq}
                    onClick={() => handleSubmit(sq)}
                    style={{
                      padding: "0.4rem 0.875rem",
                      background: "var(--bg-900)",
                      border: "1px solid var(--border)",
                      borderRadius: 999,
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      fontFamily: "var(--font-sans)",
                    }}
                    onMouseEnter={e => {
                      (e.target as HTMLElement).style.borderColor = "var(--brand-500)";
                      (e.target as HTMLElement).style.color = "var(--brand-400)";
                    }}
                    onMouseLeave={e => {
                      (e.target as HTMLElement).style.borderColor = "var(--border)";
                      (e.target as HTMLElement).style.color = "var(--text-secondary)";
                    }}
                  >
                    {sq}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", gap: "1rem", animation: "fadeIn 0.4s ease" }}>
            {/* User question bubble */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <div style={{
                maxWidth: "75%",
                padding: "0.875rem 1.25rem",
                background: "var(--brand-glow)",
                border: "1px solid rgba(99,102,241,0.3)",
                borderRadius: "var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)",
                fontSize: "0.9rem",
                lineHeight: 1.6,
                color: "var(--text-primary)",
              }}>
                {turn.question}
              </div>
            </div>

            {/* Active streaming turn */}
            {i === turns.length - 1 && isStreaming && !turn.verdict && (
              <div style={{ animation: "fadeIn 0.3s ease" }}>
                <StreamingDebate tokens={tokens} isStreaming={isStreaming} />
              </div>
            )}

            {/* Completed turn with verdict */}
            {turn.verdict && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <StreamingDebate tokens={turn.tokens} isStreaming={false} />
                <VerdictCard verdict={turn.verdict} />
              </div>
            )}
          </div>
        ))}

        {error && (
          <div style={{
            padding: "1rem",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "var(--radius-md)",
            color: "var(--red-400)",
            fontSize: "0.875rem",
          }}>
            ⚠ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: "1px solid var(--border)",
        paddingTop: "1rem",
        display: "flex",
        gap: "0.75rem",
        alignItems: "flex-end",
      }}>
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(question);
            }
          }}
          placeholder={docName ? `Ask about "${docName}"... (Enter to send)` : "Upload a document first..."}
          disabled={isStreaming || !docId}
          rows={2}
          style={{
            flex: 1,
            resize: "none",
            background: "var(--bg-900)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "0.75rem 1rem",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
            fontFamily: "var(--font-sans)",
            outline: "none",
            transition: "border-color 0.2s",
            lineHeight: 1.5,
          }}
          onFocus={e => (e.target.style.borderColor = "var(--brand-500)")}
          onBlur={e => (e.target.style.borderColor = "var(--border)")}
        />
        {isStreaming ? (
          <button onClick={abort} className="btn btn-danger">
            ■ Stop
          </button>
        ) : (
          <button
            onClick={() => handleSubmit(question)}
            disabled={!question.trim() || !docId}
            className="btn btn-primary"
          >
            Analyze ›
          </button>
        )}
      </div>
    </div>
  );
}
