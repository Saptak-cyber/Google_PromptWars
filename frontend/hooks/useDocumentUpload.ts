"use client";
import { useState, useCallback } from "react";
import { api } from "@/lib/api";

export interface UploadedDocument {
  doc_id: string;
  name: string;
  pages: number;
  chunks: number;
}

export function useDocumentUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedDoc, setUploadedDoc] = useState<UploadedDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    setUploadedDoc(null);
    setProgress(10);

    try {
      setProgress(40);
      const result = await api.uploadDocument(file, file.name);
      setProgress(100);
      setUploadedDoc(result);
      return result;
    } catch (err: any) {
      setError(err.message || "Upload failed");
      return null;
    } finally {
      setUploading(false);
    }
  }, []);

  return { upload, uploading, progress, uploadedDoc, error, setUploadedDoc };
}
