# 🚀 Replit Junior Editor Remediation Sandbox

This guide documents the **Replit-based Junior Editor Sandbox** workflow for **ContentGenAutomator Studio**.

---

## 🎯 The Problem Solved
When autonomous multi-agent pipelines run in batch mode, an automated governance check (e.g. IBM watsonx) might flag a scene prompt for a mild copyright likeness or pacing discrepancy. In typical systems, this creates a hard pipeline failure or requires high-friction local development setups for human intervention.

## 🛠️ The Replit Solution
1. **Instant Scoped Sandbox:** When a governance flag occurs, an editor is provided a direct 1-click Replit URL.
2. **Lightweight Web Editing:** The editor modifies the flagged prompt or narration line directly in the browser.
3. **Automated Re-evaluation:** The editor hits "Re-submit" which calls `POST /api/governance/inline-check` against the live backend API.
4. **Resumed Autonomous Pipeline:** Once the IBM watsonx score clears, the project automatically resumes its rendering and publishing lifecycle.

---

## Architecture

```
[OrchestratorAgent Batch Queue] ──(Flagged Scene)──► [Replit Junior Editor Sandbox]
                                                              │
                                                        (Human Tweaks)
                                                              │
[Automated YouTube Release] ◄──(Compliance Passed)── [POST /api/governance/inline-check]
```
