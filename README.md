English | [한국어](README.ko.md) | [日本語](README.ja.md)

# MR Studio

YouTube URL or your own audio file → remove vocals · adjust key (-5 to +5 semitones) → export as an instrumental (MR) track.

## Run

Double-click `run.bat` → the app opens in your browser (http://127.0.0.1:7860)

## Features

Flow: ① load audio → ② set parts & key → ③ **preview** → ④ **create (export)**  
Once audio is loaded, the preview auto-refreshes every time you change a part or the key (only the first separation of a new song takes 1-2 minutes).

- **Import**: a YouTube URL, or your own audio file (mp3/wav/flac, etc.). If a file is provided, the file takes priority.
- **Parts to keep**: toggle main vocal / chorus / drums / bass / guitar / piano / wind instruments / other instruments on/off individually.
  - Default = main vocal off only → MR that keeps the chorus
  - All on → no separation, just pitch-shifts the original track
  - Wind instruments (for orchestral use): trumpet, horn, trombone, sax, flute, etc. are separated **as one group** — there's no model that isolates trumpet alone.
    The wind-instrument separation step only runs (adding tens of seconds on first processing) when wind or "other instruments" is turned off.
- **Key adjustment**: -5 to +5 semitones (tempo preserved, via rubberband)
- **Create (export)**: exports exactly what you heard in the preview as mp3 (320k) or wav → also saved to the `output/` folder

Once a song has been separated, it's cached in `cache/`, so re-creating it with just different parts/key takes only a few seconds.

## Architecture

- Separation stage 1: Demucs `htdemucs_6s` → vocal / drums / bass / guitar / piano / other
- Separation stage 2: Mel-Roformer Karaoke → splits vocal into main vocal / chorus
- (when wind instruments are toggled) Separation stage 0: UVR `17_HP-Wind_Inst` → wind instruments / rest, then rest goes through stages 1-2
- Mix (numpy) → key shift + limiter + encode (ffmpeg)
- UI: Gradio (a v2.0 web version can extend the same app by hosting it on a server)

## Limitations

- **Amazon Music is not supported**: it's a DRM-protected stream and can't be extracted. Use a purchased/owned audio file via Import instead.
- Use YouTube-sourced audio for personal practice only (copyright).

## Setting up on a new PC

```bat
winget install --id Gyan.FFmpeg --exact
winget install --id yt-dlp.yt-dlp --exact
winget install --id DenoLand.Deno --exact
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

An NVIDIA GPU is recommended (CPU-only takes several minutes per song). On first run, the separation models (~0.9GB) are auto-downloaded to `models/`.

## Test

`.venv\Scripts\python test_app.py` → `OK`

## Made by

[Perch Creative](https://perch-creative.com) — websites · branding · custom tools
