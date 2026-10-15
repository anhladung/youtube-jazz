"""Start, validate, or preview the YouTube Vintage Jazz livestream."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from pipeline.common.channels import resolve_channel
from pipeline.common.config import PROJECT_ROOT, expand_path, load_config
from pipeline.livestream.runner import (
    build_ffmpeg_command,
    load_available_tracks,
    masked_command,
    run_supervisor,
    settings_from_config,
    write_shuffled_playlist,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Alternative YAML config file")
    parser.add_argument("--channel", default=None, help="vintage-jazz or relax-music")
    parser.add_argument("--visual", type=Path, help="Static image; defaults to the newest job thumbnail")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print a masked command")
    parser.add_argument(
        "--preview-seconds",
        type=int,
        metavar="SECONDS",
        help="Render a short local MP4 instead of connecting to YouTube",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config.resolve() if args.config else None)
    profile = resolve_channel(config, args.channel)
    config = profile.config
    print(f"Channel: {profile.label} [{profile.channel_id}]")
    visual = expand_path(args.visual) if args.visual else None
    settings = settings_from_config(config, visual)
    missing_visuals = [path for path in settings.visual_paths if not path.is_file()]
    if missing_visuals:
        raise FileNotFoundError(f"Visual image not found: {missing_visuals[0]}")
    tracks = load_available_tracks(settings.registry_path)
    write_shuffled_playlist(tracks, settings.playlist_path, seed=42 if args.dry_run else None)

    if args.preview_seconds:
        output = PROJECT_ROOT / "output" / profile.channel_id / "livestream_preview.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        command = build_ffmpeg_command(
            settings, str(output), args.preview_seconds, settings.visual_paths[0]
        )
        print(masked_command(command))
        subprocess.run(command, check=True)
        print(f"Preview created: {output}")
        return 0

    if args.dry_run:
        command = build_ffmpeg_command(
            settings,
            f"{settings.stream_url.rstrip('/')}/STREAM_KEY",
            settings.visual_duration_seconds,
            settings.visual_paths[0],
        )
        print(f"Validated {len(tracks)} tracks")
        print(
            f"Visuals: {len(settings.visual_paths)} images, "
            f"{settings.visual_duration_seconds // 60} minutes each"
        )
        print(masked_command(command))
        return 0

    run_supervisor(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

