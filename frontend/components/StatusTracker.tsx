export default function StatusTracker({ status, autoPilot }: { status: string; autoPilot: boolean }) {
  const steps = [
    { label: "Idea & Script", match: ["CREATED", "INPUT_RECEIVED", "FACT_CHECKING", "STORY_CREATED", "SCENES_PLANNED", "AWAITING_NEXT", "PROMPT_APPROVAL_PENDING", "APPROVED"] },
    { label: "Video Generation", match: ["COMPLETED", "VIDEO_REVIEW_PENDING"] },
    { label: "Publishing", match: ["VIDEO_APPROVED", "PUBLISHING_PENDING"] },
    { label: "Live on YouTube", match: ["PUBLISHED"] },
  ];

  let currentStepIndex = steps.findIndex((s) => s.match.includes(status));
  if (currentStepIndex === -1) currentStepIndex = 0;

  return (
    <div className="status-tracker panel" style={{ marginBottom: "30px", borderTop: "2px solid var(--accent)", background: "rgba(0,0,0,0.6)" }}>
      <h3 style={{ margin: "0 0 16px", color: "var(--ink)", display: "flex", justifyContent: "space-between" }}>
        Pipeline Status Tracker
        {autoPilot && <span className="pulse-dot" style={{ width: "12px", height: "12px", borderRadius: "50%", background: "var(--accent)" }}></span>}
      </h3>
      <div style={{ display: "flex", justifyContent: "space-between", position: "relative" }}>
        <div style={{ position: "absolute", top: "14px", left: "0", right: "0", height: "2px", background: "var(--line)", zIndex: 0 }}></div>
        <div style={{ position: "absolute", top: "14px", left: "0", width: `${(currentStepIndex / (steps.length - 1)) * 100}%`, height: "2px", background: "var(--accent)", transition: "width 0.5s ease", zIndex: 0 }}></div>
        
        {steps.map((step, idx) => {
          const isActive = idx <= currentStepIndex;
          const isCurrent = idx === currentStepIndex;
          return (
            <div key={idx} style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center", width: "100px", textAlign: "center" }}>
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "50%",
                  background: isActive ? "var(--accent)" : "#10101a",
                  border: `2px solid ${isActive ? "var(--accent)" : "var(--line)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: isActive ? "#fff" : "var(--muted)",
                  fontWeight: "bold",
                  marginBottom: "8px",
                  boxShadow: isCurrent ? "0 0 15px var(--accent-glow)" : "none",
                  transition: "all 0.3s ease",
                }}
              >
                {isActive ? "✓" : idx + 1}
              </div>
              <span style={{ fontSize: "12px", color: isCurrent ? "var(--ink)" : "var(--muted)", fontWeight: isCurrent ? 700 : 400 }}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
