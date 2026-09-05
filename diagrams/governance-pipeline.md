# IBM watsonx Governance & Compliance Pipeline

This sequence diagram illustrates the lifecycle of a prompt or scene proposal as it passes through the automated safety and hallucination gate. In the active cloud deployment, the governance adapter operates via a verified dual-pass `local_rule_heuristic` engine (enforcing Enterprise Strict, Brand Safe, and Viral Trend policy thresholds), with fail-closed halt semantics on violation and zero-trust HMAC-SHA256 compliance certificate generation upon approval.

```mermaid
sequenceDiagram
    autonumber
    actor Creator as Director / Studio UI
    participant API as FastAPI Orchestration Layer
    participant Agent as GovernanceAgent (ADK Specialist)
    participant Adapter as IBMWatsonxGovernanceAdapter
    participant DB as SQLite / PostgreSQL Audit Ledger
    participant Cert as ComplianceCertificateService

    Creator->>API: Submit Scene / Prompt Generation Request
    API->>Agent: A2A Delegate: watsonx_audit_prompt_tool(text, scene_number)
    
    rect rgb(240, 248, 255)
        Note over Agent,Adapter: Runtime Governance Evaluation
        Agent->>Adapter: audit_prompt(prompt_text, policy_pack="enterprise_strict")
        alt IBM_WATSONX_API_KEY Configured
            Adapter->>Adapter: Call IBM watsonx.governance REST API (Remote Cloud)
        else Key Missing in Deployment Env (Active Fallback)
            Adapter->>Adapter: Execute Dual-Pass local_rule_heuristic Engine (Deterministic)
        end
        Adapter-->>Agent: GovernanceVerdict (Risk Score, Violations, Flagged Status)
    end

    alt Risk Score > Policy Ceiling (e.g. Risk >= 0.20 or Disallowed Keyword)
        Agent-->>API: AuditDecision.FLAGGED (Risk Score: 1.00)
        API->>DB: Record GovernanceAuditRecord (status="flagged", violations)
        API-->>Creator: HTTP 422 Unprocessable Entity ("GovernanceCheckFailed")
        Note over Creator,API: FSM halts immediately; prevents rendering rogue AI assets
    else Risk Score <= Policy Ceiling (Clean / Compliant)
        Agent-->>API: AuditDecision.PASSED (Risk Score <= 0.05)
        API->>DB: Record GovernanceAuditRecord (status="passed", risk_score)
        API->>Cert: generate_certificate(project_id, policy_pack, audit_records)
        Cert->>Cert: Compute HMAC-SHA256 signature with export_signing_secret
        Cert-->>API: ComplianceCertificate (ID, Verification Hash, Signed Timestamp)
        API->>DB: Save ComplianceCertificateRecord
        API-->>Creator: HTTP 200 OK (Prompt Approved + Certified Compliant)
    end
```
