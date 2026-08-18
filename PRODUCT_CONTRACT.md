# Animated YouTube Shorts Prompt Agent

## Product Contract v1

This document defines the behavior that the MVP must preserve as providers, n8n workflows, and media generation are added.

## 1. Scope

The MVP generates structured prompts for fully animated YouTube Shorts. It does not generate or publish video directly.

Each prompt describes one ten-second vertical clip. A project contains one, two, or three connected clips.

## 2. Allowed durations

Only these values are valid: `10`, `20`, or `30` seconds. These map to one, two, or three ten-second prompts. The backend is authoritative; all other values return a validation error.

## 3. Production Contract

```json
{
  "duration_seconds": 10,
  "aspect_ratio": "9:16",
  "narration_max_seconds": 9,
  "animation_only": true,
  "voice_id": "documentary_voice_01",
  "safety_policy_version": "global_video_policy_v1",
  "prompt_template_version": "prompt_composer_v1"
}
```

## 4. Required prompt structure

Every user-facing prompt must contain these headings in this order:

1. `FORMAT`
2. `CONTINUITY LOCK — MUST REMAIN IDENTICAL`
3. `SCENE / VISUAL STORY`
4. `CAMERA AND COMPOSITION`
5. `NARRATION — EXACT SCRIPT`
6. `CAPTIONS`
7. `AUDIO`
8. `SAFETY AND EXCLUSIONS`
9. `FINAL GENERATION REQUIREMENTS`

Narration must be exact script text, captions must be synchronized to it, and the final second must contain no spoken words.

## 5. Safety baseline

Prompts require fully animated non-photorealistic visuals, original generic characters, no real-person likenesses, no named prominent figures for likeness generation, no recognizable copyrighted characters, no logos, no trademarks, and no live-action footage.

## 6. Project state transitions

```text
CREATED → INPUT_RECEIVED → FACT_CHECKING → STORY_CREATED → SCENES_PLANNED → AWAITING_NEXT → COMPLETED
```

Prompt 1 may be generated after scenes are planned. Later prompts are generated in order. Repeated completed requests return the existing prompt idempotently. Regeneration requires an existing prompt and creates a new immutable version. A project never exceeds three current prompts.

## 7. Locked and editable fields

Locked after story planning: duration, scene count, approved story outline, continuity profile, animation style, palette, camera language, voice lock, safety policy version, and approved fact references.

Editable before generation: topic wording, user facts, source URLs, tone, audience, and visual preferences.

Changing a locked field requires a new project version or explicit downstream invalidation.

## 8. Quality thresholds

A prompt is accepted only when timing, safety, and structure scores are `1.0`, overall quality is at least `0.90`, and narration ends before nine seconds.

## 9. Retention baseline

Retain project inputs, approved facts, evidence references, story and continuity versions, current and prior prompt versions, validation reports, audit events, integration events, export manifests, and checksums.

Do not retain provider API keys, unnecessary raw source pages, unrelated personal data, or temporary binary files after their retention window.

Initial recommendation: metadata and audit records for one year, temporary exports for 30 days, and generated media for 30 days until published. Make this configurable before production launch.

## 10. API error categories

Use stable machine-readable error codes and a correlation ID:

| Category | HTTP status |
|---|---:|
| Invalid input | 400 |
| Unauthenticated | 401 |
| Forbidden | 403 |
| Not found | 404 |
| Conflict / idempotency mismatch | 409 |
| Rate limited | 429 |
| Provider failure | 502 |
| Dependency unavailable | 503 |

## 11. Version and change policy

Every prompt and export records `prompt_composer_v1`, `global_video_policy_v1`, and `documentary_voice_01` or their future versions.

Changes to duration, headings, safety, state transitions, or retention must update this contract, increment the relevant version, add regression tests, and document migration behavior.

