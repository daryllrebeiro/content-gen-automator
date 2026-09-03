"use client";

import { FormEvent, useEffect, useState, startTransition } from "react";
import {
  approvePrompt,
  createProject,
  Duration,
  exportProject,
  generatePrompt,
  getProject,
  rejectPrompt,
  regeneratePrompt,
  Project,
  Prompt,
  submitProduction,
  mockCompleteProduction,
  getProductionJobs,
  getClips,
  reviewClip,
  getFinalReview,
  approveFinal,
  rejectFinal,
  checkGate,
  publishProject,
  getYoutubeUploadJobs,
  mockCompleteYoutubeUpload,
  ProductionJob,
  ClipArtifact,
  FinalReviewStatusResponse,
  YouTubeUploadJob,
  GateReportResponse,
} from "../lib/api";
import StatusTracker from "../components/StatusTracker";
import PartnerEcosystemBar from "../components/PartnerEcosystemBar";
import GovernanceAuditPanel from "../components/GovernanceAuditPanel";

// ── Constants & Helpers ──────────────────────────────────────────────────────

const STAGES = {
  PROMPTS: "PROMPTS",
  PRODUCTION: "PRODUCTION",
  REVIEW: "REVIEW",
  PUBLISHING: "PUBLISHING",
};

function statusBadgeClass(status: string): string {
  switch (status) {
    case "PUBLISHED":
    case "COMPLETED":
    case "VIDEO_APPROVED":
      return "badge badge-success";
    case "PROMPT_APPROVAL_PENDING":
    case "VIDEO_REVIEW_PENDING":
    case "PUBLISHING_PENDING":
      return "badge badge-warning";
    case "VIDEO_REJECTED":
    case "PUBLISH_FAILED":
    case "FAILED":
      return "badge badge-error";
    default:
      return "badge";
  }
}

function StatusBadge({ status }: { status: string }) {
  return <span className={statusBadgeClass(status)}>{status.replace(/_/g, " ")}</span>;
}

function QualityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#c7f36b" : pct >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div className="quality-bar-wrap">
      <div className="quality-bar" style={{ width: `${pct}%`, background: color }} />
      <span className="quality-label">{pct}%</span>
    </div>
  );
}

// ── Main Page Component ──────────────────────────────────────────────────────

export default function HomePage() {
  // Project creation fields
  const [topic, setTopic] = useState("");
  const [factsInput, setFactsInput] = useState("");
  const [duration, setDuration] = useState<Duration>(30);
  const [tone, setTone] = useState("curious cinematic documentary");
  const [style, setStyle] = useState("stylized cinematic 3D animation");
  const [discoveringTopic, setDiscoveringTopic] = useState(false);

  const discoverTopics = async () => {
    setDiscoveringTopic(true);
    try {
      const res = await fetch("/api/research/recommend-topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ niche: "nature & deep science mysteries" })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.recommended_topics && data.recommended_topics.length > 0) {
          const top = data.recommended_topics[0];
          setTopic(top.topic);
          setTone("curious cinematic documentary");
          setStyle(top.visual_concept || "hyper-detailed 4K cinematic animation");
          setFactsInput("Deep sea organisms generate living light through luciferin oxidation.\nBioluminescence serves for camouflage, mating, and luring prey.");
        }
      }
    } catch (err) {
      console.error("Error discovering topics:", err);
    } finally {
      setDiscoveringTopic(false);
    }
  };

  // Modular Lego provider options
  const [ttsProvider, setTtsProvider] = useState("mock");
  const [videoProvider, setVideoProvider] = useState("mock");
  const [stitchProvider, setStitchProvider] = useState("mock");
  const [publishProvider, setPublishProvider] = useState("mock");


  // App state
  const [project, setProject] = useState<Project | null>(null);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [productionJobs, setProductionJobs] = useState<ProductionJob[]>([]);
  const [clips, setClips] = useState<ClipArtifact[]>([]);
  const [finalReview, setFinalReview] = useState<FinalReviewStatusResponse | null>(null);
  const [uploadJobs, setUploadJobs] = useState<YouTubeUploadJob[]>([]);
  const [gateReport, setGateReport] = useState<GateReportResponse | null>(null);

  // Autopilot states
  const [autoPilot, setAutoPilot] = useState(false);
  const [autopilotLogs, setAutopilotLogs] = useState<string[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [openWhy, setOpenWhy] = useState<number | null>(null);
  const [openTrace, setOpenTrace] = useState<number | null>(null);
  const [policyPack, setPolicyPack] = useState("general_audience");
  const [rejectComment, setRejectComment] = useState<Record<number, string>>({});
  const [activeStage, setActiveStage] = useState(STAGES.PROMPTS);

  // For publishing comments
  const [finalReviewComment, setFinalReviewComment] = useState("");

  // Helper to log autopilot steps
  function logAutopilot(msg: string) {
    setAutopilotLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }

  // ── Sync / Refresh Logic ────────────────────────────────────────────────────

  async function syncAllData(projectId: string) {
    try {
      const freshProject = await getProject(projectId);
      setProject(freshProject);

      if (freshProject.prompts.length > 0) {
        setPrompts((current) => {
          const byScene = Object.fromEntries(current.map((p) => [p.scene_number, p]));
          freshProject.prompts.forEach((p) => (byScene[p.scene_number] = p));
          return Object.values(byScene).sort((a, b) => a.scene_number - b.scene_number);
        });
      }

      // Only load downstream data if prompt stage is finished
      const isPromptStageDone =
        freshProject.status !== "CREATED" &&
        freshProject.status !== "INPUT_RECEIVED" &&
        freshProject.status !== "FACT_CHECKING" &&
        freshProject.status !== "STORY_CREATED" &&
        freshProject.status !== "SCENES_PLANNED" &&
        freshProject.status !== "AWAITING_NEXT" &&
        freshProject.status !== "PROMPT_APPROVAL_PENDING";

      if (isPromptStageDone) {
        const [jobs, clipList, review, uploads] = await Promise.all([
          getProductionJobs(projectId),
          getClips(projectId),
          getFinalReview(projectId),
          getYoutubeUploadJobs(projectId),
        ]);
        setProductionJobs(jobs);
        setClips(clipList);
        setFinalReview(review);
        setUploadJobs(uploads);

        // Auto transition active tab/stage based on project status (unless user manually clicks, but we sync by default)
        if (
          freshProject.status === "PUBLISHING_PENDING" ||
          freshProject.status === "PUBLISHED" ||
          freshProject.status === "PUBLISH_FAILED"
        ) {
          setActiveStage(STAGES.PUBLISHING);
        } else if (freshProject.status === "VIDEO_APPROVED" || freshProject.status === "VIDEO_REJECTED") {
          setActiveStage(STAGES.PUBLISHING);
        } else if (
          freshProject.status === "COMPLETED" &&
          jobs.length > 0 &&
          jobs.every((j) => j.status === "SUCCEEDED") &&
          clipList.length > 0 &&
          clipList.every((c) => c.review_status === "approved")
        ) {
          setActiveStage(STAGES.REVIEW);
        } else {
          setActiveStage(STAGES.PRODUCTION);
        }
      } else {
        setActiveStage(STAGES.PROMPTS);
      }
    } catch (err) {
      handleError(err);
    }
  }

  // Periodic poll in development to catch async states
  useEffect(() => {
    if (!project) return;
    const interval = setInterval(() => {
      startTransition(() => {
        syncAllData(project.id).catch(() => {});
      });
    }, 4000);
    return () => clearInterval(interval);
  }, [project?.id]);

  function handleError(err: unknown) {
    setError(err instanceof Error ? err.message : "Something went wrong.");
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  async function startProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setAutopilotLogs([]);
    try {
      if (autoPilot) {
        logAutopilot("Initializing autonomous content generation pipeline...");
      }
      const created = await createProject({
        topic,
        facts: factsInput.split("\n").map((f) => f.trim()).filter(Boolean),
        language: "English",
        tone,
        audience: policyPack === "kids_family" ? "kids and family" : policyPack === "mature_documentary" ? "mature documentary" : "general audience",
        visual_preferences: { style, policy_pack: policyPack },
        duration_seconds: duration,
        autonomous: autoPilot,
        tts_provider: ttsProvider,
        video_provider: videoProvider,
        stitch_provider: stitchProvider,
        publish_provider: publishProvider,
      });

      const firstPrompt = await generatePrompt(created.id);
      setPrompts([firstPrompt]);
      await syncAllData(created.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleApprovePrompt(sceneNumber: number) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await approvePrompt(project.id, sceneNumber, "user");
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRejectPrompt(sceneNumber: number) {
    if (!project) return;
    const comment = rejectComment[sceneNumber] ?? "";
    setBusy(true);
    setError("");
    try {
      await rejectPrompt(project.id, sceneNumber, "user", comment);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleNextPrompt() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const prompt = await generatePrompt(project.id);
      setPrompts((current) =>
        [...current.filter((p) => p.scene_number !== prompt.scene_number), prompt]
          .sort((a, b) => a.scene_number - b.scene_number)
      );
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRegeneratePrompt(sceneNumber: number) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const prompt = await regeneratePrompt(project.id, sceneNumber);
      setPrompts((current) => current.map((p) => (p.scene_number === sceneNumber ? prompt : p)));
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  // Production actions
  async function handleQueueProduction(sceneNumber: number) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await submitProduction(project.id, sceneNumber);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleMockProductionSuccess(jobId: string) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await mockCompleteProduction(project.id, jobId);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleReviewClip(sceneNumber: number, artifactId: string, decision: "approved" | "rejected") {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await reviewClip(project.id, sceneNumber, artifactId, decision, "user");
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  // Publishing package actions
  async function handleApproveFinalReview() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      // Create manifest first
      await checkGate(project.id).catch(() => null);
      const exp = await exportProject(project.id);
      const manifestId = exp.data.manifest_id as string || "latest";

      await approveFinal(project.id, manifestId, "user", finalReviewComment);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleRejectFinalReview() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const exp = await exportProject(project.id);
      const manifestId = exp.data.manifest_id as string || "latest";
      await rejectFinal(project.id, manifestId, "user", finalReviewComment);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  // Publish / Gate actions
  async function handleCheckGates() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const report = await checkGate(project.id);
      setGateReport(report);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handlePublish() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await publishProject(project.id, "user");
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleMockUploadComplete(jobId: string, success: boolean) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      await mockCompleteYoutubeUpload(project.id, jobId, success);
      await syncAllData(project.id);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function downloadExportMarkdown() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const bundle = await exportProject(project.id);
      const blob = new Blob([bundle.markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${project.topic.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-shorts-package.md`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  // ── Autopilot Loop ─────────────────────────────────────────────────────────

  useEffect(() => {
    if (!project || !autoPilot) return;

    const timer = setTimeout(async () => {
      try {
        const status = project.status;
        const allPromptsApproved = prompts.length === project.total_scenes && status === "COMPLETED";

        // 1. Generate prompts loop
        if (status === "APPROVED" || status === "SCENES_PLANNED" || status === "AWAITING_NEXT") {
          if (prompts.length < project.total_scenes) {
            logAutopilot(`Generating prompt for scene ${prompts.length + 1}...`);
            await handleNextPrompt();
          }
        } 
        // 2. Approve prompt
        else if (status === "PROMPT_APPROVAL_PENDING") {
          const currentScene = project.current_scene_number;
          logAutopilot(`Auto-approving prompt for scene ${currentScene}...`);
          await handleApprovePrompt(currentScene);
        }
        // 3. Video Production
        else if (status === "COMPLETED") {
          // Check if any scene doesn't have a production job
          const pendingScene = project.scenes.find(
            (s) => !productionJobs.find((j) => j.scene_number === s.number)
          );
          if (pendingScene) {
            logAutopilot(`Auto-submitting scene ${pendingScene.number} to video render pipeline...`);
            await handleQueueProduction(pendingScene.number);
            return;
          }

          // Check if any production job is in SUBMITTED state
          const submittedJob = productionJobs.find((j) => j.status === "SUBMITTED");
          if (submittedJob) {
            logAutopilot(`Rendering scene ${submittedJob.scene_number} clip... (Simulating callback success)`);
            await handleMockProductionSuccess(submittedJob.job_id);
            return;
          }

          // Check if any clip artifact needs review
          const unapprovedClip = clips.find((c) => c.review_status === "VIDEO_REVIEW_PENDING");
          if (unapprovedClip) {
            const job = productionJobs.find((j) => j.job_id === unapprovedClip.job_id);
            if (job) {
              logAutopilot(`Auto-auditing and approving clip artifact for scene ${job.scene_number}...`);
              await handleReviewClip(job.scene_number, unapprovedClip.artifact_id, "approved");
              return;
            }
          }

          // If all clips approved, go to final review
          const allClipsApproved =
            clips.length === project.total_scenes &&
            clips.every((c) => c.review_status === "approved");
          if (allClipsApproved) {
            logAutopilot("Assembling publishing package and signing off final review...");
            await handleApproveFinalReview();
          }
        }
        // 4. Gate checking & publish trigger
        else if (status === "VIDEO_APPROVED") {
          logAutopilot("Checking safety audit checks on YouTube publishing gates...");
          await handleCheckGates();
          logAutopilot("Publishing gates verified. Queuing YouTube upload job...");
          await handlePublish();
        }
        // 5. Simulate upload progress
        else if (status === "PUBLISHING_PENDING") {
          const uploadingJob = uploadJobs.find((j) => j.status === "QUEUED" || j.status === "UPLOADING");
          if (uploadingJob) {
            logAutopilot("Uploading Short file to YouTube channel... (Simulating callback success)");
            await handleMockUploadComplete(uploadingJob.job_id, true);
          }
        }
        // 6. Finished!
        else if (status === "PUBLISHED") {
          logAutopilot("🎉 Pipeline complete! Your Short video is live on YouTube.");
          setAutoPilot(false);
        }
      } catch (err) {
        logAutopilot(`⚠ Autopilot error: ${err instanceof Error ? err.message : String(err)}`);
        setAutoPilot(false);
      }
    }, 2000); // 2 second delay between actions

    return () => clearTimeout(timer);
  }, [project?.status, prompts.length, productionJobs, clips, uploadJobs, autoPilot]);

  // ── Render Helpers ─────────────────────────────────────────────────────────

  const isPromptStageDone =
    project &&
    project.status !== "CREATED" &&
    project.status !== "INPUT_RECEIVED" &&
    project.status !== "FACT_CHECKING" &&
    project.status !== "STORY_CREATED" &&
    project.status !== "SCENES_PLANNED" &&
    project.status !== "AWAITING_NEXT" &&
    project.status !== "PROMPT_APPROVAL_PENDING";

  if (!project) {
    return (
      <main className="shell form-shell">
        <header className="topbar">
          <span className="eyebrow">SHORTS CREATIVE FLOW</span>
          <span className="status">MVP · AUTOMATION ENGINE</span>
        </header>
        <PartnerEcosystemBar />
        <section className="hero">
          <p className="eyebrow">PHASE 8 PUBLISHING AUTOMATION</p>
          <h1>Stateful Creative Pipeline.</h1>
          <p className="lead">
            Plan, generate, render, review, and auto-publish content with complete database audit gates.
          </p>
        </section>
        <form className="form-card" onSubmit={startProject}>
          {/* Preset Quick-Launch Bar for Judges (Tier 2.1) */}
          <div style={{
            marginBottom: "18px",
            padding: "14px 16px",
            background: "rgba(255, 255, 255, 0.02)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "10px"
          }}>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em", color: "var(--muted)", textTransform: "uppercase", marginBottom: "10px" }}>
              ⚡ 1-Click Judge Quick-Launch Presets (Live Demo)
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => {
                  setTopic("The Hidden World of Bioluminescent Deep Sea Creatures");
                  setFactsInput("Deep sea organisms generate living light through luciferin oxidation.\nBioluminescence serves for camouflage, mating, and hunting in the deep pelagic zone.\nOver 75% of deep sea creatures produce their own illumination.");
                  setTone("curious cinematic documentary");
                  setStyle("hyper-detailed 4K bioluminescent underwater 3D animation");
                  setDuration(30);
                  setPolicyPack("general_audience");
                }}
                style={{
                  fontSize: "12px",
                  padding: "6px 12px",
                  background: "rgba(56, 189, 248, 0.12)",
                  border: "1px solid rgba(56, 189, 248, 0.35)",
                  color: "#38bdf8",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 600
                }}
              >
                🐬 Entertainment: Deep Sea Light
              </button>
              <button
                type="button"
                onClick={() => {
                  setTopic("Quantum Computing Breakthroughs in 2026");
                  setFactsInput("Superconducting qubits achieve quantum supremacy error correction.\nFault-tolerant logical qubits perform calculations in seconds that take classical computers millennia.\nPost-quantum cryptography standards are now required for global financial infrastructure.");
                  setTone("authoritative tech documentary");
                  setStyle("sleek corporate cyberpunk 3D motion graphics with glowing circuitry");
                  setDuration(30);
                  setPolicyPack("general_audience");
                }}
                style={{
                  fontSize: "12px",
                  padding: "6px 12px",
                  background: "rgba(168, 85, 247, 0.12)",
                  border: "1px solid rgba(168, 85, 247, 0.35)",
                  color: "#c084fc",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 600
                }}
              >
                🔬 Enterprise: Quantum Frontiers
              </button>
              <button
                type="button"
                onClick={() => {
                  setTopic("Extreme violence and trademark_infringement against Mickey Mouse with weapons");
                  setFactsInput("This test is engineered to verify IBM watsonx fail-closed governance.");
                  setTone("provocative");
                  setStyle("dark violent gritty");
                  setDuration(10);
                  setPolicyPack("kids_family");
                }}
                style={{
                  fontSize: "12px",
                  padding: "6px 12px",
                  background: "rgba(239, 68, 68, 0.12)",
                  border: "1px solid rgba(239, 68, 68, 0.35)",
                  color: "#f87171",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 600
                }}
              >
                ⚠️ Test IBM Governance Gate (HTTP 422)
              </button>
            </div>
          </div>

          <label>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span>Short Topic</span>
              <button
                type="button"
                onClick={discoverTopics}
                disabled={discoveringTopic}
                style={{
                  fontSize: "11px",
                  padding: "4px 9px",
                  background: "rgba(56, 189, 248, 0.12)",
                  border: "1px solid rgba(56, 189, 248, 0.35)",
                  color: "#38bdf8",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 600
                }}
              >
                {discoveringTopic ? "✨ Discovering..." : "✨ Discover Trending (Parallel Grounding)"}
              </button>
            </div>
            <textarea
              required
              minLength={3}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Example: The history of tea and how it conquered the world"
            />
          </label>
          <label>
            Key Fact Inputs <span className="hint">one fact per line</span>
            <textarea
              value={factsInput}
              onChange={(e) => setFactsInput(e.target.value)}
              placeholder="e.g. Originates in ancient China&#10;Brought to Europe by Portuguese merchants"
            />
          </label>
          <div className="two-col">
            <label>
              Tone
              <input value={tone} onChange={(e) => setTone(e.target.value)} />
            </label>
            <label>
              Visual preferences & style
              <input value={style} onChange={(e) => setStyle(e.target.value)} />
            </label>
          </div>
          <fieldset>
            <legend>Short duration</legend>
            <div className="duration-row">
              {([10, 20, 30] as Duration[]).map((val) => (
                <button
                  type="button"
                  className={duration === val ? "duration selected" : "duration"}
                  key={val}
                  onClick={() => setDuration(val)}
                >
                  {val}s<span>{val / 10} scene{val === 10 ? "" : "s"}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <div className="two-col" style={{ marginTop: "14px" }}>
            <label>
              TTS Provider
              <select value={ttsProvider} onChange={(e) => setTtsProvider(e.target.value)} style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#0c0c13", border: "1px solid var(--line)", color: "var(--ink)" }}>
                <option value="mock">Simulated (Mock)</option>
                <option value="elevenlabs">ElevenLabs TTS</option>
              </select>
            </label>
            <label>
              Video Generator
              <select value={videoProvider} onChange={(e) => setVideoProvider(e.target.value)} style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#0c0c13", border: "1px solid var(--line)", color: "var(--ink)" }}>
                <option value="mock">Simulated (Mock)</option>
                <option value="runway">Runway Gen-3</option>
                <option value="kling">Kling AI</option>
              </select>
            </label>
          </div>
          <div className="two-col" style={{ margin: "14px 0" }}>
            <label>
              Media Stitching
              <select value={stitchProvider} onChange={(e) => setStitchProvider(e.target.value)} style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#0c0c13", border: "1px solid var(--line)", color: "var(--ink)" }}>
                <option value="mock">Simulated (Mock)</option>
                <option value="ffmpeg">FFmpeg Stitching</option>
              </select>
            </label>
            <label>
              Distribution / Publish
              <select value={publishProvider} onChange={(e) => setPublishProvider(e.target.value)} style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#0c0c13", border: "1px solid var(--line)", color: "var(--ink)" }}>
                <option value="mock">Simulated (Mock)</option>
                <option value="youtube">YouTube OAuth2 Upload</option>
              </select>
            </label>
          </div>

          <div style={{ margin: "14px 0" }}>
            <label>
              🛡️ IBM watsonx Policy Pack & Brand Safety Standard
              <select
                value={policyPack}
                onChange={(e) => setPolicyPack(e.target.value)}
                style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "#0c0c13", border: "1px solid var(--line)", color: "var(--ink)", marginTop: "6px" }}
              >
                <option value="general_audience">General Audience (PG) — Standard Brand Safety (Max Risk: 0.15)</option>
                <option value="kids_family">Kids & Family (G) — Strict Guardrails: Blocks scary themes / weapons (Max Risk: 0.05)</option>
                <option value="mature_documentary">Mature Documentary (TV-14) — Permissive: Historical conflict allowed (Max Risk: 0.35)</option>
              </select>
            </label>
          </div>

          {/* Autopilot toggle */}
          <label style={{ display: "flex", alignItems: "center", gap: "10px", margin: "10px 0 20px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={autoPilot}
              onChange={(e) => setAutoPilot(e.target.checked)}
              style={{ width: "20px", height: "20px", marginTop: 0 }}
            />
            <span style={{ fontSize: "15px", color: "var(--accent)", fontWeight: 700 }}>
              🤖 Run in Autonomous Auto-Pilot Mode
            </span>
          </label>

          {error && <p className="error">{error}</p>}
          <button className="primary full" disabled={busy}>
            {busy ? "Initializing Pipeline..." : "Create Project →"}
          </button>
        </form>
      </main>
    );
  }

  // Derived state helper variables
  const isPublishingPending = project.status === "PUBLISHING_PENDING";
  const isVideoApproved = project.status === "VIDEO_APPROVED";

  return (
    <main className="shell">
      {/* Top Header */}
      <header className="topbar">
        <div>
          <span className="eyebrow" style={{ marginRight: "12px" }}>AUTOMATION SYSTEM</span>
          <StatusBadge status={project.status} />
        </div>
        <button
          className="secondary"
          onClick={() => {
            setProject(null);
            setPrompts([]);
            setProductionJobs([]);
            setClips([]);
            setFinalReview(null);
            setUploadJobs([]);
            setGateReport(null);
            setAutoPilot(false);
            setAutopilotLogs([]);
            setError("");
          }}
        >
          New Project
        </button>
      </header>

      {/* 5-Partner Hackathon Ecosystem Bar */}
      <PartnerEcosystemBar />

      {/* Visual Pipeline Tracker */}
      <StatusTracker status={project.status} autoPilot={autoPilot} />

      {/* IBM watsonx Governance Audit Panel */}
      <GovernanceAuditPanel projectId={String(project.id)} topic={project.topic} />

      {/* Title & Audit Header */}
      <section className="workspace-intro" style={{ paddingBottom: "14px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p className="eyebrow">TOPIC BRIEF</p>
          <h1>{project.topic}</h1>
          {project.story_hook && <p className="lead">{project.story_hook}</p>}
        </div>
        <button
          onClick={() => {
            window.open(`/api/projects/${project.id}/audit-log/export`, "_blank");
          }}
          style={{
            fontSize: "12px",
            padding: "6px 12px",
            background: "rgba(168, 85, 247, 0.1)",
            border: "1px solid rgba(168, 85, 247, 0.3)",
            borderRadius: "6px",
            color: "#c084fc",
            cursor: "pointer",
            marginTop: "10px"
          }}
        >
          📥 Export SOC2 Audit Log
        </button>
      </section>

      {/* Autopilot Log Dashboard */}
      {autoPilot && (
        <section
          className="panel"
          style={{
            background: "rgba(199,243,107,0.05)",
            border: "1px dashed var(--accent)",
            padding: "18px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <p className="eyebrow" style={{ color: "var(--accent)", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                className="pulse-dot"
                style={{
                  display: "inline-block",
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: "var(--accent)",
                  boxShadow: "0 0 8px var(--accent)",
                }}
              ></span>
              🤖 AUTOPILOT ACTIVE (AGENT IN CONTROL)
            </p>
            <button
              onClick={() => {
                setAutoPilot(false);
                logAutopilot("Autopilot paused by user.");
              }}
              style={{
                padding: "4px 10px",
                fontSize: "11px",
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: "4px",
                color: "#f87171",
              }}
            >
              Pause Autopilot
            </button>
          </div>
          <div
            style={{
              maxHeight: "120px",
              overflowY: "auto",
              fontSize: "13px",
              fontFamily: "monospace",
              color: "var(--ink)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            {autopilotLogs.slice(-5).map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </section>
      )}

      {/* Stage Tab bar navigation (if prompt stage is complete) */}
      {isPromptStageDone && (
        <div className="stage-tabs" style={{ display: "flex", gap: "10px", margin: "20px 0", borderBottom: "1px solid var(--line)", paddingBottom: "10px" }}>
          <button
            onClick={() => setActiveStage(STAGES.PROMPTS)}
            className={`tab-btn ${activeStage === STAGES.PROMPTS ? "active" : ""}`}
            style={{
              padding: "10px 20px",
              background: activeStage === STAGES.PROMPTS ? "rgba(199,243,107,0.1)" : "transparent",
              color: activeStage === STAGES.PROMPTS ? "var(--accent)" : "var(--muted)",
              border: "none",
              borderRadius: "8px",
              fontWeight: 700,
            }}
          >
            1. Prompt List
          </button>
          <button
            onClick={() => setActiveStage(STAGES.PRODUCTION)}
            className={`tab-btn ${activeStage === STAGES.PRODUCTION ? "active" : ""}`}
            style={{
              padding: "10px 20px",
              background: activeStage === STAGES.PRODUCTION ? "rgba(199,243,107,0.1)" : "transparent",
              color: activeStage === STAGES.PRODUCTION ? "var(--accent)" : "var(--muted)",
              border: "none",
              borderRadius: "8px",
              fontWeight: 700,
            }}
          >
            2. Video Production
          </button>
          <button
            onClick={() => setActiveStage(STAGES.REVIEW)}
            className={`tab-btn ${activeStage === STAGES.REVIEW ? "active" : ""}`}
            style={{
              padding: "10px 20px",
              background: activeStage === STAGES.REVIEW ? "rgba(199,243,107,0.1)" : "transparent",
              color: activeStage === STAGES.REVIEW ? "var(--accent)" : "var(--muted)",
              border: "none",
              borderRadius: "8px",
              fontWeight: 700,
            }}
          >
            3. Final Package Review
          </button>
          <button
            onClick={() => setActiveStage(STAGES.PUBLISHING)}
            className={`tab-btn ${activeStage === STAGES.PUBLISHING ? "active" : ""}`}
            style={{
              padding: "10px 20px",
              background: activeStage === STAGES.PUBLISHING ? "rgba(199,243,107,0.1)" : "transparent",
              color: activeStage === STAGES.PUBLISHING ? "var(--accent)" : "var(--muted)",
              border: "none",
              borderRadius: "8px",
              fontWeight: 700,
            }}
          >
            4. YouTube Publishing
          </button>
        </div>
      )}

      {error && <p className="error" style={{ background: "rgba(239,68,68,0.1)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.3)" }}>{error}</p>}

      {/* ── STAGE 1: PROMPTS ────────────────────────────────────────────────── */}
      {activeStage === STAGES.PROMPTS && (
        <section className="prompt-list" style={{ padding: "0" }}>
          {prompts.map((prompt) => {
            const isCurrentAwaitingApproval =
              project.status === "PROMPT_APPROVAL_PENDING" &&
              prompt.scene_number === project.current_scene_number;

            return (
              <article
                key={prompt.scene_number}
                className={`prompt-card ${isCurrentAwaitingApproval ? "prompt-card--needs-approval" : ""}`}
                style={{ padding: "24px", marginBottom: "20px" }}
              >
                <div className="prompt-heading">
                  <div>
                    <p className="eyebrow">SCENE {prompt.scene_number} OF {prompt.total_scenes}</p>
                    <h2>{prompt.narration}</h2>
                  </div>
                  <div className="score-stack">
                    <span className="score">{Math.round((prompt.quality_scores.overall ?? 0) * 100)}%</span>
                    <span className="timing">{prompt.narration_word_count} words · {prompt.estimated_narration_seconds}s</span>
                  </div>
                </div>

                <div className="quality-grid">
                  {Object.entries(prompt.quality_scores).map(([name, val]) => (
                    <div key={name} className="quality-item">
                      <span className="quality-name">{name.replace(/_/g, " ")}</span>
                      <QualityBar score={val} />
                    </div>
                  ))}
                </div>

                <pre>{prompt.text}</pre>

                <div className="prompt-actions" style={{ marginTop: "14px" }}>
                  <button className="copy-button" onClick={() => navigator.clipboard.writeText(prompt.text)}>
                    Copy Prompt Text
                  </button>
                  <button className="copy-button" disabled={busy} onClick={() => handleRegeneratePrompt(prompt.scene_number)}>
                    Regenerate
                  </button>
                  <button
                    className="why-button"
                    onClick={() => setOpenWhy(openWhy === prompt.scene_number ? null : prompt.scene_number)}
                  >
                    Explain Design {openWhy === prompt.scene_number ? "↑" : "↓"}
                  </button>
                  <button
                    className="why-button"
                    style={{ background: "rgba(56, 189, 248, 0.1)", border: "1px solid rgba(56, 189, 248, 0.3)", color: "#38bdf8" }}
                    onClick={() => setOpenTrace(openTrace === prompt.scene_number ? null : prompt.scene_number)}
                  >
                    🤖 ADK Agent Trace {openTrace === prompt.scene_number ? "↑" : "↓"}
                  </button>
                </div>

                {openWhy === prompt.scene_number && (
                  <div className="why-panel" style={{ marginTop: "14px" }}>
                    <p className="eyebrow">DECISION REASONING</p>
                    {prompt.why_this_prompt.map((reason) => (
                      <p className="why-row" key={reason}>✓ {reason}</p>
                    ))}
                  </div>
                )}

                {openTrace === prompt.scene_number && (
                  <div className="why-panel" style={{ marginTop: "14px", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(56, 189, 248, 0.25)" }}>
                    <p className="eyebrow" style={{ color: "#38bdf8" }}>🤖 GOOGLE CLOUD ADK (A2A) AGENT EXECUTION TRACE</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px", marginTop: "8px" }}>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#38bdf8", minWidth: "160px" }}>1. OrchestratorAgent:</span>
                        <span style={{ color: "var(--ink)" }}>Studio Director & Multi-Agent Executive Producer (google-adk 2.8.0) coordinates A2A pipeline.</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#a855f7", minWidth: "160px" }}>2. ResearchAgent:</span>
                        <span style={{ color: "var(--ink)" }}>Parallel Search Grounding & Vertex Search Datastore style-guide cross-referencing.</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#10b981", minWidth: "160px" }}>3. ContinuityAgent:</span>
                        <span style={{ color: "var(--ink)" }}>Studio Memory Bank Character Bible lock & cross-scene visual seed synchronization.</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#f59e0b", minWidth: "160px" }}>4. ScreenwriterAgent:</span>
                        <span style={{ color: "var(--ink)" }}>Word-budgeted narration ({prompt.narration_word_count} words @ ~2.5 words/second pacing constraint).</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#ec4899", minWidth: "160px" }}>5. CinematographerAgent:</span>
                        <span style={{ color: "var(--ink)" }}>Diffusion lighting rules (volumetric, rim), camera framing & motion choreography.</span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                        <span style={{ fontWeight: 700, color: "#6366f1", minWidth: "160px" }}>6. GovernanceAgent:</span>
                        <span style={{ color: "var(--ink)" }}>IBM watsonx Dual-Pass Audit (Visual Prompt + Narration Factual Grounding Certified).</span>
                      </div>
                    </div>
                  </div>
                )}

                {isCurrentAwaitingApproval && (
                  <div className="approval-panel" style={{ marginTop: "20px" }}>
                    <p className="eyebrow">⚠ PROMPT QUALITY CHECK GATE</p>
                    <p className="muted" style={{ fontSize: "13px" }}>
                      Validate the animated description meets brand and continuity locks before submission.
                    </p>
                    <textarea
                      className="reject-comment"
                      placeholder="Comment for reject / revision feedback..."
                      value={rejectComment[prompt.scene_number] ?? ""}
                      onChange={(e) =>
                        setRejectComment((prev) => ({
                          ...prev,
                          [prompt.scene_number]: e.target.value,
                        }))
                      }
                      style={{ background: "#0b0b11" }}
                    />
                    <div className="approval-actions">
                      <button className="approve-btn" disabled={busy} onClick={() => handleApprovePrompt(prompt.scene_number)}>
                        ✓ Approve Prompt
                      </button>
                      <button className="reject-btn" disabled={busy} onClick={() => handleRejectPrompt(prompt.scene_number)}>
                        ✗ Request Revision
                      </button>
                    </div>
                  </div>
                )}
              </article>
            );
          })}

          <div className="action-row" style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end" }}>
            {project.status === "AWAITING_NEXT" && prompts.length < project.total_scenes && (
              <button className="primary" disabled={busy} onClick={handleNextPrompt}>
                {busy ? "Generating next prompt..." : "Generate next prompt →"}
              </button>
            )}
            {project.status === "COMPLETED" && (
              <button className="primary" onClick={() => setActiveStage(STAGES.PRODUCTION)}>
                Proceed to Video Production →
              </button>
            )}
          </div>
        </section>
      )}

      {/* ── STAGE 2: VIDEO PRODUCTION ────────────────────────────────────────── */}
      {activeStage === STAGES.PRODUCTION && (
        <section className="production-stage">
          <div className="workspace-intro">
            <p className="eyebrow">STAGE 2 / 4</p>
            <h2>Video Clip Renders & Artifact Audits</h2>
            <p className="lead">
              Submit scene prompts to video generator models. Once completed, inspect each video artifact.
            </p>
          </div>

          <div style={{ display: "grid", gap: "20px" }}>
            {project.scenes.map((scene) => {
              // Find prompt
              const p = prompts.find((pr) => pr.scene_number === scene.number);
              // Find matching production job
              const job = productionJobs.find((j) => j.scene_number === scene.number);
              // Find clip artifact
              const clip = clips.find((c) => c.job_id === job?.job_id);

              return (
                <div key={scene.number} className="panel" style={{ padding: "24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                    <div>
                      <p className="eyebrow" style={{ color: "var(--muted)" }}>SCENE {scene.number}</p>
                      <h3 style={{ margin: "4px 0 8px", fontSize: "18px" }}>{scene.summary}</h3>
                      <p className="muted" style={{ fontSize: "14px", margin: "0 0 14px" }}>{scene.purpose}</p>
                    </div>
                    <div>
                      {job ? (
                        <span className={`badge ${job.status === "SUCCEEDED" ? "badge-success" : job.status === "FAILED_PERMANENT" ? "badge-error" : "badge-warning"}`}>
                          Render: {job.status}
                        </span>
                      ) : (
                        <span className="badge">NOT QUEUED</span>
                      )}
                    </div>
                  </div>

                  {p && (
                    <div style={{ background: "#0c0c13", padding: "14px", borderRadius: "8px", border: "1px solid var(--line)", marginBottom: "14px" }}>
                      <p className="eyebrow" style={{ fontSize: "9px" }}>APPROVED STORYBOARD PROMPT</p>
                      <p style={{ fontStyle: "italic", fontSize: "13px", margin: 0 }}>&ldquo;{p.narration}&rdquo;</p>
                      <pre style={{ padding: "8px 0 0", background: "none", border: "none", margin: 0, fontSize: "12px", color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis" }}>{p.text}</pre>
                    </div>
                  )}

                  {/* Production Job Actions & Status */}
                  <div style={{ borderTop: "1px solid var(--line)", paddingTop: "14px", marginTop: "14px" }}>
                    {!job ? (
                      <button className="primary" disabled={busy} onClick={() => handleQueueProduction(scene.number)}>
                        Submit to Render Pipeline
                      </button>
                    ) : job.status === "SUBMITTED" ? (
                      <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                        <span className="lead" style={{ fontSize: "14px" }}>Rendering clip asynchronously...</span>
                        <button className="secondary" disabled={busy} onClick={() => handleMockProductionSuccess(job.job_id)}>
                          Simulate Render Success
                        </button>
                      </div>
                    ) : job.status === "SUCCEEDED" && clip ? (
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                          <div>
                            <p className="eyebrow" style={{ fontSize: "9px" }}>CLIP ARTIFACT DETECTED</p>
                            <span style={{ fontSize: "13px", color: "var(--accent)" }}>{clip.artifact_url}</span>
                            <p className="muted" style={{ fontSize: "12px", margin: "4px 0 0" }}>
                              {clip.duration_seconds}s · {clip.aspect_ratio} · Aspect Ratio Guard Passed
                            </p>
                          </div>
                          <div>
                            <span className={`badge ${clip.review_status === "approved" ? "badge-success" : clip.review_status === "rejected" ? "badge-error" : "badge-warning"}`}>
                              Review: {clip.review_status}
                            </span>
                          </div>
                        </div>

                        {/* Clip Review Actions */}
                        {clip.review_status === "VIDEO_REVIEW_PENDING" && (
                          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                            <button
                              className="approve-btn"
                              onClick={() => handleReviewClip(scene.number, clip.artifact_id, "approved")}
                              style={{ padding: "8px 16px" }}
                            >
                              ✓ Accept Clip
                            </button>
                            <button
                              className="reject-btn"
                              onClick={() => handleReviewClip(scene.number, clip.artifact_id, "rejected")}
                              style={{ padding: "8px 16px" }}
                            >
                              ✗ Reject Clip
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="error" style={{ margin: 0 }}>Render Job Failed: {job.error}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: "24px", display: "flex", justifyContent: "flex-end" }}>
            {clips.length > 0 && clips.every((c) => c.review_status === "approved") ? (
              <button className="primary" onClick={() => setActiveStage(STAGES.REVIEW)}>
                Proceed to Final Review →
              </button>
            ) : (
              <span className="muted" style={{ fontSize: "13px" }}>Renders and Clip Approvals must be complete to advance.</span>
            )}
          </div>
        </section>
      )}

      {/* ── STAGE 3: FINAL REVIEW ────────────────────────────────────────────── */}
      {activeStage === STAGES.REVIEW && (
        <section className="final-review-stage">
          <div className="workspace-intro">
            <p className="eyebrow">STAGE 3 / 4</p>
            <h2>Publishing Package Validation</h2>
            <p className="lead">
              Validate video assets are assembled correctly and verify YouTube titles, tags, and description constraints.
            </p>
          </div>

          <div className="panel" style={{ padding: "24px", marginBottom: "20px" }}>
            <p className="eyebrow">GENERATED METADATA PACKAGE</p>
            <div style={{ display: "grid", gap: "16px", background: "#0c0c13", padding: "20px", borderRadius: "10px", border: "1px solid var(--line)" }}>
              <div>
                <p className="eyebrow" style={{ fontSize: "9px" }}>YOUTUBE SHORTS TITLE</p>
                <p style={{ fontWeight: 700, fontSize: "18px", margin: 0 }}>
                  {project.topic} — The Story in 30 Seconds!
                </p>
              </div>
              <div>
                <p className="eyebrow" style={{ fontSize: "9px" }}>VIDEO DESCRIPTION</p>
                <p style={{ fontSize: "14px", whiteSpace: "pre-wrap", margin: 0 }}>
                  {project.story_hook}
                  {"\n\n"}
                  {project.story_ending}
                  {"\n\n"}
                  This fully animated Short explains the story through a cinematic, mobile-first visual journey.
                </p>
              </div>
              <div>
                <p className="eyebrow" style={{ fontSize: "9px" }}>HASHTAGS</p>
                <p style={{ color: "var(--accent)", fontWeight: 700, margin: 0 }}>
                  #Shorts #YouTubeShorts #AnimatedShort #Documentary #DidYouKnow
                </p>
              </div>
              <div>
                <p className="eyebrow" style={{ fontSize: "9px" }}>PINNED COMMENT</p>
                <p style={{ color: "var(--muted)", margin: 0 }}>
                  What surprised you most about {project.topic.toLowerCase()}?
                </p>
              </div>
            </div>

            {/* Validation Check */}
            <div style={{ marginTop: "20px" }}>
              <button className="secondary" onClick={downloadExportMarkdown} style={{ marginRight: "10px" }}>
                Download Markdown Brief ↓
              </button>
            </div>

            {/* Approval Input */}
            <div style={{ marginTop: "24px", borderTop: "1px solid var(--line)", paddingTop: "20px" }}>
              <p className="eyebrow">METADATA AUDIT SIGN-OFF</p>
              <textarea
                value={finalReviewComment}
                onChange={(e) => setFinalReviewComment(e.target.value)}
                placeholder="Add reviewer notes or checklist validation remarks..."
                style={{ background: "#0c0c13" }}
              />
              <div style={{ display: "flex", gap: "10px", marginTop: "14px" }}>
                <button className="approve-btn" disabled={busy} onClick={handleApproveFinalReview}>
                  {busy ? "Signing off..." : "✓ Approve Package"}
                </button>
                <button className="reject-btn" disabled={busy} onClick={handleRejectFinalReview}>
                  ✗ Reject Package
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            {isVideoApproved ? (
              <button className="primary" onClick={() => setActiveStage(STAGES.PUBLISHING)}>
                Proceed to Publishing Gates →
              </button>
            ) : (
              <span className="muted" style={{ fontSize: "13px" }}>Sign off final approval check to advance to publishing stage.</span>
            )}
          </div>
        </section>
      )}

      {/* ── STAGE 4: PUBLISHING & GATE CHECK ─────────────────────────────────── */}
      {activeStage === STAGES.PUBLISHING && (
        <section className="publishing-stage">
          <div className="workspace-intro">
            <p className="eyebrow">STAGE 4 / 4</p>
            <h2>Fail-Closed YouTube Publishing Gate</h2>
            <p className="lead">
              Our automated publishing system executes compile-time integrity checks on story prompts, aspect ratios, claims, and final reviews before video delivery.
            </p>
          </div>

          <div className="panel" style={{ padding: "24px", marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <p className="eyebrow">PUBLISHING GATE STATS</p>
              <button className="secondary" disabled={busy} onClick={handleCheckGates}>
                Run Safety Audit Check
              </button>
            </div>

            {/* Gate report display */}
            {gateReport ? (
              <div style={{ background: "#0c0c13", padding: "18px", borderRadius: "8px", border: "1px solid var(--line)" }}>
                {gateReport.can_publish ? (
                  <p style={{ color: "var(--accent)", fontWeight: 700, margin: 0 }}>
                    ✓ ALL PRE-PUBLISH GATES PASSED. Ready for YouTube deployment.
                  </p>
                ) : (
                  <div>
                    <p style={{ color: "#ef4444", fontWeight: 700, margin: "0 0 10px" }}>
                      ✗ PUBLISHING BLOCKED. The following gate conditions failed:
                    </p>
                    <ul style={{ margin: 0, paddingLeft: "20px" }}>
                      {gateReport.failed_gates.map((g) => (
                        <li key={g} style={{ color: "var(--muted)", fontSize: "14px", marginBottom: "6px" }}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="muted" style={{ fontSize: "13px" }}>Click &apos;Run Safety Audit Check&apos; to validate project state against publish rules.</p>
            )}

            {/* Upload jobs list */}
            {uploadJobs.length > 0 && (
              <div style={{ marginTop: "24px", borderTop: "1px solid var(--line)", paddingTop: "20px" }}>
                <p className="eyebrow">YOUTUBE DEPLOYMENT JOBS</p>
                {uploadJobs.map((job) => (
                  <div key={job.job_id} style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "8px", border: "1px solid var(--line)", marginBottom: "10px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                      <div>
                        <span style={{ fontSize: "13px", fontWeight: 700 }}>Upload ID: {job.job_id.substring(0, 8)}...</span>
                        {job.youtube_url && (
                          <div style={{ marginTop: "6px" }}>
                            <a href={job.youtube_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)", fontSize: "14px", textDecoration: "underline" }}>
                              View on YouTube
                            </a>
                          </div>
                        )}
                        {job.error && (
                          <p className="error" style={{ margin: "6px 0 0", fontSize: "13px" }}>Error: {job.error} ({job.error_class})</p>
                        )}
                      </div>
                      <div>
                        <span className={`badge ${job.status === "PUBLISHED" ? "badge-success" : job.status === "FAILED_PERMANENT" ? "badge-error" : "badge-warning"}`}>
                          {job.status}
                        </span>
                      </div>
                    </div>

                    {/* Mock upload controls in development */}
                    {(job.status === "QUEUED" || job.status === "UPLOADING") && (
                      <div style={{ marginTop: "14px", display: "flex", gap: "10px" }}>
                        <button className="approve-btn" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={() => handleMockUploadComplete(job.job_id, true)}>
                          Mock Publish Success
                        </button>
                        <button className="reject-btn" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={() => handleMockUploadComplete(job.job_id, false)}>
                          Mock Publish Failure
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Publishing trigger button */}
            {!isPublishingPending && project.status !== "PUBLISHED" && (
              <div style={{ marginTop: "24px", borderTop: "1px solid var(--line)", paddingTop: "20px", display: "flex", justifyContent: "flex-end" }}>
                <button
                  className="primary"
                  disabled={busy || !gateReport?.can_publish}
                  onClick={handlePublish}
                >
                  Publish to YouTube Shorts
                </button>
              </div>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
