# Library build and registry model

## Planned Flow batch

Store a library build under `input/library_builds/<build_id>/`:

```text
input/library_builds/<build_id>/
├── build_manifest.json
├── family_visuals.json
├── flow_prompts.json
└── visual_references/
    ├── family_visual_01.png
    └── ...
```

## Family visual record

Create these before compiling Flow prompts:

```json
{
  "visual_reference_id": "family_visual_01",
  "asset_role": "music_reference",
  "music_family": "warm-waterfront-acoustic-trio",
  "image": "visual_references/family_visual_01.png",
  "source_attributes": {
    "mood_branch": "late-night",
    "mood": ["reflective", "comforting"],
    "ambience": ["distant-harbor-water"],
    "brightness": "low"
  },
  "concept_history_policy": "excluded"
}
```

One visual per family is the default. A second reference is allowed when the family contains more than roughly 12–16 tracks or has two clearly different mood clusters.

Example prompt record:

```json
{
  "prompt_id": "flow_prompt_001",
  "music_family": "warm-waterfront-acoustic-trio",
  "outputs_per_prompt": 2,
  "visual_reference_id": "family_visual_01",
  "visual_reference_path": "visual_references/family_visual_01.png",
  "track_metadata": {
    "genre": "vintage-jazz",
    "mood_branch": "late-night",
    "family": "acoustic-trio",
    "bpm": 52,
    "mood": ["reflective", "comforting"],
    "ambience": ["distant-harbor-water"],
    "energy_profile": "flat-low-restrained"
  },
  "flow_prompt": "...",
  "status": "pending_generation"
}
```

One prompt record is one generation request and always produces two tracks. It is not itself a track record.

Automation status lifecycle:

```text
pending_generation → in_progress → generated → completed
```

- `in_progress`: prompt and image are being submitted or Flow is generating; do not automatically resubmit after an interrupted run.
- `generated`: exactly two `/song/...` links have been saved and WAV download can resume safely.
- `completed`: both WAV files have been saved and `outputs` contains their file records.

The build manifest uses the fixed two-track Flow behavior:

```json
{
  "schema_version": 1,
  "build_id": "music_build_YYYYMMDD_HHMMSS",
  "requested_track_count": 100,
  "outputs_per_prompt": 2,
  "required_prompt_count": 50,
  "expected_track_count": 100,
  "surplus_track_count": 0,
  "status": "planned"
}
```

Use `required_prompt_count = ceil(requested_track_count / 2)`. For an odd request, `expected_track_count` is one greater than requested and `surplus_track_count` is 1. Do not add a quality-review buffer.

## Registered audio track

After Flow output exists, create one registry record per real file:

```json
{
  "track_id": "track_0001",
  "file": "library/music/tracks/track_0001.wav",
  "source_prompt_id": "flow_prompt_001",
  "source_visual_reference_id": "family_visual_01",
  "flow_variant_index": 1,
  "format": "wav",
  "duration_seconds": 183.4,
  "checksum_sha256": null,
  "status": "available",
  "track_metadata": {
    "mood_branch": "late-night",
    "family": "acoustic-trio",
    "lead_instrument": "piano",
    "mood": ["reflective", "comforting"],
    "energy_profile": "flat-low-restrained",
    "brightness": "low",
    "ambience": ["distant-harbor-water"]
  },
  "usage_count": 0,
  "used_in": [],
  "last_used": null
}
```

Prefer WAV masters. If Flow only supplies M4A, preserve the source M4A instead of transcoding it to WAV. MP3 is a fallback, not the preferred master.

Both outputs inherit the same `track_metadata` from their source prompt and differ by `track_id`, file facts and `flow_variant_index`. Playlist selection uses `track_metadata` and `status: available`. No subjective audio-quality review is required.
