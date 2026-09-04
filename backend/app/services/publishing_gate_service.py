"""Publishing gate service.

All conditions that must pass before a YouTube upload job can be created.
Gate logic runs in the API layer — n8n cannot bypass it.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateReport:
    can_publish: bool
    failed_gates: list[str] = field(default_factory=list)


class PublishingGateService:
    """Checks every pre-publish condition and returns a GateReport.

    Rules (fail-closed):
    1. All scenes have at least one approved prompt decision.
    2. All scenes have a SUCCEEDED production job at the current prompt_version.
    3. All clip_artifacts for SUCCEEDED jobs have review_status == "approved".
    4. No fact in project.facts has status == "contradicted".
    5. An export manifest exists and has not expired.
    6. A final_review_event exists with decision == "approved" for the manifest.
    7. No active youtube_upload_job in UPLOADING state (prevent double-upload).
    """

    def check(self, project, repository) -> GateReport:
        from datetime import datetime, timezone

        failed: list[str] = []

        # Gate 1: prompt approvals per scene
        approval_events: list = getattr(repository, "approval_events", [])
        # Support both in-memory list and SQL repository
        if hasattr(repository, "get_approval_events_for_project"):
            approval_events = repository.get_approval_events_for_project(str(project.id))

        approved_scenes: set[int] = {
            ev.scene_number
            for ev in approval_events
            if getattr(ev, "project_id", None) == str(project.id)
            and ev.decision == "approved"
        }
        missing_approvals = [
            s.number for s in project.scenes if s.number not in approved_scenes
        ]
        if missing_approvals:
            failed.append(
                f"Scenes missing prompt approval: {missing_approvals}"
            )

        # Gate 2: SUCCEEDED production job per scene at current prompt_version
        for scene in project.scenes:
            prompt = project.prompts.get(scene.number)
            if prompt is None:
                failed.append(f"Scene {scene.number}: no prompt generated.")
                continue
            prod_job = getattr(repository, "get_production_for_prompt", lambda *_: None)(
                str(project.id), scene.number, prompt.version_number
            )
            if prod_job is None or prod_job.status != "SUCCEEDED":
                status = prod_job.status if prod_job else "MISSING"
                failed.append(
                    f"Scene {scene.number}: production job status is {status} (need SUCCEEDED)."
                )

            # Gate 3: clip artifact approved
            if prod_job and prod_job.status == "SUCCEEDED" and prod_job.artifact_id:
                clip_artifacts = getattr(repository, "clip_artifacts", {})
                artifact = (
                    clip_artifacts.get(prod_job.artifact_id)
                    if isinstance(clip_artifacts, dict)
                    else None
                )
                if hasattr(repository, "get_clip_artifact"):
                    artifact = repository.get_clip_artifact(prod_job.artifact_id)
                if artifact is None:
                    failed.append(f"Scene {scene.number}: clip artifact not found.")
                elif artifact.review_status != "approved":
                    failed.append(
                        f"Scene {scene.number}: clip review_status is "
                        f"'{artifact.review_status}' (need 'approved')."
                    )

        # Gate 4: no contradicted facts
        contradicted = [
            f.id for f in project.facts if f.status.value == "contradicted"
        ]
        if contradicted:
            failed.append(
                f"Contradicted facts must be resolved before publishing: {contradicted}"
            )

        # Gate 5: export manifest exists and not expired
        manifest = None
        if hasattr(repository, "get_latest_export_manifest"):
            manifest = repository.get_latest_export_manifest(str(project.id))
        elif hasattr(repository, "export_manifests"):
            # In-memory: find latest for project
            manifests = [
                m for m in repository.export_manifests.values()
                if m.project_id == str(project.id)
            ]
            manifest = max(manifests, key=lambda m: m.created_at, default=None)

        if manifest is None:
            failed.append("No export manifest found. Create one first.")
        elif manifest.expires_at < datetime.now(timezone.utc):
            failed.append("Export manifest has expired. Recreate it.")

        # Gate 6: final review approved for this manifest
        final_review = None
        if manifest is not None:
            if hasattr(repository, "get_latest_final_review"):
                final_review = repository.get_latest_final_review(str(project.id))
            elif hasattr(repository, "final_review_events"):
                reviews = [
                    ev for ev in repository.final_review_events
                    if ev.project_id == str(project.id)
                    and ev.manifest_id == manifest.manifest_id
                ]
                final_review = reviews[-1] if reviews else None

        if final_review is None:
            failed.append(
                "Final review has not been submitted. A human must approve the full package."
            )
        elif final_review.decision != "approved":
            failed.append(
                f"Final review decision is '{final_review.decision}'. Must be 'approved'."
            )
        elif manifest and final_review.manifest_id != manifest.manifest_id:
            failed.append(
                "Final review references a superseded manifest. Re-approve the current manifest."
            )

        # Gate 7: no active upload in progress
        active_upload = None
        if hasattr(repository, "get_active_upload_job"):
            active_upload = repository.get_active_upload_job(str(project.id))
        elif hasattr(repository, "youtube_upload_jobs"):
            active_upload = next(
                (
                    j for j in repository.youtube_upload_jobs.values()
                    if j.project_id == str(project.id) and j.status == "UPLOADING"
                ),
                None,
            )
        if active_upload is not None:
            failed.append(
                f"Upload job {active_upload.job_id} is already in UPLOADING state."
            )

        # Gate 8: multi-platform export integrity
        target_platforms = getattr(project.input, "target_platforms", [])
        platform_exports = getattr(project, "platform_exports", {}) or {}
        if len(target_platforms) > 1 or platform_exports:
            for plat in target_platforms:
                plat_key = plat.value if hasattr(plat, "value") else str(plat)
                export_rec = platform_exports.get(plat_key)
                if not export_rec or export_rec.export_status != "COMPLETED":
                    failed.append(f"Platform target '{plat_key}' is missing completed media export.")

        return GateReport(can_publish=len(failed) == 0, failed_gates=failed)
