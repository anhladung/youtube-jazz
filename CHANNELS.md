# Two-channel workspace

The code in `pipeline/` is shared. Stateful files are selected through an
explicit channel profile in `config.yaml`.

| Channel argument | Music registry | Production batches | Runtime data |
| --- | --- | --- | --- |
| `vintage-jazz` | `library/music/registry.json` | `input/batches` | `data` |
| `relax-music` | `library/relax_music/registry.json` | `input/relax_batches` | `data/relax_music` |

Vintage Jazz remains the default so existing IDE run configurations continue
to work. For Relax Music, always add `--channel relax-music`:

```powershell
python run_pipeline.py flow-queue --channel relax-music
python run_pipeline.py music-ingest path\to\flow_prompts.json --channel relax-music
python run_video_pipeline.py --channel relax-music
python build_youtube_schedule.py --channel relax-music
python run_youtube_uploader.py --channel relax-music
python run_livestream.py --channel relax-music --dry-run
```

Artifacts created by new batches should include a top-level field:

```json
{"channel_id": "relax_music"}
```

The runners reject an explicitly labelled artifact from the other channel.
For backward compatibility, an unlabelled artifact is accepted only when it is
physically inside the selected channel's own batch root. New packages should
always include `channel_id`.

## YouTube safety lock

Relax Music upload is disabled by default. Add a machine-local override to
`config.local.yaml` with a dedicated Chrome profile and the exact Studio channel
URL, then set `enabled: true`. Never reuse the Vintage Jazz browser profile.

```yaml
channels:
  relax_music:
    overrides:
      youtube:
        enabled: true
        profile_dir: "C:\\youtube_relax_profile"
        channel_url: "https://studio.youtube.com/channel/REPLACE_WITH_RELAX_CHANNEL_ID"
```
