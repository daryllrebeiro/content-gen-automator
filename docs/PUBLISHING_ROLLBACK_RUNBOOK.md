# 🚨 Operational Runbook: Video Publishing Rollback & Unpublish

## Purpose
This runbook defines the emergency procedure for withdrawing, unpublishing, and rolling back published YouTube Shorts and associated multi-platform distribution packages in ContentGenAutomator Studio.

---

## 1. When to Trigger a Rollback

Trigger a publishing rollback immediately if:
* **Brand Safety Breach:** A published video contains unauthorized brand mentions, trademark infringements, or safety violations.
* **Factual Discrepancy:** A hallucinated claim slipped past pre-production grounding and was disputed.
* **Audio/Visual Glitch:** Desynchronized captions, corrupt video frames, or audio artifacts were identified post-publication.
* **Director/Creator Request:** The creator requests a take-down or correction.

---

## 2. Automated Rollback via API

Use the authenticated Integration endpoint to trigger a zero-downtime automated rollback:

```http
POST /api/integrations/projects/{project_id}/publish/unpublish
Authorization: Bearer <INTEGRATION_SERVICE_TOKEN>
Content-Type: application/json

{
  "actor": "lead_editor",
  "reason": "Brand policy update requires immediate retraction"
}
```

### Expected Response (`200 OK`):
```json
{
  "project_id": "8f3b23e1-...",
  "status": "UNPUBLISHED",
  "message": "Project 8f3b23e1-... successfully rolled back and unpublished by lead_editor.",
  "unpublished_at": "2026-09-09T08:15:00Z"
}
```

### Automated Actions Executed:
1. **YouTube Privacy State:** If uploaded via live YouTube OAuth2, the video's privacy status is updated to `private` immediately, halting public distribution.
2. **Project State:** Project lifecycle status transitions to `UNPUBLISHED`.
3. **Audit Trail:** An immutable `project.unpublished` SOC2 audit event is logged with the actor's identity and stated reason.

---

## 3. Manual Fallback Runbook (YouTube Studio UI)

If API credentials or network connectivity fail:
1. Navigate to [YouTube Studio](https://studio.youtube.com).
2. Select **Content** ➔ **Shorts**.
3. Locate the video by `youtube_video_id` (obtained from `/api/integrations/youtube-upload-jobs/{job_id}`).
4. Under **Visibility**, change from `Public` to `Private` or select **Delete forever**.
5. Log into the ContentGenAutomator DB and update the project status:
   ```sql
   UPDATE projects SET status = 'UNPUBLISHED' WHERE id = '<project_id>';
   ```

---

## 4. Post-Rollback Procedure

1. **Verify Visibility:** Check the short's direct link in an incognito browser to confirm it displays *"This video is private"*.
2. **Regenerate & Resubmit:** If an amended version is needed, increment the scene version, request prompt regeneration with updated constraints, re-run watsonx governance certification, and re-publish through the 8 fail-closed gates.
