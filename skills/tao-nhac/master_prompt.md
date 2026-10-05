# Canonical Master DNA — Vintage Jazz

Use this as the invariant source for every generated track. Vintage Jazz is the permanent genre. Select either the default `late-night` branch or the conditional `noir` branch, then insert a track-specific instrument palette, micro-scene, melodic character, harmonic emphasis, and ambience level. Do not blindly duplicate the full text across a batch.

## Core prompt

```text
Slow vintage jazz, 50–54 BPM, with an intimate mid-century late-night character.

A quiet mid-century setting after midnight: [TRACK-SPECIFIC SCENE]. The world feels old, lived-in and connected to a weathered sailor's memories. A waterfront bar, whiskey, harbor or ocean ambience may appear only when natural to this track's scene.

[BRANCH EMOTION: for late-night, warm, mellow, intimate, reflective, nostalgic, weathered, slightly bittersweet but comforting, never tense; for noir, smoky, shadowed, mysterious and restrained with mild harmonic tension, never aggressive, tragic or frightening.]

Slow unhurried rhythm, simple memorable melodies, [BRANCH-APPROPRIATE HARMONY], spacious phrasing, generous pauses, and restrained improvisation.

Use a minimal acoustic or vintage electric jazz ensemble selected for this individual composition. Do not overcrowd the arrangement.

KEEP THE ENTIRE TRACK IN A LOW-TO-MIDDLE REGISTER FROM BEGINNING TO END.
NEVER RISE INTO A HIGH REGISTER.
NEVER INCREASE THE PITCH RANGE AS THE TRACK PROGRESSES.

Maintain a flat, restrained energy curve throughout. The second half must not become higher, louder, brighter, busier, or more emotional than the first half. The ending must remain as low, soft, slow, and restrained as the opening.

BEGIN LOW. STAY LOW. END LOW.
BEGIN QUIET. STAY QUIET. END QUIET.

No build-up, no crescendo, no dramatic climax, no soaring melody, no high notes, no aggressive solos, no virtuosic runs, and no busy instrumentation.

Use only subtle environmental ambience that naturally belongs to the selected scene. Maritime elements may include distant gentle waves, quiet harbor water, faint sea breeze or occasional dock creaks, but they are optional and must never dominate the music.

MUSIC FIRST. SCENE SECOND. AMBIENCE THIRD.

Natural intimate vintage recording, warm analog character, rich low-mids, and smooth soft highs.

Instrumental only.

The feeling: an old memory returning slowly after midnight, with nowhere to hurry and nothing to prove.

No hurry. No drama. No destination.
```

## Compilation notes

- Every Flow submission consists of one compiled music prompt plus the shared static reference image at `skills/tao-anh-bia/assets/old-print-style-reference.png`, unless the caller explicitly supplies another image.
- The image provides only a stable vintage visual cue. The text prompt remains authoritative for instrumentation, harmony, register, energy, branch, mood, ambience and scene.
- Use a precise BPM within 50–54 for each track rather than leaving a range when Flow responds better to a single value.
- Always identify the track as Vintage Jazz. Use `late-night` by default; use `noir` only when explicitly selected.
- Replace the bracketed scene, emotion and harmony fields with one concrete branch-specific direction; never leave brackets in a final Flow prompt.
- Add only the selected ensemble. Omit saxophone entirely unless the track is intentionally sax-led.
- Select a few relevant ambience elements; do not stack every maritime sound into every prompt.
- Preserve the explicit low-register and flat-energy block because brief negative wording alone has not reliably prevented Flow from building toward a climax.
- Keep scene language concise. The scene should guide atmosphere, not force instruments to imitate the ocean.
- For the `late-night` branch, keep harmony warm and comforting and omit noir/detective vocabulary.
- For the `noir` branch, allow restrained darker harmony but keep the same flat energy, low register and lack of climax.
