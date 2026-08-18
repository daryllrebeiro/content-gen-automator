# Animated YouTube Shorts Prompt Agent

## Implementation Plan

**Project type:** Devpost Taskmaster MVP  
**Product:** Stateful AI agent for producing consistent animated YouTube Shorts prompts  
**Initial output:** Copy-ready prompts for a 10-second video-generation model  
**MVP maximum:** Three prompts / 30 seconds total  
**Status:** Planning

---

## 1. Executive summary

The product is a conversational creative-production agent. A user provides a YouTube Short idea and optional requirements. The agent researches or validates important factual claims, creates one project-level story, locks the visual and audio identity, divides the story into ten-second scenes, and returns one production-ready prompt at a time.

The agent does not generate three unrelated prompts. It maintains a canonical project state and renders each scene from that state. This is the core differentiator:

> Stateful AI orchestration for consistent multi-scene video generation.

The initial product generates prompts only. It does not generate video, edit clips, synthesize final audio, or publish to YouTube.

---

## 2. Product goals

### MVP goals

1. Accept a topic or video idea.
2. Accept optional facts, events, constraints, and visual preferences.
3. Support 10, 20, or 30 seconds only.
4. Convert duration into exactly 1, 2, or 3 ten-second scenes.
5. Generate a structured story before generating prompts.
6. Validate important factual claims before using them in narration.
7. Maintain one visual style across all scenes.
8. Maintain one narration voice specification across all scenes.
9. Enforce 9:16 vertical framing.
10. Keep generated narration within approximately nine seconds.
11. Leave the final second free from spoken narration to avoid abrupt audio cut-off.
12. Prevent photorealistic humans, real-person likenesses, recognizable copyrighted characters, logos, and trademarks in visual instructions.
13. Generate Prompt 1, then wait for an explicit “Generate next” action.
14. Allow each prompt to be copied individually and the project to be exported.
15. Make generation explainable through a compact “Why this prompt?” panel.

### Non-goals for the MVP

- Actual video generation
- Automatic video editing or stitching
- Final audio mixing or TTS production
- Direct YouTube publishing
- Arbitrary durations above 30 seconds
- Character image generation
- Multi-user collaboration
- Billing and subscriptions
- Native mobile applications
- Multi-provider routing
- Distributed workers, Redis, or Celery unless performance requires them

These can be documented as future extensions without complicating the first vertical slice.

---

## 3. Core user experience

### Initial input

The user supplies:

- Topic or idea
- Optional facts or source material
- Language
- Tone
- Intended audience
- Optional visual style, palette, setting, or camera preferences
- Duration: 10, 20, or 30 seconds

Example:

```text
Topic: How a small local idea became a worldwide chain
Facts: The user-provided facts or source links
Language: English
Tone: Curious cinematic documentary
Audience: General viewers
Visual style: Stylized cinematic 3D animation
Duration: 30 seconds
```

### Conversation flow

```text
Create project
  ↓
Validate input
  ↓
Research and validate claims
  ↓
Create story outline
  ↓
Create continuity profile
  ↓
Plan 1–3 scenes
  ↓
Return Prompt 1
  ↓
Await “Generate next”
  ↓
Return Prompt 2, if required
  ↓
Await “Generate next”
  ↓
Return Prompt 3, if required
  ↓
Mark project complete
```

For a 10-second project, Prompt 1 completes the project. For 20 seconds, Prompt 2 is the final prompt. For 30 seconds, all three prompts are generated.

The backend, not the language model, decides which prompt comes next.

---

## 4. Product differentiator

The product should be positioned as a reliable creative production system rather than a generic prompt wrapper.

### Problem with a stateless approach

```text
User idea → LLM prompt 1
User idea → LLM prompt 2
User idea → LLM prompt 3
```

This commonly causes:

- Character drift
- Style drift
- Contradictory facts
- Narration timing failures
- Weak scene transitions
- Different voices or pacing
- Repeated or missing story beats

### Proposed approach

```text
                 VIDEO PROJECT
                       │
          ┌────────────┴────────────┐
          │                         │
      STORY STATE              CONTINUITY STATE
          │                         │
          └────────────┬────────────┘
                       ▼
                  SCENE ENGINE
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          Scene 1   Scene 2   Scene 3
             │         │         │
             ▼         ▼         ▼
          Prompt 1  Prompt 2  Prompt 3
```

PostgreSQL or the project repository is the source of truth. The LLM is a creative component inside a deterministic workflow, not the owner of application state.

---

## 5. Production Contract

Every scene must satisfy a structured Production Contract before its prompt is returned.

```json
{
  "duration_seconds": 10,
  "aspect_ratio": "9:16",
  "narration_max_seconds": 9,
  "language": "English",
  "voice_id": "documentary_voice_01",
  "animation_style_id": "style_01",
  "character_ids": ["character_01"],
  "fact_ids": ["fact_001", "fact_003"],
  "previous_scene_id": "scene_01",
  "safety_policy_version": "policy_v1"
}
```

The prompt generator must satisfy the contract, not merely produce a creative description.

---

## 6. Global content and visual guardrails

Store the following policy centrally and inject it into every final prompt. Do not duplicate it across application functions.

```text
Create a fully animated cinematic YouTube Short in 9:16 vertical format.

Use only stylized animated environments and animated characters. Do not use
photorealistic humans, realistic faces, live-action footage, celebrity likenesses,
public-figure likenesses, prominent fictional characters, recognizable copyrighted
character designs, logos, trademarks, or imitation of any real person.

Use generic role-based animated characters and original visual designs.
Keep the same animation medium, rendering style, color palette, lighting language,
camera language, character design, environment logic, narration voice, pronunciation,
and pacing across every scene in this project.

The visual video must be exactly 10 seconds. Keep visual action active for the full
duration. Spoken narration must end by 9.0 seconds, leaving the final second for a
clean visual hold, transition, or ambient sound. Never end speech mid-word or mid-sentence.

Burn captions into the video, synchronize them accurately, use short mobile-readable
lines, and keep captions inside the 9:16 Shorts safe area.
```

The system should treat provider policies as authoritative. These prompt rules are application guardrails and should be paired with output validation.

---

## 7. Continuity model

Create one Continuity Profile per project. Later scenes reference it instead of inventing their own style.

```json
{
  "animation_style": {
    "medium": "stylized cinematic 3D animation",
    "rendering": "soft non-photorealistic cinematic rendering",
    "detail_level": "high",
    "realism": "clearly animated, not live action"
  },
  "palette": ["warm amber", "deep blue", "muted brown"],
  "lighting": "soft directional cinematic lighting",
  "camera": {
    "language": "animated documentary",
    "aspect_ratio": "9:16",
    "motion": "smooth controlled camera movement"
  },
  "voice_lock": {
    "voice_id": "documentary_voice_01",
    "accent": "neutral English",
    "speed_wpm": 140,
    "pitch": "medium-low",
    "energy": "calm and cinematic",
    "emotion": "curious and trustworthy"
  },
  "characters": [],
  "environments": [],
  "continuity_rules": []
}
```

### Character continuity

Use stable IDs such as `character_01`, `shopkeeper_group`, or `community_group`. Each ID maps to a canonical appearance description. Scene prompts may use the IDs and expanded descriptions, but must not redesign the characters.

For safety, character descriptions should use generic roles and original traits rather than names or likeness cues for prominent real or fictional characters.

### Voice continuity

Store voice settings as structured data. Prompts must repeat the same voice lock. Exact voice consistency cannot be guaranteed by text prompts alone, so a future production version should use one dedicated TTS voice track across all clips.

---

## 8. Story and fact architecture

Do not generate the final prompt directly from raw user input. First create a structured story.

```json
{
  "hook": "A tiny local idea unexpectedly spread around the world.",
  "central_claim": "The idea expanded because of a repeatable operating model.",
  "ending": "The original concept now exists across many countries.",
  "scenes": [
    {"scene_number": 1, "purpose": "origin", "summary": "Show the small beginning."},
    {"scene_number": 2, "purpose": "breakthrough", "summary": "Show the event that enabled growth."},
    {"scene_number": 3, "purpose": "global_impact", "summary": "Show worldwide reach and takeaway."}
  ]
}
```

### Fact pipeline

```text
User claims
  ↓
Claim extraction
  ↓
Evidence lookup
  ↓
Evidence evaluation
  ↓
Confidence and status
  ↓
Approved facts
  ↓
Narration generation
```

Claim statuses:

```text
verified
partially_verified
uncertain
contradicted
unverified
```

Default policy:

```json
{
  "strictness": "high",
  "allow_uncertain_claims": false,
  "require_sources_for_dates": true,
  "require_sources_for_historical_claims": true,
  "require_sources_for_named_entities": true
}
```

Verified claims may be stated directly. Partially verified claims should use cautious wording. Contradicted claims must not appear in narration. For the first demo, source URLs and claim statuses should be visible in the “Why this prompt?” panel.

---

## 9. Narration and timing rules

Each clip has ten seconds of video but no more than nine seconds of spoken audio.

At approximately 140 words per minute, nine seconds is roughly 21 words. Use a safer default target of 15–20 words per scene.

Backend validation must check:

- Word count
- Estimated duration
- Language
- Sentence completeness
- No abrupt ending
- No unsupported factual claim

If validation fails:

```text
Generate narration
  ↓
Validate
  ├── pass → continue
  └── fail → rewrite with constraints → validate again
```

The narration validator should be deterministic and run after every LLM response.

---

## 10. Multi-stage generation pipeline

Use specialized stages rather than one large LLM call.

### Stage A — Story Architect

Input: topic, facts, audience, tone, duration.  
Output: hook, central claim, ending, scene purposes, fact references.

### Stage B — Scene Planner

Input: story outline, duration, continuity requirements.  
Output: one scene specification per ten-second clip.

### Stage C — Narration Writer

Input: current scene, approved facts, language, tone.  
Output: narration under the timing limit.

### Stage D — Visual Director

Input: current scene, Continuity Profile, previous scene summary.  
Output: animated action, camera, composition, lighting, transition.

### Stage E — Prompt Composer

Input: Production Contract, story, facts, narration, visual direction, guardrails.  
Output: structured `VideoPrompt`.

### Stage F — Validator and Repair

Validate schema, timing, safety, continuity, and completeness. Repair or regenerate failed sections before returning the prompt.

---

## 11. Internal prompt schema

Use JSON internally and render readable Markdown for the user.

```json
{
  "project_id": "uuid",
  "scene_number": 1,
  "total_scenes": 3,
  "duration_seconds": 10,
  "production_contract": {},
  "continuity": {
    "animation_style": "...",
    "palette": "...",
    "camera_language": "...",
    "voice_lock": "..."
  },
  "scene": {
    "purpose": "origin",
    "story_action": "...",
    "camera": "...",
    "composition": "...",
    "transition_in": "...",
    "transition_out": "..."
  },
  "narration": {
    "text": "...",
    "word_count": 18,
    "estimated_duration_seconds": 7.7,
    "end_seconds": 8.8
  },
  "captions": {
    "enabled": true,
    "burned_in": true,
    "style": "mobile-safe synchronized captions"
  },
  "audio": {
    "music": "...",
    "sound_effects": "...",
    "narration_end_seconds": 8.8,
    "final_second": "ambient hold or transition"
  },
  "fact_ids": ["fact_001"],
  "safety_exclusions": [],
  "why_this_prompt": []
}
```

---

## 12. User-facing prompt format

```text
# ANIMATED YOUTUBE SHORT — SCENE 1/3

## PROJECT CONTINUITY
[Locked animation, palette, camera, voice, character, and environment rules]

## SCENE
Purpose: Establish the origin.
Duration: Exactly 10 seconds.
Format: 9:16 vertical.

## STORY ACTION
[Detailed beginning-to-end animated action]

## ANIMATION STYLE
[Original, fully animated visual direction]

## CAMERA AND COMPOSITION
[Vertical framing and camera movement]

## NARRATION
Voice: [locked voice description]
Narration must end by 9.0 seconds.
Script: "[15–20 word narration]"

## CAPTIONS
Burn the narration into synchronized, mobile-safe captions.

## AUDIO
[Music, effects, narration mix, and final-second hold]

## CONTINUITY
[Rules inherited from the project and transition to the next scene]

## SAFETY AND EXCLUSIONS
[No real-person likenesses, prominent characters, logos, trademarks, photorealism, or live action]
```

---

## 13. “Why this prompt?” feature

Add a compact expandable explanation beside each generated prompt:

```text
Why this prompt was generated

✓ Based on verified fact_003
✓ Continues the previous scene
✓ Uses locked character_01
✓ Uses the project animation style
✓ Narration: 18 words / approximately 7.7 seconds
✓ Audio ends before 9 seconds
✓ Satisfies the 9:16 and safety contract
```

This makes the system’s orchestration visible in the demo and helps users trust the output.

---

## 14. Recommended architecture

For the MVP, use a modular monolith.

```text
Next.js / React / TypeScript
              │
              ▼
        FastAPI backend
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
Project    Story       Conversation
Service    Engine      State
   │          │          │
   └──────┬───┴──────────┘
          ▼
       Fact Engine
          ▼
   Continuity Engine
          ▼
      Prompt Engine
          ▼
   Validation Engine
          ▼
      PostgreSQL
```

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- React Hook Form
- Zod
- TanStack Query or equivalent

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- PostgreSQL

### Provider abstraction

```python
class LLMProvider(Protocol):
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
    ) -> dict:
        ...
```

Implement one real provider and one deterministic `MockProvider` for tests. Keep provider-specific code outside the story and prompt domain logic.

---

## 15. Repository structure

```text
animated-short-agent/
├── README.md
├── IMPLEMENTATION_PLAN.md
├── .env.example
├── docker-compose.yml
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── domain/
│   │   ├── services/
│   │   ├── providers/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── policies/
│   └── tests/
├── prompts/
│   ├── story_architect_v1.md
│   ├── scene_planner_v1.md
│   ├── narration_writer_v1.md
│   ├── visual_director_v1.md
│   ├── prompt_composer_v1.md
│   ├── safety_policy_v1.md
│   └── continuity_policy_v1.md
├── database/
│   └── migrations/
├── docs/
│   ├── product-spec.md
│   ├── api.md
│   └── prompt-system.md
└── scripts/
```

---

## 16. Database design

PostgreSQL is the persistent source of truth. Minimum tables:

### `projects`

- `id` UUID primary key
- `topic`
- `duration_seconds`
- `language`
- `tone`
- `audience`
- `visual_preferences` JSONB
- `status`
- `current_scene_number`
- `total_scenes`
- timestamps

### `project_inputs`

- `project_id`
- raw user input
- submitted facts
- source links
- input version

### `facts`

- `id`
- `project_id`
- claim text
- status
- confidence
- evidence JSONB
- source URLs

### `story_outlines`

- `project_id`
- hook
- central claim
- ending
- structured scene plan
- prompt/template version

### `continuity_profiles`

- `project_id`
- animation style
- palette
- lighting
- camera language
- voice lock
- characters
- environments
- continuity rules
- version

### `scenes`

- `project_id`
- scene number
- purpose
- story action
- fact IDs
- previous scene reference
- status

### `generated_prompts`

- `project_id`
- scene ID
- structured prompt JSON
- rendered prompt text
- validation result
- model/provider
- template version
- created timestamp

### `conversation_events`

- `project_id`
- event type
- payload JSONB
- timestamp

---

## 17. State machine

```text
CREATED
  ↓
INPUT_RECEIVED
  ↓
FACT_CHECKING
  ↓
STORY_CREATED
  ↓
SCENES_PLANNED
  ↓
PROMPT_1_READY
  ↓
AWAITING_NEXT
  ↓
PROMPT_2_READY
  ↓
AWAITING_NEXT
  ↓
PROMPT_3_READY
  ↓
COMPLETED
```

Terminal and error states should include `FAILED` with a user-safe error message and an internal diagnostic record.

The `next` operation must be idempotent. If the client retries the request, the backend should return the already-generated scene rather than creating a duplicate prompt.

---

## 18. API contracts

### Create project

```http
POST /api/projects
```

Request:

```json
{
  "topic": "string",
  "facts": ["string"],
  "source_urls": ["string"],
  "language": "English",
  "tone": "curious documentary",
  "audience": "general",
  "visual_preferences": {},
  "duration_seconds": 30
}
```

Response: project ID, status, scene count, and initial processing status.

### Generate first prompt

```http
POST /api/projects/{project_id}/generate
```

Response: Prompt 1 plus validation summary and project state.

### Generate next prompt

```http
POST /api/projects/{project_id}/prompts/next
```

Rules:

- Reject if the project is not awaiting the next scene.
- Return the next deterministic scene.
- Never exceed three prompts.
- Return the existing prompt on safe retry.

### Regenerate prompt

```http
POST /api/projects/{project_id}/prompts/{scene_number}/regenerate
```

Regeneration must preserve the story, continuity profile, facts, duration, voice lock, and safety contract unless the user explicitly changes a project setting.

### Export project

```http
GET /api/projects/{project_id}/export
```

Return Markdown and JSON representations containing the story, continuity profile, facts, prompts, validation summaries, and template versions.

---

## 19. Validation requirements

### Input validation

- Topic is required.
- Duration must be `10`, `20`, or `30`.
- Language must be supported.
- Input size must be limited.
- Source URLs must be validated and sanitized.

### Prompt validation

- Exactly 10 seconds.
- 9:16 format.
- Fully animated visual direction.
- No photorealism or live action.
- No prohibited likeness or recognizable copyrighted design instructions.
- Narration ends by 9 seconds.
- Caption instructions are present.
- Audio instructions are present.
- Voice lock is present.
- Continuity references are present.
- Scene purpose and transition are present.
- All factual claims map to approved fact IDs.

### Repair loop

```text
Generate candidate
  ↓
Parse structured output
  ↓
Validate schema and policy
  ├── pass → save and return
  └── fail → repair targeted fields
                 ↓
              validate again
```

Limit repair attempts to avoid runaway cost. If validation still fails, return a safe failure state and preserve the diagnostic details internally.

---

## 20. Frontend screens

### Screen 1 — New Short

Fields:

- Topic
- Facts and sources
- Language
- Tone
- Audience
- Visual style
- Duration selector: 10 / 20 / 30 seconds

### Screen 2 — Project workspace

Show:

- Story hook and outline
- Fact status
- Continuity Lock summary
- Scene progress: `1/3`, `2/3`, `3/3`
- Current generated prompt
- Copy button
- Generate Next button
- Regenerate button
- Why this prompt panel

### Screen 3 — Completed project

Show:

- All prompts
- Copy all
- Export Markdown
- Export JSON
- Fact and continuity summary

The initial UI should optimize for a clear demo rather than a full production dashboard.

---

## 21. Milestone plan

### Milestone 0 — Repository foundation

Deliver:

- Frontend and backend folders
- Local development instructions
- Environment configuration
- Basic health endpoint
- Mock provider
- Initial README

Acceptance criteria:

- Frontend starts locally.
- Backend starts locally.
- Mock request returns a valid response.

### Milestone 1 — Project creation and state

Deliver:

- Project input schema
- Duration validation
- Project persistence
- State machine
- Create and retrieve APIs

Acceptance criteria:

- Invalid durations are rejected by the backend.
- A project persists with the correct scene count.
- State transitions are deterministic.

### Milestone 2 — Story and scene planning

Deliver:

- Story Architect schema
- Scene Planner schema
- Fact objects and statuses
- Initial Continuity Profile

Acceptance criteria:

- 10 seconds creates one scene.
- 20 seconds creates two scenes.
- 30 seconds creates three scenes.
- Every scene has a purpose and transition.

### Milestone 3 — Prompt engine

Deliver:

- Central policy templates
- Narration writer
- Timing validator
- Visual director
- Prompt composer
- Structured prompt parser

Acceptance criteria:

- Every returned prompt contains the required sections.
- Narration is within the timing budget.
- All prompts include the same style and voice lock.

### Milestone 4 — One-at-a-time generation

Deliver:

- Generate first prompt endpoint
- Generate next endpoint
- Idempotency behavior
- Project completion state
- Prompt history

Acceptance criteria:

- Prompt 2 cannot be generated before Prompt 1.
- Prompt count never exceeds three.
- Repeated requests do not duplicate prompts.

### Milestone 5 — Demo-quality frontend

Deliver:

- New Short form
- Project workspace
- Continuity Lock card
- Prompt display and copy controls
- Generate Next interaction
- Why this prompt panel
- Completion and export view

Acceptance criteria:

- A judge can complete the entire flow without developer assistance.
- The continuity state is visibly preserved between scenes.

### Milestone 6 — Fact grounding and refinement

Deliver:

- Claim extraction
- Source/evidence records
- Confidence display
- Regeneration
- Version tracking
- Regression test dataset

Acceptance criteria:

- Unsupported claims are removed or softened.
- Regenerated prompts retain the Production Contract.
- Template versions are stored with prompts.

---

## 22. Testing strategy

### Unit tests

Test:

- Duration-to-scene mapping
- State transitions
- Narration word and duration limits
- Prompt policy injection
- Character continuity expansion
- Voice lock preservation
- Safety checks
- Idempotent next-scene generation
- Export formatting

### Integration tests

Test the complete flow for 10, 20, and 30 seconds using the MockProvider.

### LLM contract tests

Verify that malformed or incomplete model responses are repaired or rejected safely.

### Evaluation dataset

Create an initial set of 50–100 topics across:

- History
- Science
- Business
- Technology
- Geography
- Inventions
- Culture
- Mysteries
- Biographies

Score:

- Factual grounding
- Story clarity
- Hook quality
- Narration timing
- Visual specificity
- Continuity
- Safety
- Caption completeness

---

## 23. Observability and reproducibility

Record for every generation:

- Project ID
- Scene number
- Model/provider
- Prompt-template versions
- Input hash
- Continuity-profile version
- Fact IDs used
- Validation results
- Repair attempts
- Latency
- Token/cost metadata when available

This makes failures debuggable and allows prompt-template regression testing.

---

## 24. Security and cost controls

### Security

- Keep API keys in environment variables.
- Validate and sanitize all inputs.
- Use UUID project IDs.
- Apply request size limits.
- Rate-limit generation endpoints.
- Parameterize database queries.
- Sanitize exported content.
- Do not expose internal provider errors to users.

### Cost control

- Cache fact research, story outlines, and continuity profiles.
- Do not resend the entire conversation to the model.
- Send only compressed project state, relevant facts, and the current scene.
- Use the MockProvider in tests and demos where possible.
- Store hashes to avoid unnecessary regeneration.
- Limit repair attempts.

Suggested cache keys:

```text
story:{input_hash}
facts:{claim_hash}
continuity:{story_version}
narration:{scene_version}:{language}:{tone}
```

---

## 25. Devpost demo plan

The demo should show the continuity problem and the solution visually.

### Demo sequence

1. Enter a factual topic.
2. Select 30 seconds and animated documentary style.
3. Show the generated story outline.
4. Show the locked style, voice, palette, characters, and environment.
5. Generate Prompt 1.
6. Expand “Why this prompt?” to show fact, timing, continuity, and safety checks.
7. Click “Generate Next.”
8. Show that Prompt 2 inherits the same production state.
9. Generate Prompt 3.
10. Export the complete prompt package.

### Demonstration message

```text
This is not three independent prompts.
It is one production state rendered into three validated scenes.
```

### Competition positioning

Emphasize:

- Stateful orchestration
- Deterministic scene progression
- Production Contracts
- Fact-grounded narration
- Continuity locking
- Structured outputs
- Validation and repair
- Explainable generation

Avoid presenting the project as only an AI prompt generator.

---

## 26. Definition of done

The MVP is complete when:

1. A user can create a project from a topic.
2. The user can select 10, 20, or 30 seconds.
3. The backend creates the correct number of scenes.
4. Important factual claims are tracked and validated.
5. A story outline is stored before prompt generation.
6. A Continuity Profile is stored before scene rendering.
7. Prompt 1 is generated and shown.
8. The system waits for an explicit next action.
9. Prompt 2 and Prompt 3 preserve continuity.
10. Each prompt is exactly for a ten-second 9:16 animated clip.
11. Narration ends by nine seconds.
12. Captions and audio instructions are included.
13. Safety exclusions are included and validated.
14. Prompt regeneration preserves the Production Contract.
15. Prompts can be copied and exported.
16. A judge can run the end-to-end demo locally.

---

## 27. Future roadmap

After the MVP:

1. Dedicated TTS generation with a reusable voice ID.
2. Direct video-generation provider integration.
3. Clip upload and continuity review.
4. Automatic caption timing from generated audio.
5. Timeline assembly and export.
6. Style-lock editing.
7. Prompt version trees and rollback.
8. Additional video formats and durations.
9. Multi-provider generation.
10. YouTube metadata, thumbnails, and publishing workflows.
11. User accounts and collaboration.
12. Automated quality scoring and model evaluation.

---

## 28. First coding milestone

The first implementation should be deliberately narrow:

```text
Create project
  ↓
Use MockProvider to create story + continuity + scenes
  ↓
Generate Prompt 1
  ↓
Generate Prompt 2
  ↓
Generate Prompt 3
  ↓
Export Markdown
```

Before connecting a real LLM or research provider, prove that the state machine, schemas, continuity lock, timing validator, and one-at-a-time flow work end to end. This establishes a reliable foundation for later AI integration.

