"use client";

import { FormEvent, ReactNode, useState } from "react";
import { createProject, Duration, exportProject, generatePrompt, regeneratePrompt, Project, Prompt } from "../lib/api";

export default function HomePage() {
  const [topic, setTopic] = useState("");
  const [facts, setFacts] = useState("");
  const [duration, setDuration] = useState<Duration>(30);
  const [tone, setTone] = useState("curious cinematic documentary");
  const [style, setStyle] = useState("stylized cinematic 3D animation");
  const [project, setProject] = useState<Project | null>(null);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function startProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await createProject({
        topic,
        facts: facts.split("\n").map((fact) => fact.trim()).filter(Boolean),
        language: "English",
        tone,
        audience: "general audience",
        visual_preferences: { style },
        duration_seconds: duration,
      });
      const firstPrompt = await generatePrompt(created.id);
      setProject({
        ...created,
        current_scene_number: firstPrompt.scene_number,
        status: firstPrompt.scene_number === created.total_scenes ? "COMPLETED" : "AWAITING_NEXT",
      });
      setPrompts([firstPrompt]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function nextPrompt() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const prompt = await generatePrompt(project.id);
      setPrompts((current) => [...current.filter((item) => item.scene_number !== prompt.scene_number), prompt].sort((a, b) => a.scene_number - b.scene_number));
      setProject((current) => current ? { ...current, current_scene_number: prompt.scene_number, status: prompt.scene_number === current.total_scenes ? "COMPLETED" : "AWAITING_NEXT" } : current);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function regenerate(sceneNumber: number) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const prompt = await regeneratePrompt(project.id, sceneNumber);
      setPrompts((current) => current.map((item) => item.scene_number === sceneNumber ? prompt : item));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadExport() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const bundle = await exportProject(project.id);
      const blob = new Blob([bundle.markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "animated-shorts-prompt-package.md";
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (project) {
    const complete = prompts.length === project.total_scenes;
    return (
      <main className="shell">
        <header className="topbar"><span className="eyebrow">SHORTS PROMPT AGENT</span><span className="status">{project.status}</span></header>
        <section className="workspace-intro">
          <p className="eyebrow">PROJECT · {project.current_scene_number}/{project.total_scenes}</p>
          <h1>{project.topic}</h1>
          <p className="muted">{project.story_hook}</p>
        </section>
        <section className="lock-grid">
          <div className="panel"><p className="eyebrow">CONTINUITY LOCK</p><h2>{project.continuity.animation_style}</h2><p className="muted">{project.continuity.palette}</p><p className="muted">9:16 vertical · {project.continuity.camera_language}</p></div>
          <div className="panel"><p className="eyebrow">VOICE LOCK</p><h2>{project.continuity.voice_id}</h2><p className="muted">{project.continuity.voice_description}</p><p className="muted">Same voice across every scene</p></div>
        </section>
        {project.facts.length > 0 && <section className="panel fact-panel"><p className="eyebrow">FACT STATUS</p>{project.facts.map((fact) => <div className="fact-row" key={fact.id}><span>{fact.text}</span><span className={fact.approved_for_narration ? "fact-approved" : "fact-pending"}>{fact.status.replace("_", " ")}</span></div>)}</section>}
        <section className="prompt-list">
          {prompts.map((prompt) => <article className="prompt-card" key={prompt.scene_number}><div className="prompt-heading"><div><p className="eyebrow">SCENE {prompt.scene_number}/{prompt.total_scenes} · VERSION {prompt.version_number}</p><h2>{prompt.narration}</h2></div><span className="timing">{prompt.narration_word_count} words · {prompt.estimated_narration_seconds}s</span></div><pre>{prompt.text}</pre><div className="prompt-actions"><button className="copy-button" onClick={() => navigator.clipboard.writeText(prompt.text)}>Copy prompt</button><button className="copy-button" disabled={busy} onClick={() => regenerate(prompt.scene_number)}>Regenerate scene</button></div></article>)}
        </section>
        {error && <p className="error">{error}</p>}
        <div className="action-row">{complete ? <><p className="complete">Project complete · {prompts.length} prompts ready</p><button className="primary" disabled={busy} onClick={downloadExport}>{busy ? "Preparing…" : "Export package ↓"}</button></> : <button className="primary" disabled={busy} onClick={nextPrompt}>{busy ? "Generating…" : "Generate next prompt →"}</button>}<button className="secondary" onClick={() => { setProject(null); setPrompts([]); }}>New Short</button></div>
      </main>
    );
  }

  return (
    <main className="shell form-shell">
      <header className="topbar"><span className="eyebrow">SHORTS PROMPT AGENT</span><span className="status">MVP · ANIMATED ONLY</span></header>
      <section className="hero"><p className="eyebrow">STATEFUL CREATIVE PRODUCTION</p><h1>Turn one idea into a consistent animated Short.</h1><p className="lead">Build a story once, lock the style and voice, then generate validated ten-second scenes one at a time.</p></section>
      <form className="form-card" onSubmit={startProject}>
        <label>What is the Short about?<textarea required minLength={3} value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Example: How a small local idea became a worldwide chain" /></label>
        <label>Facts or requirements <span className="hint">optional · one per line</span><textarea value={facts} onChange={(event) => setFacts(event.target.value)} placeholder="Add facts, events, or specific details you want included" /></label>
        <div className="two-col"><label>Tone<input value={tone} onChange={(event) => setTone(event.target.value)} /></label><label>Animation style<input value={style} onChange={(event) => setStyle(event.target.value)} /></label></div>
        <fieldset><legend>Short length</legend><div className="duration-row">{([10, 20, 30] as Duration[]).map((value) => <button type="button" className={duration === value ? "duration selected" : "duration"} key={value} onClick={() => setDuration(value)}>{value}s<span>{value / 10} prompt{value === 10 ? "" : "s"}</span></button>)}</div></fieldset>
        {error && <p className="error">{error}</p>}<button className="primary full" disabled={busy}>{busy ? "Building project…" : "Create Prompt 1 →"}</button>
      </form>
    </main>
  );
}
