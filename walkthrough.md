# ContentGenAutomator — Phase 8 Modular Sprints Walkthrough

We have successfully implemented all sprints (Sprints 5–8) sequentially as modular "plug-and-play" Lego components. Each module is fully optional and customizable via the workspace dashboard.

---

## 🤖 Modular "Plug-and-Play" Architecture

We added four provider settings to each project. Users can choose different combinations:
- **TTS Provider:** `"mock"` | `"elevenlabs"`
- **Video Generator:** `"mock"` | `"runway"` | `"kling"`
- **Media Stitcher:** `"mock"` | `"ffmpeg"`
- **Publish Provider:** `"mock"` | `"youtube"`

### 1. Sprint 5 — ElevenLabs Voice Synthesis (`ElevenLabsTTSService`)
- **Action:** Submits the narration script of each approved scene to the ElevenLabs API to generate a professional voiceover file.
- **Local Asset Serving:** The resulting voiceover is saved to `backend/app/static/audio/` and served via `/static/audio/{project_id}_{scene_number}.mp3`.
- **Soft-Fail Fallback:** If `ELEVENLABS_API_KEY` is not present, it logs a clear setup warning and falls back to a simulated audio file instead of crashing.

### 2. Sprint 6 — Visual Clip Generation (`RealVideoGenService`)
- **Action:** Submits visual storyboard prompts to Runway Gen-3 or Kling AI to synthesize vertical 10-second MP4 clips.
- **Local Asset Serving:** Clips are saved to `backend/app/static/video/` and served via `/static/video/{project_id}_{scene_number}.mp4`.
- **Soft-Fail Fallback:** If API credentials are not set, it falls back to custom simulated visual outputs.

### 3. Sprint 7 — Sequential Clip Stitching & Audio Muxing (`FFmpegAssemblyService`)
- **Action:** Combines each scene's visual clip and narration voiceover track, then stitches the 10-second clips sequentially in scene order into a single final Short video (10s, 20s, or 30s long).
- **Tool Detection:** Checks if `ffmpeg` is available on the system PATH.
- **Actionable Setup Alerts:** If `ffmpeg` is missing (as on this system), the service raises a clean, descriptive exception alerting the user: *"FFmpeg executable not found on the system PATH. Install FFmpeg (https://ffmpeg.org) or set stitch_provider to 'mock'."*

### 4. Sprint 8 — Direct YouTube Publication (`YouTubePublishService`)
- **Action:** Connects to the YouTube Data API v3 using OAuth2 credentials to upload final stitched video files directly to the channel.
- **Metadata Sync:** Sets the title, description, and hashtags from the signed-off final review package, and uploads the video file as a vertical Short.

---

## 🎬 How to Test and Run

1. Start the API backend:
   ```powershell
   cd backend
   uvicorn app.main:app --reload
   ```
2. Start the Next.js frontend dashboard:
   ```powershell
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:3000` in your browser.
4. Set up a topic, facts, and select your preferred providers:
   - To test real video/audio generation, select **ElevenLabs TTS** or **Runway Gen-3**.
   - To test mock mode, select **Simulated (Mock)** (great for fast testing and dev).
5. Toggle **Autonomous Auto-Pilot Mode** to watch the self-driving agent execute the entire workflow end-to-end!
