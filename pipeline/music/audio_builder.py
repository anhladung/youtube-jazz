"""Build a high-quality continuous PCM master from a locked playlist."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pipeline.common.validator import ValidationError, require_file, resolve_executable


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{details}")
    return result


def build_audio_master(
    track_files: list[Path],
    output_path: Path,
    *,
    config: dict[str, Any],
    ffmpeg_value: str = "ffmpeg",
) -> Path:
    if not track_files:
        raise ValidationError("Cannot build audio master from an empty playlist")
    ffmpeg = resolve_executable(ffmpeg_value)
    for path in track_files:
        require_file(path, "playlist track")

    sample_rate = int(config.get("sample_rate", 48000))
    crossfade = float(config.get("crossfade_seconds", 3))
    codec = str(config.get("master_codec", "pcm_s24le"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate = output_path.with_name(output_path.stem + ".unnormalized.wav")

    command = [ffmpeg, "-y", "-hide_banner"]
    for path in track_files:
        command.extend(["-i", str(path)])

    filters: list[str] = []
    for index in range(len(track_files)):
        filters.append(
            f"[{index}:a]aresample={sample_rate},"
            "aformat=sample_fmts=fltp:channel_layouts=stereo"
            f"[a{index}]"
        )
    if len(track_files) == 1:
        output_label = "a0"
    else:
        previous = "a0"
        for index in range(1, len(track_files)):
            output_label = f"mix{index}"
            filters.append(
                f"[{previous}][a{index}]acrossfade=d={crossfade}:c1=tri:c2=tri"
                f"[{output_label}]"
            )
            previous = output_label

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{output_label}]",
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            "-c:a",
            codec,
            str(intermediate),
        ]
    )
    run_command(command)

    measured = analyze_loudness(intermediate, ffmpeg)
    loudnorm = (
        "loudnorm=I=-15:TP=-1.0:LRA=11:linear=true:"
        f"measured_I={measured['input_i']}:"
        f"measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:"
        f"measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:print_format=summary"
    )
    run_command(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-i",
            str(intermediate),
            "-af",
            loudnorm,
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            "-c:a",
            codec,
            str(output_path),
        ]
    )
    intermediate.unlink(missing_ok=True)
    return require_file(output_path, "audio master")


def analyze_loudness(path: Path, ffmpeg: str) -> dict[str, str]:
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-15:TP=-1.0:LRA=11:print_format=json",
            "-f",
            "null",
            "NUL",
        ],
        capture=True,
    )
    text = result.stderr or ""
    matches = re.findall(r"\{[\s\S]*?\}", text)
    if not matches:
        raise RuntimeError("FFmpeg loudnorm analysis did not return JSON")
    payload = json.loads(matches[-1])
    required = {"input_i", "input_tp", "input_lra", "input_thresh", "target_offset"}
    if not required.issubset(payload):
        raise RuntimeError(f"Incomplete loudnorm analysis: {payload}")
    return {key: str(payload[key]) for key in required}
