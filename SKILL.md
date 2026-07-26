---
name: 5am
description: Reference for the `5am` CLI — the command-line client for the 5AM app. Use when the user asks to upload/download/organize media, manage albums, generate AI media (image/video/music/audio), generate Veo video clips, concatenate/join video clips, build a memory collage / photo-montage / slideshow video (Ken Burns + crossfades, optional Lyria music), render a podcast WAV into a video (waveform overlay OR Veo b-roll with the episode audio), mix a voice track over background music with automatic ducking (broadcast-style bed staging + EQ pocket), create or chat with AI characters, manage character webhooks, run multi-character orchestration in the Playground, or do anything via the `5am` binary. Trigger on phrases like "upload to 5am", "5am album", "5am character", "list my albums", "generate an image with 5am", "generate a video with 5am", "veo video", "concatenate video clips", "join veo clips", "veo video with podcast audio", "memory collage", "photo montage video", "slideshow video", "ken burns", "collage with music", "5am chat", "5am webhook", "5am playground", "orchestrator", "multi-agent task", "wrap audio as video", "render waveform", "podcast to mp4", "duck music", "audio ducking", "music bed under narration", "mix voice over music".
when_to_use: User mentions the `5am` CLI, the 5AM Media Hub, 5am.app, or wants to perform any media-hub action from the terminal. Also invoke when the user pastes a `5am ...` command and asks for help, or asks to script against the hub.
---

# 5am CLI Reference

The `5am` binary is a CLI for the 5AM Media Hub (`https://5am.app`). It is **JSON-by-default** on stdout and **agent-optimized** — pipe to `jq`, check exit codes, no interactive prompts unless explicitly invoked.

## Operating principles

- **stdout = JSON, stderr = progress/footers.** Always pipe stdout to `jq` when consuming output. Never grep stderr for results.
- **Exit codes are meaningful** — branch on them: `0` ok, `1` generic, `2` auth (401/403/missing token), `3` validation (4xx), `4` network/timeout, `5` server (5xx), `6` CLI version below the supported floor (run `5am update`).
- **Auth is required for almost every command.** If `5am whoami` fails with exit 2, run `5am login` (or set `5AM_TOKEN`) before anything else.
- **Pass `--yes` for destructive ops in scripts.** Without it, `delete` commands prompt.
- **Use `--pretty` only for human display.** Never parse `--pretty` output.
- **Use `--json` on `chat` to get structured tool-call / media-URL data.** Default chat mode prints text to stdout and footers to stderr.

## Install (if the binary is missing)

Install or upgrade the `5am` CLI on macOS and Linux with a single command:

```sh
curl -fsSL https://cli.5am.app/cli/latest/install.sh | sh
```

For Windows:

```powershell
Invoke-WebRequest https://cli.5am.app/cli/latest/5am-windows-amd64.exe -OutFile 5am.exe
./5am.exe --version
```

Release manifest (sizes + sha256 hashes): `https://cli.5am.app/cli/latest/manifest.json`.

## Setup & auth

```sh
5am --version                          # confirm build (dev/staging/prod baked-in BASE_URL)
5am login                              # paste personal access token at prompt
5am login --token <TOKEN>              # non-interactive
5am whoami                             # verify; exit 2 if no/bad token
```

Token sources (in precedence order):
1. `--token` flag on `login`
2. `5AM_TOKEN` env var
3. Stored credential from `5am login`


Mint tokens in the web UI: **Settings → CLI Access Tokens → Generate token**. Scopes are `read`, `write`, `admin`. Token is shown once.

## Account

```sh
5am account                            # JSON: storage, plan, subscription
5am account --pretty                   # human summary
```

## Albums

```sh
5am albums list                                    # albums OWNED by the user — JSON array
5am albums list-shared                             # albums shared WITH the user by others (with price, payment status, access)
5am albums get <albumId>
5am albums create --name "Trip 2026" --description "..."
5am albums update <albumId> --name "..." --description "..."
5am albums delete <albumId> --yes                  # cascades to media; --yes required in scripts
```

**`list` vs `list-shared`** — they're distinct endpoints, not a flag on one
command. `list` returns owned-only; `list-shared` returns the albums others
have shared with the user, with extra fields (`sharePrice`, `shareCurrency`,
`sharePaymentStatus`, `shareAccessControl`). Pick by intent. The shared
endpoint is **slower** (server-side Stripe payment-status reconciliation
per pending share) — don't poll it tightly. To get the user's complete
album set, call both and merge client-side.

### Sharing an album (owner-only)

Owners can grant other users access — free or paid, read-only or contributor —
and can optionally publish a public link. All sharing commands require the
caller to own the album; the backend returns 403 otherwise. Direct shares
trigger an email notification to the recipient.

```sh
# `--share` is repeatable. Format: 'email[:price[:access]]'.
# access is 'read' (default) or 'read_and_write'. Empty/zero price = free.
5am albums share <albumId> --share alice@example.com                       # free, read-only
5am albums share <albumId> --share bob@example.com:9.99                    # $9.99, read-only
5am albums share <albumId> --share carol@example.com:0:read_and_write      # free contributor
5am albums share <albumId> \
  --share dan@example.com:19.99:read_and_write \
  --share eve@example.com                                                   # mix free + paid

# Batch from JSON file (or '-' for stdin). Mutually exclusive with --share.
# File shape: [{email, price?, currency?, access_control?}, ...]
5am albums share <albumId> --shares-file ./shares.json
cat shares.json | 5am albums share <albumId> --shares-file -

# View all shares: direct + pending email invites + public link token
5am albums shares <albumId>

# Revoke
5am albums unshare <albumId> --user <email> --yes              # revoke a share (direct or pending)

# Public link — separate subcommands. Returns publicShareToken; usable as
# https://5am.app/album/<id>?shareToken=<token>
5am albums public-link enable <albumId>
5am albums public-link disable <albumId>
5am albums public-link get <albumId>
```

Sharing nuances:
- **Currency default is `USD`** for any `--share` spec that includes a price. Override with `--currency EUR` (etc.). The flag applies to all `--share` specs in that invocation; for per-recipient currency, use `--shares-file`.
- **Existing user vs new email**: `5am albums share` handles both. If the email matches a registered user, the recipient gets a direct share and an email; if not, the backend creates a 7-day pending invite with a unique share token (the email contains the claim link).
- **Max 20 recipients per call** (backend enforces; exceeding returns 400 / exit 3).
- **Paid shares and public link are mutually exclusive.** `public-link enable` is rejected (400 / exit 3) if the album has any paid direct shares. Going the other way: adding a paid share to an album with public sharing on is also rejected — disable the public link first.
- **Cannot unshare a contributor.** If the recipient has uploaded media to the album, `unshare --user` returns 400 with `"You cannot unshare someone who contributed to the album."` Move/delete their contributions first.
- **All write commands require `write` scope.** `5am albums shares` (read-only listing) requires `read` scope. A read-scoped PAT trying to share/unshare/toggle public link exits with code `3` and `insufficient_scope`.

## Media

```sh
5am media list --album <albumId> --type image --search "sunset"   # lexical/full-text (filename, captions, EXIF text)
5am media list --album <albumId> --type video
5am media list --album <albumId> --type audio

# Semantic search — match by meaning, not literal tokens. Backed by Gemini
# embeddings over images.ai_description. Distinct from `--search` above:
# use this when the user describes what they want ("sunsets at the beach")
# rather than text they expect in the filename.
5am media semantic-search "sunsets at the beach"
5am media semantic-search "wedding photos" --album <albumId> --limit 20

5am media upload ./photos/*.jpg --album <albumId> --concurrency 8
5am media upload ./photos -r --album <albumId>                            # walk a directory
5am media upload ./photos -r --include '*.jpg,*.mp4' --album <albumId>    # filter by basename glob
5am media upload ./photos -r --exclude '*.tmp,backup_*' --album <albumId>

5am media download <mediaId> --output ./photo.jpg
5am media delete <mediaId> --yes

# View media as a full-screen, browser-based slideshow
# Launches a local server and opens the default browser automatically.
# Serves images, videos, and audio with cross-fade transitions.
5am media slideshow --folder ./photos --delay 5s                # Local files
5am media slideshow --album <albumId> --delay 10s --metadata    # Remote album, with metadata overlay

# Convert a local image. Inputs: PNG, JPEG, WebP, HEIF/HEIC. Outputs: PNG, JPEG, WebP.
# Two modes:
#
# SINGLE-FILE: one input arg + --output. Target format inferred from --output
# extension (.jpg/.jpeg, .png, .webp). --quality 1–100 (default 90) applies to
# JPEG output only — ignored for PNG and WebP (both lossless in this CLI). Input
# format detected from file header, NOT extension. JPEG targets flatten alpha.
5am media convert input.png --output out.jpg --quality 90
5am media convert input.jpg --output out.png
5am media convert input.png --output out.webp             # lossless WebP
5am media convert IMG_4421.HEIC --output out.jpg          # iPhone HEIC

# BATCH: multiple inputs, a directory, or -r. --output-dir + --to required.
# Output filename = <basename>.<target-ext> in --output-dir. Per-file failures
# appear in the manifest with status="error"; the batch keeps going.
# Output collisions (two inputs sharing a basename) are flagged as errors on
# the second file rather than overwriting silently.
5am media convert ./photos/*.heic --output-dir ./out --to jpg --concurrency 8
5am media convert ./photos -r --include '*.heic,*.png' --output-dir ./out --to webp
# Filter: --include / --exclude are comma-separated basename globs.
# When scripting partial-failure-tolerant flows, filter the manifest:
#   5am media convert ./pics -r --include '*.png' --output-dir ./out --to jpg \
#     | jq '.[] | select(.status=="error")'
# Exit is 0 even with per-file failures (same as `media upload`) — branch on the
# manifest, not the exit code.

# HEIF/HEIC input requires a platform helper (CLI shells out to it):
#   macOS:    `sips` — built into macOS, no install needed.
#   Linux:    `heif-convert` — apt install libheif-examples (Debian/Ubuntu).
#   Windows:  NOT SUPPORTED. The CLI returns an error pointing to macOS/Linux.
# Missing helper on a supported platform → exit 1 with install instructions.
# HEIF output is not supported on any platform.

# Resize a local image. PNG/JPEG/WebP in, same format out. Pass exactly one of
# --width or --height; the other is derived from the source aspect ratio.
# Aspect-ratio is always preserved (no cropping, no distortion). Upscaling is
# allowed without warning. Uses pure-Go CatmullRom (Lanczos-quality).
# HEIF input is NOT supported by resize — pipe through `media convert` first.
5am media resize input.png --output thumb.png --width 800
5am media resize input.jpg --output small.jpg --height 600
# JSON output includes: format, sourceWidth, sourceHeight, outputWidth, outputHeight.

# Render an MP4 from a local audio file with a Winamp-style animated waveform
# overlay. Optional cover image is letterboxed onto a slate-950 (#020617)
# canvas; without --cover the canvas is solid slate-950. Use for posting
# podcast WAVs (or any audio) to platforms that prefer video — YouTube, X,
# Instagram, TikTok. Pure file-in, file-out: no backend calls, no auth.
#
# Requires a local ffmpeg binary. Resolution order:
#   1. --ffmpeg <path> flag
#   2. $FFMPEG env var
#   3. PATH lookup ("ffmpeg")
# Missing binary returns an error with platform-specific install hints
# (`brew install ffmpeg`, `apt install ffmpeg`, `winget install ffmpeg`).
#
# Visualization style is one of ffmpeg's built-in audio-visualization filters.
# Default is `showwaves` (scrolling oscilloscope line). Others: `showfreqs`
# (frequency bars), `showcqt` (constant-Q transform), `showspectrum`
# (waterfall). Unknown styles error out client-side.
5am media visualize episode.wav --output episode.mp4
5am media visualize episode.wav --cover cover.jpg --output episode.mp4
5am media visualize episode.wav --cover cover.jpg --style showfreqs --output episode.mp4

# Burn in captions with --subtitles <file.srt|.vtt>. Pair it with the .srt/.vtt
# the Podcast Studio exports — timestamps are synced to the WAV. Only .srt and
# .vtt are accepted (the Studio's .json transcript is rejected with a hint).
# Captions are styled white-on-translucent-box and positioned just above the
# waveform strip so the visualization never covers the text.
5am media visualize episode.wav --cover cover.jpg --subtitles episode.srt --output episode.mp4

# Aspect-ratio presets via --aspect:
#   16:9 (default, 1280x720)  — YouTube landscape, X, generic
#   1:1  (1080x1080)          — IG feed, square crops
#   9:16 (1080x1920)          — IG Stories/Reels, TikTok, YouTube Shorts
# Explicit --width AND --height override --aspect; setting only one side
# derives the other from the aspect ratio (rounded to even for libx264).
5am media visualize episode.wav --cover cover.jpg --aspect 1:1 --output episode-square.mp4
5am media visualize episode.wav --cover cover.jpg --aspect 9:16 --output episode-vertical.mp4
5am media visualize episode.wav --aspect 9:16 --width 720 --output episode-720p-vertical.mp4   # → 720x1280
5am media visualize episode.wav --width 800 --height 800 --output episode-800.mp4              # explicit, --aspect ignored

# Custom ffmpeg path:
5am media visualize episode.wav --ffmpeg /opt/ffmpeg/bin/ffmpeg --output episode.mp4
FFMPEG=/opt/ffmpeg/bin/ffmpeg 5am media visualize episode.wav --output episode.mp4

# Overwrite an existing output file (default refuses):
5am media visualize episode.wav --output episode.mp4 --yes

# Free/unauthenticated runs include a small "Powered by 5AM" watermark in
# the bottom-left corner. Rendering works fully offline, logged in or not.
# When the watermark is rendered, the CLI prints a one-line "[5am]
# watermark added" hint to stderr; suggest `5am login` (free) when the
# user wants it gone.
#
# JSON output includes: input, cover (empty string if unset), output,
# style, aspect, width, height, ffmpeg (resolved binary path), watermark
# (bool), loggedIn (bool). ffmpeg's own progress (`time=… bitrate=…`)
# streams to stderr — do not parse it; rely on the JSON result and the
# exit code. Output container is MP4 with H.264 + AAC 128k and +faststart
# (QuickTime/iOS/YouTube-friendly).
#
# HEIF/HEIC covers are NOT supported — convert first with `5am media convert`.
# Any audio format ffmpeg understands works as input (WAV, MP3, M4A, FLAC, OGG).

# Download every media item in an album to a directory (paginates internally)
5am albums download <albumId> --output ./trip --concurrency 8
5am albums download <albumId> --output ./videos --type video
```

Upload notes:
- **HEIC/HEIF files are pre-converted to JPEG locally** before upload, using `sips` (macOS, built-in) or `heif-convert` (Linux, `apt install libheif-examples`). The server treats the upload as `image/jpeg` and skips its own conversion step — saves backend CPU. Quality is 100 to match the backend's own converter. On Windows, or on Linux without the helper, the HEIC is sent as-is (silent fallback). Original files on disk are never modified.
- **Every upload requires an album** — pass `--album <id-or-name>` or `--new-album <name>`. Applies to images, videos, and audio (the backend rejects uploads with no album for all media types). Without one, the CLI fails fast with a list of the user's albums; never let a script invoke `5am media upload` without picking one.
- Bare directory args require `-r/--recursive` — without it the command errors with a hint.
- Glob expansion: the shell expands first; the CLI also globs anything that survives. Quote the pattern (`'./photos/*.jpg'`) to force CLI-side globbing.
- `--include` / `--exclude` take comma-separated globs matched against the **basename** only. Exclude beats include. Hidden files (`.DS_Store`, `.git/...`) are always skipped during recursive walks and `*` glob expansion.
- Explicit file args bypass `--include` / `--exclude` filters — if you name a file directly, it uploads.
- Per-file progress lines stream to **stderr**; the final JSON manifest is on **stdout**.
- `--concurrency` defaults are conservative; bump to 8–16 for many small files.
- Videos use a presigned-URL flow internally — no client-side size limit.

Download notes:
- `albums download` paginates through the album server-side (fixed pageSize=20) and downloads concurrently.
- Output dir is created if missing.
- Filename collisions (two media items with the same `fileName`) get `_<id-prefix-8>` spliced before the extension. Items with no `fileName` save as `<id>.bin`.
- Path-traversal in server-supplied filenames is sanitized to basename — files always land inside `--output`.

## Media generation (text → media)

Requires API keys configured via `5am keys set` (see API Keys). All generators write the resulting file locally **and** return a JSON manifest on stdout.

```sh
5am media generate image --prompt "a cybernetic owl" --provider gemini --output owl.png
5am media generate video --prompt "a flowing river in autumn" --output river.mp4
5am media generate music --prompt "lo-fi hip hop for studying" --output chill.mp3
5am media generate audio --text "Hello, I am your AI assistant" --voice Puck --output hello.wav
5am media generate text --prompt "Write 3 b-roll scene ideas, one per line"   # → stdout
```

### Gemini image models (Nano Banana) — `media generate image`

The Gemini provider supports all three native image models via `--model`.
Default (when `--model` is omitted) is `gemini-2.5-flash-image`. The model is
**validated** — an unsupported value exits `3` with the accepted list.

| `--model` | Nickname | Notes |
|---|---|---|
| `gemini-2.5-flash-image` (default) | Nano Banana | Fastest/cheapest. Fixed 1024px — `--resolution` is ignored. |
| `gemini-3.1-flash-image` | Nano Banana 2 | Speed/cost balance. Adds 512px + extra aspect ratios + image-search grounding. |
| `gemini-3-pro-image` | Nano Banana Pro | Professional output, advanced "thinking", up to 4K. |

Optional generation controls (**Gemini provider only** — the OpenAI provider
ignores all of them):

- `--aspect-ratio <ratio>` — `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`,
  `9:16`, `16:9`, `21:9` (and `1:4`/`4:1`/`1:8`/`8:1` on `gemini-3.1-flash-image`).
- `--resolution <size>` — `512` (3.1 Flash only), `1K`, `2K`, `4K`. Uppercase
  `K`. 3.x models only; `gemini-2.5-flash-image` ignores it (always 1024px).
- `--image <path>` — **repeatable** reference/input image for editing,
  composition, or style transfer (up to 14 on 3.x). Must be `.png`,
  `.jpg`/`.jpeg`, or `.webp`; a bad type exits `3`.
- `--grounding` — enable Google Search grounding (web) so the image reflects
  real-time facts (weather, scores, current events).
- `--grounding-images` — additionally use web image-search results as visual
  context. **Only honored by `gemini-3.1-flash-image`.** Implies `--grounding`.

```sh
# Pick a model
5am media generate image --prompt "a cybernetic owl" --model gemini-3-pro-image --output owl.png

# Aspect ratio + resolution (3.x)
5am media generate image --prompt "a desert highway at golden hour" \
  --model gemini-3.1-flash-image --aspect-ratio 16:9 --resolution 2K --output road.png

# Reference images for editing/composition (repeat --image)
5am media generate image --prompt "put this logo on a coffee mug, photorealistic" \
  --image logo.png --image mug.jpg --model gemini-3-pro-image --output mockup.png

# Search-grounded image (real-time data)
5am media generate image --prompt "a chart of today's weather in San Francisco" \
  --model gemini-3.1-flash-image --grounding --aspect-ratio 16:9 --output weather.png

# Image-search grounding (3.1 Flash only)
5am media generate image --prompt "a detailed painting of a resplendent quetzal" \
  --model gemini-3.1-flash-image --grounding-images --output quetzal.png
```

The output extension is auto-corrected to the bytes actually returned (PNG /
JPEG / WebP), so `--output cover.png` may be saved as `cover.jpg` with a stderr
note. The same controls are exposed to AI characters through the
`local_generate_image` skill args: `model`, `aspect_ratio`, `resolution`,
`reference_images` (array of paths), and `grounding`.

### Gemini video models (Veo) — `media generate video`

Supports the Veo 3.1 family via a **validated** `--model` (bad value exits `3`
with the accepted list). Default `veo-3.1-generate-preview`. Clips are short
(~8s) — generate several and join them with `media concat` (below).

| `--model` | Notes |
|---|---|
| `veo-3.1-generate-preview` (default) | Highest quality. |
| `veo-3.1-fast-generate-preview` | Faster / lower cost. |
| `veo-3.1-lite-generate-preview` | Lightest / cheapest. |

Parameters: `--aspect-ratio` (`16:9`/`9:16`), `--resolution` (`720p`/`1080p`/`4k`),
`--duration` (seconds), `--negative-prompt`, and image inputs:
- `--image <path>` — initial/first frame (image-to-video).
- `--last-frame <path>` — final frame for interpolation; **requires `--image`**.
- `--reference-image <path>` (repeatable) — asset references; **cannot** combine
  with `--image`/`--last-frame`.
Frame/reference images must be `.png`, `.jpg`/`.jpeg`, or `.webp`.

```sh
5am media generate video --prompt "a river" --model veo-3.1-fast-generate-preview \
  --aspect-ratio 16:9 --resolution 1080p --duration 8 --output river.mp4
5am media generate video --prompt "slow zoom out" --image start.png --output clip.mp4
5am media generate video --prompt "she fades" --image first.png --last-frame last.png --output interp.mp4
5am media generate video --prompt "x" --last-frame end.png            # error: --last-frame requires --image
5am media generate video --prompt "x" --image a.png --reference-image b.png  # error: mutually exclusive
```

The simple text params (`model`, `aspect_ratio`, `duration`, `resolution`,
`negative_prompt`) are also exposed to AI characters via the
`local_generate_video` skill. (Image inputs are CLI-only.)

### Generate text — `media generate text`

`5am media generate text --prompt "..."` generates plain text with a Gemini
text model. Unlike the other generators (which write binary files), the response
goes to **stdout** by default so it can be piped/captured; `--output <file>`
writes to a file instead. Markdown code fences are stripped. Requires a Gemini
key (`5am keys set gemini <key>`).

```sh
5am media generate text --prompt "Summarize in one sentence: ..."          # → stdout
SUMMARY=$(5am media generate text --prompt "...")                          # capture
5am media generate text --prompt "..." --output notes.txt --yes            # → file
5am media generate text --prompt "..." --model gemini-2.5-pro              # pick model
```

Models (`--model`, default `gemini-3-flash-preview`): `gemini-3-flash-preview`
(fast), `gemini-2.5-flash`, `gemini-2.5-pro` (strongest). This backs the
transcript-driven scene prompts in `scripts/podcast_to_video.py` — it turns a
podcast transcript into per-scene b-roll prompts so the video tracks the
conversation.

### Join video clips — `media concat`

`5am media concat <clip1> <clip2> [more...] --output combined.mp4` joins clips
via a local ffmpeg (resolved `--ffmpeg` → `$FFMPEG` → PATH, like `media
visualize`). Needs **at least 2** clips. By default it **stream-copies**
(lossless, instant) and **auto-falls-back to re-encode** if the clips' codecs
don't match; `--reencode` forces re-encode. `--audio <file>` lays an audio track
over the joined video (replaces clip audio, `-shortest`) — the Veo path for
podcast audio→video. `--yes` overwrites the output.

```sh
5am media concat scene1.mp4 scene2.mp4 scene3.mp4 --output story.mp4
5am media concat a.mp4 b.mp4 --reencode --output combined.mp4
5am media concat v1.mp4 v2.mp4 --audio episode.wav --output podcast-video.mp4   # podcast b-roll
```

JSON result: `inputs`, `output`, `mode` (`copy`/`reencode`), `audio`, `ffmpeg`.
ffmpeg progress streams to stderr — rely on the JSON + exit code, not stderr.

### Duck background music under a voice — `media mix`

`5am media mix --voice <dialogue> --music <bed> --output <mix>` mixes a
voice/dialogue track over background music with **automatic ducking** via a
local ffmpeg ≥ 4.4 (resolved `--ffmpeg` → `$FFMPEG` → PATH, like `media
visualize`): the music is loudness-staged under the voice, sidechain-ducked
while the voice speaks, and ducked deeper in the 250 Hz–4 kHz speech band (a
dynamic **EQ pocket**). Output length = voice length; shorter music loops and
fades out at the end. Output format from the `--output` extension: `.wav`,
`.mp3`, `.m4a`, `.flac`. Inputs must be audio files (video containers are
rejected — extract audio first with `ffmpeg -i in.mp4 -vn audio.m4a`).

`--style` presets: `podcast` (default — voice is king, bed −18 dB, −16 LUFS),
`documentary` (gentler, slower release), `promo` (music-forward, −14 LUFS),
`ambient` (barely-there bed). Every parameter is overridable: `--bed-level`,
`--duck-depth`, `--pocket-depth` (0 disables the pocket), `--ratio`,
`--attack`, `--release`, `--target-lufs`, `--true-peak`, `--fade-out`.
`--yes` overwrites the output.

```sh
5am media mix --voice episode.wav --music bed.mp3 --output mix.wav
5am media mix --voice narration.wav --music score.mp3 --style documentary --output cut.m4a
5am media mix --voice ep.wav --music bed.mp3 --bed-level -24 --duck-depth 16 --output deep.mp3
```

Unauthenticated runs append a short spoken "Powered by 5AM" tag at the very
end of the mix (removed by `5am login`; rendering is fully offline). JSON result:
inputs, `style`, measured `voiceLufs`/`musicLufs`/durations, applied
`voiceGainDb`/`musicGainDb`, all resolved duck parameters, `multiband`
(EQ-pocket vs full-band fallback), `watermarkTag`, `ffmpeg`. ffmpeg progress
streams to stderr — rely on the JSON + exit code.

### AI highlight reels & the video-edit DSL — `media edit` / `media transcribe` / `media highlight`

Turn a long talking video into a highlight reel. The interchange format is
`.vedl` — a line-based edit DSL (cuts, transitions, text/image overlays,
color grading, ducked music bed, normalize, fades) executed by a
deterministic ffmpeg engine (local ffmpeg, `--ffmpeg` → `$FFMPEG` → PATH).
Transcription + edit generation need a Gemini key. Full `.vedl` language
reference: https://5am.app/cli/docs

```sh
5am media highlight talk.mp4 --output reel.mp4 --brief "a 60s teaser" --target-duration 60
5am media highlight talk.mp4 --output reel.mp4    # always writes reel.vedl + reel.transcript.json + reel.ops.json
5am media highlight talk.mp4 --music bed.mp3 --output reel.mp4    # ducked bed (media mix pipeline)

5am media transcribe talk.mp4                                     # → talk.transcript.json (or --format srt|vtt)
5am media edit generate --transcript talk.transcript.json --source talk.mp4 -o talk.vedl
5am media edit render talk.vedl --output cut.mp4 [--aspect 9:16] [--upload-album <id|name>]
5am media edit export talk.vedl --new-album "Edit sources"        # → web video-editor project (login required)
```

Key facts for agents:
- The AI edit is **segment-index anchored** — cut points always land on
  transcript boundaries; repairs are deterministic and reported in the JSON
  result (`warnings`/`repairs`).
- To iterate on an edit, edit the `.vedl` (plain text, `#` comments) and
  re-run `edit render` — no AI call needed. `cut` keeps, `delete` removes
  (one style per script); `atsrc`/`fromsrc` = source time, `at`/`from` =
  output time. No straight apostrophes in `text` (use `’`).
- `music`/`normalize` reuse the `media mix` staging/duck math and its style
  presets; grading degrades with warnings on old ffmpeg; logged-out renders
  are watermarked (rendering itself is fully offline).
- `edit export` uploads the referenced media into an album and creates the
  project via the video-editor API; ducking/fades/HSL are not representable
  web-side (carried as `vedl*` fields — the CLI render is authoritative).

### Memory collage video — `media collage`

`5am media collage [paths... | --folder <dir> | --album <id|name>] --output
<out.mp4>` builds a montage ("memory collage") video from photos and/or videos
via a local ffmpeg (resolved `--ffmpeg` → `$FFMPEG` → PATH, like `media
visualize`/`concat`). Stills get a slow **Ken Burns** pan/zoom and cross-fade
together; videos are normalized to the canvas and joined inline. With `--music
"<prompt>"` it generates a **Lyria** track (`lyria-3-clip-preview`, needs a
Gemini key) and lays it over the montage (looped, `-shortest`); `--music-file
<track>` supplies your own instead (no key needed); omit both for a silent
montage. With `--upload-album <id|name>` (or `--new-upload-album <name>`) the
finished MP4 is uploaded into a 5AM album after rendering.

Source is **exactly one** of: positional paths, `--folder`, or `--album`
(downloaded first). Stills: `.jpg/.jpeg/.png/.webp`; videos: `.mp4/.mov/.m4v`
(HEIC skipped with a "convert first" hint). Crossfades use `xfade` for all-stills
sets; sets that mix in a video, or `--transition 0`, use hard cuts.

```sh
5am media collage --folder ./photos --output memory.mp4 --music "warm nostalgic piano" --aspect 9:16
5am media collage img1.jpg img2.jpg clip.mp4 --output memory.mp4 --music-file track.mp3
5am media collage --album "Trip 2026" --output trip.mp4 --music "upbeat indie" --upload-album "Memories"
5am media collage ./photos/*.jpg --output m.mp4 --seconds-per-photo 3 --transition 0.5   # pacing
5am media collage ./photos/*.jpg --output m.mp4 --no-kenburns --transition 0             # static, hard cuts
```

Framing: by default each item **fills** the canvas and the overflow is cropped
(crop biased toward the top so faces in the upper part of a portrait survive a
square/landscape canvas). Pass `--fit` to **letterbox** the whole item instead —
nothing is cropped — when subjects sit near the edges. Or pass `--smart-crop` to
keep the fill crop but have **Gemini Vision** find each still's main subject and
**center the crop on it** (stills only, needs a Gemini key; detected boxes —
and failures — are cached to `~/.5am/collage-subjects.json`, override via
`--smart-crop-cache`, so repeat runs don't re-call the model; a deterministic
failure is recorded once and skipped thereafter, a transient one retried up to
3 runs; failures fall back to the heuristic crop; ignored with `--fit`). (With
Ken Burns the zoom re-centers slightly; for guaranteed no-crop use `--fit`, or
`--fit --no-kenburns`.)

Flags: `--aspect` (`16:9`/`1:1`/`9:16`, default `16:9`) or explicit
`--width`/`--height`; `--seconds-per-photo` (default 4); `--transition` (default
0.5s, 0 = hard cuts); `--no-kenburns`; `--fit`; `--smart-crop` /
`--smart-crop-cache`; `--ffmpeg`; `--yes`. Unauthenticated runs add a "Powered
by 5AM" watermark (removed by `5am login`). Output is H.264 (yuv420p) + AAC-128k
stereo MP4 with `+faststart`. JSON result: `inputs`, `output`, dims,
`music`/`musicFile`, `transition`, `kenBurns`, `fit`, `smartCrop`, `watermark`,
`ffmpeg`, and `uploadedToAlbum` (when uploaded). ffmpeg progress streams to
stderr — rely on the JSON + exit code.

## API keys (third-party providers)

Stored encrypted server-side; used by `media generate` and the local generation skills.

```sh
5am keys list                          # redacted
5am keys set gemini <KEY>
5am keys set openai <KEY>
5am keys delete gemini --yes
```

## AI Characters

Characters are server-side AI personas with their own scoped CLI token, optional skills, and optional webhooks.

### Inspect

```sh
5am characters list
5am characters get <characterId>
```

### Create

```sh
# Minimal — auto-mints a CLI token at scopes=read.
# The plaintext token is on the response under `cli_token`; surface it once
# to the user since the server keeps only the hash.
5am characters create --name "Pico"

# Skip auto-mint — character starts tokenless. Mint later via web Settings
# tab. Use this for scripts that don't need to drive the character via CLI.
5am characters create --name "Pico" --no-token

# Full profile
5am characters create \
  --name "Pico" \
  --type hybrid \
  --communication-style "friendly and concise" \
  --expertise "photography,travel" \
  --values "honesty,curiosity" \
  --goals "help me organize my photo library" \
  --skills get_album_images,fetch_media \
  --scopes read,write \
  --ai-model gemini-2.5-flash

# Load a long system prompt from a .md or .txt file (max 256 KB).
# Mutually exclusive with --system-instruction.
5am characters create --name "Pico" --system-instruction-file ./prompts/pico.md

# From a JSON template (flags layer on top, override fields)
5am characters create --from-file ./pico.json --name "Pico v2"
```

### Update / delete

Updates are **partial** — only flags you pass are sent.

```sh
5am characters update <characterId> --communication-style "warmer, more playful"
5am characters update <characterId> --skills get_album_images,fetch_media,generate_image --scopes read,write
5am characters update <characterId> --active false        # kill switch (see gotchas)
5am characters update <characterId> --memory-enabled false

# Replace system_instruction from a .md or .txt file (same flag as create).
5am characters update <characterId> --system-instruction-file ./prompts/pico-v2.md

5am characters delete <characterId> --yes                 # cascades to token, webhooks, interactions, memory
```

Important nuances:
- `--skills` enables skills with **default config**. For per-skill config overrides, use `--from-file` with the full JSON body.
- `--scopes` updates the per-character CLI token's scopes **in place** — no rotation, no new plaintext.
- `--active false` deactivates the character's CLI token at lookup time. Outstanding 15-min CLI JWTs continue working until expiry.
- **`--no-token` is `create`-only.** By default `create` mints a CLI token and returns the plaintext **exactly once** under `cli_token` on the response. Capture it from the JSON before any further processing — it cannot be retrieved later, only rotated.
- **`--system-instruction-file`** (create + update) accepts only `.md` and `.txt` (case-insensitive). Capped at 256 KB. Cannot be combined with `--system-instruction` — passing both errors out before any network call.

### Chat

Two modes: one-shot (message as arg) or REPL (no message arg, reads stdin).

```sh
# One-shot
5am characters chat <characterId> "what's on my schedule today?"

# REPL — empty line or Ctrl+D exits
5am characters chat <characterId>

# Persistent multi-turn context across runs
5am characters chat <characterId> "remember my dog is called Pico" --history /tmp/chat.json
5am characters chat <characterId> "what's my dog's name?"          --history /tmp/chat.json

# Local skills (file/command access) — prompts for approval by default
5am characters chat <characterId> "create a summary.txt of my recent work"

# Autonomous mode — bypass approval for non-destructive skills.
# Still prompts on: destructive commands (rm, dd, mkfs, sudo rm, ...), and
# read_file/write_file paths outside the current working directory.
5am characters chat <characterId> "cleanup my logs" --auto-approve

# Fully unattended (only when the user has explicitly opted in to
# out-of-workspace access for this session):
5am characters chat <characterId> "..." --auto-approve --allow-outside-workspace

# Structured response (tool_calls, media_urls, tokens_used, interaction_id)
5am characters chat <characterId> "draw me a sunset" --json | jq .
```

Output behavior:
- **Default mode**: model text → stdout, tool-call/media-URL footers → stderr (clean piping).
- **`--json`**: full structured JSON → stdout, nothing on stderr.
- **`--history <path>`**: file rewritten on each turn (one-shot) or once on REPL exit.
- **`--no-save`**: disable history writing.

### Evals — `5am characters eval <id> --suite tests.json`

Runs a fixed prompt set against a character and reports pass/fail per test.
JSON report on stdout (jq-friendly), summary line on stderr, exit `3` if
any test failed.

Three judge modes per test:

- `llm_judge` (default) — rubric sent to Gemini judge (default
  `gemini-2.5-pro`). Use for open-ended / creative responses.
- `tool_calls` — deterministic. Empty list asserts **no** tool calls.
  `args_match` constraints: `equals`, `contains`, `regex`, `exists`.
- `expected_response` — text overlay: `equals` / `contains` / `regex`.
  ANDed with the chosen judge.

Use evals to guard regressions when:
- Editing a character's system_instruction
- Changing the enabled skills set
- Upgrading models

Tests run in parallel by default (`--concurrency 4`). Bump to 8 for
large suites; drop to 1 if you hit rate-limit errors. Result ordering
in the JSON report is stable — `.results[i]` always maps to
`.tests[i]` in the suite, so existing `jq` filters keep working
regardless of worker scheduling.

Skill recipe:
bin/5am characters eval <characterId> --suite cli/examples/eval/smoke.json
bin/5am characters eval <characterId> --suite cli/examples/eval/smoke.json --concurrency 8


### Semantic search — `5am media semantic-search` and the `library_search` skill

Same engine, two surfaces. Both run vector search over
`images.ai_description` (Gemini embeddings, 768d, `gemini-embedding-2`).

- **Direct CLI**: `5am media semantic-search <query> [--album <id>] [--limit N]`.
  Read-scoped, no character needed. Use this when the user wants results
  themselves; pipe to `jq`.
- **Skill (agent-driven)**: characters with `library_search` enabled call
  `library_search({query, album_id?, limit?})` mid-chat to find media by
  meaning, then talk about the matches. Use this when the user is
  conversing with a character that should browse their library.

Both paths return the same shape: `{matches: [{media_id, file_name,
ai_description, album_id, album_name, media_type, similarity}], total_count}`.

**Distinct from `5am media list --search <text>`** which is *lexical*
full-text — it matches literal tokens in filename / captions / EXIF text.
Pick by intent:

- "find IMG_kim.jpg" → `media list --search "kim"` (token match)
- "find sunset photos" → `media semantic-search "sunsets"` or the
  `library_search` skill (meaning match)

Prerequisite (semantic only): items must have an `ai_description`.
Backfill from the CLI — one command for both images and video/audio,
backend dispatches by media_type:

```sh
# Single item — sync for images, async for video/audio.
5am media generate-summary <mediaId>
5am media generate-summary <mediaId> --force   # overwrite (images only)

# Whole album — async. Submits the album for semantic-search indexing via
# the Gemini Batch API (images embedded multimodally at 50% of standard
# rate; video/audio missing a description always get a Go-service summary
# triggered as part of the same call — no flag needed).
5am albums generate-summary <albumId>
```

The whole-album response is `{batch_job_ids[], summaries_triggered,
summaries_failed, summary_errors?, estimated_cost_usd, nothing_to_do}`.
Embeddings land via a batch poller (minutes to hours), summaries via
`/api/video-webhook` — both async, so don't expect results immediately on the
202. Re-running on an album that's already fully indexed is a no-op and
returns `nothing_to_do: true` with empty `batch_job_ids` — that's expected,
not a failure; don't retry it as if something went wrong. A bad or
not-yours album id is a different story: it fails with exit 3 (`404
album_not_found`) or exit 2 (`403 forbidden`), not a silent success — so
branch on the exit code, and don't confuse a 404 with `nothing_to_do`. (The
single-item `5am media generate-summary` above is the only synchronous path,
and only for images.)

A `total_count == 0` result has two possible causes, and they need
different follow-ups:
- **Nothing indexed yet** — the items lack embeddings. Suggest
  `5am albums generate-summary <id>` and retry once it lands.
- **Nothing relevant** — the library is indexed but holds nothing close to
  the query. The endpoint applies a minimum-similarity floor (~0.6 cosine),
  so weak matches are dropped rather than returned with low scores. This is
  intentional: a search for "scuba diving" over a baking library correctly
  returns nothing instead of confidently-ranked irrelevant photos. Don't
  keep suggesting re-indexing in this case — the user simply may not have
  matching media.

The skill's audit row stores `{count, top_similarity}`, not the matches.

### `render_html` — sandboxed HTML output

Server-side skill (write scope). The model invokes it to produce HTML/CSS/JS
that renders in a sandboxed iframe in the web chat UI (CSP-locked, CDN
allowlist for Chart.js/D3/Plotly/jsdelivr/unpkg). Web chat: appears inline
above any text response. CLI: HTML written to a temp file, path printed to
stderr; pass `--render-html-open` to auto-launch the default browser, or
`--render-html-output <path>` to pin a specific file.

When suggesting prompts that benefit from `render_html`, hint at the kind of
output (chart, demo widget, interactive form). Don't try to inline the HTML
in stdout — `render_html` results don't appear in `resp.response`, only in
`resp.tool_calls[]`.

```sh
# Auto-open output:
5am characters chat <id> "draw a bar chart of [1,5,3,8,2]" --render-html-open
# Save to specific path:
5am characters chat <id> "..." --render-html-output ./chart.html
```

Audit row stores `{html_size, has_external_scripts, external_script_count}` —
not the raw HTML.

### Custom skills (user-defined)

Users can extend the local-skill catalog with JSON manifests in
`~/.5am/skills/<name>.json` (or `$5AM_SKILLS_DIR`). Each manifest declares
`{name, description, input_schema, run|shell, timeout_seconds?,
max_output_bytes?}`. The CLI merges them with built-ins on every chat — the
model sees them as ordinary tools. Two execution modes:

- `run: ["cmd", "arg", "{{key}}"]` — argv form, `{{key}}` substituted from args
- `shell: "cmd \"$key\" | head"` — string passed to `$SHELL -c`, args via env

Manage from the CLI:

```sh
5am skills list                          # built-ins + enabled custom (JSON)
5am skills list --all                    # include disabled
5am skills validate ./manifest.json      # static check before installing
5am skills disable <name> / enable <name>
```

When scripting against a user's environment, **do not assume the skill set is
exactly the built-ins** — a custom skill may be defined that the model can
call. `5am skills list --all | jq '.[] | select(.kind=="custom")'` reveals them.

### Local skills (run on the user's machine)

Provided by the CLI to characters in `chat`:
- `read_file` — read a local file. **Workspace-sandboxed** (see below).
- `write_file` — create/update a local file. **Workspace-sandboxed** (see below).
- `run_command` — execute shell command. Destructive ops prompt even under `--auto-approve`. Uses `$SHELL` → `sh` → `bash` on Unix, `cmd.exe` on Windows; override with `5AM_SHELL=/path/to/shell`.
- `local_ffmpeg` — invoke local FFmpeg. **Args take an array of strings**, e.g. `{"args": ["-i", "my photo.jpg", "out.mp4"]}` — no shell parsing, so filenames with spaces/special characters work. The legacy single-string form is rejected with a hint.
- `local_generate_image` — render AI image, save locally. Accepts `provider` (`gemini`/`openai`) plus, on Gemini, `model` (the three Nano Banana models), `aspect_ratio`, `resolution`, `reference_images` (array of local paths), and `grounding`.
- `local_generate_video` — render AI video (Veo), save locally. Accepts `model` (the three Veo 3.1 models), `aspect_ratio`, `duration`, `resolution`, `negative_prompt`. (Image inputs are CLI-only, not exposed to the skill.)
- `local_generate_music` — render AI music, save locally
- `local_generate_audio` — TTS, save locally

#### Workspace sandbox (read_file / write_file)

`read_file` and `write_file` are scoped to the CLI's current working directory by default. Symlinks are resolved before the check, so an in-workspace symlink pointing at `/etc` is treated as out-of-workspace.

- **Inside CWD**: silent under `--auto-approve`, prompted otherwise.
- **Outside CWD**: forces an interactive `[y/N]` prompt **even with `--auto-approve`**, showing the resolved path. Non-TTY scripts that try to read/write outside CWD will block.
- **Opt-out**: pass `--allow-outside-workspace` on `chat` (or set `5AM_ALLOW_OUTSIDE_WORKSPACE=1`) to fall back to the normal `--auto-approve` rules. Use sparingly — it grants the character full read/write to the user's home directory.

When scripting, either run the CLI from the directory the character should operate in, or pass `--allow-outside-workspace` if the user has explicitly opted in.

#### Destructive-command detection

Any skill that ultimately shells out — `run_command`, `local_ffmpeg`, and **custom skills** (both `run` and `shell` modes) — is screened against a heuristic deny-list before execution. A match forces an interactive `[y/N]` prompt **even under `--auto-approve`**.

Detection covers:
- **Whole-token binaries**: `rm`, `rmdir`, `dd`, `mkfs.*`, `mkswap`, `fdisk`, `parted`, `sgdisk`, `wipefs`, `kill`, `pkill`, `killall`, `shred`, `wipe`, `truncate`, Windows `format`.
- **Privilege-elevation prefixes** (`sudo`, `doas`, `pkexec`) are stripped before matching, so `sudo rm -rf /` still trips on `rm`.
- **Substring patterns**: shell output redirection (`>`), block-device paths (`/dev/sd*`, `/dev/nvme*`, `/dev/disk*`, `/dev/hd*`), recursive permission rewrites (`chmod -R`, `chown -R`), fork-bomb prefix `:(){`.

For custom skills the screen checks what will actually execute: `run` (argv) mode expands `{{key}}` placeholders first, so a malicious arg can't hide behind a template; `shell` mode screens the command string itself (args arrive as env vars, and quoted expansions like `"$path"` can't become shell syntax). Note that `shell` mode **never** substitutes `{{key}}` at execution — a `{{key}}` left in a `shell` string reaches the shell as literal text; write `"$key"` instead.

The detector errs aggressive: false positives just mean an extra prompt; false negatives could mean silent data loss. When scripting unattended workflows that legitimately need destructive commands, the only escape is interactive approval — there is no flag to bypass destructive screening.

### Server-side skills

```sh
5am characters skills available                              # platform-wide catalog
5am characters skills tools <characterId>                    # this character's enabled tools (Gemini function-calling schemas)

5am characters skills execute <characterId> get_album_images \
  --input '{"album_id":"<albumId>","limit":5}'

5am characters skills execute <characterId> generate_image \
  --input-file prompt.json                                    # use '-' for stdin
```

Insufficient scope returns a **structured denial in the response**, not an HTTP error — check the JSON, don't rely on exit code alone.

### Webhooks

Each character can have one or more webhook endpoints receiving `chat.completed` and `skill.executed` events. Every delivery carries `X-5am-Signature: sha256=<hex>` = `HMAC-SHA256(<timestamp>.<body>, <signing_secret>)`. The signing secret is the connection's `access_token` — get it via `webhooks list` or rotate with `rotate-secret`.

```sh
# CRUD
5am characters webhooks list <characterId>
5am characters webhooks create <characterId> \
  --name "Slack relay" \
  --url https://example.com/hooks/5am \
  --events chat,skill                                  # values: chat, skill (comma-separated)

# Outbound auth (how the CLI identifies itself to the receiver)
5am characters webhooks create <characterId> \
  --name "Bearer auth" --url https://example.com/hooks/5am \
  --auth bearer --bearer-token "$TOKEN"

5am characters webhooks create <characterId> \
  --name "Header auth" --url https://example.com/hooks/5am \
  --auth header --header-name X-Webhook-Secret --header-value "$SECRET"

# Partial updates — only passed flags are sent
5am characters webhooks update <characterId> <connId> --active false
5am characters webhooks update <characterId> <connId> --events chat
5am characters webhooks update <characterId> <connId> --url https://new.example.com/hooks

# Test — POSTs a synthetic connection.test event, prints receiver status + signed timestamp + HMAC.
# Bypasses is_active and allowed_actions; does NOT bookkeep error_count.
5am characters webhooks test <characterId> <connId>

# Rotate signing secret — old secret stops verifying immediately. Update receiver BEFORE next real delivery.
5am characters webhooks rotate-secret <characterId> <connId>

5am characters webhooks delete <characterId> <connId> --yes
```

#### Local webhook listener (for development)

`webhooks listen` runs a local HTTP server, registers a temporary connection pointing at a public URL the user supplies (via ngrok / cloudflared / their own proxy — the CLI does not bundle a tunnel), verifies HMAC, and prints validated events. Deletes the connection on Ctrl+C.

```sh
# Terminal 1: expose port
ngrok http 4747

# Terminal 2: register webhook + stream events
5am characters webhooks listen <characterId> \
  --url https://abc-123.ngrok.app \
  --port 4747

# Pipe raw event JSON
5am characters webhooks listen <characterId> --url https://... --port 4747 --json | jq .

# Filter to one event family
5am characters webhooks listen <characterId> --url https://... --port 4747 --events skill

# Leave the connection registered on Ctrl+C (debugging)
5am characters webhooks listen <characterId> --url https://... --port 4747 --keep
```

Listener behavior:
- Verifies `X-5am-Signature`. Mismatched or stale (>5 min skew) → `401`.
- Connection name defaults to `5am-cli-listen-<pid>` — override with `--name`.
- `--port` is the local bind port. `--url` is the **public** URL the dispatcher POSTs to (must route to that local port via the user's tunnel).
- Path defaults to `/hook` — change with `--path`.

## Server agents & local datasets

Deploy the CLI on a server as an outbound agent so the user's AI characters can
answer live questions about that machine ("how many unique IPs hit us in the
last 24h?", "what was peak CPU overnight?"). Data stays in a local SQLite store
(`~/.5am/agent/data.db`, override `$5AM_AGENT_DIR` or `--data-dir`); only query
results leave the box. The daemon dials OUT (HTTPS long-poll) — no inbound
port, works behind NAT. Full runbook: [`docs/server-agent.md`](docs/server-agent.md).

### Datasets (`5am data`)

Schema file: `{"fields": {"<name>": "string|number|timestamp", ...}, "time_field": "<field>"}`.
Names match `[a-z][a-z0-9_]{0,63}`. `time_field` optional but required for
`--since/--until`, `latest`, and `prune`. Timestamps accept RFC3339, unix s, unix ms.

```sh
# Ingest from a FILE — ALWAYS prefer this for files: keeps a byte-offset
# resume checkpoint (per dataset+file, committed atomically with the rows),
# so re-runs ingest only NEW lines. Detects rotation and truncation.
5am data ingest --dataset requests --schema requests.schema.json \
  --file /var/log/nginx/access.log --format combined

# --follow = keep tailing (tail -F semantics); run under systemd. Blocks.
5am data ingest --dataset requests --schema requests.schema.json \
  --file /var/log/nginx/access.log --format combined --follow

# --format combined parses nginx/apache access logs natively into
# ip/method/path/status/bytes/ts — declare the subset you want in the schema.
# Default format is jsonl (one JSON object per line; unknown keys ignored,
# missing fields become NULL).

# stdin works for one-shot pipes (NO checkpoint — do not cron `cat file |`):
journalctl -o json -u nginx | 5am data ingest --dataset njournal --schema j.schema.json

# Result JSON: {dataset, rows_ok, rows_rejected, first_errors[]} — bad rows
# are skipped and counted; --strict aborts on the first bad row instead.
# --replace REBUILDS the dataset (drops rows AND resets checkpoints).

# Query locally — the same engine the character's queries run through
5am data query --dataset requests --op count_distinct --field ip --since -24h
5am data query --dataset requests --op group_by --field path --limit 5
5am data query --dataset requests --op count --filter 'status:gte:500' --since -7d
5am data query --dataset sysmetrics --op stats --field cpu_pct --since -24h   # min/max/avg
5am data query --dataset sysmetrics --op latest                                # most recent row
5am data query --op list_datasets

# Ops: list_datasets | count | count_distinct | group_by | stats | latest.
# --filter 'field:op:value' repeatable; ops eq,ne,gt,gte,lt,lte,contains.
# stats needs a number field; latest/since/until need the dataset's time_field.

5am data list                                          # datasets + row counts + time coverage
5am data prune --dataset requests --keep-days 30       # retention (cron this)
```

### Agent daemon (`5am agent`, `5am serve agent`)

```sh
5am serve agent --name web-1        # the daemon: registers, long-polls, answers. Blocks.
5am agent list                      # registered agents + online flag (polled within 90s)
5am agent remove web-1 --yes        # revoke (daemon starts getting 404s; re-register to restore)
```

The daemon's queryable surface is EXACTLY: the built-in `dataset_query`
capability, plus the user's enabled custom-skill manifests (`~/.5am/skills/`,
see Local Skills above). Characters can never run arbitrary commands on the
box. Custom-skill invocations that trip the destructive screen (rm, dd, …)
are refused headlessly unless the daemon runs with `--allow-destructive`.

A READ-ONLY PAT is sufficient (all agent endpoints are read-scope by design) —
mint one for server deployments so a leaked token can't touch media.

### Wiring a character to it

Enable the `query_server` skill on a character (web Skills tab, or
`--skills query_server` at create). During chat the model sees the live agent
registry (names, online state, dataset schemas) injected into the tool
description and constructs structured queries; the agent executes them
locally and the answer resolves into the same chat turn (1–3s when online).
Offline/timeout produce explicit `agent_offline`/`agent_timeout` results —
the character reports the outage rather than inventing data.

## AI Playground (multi-character orchestration)

The Playground runs **sessions** where one **orchestrator** character coordinates a team of specialists to complete a task. Workflow: pick an orchestrator → create a session → submit a task → orchestration runs (with live progress on stderr) → final synthesized result lands on stdout as JSON.

**Paid plan required** for `sessions create`, `task`, and proposal/feedback writes — same gate as character chat/skills. Reads (`list`, `get`, `messages`, `orchestrators`) and `sessions delete` work on free plans so users keep control of their data.

### Inspect

```sh
5am playground orchestrators                        # characters with is_orchestrator=true
5am playground sessions list                        # all sessions (JSON)
5am playground sessions list --status active        # filter
5am playground sessions list --limit 50 --offset 0
5am playground sessions get <sessionId>             # full state: orchestrator, team, transcript
5am playground messages <sessionId>                 # transcript only (default 50, --limit/--offset)
```

### Create / delete sessions

```sh
5am playground sessions create \
  --name "Weekly newsletter" \
  --orchestrator <orchestratorId> \
  --team <id1>,<id2>                                # optional: pre-seed team

5am playground sessions delete <sessionId> --yes    # cleanup; works on free plan
```

### Submit a task (the headline command)

```sh
# Default: live progress to stderr (one line per orchestration event),
# final synthesized result JSON to stdout. Pipe stdout to jq.
5am playground task <sessionId> "Draft a newsletter from these URLs: https://..., https://..."

# Quiet — block on result, no progress stream.
5am playground task <sessionId> "..." --no-stream

# Capture result for downstream processing.
5am playground task <sessionId> "..." | jq '.result'

# Unattended: auto-approve proposals during orchestration. Caps new-character
# creation per task at --max-new-characters (default 3); excess proposals
# are auto-rejected. Multi-stage proposal flows are handled in-loop.
5am playground task <sessionId> "..." --auto-approve-proposals
5am playground task <sessionId> "..." --auto-approve-proposals --max-new-characters 5
```

While the task runs, stderr emits one line per `playground-*` SSE event:

```
[14:32:01] coordinator-thinking
[14:32:03] delegation-started — Researcher
[14:32:08] specialist-progress — Researcher
[14:32:14] specialist-complete — Researcher
[14:32:21] synthesis-started
{ "result": { ... } }   ← stdout
```

### Concepts

- **Session** — one orchestrated workflow (name, orchestrator, team, transcript).
- **Orchestrator** — character with `is_orchestrator=true`. Coordinates only; doesn't do specialist work.
- **Team member** — any other character pulled in (via `--team` on create, or by orchestrator proposing one mid-task).
- **Task** — plain-English prompt to the orchestrator. Triggers analysis → proposals (if specialists missing) → parallel delegation → synthesis.
- **Proposal** — orchestrator wants a specialist that doesn't exist yet. The task pauses; `sessions get` exposes the proposal state. Resolve **either** with `--auto-approve-proposals` on `5am playground task` (preferred for scripts; capped to prevent unbounded character creation) **or** in the web UI for hand-curation.
- **Feedback** — `approve` / `redirect` / `reject` on a result. Web-only today.

### Important nuances

- **Promote/demote orchestrators from the CLI**: `5am characters update <id> --orchestrator true|false`. Or create one as an orchestrator: `5am characters create --name "Lead" --orchestrator true`. The web UI Settings tab does the same thing.
- **Tasks run on the orchestrator's user — not the CLI token's character.** A user PAT works; a *character-bound* CLI token also works (the playground operates against the owner's account either way).
- **`task` is sync.** It blocks until orchestration completes (or pauses for proposals). Long workflows tie up the terminal — use `--no-stream` to run quietly, or run in the background and poll `sessions get`.
- **SSE auth**: the live progress stream uses `/api/sse` with the same JWT as everything else. If the user has only a `read`-scoped token, the stream still works (it's read-only); but `task` itself needs `write` + paid plan.
- **Proposals pause the task by default.** Two ways to handle them:
  - **Scripts (preferred)**: pass `--auto-approve-proposals` on `task`. Caps creation at `--max-new-characters` (default 3); rest are auto-rejected. Multi-stage flows handled in-loop, with a defensive 5-stage cap.
  - **Hand-curation**: omit the flag; the task POST returns `status: "awaiting_approval"` with a `proposals` array. Resolve in the web UI, then call `POST /api/playground/sessions/:id/resume` (REST only; CLI `playground resume` subcommand TBD) — or just re-run `5am playground task` with the same prompt.
- **Auto-approve creates characters that persist.** Each new character lives in `5am characters list` after the task. Adjust `--max-new-characters` accordingly; clean up afterwards with `5am characters delete <id> --yes` if needed.

## Recipes (agent workflows)

### "Upload these files to a new album and report the album URL"

```sh
ALBUM=$(5am albums create --name "$NAME" --description "$DESC" | jq -r .id)
5am media upload ./files -r --include '*.jpg,*.mp4' --album "$ALBUM" --concurrency 8 > /tmp/manifest.json
echo "Album ID: $ALBUM"
```

### "Download an entire album to a local directory"

```sh
5am albums download "$ALBUM" --output ./trip --concurrency 8 > /tmp/manifest.json
# Inspect failures (status="error") if any
jq '[.[] | select(.status=="error")]' /tmp/manifest.json
```

### "Wrap a podcast WAV into a shareable MP4 with a cover and waveform"

```sh
# Default style (showwaves) on a slate-950 background, with a cover image
5am media visualize ./episode.wav \
  --cover ./cover.jpg \
  --output ./episode.mp4

# For Instagram / TikTok — square aspect (or use --aspect 9:16 for Stories/Reels)
5am media visualize ./episode.wav \
  --cover ./cover.jpg --aspect 1:1 \
  --output ./episode-square.mp4
5am media visualize ./episode.wav \
  --cover ./cover.jpg --aspect 9:16 \
  --output ./episode-vertical.mp4

# Parse the JSON manifest if you need the resolved ffmpeg path or dims
5am media visualize ./episode.wav --output ./episode.mp4 \
  | jq '{output, style, width, height, ffmpeg}'
```

Then upload as audio (5AM stores the underlying WAV; the MP4 is a derived
artifact for off-platform sharing):

```sh
5am media upload ./episode.wav --album "$ALBUM"
# Or upload the MP4 if you want to keep both:
5am media upload ./episode.mp4 ./episode.wav --album "$ALBUM"
```

### "Turn a podcast WAV into a Veo b-roll video"

A richer alternative to the waveform overlay: generate a few Veo clips, join
them, and lay the episode audio over the result. Each Veo clip is ~8s and takes
minutes to render, so generate them as separate steps and `concat` deliberately.

```sh
# 1. Generate b-roll clips (one per scene). Match aspect ratio to the target.
5am media generate video --prompt "lo-fi study desk, warm lamp, slow pan" \
  --aspect-ratio 16:9 --duration 8 --output v1.mp4
5am media generate video --prompt "rain streaking down a city window at night" \
  --aspect-ratio 16:9 --duration 8 --output v2.mp4

# 2. Join the clips and lay the episode audio over them (replaces clip audio).
5am media concat v1.mp4 v2.mp4 --audio ./episode.wav --output ./episode-veo.mp4

# 3. (optional) upload the result alongside the WAV
5am media upload ./episode-veo.mp4 ./episode.wav --album "$ALBUM"
```

`media concat` stream-copies by default (instant) and falls back to re-encode if
the clips don't match; check the JSON `mode` field. Output length is the shorter
of the joined video and the `--audio` track (`-shortest`).

**One-shot wrapper (recommended).** `scripts/podcast_to_video.py` (stdlib-only
Python, cross-platform) automates the whole flow: measure duration → generate
enough clips → concat → mux audio → optionally burn in a transcript. When you
pass a transcript (`-s`) and no `-p` prompts, it uses `media generate text` to
write **per-scene b-roll prompts from the transcript**, so each clip tracks the
conversation. Clips retry up to 3× on transient Veo failures (jittered backoff).

```sh
# Transcript-driven b-roll, vertical, with burned-in captions:
python3 scripts/podcast_to_video.py -i episode.wav -s episode.srt -a 9:16 -o reel.mp4

# Cheap proof first (2 clips), keep the per-clip files for inspection:
python3 scripts/podcast_to_video.py -i episode.wav -s episode.srt --clips 2 --keep --workdir ./clips
```

Flags: `-m/--model` (Veo model), `-p/--prompt` (your own scenes — overrides the
transcript scene-writer), `--no-scene-prompts` (disable it), `-n/--clips`,
`-d/--duration`, `--max-clips` (default 30), `-j/--jobs` (generate N clips in
parallel; `-j 3`/`-j 4` is a good range), `--keep`/`--workdir` (clips land in
`<workdir>/clip_NNN.mp4`). Run `--help` for the full list. Each
Veo clip costs quota — start with `--clips 2`.

### "Find a media item by search and download it"

Two flavors. Pick by what the user actually said:

```sh
# Lexical: user gave you a literal token they expect in the filename/etc.
MEDIA=$(5am media list --album "$ALBUM" --search "kim" | jq -r '.[0].id')

# Semantic: user described what they want.
MEDIA=$(5am media semantic-search "sunset over the ocean" --album "$ALBUM" --limit 1 \
        | jq -r '.matches[0].media_id')

5am media download "$MEDIA" --output ./photo.jpg
```

Semantic returns no matches when items lack `ai_description` — if `total_count: 0`
on a fresh album, run `5am albums generate-summary "$ALBUM"` and retry once the
worker drains.

### "Share an album with a list of people and report what happened"

```sh
# Mix free + paid in one call.
RESULT=$(5am albums share "$ALBUM" \
  --share alice@example.com \
  --share bob@example.com:9.99 \
  --share carol@example.com:0:read_and_write)

# `succeeded` and `failed` arrays are on `.results`
echo "$RESULT" | jq '{succeeded: .results.succeeded, failed: .results.failed}'
```

### "Publish an album as a public link"

```sh
# Will fail (exit 3) if the album has any paid direct shares.
TOKEN=$(5am albums public-link enable "$ALBUM" | jq -r .publicShareToken)
echo "Public URL: https://5am.app/album/$ALBUM?shareToken=$TOKEN"

# Later: turn it off.
5am albums public-link disable "$ALBUM"
```

### "Revoke every direct share on an album"

```sh
# Pull emails of direct shares and unshare each. Contributors are skipped
# server-side (400); the loop continues.
5am albums shares "$ALBUM" | jq -r '.directShares[].email' | while read -r email; do
  5am albums unshare "$ALBUM" --user "$email" --yes || \
    echo "skipped $email (likely a contributor)" >&2
done
```

### "Bulk-delete an album safely"

Albums must be emptied first (server-side safety check on the platform).

```sh
5am media list --album "$ALBUM" | jq -r '.[].id' | \
  xargs -I{} 5am media delete {} --yes
5am albums delete "$ALBUM" --yes
```

### "Spin up a character, give it scopes, chat once, tear down"

```sh
CHAR=$(5am characters create --name "Scratch" --skills get_album_images --scopes read | jq -r .id)
5am characters chat "$CHAR" "list my albums" --json | jq .
5am characters delete "$CHAR" --yes
```

### "Run a multi-character orchestration end-to-end (unattended)"

```sh
# 1. Find an orchestrator, or promote one if none exist.
ORCH=$(5am playground orchestrators | jq -r '.[0].id // empty')
if [ -z "$ORCH" ]; then
  # Promote the first character we have, or create a fresh orchestrator.
  CHAR=$(5am characters list | jq -r '.[0].id // empty')
  if [ -n "$CHAR" ]; then
    5am characters update "$CHAR" --orchestrator true >/dev/null
    ORCH="$CHAR"
  else
    ORCH=$(5am characters create --name "Lead" --orchestrator true \
      --communication-style "decisive, breaks tasks into pieces" \
      | jq -r .id)
  fi
fi

# 2. Create a session.
SESSION=$(5am playground sessions create \
  --name "Newsletter $(date +%Y-%m-%d)" \
  --orchestrator "$ORCH" \
  | jq -r .id)

# 3. Submit the task with auto-approve so the orchestrator can spin up
#    specialists on its own. Cap creation at 3 to bound the blast radius.
5am playground task "$SESSION" \
  "Draft a weekly newsletter summarizing these URLs: $URL1, $URL2" \
  --auto-approve-proposals --max-new-characters 3 \
  | jq '.result' > newsletter.json

# 4. Audit the transcript if you want to see how the team got there.
5am playground messages "$SESSION" | jq '.[] | {sender_type, sender_name, content}'
```

### "Run with hand-curated proposals (interactive)"

```sh
# Default: task pauses on proposals. Inspect, then resume in the web UI
# (or via the REST `/sessions/:id/resume` endpoint).
RESULT=$(5am playground task "$SESSION" "$PROMPT")
STATUS=$(echo "$RESULT" | jq -r '.status // "unknown"')

if [ "$STATUS" = "awaiting_approval" ]; then
  echo "Orchestrator proposed new specialists. Review/approve at:" >&2
  echo "  https://5am.app/ai/playground/$SESSION" >&2
  echo "$RESULT" | jq '.proposals'
  exit 3
fi
echo "$RESULT" | jq '.result'
```

### "Install a one-off custom skill from a recipe"

```sh
mkdir -p ~/.5am/skills
cat > ~/.5am/skills/git-status.json <<'JSON'
{
  "name": "git_status",
  "description": "Show git status (short form) for a local repo path",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Repo directory" }
    },
    "required": ["path"]
  },
  "run": ["git", "-C", "{{path}}", "status", "--short"],
  "timeout_seconds": 15
}
JSON
5am skills validate ~/.5am/skills/git-status.json   # confirm shape
5am skills list | jq '.[] | select(.kind=="custom")'
# Now any character chat can use git_status:
5am characters chat "$CHAR" "what's the git status of /tmp/repo?"
```

### "Cleanup characters spawned by auto-approve"

Auto-approved characters persist across tasks. To prune those introduced by
a specific session, diff the team-member list before/after:

```sh
# Capture the team after orchestration completed
AFTER=$(5am playground sessions get "$SESSION" | jq -r '.team_members[].id')
# (Pre-task team would have been the orchestrator alone or a known seed.)
# Delete any characters you don't want to keep:
echo "$AFTER" | while read -r id; do
  read -p "Delete character $id? [y/N] " a < /dev/tty
  [ "$a" = "y" ] && 5am characters delete "$id" --yes
done
```

### "Watch webhook events during local development"

```sh
# Terminal 1
ngrok http 4747

# Terminal 2 — feed events into a processor
5am characters webhooks listen "$CHAR" --url https://abc.ngrok.app --port 4747 --json \
  | jq -c 'select(.event=="skill.executed")' \
  | while read -r ev; do echo "skill: $(echo "$ev" | jq -r .skill)"; done
```

### "Conditional logic on auth state"

```sh
if ! 5am whoami >/dev/null 2>&1; then
  case $? in
    2) echo "Not authenticated. Run: 5am login" >&2; exit 2 ;;
    *) echo "5am unreachable" >&2; exit 4 ;;
  esac
fi
```

### "Let a character answer questions about this server's traffic"

```sh
# One-time: schema + first ingest (checkpointed) + agent registration
cat > /etc/5am/requests.schema.json <<'EOF'
{"fields":{"ip":"string","method":"string","path":"string","status":"number","bytes":"number","ts":"timestamp"},"time_field":"ts"}
EOF
5am data ingest --dataset requests --schema /etc/5am/requests.schema.json \
  --file /var/log/nginx/access.log --format combined

# Sanity-check what the character will see
5am data query --dataset requests --op count_distinct --field ip --since -24h

# Run continuously (systemd units in production — see docs/server-agent.md,
# or examples/install-agent.sh which writes them for you):
5am data ingest --dataset requests --schema /etc/5am/requests.schema.json \
  --file /var/log/nginx/access.log --format combined --follow &
5am serve agent --name web-1

# Then enable query_server on a character and ask it:
#   "how many unique IPs hit web-1 in the last 24 hours?"
```

## Gotchas (read these before scripting)

- **`--yes` is required to skip confirmation on `delete` commands.** A non-TTY environment will hang without it.
- **Never cron `cat file | 5am data ingest`** — stdin has no checkpoint, so every run re-ingests the whole file and duplicates rows. Use `--file` (incremental) for anything scheduled; stdin is for one-shot pipes only.
- **`5am data ingest --replace` drops the dataset's rows AND its file checkpoints.** It is a full rebuild even when the schema is unchanged — not a "force" flag for appends.
- **`5am serve agent` and `data ingest --follow` block forever.** Run them under systemd (or background them) — they are daemons, not one-shots. Both exit cleanly on SIGTERM.
- **Characters can only query an ONLINE agent** (daemon polled within 90s). Offline agents fast-fail with `agent_offline` — the character will say so; it is not an error in your setup.
- **`stats` requires a `number` field; `latest`, `--since`/`--until`, and `prune` require the dataset's `time_field`.** Datasets without a time field still support count/count_distinct/group_by/stats.
- **Destructive custom skills are refused by the headless agent** (`destructive_refused`) unless it runs with `--allow-destructive` — the interactive confirm prompt from `characters chat` does not exist in the daemon.
- **Album delete cascades to media. Character delete cascades to token, webhooks, interactions, and memory.** Both are irreversible.
- **Paid direct shares and public-link sharing are mutually exclusive on the same album.** `5am albums public-link enable` returns 400 (exit 3) if the album has any paid direct shares; adding a paid share to an album with public sharing on is also rejected. To switch modes, disable the conflicting side first.
- **`5am albums unshare --user` is rejected for contributors.** If the recipient uploaded media to the album, the unshare returns 400 with `"You cannot unshare someone who contributed to the album."` Reassign or delete their media first.
- **`5am albums share` max 20 recipients per call.** Exceeding returns 400. Split into batches in a loop for larger sets.
- **`characters update --active false` is a soft kill at the token-lookup layer.** Already-issued 15-minute CLI JWTs stay valid until they expire — do not assume "active=false" instantly invalidates active sessions.
- **`webhooks rotate-secret` invalidates the old secret immediately.** Update the receiver *before* rotating in production, or you will drop deliveries.
- **`webhooks test` does not increment `error_count`** and bypasses `is_active` / `allowed_actions` — it tests connectivity, not policy.
- **`media list` returns paginated JSON.** Inspect for pagination keys; do not assume the first response is the full set when listing large albums.
- **`5am characters skills execute` denials are returned in the JSON body**, not as non-zero exit. Always `jq` for an `error` / `denied` field.
- **Skills enabled via `--skills` flag use defaults.** If the user wants per-skill config (e.g., a skill that takes its own API key, model, or limits), use `--from-file`.
- **The CLI does not bundle a tunnel.** `webhooks listen` requires the user to run `ngrok`, `cloudflared`, or equivalent in another terminal first.
- **Generation commands need `5am keys set <provider>` to be configured first.** A missing key surfaces as a 4xx (exit 3), not a 5xx.
- **`media generate image --model` is validated against the three Gemini image models** (`gemini-2.5-flash-image` default, `gemini-3.1-flash-image`, `gemini-3-pro-image`); anything else exits `3` with the accepted list. The `--aspect-ratio`, `--resolution`, `--image`, `--grounding`, and `--grounding-images` flags are **Gemini-only** (the OpenAI provider ignores them). `--resolution` is honored only by the 3.x models — `gemini-2.5-flash-image` is fixed at 1024px — and `--grounding-images` only by `gemini-3.1-flash-image`.
- **`local_ffmpeg` args must be a JSON array of strings**, not a single space-separated string. `{"args": ["-i", "in.mp4", "out.mp3"]}` works; `{"args": "-i in.mp4 out.mp3"}` is rejected with a hint. Pass each token as its own array element so filenames with spaces are preserved.
- **`5am media generate video --model` is validated** against the Veo 3.1 models (`veo-3.1-generate-preview` default, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`); a bad value exits `3` with the list. `--last-frame` requires `--image`; `--reference-image` cannot combine with `--image`/`--last-frame` — both rejected before any API call. Veo is long-running (minutes) and synchronous; clips are ~8s, so use `5am media concat` to build longer videos.
- **`5am media concat` needs ≥2 clips and a local ffmpeg.** Same `--ffmpeg`→`$FFMPEG`→PATH resolution and install-hint behavior as `media visualize`. Default is stream-copy with an **automatic re-encode fallback** (it logs `stream-copy concat failed, retrying with re-encode...` to stderr and retries) — so a `copy`-vs-`reencode` result in the JSON `mode` field tells you which path ran. `--audio` muxes a track over the joined video with `-shortest`, so output length is the shorter of video/audio.
- **`5am media visualize` depends on a local ffmpeg binary.** Looks up `--ffmpeg` → `$FFMPEG` → PATH. A missing binary surfaces as exit 1 with platform-specific install hints (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Linux, `winget install ffmpeg` on Windows) — don't auto-install on the user's behalf; suggest the hint and let them confirm. HEIF covers are rejected client-side; convert with `5am media convert` first.
- **`5am media visualize` watermarks unauthenticated runs.** A small "Powered by 5AM" overlay is added in the bottom-left corner if there's no token configured (no `5am login`, no `$5AM_TOKEN`). To remove: `5am login` (free). Rendering works fully offline either way. The JSON result includes `"watermark": true|false` and `"loggedIn": true|false`; branch on those if you need to know what shipped.
- **`5am media visualize --aspect` precedence.** `--aspect 16:9|1:1|9:16` picks canonical dims (1280x720 / 1080x1080 / 1080x1920). Explicit `--width` AND `--height` together override `--aspect`; passing only one side derives the other from the aspect ratio (always rounded to even so libx264 yuv420p is happy). Unknown aspect strings reject before any ffmpeg call.
- **`read_file`/`write_file` are sandboxed to CWD by default.** Out-of-workspace paths force an interactive `[y/N]` prompt **even with `--auto-approve`** — non-TTY scripts will block. Either run the CLI from the right directory, or pass `--allow-outside-workspace` (or set `5AM_ALLOW_OUTSIDE_WORKSPACE=1`) when the user has opted in.
- **Destructive-command detection cannot be bypassed.** `--auto-approve` skips approval for benign skills only; `rm`, `dd`, `mkfs`, `sudo rm`, redirects to `/dev/sd*`, `chmod -R`, etc. always prompt. The same screen applies to `local_ffmpeg` and to custom skills (`run` mode after `{{placeholder}}` expansion; `shell` mode on the command string — its args pass as env vars, never `{{}}`-expanded). For unattended workflows that legitimately need destructive commands, there is no escape — restructure the workflow to avoid them or have the user run interactively.
- **`5am characters create` returns `cli_token` (plaintext) exactly once.** Capture it from the response JSON before any subsequent command — the server stores only a hash and there is no recovery API. If you need a tokenless character (e.g., script-only, web-driven later), use `--no-token`.
- **`--system-instruction-file` accepts only `.md` and `.txt`** (case-insensitive). Other extensions error out client-side; max size 256 KB. Mutually exclusive with `--system-instruction`.
- **`5am playground task` is synchronous and blocks for the entire orchestration.** Long workflows tie up the terminal. For unattended scripts, run in the background or use `--no-stream` and tail `sessions get` separately.
- **Auto-approve creates persistent characters.** `--auto-approve-proposals` mints real characters in the user's account every time the orchestrator proposes one. Always pair with `--max-new-characters N` (default 3) so a single task can't spawn unbounded characters. Beyond the cap, remaining proposals are auto-rejected with a reason. Multi-stage proposal flows are handled in-loop with a defensive 5-stage cap.
- **Without `--auto-approve-proposals`, tasks pause on proposals.** `task` POST returns `status: "awaiting_approval"` with a `proposals` array. Resolve in the web UI, then call the REST `/sessions/:id/resume` endpoint (no CLI subcommand yet) — or just re-run `5am playground task` with the same prompt.
- **Promote/demote orchestrators with `5am characters update <id> --orchestrator true|false`.** Or set the flag at create time with `--orchestrator true`. If `5am playground orchestrators` returns `[]`, that's the fix.
- **Playground writes (sessions create, task, feedback, proposals approve/modify/use-existing, resume) require a paid plan.** Reads, deletes, metadata writes (`sessions update`), and proposal `reject` work on free plans so lapsed users keep cleanup access. 402 with `error: "paid_plan_required"` and `upgrade_url` for gated calls.

## When to suggest `--pretty`

Only when the user explicitly asks to *see* the data ("show me my albums"). For any further processing (counting, filtering, piping to another command), use the default JSON output and `jq`.

## Useful env vars

- `5AM_TOKEN` — auth token (overrides stored login)
- `5AM_BASE_URL` — API base URL override
- `5AM_PRETTY=1` — globally enable `--pretty` output
- `5AM_SHELL` — shell binary used by the local `run_command` skill. Defaults to `$SHELL` on Unix (falling back to `sh`, then `bash`) and `cmd.exe` on Windows. Override with an absolute path when running inside minimal containers (e.g. Alpine without bash).
- `5AM_ALLOW_OUTSIDE_WORKSPACE=1` — equivalent to `--allow-outside-workspace` on `chat`. Lets `read_file`/`write_file` skip the interactive prompt for paths outside CWD. Only use with explicit user consent.

See the CLI's `.env.example` for the full list and precedence rules.
