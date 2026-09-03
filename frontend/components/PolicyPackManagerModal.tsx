"use client";

import React, { useEffect, useState } from "react";

interface PolicyPack {
  id: string;
  name: string;
  description: string;
  max_risk_score_allowed: number;
  allow_mild_action: boolean;
  copyright_strictness: string;
  is_default?: boolean;
}

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPack?: (packId: string) => void;
}

export default function PolicyPackManagerModal({ isOpen, onClose, onSelectPack }: ModalProps) {
  const [packs, setPacks] = useState<PolicyPack[]>([]);
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newRisk, setNewRisk] = useState("0.10");
  const [loading, setLoading] = useState(false);

  const fetchPacks = async () => {
    try {
      const res = await fetch("/api/governance/policy-packs");
      if (res.ok) {
        setPacks(await res.json());
      }
    } catch (e) {
      // Fallback
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPacks();
    }
  }, [isOpen]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newId || !newName) return;
    setLoading(true);
    try {
      const res = await fetch("/api/governance/policy-packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: newId.toLowerCase().replace(/\s+/g, "_"),
          name: newName,
          description: newDesc || "Custom studio policy pack",
          max_risk_score_allowed: parseFloat(newRisk) || 0.10,
          allow_mild_action: true,
          copyright_strictness: "strict"
        })
      });
      if (res.ok) {
        setNewId("");
        setNewName("");
        setNewDesc("");
        await fetchPacks();
      }
    } catch (e) {
      // error
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(0, 0, 0, 0.75)",
      backdropFilter: "blur(12px)",
      zIndex: 9999,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px"
    }}>
      <div style={{
        background: "#0d0f1a",
        border: "1px solid rgba(139, 92, 246, 0.4)",
        borderRadius: "14px",
        maxWidth: "680px",
        width: "100%",
        maxHeight: "85vh",
        overflowY: "auto",
        padding: "24px",
        color: "var(--ink)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0, color: "#c084fc" }}>
            🛡️ IBM watsonx Policy Pack Manager
          </h2>
          <button
            onClick={onClose}
            style={{ background: "transparent", border: "none", color: "var(--muted)", fontSize: "18px", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
        <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "20px" }}>
          Configure brand safety thresholds, copyright strictness, and fail-closed gate limits for video scene generation.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
          {packs.map((p) => (
            <div key={p.id} style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "8px",
              padding: "12px 16px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontWeight: 700, fontSize: "14px", color: "#38bdf8" }}>{p.name}</span>
                  <span style={{ fontSize: "11px", padding: "2px 6px", background: "rgba(56, 189, 248, 0.15)", borderRadius: "4px", color: "#38bdf8" }}>
                    Max Risk: {p.max_risk_score_allowed}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--muted)", margin: "4px 0 0" }}>{p.description}</p>
              </div>
              {onSelectPack && (
                <button
                  type="button"
                  onClick={() => { onSelectPack(p.id); onClose(); }}
                  style={{
                    fontSize: "11px",
                    padding: "4px 10px",
                    background: "rgba(168, 85, 247, 0.2)",
                    border: "1px solid rgba(168, 85, 247, 0.5)",
                    color: "#c084fc",
                    borderRadius: "6px",
                    cursor: "pointer"
                  }}
                >
                  Apply
                </button>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleCreate} style={{ borderTop: "1px solid rgba(255, 255, 255, 0.1)", paddingTop: "18px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "10px", color: "var(--ink)" }}>
            + Register Custom Policy Pack
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
            <input
              placeholder="Policy ID (e.g. enterprise_strict)"
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              required
              style={{ padding: "8px", borderRadius: "6px", background: "#06070c", border: "1px solid var(--line)", color: "var(--ink)", fontSize: "12px" }}
            />
            <input
              placeholder="Display Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
              style={{ padding: "8px", borderRadius: "6px", background: "#06070c", border: "1px solid var(--line)", color: "var(--ink)", fontSize: "12px" }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "10px", marginBottom: "10px" }}>
            <input
              placeholder="Description / Guidelines"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              style={{ padding: "8px", borderRadius: "6px", background: "#06070c", border: "1px solid var(--line)", color: "var(--ink)", fontSize: "12px" }}
            />
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="1.0"
              placeholder="Max Risk (0.01 - 1.0)"
              value={newRisk}
              onChange={(e) => setNewRisk(e.target.value)}
              style={{ padding: "8px", borderRadius: "6px", background: "#06070c", border: "1px solid var(--line)", color: "var(--ink)", fontSize: "12px" }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: "8px 16px",
              background: "#8b5cf6",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              fontSize: "12px",
              cursor: "pointer"
            }}
          >
            {loading ? "Registering..." : "Add Policy Pack"}
          </button>
        </form>
      </div>
    </div>
  );
}
