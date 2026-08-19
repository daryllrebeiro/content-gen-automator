"""Tests for PublishingGateService — all gate combinations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.facts import FactClaim, FactStatus
from app.domain.integration import (
    ApprovalEvent,
    ClipArtifact,
    ExportManifest,
    FinalReviewEvent,
    ProductionJob,
    YouTubeUploadJob,
)
from app.domain.project import (
    ContinuityProfile,
    Project,
    ProjectInput,
    ProjectStatus,
    Scene,
    VideoPrompt,
)
from app.services.project_service import InMemoryProjectRepository
from app.services.publishing_gate_service import GateReport, PublishingGateService


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_project(n_scenes: int = 1) -> Project:
    inp = ProjectInput(topic="Test topic", duration_seconds=10 * n_scenes)  # type: ignore[arg-type]
    project = Project(input=inp, status=ProjectStatus.COMPLETED)
    project.scenes = [Scene(number=i, purpose="test", summary="s") for i in range(1, n_scenes + 1)]
    project.facts = []
    return project


def _add_prompt(project: Project, scene_number: int, version: int = 1) -> VideoPrompt:
    prompt = VideoPrompt(
        project_id=project.id,
        scene_number=scene_number,
        total_scenes=len(project.scenes),
        text="test",
        narration="test narration",
        narration_word_count=2,
        estimated_narration_seconds=1.0,
        version_number=version,
    )
    project.prompts[scene_number] = prompt
    return prompt


def _add_approval(repo: InMemoryProjectRepository, project: Project, scene_number: int) -> None:
    event = ApprovalEvent(
        event_id=str(uuid4())[:24],
        project_id=str(project.id),
        scene_number=scene_number,
        decision="approved",
        actor="tester",
        comment="",
        created_at=datetime.now(timezone.utc),
    )
    repo.save_approval_event(event)


def _add_succeeded_production(repo: InMemoryProjectRepository, project: Project, scene_number: int) -> str:
    artifact_id = str(uuid4())
    job = ProductionJob(
        job_id=str(uuid4()),
        project_id=str(project.id),
        scene_number=scene_number,
        prompt_version=project.prompts[scene_number].version_number,
        job_type="video_clip",
        provider="mock",
        provider_job_id="mock-job",
        status="SUCCEEDED",
        contract={},
        artifact_id=artifact_id,
    )
    repo.save_production_job(job)
    return artifact_id


def _add_clip_artifact(repo: InMemoryProjectRepository, artifact_id: str, job_id: str, review_status: str = "approved") -> None:
    artifact = ClipArtifact(
        artifact_id=artifact_id,
        job_id=job_id,
        checksum="abc",
        duration_seconds=10.0,
        aspect_ratio="9:16",
        narration_end_seconds=8.5,
        artifact_url="http://mock/clip.mp4",
        review_status=review_status,
    )
    repo.save_clip_artifact(artifact)


def _add_manifest(repo: InMemoryProjectRepository, project: Project) -> ExportManifest:
    manifest = ExportManifest(
        manifest_id=str(uuid4())[:24],
        project_id=str(project.id),
        package_version="v1",
        checksum="abc123",
        markdown="# test",
        data={},
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    repo.save_export_manifest(manifest)
    return manifest


def _add_final_review(repo: InMemoryProjectRepository, project: Project, manifest_id: str, decision: str = "approved") -> None:
    event = FinalReviewEvent(
        event_id=str(uuid4())[:24],
        project_id=str(project.id),
        manifest_id=manifest_id,
        decision=decision,
        actor="reviewer",
        comment="",
        created_at=datetime.now(timezone.utc),
    )
    repo.save_final_review_event(event)


def _build_fully_passing_repo(n_scenes: int = 1):
    """Build project + repo with all gates passing."""
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(n_scenes)

    for i in range(1, n_scenes + 1):
        _add_prompt(project, i)
        _add_approval(repo, project, i)
        art_id = _add_succeeded_production(repo, project, i)
        # get the job id from the repo
        job_id = next(j.job_id for j in repo.production_jobs.values() if j.project_id == str(project.id) and j.scene_number == i)
        _add_clip_artifact(repo, art_id, job_id, "approved")

    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)
    return gate, repo, project, manifest


# ── Gate tests ───────────────────────────────────────────────────────────────

def test_all_gates_pass():
    gate, repo, project, manifest = _build_fully_passing_repo()
    report = gate.check(project, repo)
    assert report.can_publish is True
    assert report.failed_gates == []


def test_gate1_fails_missing_prompt_approval():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    # NO approval event
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("approval" in g.lower() for g in report.failed_gates)


def test_gate2_fails_production_job_not_succeeded():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    # production job SUBMITTED not SUCCEEDED
    job = ProductionJob(str(uuid4()), str(project.id), 1, 1, "video_clip", "mock", "m", "SUBMITTED", {})
    repo.save_production_job(job)
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("SUBMITTED" in g for g in report.failed_gates)


def test_gate3_fails_clip_not_approved():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "VIDEO_REVIEW_PENDING")  # not approved
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("review_status" in g for g in report.failed_gates)


def test_gate4_fails_contradicted_fact():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    project.facts = [FactClaim(id="f1", text="bad claim", status=FactStatus.CONTRADICTED)]
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("contradict" in g.lower() for g in report.failed_gates)


def test_gate5_fails_no_manifest():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    # No manifest

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("manifest" in g.lower() for g in report.failed_gates)


def test_gate5_fails_expired_manifest():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    # Expired manifest
    manifest = ExportManifest(str(uuid4())[:24], str(project.id), "v1", "abc", "# x", {}, datetime.now(timezone.utc) - timedelta(hours=25), datetime.now(timezone.utc) - timedelta(hours=1))
    repo.save_export_manifest(manifest)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("expired" in g.lower() for g in report.failed_gates)


def test_gate6_fails_no_final_review():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    _add_manifest(repo, project)
    # No final review

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("final review" in g.lower() for g in report.failed_gates)


def test_gate6_fails_final_review_rejected():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(1)
    _add_prompt(project, 1)
    _add_approval(repo, project, 1)
    art_id = _add_succeeded_production(repo, project, 1)
    job_id = next(j.job_id for j in repo.production_jobs.values())
    _add_clip_artifact(repo, art_id, job_id, "approved")
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id, "rejected")

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("rejected" in g.lower() for g in report.failed_gates)


def test_gate7_fails_active_upload_in_progress():
    gate, repo, project, manifest = _build_fully_passing_repo()
    # Add an UPLOADING job
    active = YouTubeUploadJob(str(uuid4()), str(project.id), manifest.manifest_id, "UPLOADING", "chk")
    repo.save_youtube_upload_job(active)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("UPLOADING" in g for g in report.failed_gates)


def test_multi_scene_all_gates_pass():
    gate, repo, project, manifest = _build_fully_passing_repo(n_scenes=3)
    report = gate.check(project, repo)
    assert report.can_publish is True


def test_multi_scene_partial_approval_fails():
    gate = PublishingGateService()
    repo = InMemoryProjectRepository()
    project = _make_project(3)

    for i in range(1, 4):
        _add_prompt(project, i)
        art_id = _add_succeeded_production(repo, project, i)
        job_id = next(j.job_id for j in repo.production_jobs.values() if j.scene_number == i and j.project_id == str(project.id))
        _add_clip_artifact(repo, art_id, job_id, "approved")

    # Approve only scene 1
    _add_approval(repo, project, 1)
    repo.save(project)
    manifest = _add_manifest(repo, project)
    _add_final_review(repo, project, manifest.manifest_id)

    report = gate.check(project, repo)
    assert report.can_publish is False
    assert any("2" in g or "3" in g for g in report.failed_gates)
