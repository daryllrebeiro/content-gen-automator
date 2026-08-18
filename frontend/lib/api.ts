export type Duration = 10 | 20 | 30;

export type ProjectInput = {
  topic: string;
  facts: string[];
  language: string;
  tone: string;
  audience: string;
  visual_preferences: Record<string, string>;
  duration_seconds: Duration;
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

export function generatePrompt(projectId: string) {
  return request<Prompt>(`/api/projects/${projectId}/prompts/next`, { method: "POST" });
}

export function regeneratePrompt(projectId: string, sceneNumber: number) {
  return request<Prompt>(`/api/projects/${projectId}/prompts/${sceneNumber}/regenerate`, { method: "POST" });
}
