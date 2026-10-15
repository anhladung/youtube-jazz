"""Command-line entry point for the YouTube music pipeline."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pipeline.common.channels import ChannelProfile, assert_library_queue, resolve_channel
from pipeline.common.config import load_config
from pipeline.flow.flow_automation import run_flow_queue, setup_flow_profile
from pipeline.music.library_manager import ingest_flow_queue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="youtube-music-pipeline")
    subparsers = parser.add_subparsers(dest="command")

    flow = subparsers.add_parser(
        "flow-generate", help="Generate and download WAV tracks from a Flow prompt queue"
    )
    flow.add_argument("queue", type=Path, help="Path to flow_prompts.json")
    flow.add_argument(
        "--limit", type=int, default=None, help="Process at most this many pending prompts"
    )
    flow.add_argument(
        "--config", type=Path, default=None, help="Path to an alternative config.yaml"
    )
    flow.add_argument("--channel", default=None, help="vintage-jazz or relax-music")

    setup = subparsers.add_parser(
        "flow-profile-setup",
        help="Open the dedicated flow_auto_profile_03 data directory for one-time login",
    )
    setup.add_argument(
        "--config", type=Path, default=None, help="Path to an alternative config.yaml"
    )
    setup.add_argument("--channel", default=None, help="vintage-jazz or relax-music")

    queue = subparsers.add_parser(
        "flow-queue",
        help="Process every flow_prompts.json queue under input/library_builds",
    )
    queue.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root directory containing library builds",
    )
    queue.add_argument(
        "--limit-per-build",
        type=int,
        default=None,
        help="Process at most this many prompts from each build",
    )
    queue.add_argument(
        "--config", type=Path, default=None, help="Path to an alternative config.yaml"
    )
    queue.add_argument("--channel", default=None, help="vintage-jazz or relax-music")

    ingest = subparsers.add_parser(
        "music-ingest", help="Register completed WAV outputs without running Flow"
    )
    ingest.add_argument("queue", type=Path, help="Path to flow_prompts.json")
    ingest.add_argument("--config", type=Path, default=None)
    ingest.add_argument("--channel", default=None, help="vintage-jazz or relax-music")
    return parser


def register_completed_tracks(queue_path: Path, profile: ChannelProfile) -> None:
    assert_library_queue(queue_path, profile)
    added = ingest_flow_queue(
        queue_path,
        profile.registry_path,
        channel_id=profile.channel_id,
        expected_genre=profile.expected_genre,
    )
    print(f"Registered {len(added)} new library track(s) from {queue_path}")


async def run_all_build_queues(
    profile: ChannelProfile, root: Path | None = None, limit_per_build: int | None = None
) -> None:
    config = profile.config
    root = (root or profile.library_builds_dir).resolve()
    queue_paths = sorted(root.glob("*/flow_prompts.json"))
    if not queue_paths:
        print(f"No Flow queues found under: {root.resolve()}")
        return

    print(f"Found {len(queue_paths)} Flow queue(s) under: {root.resolve()}")
    for index, queue_path in enumerate(queue_paths, start=1):
        print(f"[{index}/{len(queue_paths)}] Processing {queue_path}")
        await run_flow_queue(config.get("flow", {}), queue_path, limit=limit_per_build)
        register_completed_tracks(queue_path, profile)


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(getattr(args, "config", None))
    profile = resolve_channel(config, getattr(args, "channel", None))
    config = profile.config
    print(f"Channel: {profile.label} [{profile.channel_id}]")
    if args.command == "flow-generate":
        assert_library_queue(args.queue, profile)
        asyncio.run(
            run_flow_queue(config.get("flow", {}), args.queue, limit=args.limit)
        )
        register_completed_tracks(args.queue, profile)
    elif args.command == "flow-profile-setup":
        asyncio.run(setup_flow_profile(config.get("flow", {})))
    elif args.command == "flow-queue":
        asyncio.run(
            run_all_build_queues(
                profile, root=args.root, limit_per_build=args.limit_per_build
            )
        )
    elif args.command == "music-ingest":
        register_completed_tracks(args.queue, profile)
    else:
        print("No command supplied; running all pending Flow build queues.")
        asyncio.run(run_all_build_queues(profile))


if __name__ == "__main__":
    main()
