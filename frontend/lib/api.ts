const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Document {
  doc_id: string;
  name: string;
  mime_type: string;
  chunk_count: number;
  page_count: number;
  uploaded_at: string;
}

export interface VerdictResult {
  verdict: "ACCEPT" | "NEGOTIATE" | "REJECT";
  risk_score: number;
  risk_label: "Critical" | "High" | "Medium" | "Low";
  verdict_summary: string;
  plain_english: string;
  prosecution_valid_points: string[];
  defense_valid_points: string[];
  negotiate_suggestions: string[];
  bottom_line: string;
  prosecution: {
    argument: string;
    risk_level: string;
    flagged_issues: string[];
    consumer_impact: string;
  };
  defense: {
    argument: string;
    justification: string;
    industry_standard: boolean;
    user_benefits: string[];
  };
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "prosecutor" | "advocate" | "judge";
  content: string;
  metadata?: VerdictResult;
  created_at: string;
}

export const api = {
  async uploadDocument(file: File, docName?: string): Promise<{ doc_id: string; name: string; pages: number; chunks: number }> {
    const form = new FormData();
    form.append("file", file);
    if (docName) form.append("doc_name", docName);
    const res = await fetch(`${API_BASE}/api/ingest`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listDocuments(): Promise<{ documents: Document[] }> {
    const res = await fetch(`${API_BASE}/api/documents`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteDocument(docId: string): Promise<void> {
    await fetch(`${API_BASE}/api/documents/${docId}`, { method: "DELETE" });
  },

  async createConversation(docId?: string): Promise<{ conversation_id: string }> {
    const res = await fetch(`${API_BASE}/api/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: docId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getConversation(conversationId: string): Promise<{ messages: Message[] }> {
    const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  queryStream(question: string, docId?: string, conversationId?: string): EventSource {
    // We use fetch + ReadableStream for POST SSE
    return { question, docId, conversationId } as unknown as EventSource;
  },

  getQueryStreamUrl(): string {
    return `${API_BASE}/api/query`;
  },

  getApiBase(): string {
    return API_BASE;
  },
};
