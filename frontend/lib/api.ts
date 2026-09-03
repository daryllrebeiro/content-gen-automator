export type Duration = 10 | 20 | 30;

export type Platform = "YOUTUBE_SHORTS" | "TIKTOK" | "INSTAGRAM_REELS";

export type PlatformExport = {
  platform: Platform;
  aspect_ratio: string;
  output_asset_ref: string;
  export_status: string;
  publish_status: string;
  publish_asset_ref?: string | null;
  publish_metadata?: Record<string, any>;
};

export type VideoProviderCatalogItem = {
  id: string;
  name: string;
  cost_per_scene: string;
  estimated_latency: string;
  strengths: string;
  is_available: boolean;
  disabled_reason?: string | null;
};

export type ModelTierItem = {
  id: string;
  display_name: string;
  screenwriter_model: string;
  cinematographer_model: string;
  governance_model: string;
  estimated_cost_per_draft: string;
  estimated_latency_ms: string;
  description: string;
};

export type StudioPreset = {
  id: string;
  name: string;
  description: string;
  target_platforms: Platform[];
  video_provider: string;
  model_tier: string;
  policy_pack_id: string;
  suggested_topic?: string;
  suggested_duration?: Duration;
  suggested_tone?: string;
  suggested_style?: string;
  is_system_preset?: boolean;
};

export type ProjectInput = {
  topic: string;
  facts: string[];
  language: string;
  tone: string;
  audience: string;
  visual_preferences: Record<string, string>;
  duration_seconds: Duration;
  autonomous: boolean;
  tts_provider: string;
  video_provider: string;
  stitch_provider: string;
  publish_provider: string;
  target_platforms?: Platform[];
  model_tier?: string;
};



export type Prompt = {
  scene_number: number;
  total_scenes: number;
  duration_seconds: number;
  text: string;
  narration: string;
  narration_word_count: number;
  estimated_narration_seconds: number;
  version_number: number;
  template_version: string;
  why_this_prompt: string[];
  quality_scores: Record<string, number>;
};

export type Project = {
  id: string;
  status: string;
  topic: string;
  duration_seconds: number;
  current_scene_number: number;
  total_scenes: number;
  story_hook: string;
  story_central_claim: string;
  story_ending: string;
  facts: { id: string; text: string; status: string; confidence: number; sources: string[]; notes: string; approved_for_narration: boolean }[];
  scenes: { number: number; purpose: string; summary: string; previous_scene_number: number | null }[];
  continuity: {
    animation_style: string;
    palette: string;
    camera_language: string;
    voice_id: string;
    voice_description: string;
    continuity_rules: string[];
  };
  prompts: Prompt[];
  tts_provider: string;
  video_provider: string;
  stitch_provider: string;
  publish_provider: string;
  target_platforms?: string[];
  model_tier?: string;
  platform_exports?: Record<string, PlatformExport>;
};


export type ExportBundle = {
  project_id: string;
  markdown: string;
  publishing: { title: string; description: string; hashtags: string[]; pinned_comment: string };
  data: Record<string, unknown>;
};

export type ApprovalResponse = {
  project_id: string;
  scene_number: number;
  decision: string;
  status: string;
};

export type ProductionJob = {
  job_id: string;
  project_id: string;
  scene_number: number;
  prompt_version: number;
  job_type: string;
  provider: string;
  provider_job_id: string;
  status: string;
  contract: Record<string, unknown>;
  artifact_id: string;
  error: string;
};

export type ClipArtifact = {
  artifact_id: string;
  job_id: string;
  checksum: string;
  duration_seconds: number;
  aspect_ratio: string;
  narration_end_seconds: number;
  artifact_url: string;
  review_status: string;
  created_at: string;
};

export type ClipReviewResponse = {
  project_id: string;
  scene_number: number;
  artifact_id: string;
  decision: string;
  actor: string;
  status: string;
};

export type FinalReviewStatusResponse = {
  project_id: string;
  has_review: boolean;
  decision: string | null;
  actor: string | null;
  manifest_id: string | null;
  comment: string | null;
};

export type FinalReviewResponse = {
  project_id: string;
  decision: string;
  actor: string;
  manifest_id: string;
  project_status: string;
};

export type GateReportResponse = {
  can_publish: boolean;
  failed_gates: string[];
};

export type PublishResponse = {
  job_id: string;
  project_id: string;
  manifest_id: string;
  status: string;
  upload_checksum: string;
};

export type YouTubeUploadJob = {
  job_id: string;
  project_id: string;
  manifest_id: string;
  status: string;
  youtube_video_id: string;
  upload_attempts: number;
  error_class: string;
  youtube_url: string;
  error: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createProject(input: ProjectInput) {
  return request<Project>("/api/projects", { method: "POST", body: JSON.stringify(input) });
}

export function getProject(projectId: string) {
  return request<Project>(`/api/projects/${projectId}`);
}

export function generatePrompt(projectId: string) {
  return request<Prompt>(`/api/projects/${projectId}/prompts/next`, { method: "POST" });
}

export function regeneratePrompt(projectId: string, sceneNumber: number) {
  return request<Prompt>(`/api/projects/${projectId}/prompts/${sceneNumber}/regenerate`, { method: "POST" });
}

export function approvePrompt(projectId: string, sceneNumber: number, actor = "user", comment = "") {
  return request<ApprovalResponse>(`/api/projects/${projectId}/prompts/${sceneNumber}/approve`, {
    method: "POST",
    body: JSON.stringify({ actor, comment }),
  });
}

export function rejectPrompt(projectId: string, sceneNumber: number, actor = "user", comment = "") {
  return request<ApprovalResponse>(`/api/projects/${projectId}/prompts/${sceneNumber}/reject`, {
    method: "POST",
    body: JSON.stringify({ actor, comment }),
  });
}

export function exportProject(projectId: string) {
  return request<ExportBundle>(`/api/projects/${projectId}/export`);
}

// ── Production APIs ─────────────────────────────────────────────────────────

export function submitProduction(projectId: string, sceneNumber: number) {
  return request<ProductionJob>(`/api/projects/${projectId}/scenes/${sceneNumber}/production`, { method: "POST" });
}

export function mockCompleteProduction(projectId: string, jobId: string) {
  return request<ProductionJob>(`/api/projects/${projectId}/production-jobs/${jobId}/mock-complete`, { method: "POST" });
}

export function getProductionJobs(projectId: string) {
  return request<ProductionJob[]>(`/api/projects/${projectId}/production-jobs`);
}

export function getClips(projectId: string) {
  return request<ClipArtifact[]>(`/api/projects/${projectId}/clips`);
}

export function reviewClip(projectId: string, sceneNumber: number, artifactId: string, decision: "approved" | "rejected", actor = "user", comment = "") {
  return request<ClipReviewResponse>(`/api/projects/${projectId}/clips/${sceneNumber}/review`, {
    method: "POST",
    body: JSON.stringify({ artifact_id: artifactId, decision, actor, comment }),
  });
}

// ── Publishing APIs ─────────────────────────────────────────────────────────

export function getFinalReview(projectId: string) {
  return request<FinalReviewStatusResponse>(`/api/projects/${projectId}/final-review`);
}

export function approveFinal(projectId: string, manifestId: string, actor = "user", comment = "") {
  return request<FinalReviewResponse>(`/api/projects/${projectId}/final-review/approve`, {
    method: "POST",
    body: JSON.stringify({ manifest_id: manifestId, actor, comment }),
  });
}

export function rejectFinal(projectId: string, manifestId: string, actor = "user", comment = "") {
  return request<FinalReviewResponse>(`/api/projects/${projectId}/final-review/reject`, {
    method: "POST",
    body: JSON.stringify({ manifest_id: manifestId, actor, comment }),
  });
}

export function checkGate(projectId: string) {
  return request<GateReportResponse>(`/api/projects/${projectId}/publish/gate`);
}

export function publishProject(projectId: string, actor = "user") {
  const idempotencyKey = `publish-${projectId}-${Date.now()}`;
  return request<PublishResponse>(`/api/projects/${projectId}/publish`, {
    method: "POST",
    body: JSON.stringify({ actor, idempotency_key: idempotencyKey }),
  });
}

export function getYoutubeUploadJobs(projectId: string) {
  return request<YouTubeUploadJob[]>(`/api/projects/${projectId}/youtube-upload-jobs`);
}

export function mockCompleteYoutubeUpload(projectId: string, jobId: string, success = true) {
  return request<YouTubeUploadJob>(`/api/projects/${projectId}/youtube-upload-jobs/${jobId}/mock-complete?success=${success}`, { method: "POST" });
}

export function fetchVideoProviders() {
  return request<VideoProviderCatalogItem[]>("/api/catalog/video-providers");
}

export function fetchModelTiers() {
  return request<ModelTierItem[]>("/api/catalog/model-tiers");
}

export function fetchStudioPresets() {
  return request<StudioPreset[]>("/api/presets");
}

export function createStudioPreset(preset: Partial<StudioPreset>) {
  return request<StudioPreset>("/api/presets", {
    method: "POST",
    body: JSON.stringify(preset),
  });
}

export function fetchPlatformExports(projectId: string) {
  return request<Record<string, PlatformExport>>(`/api/projects/${projectId}/platform-exports`);
}
