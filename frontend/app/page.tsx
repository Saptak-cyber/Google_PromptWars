"use client";
import { useState, useEffect } from "react";
import { DocumentUploader } from "@/components/DocumentUploader";
import { ConversationThread } from "@/components/ConversationThread";
import { api, Document } from "@/lib/api";

export default function Home() {
  const [activeDoc, setActiveDoc] = useState<{ id: string; name: string } | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    api.listDocuments()
      .then(r => setDocuments(r.documents))
      .catch(() => {})
      .finally(() => setLoadingDocs(false));
  }, []);

  const handleUploadSuccess = (docId: string, docName: string) => {
    setActiveDoc({ id: docId, name: docName });
    setDocuments(prev => [{
      doc_id: docId, name: docName,
      mime_type: "", chunk_count: 0, page_count: 0,
      uploaded_at: new Date().toISOString(),
    }, ...prev]);
  };

  const handleDeleteDoc = async (docId: string) => {
    await api.deleteDocument(docId);
    setDocuments(prev => prev.filter(d => d.doc_id !== docId));
    if (activeDoc?.id === docId) setActiveDoc(null);
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-950)" }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header style={{
        padding: "1rem 1.5rem",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: "1rem",
        background: "rgba(15,23,42,0.95)",
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{
            width: 36, height: 36,
            background: "linear-gradient(135deg, var(--brand-500), #a78bfa)",
            borderRadius: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1.1rem",
            boxShadow: "0 0 16px var(--brand-glow)",
          }}>⚖</div>
          <div>
            <h1 style={{ fontSize: "1.1rem", fontWeight: 800, lineHeight: 1.1 }}>
              Lex<span className="gradient-text">Guard</span>
            </h1>
            <p style={{ fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.06em", fontWeight: 600 }}>
              AI CONTRACT INTELLIGENCE
            </p>
          </div>
        </div>
        <div style={{ flex: 1 }} />
        {activeDoc && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.375rem 0.875rem",
            background: "var(--bg-900)",
            border: "1px solid var(--border)",
            borderRadius: 999,
            maxWidth: 320,
          }}>
            <span style={{ fontSize: "0.75rem" }}>📄</span>
            <span style={{
              fontSize: "0.8rem",
              color: "var(--text-secondary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {activeDoc.name}
            </span>
          </div>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="btn btn-ghost btn-sm"
        >
          {sidebarOpen ? "◁ Hide" : "▷ Show"} Panel
        </button>
      </header>

      {/* ── Main layout ─────────────────────────────────────────────────── */}
      <main style={{ flex: 1, display: "flex", overflow: "hidden", height: "calc(100vh - 65px)" }}>

        {/* Left sidebar */}
        {sidebarOpen && (
          <aside style={{
            width: 320,
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            background: "var(--bg-900)",
            flexShrink: 0,
            overflowY: "auto",
          }}>
            <div style={{ padding: "1.25rem" }}>
              <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "1rem" }}>
                UPLOAD DOCUMENT
              </p>
              <DocumentUploader onSuccess={handleUploadSuccess} />
            </div>

            <div style={{ padding: "0 1.25rem 1.25rem" }}>
              <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
                INDEXED DOCUMENTS ({documents.length})
              </p>
              {loadingDocs ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {[1, 2, 3].map(i => (
                    <div key={i} className="skeleton" style={{ height: 56 }} />
                  ))}
                </div>
              ) : documents.length === 0 ? (
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "center", padding: "1rem 0" }}>
                  No documents yet
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {documents.map(doc => (
                    <div
                      key={doc.doc_id}
                      style={{
                        padding: "0.75rem",
                        background: activeDoc?.id === doc.doc_id ? "var(--brand-glow)" : "var(--surface)",
                        border: `1px solid ${activeDoc?.id === doc.doc_id ? "rgba(99,102,241,0.4)" : "var(--border)"}`,
                        borderRadius: "var(--radius-md)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.6rem",
                        transition: "all 0.2s",
                      }}
                      onClick={() => setActiveDoc({ id: doc.doc_id, name: doc.name })}
                    >
                      <span style={{ fontSize: "1.1rem", flexShrink: 0 }}>📄</span>
                      <div style={{ flex: 1, overflow: "hidden" }}>
                        <p style={{
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          color: activeDoc?.id === doc.doc_id ? "var(--brand-400)" : "var(--text-primary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}>
                          {doc.name}
                        </p>
                        <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
                          {doc.chunk_count} chunks · {doc.page_count} pages
                        </p>
                      </div>
                      <button
                        onClick={e => { e.stopPropagation(); handleDeleteDoc(doc.doc_id); }}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "var(--text-muted)", fontSize: "0.8rem", padding: "0.25rem",
                          borderRadius: 4, transition: "color 0.2s",
                        }}
                        onMouseEnter={e => ((e.target as HTMLElement).style.color = "var(--red-400)")}
                        onMouseLeave={e => ((e.target as HTMLElement).style.color = "var(--text-muted)")}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}

        {/* Right: Conversation area */}
        <section style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: "1.5rem",
          overflow: "hidden",
        }}>
          {!activeDoc ? (
            /* Hero state — no document selected */
            <div style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "2rem",
              textAlign: "center",
            }}>
              <div style={{
                width: 96, height: 96,
                background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(167,139,250,0.2))",
                border: "1px solid rgba(99,102,241,0.3)",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "2.5rem",
                animation: "glow 3s ease-in-out infinite",
              }}>
                ⚖️
              </div>
              <div>
                <h2 style={{ fontSize: "2rem", fontWeight: 800, marginBottom: "0.5rem" }}>
                  Know What You're <span className="gradient-text">Signing</span>
                </h2>
                <p style={{ color: "var(--text-muted)", maxWidth: 480, lineHeight: 1.7 }}>
                  Upload any contract, offer letter, or policy document. LexGuard's adversarial AI 
                  will analyze every clause — a Prosecutor argues against it, a Devil's Advocate 
                  defends it, and a Judge delivers an impartial verdict.
                </p>
              </div>
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "1rem",
                maxWidth: 560,
                width: "100%",
              }} className="stagger">
                {[
                  { icon: "⚔️", label: "Prosecutor", desc: "Finds every risk against you", color: "var(--red-400)" },
                  { icon: "🛡️", label: "Devil's Advocate", desc: "Argues the clause is fair", color: "var(--blue-400)" },
                  { icon: "⚖️", label: "Judge", desc: "ACCEPT / NEGOTIATE / REJECT", color: "var(--gold-400)" },
                ].map(card => (
                  <div key={card.label} style={{
                    padding: "1.25rem",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-lg)",
                    textAlign: "center",
                  }}>
                    <div style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>{card.icon}</div>
                    <p style={{ fontWeight: 700, fontSize: "0.85rem", color: card.color, marginBottom: 4 }}>{card.label}</p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.4 }}>{card.desc}</p>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                ← Upload a document in the panel to get started
              </p>
            </div>
          ) : (
            /* Conversation view */
            <ConversationThread docId={activeDoc.id} docName={activeDoc.name} />
          )}
        </section>
      </main>
    </div>
  );
}
