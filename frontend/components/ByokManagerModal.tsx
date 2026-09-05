"use client";

import React, { useState, useEffect } from "react";
import { getStoredByokKeys, saveStoredByokKeys, clearStoredByokKeys, ByokKeys, verifyByokKey } from "../lib/api";

interface ByokManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKeysUpdated?: () => void;
}

export default function ByokManagerModal({ isOpen, onClose, onKeysUpdated }: ByokManagerModalProps) {
  const [keys, setKeys] = useState<ByokKeys>({});
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [verifying, setVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<{
    valid?: boolean;
    message?: string;
  } | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setKeys(getStoredByokKeys());
      setVerifyStatus(null);
      setSaveMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleShow = (provider: string) => {
    setShowKey((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleKeyChange = (provider: keyof ByokKeys, value: string) => {
    setKeys((prev) => ({ ...prev, [provider]: value }));
    setVerifyStatus(null);
    setSaveMessage(null);
  };

  const handleVerifyGemini = async () => {
    const geminiKey = keys.gemini?.trim();
    if (!geminiKey) {
      setVerifyStatus({ valid: false, message: "Please enter a Gemini API key first." });
      return;
    }
    setVerifying(true);
    setVerifyStatus(null);
    try {
      const res = await verifyByokKey("gemini", geminiKey);
      setVerifyStatus(res);
    } catch (err: any) {
      setVerifyStatus({
        valid: false,
        message: err?.message || "Verification failed. Please check the API key.",
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleSave = () => {
    saveStoredByokKeys(keys);
    setSaveMessage("Keys saved securely to browser localStorage!");
    if (onKeysUpdated) onKeysUpdated();
    setTimeout(() => {
      setSaveMessage(null);
    }, 2500);
  };

  const handleClear = () => {
    if (confirm("Are you sure you want to clear all stored API keys from your browser?")) {
      clearStoredByokKeys();
      setKeys({});
      setVerifyStatus(null);
      setSaveMessage("All API keys removed from browser storage.");
      if (onKeysUpdated) onKeysUpdated();
      setTimeout(() => {
        setSaveMessage(null);
      }, 2500);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.8)",
        backdropFilter: "blur(12px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "#0d0f1a",
          border: "1px solid rgba(199, 243, 107, 0.4)",
          borderRadius: "16px",
          maxWidth: "680px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "28px",
          color: "var(--ink, #f3f4f6)",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6), 0 0 30px rgba(199, 243, 107, 0.1)",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span style={{ fontSize: "20px" }}>🔑</span>
              <h2 style={{ fontSize: "19px", fontWeight: 700, margin: 0, color: "#c7f36b" }}>
                Bring Your Own Key (BYOK) Studio Settings
              </h2>
            </div>
            <p style={{ fontSize: "13px", color: "var(--muted, #9ca3af)", margin: 0 }}>
              Supply your own provider keys for generation. Zero server-side persistence.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--muted, #9ca3af)",
              fontSize: "20px",
              cursor: "pointer",
              padding: "4px 8px",
            }}
          >
            ✕
          </button>
        </div>

        {/* Security & Privacy Banner */}
        <div
          style={{
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "10px",
            padding: "14px 16px",
            marginBottom: "22px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
            <span style={{ fontSize: "14px" }}>🛡️</span>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Zero-Storage Client-Side Security Guarantee
            </span>
          </div>
          <p style={{ fontSize: "12px", color: "#d1d5db", margin: 0, lineHeight: 1.5 }}>
            Your API keys are stored <strong>strictly in your browser&apos;s localStorage</strong>. When executing requests, keys are
            transmitted as temporary in-memory HTTP headers directly to the API providers.
            <strong style={{ color: "#c7f36b" }}> They are NEVER written to a database, server disk, or permanent logs.</strong>
          </p>
        </div>

        {/* Form fields */}
        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          {/* Google Gemini */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "10px",
              padding: "16px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label style={{ fontSize: "13px", fontWeight: 600, color: "#f3f4f6", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>✨ Google Gemini API Key</span>
                <span style={{ fontSize: "10px", background: "rgba(199, 243, 107, 0.15)", color: "#c7f36b", padding: "1px 6px", borderRadius: "4px", border: "1px solid rgba(199, 243, 107, 0.3)" }}>
                  Required for Gemini
                </span>
              </label>
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: "11px", color: "#60a5fa", textDecoration: "underline" }}
              >
                Get Key from Google AI Studio ↗
              </a>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type={showKey.gemini ? "text" : "password"}
                value={keys.gemini || ""}
                onChange={(e) => handleKeyChange("gemini", e.target.value)}
                placeholder="AIzaSy..."
                style={{
                  flex: 1,
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "8px",
                  padding: "8px 12px",
                  color: "#f3f4f6",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              />
              <button
                type="button"
                onClick={() => toggleShow("gemini")}
                style={{
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "8px",
                  color: "#9ca3af",
                  padding: "0 12px",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                {showKey.gemini ? "Hide" : "Show"}
              </button>
              <button
                type="button"
                onClick={handleVerifyGemini}
                disabled={verifying || !keys.gemini}
                style={{
                  background: "rgba(99, 102, 241, 0.15)",
                  border: "1px solid rgba(99, 102, 241, 0.4)",
                  borderRadius: "8px",
                  color: "#818cf8",
                  padding: "0 14px",
                  cursor: verifying || !keys.gemini ? "not-allowed" : "pointer",
                  fontSize: "12px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  opacity: verifying || !keys.gemini ? 0.6 : 1,
                }}
              >
                {verifying ? "Checking..." : "Verify Key"}
              </button>
            </div>

            {verifyStatus && (
              <div
                style={{
                  marginTop: "10px",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: verifyStatus.valid ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                  border: verifyStatus.valid ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)",
                  color: verifyStatus.valid ? "#10b981" : "#ef4444",
                }}
              >
                <span>{verifyStatus.valid ? "✓" : "⚠"}</span>
                <span>{verifyStatus.message}</span>
              </div>
            )}
          </div>

          {/* Runway Gen-3 Alpha */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "10px",
              padding: "16px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label style={{ fontSize: "13px", fontWeight: 600, color: "#f3f4f6", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>🎬 RunwayML API Key</span>
                <span style={{ fontSize: "10px", background: "rgba(255, 255, 255, 0.06)", color: "#9ca3af", padding: "1px 6px", borderRadius: "4px" }}>
                  Optional · Video Gen
                </span>
              </label>
              <a
                href="https://dev.runwayml.com/"
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: "11px", color: "#60a5fa", textDecoration: "underline" }}
              >
                Runway Developer Portal ↗
              </a>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type={showKey.runway ? "text" : "password"}
                value={keys.runway || ""}
                onChange={(e) => handleKeyChange("runway", e.target.value)}
                placeholder="key_..."
                style={{
                  flex: 1,
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "8px",
                  padding: "8px 12px",
                  color: "#f3f4f6",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              />
              <button
                type="button"
                onClick={() => toggleShow("runway")}
                style={{
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "8px",
                  color: "#9ca3af",
                  padding: "0 12px",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                {showKey.runway ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Kling AI Video */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "10px",
              padding: "16px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label style={{ fontSize: "13px", fontWeight: 600, color: "#f3f4f6", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>⚡ Kling AI API Key</span>
                <span style={{ fontSize: "10px", background: "rgba(255, 255, 255, 0.06)", color: "#9ca3af", padding: "1px 6px", borderRadius: "4px" }}>
                  Optional · Video Gen
                </span>
              </label>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type={showKey.kling ? "text" : "password"}
                value={keys.kling || ""}
                onChange={(e) => handleKeyChange("kling", e.target.value)}
                placeholder="kling_..."
                style={{
                  flex: 1,
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "8px",
                  padding: "8px 12px",
                  color: "#f3f4f6",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              />
              <button
                type="button"
                onClick={() => toggleShow("kling")}
                style={{
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "8px",
                  color: "#9ca3af",
                  padding: "0 12px",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                {showKey.kling ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* ElevenLabs TTS */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "10px",
              padding: "16px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label style={{ fontSize: "13px", fontWeight: 600, color: "#f3f4f6", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>🎙️ ElevenLabs API Key</span>
                <span style={{ fontSize: "10px", background: "rgba(255, 255, 255, 0.06)", color: "#9ca3af", padding: "1px 6px", borderRadius: "4px" }}>
                  Optional · Neural TTS
                </span>
              </label>
              <a
                href="https://elevenlabs.io/"
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: "11px", color: "#60a5fa", textDecoration: "underline" }}
              >
                ElevenLabs Portal ↗
              </a>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type={showKey.elevenlabs ? "text" : "password"}
                value={keys.elevenlabs || ""}
                onChange={(e) => handleKeyChange("elevenlabs", e.target.value)}
                placeholder="sk_..."
                style={{
                  flex: 1,
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "8px",
                  padding: "8px 12px",
                  color: "#f3f4f6",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              />
              <button
                type="button"
                onClick={() => toggleShow("elevenlabs")}
                style={{
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "8px",
                  color: "#9ca3af",
                  padding: "0 12px",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                {showKey.elevenlabs ? "Hide" : "Show"}
              </button>
            </div>
          </div>
        </div>

        {saveMessage && (
          <div
            style={{
              marginTop: "16px",
              padding: "10px 14px",
              borderRadius: "8px",
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              color: "#10b981",
              fontSize: "13px",
              textAlign: "center",
              fontWeight: 600,
            }}
          >
            {saveMessage}
          </div>
        )}

        {/* Actions */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <button
            type="button"
            onClick={handleClear}
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "#ef4444",
              padding: "8px 14px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            🗑 Clear All Keys
          </button>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: "rgba(255, 255, 255, 0.06)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                color: "#d1d5db",
                padding: "8px 16px",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              Close
            </button>
            <button
              type="button"
              onClick={handleSave}
              style={{
                background: "#c7f36b",
                border: "none",
                borderRadius: "8px",
                color: "#111827",
                padding: "8px 20px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 700,
                boxShadow: "0 0 15px rgba(199, 243, 107, 0.3)",
              }}
            >
              💾 Save Keys
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
