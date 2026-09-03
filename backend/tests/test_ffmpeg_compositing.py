import os
from uuid import uuid4
from app.services.ffmpeg_service import FFmpegAssemblyService
from app.services.brand_kit_service import BrandKit
from app.domain.project import Project, ProjectInput

def test_ffmpeg_watermark_filter_construction():
    service = FFmpegAssemblyService()
    kit_top_right = BrandKit(
        studio_id="test_studio",
        studio_name="Cyber Studio",
        watermark_opacity=0.75,
        watermark_position="top_right"
    )
    fgraph = service.build_watermark_filter(kit_top_right)
    assert "colorchannelmixer=aa=0.75" in fgraph
    assert "overlay=W-w-30:30" in fgraph

    kit_bottom_right = BrandKit(
        studio_id="test_studio",
        studio_name="Cyber Studio",
        watermark_opacity=0.9,
        watermark_position="bottom_right"
    )
    fgraph_br = service.build_watermark_filter(kit_bottom_right)
    assert "colorchannelmixer=aa=0.9" in fgraph_br
    assert "overlay=W-w-30:H-h-30" in fgraph_br


def test_ffmpeg_crop_filter_aspect_ratios():
    service = FFmpegAssemblyService()
    crop_1_1 = service.build_crop_filter("1:1")
    assert "crop=min(iw\\,ih):min(iw\\,ih)" in crop_1_1

    crop_9_16 = service.build_crop_filter("9:16")
    assert "crop=ih*(9/16):ih" in crop_9_16


def test_ffmpeg_multi_format_export_dry_run():
    service = FFmpegAssemblyService()
    project = Project(
        id=uuid4(),
        input=ProjectInput(topic="Quantum Mechanics", duration_seconds=10)
    )
    export_result = service.export_multi_format(project, dry_run=True)
    assert export_result["status"] == "completed"
    assert export_result["primary_9_16"].endswith(f"{project.id}_9_16.mp4")
    assert export_result["square_1_1"].endswith(f"{project.id}_1_1.mp4")
    assert os.path.exists(export_result["primary_9_16"])
    assert os.path.exists(export_result["square_1_1"])
