"use client";

import React, { useEffect, useState } from "react";

interface BudgetStatus {
  project_id: string;
  token_budget: number;
  tokens_consumed: number;
  budget_headroom: number;
  percent_used: number;
  cost_ceiling_exceeded: boolean;
}

interface FinOpsProps {
  projectId?: string;
}

export default function FinOpsBudgetMonitor({ projectId }: FinOpsProps) {
  const [budget, setBudget] = useState<BudgetStatus | null>(null);

  useEffect(() => {
    if (!projectId) {
      setBudget({
        project_id: "preview",
        token_budget: 50000,
        tokens_consumed: 420,
        budget_headroom: 49580,
        percent_used: 0.8,
        cost_ceiling_exceeded: false
      });
      return;
    }

    const fetchBudget = async () => {
      try {
        const res = await fetch(`/api/telemetry/budget-status/${projectId}`);
        if (res.ok) {
          const json = await res.json();
          setBudget(json);
        }
      } catch (e) {
        // Fallback
      }
    };
    fetchBudget();
    const timer = setInterval(fetchBudget, 5000);
    return () => clearInterval(timer);
  }, [projectId]);

  if (!budget) return null;

  const pct = Math.min(100, Math.max(0, budget.percent_used));
  const barColor = pct > 90 ? "#ef4444" : pct > 70 ? "#f59e0b" : "#10b981";

  return (
    <div style={{
      background: "rgba(15, 23, 42, 0.55)",
      border: "1px solid rgba(56, 189, 248, 0.2)",
      borderRadius: "10px",
      padding: "10px 14px",
      marginBottom: "16px",
      fontSize: "12px"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontWeight: 700, color: "#38bdf8" }}>💳 FinOps Token Budget:</span>
          <span style={{ color: "var(--ink)" }}>{budget.tokens_consumed.toLocaleString()} / {budget.token_budget.toLocaleString()} tokens ({pct}%)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ color: "var(--muted)", fontSize: "11px" }}>Headroom: {budget.budget_headroom.toLocaleString()} tokens</span>
          <span style={{
            fontSize: "10px",
            fontWeight: 700,
            padding: "2px 6px",
            borderRadius: "4px",
            background: budget.cost_ceiling_exceeded ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.15)",
            color: budget.cost_ceiling_exceeded ? "#ef4444" : "#10b981",
            border: `1px solid ${budget.cost_ceiling_exceeded ? "#ef4444" : "#10b981"}`
          }}>
            {budget.cost_ceiling_exceeded ? "CEILING EXCEEDED" : "GUARDRAIL ACTIVE"}
          </span>
        </div>
      </div>
      <div style={{ width: "100%", height: "6px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "3px", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: barColor, transition: "width 0.4s ease" }} />
      </div>
    </div>
  );
}
