"""Compile a reviewed Relax Music prompt plan into a Flow queue."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


HEADING = re.compile(r"^### (\d{2}) · (.+)$", re.MULTILINE)
METADATA = re.compile(r"^`prompt_id: ([^`]+)` · (.+)$", re.MULTILINE)
FLOW_PROMPT = re.compile(r"^\*\*Flow prompt:\*\* (.+)$", re.MULTILINE)


def read_records(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    headings = list(HEADING.finditer(text))
    records = []
    for index, heading in enumerate(headings):
        section = text[heading.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)]
        metadata_match = METADATA.search(section)
        prompt_match = FLOW_PROMPT.search(section)
        if not metadata_match or not prompt_match:
            raise ValueError(f"Missing metadata or Flow prompt in section {heading.group(1)}")
        metadata = dict(re.findall(r"`([^:]+): ([^`]+)`", metadata_match.group(0)))
        required = {"family", "tempo_bpm", "primary_texture", "accents", "nature_scene", "ambience", "use", "signature"}
        if missing := required - metadata.keys():
            raise ValueError(f"Missing metadata in section {heading.group(1)}: {sorted(missing)}")
        prompt_id = metadata_match.group(1)
        if prompt_id != f"relax_eu_autumn_{int(heading.group(1)):03d}":
            raise ValueError(f"Prompt ID does not match section {heading.group(1)}: {prompt_id}")
        ambience = metadata["ambience"]
        ambience_level = "very_subtle" if ambience.startswith("very_subtle_") else "subtle"
        records.append({
            "prompt_id": prompt_id,
            "music_family": f"autumn-{metadata['family']}",
            "outputs_per_prompt": 2,
            "track_metadata": {
                "title_concept": heading.group(2).strip(),
                "genre": "relax-music",
                "mood_branch": "dreamy-nature",
                "family": metadata["family"],
                "tempo_bpm": int(metadata["tempo_bpm"]),
                "primary_texture": metadata["primary_texture"],
                "accent_instruments": [value.strip() for value in metadata["accents"].split(",")],
                "mood": ["peaceful", "comforting"],
                "melody_character": "sparse_long_notes_with_generous_silence",
                "harmony_character": "very_slow_consonant_suspended",
                "ambience": {"level": ambience_level, "elements": [ambience]},
                "nature_scene": metadata["nature_scene"],
                "season": "autumn",
                "listening_use": [metadata["use"]],
                "energy_profile": "flat_low_nearly_motionless",
                "variation_signature": f"relax-music|dreamy-nature|{metadata['signature']}|autumn",
                "novelty_check": "batch_only",
                "generation_tool": "google_flow_music",
            },
            "flow_prompt": prompt_match.group(1).strip(),
            "status": "planned",
            "outputs": [],
        })
    if len(records) != 50 or len({item["prompt_id"] for item in records}) != 50:
        raise ValueError(f"Expected 50 unique prompt records, found {len(records)}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("build_dir", type=Path)
    args = parser.parse_args()
    records = read_records(args.plan)
    args.build_dir.mkdir(parents=True, exist_ok=True)
    build_id = args.build_dir.name
    queue = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "build_id": build_id,
        "request_interpretation": "50 Flow prompts requested; each prompt produces exactly two Relax Music tracks",
        "prompts": records,
    }
    counts = Counter(item["track_metadata"]["family"] for item in records)
    manifest = {
        "schema_version": 1,
        "channel_id": "relax_music",
        "build_id": build_id,
        "requested_prompt_count": 50,
        "requested_track_count": 100,
        "outputs_per_prompt": 2,
        "required_prompt_count": 50,
        "expected_track_count": 100,
        "surplus_track_count": 0,
        "mood_branch": "dreamy-nature",
        "season": "autumn",
        "family_allocation": dict(sorted(counts.items())),
        "novelty_check": "batch_only",
        "status": "planned",
    }
    for filename, payload in (("flow_prompts.json", queue), ("build_manifest.json", manifest)):
        (args.build_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compiled {len(records)} prompts into {args.build_dir}")


if __name__ == "__main__":
    main()
