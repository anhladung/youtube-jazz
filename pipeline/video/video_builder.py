"""Render and verify a YouTube-ready still-image music video."""

from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

from pipeline.common.validator import ValidationError, require_file, resolve_executable


def _run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, check=False)
    if result.returncode:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{details}")
    return result


def prepare_thumbnail(source: Path, output: Path, *, config: dict[str, Any], ffmpeg_value: str) -> Path:
    ffmpeg = resolve_executable(ffmpeg_value)
    require_file(source, "thumbnail image")
    width, height = int(config.get("width", 3840)), int(config.get("height", 2160))
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    max_bytes = int(config.get("max_bytes", 2_000_000))
    # q:v 2 is the best practical JPEG quality. Increase only when needed to
    # meet YouTube's thumbnail upload-size limit.
    for quality in (2, 3, 4, 5, 6, 7, 8, 10, 12):
        _run([ffmpeg, "-y", "-hide_banner", "-i", str(source), "-vf", vf,
              "-frames:v", "1", "-update", "1", "-q:v", str(quality), str(output)])
        if output.stat().st_size <= max_bytes:
            return require_file(output, "normalized thumbnail")
    raise ValidationError(f"Thumbnail remains larger than {max_bytes} bytes: {output}")


def render_video(thumbnail: Path, audio: Path, output: Path, *, config: dict[str, Any], ffmpeg_value: str) -> Path:
    ffmpeg = resolve_executable(ffmpeg_value)
    require_file(thumbnail, "thumbnail image")
    require_file(audio, "audio master")
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height, fps = int(config.get("width", 1920)), int(config.get("height", 1080)), int(config.get("fps", 30))
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase:out_range=tv,"
        f"crop={width}:{height},format={config.get('pixel_format', 'yuv420p')},"
        "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
    )
    _run([
        ffmpeg, "-y", "-hide_banner", "-loop", "1", "-framerate", str(fps), "-i", str(thumbnail), "-i", str(audio),
        "-vf", vf, "-r", str(fps), "-c:v", str(config.get("codec", "libx264")),
        "-profile:v", str(config.get("profile", "high")), "-b:v", str(config.get("video_bitrate", "8M")),
        "-maxrate", str(config.get("max_bitrate", "12M")), "-bufsize", str(config.get("buffer_size", "16M")),
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", str(config.get("audio_codec", "aac")), "-b:a", str(config.get("audio_bitrate", "384k")),
        "-ar", str(config.get("audio_sample_rate", 48000)), "-ac", "2", "-movflags", "+faststart", "-shortest", str(output),
    ])
    return require_file(output, "rendered video")


def probe_media(path: Path, ffprobe_value: str) -> dict[str, Any]:
    ffprobe = resolve_executable(ffprobe_value)
    result = _run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture=True)
    return json.loads(result.stdout or "{}")


def validate_video(path: Path, *, config: dict[str, Any], ffmpeg_value: str, ffprobe_value: str) -> dict[str, Any]:
    require_file(path, "rendered video")
    payload = probe_media(path, ffprobe_value)
    streams = payload.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    issues: list[str] = []
    if not video:
        issues.append("missing video stream")
    else:
        if video.get("codec_name") != "h264": issues.append("video codec is not H.264")
        if (video.get("width"), video.get("height")) != (int(config.get("width", 1920)), int(config.get("height", 1080))): issues.append("video resolution mismatch")
        if video.get("pix_fmt") != str(config.get("pixel_format", "yuv420p")): issues.append("pixel format is not yuv420p")
        try:
            if abs(float(Fraction(video.get("avg_frame_rate", "0/1"))) - int(config.get("fps", 30))) > 0.01: issues.append("frame rate mismatch")
        except (ValueError, ZeroDivisionError): issues.append("invalid frame rate")
        for key in ("color_space", "color_transfer", "color_primaries"):
            if video.get(key) not in {"bt709", None}: issues.append(f"{key} is not BT.709")
    if not audio:
        issues.append("missing audio stream")
    else:
        if audio.get("codec_name") != "aac": issues.append("audio codec is not AAC")
        if int(audio.get("sample_rate", 0)) != int(config.get("audio_sample_rate", 48000)): issues.append("audio sample rate mismatch")
        if int(audio.get("channels", 0)) != 2: issues.append("audio is not stereo")
    _run([resolve_executable(ffmpeg_value), "-v", "error", "-i", str(path), "-f", "null", "NUL"], capture=True)
    report = {"status": "passed" if not issues else "failed", "file": str(path.resolve()),
              "size_bytes": path.stat().st_size, "duration_seconds": float(payload.get("format", {}).get("duration", 0) or 0),
              "issues": issues, "probe": payload}
    if issues: raise ValidationError("Video validation failed: " + "; ".join(issues))
    return report
