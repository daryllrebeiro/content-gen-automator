# Dual-Deployment Architecture & Security Infrastructure

ContentGenAutomator Studio is architected for dual-target cloud execution: Google Cloud Run as the scalable primary backend target and Replit as an instant, zero-setup secondary runtime. The deployment pipeline integrates Google Secret Manager, client-side BYOK header forwarding, strict CORS origin isolation, and an inline FinOps token cost-ceiling guardrail (HTTP 429) that prevents runaways.

```mermaid
flowchart TB
    classDef live fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff;
    classDef fallback fill:#f9a825,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
    classDef security fill:#c62828,stroke:#b71c1c,stroke-width:2px,color:#fff;
    classDef client fill:#1565c0,stroke:#0d47a1,stroke-width:2px,color:#fff;

    subgraph Client_Layer ["Client Browser (Director Studio UI)"]
        Browser["Next.js Cyberpunk Studio UI
        (Port 3000 / Replit Cloud Domain)"]:::client
        KeyStore[("Browser LocalStorage
        (BYOK: X-Gemini-API-Key,
        X-Runway-API-Key, etc.)")]:::security
        Browser -.->|Read Keys on Request| KeyStore
    end

    subgraph Edge_Security ["Security Perimeter & CORS Boundary"]
        CORS["CORS Policy Validation
        (Allowed Origins: Replit URL, Cloud Run, Localhost)"]:::security
        RateLimiter["BYOK Verify Rate Limiter
        (10 req/min per IP)"]:::security
    end

    Browser -->|HTTP Request + BYOK Headers| Edge_Security

    subgraph Production_Targets ["Dual-Deployment Production Targets"]
        subgraph Target_CloudRun ["Target 1: Google Cloud Run (Primary Production)"]
            CloudRun["Cloud Run Backend Container
            (FastAPI + ADK 2.8.0 Engine)
            https://content-gen-automator-backend-..."]:::live
            SecretManager[("Google Secret Manager
            - GEMINI_API_KEY
            - INTEGRATION_SECRET
            - EXPORT_SIGNING_SECRET")]:::security
            SecretManager -->|Injected at Build/Boot| CloudRun
        end

        subgraph Target_Replit ["Target 2: Replit Deployment (Secondary Production)"]
            ReplitProc["Replit Multi-Process Supervisor
            (scripts/replit_start.sh)"]:::live
            ReplitUI["Next.js Web Server (0.0.0.0:3000)"]:::live
            ReplitAPI["FastAPI Engine (127.0.0.1:8000)"]:::live
            ReplitProc --> ReplitUI
            ReplitProc --> ReplitAPI
            ReplitUI -->|Proxy /api| ReplitAPI
        end
    end

    Edge_Security -->|Dispatched to Cloud Run| CloudRun
    Edge_Security -->|Dispatched to Replit| ReplitProc

    subgraph Guardrail_Pipeline ["FastAPI Request & Safety Pipeline"]
        BYOKResolver["BYOK Credential Resolver
        (app/api/byok.py)
        Client Key > Server Env Key"]:::live
        
        FinOpsGate{"FinOps Guardrail
        Tokens > 50,000 Budget?"}:::security

        Halt429["HTTP 429 Too Many Requests
        (Cost Ceiling Exceeded - Halt)"]:::security

        ADKTree["ADK Multi-Agent Core & Generation"]:::live

        BYOKResolver --> FinOpsGate
        FinOpsGate -->|Yes| Halt429
        FinOpsGate -->|No (Within Headroom)| ADKTree
    end

    CloudRun --> BYOKResolver
    ReplitAPI --> BYOKResolver
```
