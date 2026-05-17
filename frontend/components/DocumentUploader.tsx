"use client";
import { useCallback, useState } from "react";
import { useDocumentUpload } from "@/hooks/useDocumentUpload";

const ACCEPTED_FORMATS = [
  { ext: "PDF", mime: "application/pdf" },
  { ext: "DOCX", mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
  { ext: "DOC", mime: "application/msword" },
  { ext: "TXT", mime: "text/plain" },
  { ext: "HTML", mime: "text/html" },
  { ext: "PPTX", mime: "application/vnd.openxmlformats-officedocument.presentationml.presentation" },
  { ext: "XLSX", mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
  { ext: "RTF", mime: "application/rtf" },
  { ext: "MD", mime: "text/markdown" },
];

interface Props {
  onSuccess: (docId: string, docName: string) => void;
}

export function DocumentUploader({ onSuccess }: Props) {
  const { upload, uploading, progress, error } = useDocumentUpload();
  const [dragOver, setDragOver] = useState(false);
  const [uploadedName, setUploadedName] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setUploadedName(null);
    const result = await upload(file);
    if (result) {
      setUploadedName(result.name);
      onSuccess(result.doc_id, result.name);
    }
  }, [upload, onSuccess]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div style={{ width: "100%" }}>
      <label
        htmlFor="file-upload"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1rem",
          padding: "3rem 2rem",
          border: `2px dashed ${dragOver ? "var(--brand-500)" : "var(--border)"}`,
          borderRadius: "var(--radius-xl)",
          background: dragOver ? "var(--brand-glow)" : "var(--bg-900)",
          cursor: "pointer",
          transition: "all 0.2s",
          minHeight: 220,
        }}
      >
        <input
          id="file-upload"
          type="file"
          accept={ACCEPTED_FORMATS.map(f => f.mime).join(",")}
          style={{ display: "none" }}
          onChange={onInputChange}
          disabled={uploading}
        />

        {uploading ? (
          <>
            <div style={{ fontSize: "2.5rem" }}>⚙️</div>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontWeight: 600, color: "var(--brand-400)", marginBottom: 8 }}>
                Analyzing document...
              </p>
              <div style={{
                width: 220, height: 6,
                background: "var(--bg-800)",
                borderRadius: 3,
                overflow: "hidden",
              }}>
                <div style={{
                  height: "100%",
                  width: `${progress}%`,
                  background: "linear-gradient(90deg, var(--brand-500), var(--brand-300))",
                  borderRadius: 3,
                  transition: "width 0.3s",
                }} />
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 8 }}>
                Parsing with LlamaParse & building embeddings...
              </p>
            </div>
          </>
        ) : uploadedName ? (
          <>
            <div style={{
              width: 56, height: 56,
              background: "rgba(34,197,94,0.12)",
              border: "1px solid rgba(34,197,94,0.3)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.5rem",
            }}>✓</div>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontWeight: 600, color: "#4ade80" }}>Document indexed!</p>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginTop: 4 }}>{uploadedName}</p>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 8 }}>
                Drop another file to replace
              </p>
            </div>
          </>
        ) : (
          <>
            <div style={{
              width: 64, height: 64,
              background: "var(--brand-glow)",
              border: "1px solid rgba(99,102,241,0.3)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.75rem",
              transition: "transform 0.2s",
            }}>
              📄
            </div>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontWeight: 600, fontSize: "1rem", marginBottom: 6 }}>
                Drop your document here
              </p>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                or <span style={{ color: "var(--brand-400)", fontWeight: 600 }}>click to browse</span>
              </p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}>
                Max 50 MB
              </p>
            </div>
          </>
        )}
      </label>

      {error && (
        <div style={{
          marginTop: 12,
          padding: "0.75rem 1rem",
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: "var(--radius-md)",
          color: "var(--red-400)",
          fontSize: "0.875rem",
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Format badges */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "1rem", justifyContent: "center" }}>
        {ACCEPTED_FORMATS.map(f => (
          <span key={f.ext} style={{
            padding: "0.2rem 0.6rem",
            background: "var(--bg-800)",
            border: "1px solid var(--border)",
            borderRadius: 999,
            fontSize: "0.7rem",
            color: "var(--text-muted)",
            fontWeight: 600,
            letterSpacing: "0.05em",
          }}>
            {f.ext}
          </span>
        ))}
      </div>
    </div>
  );
}
