import os
import shutil
import subprocess
from app.domain.project import Project

class FFmpegAssemblyService:
    def __init__(self) -> None:
        self.ffmpeg_path = shutil.which("ffmpeg")

    def assemble_shorts(self, project: Project) -> str:
        """Stitches the 10s scene clips together sequentially using FFmpeg.

        First combines scene video with scene audio, then concatenates in correct scene order.
        Raises RuntimeError with custom advice if FFmpeg is missing.
        """
        if not self.ffmpeg_path:
            raise RuntimeError(
                "FFmpeg executable not found on the system PATH. "
                "Install FFmpeg (https://ffmpeg.org) and add it to your system PATH to run "
                "real media assembly, or set stitch_provider to 'mock'."
            )

        project_id = str(project.id)
        total_scenes = len(project.scenes)
        scene_outputs = []

        # Ensure directories exist
        os.makedirs("app/static/temp", exist_ok=True)
        os.makedirs("app/static/output", exist_ok=True)

        try:
            # 1. Overlay audio on visual clip for each scene
            for i in range(1, total_scenes + 1):
                video_input = f"app/static/video/{project_id}_{i}.mp4"
                audio_input = f"app/static/audio/{project_id}_{i}.mp3"
                scene_output = f"app/static/temp/{project_id}_scene_{i}_muxed.mp4"

                # Check if input files exist
                if not os.path.exists(video_input) or not os.path.exists(audio_input):
                    raise FileNotFoundError(
                        f"Media files for Scene {i} not found. Ensure rendering & TTS are complete."
                    )

                # ffmpeg command to mux audio & video
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", video_input,
                    "-i", audio_input,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    scene_output
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                scene_outputs.append(scene_output)

            # 2. Concat all scenes in chronological order
            list_file_path = f"app/static/temp/{project_id}_list.txt"
            with open(list_file_path, "w") as lf:
                for path in scene_outputs:
                    # FFmpeg concat file paths should be normalized and escaped
                    normalized = os.path.abspath(path).replace("\\", "/")
                    lf.write(f"file '{normalized}'\n")

            final_output_path = f"app/static/output/{project_id}_final.mp4"
            concat_cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                final_output_path
            ]
            subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return final_output_path
        finally:
            # Cleanup temporary files
            try:
                if os.path.exists(f"app/static/temp/{project_id}_list.txt"):
                    os.remove(f"app/static/temp/{project_id}_list.txt")
                for path in scene_outputs:
                    if os.path.exists(path):
                        os.remove(path)
            except Exception:
                pass
