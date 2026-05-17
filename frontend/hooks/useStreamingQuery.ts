"use client";
import { useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";

export type AgentStatus = "idle" | "active" | "complete" | "error";

export interface PipelineState {
  query_rewrite: AgentStatus;
  retrieval: AgentStatus;
  sufficiency: AgentStatus;
  prosecutor: AgentStatus;
  advocate: AgentStatus;
  judge: AgentStatus;
  quality_check: AgentStatus;
  done: AgentStatus;
}

export interface AgentTokens {
  prosecutor: string;
  advocate: string;
  judge: string;
}

const initialPipeline: PipelineState = {
  query_rewrite: "idle",
  retrieval: "idle",
  sufficiency: "idle",
  prosecutor: "idle",
  advocate: "idle",
  judge: "idle",
  quality_check: "idle",
  done: "idle",
};

export function useStreamingQuery() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineState>(initialPipeline);
  const [tokens, setTokens] = useState<AgentTokens>({ prosecutor: "", advocate: "", judge: "" });
  const [verdict, setVerdict] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const resetState = () => {
    setPipeline(initialPipeline);
    setTokens({ prosecutor: "", advocate: "", judge: "" });
    setVerdict(null);
    setError(null);
  };

  const sendQuery = useCallback(
    async (
      question: string,
      docId?: string,
      existingConversationId?: string
    ) => {
      resetState();
      setIsStreaming(true);

      abortRef.current = new AbortController();

      try {
        const res = await fetch(api.getQueryStreamUrl(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            doc_id: docId,
            conversation_id: existingConversationId,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let currentEvent = "";
          let currentData = "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              currentData = line.slice(5).trim();
              if (currentEvent && currentData) {
                handleEvent(currentEvent, currentData);
                currentEvent = "";
                currentData = "";
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message || "Stream failed");
        }
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  function handleEvent(event: string, data: string) {
    try {
      const parsed = JSON.parse(data);
      switch (event) {
        case "conversation_id":
          setConversationId(parsed.conversation_id);
          break;
        case "agent_status":
          if (parsed.step && parsed.status) {
            setPipeline((prev) => ({
              ...prev,
              [parsed.step]: parsed.status as AgentStatus,
            }));
          }
          break;
        case "token":
          if (parsed.agent && parsed.token) {
            const agent = parsed.agent as keyof AgentTokens;
            if (agent in { prosecutor: 1, advocate: 1, judge: 1 }) {
              setTokens((prev) => ({
                ...prev,
                [agent]: prev[agent] + parsed.token,
              }));
            }
          }
          break;
        case "verdict":
          setVerdict(parsed);
          break;
        case "error":
          setError(parsed.message || "Unknown error");
          break;
        case "done":
          break;
      }
    } catch {
      // Ignore parse errors
    }
  }

  const abort = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
  };

  return {
    sendQuery,
    abort,
    isStreaming,
    pipeline,
    tokens,
    verdict,
    error,
    conversationId,
    setConversationId,
  };
}
