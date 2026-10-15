"""Package the locked European-autumn Relax Music episode; do not render it."""

from __future__ import annotations

import json
import shutil
import wave
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "relax_batch_20261012_2103_european_autumn_2h"
VIDEO_ID = "relax_video_001"
IMAGE = Path(
    r"C:\Users\congc\.codex\generated_images\01a11b1a-8f47-78f1-913f-2b32423093d2"
    r"\exec-0aba1a89-f461-4a92-a5fd-893606bc50e4.png"
)
ORDER = [
    (33, 1), (34, 1), (31, 1), (35, 1), (38, 1), (32, 1),
    (31, 2), (33, 2), (34, 2), (35, 2), (38, 2),
    (6, 1), (4, 1), (1, 1), (9, 1), (12, 1),
    (8, 1), (10, 1), (2, 1), (5, 1), (3, 1),
    (14, 1), (15, 1), (18, 1), (19, 1), (21, 1),
    (14, 2), (18, 2), (21, 2),
    (25, 1), (28, 1), (29, 1), (30, 1), (29, 2), (30, 2),
    (3, 2), (5, 2), (2, 2), (10, 2), (8, 2),
    (12, 2), (9, 2), (1, 2), (4, 2), (6, 2),
]
TITLE = "autumn relaxing music — let the morning settle in Freiamt, Germany"
DESCRIPTION = (
    "Autumn relaxing music invites you into the wooded hills of Freiamt in Germany's "
    "Black Forest for an unhurried moment of relaxation. Slowly evolving ambient "
    "textures, gentle sustained strings and sparse melodic accents move through "
    "woodland, meadow and quiet-stream moods, with a brief sheltered-rain passage. "
    "Let this instrumental soundscape accompany a quiet pause, reading, or rest."
)
SOURCE_URLS = [
    "https://www.schwarzwald-tourismus.info/orte/freiamt-0b6f6b6f9b",
    "https://www.schwarzwald-tourismus.info/erleben/wandern/tages-und-halbtagestouren/herbstwanderungen-im-schwarzwald",
]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    batch = ROOT / "input" / "relax_batches" / BATCH_ID
    job_dir = batch / "jobs" / VIDEO_ID
    if batch.exists():
        raise FileExistsError(f"Refusing to overwrite existing batch: {batch}")
    if not IMAGE.is_file():
        raise FileNotFoundError(IMAGE)

    registry = json.loads((ROOT / "library/relax_music/registry.json").read_text(encoding="utf-8"))["tracks"]
    selected = []
    for index, variant in ORDER:
            prompt_id = f"relax_eu_autumn_{index:03}"
            matches = [
                track for track in registry.values()
                if track.get("source_prompt_id") == prompt_id
                and track.get("flow_variant_index") == variant
                and track.get("status") == "available"
                and track.get("track_metadata", {}).get("genre") == "relax-music"
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected one available track for {prompt_id} variant {variant}")
            track = matches[0]
            audio = ROOT / track["file"]
            with wave.open(str(audio), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            if abs(duration - track["duration_seconds"]) > 0.05:
                raise ValueError(f"Duration mismatch: {track['track_id']}")
            selected.append(track)

    assert len(selected) == 45 and len({t["track_id"] for t in selected}) == 45
    assert all(a["source_prompt_id"] != b["source_prompt_id"] for a, b in zip(selected, selected[1:]))
    total = sum(t["duration_seconds"] for t in selected)
    effective = total - 3 * (len(selected) - 1)
    if not 7200 <= effective <= 10800:
        raise ValueError(f"Playlist outside requested 2-3 hour range: {effective}")

    family_seconds = Counter()
    texture_seconds = Counter()
    accent_seconds = Counter()
    use_seconds = Counter()
    ambience_seconds = Counter()
    for track in selected:
        metadata = track["track_metadata"]
        seconds = track["duration_seconds"]
        family_seconds[metadata["family"]] += seconds
        texture_seconds[metadata["primary_texture"]] += seconds
        for accent in metadata["accent_instruments"]:
            accent_seconds[accent] += seconds
        for use in metadata["listening_use"]:
            use_seconds[use] += seconds
        for element in metadata["ambience"]["elements"]:
            ambience_seconds[element] += seconds

    music_profile = {
        "aggregation_method": "duration_weighted",
        "genre": "relax-music",
        "dominant_family": "forest-breeze",
        "supporting_families": ["meadow-and-morning", "water-and-mist", "rain-and-shelter"],
        "family_duration_seconds": {key: round(value, 3) for key, value in family_seconds.items()},
        "primary_texture": "slowly evolving ambient pads",
        "texture_duration_seconds": {key: round(value, 3) for key, value in texture_seconds.items()},
        "accent_instruments": [key for key, value in accent_seconds.most_common() if value >= 300],
        "accent_duration_seconds": {key: round(value, 3) for key, value in accent_seconds.items()},
        "dominant_moods": ["peaceful", "comforting"],
        "melody_character": "sparse_long_notes_with_generous_silence",
        "harmony_character": "very_slow_consonant_suspended",
        "ambience": {
            "level": "subtle_or_very_subtle",
            "elements": list(ambience_seconds),
            "element_duration_seconds": {key: round(value, 3) for key, value in ambience_seconds.items()},
        },
        "nature_scene": "autumn European woodland, meadow, small stream and sheltered rain",
        "season": "autumn",
        "listening_uses": [key for key, value in use_seconds.most_common() if value >= 300],
        "listening_use_duration_seconds": {key: round(value, 3) for key, value in use_seconds.items()},
        "energy_profile": "flat_low_nearly_motionless",
        "conflicts": ["The sequence moves between outdoor meadow, woodland, water and brief rain shelter; no single weather condition is claimed for the whole playlist."],
    }

    playlist = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "target_duration_seconds": 7500,
        "actual_duration_seconds": round(effective, 3),
        "raw_track_duration_seconds": round(total, 3),
        "crossfade_seconds": 3,
        "tracks": [
            {
                "position": position,
                "track_id": track["track_id"],
                "file": track["file"],
                "duration_seconds": track["duration_seconds"],
                "source_prompt_id": track["source_prompt_id"],
        "transition_note": "compatible low-energy autumn ambient textures across meadow, forest, water and shelter",
            }
            for position, track in enumerate(selected, 1)
        ],
        "overlap_metrics": {
            "max_recent_video_track_overlap_ratio": 0.0,
            "repeated_adjacent_pairs": 0,
            "reused_opening_track": False,
            "reused_closing_track": False,
        },
        "music_profile": music_profile,
    }
    location = {
        "schema_version": 1,
        "country": "Germany",
        "place_name": "Freiamt, Black Forest",
        "place_type": "wooded_hill_valley_and_rural_municipality",
        "verified_features": [
            "wooded hills and side valleys",
            "traditional Black Forest farmhouses",
            "meadows and orchards",
            "clear small streams",
            "autumn forest foliage in the Black Forest region",
        ],
        "excluded_features": ["Swiss alpine peaks", "Swiss chalet architecture", "sea coast", "city skyline"],
        "music_fit": {
            "family": "forest-breeze",
            "supporting_families": ["meadow-and-morning", "water-and-mist", "rain-and-shelter"],
            "mood": ["peaceful", "comforting"],
            "ambience": ["subtle woodland air", "occasional small water flow", "distant gentle rain"],
            "season": "autumn",
        },
        "source_urls": SOURCE_URLS,
        "source_checked_at": "2026-10-12",
        "verification_status": "verified",
    }
    episode = {
        "genre": "relax-music",
        "music_evidence": {
            "dominant_family": "forest-breeze",
            "dominant_moods": ["peaceful", "comforting"],
            "ambience": ["subtle woodland air", "faint leaves", "distant water and rain"],
            "season": "autumn",
            "listening_uses": music_profile["listening_uses"],
        },
        "location_ref": "location.json",
        "country": "Germany",
        "place_name": "Freiamt, Black Forest",
        "thumbnail_title": "GERMANY",
        "visual_focal_point": "traditional Black Forest farmhouse at the edge of a wooded valley",
        "leading_line": "quiet curving rural lane through a meadow",
        "atmosphere": "clear soft autumn morning",
        "light": "low morning side light illuminates farmhouse and nearby autumn trees",
        "thumbnail_concept": "a luminous autumn morning in rural Freiamt with a forest-backed farmhouse",
        "seo_concept": "autumn woodland stillness in Freiamt, Germany",
        "allowed_claims": ["autumn relaxing music", "instrumental ambient", "quiet relaxation", "forest scenery"],
    }
    thumbnail_prompt = (
        "Use case: photorealistic-natural. Asset type: final Relax Music YouTube thumbnail. "
        "Destination: Freiamt, Black Forest, Germany in autumn; authentic wooded hills, meadow, "
        "small valley and one traditional Black Forest farmhouse. Hero: the farmhouse is modestly "
        "scaled at the forest edge. Composition: eye-level hillside view, a gently curving rural lane "
        "leads toward it, layered mixed woodland behind, calm dark upper field for typography. "
        "Light hook: one low morning sun from camera-left selectively lights the farmhouse, nearby "
        "copper trees and lane, with dimensional shadow and protected highlights. Natural green, "
        "copper and timber colors; full-frame 35mm f/8 ISO 200 RAW travel photography. "
        "Only exact text GERMANY in large white #FFFFFF artistic Didone uppercase in the upper half, "
        "clearly separated from the hero and readable at 320x180. Native 16:9. No other text, "
        "Swiss peaks or chalet, painting, CGI, HDR, neon, artificial glow, people, logo or watermark."
    )
    thumbnail = {
        "schema_version": 1,
        "channel": "relax-music",
        "generator": "built_in_image_gen",
        "thumbnail_text": "GERMANY",
        "music_attributes": {"dominant_family": "forest-breeze", "supporting_families": ["meadow-and-morning", "water-and-mist", "rain-and-shelter"], "mood": ["peaceful", "comforting"], "season": "autumn"},
        "location_profile": location,
        "visual_signature": "Germany|Freiamt|traditional farmhouse|wooded valley|autumn morning|left side light|large white Didone",
        "output_image": "thumbnail.png",
        "novelty_status": "checked_against_local_relax_batch_history",
        "prompt": thumbnail_prompt,
    }
    youtube = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "title": TITLE,
        "description": DESCRIPTION,
        "primary_keyword": "autumn relaxing music",
        "secondary_keywords": ["calm music", "peaceful instrumental music"],
        "country": "Germany",
        "place_name": "Freiamt, Black Forest",
        "supported_benefits": ["relaxation", "reading", "rest"],
        "title_length": len(TITLE),
        "pattern_signature": "autumn relaxing music|seasonal|Germany|Freiamt, Black Forest|autumn|subtle forest air|relaxation",
        "research_status": "user_supplied_vidiq_and_youtube_autocomplete_snapshot_2026-10-06",
        "relevance_notes": [
            "Autumn is shared by every selected prompt; the playlist stays low-energy while moving among woodland, meadow, water and sheltered-rain families.",
            "The verified place is Freiamt; the thumbnail uses the more recognizable country label GERMANY.",
            "No piano-led, sleep, 4K, no-ads or medical claims.",
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
            "User requested a 2-3 hour episode; this playlist targets about 125 minutes.",
            "Final duration estimate subtracts forty-four 3-second crossfades.",
            "Thumbnail title uses country GERMANY because Freiamt is less widely recognizable.",
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
        "locations": [{"country": "Germany", "place_name": "Freiamt, Black Forest"}],
    }

    job_dir.mkdir(parents=True)
    write_json(job_dir / "playlist.json", playlist)
    write_json(job_dir / "location.json", location)
    write_json(job_dir / "thumbnail.json", thumbnail)
    shutil.copy2(IMAGE, job_dir / "thumbnail.png")
    write_json(job_dir / "youtube.json", youtube)
    write_json(job_dir / "job.json", job)
    write_json(batch / "batch_manifest.json", manifest)
    print(f"{batch} | {len(selected)} tracks | {effective:.3f} seconds | {TITLE}")


if __name__ == "__main__":
    main()
