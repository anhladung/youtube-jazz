---
name: tao-nhac
description: Xây thư viện Vintage Jazz theo batch bằng prompt Google Flow Music và metadata cho từng music family. Flow luôn tạo đúng hai track cho mỗi prompt; sau khi tải về, hai file được đăng ký riêng để skill điều phối sử dụng.
---

# Vintage Jazz Music

Create Flow-ready instrumental jazz prompts from the canonical DNA in [master_prompt.md](master_prompt.md). Preserve the identity while varying each track deliberately.

## Channel hierarchy

- `vintage-jazz` là genre và sonic identity bắt buộc của toàn bộ library.
- `late-night` là branch mặc định: chậm, ấm, intimate, reflective và comforting.
- `noir` là branch có điều kiện: tối hơn, nhiều sương và tension hơn nhưng vẫn restrained, low-register và không cinematic climax.
- `Whiskey at Night` là một concept/scene family quan trọng trong branch `late-night`, không phải genre duy nhất của channel.

Mỗi track phải có `genre: vintage-jazz` và một `mood_branch` rõ ràng. Không trộn noir vocabulary vào track late-night chỉ để tạo cảm giác khác biệt.

## Responsibilities

- Produce a track specification, a focused English prompt for Google Flow Music, and metadata for the library registry.
- For batches, plan variation across the batch before writing individual prompts.
- Treat any registry records or collision summary supplied by the pipeline as authoritative context for novelty.
- Never claim to have checked prior tracks unless their metadata was supplied in the current request.
- Support a library-build request such as “tạo kế hoạch 100 bài”, using the invariant that every Flow prompt creates exactly two tracks.
- Keep one prompt record during planning, then create two real track records only after the two audio files have been downloaded.

Do not read novelty from chat history or conversational memory. Do not update `registry.json` or history files unless the caller explicitly asks for that separate pipeline operation. The pipeline owns persistence, collision scoring, IDs, usage counts, and acceptance/rejection.

## Two-stage library model

### Stage A — plan Flow prompts

- Allocate the requested tracks across meaningful `music_family` groups before writing prompts.
- Lock metadata for every music family before writing individual prompts.
- Do not generate a separate image for each music family. Reuse the project-wide static Flow reference at `skills/tao-anh-bia/assets/old-print-style-reference.png` for every prompt unless the caller explicitly supplies another image.
- A library build may keep previously generated family images under `input/library_builds/<build_id>/visual_references/`, but they are archival and must not be selected automatically.
- `outputs_per_prompt` is permanently `2`; do not infer it from prompt wording and do not expose it as a creative option.
- Calculate `required_prompt_count = ceil(requested_track_count / 2)`. Thus 100 tracks require exactly 50 prompts. An odd target produces one declared surplus track.
- Give every prompt a `prompt_id`, family metadata, the shared `visual_reference_id` and `visual_reference_path`, and `outputs_per_prompt: 2`.
- Do not create two fake track records from one prompt before files actually exist.

### Stage B — ingest rendered tracks

After the user or code runs Flow and downloads audio, register both files separately with their own `track_id`, path, format, duration, checksum when available, `source_prompt_id` and `flow_variant_index` 1 or 2.

Copy the prompt's music-family metadata and visual-reference identity to both track records. No listening review, quality score or subjective acceptance gate is required. A file becomes `status: available` after minimal technical ingestion confirms that it exists and its duration can be read.

Read [references/library-build-schema.md](references/library-build-schema.md) whenever planning a library batch or registering Flow outputs.

## Inputs

Use what the caller provides. Reasonable defaults are allowed for omitted creative fields.

- Track count or a single-track request
- Optional family, instruments, micro-scene, BPM, or mood
- Optional mood branch: `late-night` mặc định hoặc `noir` khi caller yêu cầu
- Optional `track_id` assigned by the pipeline
- Optional registry records or compact novelty constraints such as recently used signatures and disallowed combinations
- Optional target music-family distribution for a library build

If no novelty context is supplied, create internal diversity within the requested batch. Use `batch_only` for a batch and `not_checked` for a single track.

This skill creates reusable music, not video-specific stories. Keep scene metadata broad enough that tracks can support several compatible episodes later.

## Composition workflow

1. Select a micro-scene inside the same vintage sailor-jazz world: an old waterfront bar, closing tavern, ship cabin, harbor room, foggy night interior, fireplace corner, or another historically coherent setting.
2. Choose one restrained ensemble. Do not fill every track with a standard jazz lineup.
3. Set 50–54 BPM unless the caller explicitly chooses another tempo compatible with the concept.
4. Vary lead voice, support palette, melodic behavior, harmonic emphasis, ambience amount, and scene detail without leaving Vintage Jazz or confusing the selected branch.
5. Compile the final prompt from the canonical DNA plus the track-specific variation and hard energy constraints.
6. Return structured metadata and a normalized `variation_signature` so the pipeline can detect collisions deterministically.

## Instrument decisions

- Never add saxophone automatically.
- If saxophone is requested, classify the track as `sax-led`; Flow may make saxophone dominant even when described as sparse.
- Prefer small ensembles using only instruments that serve the composition.
- Useful families include `rhodes-trio`, `acoustic-trio`, `vibraphone`, `bass-forward`, and explicitly requested `sax-led`. These are options, not a closed taxonomy.
- Do not solve saxophone repetition by making every other track piano-led.
- Let upright bass have gentle musical presence. Keep brushes extremely soft and avoid energetic fills.
- Jazz instruments should play naturally; do not ask them to imitate waves or other maritime motion.

## Musical invariants

- Instrumental only.
- Vintage Jazz throughout: acoustic or period-appropriate vintage electric palette, natural ensemble interaction, analog recording character and no modern glossy production.
- Warm, mellow, intimate, reflective, mature, nostalgic, weathered, unhurried, slightly bittersweet but comforting.
- Low-to-middle register from beginning to end.
- Flat, restrained energy throughout; the second half and ending must not become higher, louder, brighter, busier, or more emotional than the opening.
- Simple memorable melody, small intervals, spacious phrasing, generous pauses, and restrained improvisation.
- Favor warm major 7th, minor 7th, major 9th, 6/9, and gentle dominant colors. Avoid sustained noir tension, excessive chromaticism, and heavy diminished harmony.
- Environmental ambience remains distant and secondary. Human intimacy and musical quality remain primary.
- Natural intimate vintage recording, warm analog character, rich low-mids, and smooth soft highs.

Avoid build-ups, crescendos, climaxes, soaring melodies, high-register peaks, aggressive or virtuosic solos, busy arrangements, punchy drums, storm sounds, loud waves, seagulls, and pirate or sea-shanty cues. In the `late-night` branch, also avoid dark/depressing/noir language; in the `noir` branch, use dark vocabulary sparingly and never imply despair or danger-driven action.

## Branch behavior

### `late-night` — default

- Keep the current warm, mellow, intimate and comforting DNA.
- Favor major 7th, minor 7th, major 9th, 6/9 and gentle dominant colors.
- Suitable scenes include whiskey bar, closing tavern, quiet room, fireplace, harbor window and peaceful night waterfront.
- Noir, detective, danger, suspense and heavy chromatic language are prohibited.

### `noir` — conditional

- Use only when the caller or video concept explicitly selects Jazz Noir.
- Allow darker minor harmony, restrained chromatic color, muted trumpet or intentional low sax-led instrumentation when suitable.
- Preserve 50–54 BPM, flat energy, low-to-middle register and listening comfort.
- Darker does not mean aggressive, tragic, cinematic, high-energy or climax-driven.

## Era compatibility

- If the requested music family names the 1940s or 1950s, use period-compatible acoustic instrumentation; do not use Fender Rhodes.
- Fender Rhodes belongs to a later vintage setting, roughly late 1960s–1970s, or to titles that use a non-calendar time anchor such as `after midnight`.
- Do not claim a precise historical year when the selected instrument family conflicts with it.

## Variation and collision interface

For each track, create this normalized signature:

```text
genre|mood_branch|family|bpm_bucket|lead_instrument|supporting_instruments_sorted|mood_pair|melody_character|harmony_emphasis|ambience_level|micro_scene_key
```

Compare against supplied registry context only. Avoid exact signature matches and overly close combinations identified by the caller. Within a batch, do not repeat the same lead/support combination and micro-scene unless explicitly requested.

Novelty metadata must be one of:

- `checked`: compared with registry data supplied by the caller;
- `batch_only`: checked only against other tracks in this generated batch;
- `not_checked`: a single track with no prior-track context.

## Output contract

Return one object per track in JSON-compatible form:

```yaml
track_id: null
title_concept: "Last Glass by the Window"
genre: vintage-jazz
mood_branch: late-night
family: rhodes-trio
bpm: 52
lead_instrument: fender_rhodes
supporting_instruments:
  - upright_bass
  - brushed_drums
mood:
  - reflective
  - comforting
melody_character: sparse_descending_small_intervals
harmony_character: warm_major_7_minor_7
ambience:
  level: very_subtle
  elements:
    - distant_gentle_waves
scene: nearly_empty_waterfront_bar_window_after_midnight
energy_profile: flat_low_restrained
variation_signature: vintage-jazz|late-night|rhodes-trio|50-54|fender_rhodes|brushed_drums+upright_bass|comforting+reflective|sparse_descending_small_intervals|warm_major_7_minor_7|very_subtle|waterfront_bar_window
novelty_check: batch_only
generation_tool: google_flow_music
prompt: "..."
```

Keep the Flow prompt focused and ordered as: style/BPM, ensemble, melody/harmony, register/energy constraints, scene, ambience, emotional target, negatives. Do not include metadata syntax inside the prompt.

When generating a batch, also give a short batch summary of family counts and metadata collision risks. Both Flow outputs inherit the prompt metadata automatically after their files are ingested.

For library builds, wrap prompts in a build manifest with:

- requested track count;
- fixed outputs per prompt: 2;
- required prompt count;
- family allocation;
- one shared static `music-reference` record for the build;
- prompt records;
- expected track count;
- surplus or shortfall;
- status `planned`; generated files later become `available` when ingested.
