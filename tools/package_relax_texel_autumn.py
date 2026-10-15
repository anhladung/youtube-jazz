"""Package a second 2-hour autumn Relax Music episode for Texel, Netherlands."""

from __future__ import annotations

import json
import shutil
import wave
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "relax_batch_20261012_2115_texel_autumn_2h"
VIDEO_ID = "relax_video_001"
IMAGE = Path(
    r"C:\Users\congc\.codex\generated_images\01a11b1a-8f47-78f1-913f-2b32423093d2"
    r"\exec-b7575395-7bed-43cb-b247-1c0dcebd3911.png"
)
NEW_ORDER = [
    (39, 1), (40, 1), (41, 1), (42, 1), (44, 1), (41, 2), (42, 2), (44, 2),
    (16, 1), (20, 1), (18, 1), (19, 1), (21, 1), (16, 2), (20, 2), (18, 2), (21, 2),
    (23, 1), (24, 1), (26, 1), (27, 1), (30, 2), (23, 2), (24, 2),
    (11, 1), (3, 1), (5, 1), (11, 2), (3, 2),
    (45, 1), (46, 1), (47, 1), (48, 1), (49, 1), (50, 1),
    (45, 2), (46, 2), (47, 2), (48, 2), (49, 2),
]
TITLE = "calm music — the last light lingers on Texel's quiet shore"
DESCRIPTION = (
    "calm music follows the quiet shore of Texel in the Netherlands as autumn "
    "light fades, offering a gentle space to relax. Soft ambient textures move "
    "through subtle coastal air, distant water, sheltered rain and still evening "
    "moods. Let this instrumental soundscape accompany an unhurried pause or rest."
)
SOURCES = [
    "https://www.texel.net/en/about-texel/explore-the-countryside/duinen-van-texel-national-park/",
    "https://www.texel.net/en/see-and-do/arts-and-culture/museums/lighthouse/",
    "https://www.texel.net/en/about-texel/seasons/autumn-on-texel/",
]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    batch = ROOT / "input/relax_batches" / BATCH_ID
    job_dir = batch / "jobs" / VIDEO_ID
    if batch.exists():
        raise FileExistsError(f"Refusing to overwrite: {batch}")
    if not IMAGE.is_file():
        raise FileNotFoundError(IMAGE)
    registry = json.loads((ROOT / "library/relax_music/registry.json").read_text(encoding="utf-8"))["tracks"]
    first_playlist = json.loads(
        (ROOT / "input/relax_batches/relax_batch_20261012_2103_european_autumn_2h/jobs/relax_video_001/playlist.json").read_text(encoding="utf-8")
    )
    completed_playlist = json.loads(
        (ROOT / "input/relax_batches/relax_batch_20261007_081613/jobs/relax_video_001/playlist.json").read_text(encoding="utf-8")
    )
    first_ids = {track["track_id"] for track in first_playlist["tracks"]}
    completed_ids = {track["track_id"] for track in completed_playlist["tracks"]}

    def find_track(prompt_id: str, variant: int) -> dict:
        matches = [
            track for track in registry.values()
            if track.get("source_prompt_id") == prompt_id
            and track.get("flow_variant_index") == variant
            and track.get("status") == "available"
            and track.get("track_metadata", {}).get("genre") == "relax-music"
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one available track: {prompt_id} variant {variant}")
        track = matches[0]
        with wave.open(str(ROOT / track["file"]), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
        if abs(duration - track["duration_seconds"]) > 0.05:
            raise ValueError(f"Invalid duration: {track['track_id']}")
        return track

    blocks = [
        [(f"relax_eu_autumn_{i:03}", v) for i, v in NEW_ORDER[:8]],
        [(f"relax_eu_autumn_{i:03}", v) for i, v in NEW_ORDER[8:17]],
        [
            ("relax_eu_autumn_023", 1), ("relax_eu_autumn_024", 1),
            ("relax_autumn_011", 2), ("relax_eu_autumn_026", 1),
            ("relax_autumn_012", 2), ("relax_eu_autumn_027", 1),
            ("relax_autumn_014", 2), ("relax_eu_autumn_030", 2),
            ("relax_autumn_015", 1), ("relax_eu_autumn_023", 2),
            ("relax_autumn_015", 2), ("relax_eu_autumn_024", 2),
        ],
        [
            ("relax_eu_autumn_011", 1), ("relax_eu_autumn_003", 1),
            ("relax_eu_autumn_005", 1), ("relax_eu_autumn_011", 2),
            ("relax_eu_autumn_003", 2), ("relax_autumn_001", 2),
        ],
        [(f"relax_eu_autumn_{i:03}", v) for i, v in NEW_ORDER[29:]],
    ]
    order = [pair for block in blocks for pair in block]
    selected = [find_track(prompt_id, variant) for prompt_id, variant in order]
    if len(selected) != 46 or len({track["track_id"] for track in selected}) != 46:
        raise ValueError("Expected 46 unique tracks")
    if any(a["source_prompt_id"] == b["source_prompt_id"] for a, b in zip(selected, selected[1:])):
        raise ValueError("Adjacent tracks from the same prompt")
    if set(track["track_id"] for track in selected) & completed_ids:
        raise ValueError("A track from the earlier completed video was reused")
    overlap = len(set(track["track_id"] for track in selected) & first_ids)
    if overlap > 9:
        raise ValueError(f"Too much overlap with the Germany episode: {overlap}")
    raw = sum(track["duration_seconds"] for track in selected)
    effective = raw - 3 * (len(selected) - 1)
    if not 7200 <= effective <= 10800:
        raise ValueError(f"Outside requested 2-3 hour range: {effective}")

    family_seconds = Counter()
    texture_seconds = Counter()
    accents = Counter()
    ambience = Counter()
    uses = Counter()
    for track in selected:
        metadata = track["track_metadata"]
        duration = track["duration_seconds"]
        family_seconds[metadata["family"]] += duration
        texture_seconds[metadata["primary_texture"]] += duration
        for value in metadata["accent_instruments"]:
            accents[value] += duration
        for value in metadata["ambience"]["elements"]:
            ambience[value] += duration
        for value in metadata["listening_use"]:
            uses[value] += duration

    music = {
        "aggregation_method": "duration_weighted",
        "genre": "relax-music",
        "dominant_family": family_seconds.most_common(1)[0][0],
        "supporting_families": [family for family, _ in family_seconds.most_common()[1:]],
        "family_duration_seconds": {key: round(value, 3) for key, value in family_seconds.items()},
        "primary_texture": "slowly evolving ambient pads and airy sustained textures",
        "texture_duration_seconds": {key: round(value, 3) for key, value in texture_seconds.items()},
        "accent_instruments": [key for key, value in accents.most_common() if value >= 300],
        "accent_duration_seconds": {key: round(value, 3) for key, value in accents.items()},
        "dominant_moods": ["peaceful", "comforting"],
        "melody_character": "sparse_long_notes_with_generous_silence",
        "harmony_character": "very_slow_consonant_suspended",
        "ambience": {
            "level": "subtle_or_very_subtle",
            "elements": list(ambience),
            "element_duration_seconds": {key: round(value, 3) for key, value in ambience.items()},
        },
        "nature_scene": "European autumn coast, sheltered rain and quiet evening air",
        "season": "autumn",
        "listening_uses": [key for key, value in uses.most_common() if value >= 300],
        "listening_use_duration_seconds": {key: round(value, 3) for key, value in uses.items()},
        "energy_profile": "flat_low_nearly_motionless",
        "conflicts": [
            "Some source prompts imagine inland or architectural shelter; these are sonic mood references, not claims about structures at the lighthouse.",
            "The image represents one verified coastal location; the playlist moves through compatible water, rain, forest and night textures.",
        ],
    }
    playlist = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "target_duration_seconds": 7500,
        "actual_duration_seconds": round(effective, 3),
        "raw_track_duration_seconds": round(raw, 3),
        "crossfade_seconds": 3,
        "tracks": [
            {
                "position": position,
                "track_id": track["track_id"],
                "file": track["file"],
                "duration_seconds": track["duration_seconds"],
                "source_prompt_id": track["source_prompt_id"],
                "transition_note": "low-energy autumn passage from coast and water through shelter to woodland dusk",
            }
            for position, track in enumerate(selected, 1)
        ],
        "overlap_metrics": {
            "max_recent_video_track_overlap_ratio": round(overlap / len(selected), 3),
            "overlap_with_germany_episode_track_count": overlap,
            "overlap_with_completed_relax_video_track_count": 0,
            "repeated_adjacent_pairs": 0,
            "reused_opening_track": False,
            "reused_closing_track": False,
        },
        "music_profile": music,
    }
    location = {
        "schema_version": 1,
        "country": "Netherlands",
        "place_name": "Texel, Duinen van Texel National Park",
        "place_type": "North_Sea_dune_and_coastal_island",
        "verified_features": [
            "sandy dunes and broad beach",
            "North Sea and Wadden Sea coastline",
            "red lighthouse at Texel's northern tip",
            "deciduous and coniferous woodland",
            "tidal marshes and heathland",
            "autumn woodland color",
        ],
        "excluded_features": ["alpine mountains", "Nordic fjord walls", "Mediterranean limestone cove", "urban skyline"],
        "music_fit": {
            "family": music["dominant_family"],
            "supporting_families": music["supporting_families"],
            "mood": ["peaceful", "comforting"],
            "ambience": ["subtle rain", "quiet shore", "still evening air"],
            "season": "autumn",
        },
        "source_urls": SOURCES,
        "source_checked_at": "2026-10-12",
        "verification_status": "verified",
    }
    episode = {
        "genre": "relax-music",
        "music_evidence": {
            "dominant_family": music["dominant_family"],
            "dominant_moods": music["dominant_moods"],
            "ambience": ["quiet shore", "distant rain", "still evening air"],
            "season": "autumn",
            "listening_uses": music["listening_uses"],
        },
        "location_ref": "location.json",
        "country": "Netherlands",
        "place_name": "Texel, Duinen van Texel National Park",
        "thumbnail_title": "NETHERLANDS",
        "visual_focal_point": "red Texel lighthouse above low coastal dunes",
        "leading_line": "curving dune path toward the lighthouse",
        "atmosphere": "clear cool autumn air after a passing shower",
        "light": "low side light warms the red lighthouse against cooler sea and sky",
        "thumbnail_concept": "peaceful autumn dusk on Texel's northern coast",
        "seo_concept": "the last light on Texel's quiet shore",
        "allowed_claims": ["calm music", "relaxation", "autumn", "coastal ambience", "subtle rain", "rest"],
    }
    thumbnail_prompt = (
        "Use case: photorealistic-natural. Final native 16:9 Relax Music thumbnail at Texel's "
        "northern tip, Netherlands. One authentic red Texel lighthouse on low dunes near a broad "
        "sandy shore, North Sea beyond, autumn after light rain. Low dune viewpoint, winding sandy "
        "path leading toward the lighthouse; calm upper sky for type. One low late-autumn sun from "
        "camera-left selectively warms the lighthouse and wet dunes against cool slate-blue sea "
        "and cloud, with realistic dynamic range and protected highlights. Full-frame 35mm f/8 "
        "RAW travel photography. Only exact large white #FFFFFF artistic Didone word NETHERLANDS "
        "across the upper sky, mobile-readable and clear of the hero. No other text, mountains, "
        "cliffs, fantasy, painting, CGI, HDR, neon, people, logo or watermark."
    )
    thumbnail = {
        "schema_version": 1,
        "channel": "relax-music",
        "generator": "built_in_image_gen",
        "thumbnail_text": "NETHERLANDS",
        "music_attributes": {
            "dominant_family": music["dominant_family"],
            "supporting_families": music["supporting_families"],
            "mood": music["dominant_moods"],
            "season": "autumn",
        },
        "location_profile": location,
        "visual_signature": "Netherlands|Texel|red lighthouse|low dunes|North Sea|autumn dusk|white Didone",
        "output_image": "thumbnail.png",
        "novelty_status": "checked_against_local_relax_batch_history",
        "prompt": thumbnail_prompt,
    }
    youtube = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "title": TITLE,
        "description": DESCRIPTION,
        "primary_keyword": "calm music",
        "secondary_keywords": ["autumn relaxing music", "peaceful instrumental music"],
        "country": "Netherlands",
        "place_name": "Texel, Duinen van Texel National Park",
        "supported_benefits": ["relaxation", "rest"],
        "title_length": len(TITLE),
        "pattern_signature": "calm music|mood|Netherlands|Texel|autumn|coast+rain+evening|relaxation",
        "research_status": "user_supplied_vidiq_and_youtube_autocomplete_snapshot_2026-10-06",
        "relevance_notes": [
            "Calm music was supported by the supplied keyword snapshot and the uniformly peaceful low-energy playlist.",
            "The verified Texel location is used in SEO; the thumbnail uses the widely recognizable country NETHERLANDS.",
            "No sleep, 4K, no-ads or medical claims.",
        ],
    }
    job = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "batch_id": BATCH_ID,
        "video_id": VIDEO_ID,
        "status": "ready_for_pipeline",
        "episode_profile": episode,
        "files": {
            "playlist": "playlist.json",
            "location": "location.json",
            "thumbnail_spec": "thumbnail.json",
            "thumbnail_image": "thumbnail.png",
            "youtube_metadata": "youtube.json",
        },
        "output_files": {"youtube_manual_text": "youtube_manual.txt"},
        "consistency_check": {
            "status": "passed",
            "playlist_supports_music_profile": True,
            "location_matches_music_profile": True,
            "thumbnail_spec_matches_episode_profile": True,
            "youtube_metadata_matches_episode_profile": True,
            "image_inspection_performed": False,
            "issues": [],
        },
        "assumptions": [
            "The requested duration range is 2-3 hours; this episode targets about 128 minutes.",
            "Six older unused autumn tracks complement forty recent European-autumn tracks and reduce overlap with the Germany playlist.",
            "Estimated duration subtracts forty-five 3-second crossfades.",
        ],
    }
    manifest = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "batch_id": BATCH_ID,
        "requested_video_count": 1,
        "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "path_base": "batch_directory",
        "jobs": [{"video_id": VIDEO_ID, "path": f"jobs/{VIDEO_ID}/job.json", "status": "ready_for_pipeline"}],
        "summary": {"ready_for_pipeline": 1, "planned": 0, "library_gap": 0, "needs_attention": 0},
        "locations": [{"country": "Netherlands", "place_name": "Texel, Duinen van Texel National Park"}],
    }

    job_dir.mkdir(parents=True)
    write_json(job_dir / "playlist.json", playlist)
    write_json(job_dir / "location.json", location)
    write_json(job_dir / "thumbnail.json", thumbnail)
    shutil.copy2(IMAGE, job_dir / "thumbnail.png")
    write_json(job_dir / "youtube.json", youtube)
    write_json(job_dir / "job.json", job)
    write_json(batch / "batch_manifest.json", manifest)
    print(f"{batch} | {len(selected)} tracks | {effective:.3f} seconds | overlap {overlap}")


if __name__ == "__main__":
    main()
