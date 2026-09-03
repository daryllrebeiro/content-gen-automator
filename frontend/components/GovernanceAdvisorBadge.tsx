"use client";

import React, { useEffect, useState } from "react";

interface AdvisorProps {
  text: string;
  policyPack?: string;
}

export default function GovernanceAdvisorBadge({ text, policyPack = "general_audience" }: AdvisorProps) {
  const [advisory, setAdvisory] = useState<{
    status: string;
    decision: string;
    risk_score: number;
    advisory_warnings: string[];
    is_safe_to_submit: boolean;
  } | null>(null);

  useEffect(() => {
    if (!text || text.trim().length < 4) {
      setAdvisory(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await fetch("/api/governance/advisor", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt_text: text, policy_pack: policyPack })
        });
        if (res.ok) {
          const data = await res.json();
          setAdvisory(data);
        }
      } catch (e) {
        // Silent fallback
      }
    }, 450);

    return () => clearTimeout(timer);
  }, [text, policyPack]);

  if (!advisory) return null;

  const isSafe = advisory.is_safe_to_submit;

  return (
    <div style={{
      marginTop: "6px",
      marginBottom: "10px",
      padding: "6px 10px",
      borderRadius: "6px",
      background: isSafe ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.12)",
      border: `1px solid ${isSafe ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.4)"}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      fontSize: "11px"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span>{isSafe ? "🛡️ Governance Advisor:" : "⚠️ Governance Warning:"}</span>
        <span style={{ color: isSafe ? "#10b981" : "#f87171", fontWeight: 600 }}>
          {isSafe ? "Clean & Compliant" : "Potential Policy Violation"} (Risk: {advisory.risk_score.toFixed(2)})
        </span>
        {advisory.advisory_warnings.length > 0 && (
          <span style={{ color: "var(--muted)", marginLeft: "4px" }}>
            — {advisory.advisory_warnings.join("; ")}
          </span>
        )}
      </div>
      <span style={{
        fontSize: "10px",
        fontWeight: 700,
        textTransform: "uppercase",
        color: isSafe ? "#10b981" : "#f87171"
      }}>
        {isSafe ? "Pre-Check: Pass" : "Pre-Check: Block"}
      </span>
    </div>
  );
}
