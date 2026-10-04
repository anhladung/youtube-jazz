# Master Prompt — Vintage Jazz Episode Packaging

Package N Popeye Vintage Jazz episodes from real, available tracks already present in `youtube_music_pipeline`.

## Permanent channel identity

- Main genre: Vintage Jazz.
- Default branch: Late Night Jazz.
- Conditional branch: Jazz Noir.
- Character world: an old, calm, weathered sailor in a vintage illustrated universe.
- Maritime identity: present in every episode, directly or indirectly.
- Emotional range: reflective, nostalgic, mature, slightly bittersweet and comforting.

## Direction of truth

```text
available audio + prompt-derived track metadata
→ locked playlist
→ duration-weighted playlist profile
→ episode profile
→ thumbnail
→ lowercase YouTube title and short description
```

Do not invent an episode first and force library tracks into it. Use the metadata assigned by each source prompt; no subjective listening review is required.

## Required sequence

1. Inspect config, registry and completed history.
2. Validate real files, readable durations, available status and track metadata.
3. Build all N playlists together, balancing coherence, reuse, overlap and usage counts.
4. Lock track order and calculate a duration-weighted profile for every playlist.
5. Derive a compatible episode profile from each playlist.
6. Validate branch, era/instrument, time, maritime and prop logic.
7. Create the final thumbnail from the locked episode profile.
8. Create lowercase SEO title and short description from the same profile and playlist evidence.
9. Run cross-consistency validation and write job packages.

If the library cannot support N sufficiently distinct and coherent episodes, return a structured `library_gap`. State the missing families, moods, instrumentation or duration. Do not generate Flow prompts during episode packaging; the user can run a separate `$tao-nhac` library-build request.

Stop after producing validated pipeline inputs. Do not operate Google Flow Music, concatenate audio, render video or upload to YouTube.
