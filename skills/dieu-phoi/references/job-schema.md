# Episode packaging schema

The orchestrator writes packages under:

```text
input/
└── batches/
    └── <batch_id>/
        ├── batch_manifest.json
        └── jobs/
            └── <video_id>/
                ├── job.json
                ├── playlist.json
                ├── thumbnail.json
                ├── thumbnail.png
                └── youtube.json
```

Do not overwrite `input/current_job`. Paths inside a batch use the batch directory as their base.

## `playlist.json`

```json
{
  "schema_version": 2,
  "target_duration_seconds": 3600,
  "actual_duration_seconds": 3618.4,
  "tracks": [
    {
      "position": 1,
      "track_id": "track_0001",
      "file": "library/music/tracks/track_0001.wav",
      "duration_seconds": 183.4,
      "source_visual_reference_id": "family_visual_01",
      "transition_note": "warm acoustic opening"
    }
  ],
  "overlap_metrics": {
    "max_recent_video_track_overlap_ratio": 0.24,
    "repeated_adjacent_pairs": 0,
    "reused_opening_track": false,
    "reused_closing_track": false
  },
  "playlist_profile": {
    "aggregation_method": "duration_weighted",
    "dominant_branch": "late-night",
    "dominant_family": "acoustic-trio",
    "supporting_families": ["vibraphone"],
    "dominant_moods": ["reflective", "comforting"],
    "register": "low-to-middle",
    "brightness": "low",
    "energy_profile": "flat-low-restrained",
    "ambience": ["distant-harbor-water"],
    "dominant_visual_reference_ids": ["family_visual_01"],
    "conflicts": []
  }
}
```

Only real registry tracks with `status: available` may appear here. No subjective music-quality review is required. Track order is final input for the audio builder.

## `job.json`

```json
{
  "schema_version": 2,
  "batch_id": "batch_YYYYMMDD_HHMMSS",
  "video_id": "video_001",
  "status": "ready_for_pipeline",
  "episode_profile": {
    "genre": "vintage-jazz",
    "mood_branch": "late-night",
    "evidence": {
      "dominant_family": "acoustic-trio",
      "dominant_moods": ["reflective", "comforting"],
      "ambience": ["distant-harbor-water"]
    },
    "emotional_premise": "quiet reflection after many years at sea",
    "time_anchor": "after midnight",
    "maritime_anchor": "calm harbor water beyond the old seawall",
    "location": "quiet harbor edge",
    "weather": "thin sea mist",
    "micro_story": "an old sailor watches the last boats return",
    "character_situation": "seated alone on a sheltered seawall",
    "prop_logic": ["small harbor lantern beside the stone wall"],
    "visual_direction": "aged imperfect vintage print",
    "seo_hook_type": "scene"
  },
  "files": {
    "playlist": "playlist.json",
    "thumbnail_spec": "thumbnail.json",
    "thumbnail_image": "thumbnail.png",
    "youtube_metadata": "youtube.json"
  },
  "consistency_check": {
    "status": "passed",
    "playlist_supports_episode_profile": true,
    "thumbnail_matches_profile": true,
    "youtube_metadata_matches_profile": true,
    "issues": []
  },
  "assumptions": []
}
```

## `thumbnail.json`

Contains the `$tao-anh-bia` result, shared episode-profile fields, the Popeye1 character-reference path, generated image path, prop-context result and novelty status. No style-reference image path is allowed.

## `youtube.json`

Contains the `$seo-youtube` result, lowercase title, keywords, time and maritime anchors, pattern signature, SEO research status and playlist-supported claims.

## `batch_manifest.json`

Write this file last:

```json
{
  "schema_version": 2,
  "batch_id": "batch_YYYYMMDD_HHMMSS",
  "requested_video_count": 3,
  "created_at": "ISO-8601 timestamp",
  "path_base": "batch_directory",
  "jobs": [
    {
      "video_id": "video_001",
      "path": "jobs/video_001/job.json",
      "status": "ready_for_pipeline"
    }
  ],
  "summary": {
    "ready_for_pipeline": 3,
    "library_gap": 0,
    "needs_attention": 0
  }
}
```

If the library is insufficient, report gaps without fabricating jobs or tracks. All JSON must parse successfully.
