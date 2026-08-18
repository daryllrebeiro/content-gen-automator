# Robustness and n8n Integration Plan

## Executive recommendation

Integrate n8n, but keep the core Shorts agent as the authoritative application.

### The application should own

- Project state and state transitions
- PostgreSQL persistence
- Story and scene schemas
- Continuity locks
- Production Contracts
- Prompt templates and versions
- Fact statuses and evidence records
- Timing and safety validation
- Idempotency and concurrency control
- Quality scoring
- Export data

### n8n should own

- External triggers and webhooks
- Scheduled content ideas
- Research and enrichment workflows
- Human approval steps
- Notifications
- Calling external video, TTS, storage, and publishing APIs
- Retryable long-running jobs
- Cross-application automation
- Operational notifications and workflow-level reporting

This gives the product the best of both systems: deterministic application behavior and flexible automation around it.

n8n describes itself as a tool for connecting applications and manipulating data between them, which matches the integration layer proposed here. Its execution history can be retried, but it should not replace the project database as the canonical source of truth. [n8n documentation](https://docs.n8n.io/)

---

## 1. Target architecture

```text
                         USER / SCHEDULE / EXTERNAL EVENT
                                      │
                                      ▼
                              ┌──────────────┐
                              │     n8n      │
                              │ Orchestration│
                              └──────┬───────┘
                                     │ authenticated API calls
                                     ▼
                         ┌────────────────────────┐
                         │ Shorts Agent API       │
                         │ source of truth        │
                         └───────────┬────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        PostgreSQL             LLM / Fact             Prompt / Quality
        Project state           Providers              Validators
                                     │
                                     ▼
                           ┌─────────────────┐
                           │ External media  │
                           │ Video / TTS     │
                           │ Storage / YouTube│
                           └─────────────────┘
```

### Principle

n8n can request a state transition, but it cannot invent one. The API validates whether the transition is legal, records it transactionally, and returns an idempotent result.

---

## 2. Recommended n8n workflows

### Workflow A — Create project from a user or external trigger

```text
Webhook / Form / Airtable / Notion
  ↓
Normalize input
  ↓
Validate topic and duration
  ↓
POST /api/projects
  ↓
POST /api/projects/{id}/prompts/next
  ↓
Send Prompt 1 to user or approval channel
```

The webhook should receive a request ID supplied by the caller. The API should use it as an idempotency key.

### Workflow B — Human approval between scenes

```text
Prompt 1 ready
  ↓
n8n sends email / Slack / Teams approval request
  ↓
Human approves or requests regeneration
  ├── approve → POST /prompts/next
  └── regenerate → POST /prompts/{scene}/regenerate
```

The approval decision belongs to n8n, but the prompt version and resulting state belong to the application.

### Workflow C — Research and fact verification

```text
Project created
  ↓
n8n receives fact-check job event
  ↓
Search / URL Context / source APIs
  ↓
POST verified evidence to the agent API
  ↓
Agent updates fact statuses transactionally
  ↓
Narration becomes eligible for approved claims
```

For the first version, keep Gemini grounding inside the application. Add n8n as a research coordinator when multiple external sources or human review are required.

### Workflow D — Prompt package delivery

```text
Project completed
  ↓
GET /api/projects/{id}/export
  ↓
Upload Markdown / JSON to storage
  ↓
Send link to user
  ↓
Record delivery result
```

### Workflow E — Future video production

```text
Project complete
  ↓
Read exported scene prompts
  ↓
Submit each 10-second scene to video provider
  ↓
Poll provider job status
  ↓
Store clip references
  ↓
Generate or attach consistent TTS narration
  ↓
Human review
  ↓
Assemble and publish
```

Do not make n8n poll indefinitely without a bounded retry policy and a persisted job status in the application.

---

## 3. API contract required for n8n

Add a dedicated integration surface rather than exposing internal database operations.

### Authentication

Use one of:

- Signed webhook requests with HMAC
- Short-lived service tokens
- OAuth2 client credentials
- n8n credential storage for the service token

Never put Gemini keys, database credentials, or provider secrets into incoming webhook payloads.

### Required headers

```text
Authorization: Bearer <service-token>
X-Request-ID: <caller-generated-id>
Idempotency-Key: <stable-operation-key>
X-Agent-Version: <client-version>
```

### Recommended endpoints

```text
POST /api/integrations/projects
POST /api/integrations/projects/{id}/events
POST /api/integrations/projects/{id}/approve
POST /api/integrations/projects/{id}/reject
POST /api/integrations/projects/{id}/prompts/{scene}/regenerate
GET  /api/integrations/projects/{id}/status
GET  /api/integrations/projects/{id}/export
```

The current application endpoints can remain available for the frontend. The integration endpoints should enforce stronger authentication, request signing, audit logging, and idempotency.

---

## 4. Durable state and idempotency

### Database changes

Add these entities:

#### `idempotency_keys`

- Key
- Operation name
- Request hash
- Project ID
- Response JSON
- Status
- Expiry timestamp

#### `integration_events`

- Event ID
- Source system
- Event type
- Project ID
- Payload hash
- Received timestamp
- Processed timestamp
- Processing result

#### `approval_events`

- Project ID
- Scene number
- Decision
- Actor
- Comment
- Timestamp

#### `provider_jobs`

- Project ID
- Scene number
- Provider
- External job ID
- Status
- Retry count
- Last error
- Started and completed timestamps

### Rules

1. Repeat requests with the same idempotency key return the original response.
2. The same key with a different payload returns `409 Conflict`.
3. Scene generation uses a database lock or compare-and-swap on the current scene number.
4. Regeneration creates a new immutable prompt version.
5. External provider jobs are never assumed successful without a callback or status check.
6. Every state transition creates an audit event.

---

## 5. Reliability model

### Retry classification

Retry automatically:

- Network timeouts
- Temporary provider errors
- Rate limits with `Retry-After`
- Temporary database connection errors

Do not retry automatically:

- Invalid user input
- Safety-policy rejection
- Schema validation failure after repair attempts
- Contradicted facts
- Authentication failures
- Invalid provider configuration

Use exponential backoff with jitter and a maximum attempt count. Every retry should increment `repair_attempts` or `provider_retry_count`, depending on the failure type.

### Dead-letter handling

After the maximum retry count:

1. Persist the failure.
2. Mark the job as `FAILED_RETRYABLE` or `FAILED_PERMANENT`.
3. Send an n8n error event.
4. Notify the operator or user.
5. Preserve the original input and provider response metadata.

n8n has execution retry and execution-history features, but application-level job state is still necessary for reliable cross-system recovery. [n8n execution retry documentation](https://docs.n8n.io/workflows/executions/all-executions/)

---

## 6. Prompt and content robustness

### Input normalization

- Normalize whitespace and language metadata.
- Reject empty or excessively large topics.
- Limit facts and source URLs.
- Validate source URL schemes.
- Strip unsupported control characters.
- Store raw input separately from normalized input.

### Prompt injection defense

Treat user facts, source pages, and n8n payloads as data, not instructions.

The pipeline should separate:

```text
System policy
Project contract
Approved facts
Untrusted user content
Generated creative content
```

Never allow a source page or user fact to override safety policy, scene count, audio timing, or continuity rules.

### Provider output defense

Every provider response must pass:

- JSON schema validation
- Narration timing validation
- Required-heading validation
- Safety term validation
- Continuity validation
- Fact-reference validation
- Quality scoring

Only validated output is stored as the current prompt version.

---

## 7. n8n-specific operating model

### Use n8n for orchestration, not hidden business logic

Avoid putting these rules only in Code nodes:

- Scene count
- Prompt version increments
- Safety policies
- Approved fact logic
- Database state transitions
- Provider fallback rules

Those rules must remain testable in the application repository.

### Workflow design rules

- Keep workflows small and composable.
- Use explicit success and error branches.
- Pass project IDs instead of entire prompt histories.
- Store execution IDs with application job IDs.
- Add timeouts to HTTP calls.
- Add bounded retries.
- Do not store large binary assets in ordinary workflow data.
- Use credentials managed by n8n rather than hard-coded values.
- Add a manual approval node before irreversible publishing.

n8n provides credentials, execution history, retry behavior, and workflow-level operations. Its security audit can identify risky nodes, unprotected webhooks, missing security settings, and other issues. [n8n security audit documentation](https://docs.n8n.io/hosting/securing/security-audit/)

### Scaling

Start with one n8n instance and one application instance. Introduce queue mode only when long-running media jobs or concurrent users justify it. If n8n is scaled, keep main, worker, and runner versions aligned. [n8n scaling documentation](https://docs.n8n.io/hosting/scaling/external-storage/)

For video files or large binary assets, use object storage and pass references through workflows instead of embedding large payloads. n8n documents external binary storage for this purpose, subject to plan availability. [n8n external storage documentation](https://docs.n8n.io/hosting/scaling/external-storage/)

---

## 8. Security hardening

### Application

- Use HTTPS outside local development.
- Rotate service tokens.
- Restrict CORS to known frontend origins.
- Add request size limits.
- Add rate limiting per user and integration key.
- Redact API keys and provider responses from logs.
- Encrypt sensitive database fields where needed.
- Validate webhook signatures before parsing payloads.
- Use least-privilege database credentials.
- Keep provider keys server-side only.

### n8n

- Protect the editor with authentication and HTTPS.
- Set a custom encryption key.
- Use separate development and production instances.
- Restrict webhook exposure.
- Review risky and community nodes.
- Run the n8n security audit regularly.
- Keep workflows under version control where the deployment plan supports it.

n8n’s source-control environment guidance recommends a one-directional promotion model and warns against casually pushing and pulling the same instance. [n8n source-control environments](https://docs.n8n.io/source-control-environments/create-environments/)

---

## 9. Observability

### Correlation identifiers

Carry these through the entire flow:

```text
project_id
scene_number
prompt_version
request_id
idempotency_key
n8n_execution_id
provider_job_id
```

### Metrics

Track:

- Project creation success rate
- Prompt generation latency
- Provider error rate
- Fact verification failure rate
- Narration repair rate
- Safety rejection rate
- Regeneration rate per scene
- Export success rate
- n8n workflow failure rate
- End-to-end time from project creation to export
- Estimated token cost per project

### Alerts

Alert on:

- Repeated provider failures
- Elevated safety rejection rate
- Export failures
- Database readiness failures
- Stuck provider jobs
- n8n workflow error spikes
- Increasing regeneration rate

---

## 10. Human approval model

Recommended approval gates:

### Gate 1 — Story approval

Before generating all prompts, the user can approve the hook, facts, and scene plan.

### Gate 2 — Prompt approval

Before sending prompts to a video provider, the user approves the complete prompt package.

### Gate 3 — Video approval

Before publishing, the user reviews the generated clips, captions, narration, and safety flags.

n8n is well-suited to route these approval steps to email, Slack, Teams, or another connected system. The application should still record the final approval decision and actor.

---

## 11. Detailed phased implementation roadmap

The phases below are ordered by dependency. Do not begin long-running video automation before the application has durable state, idempotency, validation, and an approval boundary.

### Phase 0 — Product contract and operational baseline

**Objective:** Freeze the MVP behavior so later automation cannot silently change the product contract.

**Build:**

- Document the accepted duration enum: `10 | 20 | 30`.
- Document the exact structured prompt headings.
- Document the Production Contract and safety policy versions.
- Define project and prompt state transitions.
- Define which fields are user-editable and which are locked.
- Define data retention rules for prompts, facts, source URLs, and exports.
- Define the first quality-score thresholds.

**Deliverables:**

- Product contract document
- Versioned prompt policy
- State-transition table
- API error catalog
- Initial data-retention decision

**Acceptance criteria:**

- A new developer can explain when Prompt 2 may be generated.
- Every generated prompt has a policy and template version.
- Unsupported durations and invalid states are rejected consistently.

**Main risk:** Scope drift.
**Control:** Any feature that changes the contract becomes a separately versioned decision.

---

### Phase 1 — Application reliability foundation

**Objective:** Make the agent API safe to call repeatedly and safe to restart.

**Build:**

- Replace production `create_all` with a migration runner.
- Add `idempotency_keys` and `integration_events` tables.
- Add unique constraints for project IDs, scene numbers, prompt versions, and event IDs.
- Add transactional state transitions.
- Add optimistic locking or row locking around “Generate Next.”
- Add request size limits and rate limits.
- Add authenticated service-to-service requests.
- Add structured audit events for create, generate, regenerate, approve, export, and failure.
- Add database backup and restore instructions.

**Deliverables:**

- Migration command
- Auth middleware
- Idempotency middleware
- Audit-event repository
- Backup/restore runbook

**Acceptance criteria:**

- Replaying the same request returns the original response.
- Replaying the same key with a different payload returns `409`.
- Two concurrent requests cannot generate the same scene twice.
- A server restart does not lose project progress.
- A failed transaction leaves no partial prompt version.

**Main risk:** Duplicate external requests.
**Control:** Require `Idempotency-Key` for every n8n mutation endpoint.

---

### Phase 2 — Provider and validation hardening

**Objective:** Make real-provider output as reliable as the deterministic mock flow.

**Build:**

- Add provider timeouts and bounded retries.
- Add provider-specific error classification.
- Add structured-output repair calls with a maximum repair count.
- Add schema validation before every database write.
- Add safety validation after repair, not only before it.
- Add narration timing checks per language.
- Add fact-reference checks so unapproved claims cannot enter narration.
- Add provider fallback behavior that fails closed.
- Store raw provider metadata separately from user-facing prompt text.
- Add prompt-template version pinning per project.

**Deliverables:**

- Provider error taxonomy
- Repair policy
- Validation report object
- Provider contract tests
- Mock, fake, and live-provider test modes

**Acceptance criteria:**

- Malformed JSON never reaches the user as a valid prompt.
- Provider timeouts become retryable failures.
- Safety failures become permanent failures unless the input changes.
- A prompt can be reproduced from stored input, template, policy, and model metadata.

**Main risk:** A model produces plausible but invalid content.
**Control:** Treat model output as an untrusted candidate until all validators pass.

---

### Phase 3 — n8n development integration

**Objective:** Connect n8n without moving core business logic into workflows.

**Build:**

- Create a private n8n development instance.
- Store the agent service token in n8n credentials.
- Add an authenticated `POST /api/integrations/projects` endpoint.
- Add request signing or a short-lived service token.
- Add `X-Request-ID` and `Idempotency-Key` propagation.
- Create a workflow named `shorts_create_project_dev`.
- Add a workflow named `shorts_notify_prompt_ready_dev`.
- Add a workflow named `shorts_generate_next_dev`.
- Add a workflow named `shorts_error_handler_dev`.
- Store `n8n_execution_id` in the application event record.

**Recommended first workflow:**

```text
Webhook
  ↓
Validate required fields
  ↓
HTTP Request: create project
  ↓
HTTP Request: generate Prompt 1
  ↓
IF: response status is ready
  ├── yes → send prompt to approval channel
  └── no  → call error workflow
```

**Acceptance criteria:**

- A webhook creates exactly one project for a repeated request.
- n8n never sends the database password or Gemini key.
- A failed HTTP call is visible in both n8n and the application audit log.
- The workflow passes only IDs and bounded payloads between steps.

**Main risk:** Hidden business logic in n8n Code nodes.
**Control:** Keep all contract and state decisions in the application API.

---

### Phase 4 — Human approval and controlled scene progression

**Objective:** Add a human checkpoint before the system generates or publishes downstream assets.

**Build:**

- Add `STORY_APPROVAL_PENDING`, `PROMPT_APPROVAL_PENDING`, and `APPROVED` states.
- Add approval and rejection API endpoints.
- Add `approval_events` table.
- Add approval comments and actor identity.
- Build n8n approval workflows for email, Slack, or Teams.
- Add regeneration from an approval rejection.
- Preserve rejected versions for audit but never mark them current.

**Acceptance criteria:**

- Prompt generation cannot bypass a required approval state.
- Rejection creates an auditable event.
- Approval is tied to a project version, not only a project ID.
- Regeneration preserves approved facts and continuity locks.

**Main risk:** Approving one version while another is current.
**Control:** Approvals must reference `project_version` and `prompt_version`.

---

### Phase 5 — Evidence and research automation

**Objective:** Make factual narration reliable for topics requiring research.

**Build:**

- Add `fact_verification_jobs` and evidence records.
- Add a source allowlist/denylist policy.
- Add source quality ranking.
- Add citation extraction and normalization.
- Add a human review path for uncertain or contradictory claims.
- Add n8n workflow for source collection and review.
- Add webhook callbacks for verification completion.
- Keep claim status changes transactional.

**Acceptance criteria:**

- No `unverified` claim is rendered as a direct factual statement.
- Every verified claim has at least one stored source reference.
- Contradicted claims are visibly blocked.
- Research failure leaves the project usable but marks it as awaiting evidence.

**Main risk:** Search results are incomplete or conflicting.
**Control:** Use confidence thresholds and require human review below threshold.

---

### Phase 6 — Export, storage, and delivery automation

**Objective:** Deliver prompt packages reliably to the user and external systems.

**Build:**

- Add object storage for Markdown, JSON, and future media.
- Add signed, expiring download URLs.
- Add `delivery_jobs` table.
- Add export checksum and package version.
- Create n8n workflow for upload and notification.
- Add delivery retry and dead-letter status.
- Add retention and cleanup policies.

**Acceptance criteria:**

- An export can be downloaded after an application restart.
- Repeating delivery does not create duplicate package records.
- Every download link expires.
- Large binary files never pass through ordinary n8n JSON fields.

**Main risk:** Lost or duplicated exports.
**Control:** Store immutable export manifests with checksums.

---

### Phase 7 — Video and narration production jobs

**Objective:** Extend from prompt generation to actual clip production without weakening the prompt system.

**Build:**

- Add `provider_jobs` table.
- Define a provider-neutral video job interface.
- Submit exactly one job per ten-second prompt.
- Attach the prompt version and Production Contract to every job.
- Add provider callback endpoint and polling fallback.
- Add canonical narration/TTS job with a stable voice ID.
- Add clip artifact records and checksums.
- Add automatic duration, aspect-ratio, and audio checks.
- Add a human video-review state.

**Acceptance criteria:**

- A failed Clip 2 job does not invalidate Clip 1.
- A provider callback is idempotent.
- Generated artifacts map to exact prompt versions.
- Narration ends before the nine-second limit.
- Clips remain 9:16 and ten seconds long.

**Main risk:** Video-provider output does not obey the textual prompt.
**Control:** Validate artifacts after generation and require review before publishing.

---

### Phase 8 — Publishing automation

**Objective:** Automate publishing only after all content and safety gates pass.

**Build:**

- Add final review and publish approval state.
- Add YouTube metadata validation.
- Add thumbnail and title checks.
- Add YouTube upload job records.
- Add n8n publishing workflow.
- Add publish callback and final URL storage.
- Add rollback/unpublish runbook where supported.
- Add platform-specific rate-limit handling.

**Acceptance criteria:**

- No project can publish without final approval.
- Title, description, hashtags, captions, and clips are version-matched.
- A failed upload can resume without duplicating the video.
- Publishing credentials remain in n8n or a secret manager.

**Main risk:** Irreversible external publishing.
**Control:** Require explicit human approval immediately before publish.

---

### Phase 9 — Production scale and governance

**Objective:** Scale safely once usage justifies it.

**Build:**

- Add background workers for long-running jobs.
- Introduce n8n queue mode only when needed.
- Add OpenTelemetry traces.
- Add dashboards and alert thresholds.
- Add tenant/user quotas.
- Add model and provider cost budgets.
- Add staged deployments and rollback.
- Add n8n workflow version promotion.
- Add disaster recovery testing.
- Add security review and dependency scanning.

**Acceptance criteria:**

- A worker can restart without losing jobs.
- Queue depth and stuck jobs are visible.
- Production workflows are promoted through reviewable versions.
- A database restore has been tested, not just documented.
- Cost and quota limits are enforced before provider calls.

**Main risk:** Operational complexity exceeds product value.
**Control:** Do not introduce queue mode, multiple n8n instances, or media infrastructure until measured workload requires it.

---

## 12. Suggested delivery order

For the next implementation cycle, use this exact order:

```text
1. Idempotency and database migrations
2. API authentication and audit events
3. Provider repair/error classification
4. n8n development webhook
5. Prompt-ready notification
6. Human approval state
7. Evidence review workflow
8. Export delivery to object storage
9. Video provider job abstraction
10. Publishing workflow
```

Each item should be merged only after its acceptance criteria and regression tests pass.

---

## 13. Definition of robust

The system is robust when:

1. A duplicate n8n webhook cannot create duplicate projects.
2. A repeated “Generate Next” request cannot create duplicate scenes.
3. A failed provider call can resume without losing project state.
4. A failed evidence lookup cannot approve an unsupported claim.
5. A regenerated scene never changes the project continuity lock.
6. Every prompt is schema-validated before storage.
7. Every prompt version can be reproduced from stored metadata.
8. Every external job has a durable status and retry policy.
9. Every workflow failure is visible to an operator.
10. A human can approve or reject before irreversible publishing.
11. The system can be deployed without exposing provider secrets.
12. The system can be evaluated against a stable regression dataset.

---

## Final recommendation

Use n8n as the automation shell around the Shorts Agent:

```text
n8n = triggers, approvals, integrations, notifications, external jobs
Agent API = contracts, state, continuity, validation, facts, prompt versions
PostgreSQL = durable source of truth
Object storage = media and exports
```

That architecture keeps the product technically credible for the Devpost Taskmaster track while leaving room to automate the complete journey from idea to published Short.
