---
name: 5am
description: Reference for the `5am` CLI — the command-line client for the 5AM app. Use when the user asks to upload/download/organize media, manage albums, generate AI media (image/video/music/audio), generate AI video clips (gemini-omni-1.1-flash, which replaced Veo), concatenate/join video clips, cut a long video into short clips for Shorts/Reels/TikTok (subtitles + AI titles burned in), build an AI highlight reel from a talk, transcribe a video or podcast, build a memory collage / photo-montage / slideshow video (Ken Burns + crossfades, optional Lyria music), generate and render reusable image-edit recipes (IEDL, masked adjustments, presets, and AI edits), AI smart-crop photos to a pixel size or aspect ratio (subject detection keeps faces in frame), make motion graphics films from a brief (kinetic type, counters, charts, photos; Motion Studio's engine; free stills and contact sheets, 20-credit MP4 export), render a podcast WAV into a video (waveform overlay OR AI b-roll with the episode audio), mix a voice track over background music with automatic ducking (broadcast-style bed staging + EQ pocket), create or chat with AI characters, manage character webhooks, run multi-character orchestration in the Playground, read the sales pipeline a character keeps and drive its outreach approval queue, run a clip-outreach batch (one personalized Motion clip per prospect from a CSV, drafts staged in the pipeline, reviewed on a local page, sent from the user's own Gmail), or do anything via the `5am` binary. Trigger on phrases like "upload to 5am", "5am album", "5am character", "list my albums", "generate an image with 5am", "generate a video with 5am", "veo video", "concatenate video clips", "join veo clips", "veo video with podcast audio", "turn this video into shorts", "make tiktoks from", "make reels from", "cut this into clips", "short clips from a long video", "clip maker", "5am studio", "highlight reel", "summarize this video into a reel", "transcribe this video", "burn in subtitles", "memory collage", "photo montage video", "slideshow video", "ken burns", "collage with music", "smart crop", "crop to aspect ratio", "crop for Instagram", "keep faces in the frame", "recrop photos", "5am chat", "5am webhook", "5am playground", "scheduled task", "character runs daily", "autonomous character", "orchestrator", "multi-agent task", "wrap audio as video", "render waveform", "podcast to mp4", "duck music", "audio ducking", "music bed under narration", "mix voice over music", "motion graphics", "kinetic typography", "animated title video", "launch film", "motion design", "5am motion", "motion studio", "5am pipeline", "sales pipeline", "outreach drafts", "approve the draft", "5am outreach", "clip outreach", "a clip for each prospect", "prospects csv", "send from my gmail".
when_to_use: User mentions the `5am` CLI, the 5AM Media Hub, 5am.app, or wants to perform any media-hub action from the terminal. Also invoke when the user pastes a `5am ...` command and asks for help, or asks to script against the hub.
---

# 5am CLI Reference

The `5am` binary is a Go CLI for the 5AM Media Hub (`https://5am.app`). It is **JSON-by-default** on stdout and **agent-optimized** — pipe to `jq`, check exit codes, no interactive prompts unless explicitly invoked.

## Operating principles

- **stdout = JSON, stderr = progress/footers.** Always pipe stdout to `jq` when consuming output. Never grep stderr for results.
- **Exit codes are meaningful** — branch on them: `0` ok, `1` generic, `2` auth (401/403/missing token), `3` validation (4xx), `4` network/timeout, `5` server (5xx), `6` CLI version below the supported floor (run `5am update`).
- **Errors are JSON on stderr**: `{"error", "category", "hint"}`. Category `credits` means AI credits stopped the command (exit `3` when they ran out, `5` when credits are paused platform-wide); its `credits` object says `reason` (`exhausted` | `paused`), `needed` / `available` (credits, when known) and `export: true` for an export, which a Gemini key does not pay for. Tell the user; never retry it in a loop. Category `network` with an error that starts "the network proxy at … refused to connect to 5am.app" (exit `4`) means this computer's own proxy (`HTTPS_PROXY`, an agent sandbox's egress) blocked the request before it left: 5AM never saw it, so neither your token nor the account is the problem. Tell the user the computer's network has to allow 5am.app; it is not an auth failure, and `5am login` will not fix it.
- **Auth is required for almost every command.** Local image-edit validation, inspection, and local-only rendering/batching need no login; recipe generation uses normal Gemini access, and library-backed AI edits require auth. If `5am whoami` fails with exit 2, run `5am login` (or set `5AM_TOKEN`) before anything else.
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

`whoami` nests the account under `user` — the email is **`.user.email`**, not a
top-level `.email`, and reading the wrong key yields a silently empty string
rather than an error:

```json
{
  "user": { "id": "1176...", "email": "you@example.com", "name": "Your Name" },
  "auth_method": "cli",
  "scopes": ["read", "write"],
  "token_id": "459830b3-..."
}
```

```sh
EMAIL=$(5am whoami | jq -r .user.email)
SCOPES=$(5am whoami | jq -r '.scopes | join(",")')
```

Token sources (in precedence order):

1. `--token` flag on `login`
2. `5AM_TOKEN` env var
3. Stored credential from `5am login`

Base URL override (default is baked in at build time):

```sh
5am --base-url http://localhost:8080 whoami
5AM_BASE_URL=http://localhost:8080 5am whoami
```

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
5am albums delete <albumId> --yes                  # admin scope; refused (400, exit 3) while the album has media; --yes required in scripts
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

# Public link — separate subcommands. Returns publicUrl, the link to post
# (https://5am.app/album/<id>?shareToken=<token>), plus publicShareToken.
# Viewers without a 5AM account sign up (free) before the album opens.
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

# "Everything added since X": filter server-side with --added-after /
# --added-before (ISO 8601). These filter UPLOAD time — when the item entered
# the library — not the EXIF capture date; results page newest-upload first.
# The server rejects an unparseable date (400) rather than silently ignoring
# the filter.
5am media list --added-after 2026-08-01
5am media list --added-after 2026-07-02 --added-before 2026-08-01 --type image

# Listing is PAGED, with or without --album: 20 per call by default. A bare
# `media list` returns ONLY the newest 20 — a script that filters the whole
# library client-side over it silently misses the rest. Prefer the date
# window above to narrow server-side; to walk more, pass --limit (server
# caps at 100) and step --offset until a call returns fewer than the limit:
5am media list --limit 100
5am media list --limit 100 --offset 100

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

# Edit a media item's metadata. Only the flags you pass change; omitted fields
# are left alone. Clearing is explicit (--clear-*), never an empty string.
# Changing --description re-indexes the item for SEMANTIC search in the
# background (the JSON result reports `reembedding`); lexical search updates
# immediately either way.
5am media update <mediaId> --tags "Instagram, Vertical"
5am media update <mediaId> --description "a 30s vertical cut of the product demo"
5am media update <mediaId> --name "demo-vertical.mp4" --date-taken 2026-08-10T09:00:00Z
5am media update <mediaId> --clear-tags

5am media delete <mediaId> --yes

# A no-login page for one VIDEO (https://5am.app/c/<token>): the link to send
# someone without a 5AM account. Private by its token and never indexed.
5am media public-link enable <mediaId> --title "Clip for Sam" [--preview <gifMediaId>]   # idempotent; prints publicUrl (send that) and previewUrl (the GIF for an email)
5am media public-link get <mediaId>                 # link, preview, counts (views, opens, plays, shares, downloads, clicks, sign-ups), text, the episode link, items, publish state (`indexable`), `claimed`/`role` (the prospect who claimed the page edits it beside the creator)
5am media public-link disable <mediaId>             # the old link stops working at once

# The same page, PUBLISHED: a readable URL (https://5am.app/clips/<slug>), a template,
# text search engines read, extra media beside the clip. A page ranks only when
# published, and publishing is a deliberate act: publish only pages meant for the
# public, never a prospect's outreach page (the outreach flow never publishes).
5am media public-link set <mediaId> --template episode --headline "Ten minutes on Rust tooling for Python developers" \
  --description "What ruff, uv and Polars change for a Python team in 2026, in one clip." --body-file page.txt \
  --item <imageId>:"The cold open" --item <videoId>       # only the flags passed change; --item replaces the list (max 12); --clear-items empties it
5am media public-link set <mediaId> --source-url https://pod.example/ep/41 --source-title "Episode 41: ..."   # what the clip is about: the page links back to it, the writer writes about it
5am media public-link draft <mediaId> [--notes "show notes..."|--notes-file notes.txt] [--apply]   # Gemini writes headline, description, body (300+ chars) ABOUT the episode/show (source link + notes; the clip is only the teaser); --apply saves (never publishes); spends Gemini access
5am media public-link publish <mediaId> [--slug rust-for-python-devs]   # needs headline >= 10, description >= 40; indexable (sitemap, no noindex) only once body >= 300 chars (`indexable` in the answer); slug_taken -> pick another --slug
5am media public-link unpublish <mediaId>            # leaves search again; the slug is kept, so publishing again restores the URL

# AI video editing. Two DIFFERENT jobs — see the sections further down.
#   clips     → N standalone shorts from one video (subtitles, titles, 9:16)
#   highlight → ONE composed reel summarizing the whole video
# Never loop `highlight` to produce several clips: `clips` does it in one
# transcription and one model call.
5am media clips talk.mp4 --count 5 --aspect 9:16 --style bold
5am media clips rally.mp4 --visual                              # pick from frames, not speech
5am media highlight talk.mp4 --output reel.mp4 --target-duration 60
5am media transcribe talk.mp4                                   # → talk.transcript.json

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

# AI smart-crop a photo (photos only, pure Go, no ffmpeg): Gemini Vision
# locates the main subject and the crop keeps it fully in frame. Same detector
# and on-disk subject cache as `media collage --smart-crop` (shared hits;
# override the cache path with --cache). Needs a Gemini key.
#
# Target — exactly one of:
#   --size WxH    exact output pixels: crop to that aspect around the subject,
#                 then scale (upscales small sources with a warning). Add
#                 --no-scale to cut a literal WxH window (error if src smaller).
#   --aspect W:H  any integer ratio (4:5, 3:2, ...): largest matching region
#                 at native resolution, never resampled.
# --clue "free text" optionally steers the detector; it overrides the default
# face-first preference ("focus on the red car", "keep both people").
# No subject found / detection failed → heuristic crop (centered X, top-biased
# Y), never aborts. AGENTS: always pass --size/--aspect — on a TTY missing
# flags prompt interactively, headless they error.
5am media smartcrop photo.jpg --clue "make sure faces are in the frame" \
  --size 1080x1350 --output crop.jpg
5am media smartcrop photo.jpg --aspect 4:5 --output crop.jpg
# Batch (multiple paths, --folder, or --album): files land in --output-dir as
# <name>-smartcrop.<ext>; per-file failures don't abort the batch.
5am media smartcrop --folder ./photos --aspect 1:1 --output-dir ./cropped
5am media smartcrop --album "Trip 2026" --size 1080x1350 --output-dir ./cropped
# PNG/JPEG/WebP in, same format out (--quality = JPEG only, default 90).
# HEIF/HEIC → `media convert` first. JSON result per file: input, output,
# format, sourceWidth/Height, crop {x,y,width,height}, outputWidth/Height,
# subject ("detected"|"heuristic"), upscaled, status (batch prints an array).

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
- **`--new-album` creates an album EVERY time it runs — never put it inside a per-item loop.** Uploading N files with `--new-album "Deliverables"` in the loop body creates N albums all named "Deliverables". Create-or-reuse ONCE up front (`5am albums list` to find it, `5am albums create` if missing — or `--album <name>`, which resolves an existing album by name), then upload with `--album <id>`.
- **Batch uploads.** `media upload` takes MANY paths in one invocation (plus `-r`, globs and `--concurrency`); uploading a processed batch is ONE command, not a per-file loop. One call per file forfeits the CLI's own parallelism and multiplies startup/auth overhead.
- Bare directory args require `-r/--recursive` — without it the command errors with a hint.
- Glob expansion: the shell expands first; the CLI also globs anything that survives. Quote the pattern (`'./photos/*.jpg'`) to force CLI-side globbing.
- `--include` / `--exclude` take comma-separated globs matched against the **basename** only. Exclude beats include. Hidden files (`.DS_Store`, `.git/...`) are always skipped during recursive walks and `*` glob expansion.
- Explicit file args bypass `--include` / `--exclude` filters — if you name a file directly, it uploads.
- Per-file progress lines stream to **stderr**; the final JSON manifest is on **stdout**.
- `--concurrency` defaults are conservative; bump to 8–16 for many small files.
- Videos use a presigned-URL flow internally. Video/audio ≥ 64 MB goes up as 16 MB multipart parts, several in parallel per file (`--part-concurrency`, default 4).
- **Interrupted multipart uploads resume**: re-running the SAME upload command within ~6 days reuses already-uploaded parts, the transcoded proxy, and a captured `--describe` result — only missing parts move. Never tell a user to delete `~/.5am/uploads/` after a failed large upload; that's the resume state.
- **`--describe` generates an AI description at upload time**, computed locally with the user's Gemini key. Requires a configured Gemini key, plus ffmpeg when the batch has video/audio (the command fails fast if a prerequisite is missing); a describe failure warns but never fails the upload. Opt-in because it spends the user's Gemini quota.
- **Videos up to 10 GB are CLI-only** (web/mobile cap at 2 GB) and **require a Premium or Ultra plan** — the backend rejects >2 GB videos with `402 paid_plan_required` before any byte moves. Anything **over 2 GB also requires ffmpeg locally** (`--ffmpeg` / `$FFMPEG` / PATH): the server doesn't transcode files that large, so the CLI extracts the poster + metadata itself and — when the source isn't web-safe (HEVC/10-bit/4K/non-AAC/.mov) — encodes a 1080p H.264 playback proxy before uploading the untouched original plus derivatives. Without ffmpeg, a batch containing a >2 GB video fails fast with an install hint. File-level concurrency auto-drops to 1 for such batches (one transcode at a time) unless `--concurrency` is set explicitly.

Update notes (`media update`):

- **Owner-only.** A sharee with write access can add media to an album but cannot rewrite the owner's metadata (403).
- Editable: `--name`, `--description`, `--tags`, `--date-taken`. Anything else in the body is ignored, and a request with no editable field is a 400 — you cannot move an item between albums this way (use `media move`).
- **Only the flags you pass are written.** Setting tags never blanks the description by omission.
- **An empty value is rejected, not treated as "clear"** — `--description "$SUMMARY"` with an unset shell variable is a normal scripting accident, and silently wiping a description over it is not a failure mode worth having. Use `--clear-description` / `--clear-tags` / `--clear-date-taken`.
- Tags are normalized the same way the AI classifier normalizes them (trim, dedupe, `, `-joined), so hand-set and AI-set tags are indistinguishable downstream.
- Changing the description enqueues a **re-embed** so `media semantic-search` reflects the edit; it lands within seconds-to-minutes, not instantly. Editing tags or the name does not re-embed (it would spend Gemini quota for nothing).

Download notes:

- `albums download` paginates through the album server-side (fixed pageSize=20) and downloads concurrently.
- Output dir is created if missing.
- Filename collisions (two media items with the same `fileName`) get `_<id-prefix-8>` spliced before the extension. Items with no `fileName` save as `<id>.bin`.
- Path-traversal in server-supplied filenames is sanitized to basename — files always land inside `--output`.

## Media generation (text → media)

Requires API keys configured via `5am keys set` (see API Keys). All generators write the resulting file locally **and** return a JSON manifest on stdout (`media generate text` is the exception — it prints the text itself).

**Take the next step's input path from the manifest's `output`, never from the string you passed to `--output`.** `media generate image` corrects the extension to match the bytes the provider actually returned, so `--output cover.png` can write `cover.jpg` — the rename is announced on stderr, and `output` is always the path that exists:

```sh
path=$(5am media generate image --prompt "a cybernetic owl" --output owl.png | jq -r .output)
5am media generate video --prompt "gentle motion" --image "$path" --output owl.mp4
```

Reusing `owl.png` on the second line is the bug this note exists to prevent: it names a file that may never have been written.

```sh
5am media generate image --prompt "a cybernetic owl" --provider gemini --output owl.png
5am media generate video --prompt "a flowing river in autumn" --output river.mp4
5am media generate music --prompt "lo-fi hip hop for studying" --output chill.mp3
5am media generate audio --text "Hello, I am your AI assistant" --voice Puck --output hello.wav
5am media generate text --prompt "Write 3 b-roll scene ideas, one per line"   # → stdout
```

### Gemini image models (Nano Banana) — `media generate image`

The Gemini provider supports all three native image models via `--model`.
Default (when `--model` is omitted) is `gemini-3.1-flash-image`. The model is
**validated** — an unsupported value exits `3` with the accepted list.

| `--model`                          | Nickname        | Notes                                                                          |
| ---------------------------------- | --------------- | ------------------------------------------------------------------------------ |
| `gemini-2.5-flash-image`           | Nano Banana     | Fastest/cheapest. Fixed 1024px — `--resolution` is ignored.                    |
| `gemini-3.1-flash-image` (default) | Nano Banana 2   | Speed/cost balance. Adds 512px + extra aspect ratios + image-search grounding. |
| `gemini-3-pro-image`               | Nano Banana Pro | Professional output, advanced "thinking", up to 4K.                            |

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

### Gemini video model: `media generate video` (`gemini-omni-1.1-flash`)

One model, `gemini-omni-1.1-flash`, through the Gemini Interactions API (it
replaced the Veo 3.1 previews, which Google turns off on 2026-10-22).
`--model` defaults to it; a retired `veo-*` id is accepted and mapped to it
with a note on stderr; anything else exits `3`. Each call makes ONE clip of
`--duration` 4, 6, 8 (default) or 10 seconds, in about half a minute at 720p,
for about $0.10 per second of 720p. Generate several and join them with
`media concat` (below).

Parameters: `--aspect-ratio` (`16:9` default / `9:16`), `--resolution`
(`360p`/`720p` default/`1080p`/`4k`; the last two are upscaled), `--duration`
(`4`/`6`/`8`/`10` seconds), `--negative-prompt` (folded into the prompt as
"Do not include: ..."; the model has no such parameter), and media inputs:

- `--image <path>` — initial/first frame (image-to-video).
- `--last-frame <path>` — final frame for interpolation; **requires `--image`**.
- `--reference-image <path>` (repeatable): subject or style references;
  **cannot** combine with `--image`/`--last-frame`. Name them in the prompt as
  `<IMAGE_REF_0>`, `<IMAGE_REF_1>`, ... to say which is which.
- `--extend <path>`: video extension, continues a clip (`.mp4`/`.mov`/`.webm`)
  of 10 s or less (longer is refused before upload). The clip is uploaded
  through the Gemini Files API first (deleted after). Describe the
  continuation ("Continue the scene: ..."); `--duration` is the length to ADD
  (4/6/8/10), else the model picks 3 to 10 s. `--reference-image` may join it
  to introduce a character or object (`<IMAGE_REF_0>` in the prompt);
  **cannot** combine with `--image`/`--last-frame`. Appends at the end only;
  no new dialogue on an uploaded clip where someone talks. Google refuses
  edits of uploaded videos in the EEA, Switzerland and the UK.
  Frame/reference images must be `.png`, `.jpg`/`.jpeg`, or `.webp`.

```sh
5am media generate video --prompt "a river" \
  --aspect-ratio 16:9 --resolution 1080p --duration 8 --output river.mp4
5am media generate video --prompt "slow zoom out" --image start.png --output clip.mp4
5am media generate video --prompt "she fades" --image first.png --last-frame last.png --output interp.mp4
5am media generate video --prompt "track the butterfly into the garden" \
  --extend butterfly.mp4 --output butterfly-extended.mp4
5am media generate video --prompt "x" --last-frame end.png            # error: --last-frame requires --image
5am media generate video --prompt "x" --image a.png --reference-image b.png  # error: mutually exclusive
5am media generate video --prompt "x" --duration 5                     # error: 4, 6, 8 or 10
5am media generate video --prompt "Continue the scene: the camera pans up" --extend a.mp4 --duration 6  # adds about 6 s
5am media generate video --prompt "Extend this video: have the character in <IMAGE_REF_0> enter and wave" \
  --extend scene.mp4 --reference-image character.png --output scene-extended.mp4
5am media generate video --prompt "x" --extend long-30s.mp4            # error: uploaded clips must be 10 s or less
```

The simple text params (`aspect_ratio`, `duration`, `resolution`,
`negative_prompt`) are also exposed to AI characters via the
`local_generate_video` skill. (Image inputs are CLI-only.)

### Generate text — `media generate text`

`5am media generate text --prompt "..."` generates plain text with a Gemini
text model. Unlike the other generators (which write binary files), the response
goes to **stdout** by default so it can be piped/captured; `--output <file>`
writes to a file instead. Markdown code fences are stripped. Requires Gemini
access (`5am keys set gemini <key>`, or the account's AI credits; see "API
keys").

```sh
5am media generate text --prompt "Summarize in one sentence: ..."          # → stdout
SUMMARY=$(5am media generate text --prompt "...")                          # capture
5am media generate text --prompt "..." --output notes.txt --yes            # → file
5am media generate text --prompt "..." --model gemini-3.1-pro-preview      # pick model
5am media generate text --prompt "Tell me about this instrument" --image organ.jpg  # multimodal (repeatable --image)
5am media generate text --prompt "Summarize this lecture" --file lecture.mp3        # audio/video/PDF via --file (Files API, deleted after)

# LONG prompts: read from stdin. Prefer this whenever the prompt is built from
# a document, a transcript or JSON — argv has an OS size limit and embedded
# quotes/newlines are easy to get wrong.
printf '%s' "$LONG_PROMPT" | 5am media generate text --prompt -
5am media generate text --prompt - < brief.md
```

> `--prompt -` means **read the prompt from stdin**. Passing a long prompt as an
> argv string risks both the OS argument limit and a quoting mistake; with `-`
> the text crosses as bytes on a pipe. Piping nothing is an error rather than an
> empty prompt — an empty prompt gets a generic "How can I help you today?"
> answer, which looks like a working pipeline and is not.

Models (`--model`, default `gemini-3-flash-preview`): `gemini-3-flash-preview`
(fast), `gemini-3.8-flash` (newest flash),
`gemini-3.5-flash-lite` (lightest), `gemini-3.1-flash-lite`,
`gemini-3.1-pro-preview` (strongest). Anything else is refused before the
API call (`internal/textmodels.Supported`). This backs the
transcript-driven scene prompts in `scripts/podcast_to_video.py` — it turns a
podcast transcript into per-scene b-roll prompts so the video tracks the
conversation.

### Join video clips — `media concat`

`5am media concat <clip1> <clip2> [more...] --output combined.mp4` joins clips
via a local ffmpeg (resolved `--ffmpeg` → `$FFMPEG` → PATH, like `media
visualize`). Needs **at least 2** clips. By default it **stream-copies**
(lossless, instant) and **auto-falls-back to re-encode** if the clips' codecs
don't match; `--reencode` forces re-encode. `--audio <file>` lays an audio track
over the joined video (replaces clip audio, `-shortest`), the AI b-roll path for
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
Transcription + edit generation need a Gemini key. Spec:
`cli/docs/VIDEO_EDIT_DSL.md`.

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

### AI short clips — `media clips`

Cut ONE long video into **N standalone short clips** (Shorts/Reels/TikTok
shaped), each with burned-in subtitles and an AI title. One cached
transcription, one Gemini call that picks the strongest self-contained moments
(ranked strongest-first), then a cheap seeked render per clip. Needs a Gemini
key and a local ffmpeg with libass (unless `--style none` or `--visual`).

```sh
5am media clips talk.mp4                                  # 5 clips → talk-clips/
5am media clips talk.mp4 --count 3 --max-clip-len 30 \
  --brief "the product demo moments" --aspect 9:16 --style bold
5am media clips talk.mp4 --aspect source --style none --no-titles
5am media clips rally.mp4 --visual --brief "the best rallies"   # pick from FRAMES, not speech
5am media clips talk.mp4 --new-upload-album "Shorts"      # upload the results
```

**Use `clips`, not a loop over `highlight`.** This is the single most common
mistake when scripting this CLI. `media clips` produces N clips from ONE
transcription and ONE model call; calling `media highlight` N times re-analyses
the entire video N times — on a long source that is minutes of wasted compute
and N× the Gemini spend, for a worse result (highlight composes a _reel_, it
does not produce standalone moments).

Choosing between them:

|              | `media highlight`                        | `media clips`                                                                |
| ------------ | ---------------------------------------- | ---------------------------------------------------------------------------- |
| Answers      | "summarize this video"                   | "mine this video for posts"                                                  |
| Output       | ONE composed reel, many ranges joined    | N separate videos, one contiguous moment each                                |
| Only it does | ducked music bed, normalize, color grade | burned-in subtitles, cover-crop to 9:16/1:1, per-clip title, `manifest.json` |

Flags:

- `--count` 1–10 (default 5) · `--max-clip-len <seconds>` (snapped to sentence
  boundaries) · `--brief "<what to capture>"` · `--aspect source|9:16|1:1|16:9`
  (default 9:16) · `--fit cover|contain` (default cover = center-crop;
  `contain` letterboxes).
- `--style clean|bold|minimal|none` — subtitle look. Subtitles AND titles burn
  via libass, so RTL (Farsi/Arabic) and CJK shape and reorder correctly with
  automatic font fallback; `--font` is NOT needed for titles.
- `--no-titles` · `--upload-album <id|name>` / `--new-upload-album <name>` ·
  `--out-dir <dir>` (default `<video-basename>-clips/`) · `--language <hint>`
  for transcription · `--force-transcribe` to bypass the transcript cache.
- `--visual` — select from the video's **frames** instead of its speech: a 360p
  copy goes to Gemini and moments come back as time ranges. No transcript, no
  burned-in subtitles, no libass needed. For footage that is about what is on
  screen (sport, pets, reactions, b-roll). **Applied automatically** when a
  source has no audio or its speech is too sparse — `clips` falls back rather
  than failing, so a silent video still produces clips.

Outputs, per clip, in `<name>-clips/`: `clip-NN.mp4`, `clip-NN.srt`, and an
editable `clip-NN.vedl` (one cut, optional title, edge fades). Plus
`manifest.json` and `transcript.json`. To adjust a cut point or retitle, edit
the `.vedl` and `5am media edit render clip-01.vedl --output better.mp4` — no
AI call.

Transcriptions are cached (`~/.5am/transcripts`), so re-running with a
different `--brief` or `--count` skips the paid call — and `highlight` and
`clips` on the same video share one transcript.

### Clip Maker companion — `5am studio`

The web Clip Maker (`<base-url>/clip-maker`) drives the `media clips` pipeline
on the USER'S machine through a loopback-only companion server. The source
video never uploads, which is what keeps the feature free.

```sh
5am login && 5am studio          # then open <base-url>/clip-maker
5am studio --dir ~/Videos --port 5200 --keep-days 14
```

Agent-relevant facts: loopback only; accepts connections solely from 5am.app
pages (and localhost in dev) signed into the **same account** as the CLI; lists
videos from Movies, Desktop and Downloads plus any `--dir`; finished jobs
survive a restart. Safari cannot reach loopback from an https page — tell the
user to use Chrome, Edge or Firefox. Full protocol + security model:
`cli/docs/STUDIO.md`.

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

## Motion Studio films — `5am motion`

Motion graphics from a brief: kinetic type, shapes, counters, charts and the
user's photos, cut on a beat grid with a composed score, by the web Motion
Studio's own engine. A film is a MotionDoc JSON file (`*.motion.json`). Needs the
image-edit runtime (`5am update --runtime-only`, which also installs Skia, the render
engine, with npm) and Node.js 20+; `stills`, `sheet` and `render` also need ffmpeg (so
does `--clip`, which Skia reads through ffmpeg's ffprobe). Chrome/Chromium is needed
only for the `--engine chrome` rollback and to probe the video clips of a `preview`
(which plays in the default browser). `5am motion doctor` checks the engine renders
use (Skia unless `FIVEAM_MOTION_ENGINE=chrome`) and fails only on that one; it reports
the other in its JSON (`chrome: {ok, path, error}`, `skia: {ok, nativeCanvasVersion,
error}`).

```sh
5am motion generate --brief "A 10 second launch film for a coffee app" --format 9:16 --duration 10 -o coffee.motion.json
5am motion revise coffee.motion.json "warmer colours, slower ending" -o coffee-v2.motion.json   # or --in-place
5am motion narrate coffee-v2.motion.json --script "Mornings, sorted. Order ahead." --voice Kore
5am motion lint coffee-v2.motion.json
5am motion sheet coffee-v2.motion.json -o coffee.png --count 24
5am motion stills coffee-v2.motion.json --times 0.5,4 --out-dir stills
5am motion render coffee-v2.motion.json -o coffee.mp4 --dry-run
5am motion render coffee-v2.motion.json -o coffee.mp4 --fps 30 --new-album "Films"
5am motion finalize <requestId>
5am motion finalize --unfinished    # release the reservations of renders that stopped partway
```

| Command | Costs | Prints |
|---|---|---|
| `generate`, `revise` | Gemini access: 1 call, 2 with a layout repair | `output` (the film file), `title`, `format`, `duration`, `scenes`, `photos`, `calls`, `repaired`, `fixes`, `issues`, `warnings` |
| `narrate` | Gemini access: 1 speech call (made even when the take is refused) | `output` (the `.narration.json`), `audio` (the WAV), `duration`, `filmDuration`, `voice`, `mood`, `model` |
| `lint` | free, offline | `fixes`, `issues` (level `fix`/`note`), `warnings`, `frames`, `width`, `height`, `fonts`, `hash` |
| `stills` / `sheet` | free (watermarked) | `files` / `output`, `frames` |
| `render` | **20 AI credits** per export, every account (a personal Gemini key does NOT exempt it) | `output`, `requestId`, `credits`, `frames`, `fps`, `width`, `height`, `audio`, `bytes`; with `--dry-run`: `dryRun: true` and no `output` |
| `finalize` | pays a kept render (no second charge if already paid) | as `render`; without an id, a JSON ARRAY of kept renders, each with `state` (`rendered`: pay it; `rendering`: another process is on it; `stopped`: killed partway, nothing to pay) and `next`; `--unfinished` releases the stopped ones' reservations: `released`, `kept`, `failed` |
| `preview` | free | `url`, then runs until Ctrl-C: **never run it unattended** (use `sheet`) |
| `fonts` | free | `dir`, `fonts`, `bytes` |

Agent rules:
- **Iterate on the film, not the MP4.** `lint` and `sheet` are free; use `revise`
  for changes and `render` once at the end. Look at a sheet before rendering: the
  lint cannot see contrast.
- **`fixes > 0`** after `generate` is worth a `revise` that names the issues; the
  film still renders.
- **Never render twice to recover a failure.** `render` loads every font and photo
  before charging (a refusal at that point renders nothing). If the final charge
  is refused, the MP4 is kept for 24 hours and the error names
  `5am motion finalize <requestId>`: run that after the user buys credits. A
  second `render` is a second export.
- **Never kill a render.** Every render reserves its export before the first
  frame and pays after the last; an account may hold 10 unpaid reservations.
  Ctrl-C (SIGINT) or SIGTERM stops a render and releases its reservation, but a
  killed process (SIGKILL, a command timeout that kills, a VM restart) keeps it
  for 24 hours. Give renders time to finish (about a minute or two each; run a
  long batch in the background and check on it) rather than a short timeout.
  On `too_many_pending_exports` (429), the error says how many are held and when
  the oldest clears: run `5am motion finalize` to see this machine's,
  `5am motion finalize --unfinished` to release the stopped ones, and
  `finalize <requestId>` for a `rendered` one; never retry `render` in a loop.
- **Photos:** `--photo <file>` (JPEG, PNG, WebP, GIF, HEIC) or `--photo media:<id>`,
  up to 12. On `revise`, `--photo` REPLACES the film's photos. Local photos are
  stored as `file:<path relative to the film>`: keep them beside the film.
  Local photos are described with Gemini once (cached) unless `--no-describe`.
- **Video clips:** `--clip <file>` or `--clip media:<id>`, up to 4, on `generate`
  and `revise` (where it REPLACES the film's clips). Needs the server's video flag
  (`video clips in Motion films are not enabled on this server` otherwise). Skia
  reads clips through ffmpeg (ProRes and HEVC included); with `--engine chrome`,
  clips Chrome cannot decode get a cached ffmpeg proxy automatically.
- **Narration:** `narrate` writes `<film>.narration.wav` + `.narration.json` beside
  the film; lint, stills, sheet, preview and render use them (`--no-narration` to
  leave them out). Settle the film's length first: a take longer than the film is
  refused, never cut (about 45 to 65 words per 30 s). A new take means a new export
  hash. After `revise --in-place` the old take still plays: narrate again with
  `--overwrite` if the words changed.
- **Formats** 16:9, 9:16, 1:1; **duration** 6 to 60 s; `--fps` 60 or 30;
  `--resolution` 1080p or 1440p. With Skia, a 15-second 9:16 film (1080x1920) took
  42 to 54 s at 60 fps and 33 s at 30 fps on an Apple M1 Max with other work running
  (17 to 22 frames a second at 60 fps); allow longer on small machines.
- **Tokens:** `render` needs write scope; an AI character's token is refused for
  exports even with write scope.
- **Engine:** Skia by default; `--engine chrome` (or `FIVEAM_MOTION_ENGINE=chrome`) is
  the only alternative, a rollback. There is no `auto` (`unknown motion engine "auto":
  use skia or chrome`). Nothing falls back: on `Skia isn't installed: <reason>. Run
  \`5am update --runtime-only\` again, or render with --engine chrome.` run
  `5am update --runtime-only` (it prints the `skia` object: `installed`, `package`,
  or the `error` that stopped it, and exits non-zero when Skia could not be installed
  although the runtime was), then render again; nothing was charged.
- **Cloud workflow runs** have the runtime, Skia and every font preinstalled
  (`FIVEAM_MOTION_FONTS`); render there like anywhere else.
- **Not supported:** Ad Maker's unmarked export (every CLI render carries the
  "Made with 5AM.app" mark), sending a film to the web studio.

Full guide and sample films: https://github.com/digvan/5am-cli/blob/main/docs/motion.md

## Gemini from the CLI

```sh
5am ai ask --prompt "Which year did the Talk Python podcast start?" --search        # grounded in Google Search: text + sources[] {title,url,domain} + queries[]
5am ai ask --prompt-file question.txt --json [--search] [--system "Answer tersely."] [--model gemini-3.8-flash] [--thinking low|medium|high]   # one JSON value, parsed into `json`
```

One question, one answer, on the user's saved Gemini key or their AI credits through the proxy (a credits refusal is category `credits`, exit 3). With `--search` the answer is grounded and the pages it rests on come back as `sources[]`; `grounded` says whether a search informed the answer: Google cited pages, or ran its searches step by step and fed the results into the model's context (such answers, and every JSON answer, carry no citations; the CLI tells by counting the prompt's own tokens, free). False: the model answered from memory, which a caller may trust less. With `--json` the first JSON value in the answer is returned parsed (refused when there is none). `--thinking` sets a Gemini 3 thinking level. A grounded run comes back from Google with no candidate at all now and then (after a minute or more of searching): the CLI tries once more, thinking less, and when that is empty too the error names what came back (`FIVEAM_AI_DEBUG=1` prints the raw responses). Programs that need grounded research can call `5am ai ask --search --json` and verify the returned sources before acting.

## Pipeline: `5am pipeline`

The sales pipeline an AI character (the Sales Director by default) keeps for
its owner: items (prospects), contacts, append-only activities and the
**outreach approval queue**. The character stages email DRAFTS; the owner
approves them and sends from their own mailbox; nothing is sent by the
platform. These commands READ the pipeline and drive the approval loop. Writes
to items, contacts and activities stay with the character's skills
(`5am characters skills execute <id> pipeline_upsert --input '{...}'`), which
`5am outreach prepare` does for you.

```sh
5am pipeline items list                              # {items, stages}; complete (cap 200)
5am pipeline items list --stage researched --search acme
5am pipeline items list --csv prospects.csv          # one row per item with its primary contact
5am pipeline items get <itemId>                      # + contacts, activities, outreach_drafts
5am pipeline outreach list --status staged           # staged | approved | sending | rejected | sent
5am pipeline outreach edit <draftId> --subject "..." --body-file message.txt   # while staged only
5am pipeline outreach approve <draftId>
5am pipeline outreach unapprove <draftId>            # approved -> staged, so the owner can edit and approve again
5am pipeline outreach reject <draftId> --note "too long"                        # the character reads the note
5am pipeline outreach mark-sent <draftId>            # after YOU sent it from your mailbox (or found a sending one in Gmail's Sent folder)
5am pipeline outreach mark-sent <draftId> --sent-at 2026-10-10T14:05:00Z   # a send made EARLIER, recorded now (time from Gmail's Sent folder)
5am pipeline outreach release <draftId>              # a sending draft that is NOT in Gmail's Sent folder: back to approved
```

**Bulk review.** `approve`, `unapprove`, `reject` and `mark-sent` accept multiple
IDs, `--batch <slug>`, or `--ids-file <file>` (one source); `--ids-file -` reads
stdin. `--dry-run` lists IDs without mutation or checking their server states.
Each result reports success/failure and a partial failure exits nonzero. Batch
selection includes every saved draft ID, so ineligible states fail individually.
`mark-sent` only records a send that already happened.

```sh
5am pipeline outreach approve --batch oct_week_1 --dry-run
5am pipeline outreach approve <id1> <id2>
5am pipeline outreach reject --ids-file drafts.txt --note "Revise the opening"
5am pipeline outreach mark-sent --ids-file - < sent-drafts.txt
```

- Rows are keyed `id`; the skills call the same thing `item_id` / `contact_id` /
  `draft_id`. An item is open while `closed_at` is null; stage names are the
  character's own vocabulary (`stages` lists them in order).
- A draft moves `staged → approved → sent` or `staged → rejected`;
  `5am outreach send` holds it in `sending` across its Gmail attempt
  (`approved → sending → sent`, back to approved, or `rejected` with the
  `review_note` "Gmail refused the message: <reply>" when Gmail refused it for
  good). A token bound to an AI character may approve, reject or edit drafts
  another character wrote, never its own (403 `own_draft_review_not_allowed`),
  and cannot reserve, release, refuse or mark-sent at all (403
  `cli_token_not_allowed_here`): sending is the owner's. A wrong-state approve,
  reject or mark-sent answers **404** (exit 3), not 409: read the message;
  `release` answers 409 naming the status. `edit` works only while staged, so
  the stored draft is exactly what was sent. Settle a `sending` draft only after
  the person looked in their Gmail Sent folder: never guess.
- **Recording an email that already went out** (sent by hand, or by you from
  the person's Gmail, before the pipeline knew), so duplicate protection and
  `--follow-up` know the prospect was emailed. No film, clip or contact sheet is
  involved: never use `5am outreach prepare` or `draft` for this (they render
  films). With the batch's character:

  ```sh
  5am characters skills execute <characterId> pipeline_query --input '{"mode":"get_item","name":"Acme Podcast"}'   # item_id, contacts[].contact_id, if it exists
  5am characters skills execute <characterId> pipeline_upsert --input '{"entity":"item","name":"Acme Podcast","website":"https://acme.example","contacts":[{"name":"Sam Lee","email":"sam@acme.example","is_primary":true}]}'   # only if it does not
  5am characters skills execute <characterId> stage_outreach --quiet-push \
    --input '{"item_id":"…","recipient_name":"Sam Lee","recipient_email":"sam@acme.example","subject":"<as sent>","body":"<as sent>"}'
  5am pipeline outreach approve <draftId>
  5am pipeline outreach mark-sent <draftId> --sent-at 2026-10-10T14:05:00Z   # the time in the Gmail Sent folder
  ```

  - The subject and body exactly as sent; the address the email actually went
    to (`recipient_email`, or `contact_id` when it was the contact on file):
    duplicate protection is per address.
  - `--quiet-push` skips the review notification a new draft sends the person;
    this one is already out. It is a flag, never a key in `--input`.
  - `--sent-at`: RFC 3339 with a zone (`Z` or `+02:00`); a bare date means noon
    that day. Not in the future, at most 365 days back (`invalid_sent_at`).
  - The draft keeps that time as `sent_at`, so a `--follow-up` counts its gap
    from the real send, and the item's activity shows the email on that day,
    "(recorded on <today>)". Duplicate protection goes by when it was
    RECORDED: an approved draft to that address written before the record
    never sends (`outreach send` closes it as rejected, "Not sent, to avoid a
    duplicate"). Tell the person if one was waiting.
  - `duplicate_draft` from `stage_outreach`: a staged draft to that address
    already waits on the item. Make it the record instead: `5am pipeline
    outreach edit <draftId> --subject "<as sent>" --body-file sent.txt`, then
    approve and `mark-sent --sent-at` it.
  - Approving here is a bookkeeping step, not a review: the words already left.
    Do it only for an email the person confirms went out.
- `--csv` writes `name,title,stage,website,notes,contact_name,contact_email,contact_role`,
  the file `5am outreach prepare --csv` reads; `--overwrite` to replace it.

## Clip outreach: `5am outreach`

One personalized Motion clip per prospect from a CSV, in that prospect's own
album with a **no-login page** (`https://5am.app/c/<token>`, the link to send),
an email draft per prospect staged in the Pipeline, a local review page, and
sending from the user's **own Gmail** after they approved each message. Six
steps on one batch folder (`~/.5am/outreach/<batch>/`); each resumes.
Walkthrough for a person: `cli/docs/OUTREACH_GETTING_STARTED.md`; reference:
`cli/docs/OUTREACH.md`. The page's button is "Claim and publish this page":
the prospect signs up, becomes the page's second editor (`claimed_by`) and
publishes it under their name on their own Gemini access; the sender keeps
editing rights, and the outreach flow itself never publishes a page.

**Sender and templates.** Configure `outreach config set --sender-name --mailbox`
before new batches. The config is saved at `~/.5am/outreach/config.json` and binds
to the signed-in account; `config show --check-account` verifies it. `--mailbox`
is the expected Gmail address, separate from `outreach mail setup` credentials.
`config set --subject --body-file` saves templates (the body file is copied when
configured). Email placeholders are `{{name}}`, `{{show}}`, `{{line}}`,
`{{clip_url}}` and `{{sender}}`; the body must contain `{{clip_url}}`.
`draft --subject`, `--body-file` and `--sender-name` override defaults for new
messages. Saved batch/row templates, text and sender survive retries. A legacy
batch without explicit or saved identity can fall back to the account profile;
use `draft --require-sender` in scripts to require configured or explicit identity.

**Preview and correct.** `draft --dry-run` shows sender, mailbox, subject, body,
clip URL, planned action and validation errors without saving, staging, notifying
or calling a model. It cannot run with `--personalize`. `--refresh-staged`
deliberately replaces existing staged text with current templates; use `--only`
to bound the change. The owner must first return an approved draft with
`pipeline outreach unapprove <id>` (or **Return to review** in the local review
page), then edit and approve again. Unapprove clears the review decision and
can fail if the staged slot is occupied or the 100-draft queue is full. Approved
drafts can also be rejected. Sending/sent drafts cannot be unapproved or edited.
The send command validates and sends the freshly reserved server message.

**Select rows.** `prepare`, `clips`, `draft` and `send` accept
`--only slug,email@example.com`. Unknown selectors fail. Use the same selection
for `clips --dry-run` and the paid run. Prepare matches rows by stable `work_id`
or email across CSV reordering; the CSV validation and batch limits still apply.

**Per-row templates.** Add optional `template_file` paths to the CSV to mix
Motion designs in one batch. Use absolute paths; relative paths resolve from
the CLI's working directory. A blank cell uses the required `--template`
fallback. `prepare --require-row-templates` rejects any row missing that cell,
useful for scripts that assign every design explicitly. Each selected editable
row's template is validated before pipeline item mutations. Batch JSON and
prepare output retain `template_file`, `template_name` (filename stem) and
`template_hash` (SHA-256 of the source JSON, with surrounding whitespace trimmed).
The local review card shows the name and short hash. Completed rows keep their
original template attribution on retries. The CLI uses the choices in your CSV;
it does not randomize them or aggregate results by template. For analysis, join
the saved attribution to `5am outreach stats --batch <slug>` by prospect slug.

**Branding and manual edits.** The CSV's optional `brand_file` is a local JSON
path, containing `colors` (`background`, `text`, `accent`, optional `accent2`,
all `#RRGGBB`), `fonts` (`display`, `body`, Motion font IDs such as `inter`) and optional
`artwork` (`src`, `width`, `height`). Use absolute paths for local files. A Motion
image layer with `photo: "podcast-artwork"` displays that artwork. Colors/fonts
can be supplied without artwork. Prepare auto-fits text down to a floor of 28
for larger text; layers over 160 characters are held without truncation.
Prepare preserves hand-edited films and rechecks lint/contact sheets. If the
source also changed, reconcile the film or deliberately use `--regenerate
--only ...`. Rows with export checkpoints remain intact.

Reusable films should use palette tokens for graphics and omit text `color`
so the renderer chooses a contrasting foreground. A light sample brand is
`{"background":"#F5EEDC","text":"#172A28","accent":"#34806D","accent2":"#C56C45"}`
inside `colors`; fixed hex paint inside layers will not follow it. Motion's
`sound.style` (`minimal`, `pulse`, `house`, `ambient`) supplies synthesized
music and animation cues; `none` silences them. It does not excerpt podcast audio.

**Recover and inspect.** After interruption, rerun `clips` to resume saved
exports/uploads and `draft` to stage rendered rows. Paid checkpoints cost no
new export credits; missing paid files or ambiguous receipts stop for inspection.
Never render the film separately to bypass recovery. Prepare/clips/draft share
a batch operation lock. `clips --progress-file clips.log` appends timestamped
progress; stdout stays JSON and warnings/progress stay on stderr. Use
`tail -f clips.log`, keeping `2>&1` out of JSON pipelines. `motion doctor` checks
that Skia (the render engine) loads, and reports whether Chrome launches, without an
export; Chrome is needed only with `--engine chrome` / `FIVEAM_MOTION_ENGINE=chrome`,
and then prepare/clips take `--browser` (else `CHROME_PATH` or discovery).
See [OUTREACH.md](docs/OUTREACH.md) and the public
[Clip Outreach reference](https://5am.app/cli/docs/outreach).

```sh
5am outreach config set --sender-name "Your name" --mailbox you@gmail.com --subject "A teaser for your podcast: {{show}}"
5am outreach config show --check-account
5am motion doctor                                    # checks Skia (and reports Chrome); no paid export
5am outreach mail setup --address you@gmail.com        # once: Gmail app password (2-step verification on)
FIVEAM_GMAIL_APP_PASSWORD='abcd efgh ijkl mnop' 5AM_DISABLE_KEYRING=1 5am outreach mail setup --address you@gmail.com   # no terminal (an agent): from the environment, or a piped line
5am outreach mail report --subject "Weekly digest" --body-file digest.md   # mails the file to YOURSELF (the stored address, nobody else): the self-report door for unattended programs
5am pipeline items list --csv prospects.csv            # or write the CSV by hand: name[,email,instagram,website,source_url,source_title,observation,inference,line,context,show,site,work_id,brand_file,template_file]
5am motion generate --brief "A 10 second hello for a photographer" --format 9:16 --duration 10 -o template.motion.json
# edit template.motion.json: put {{name}} (and optionally {{line}}) in the title or a text layer
5am outreach prepare --csv prospects.csv --template template.motion.json --batch oct_week_1 --character "Sales Director"
#   -> items created or matched, one film + contact sheet per prospect (FREE). Look at the sheets.
5am outreach clips --batch oct_week_1 --dry-run        # price + toolchain check
5am outreach clips --batch oct_week_1 --yes            # 20 AI credits each; album "Clip for <name>"; public link (headline = line, episode link = source_url); pipeline note
5am outreach clips --batch oct_week_1 --yes --page-text   # + Gemini writes each page's text ABOUT the episode from the context column (spends Gemini access; never publishes)
5am outreach draft --batch oct_week_1 --dry-run        # inspect sender, subject, body and clip before staging
5am outreach draft --batch oct_week_1                  # one staged draft per prospect, the link inside
5am outreach review --batch oct_week_1                 # a page on 127.0.0.1: watch, edit, Approve / Skip, Done
5am outreach send --batch oct_week_1 --dry-run         # the exact messages
5am outreach send --batch oct_week_1 --yes             # from your Gmail; mark-sent on each
5am outreach stats --batch oct_week_1 --record         # views, opens, plays, shares, downloads, clicks, sign-ups per prospect (a sign-up = the prospect claimed the page)
```

| Command | Costs | Needs | Prints |
|---|---|---|---|
| `prepare` | free (Gemini is not called) | the motion runtime with Skia, Node 20+, ffmpeg (Chrome only with `--engine chrome`); a Premium plan and a character with `pipeline_query`, `pipeline_upsert`, `stage_outreach` | per prospect `status` prepared / needs_fix / failed, `sheet`, `credits_needed` |
| `clips` | **20 AI credits per prospect** | the same toolchain; a write-scope token | `rendered`, `failed` (a check: MP4 size, page on), `credits_charged`, `pending_payment`, per prospect `public_url`, `gif`, `preview_url`, `album_id`, `media_id` |
| `draft` | free (`--personalize`: one Gemini chat per prospect) | the character | `drafted`, `held_no_email`, `failed` (a message check), per prospect `draft_id`; `notice` (the review card posted into the character's chat: `interaction_id`, `drafts`, or `error`, retried by the next `draft`; `--no-review-notice` skips it) |
| `review` | free | a person and a browser | blocks until Done; `approved`, `skipped` |
| `send` | free | the Gmail credential; **never in a workflow run** | `sent`, `failed` (not taken by Gmail; still approved, the next run retries), `skipped`, `uncertain`, `refused` (Gmail refused it for good; the draft is rejected, never retried), `stopped` (why the run ended early: Ctrl-C, a failed reservation), `messages[]` (each with `html` when the GIF part was added, `error` naming a failed check, Gmail's reply, or how to settle an uncertain one) |
| `stats` | free | | `views`, `opens`, `plays`, `shares`, `downloads`, `clicks`, `signups` per prospect |

Agent rules:

- **Look before paying.** `prepare` draws a free contact sheet per prospect;
  show them (or their paths) to the user before `clips`. `needs_fix` means a
  layout or input check still needs attention after fitting. Follow the row's
  remedy, edit the film and run `prepare` again. Text over 160 characters must
  be shortened. Never render a `needs_fix` film by hand.
- **Never render twice.** `clips` resumes: a refused charge leaves the row
  `pending_finalize` and the next `clips` run PAYS for the kept render instead
  of rendering again. A second `motion render` is a second export.
- **The person approves and the person sends.** `draft` posts the batch into
  the character's chat with a review card and pushes the person's phone: tell
  them to review there (web or iOS), on the web Outreach tab, or with `review`.
  `review` is for a human at a browser (do not run it unattended; it blocks
  until Done). `send` sends only
  rows the person approved, refuses inside a workflow run, and stops on a
  refused Gmail sign-in. It reserves each draft in the pipeline before Gmail
  sees it, so overlapping runs never send one twice; a closed pipeline item is
  skipped.
- **An `uncertain` row is the person's call.** The connection broke after Gmail
  had the message, so it may have gone. Ask the person to look in their Gmail
  Sent folder, then run `5am pipeline outreach mark-sent <draftId>` (it is
  there) or `release <draftId>` (it is not) as `messages[].error` says. Never
  release one unchecked, and never resend it by hand: that is how a prospect
  gets the same email twice.
- **A `refused` row is closed.** Gmail refused that message for good (a bad
  address, a message it will not take); the draft is rejected in the pipeline
  with Gmail's reply as its note. Tell the person the reply; do not retry it.
- **Links are the only thing in the email.** Every draft carries the prospect's
  clip page once, with campaign labels (`utm_campaign` = the batch slug,
  `utm_content` = `p01`, never a name), and the opt-out sentence. `--personalize`
  output is kept only if it has that one link and nothing else.
- **At most 100 prospects per batch** (`--limit`). The CSV
  is validated and deduplicated; more rows than the limit is an error, not a cut.
- **A second touch needs `--follow-up`.** `prepare` refuses a prospect who was
  already emailed; with `--follow-up` it accepts them only once the last send is
  at least `--min-days-since-sent` days old (3 by default), for a new episode
  or a check-in. Never work around it with another name.
- **An email sent outside a batch is recorded, never drafted again.** When the
  person (or you) emailed a prospect before the pipeline knew, record it with
  `mark-sent --sent-at` (Pipeline, "Recording an email that already went
  out"); then `prepare` treats them as emailed. Running `prepare` and `draft`
  for it renders a film nobody needs and stages a second message.
- **Every step verifies its output; read the `failed` rows.** `clips` checks the
  MP4 and that the page is on, `draft` refuses an unknown `{{placeholder}}` and a
  message without exactly one clip link, and `send` verifies the server draft's
  link and recipient against the batch: a skipped row's `error` says which check
  failed. Fix the cause (shorten a name, restore the link in review), do not
  resend by hand.
- **The email shows the clip.** `clips` makes a GIF of each clip's first seconds
  (`--no-gif` to skip) and `send` adds an HTML part with it linked to the page
  (`--no-html` for text only); the plain-text part is always the draft itself.
- **The film's sign-off is the show's card.** The gallery templates end on
  `{{show}}` (the show's name) and "LISTEN AT `{{site}}`": the CSV's `show`
  and `site` columns, else the name and the website's host, else `5am.app`;
  the renderer's own "Made with 5AM.app" mark sits in the corner. The clip page's own address cannot be in the
  film: it exists only after the render is uploaded.
- **The page links back and can be written for you.** `clips` sets the page's
  headline (the CSV `line`), a one-line description and the link back to what
  the clip is about (`source_url`, titled by `source_title`, else `line`); the
  page shows "Listen to the episode: <title>". `--page-text` (or
  `5am media public-link draft <mediaId> --apply`) has Gemini write the
  headline, description and body ABOUT that episode or show from `context`
  (show notes), never about the clip; it spends the user's Gemini access and
  never publishes. A page is indexable only once its body has 300 characters;
  outreach pages are never published by this flow.

## API keys (third-party providers)

Stored encrypted server-side; used by `media generate` and the local generation skills.

```sh
5am keys list                          # redacted, plus gemini_access / ai_credits (below)
5am credits                            # the AI credit balance and the packs on sale
5am credits buy --pack <id> --no-wait # a payment link for the user (no sign-in needed to pay)
5am keys set gemini <KEY>              # → {"provider":"gemini","status":"updated","stored_locally":true}
5am keys set openai <KEY>
5am keys delete gemini --yes           # → {"provider":"gemini","status":"deleted"}
```

**No Gemini key is needed while the account has AI credits.** Every Gemini
call in the CLI (`media generate`, `describe`, `transcribe`, `clips`,
`highlight`, `smartcrop`, the collage music, `5am studio`, the local skills,
the eval judge) resolves access in this order: `GEMINI_API_KEY` in the
environment (with `GOOGLE_GEMINI_BASE_URL` beside it the key is an AI-credits
proxy token, which is how a cloud workflow run is configured), then the key
stored by `5am keys set gemini`, then the account: its own key, or, when it
has none, a one-hour AI-credits proxy token that the CLI renews by itself
during long jobs. A token is memory-only and never printed. `5am keys list`
reports the verdict:

```json
{"gemini_api_key":"","openai_api_key":"",
 "gemini_access":{"mode":"credits","source":"account"},
 "ai_credits":{"balance_micros":480000,"balance_credits":"480",
               "total_balance_micros":480000,"total_credits":"480",
               "allowance_micros":3000000,"allowance_credits":"3,000",
               "credit_micros":1000,"plan":"premium","period_key":"2026-09","period_end":"2026-10-01T00:00:00.000Z",
               "summary":"AI credits: 480 of 3,000 left (resets 2026-10-01)"}}
```

`mode` is `byok` | `credits` | `none`; on `none`, `reason` says why
(`cli_read_scope`: this CLI token has read scope and cannot obtain a token
that spends money, so create one with write scope or set your own key;
`exhausted`: buy credits at https://5am.app/settings#ai-credits or set a
key; `paused`: credits are paused platform-wide, set a key or wait;
`credits_disabled`: set a key). Amounts are AI credits,
never dollars: the `*_micros` fields are the raw micro-dollars for scripts,
the `*_credits` fields the same amounts in credits (1 credit =
`credit_micros` micro-dollars, whole credits rounded down, thousands
grouped), and `summary` the line a person reads; `--pretty` prints that
line. A command that runs out of credits mid-way fails with category
`credits` (see "Operating principles") and "not enough AI credits: this needs
about 800 credits and you have 480 credits: buy credits with '5am credits
buy' …" (the need rounds up, the balance down) or, without the amounts, "your
AI credits are used up"; some models are BYOK-only and answer "this feature is
not available on AI credits".

**Buying credits.** `5am credits` prints the balance (`ai_credits`, the same
shape as above), the access verdict and the `packs` on sale (`id`, `credits`,
`price_usd`: the only dollars anywhere). `5am credits buy` makes a **payment
link** (`https://5am.app/pay#…`) for one pack (`--pack ai_pack_20` or
`--pack 20000`; default the smallest). The user opens it on any device and
pays **without signing in** (a card, or a wallet where offered); it lasts 30 minutes
and the credits always go to this account. Nobody is charged until someone
pays on that page.

**Agents (including ones on their own computer, like Muse):**
1. Only when the user asks to buy credits, or agrees after a credits stop: say
   which pack and price (from `5am credits`) and get a yes.
2. `5am credits buy --pack <id> --no-wait` prints
   `{"status":"awaiting_payment","url":…,"expires_at":…,"pack":{…},"purchased_total_micros":…}`.
   **Send `url` to the user**; never open or pay it yourself.
3. `5am credits wait --since <purchased_total_micros>` waits (35 min by
   default) and prints `"status":"added"` with `added_credits` and the new
   balance, or `not_received`. Never run `credits buy` again to wait: that
   makes a second link. Then continue the work that stopped.

At a terminal with a person present, plain `5am credits buy --pack <id>` does
both: it opens the link in their browser and waits.

Refused for an AI character's token and inside a workflow run. Purchased credits
never expire.

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
  --ai-model gemini-3-flash-preview

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

### Scheduled tasks (`characters tasks`)

Daily autonomous runs: the saved prompt runs once a day (02:30 UTC) through the
SAME chat pipeline as an interactive message (skills, memory, webhooks), until
cancelled or the end date passes. Runs land in the chat thread; the owner is
notified per run and gets a recap when the task expires.

```sh
5am characters tasks create <characterId> --prompt "Post a morning haiku"   # paid plan
5am characters tasks create <characterId> --prompt "…" --start-date 2026-09-01 \
  --end-date 2026-09-30 --session <playgroundSessionId> --budget-tokens 20000
5am characters tasks list <characterId>                                     # JSON array
5am characters tasks update <characterId> <taskId> --end-date 2026-10-15    # partial update
5am characters tasks update <characterId> <taskId> --clear-end-date         # three-state: clear
5am characters tasks cancel <characterId> <taskId>   # admin scope; any plan; row kept
```

Dates are UTC calendar days (YYYY-MM-DD; end date inclusive). On update,
`--end-date`/`--start-date`/`--session`/`--budget-tokens` each have a
`--clear-*` twin (set XOR clear). Create/update are paid-gated (402
`paid_plan_required` on a free plan); cancel needs an admin-scope token.
Resume a cancelled task with `--status active`.

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

- `llm_judge` (default) — rubric sent to a Gemini judge (default
  `gemini-3.1-pro-preview`; override with `--judge-model` or the suite's `judge_model`). Use for open-ended / creative responses.
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

**Distinct from `5am media list --search <text>`** which is _lexical_
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
`/api/video-webhook` — both async, so don't expect results immediately on the 202. Re-running on an album that's already fully indexed is a no-op and
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
- `local_generate_video`: render AI video (`gemini-omni-1.1-flash`), save locally. Accepts `aspect_ratio`, `duration` (4, 6, 8 default, or 10 seconds), `resolution`, `negative_prompt`; there is no model choice (a retired Veo `model` value is mapped to Omni). (Image inputs are CLI-only, not exposed to the skill.)
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
port, works behind NAT. Full runbook: `cli/docs/SERVER_AGENT.md`.

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

# Bound the wait, or skip it entirely.
5am playground task <sessionId> "..." --wait-timeout 5m
5am playground task <sessionId> "..." --wait=false     # returns status:"accepted", no result
```

**Output shape.** The orchestration runs in the BACKGROUND — submitting only
queues it — so the command polls until the orchestrator's answer lands:

```json
{
  "status": "completed",
  "session_id": "b45f5737-...",
  "message_id": "b1b5ad00-...",
  "result": "[{\"name\": \"Sarah Jenkins\", \"company\": \"Apex Creative Agency\"}]"
}
```

`result` is the synthesis **as text**, so a prompt asking for JSON gives you a
string to parse — often fenced in ` ```json `. `status` is
`completed`, `accepted` (with `--wait=false`, and then there is no result), or
`timeout` (exit non-zero; the task may still be running). Always branch on
`status` before reading `result`:

```sh
OUT=$(5am playground task "$SESSION" "...return JSON..." --no-stream)
[ "$(echo "$OUT" | jq -r .status)" = "completed" ] || exit 1
echo "$OUT" | jq -r .result | sed 's/^```json//; s/^```//; s/```$//' | jq .
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
- **Tasks run on the orchestrator's user — not the CLI token's character.** A user PAT works; a _character-bound_ CLI token also works (the playground operates against the owner's account either way).
- **`task` is sync.** It blocks until orchestration completes (or pauses for proposals). Long workflows tie up the terminal — use `--no-stream` to run quietly, or run in the background and poll `sessions get`.
- **SSE auth**: the live progress stream uses `/api/sse` with the same JWT as everything else. If the user has only a `read`-scoped token, the stream still works (it's read-only); but `task` itself needs `write` + paid plan.
- **Proposals pause the task by default.** Two ways to handle them:
  - **Scripts (preferred)**: pass `--auto-approve-proposals` on `task`. Caps creation at `--max-new-characters` (default 3); rest are auto-rejected. Multi-stage flows handled in-loop, with a defensive 5-stage cap.
  - **Hand-curation**: omit the flag; the task POST returns `status: "awaiting_approval"` with a `proposals` array. Resolve in the web UI, then call `POST /api/playground/sessions/:id/resume` (REST only; CLI `playground resume` subcommand TBD) — or just re-run `5am playground task` with the same prompt.
- **Auto-approve creates characters that persist.** Each new character lives in `5am characters list` after the task. Adjust `--max-new-characters` accordingly; clean up afterwards with `5am characters delete <id> --yes` if needed.

## Managed Workflow attachments

A Managed Workflow's plan (authored at `<base-url>/workflows`) can carry
user-picked attachments: albums, media items, and uploaded FONT files. Each id
appears in the plan and in the generated program.

```sh
# Fetch an attached font by its font_id (from the plan). --output is required.
5am workflow attachment get <font_id> --output fonts/Brand.ttf
# → {"attachment_id":"…","file_name":"Brand.ttf","path":"fonts/Brand.ttf",…}

# Attached albums and media are ordinary library objects — use the ordinary
# commands with the attached id:
5am media list --album <album_id>
5am media download <media_id> --output ./watermark.png
```

- `attachment get` uses ordinary CLI auth: it works inside a managed run (the
  run's scoped token) and on your own machine after `5am login`.
- Fonts are for BRAND typography: pass the downloaded path to `--font` on
  `media clips`, `media highlight`, `media edit render` or `studio`. Generic
  subtitle/title burning does not need it — libass falls back through the
  installed Noto/DejaVu families, including for RTL and CJK.

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

### "Turn one long video into N short clips for socials"

```sh
# ONE command produces all N clips — one transcription, one model call.
5am media clips talk.mp4 --count 5 --aspect 9:16 --style bold \
  --brief "the strongest self-contained moments" > /tmp/clips.json

# The renders, subtitles and per-clip .vedl land in ./talk-clips/
jq -r '.clips[] | "\(.path)  \(.title)"' /tmp/clips.json

# Publish the keepers (each clip is an ordinary MP4)
5am media upload ./talk-clips/clip-01.mp4 ./talk-clips/clip-03.mp4 --new-album "Shorts" > /tmp/up.json

# Tag each upload with the platform it was cut for, so they're findable later
jq -r '.[].id' /tmp/up.json | head -1 | while read -r ID; do
  5am media update "$ID" --tags "Instagram, Vertical"
done
```

Do NOT do this:

```sh
# WRONG — re-analyses the whole video 5 times, 5× the Gemini spend, and
# produces reels rather than standalone clips.
for i in 1 2 3 4 5; do 5am media highlight talk.mp4 --output "clip-$i.mp4"; done
```

For footage that is about what's on screen rather than what's said (sport,
pets, reactions, b-roll), add `--visual`. It also engages automatically when
the source has no audio or too little speech, so a silent video still yields
clips instead of an error.

### "Make a motion graphics film from a brief and export it"

```sh
5am motion generate --brief "A 12 second launch film for Northside Coffee: bold type, a counter to 10,000 cups, an end card" \
  --format 9:16 --duration 12 -o launch.motion.json > /tmp/gen.json
jq '{fixes, issues}' /tmp/gen.json                      # layout issues left after the repair and tidy passes
5am motion sheet launch.motion.json -o launch.png       # free: look before paying
5am motion revise launch.motion.json "bigger counter, slower end card" --in-place
5am motion render launch.motion.json -o launch.mp4 --fps 30 > /tmp/render.json   # 20 AI credits
jq -r '.output' /tmp/render.json
```

If `render` exits non-zero after it began charging, read the error: a refused
final charge keeps the MP4 for `5am motion finalize <requestId>`. Do not run
`render` again.

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

### "Turn a podcast WAV into an AI b-roll video"

A richer alternative to the waveform overlay: generate a few clips, join them,
and lay the episode audio over the result. Each clip is 4 to 10s (8s by
default), takes about half a minute and costs about $0.10 per second of 720p,
so generate them as separate steps and `concat` deliberately.

```sh
# 1. Generate b-roll clips (one per scene). Match aspect ratio to the target.
5am media generate video --prompt "lo-fi study desk, warm lamp, slow pan" \
  --aspect-ratio 16:9 --duration 8 --output v1.mp4
5am media generate video --prompt "rain streaking down a city window at night" \
  --aspect-ratio 16:9 --duration 8 --output v2.mp4

# 2. Join the clips and lay the episode audio over them (replaces clip audio).
5am media concat v1.mp4 v2.mp4 --audio ./episode.wav --output ./episode-broll.mp4

# 3. (optional) upload the result alongside the WAV
5am media upload ./episode-broll.mp4 ./episode.wav --album "$ALBUM"
```

`media concat` stream-copies by default (instant) and falls back to re-encode if
the clips don't match; check the JSON `mode` field. Output length is the shorter
of the joined video and the `--audio` track (`-shortest`).

**One-shot wrapper (recommended).** `scripts/podcast_to_video.py` (stdlib-only
Python, cross-platform) automates the whole flow: measure duration → generate
enough clips → concat → mux audio → optionally burn in a transcript. When you
pass a transcript (`-s`) and no `-p` prompts, it uses `media generate text` to
write **per-scene b-roll prompts from the transcript**, so each clip tracks the
conversation. Clips retry up to 3× on transient generation failures (jittered backoff).

```sh
# Transcript-driven b-roll, vertical, with burned-in captions:
python3 scripts/podcast_to_video.py -i episode.wav -s episode.srt -a 9:16 -o reel.mp4

# Cheap proof first (2 clips), keep the per-clip files for inspection:
python3 scripts/podcast_to_video.py -i episode.wav -s episode.srt --clips 2 --keep --workdir ./clips
```

Flags: `-m/--model` (default `gemini-omni-1.1-flash`, the only video model),
`-p/--prompt` (your own scenes; overrides the
transcript scene-writer), `--no-scene-prompts` (disable it), `-n/--clips`,
`-d/--duration` (4, 6, 8 default, or 10 seconds per clip), `--max-clips` (default 30), `-j/--jobs` (generate N clips in
parallel; `-j 3`/`-j 4` is a good range), `--keep`/`--workdir` (clips land in
`<workdir>/clip_NNN.mp4`). Run `--help` for the full list. Each
8s clip costs about $0.80 at 720p (about twice the retired Veo 3.1 Lite), so start with `--clips 2`.

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
URL=$(5am albums public-link enable "$ALBUM" | jq -r .publicUrl)
echo "Public URL: $URL"

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

Albums must be emptied first (server-side safety check), and both deletes need an
admin-scope token. `media list` returns one page, so loop until the album is empty:

```sh
while IDS=$(5am media list --album "$ALBUM" --limit 100 | jq -r '.[].id') && [ -n "$IDS" ]; do
  echo "$IDS" | xargs -I{} 5am media delete {} --yes || break
done
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

# Run continuously (systemd units in production — see cli/docs/SERVER_AGENT.md):
5am data ingest --dataset requests --schema /etc/5am/requests.schema.json \
  --file /var/log/nginx/access.log --format combined --follow &
5am serve agent --name web-1

# Then enable query_server on a character and ask it:
#   "how many unique IPs hit web-1 in the last 24 hours?"
```

### "Make a clip for each prospect in this CSV and email it to them"

```sh
# 1. once: the sender identity and Gmail app password send uses
5am outreach config set --sender-name "Your name" --mailbox you@gmail.com
5am outreach mail setup --address you@gmail.com && 5am outreach mail test
# 2. a template film with {{name}} in a text layer (edit the JSON after generating)
5am motion generate --brief "A 10 second hello for a wedding photographer, their name large" --format 9:16 --duration 10 -o template.motion.json
# 3. the free half: items + one film + one contact sheet per prospect; STOP and show the sheets
5am outreach prepare --csv prospects.csv --template template.motion.json --batch oct_week_1 > prepare.json
jq -r '.prospects[] | "\(.status)\t\(.name)\t\(.sheet)"' prepare.json
# 4. after the user approves the sheets: render (20 credits each), draft, then the user reviews in a browser
5am outreach clips --batch oct_week_1 --dry-run && 5am outreach clips --batch oct_week_1 --yes
5am outreach draft --batch oct_week_1 --dry-run
5am outreach draft --batch oct_week_1
5am outreach review --batch oct_week_1          # a person clicks Approve per message, then Done
# 5. send what was approved, from the user's Gmail; then watch the pages
5am outreach send --batch oct_week_1 --dry-run && 5am outreach send --batch oct_week_1 --yes
5am outreach stats --batch oct_week_1
```

## Gotchas (read these before scripting)

- **Global flags (`--token`, `--base-url`) go before or after the subcommand, but need a value.** `5am --token "$T" catalog create --name Y` and `5am catalog create --name Y --token "$T"` are the same. If `$T` is empty the flag swallows the next word, so the CLI exits 3 with `--token needs a value, but the next word is the command "catalog"`. Check the variable, or write `--token="$T"`.
- **`--yes` is required to skip confirmation on `delete` commands.** Without it the command prompts on stdin: it blocks if stdin is open, and if stdin is at EOF it declines and exits `0` having deleted nothing, so the exit code cannot tell you the delete was skipped.
- **Use `media clips` for N shorts; never loop `media highlight`.** `clips` produces all N from one transcription and one model call. Looping `highlight` re-analyses the entire video every iteration — minutes of wasted compute and N× the Gemini spend on a long source — and yields composed reels rather than standalone moments. They are different commands for different jobs, not two speeds of the same one.
- **`media clips` and `media highlight` share the transcript cache** (`~/.5am/transcripts`). Running both on one video, or re-running either with a different `--brief`, pays for transcription once. Do not add your own caching layer, and do not pass `--force-transcribe` in a loop.
- **`media clips` needs ffmpeg with libass** for burned-in subtitles and titles. `--style none` and `--visual` skip libass entirely — reach for those if a user's ffmpeg lacks it, rather than telling them to rebuild ffmpeg.
- **Don't pass `--font` to fix non-Latin clip TITLES.** Titles and subtitles both burn through libass with automatic font fallback, so Farsi/Arabic/CJK shape correctly out of the box. If glyphs show as boxes the fix is installing the Noto families, not a `--font` flag.
- **Never cron `cat file | 5am data ingest`** — stdin has no checkpoint, so every run re-ingests the whole file and duplicates rows. Use `--file` (incremental) for anything scheduled; stdin is for one-shot pipes only.
- **`5am data ingest --replace` drops the dataset's rows AND its file checkpoints.** It is a full rebuild even when the schema is unchanged — not a "force" flag for appends.
- **`5am serve agent` and `data ingest --follow` block forever.** Run them under systemd (or background them) — they are daemons, not one-shots. Both exit cleanly on SIGTERM.
- **Characters can only query an ONLINE agent** (daemon polled within 90s). Offline agents fast-fail with `agent_offline` — the character will say so; it is not an error in your setup.
- **`stats` requires a `number` field; `latest`, `--since`/`--until`, and `prune` require the dataset's `time_field`.** Datasets without a time field still support count/count_distinct/group_by/stats.
- **Destructive custom skills are refused by the headless agent** (`destructive_refused`) unless it runs with `--allow-destructive` — the interactive confirm prompt from `characters chat` does not exist in the daemon.
- **Album delete refuses an album that still has media** (400, exit 3; empty it first) and, like `media delete`, needs an admin-scope token. **Character delete cascades to token, webhooks, interactions, and memory.** Both deletes are irreversible.
- **Paid direct shares and public-link sharing are mutually exclusive on the same album.** `5am albums public-link enable` returns 400 (exit 3) if the album has any paid direct shares; adding a paid share to an album with public sharing on is also rejected. To switch modes, disable the conflicting side first.
- **`5am albums unshare --user` is rejected for contributors.** If the recipient uploaded media to the album, the unshare returns 400 with `"You cannot unshare someone who contributed to the album."` Reassign or delete their media first.
- **`5am albums share` max 20 recipients per call.** Exceeding returns 400. Split into batches in a loop for larger sets.
- **`characters update --active false` is a soft kill at the token-lookup layer.** Already-issued 15-minute CLI JWTs stay valid until they expire — do not assume "active=false" instantly invalidates active sessions.
- **`webhooks rotate-secret` invalidates the old secret immediately.** Update the receiver _before_ rotating in production, or you will drop deliveries.
- **`webhooks test` does not increment `error_count`** and bypasses `is_active` / `allowed_actions` — it tests connectivity, not policy.
- **`media list` returns ONE page as a bare JSON array** (default 20, `--limit` up to 100), with or without `--album`. Step `--offset` until a call returns fewer than `--limit`; the first response is not the full set.
- **`5am characters skills execute` denials are returned in the JSON body**, not as non-zero exit. Always `jq` for an `error` / `denied` field.
- **Skills enabled via `--skills` flag use defaults.** If the user wants per-skill config (e.g., a skill that takes its own API key, model, or limits), use `--from-file`.
- **The CLI does not bundle a tunnel.** `webhooks listen` requires the user to run `ngrok`, `cloudflared`, or equivalent in another terminal first.
- **For generation commands requiring a stored provider key, configure `5am keys set <provider>` first.** `media image-edit generate` uses the normal Gemini access flow (including supported proxy access), so do not assume a stored key is its only option. A missing key surfaces as a 4xx (exit 3), not a 5xx.
- **`media generate image --model` is validated against the three Gemini image models** (`gemini-3.1-flash-image` default, `gemini-2.5-flash-image`, `gemini-3-pro-image`); anything else exits `3` with the accepted list. The `--aspect-ratio`, `--resolution`, `--image`, `--grounding`, and `--grounding-images` flags are **Gemini-only** (the OpenAI provider ignores them). `--resolution` is honored only by the 3.x models — `gemini-2.5-flash-image` is fixed at 1024px — and `--grounding-images` only by `gemini-3.1-flash-image`.
- **`local_ffmpeg` args must be a JSON array of strings**, not a single space-separated string. `{"args": ["-i", "in.mp4", "out.mp3"]}` works; `{"args": "-i in.mp4 out.mp3"}` is rejected with a hint. Pass each token as its own array element so filenames with spaces are preserved.
- **`5am media generate video` runs one model, `gemini-omni-1.1-flash`** (the Veo 3.1 previews retire on 2026-10-22). A retired `veo-*` `--model` is mapped to it with a stderr note; any other value exits `3`. `--duration` must be 4, 6, 8 (default) or 10 and is refused with `--extend`; `--last-frame` requires `--image`; `--reference-image` cannot combine with `--image`/`--last-frame`; all are rejected before any API call. A call is synchronous and takes about half a minute at 720p; for longer videos generate several clips and `5am media concat` them.
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

- **`5am outreach clips` charges 20 AI credits per prospect; `prepare` is free.** Run `prepare`, show the sheets, then `clips --dry-run`, then `clips`. A `pending_finalize` row is paid by the NEXT `clips` run; never `motion render` it yourself.
- **`5am outreach review` blocks until a person clicks Done** (or Ctrl-C) and opens a browser page on 127.0.0.1. Never run it unattended; `5am pipeline outreach list --status staged` shows the drafts without it.
- **`5am outreach send` is refused in a workflow run** and never sends a draft the person did not approve. It stops the batch on a refused Gmail sign-in (fix with `mail setup`, then send again: the rows stay approved). A closed pipeline item is skipped, not emailed. An `uncertain` row waits for the person's Gmail Sent folder check (mark-sent or release); send never retries it on its own. A `refused` row (Gmail's permanent refusal) is closed: its draft is rejected with Gmail's reply and never sent again.
- **Pipeline state errors depend on the action.** `approve` on a non-staged draft and `mark-sent` on a draft that is neither approved nor sending answer 404; `edit` works while staged only. `unapprove` on a non-approved draft and `release` (plus the reserve/refuse actions used by send) answer 409 with the current `status`. Unapprove can also return 409 `review_queue_conflict`.

## When to suggest `--pretty`

Only when the user explicitly asks to _see_ the data ("show me my albums"). For any further processing (counting, filtering, piping to another command), use the default JSON output and `jq`.

## Useful env vars

- `5AM_TOKEN` — auth token (overrides stored login)
- `5AM_BASE_URL` — API base URL override
- `5AM_PRETTY=1` — globally enable `--pretty` output
- `FIVEAM_GMAIL_ADDRESS`, `FIVEAM_GMAIL_APP_PASSWORD`: the outreach Gmail credential, read before the stored one by `outreach send` and `outreach mail test|report`, and by `outreach mail setup` instead of asking
- `5AM_DISABLE_KEYRING=1`: store secrets (the login token, the Gmail credential) in `config.toml` without trying the OS keychain first, as on a server with none
- `5AM_SHELL` — shell binary used by the local `run_command` skill. Defaults to `$SHELL` on Unix (falling back to `sh`, then `bash`) and `cmd.exe` on Windows. Override with an absolute path when running inside minimal containers (e.g. Alpine without bash).
- `5AM_ALLOW_OUTSIDE_WORKSPACE=1` — equivalent to `--allow-outside-workspace` on `chat`. Lets `read_file`/`write_file` skip the interactive prompt for paths outside CWD. Only use with explicit user consent.

See the CLI's `.env.example` for the full list and precedence rules.

## Image editing through the CLI

Delegate recipe creation to the CLI's LLM; workflow Python must not implement
IEDL grammar or write recipes itself. Generate a reusable recipe once per brief,
then reuse it for matching images. If the user supplies an approved recipe
attachment, preserve its exact bytes and validate/render it instead of generating
a replacement. Copying supplied file content is glue, not authoring IEDL:

```sh
5am media image-edit generate --brief "Warm portrait, gentle contrast, 4:5 crop. Local adjustments only; no AI selections or generative edits." -o portrait.iedl
5am media image-edit validate portrait.iedl
5am media image-edit render portrait.iedl --input photo.jpg -o edited.jpg --resolved edited.iedl-resolved.json --bundle edited.iedl.zip
```

`generate` uses the normal Gemini access flow and model quota, and validates its
output before writing the file. It does not analyze a supplied photograph; put
the editing intent and constraints in the brief. Workflows must still invoke
`media image-edit validate` on the saved file before publishing it as an artifact or rendering it, including
recipe-only workflows. Stop on validation failure. `generate` and `validate` need
Node and the runtime but no browser. `inspect portrait.iedl --input photo.jpg`
and `render` run on Native Skia (`@napi-rs/canvas` 1.0.11, `skia` by default) in
Node worker threads without a browser (or on Headless Chrome with `--engine chrome` /
`FIVEAM_IEDL_ENGINE=chrome`); `inspect` reports bindings and unresolved operations
and does not generate masks or apply analysis.
`render` writes local output; uploading or publishing artifacts is a separate CLI
operation. Keep originals intact. Use subprocess argument lists, check each exit
status, and stop if generation/validation fails. Do not call the model SDK,
Puppeteer, or the Python image-editing API directly from workflow code.

Include requirements in the brief: desired look, local-only versus requested AI
modification, protected regions, output format, and reusable parameters. For AI
selection/masked generation, bind the matching library source with `--media-id`
instead of `--input` (the CLI downloads the original).
Do not retry an ambiguous paid render. Preserve the recipe and resolved bundle for
replay.

```sh
5am media image-edit render approved.iedl --media-id MEDIA_ID --format png -o edited.png --bundle edited.iedl.zip
5am media image-edit render edited.iedl.zip --input matching-original.jpg --format png -o replay.png
5am media image-edit render edited.iedl.zip --input matching-original.jpg --mask MASK_ID -o mask.png
5am media image-edit batch portrait.iedl --input-dir photos --output-dir edited --report batch.json
```

Use actual declared mask IDs for `--mask`. Bundles reuse resolved adjustments and
stored generated assets; they require the matching source image, not another
photo. Mask export produces original-space PNG. `batch` is nonrecursive and accepts
PNG/JPEG/WebP; it cannot use `--media-id`. It runs up to four images in isolated
Node worker threads on Native Skia (`skia`) by default (or shares one Chrome
browser across isolated contexts with `--engine chrome`). Set `--concurrency 1`
through `4` to control memory and CPU use. Use local-only recipes for directory batches. It
continues after per-image failures, writes results in input order, and exits
nonzero if any image failed. Inspect the report before publishing results.

Use repeated `--param name=value` and `--asset name=path` for explicit bindings.
`--timeout 2m` is the default per-image deadline; `--overwrite` explicitly allows
replacing output files. A valid recipe still needs visual review: preserve facial
detail and inspect mask edges before approving a look for batch reuse.

Image editing is opt-in: `5am update --runtime-only` installs the version-matched
runtime, locked JS dependencies, and Skia (`@napi-rs/canvas` 1.0.11)
with Node's npm. Alternatively pass `--with-image-edit` to
the installer (`curl .../install.sh | sh -s -- --with-image-edit`). Image-edit
execution, rendering, and input-bound inspection need Node 20+ and Skia (installed
by `5am update --runtime-only`); Chrome/Chromium is only needed for the
`--engine chrome` (`FIVEAM_IEDL_ENGINE=chrome`) rollback. Core CLI installation and use
remain independent of these dependencies. Normal updates synchronize an opted-in
managed runtime; core-only updates do not download one.

When `--engine chrome` is used, the runner discovers compatible installed Chrome/Chromium automatically;
`--browser` or `CHROME_PATH` overrides discovery. `--runtime` or `IEDL_RUNTIME`
locates an explicitly managed bundle; `--node` overrides the Node executable.
Missing dependencies produce setup guidance. A larger workflow machine alone does
not provide them: use an explicitly provisioned image-edit runner.
No browser/dependency installation during a managed run. Report missing capabilities
clearly instead of silently substituting a different editing engine.

**Cloud agent VMs and containers** (Linux, often running as root; for example Meta's
Muse). Outside managed runs, install what the commands ask for:

- **ffmpeg:** `apt install ffmpeg`. Debian and Ubuntu builds include libass and the
  filters clips, collage, mix and highlight use.
- **Node.js 20+:** `apt install nodejs` gives 18 on Ubuntu 24.04 and Debian 12; install
  20 or newer from nodejs.org or NodeSource instead.
- **Chrome (optional, only for `--engine chrome` rollback or `motion preview`):** on Debian, `apt install chromium`. On Ubuntu, `chromium-browser` is only a
  Snap stub that does not run in containers; on x86_64 install Google Chrome's .deb
  (`https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`, then
  `apt install ./google-chrome-stable_current_amd64.deb`).
- **Root is handled.** As root on Linux the runtime launches Chrome with `--no-sandbox`
  (Chrome refuses to start as root otherwise; the VM or container is the boundary).
  Do not wrap Chrome to add flags yourself.
- **Install location:** `curl -fsSL https://cli.5am.app/cli/latest/install.sh |
  FIVEAM_INSTALL_DIR="$HOME/.local/bin" sh` needs no sudo and keeps the CLI and its
  runtime beside the agent's own files.
If the task explicitly states that the runtime is unavailable, produce only the
requested diagnostic artifact. Do not include speculative generate/render/batch
branches or treat local PATH/environment probes as deployment confirmation.

For direct IEDL authoring when explicitly requested, use the focused
[IEDL skill](skills/iedl/SKILL.md) in the repository. Workflow code generation
needs only the CLI guidance above. The public [IEDL reference](https://5am.app/cli/docs/iedl)
covers presets, local analysis, masks, and the complete language.

---

## Agentic Content Supply Chain (`brand-kits`, `ads`, `catalog`, `campaign`, `campaigns`, `telemetry`)

Creative supply chain commands for ingesting product SKU catalogs, running ad campaigns on
them, generating on-brand localized video ads with Ad Maker, recording staged ad
deployments under CMO budget guardrails, and re-rendering ads that their conversion results
mark as tired (pulled hourly from Meta or Google for published ads, uploaded for the rest).

The campaign (`5am campaign`, singular) is the unit everything runs on: it draws from one
catalog, has its networks, locales, formats, per-network budgets and the workflow that
builds its ads, tracks which SKUs it has rendered, and has its own AI character. The ad
deployments (`5am campaigns`, plural) are the variants that belong to a campaign.

**Where approved ads go.** The account owner connects ad accounts on the web, never with
the CLI. An ad approved while the account's Meta ad account is connected is published on
Meta (`network_dispatch: "meta"`); one approved while its Google Ads account is connected
is published on Google, in a Demand Gen campaign (`network_dispatch: "google"`). Each
published ad carries `dispatch_state` (`queued`, `publishing`, `published`, `failed`, with
`dispatch_error`), `external_ad_id` (Meta's ad id, or Google's AdGroupAd resource name),
`network_status` and `network_review`. The network reviews every ad before it runs:
- **Meta:** `network_status` is Meta's `effective_status` (`PENDING_REVIEW`, `ACTIVE`,
  `DISAPPROVED`, ...), and `network_review` holds Meta's feedback and issues.
- **Google:** `network_status` is Google's approval or review state (in review, approved,
  approved limited, disapproved: `REVIEW_IN_PROGRESS`, `APPROVED`, `APPROVED_LIMITED`,
  `DISAPPROVED`), and `network_review` holds Google's policy topics.
- **A disapproved ad** comes back `rejected`, with the network's reasons, and spends
  nothing.

Every other ad is simulated: `active` is a status here, not an ad running anywhere
(`network_dispatch: "simulated"`, `sim_` external ids). `5am campaigns list --pretty`
says where each ad stands ("Live on Meta", "In review on Google", "Approved on Google
(limited): Alcohol", "Disapproved by Google: <topics>", "Simulated"). The `catalog`,
`campaign`, `campaigns` and `telemetry` commands answer 404 unless the server has the
content supply chain switched on.

For a published ad, a local pause is a request to the network. The CLI shows
"Pausing on Meta" / "Pausing on Google" until the remote status confirms the pause,
then "Paused on Meta" / "Paused on Google". A failed remote pause displays
"Failed: <dispatch_error>" even when `dispatch_state` remains `published`.
A local `paused` status alone does not confirm that spending has stopped.

### Account Brand Kits (`5am brand-kits`)

```sh
5am brand-kits list
5am brand-kits get default
```

- `brand-kits get <id|default>` resolves a kit by UUID, name, or `default`.
- Pass `--brand-kit default` (or a kit ID) to `5am ads draft` and `5am ads generate` to
  apply the brand's palette, catalog fonts, logo mark, and default CTA.
- A kit that does not exist exits `3` with `code` `brand_kit_not_found` (the message names
  it). Any other failure to read the kit (401, 403, a server error) stops the command with
  that error: an ad never goes out silently without the kit you named.

### Headless Ad Maker (`5am ads`)

```sh
5am ads templates
5am ads draft --template signature-reveal --format 9:16 --duration 15 \
  --name "AeroRun Carbon" --audience "Marathon runners" \
  --benefit "4% faster marathon pace" --cta "Shop Now" --offer "Free 2-Day Shipping" \
  --brand-kit default --photo media:<mediaId> -o draft.motion.json --overwrite

5am ads generate --adapt draft.motion.json --locale es-MX --format 9:16 \
  --name "AeroRun Carbon" --audience "Corredores de maratón" \
  --benefit "4% más rápido en día de carrera" --cta "Comprar Ahora" \
  --brand-kit default -o ad-es-mx.motion.json --overwrite

5am motion render ad-es-mx.motion.json -o ad-es-mx.mp4 --overwrite
```

- `ads draft` builds a complete `.motion.json` deterministically in code from one of the
  16 curated Ad Maker templates: no model writes the ad and it costs `0` credits.
  `--duration` defaults to 30 seconds, as on the web. As on the web, a photo without a
  description is described once with Gemini (cached per photo, on your Gemini access) so
  the template can place it; `--no-describe` skips that and the draft then uses no Gemini
  at all.
- `ads generate` composes a new ad or adapts (`--adapt`) and localizes (`--locale`) a draft
  with Gemini using Ad Maker's advertising rules (`adIntent`) and enforces the Brand Kit.
  An adapted draft keeps its own format and duration unless you pass `--format` or
  `--duration`.
- Render an ad with `5am motion render` (the Motion export, 20 credits). Like every CLI
  render it carries the "Made with 5AM.app" mark: there is no unmarked local export. The
  unmarked 500-credit ad export is Ad Maker's, on the web.
- A campaign's ads render unmarked on 5AM's servers instead, with `5am campaign render`
  (Business plan; see below). Build those films with library photos and clips (`--photo
  media:<id>`, `--clip media:<id>`): the server cannot read a local file.

**An ad for a catalog SKU: `--catalog <catalog-id> --sku <sku-id>`** (both commands).

```sh
5am catalog import-media <catalog-id> --sku SHOE-1 --limit 4 --wait --wait-timeout 5m
5am ads draft --catalog <catalog-id> --sku SHOE-1 --template signature-reveal --format 9:16 \
  -o draft.motion.json --overwrite
5am ads generate --adapt draft.motion.json --locale es-MX --catalog <catalog-id> --sku SHOE-1 \
  -o ad-es-mx.motion.json --overwrite
```

- The campaign fields come from the SKU, so the ad states only the merchant's own claims.
  Flags you pass win. Never write a SKU's claims yourself:
  - name: `title`;
  - benefit: `benefit`, else the first sentence of `description`;
  - audience: `audience`, else the catalog's `default_audience`, else "Shoppers looking for
    <category>";
  - cta: `cta`, else the catalog's `default_cta`, else "Shop now";
  - offer: `offer`, else a sale line from `sale_price` and `price` ("Now $99.00, was $129.00");
  - proof: `proof` only;
  - destination: the product page;
  - photos: the SKU's first 4 images in the catalog's order, unless you pass `--photo`. The
    owner chooses a product's ad images in the catalog (on the web): the order (the first
    is the hero), images kept out of ads (`use_in_ads: false` in the SKU's `media`, never
    used), and images of their own (`origin: "owner"`). Feed images arrive with
    `catalog import-media`;
  - clips (`ads generate` only): the SKU's imported videos that are READY (processed) and
    used in ads, in the same order, at most 4, unless you pass `--clip` or the adapted draft
    has clips. `clips` in the output
    counts them. A video still processing is left out with a line in `warnings`: wait for it
    with `catalog import-media <catalog-id> --sku <sku-id> --wait`.
  - brand kit: the catalog's, unless you pass `--brand-kit`. If the catalog's kit no longer
    exists, the ad is made without one and `warnings` says so; any other failure to read
    it stops the command.
- **No template uses video:** Ad Maker's 16 code templates draw photos only, so `ads draft`
  never adds clips; it names the SKU's videos in `warnings`. The SKU's videos reach an ad
  through `ads generate` (adapting the draft, as above).
- The output's `campaign` object shows the fields used.
- **Refusals exit 2 with a `code`** on the stderr JSON error; `sku` names the SKU:
  - `missing_benefit`: no benefit and no description. Add one to the feed and sync, or pass
    `--benefit`.
  - `sku_out_of_stock`: the SKU is out of stock.
  - `sku_removed`: the SKU was removed from the catalog.
  - No file is written for any of them. Exit 2 with one of these codes is NOT an auth
    failure: skip the SKU.
- `ads generate --adapt` keeps the draft's photos (and clips). It uses the SKU's images only
  when the draft has none.

### SKU Catalogs & SHA-256 Delta Ingestion (`5am catalog`)

```sh
5am catalog list
5am catalog create --name "Summer Footwear SKUs" --source json --brand-kit default --locales en-US,es-MX \
  --default-audience "Road runners" --default-cta "Shop now"
5am catalog update <catalog-id> --default-cta "Run with us" --auto-trigger=false   # owner only
5am catalog sync <catalog-id> --from-file skus.json --import-media
5am catalog sync <catalog-id> --from-file all-skus.csv --full      # the file is the whole catalog
5am catalog sync <catalog-id> --from-file products_export.csv --store-domain mystore.com --currency USD   # a Shopify export
5am catalog import-media <catalog-id>                  # --sku <id>; --limit N; --wait
5am catalog skus <catalog-id> --limit 50
5am catalog skus <catalog-id> --limit 50 --offset 50   # the next page
5am catalog skus <catalog-id> --all                    # every SKU
5am catalog delete-media <catalog-id> <media-id> --yes             # owner only
5am catalog sku delete <catalog-id> <sku-id-or-external> --yes     # owner only
5am catalog delete <catalog-id> [--delete-media] --yes             # owner only
```

- **Feed columns** beyond the product facts (title, description, price, sale_price,
  currency, product_url, image_urls, category, locales, promo_badge):
  - product videos: `video_urls` (at most 4, http or https; in a CSV `video_url` or
    `video_urls`, several separated by `|`);
  - stock: `in_stock` (true/false/yes/no/1/0) and `availability` (`in_stock`,
    `out_of_stock`, `preorder`, `backorder`; "in stock" and "out of stock" also work);
  - the merchant's ad claims: `audience`, `benefit`, `cta`, `offer` and `proof`.
  - A sync that changes a SKU's claims, or takes it out of stock, pauses its staged and
    active ads in every campaign (`paused.deployments`, `paused.campaigns`).
- **A Shopify product export** (Shopify admin, Products, Export) syncs as it is, one SKU per
  product (not per variant), keyed by its handle. It is recognized by its columns (`URL handle`
  and `Price` in the 2026 export, `Handle` and `Variant Price` in the older one).
  - `--store-domain` and `--currency` are required for it (the export has neither): without
    them the command exits non-zero with "This is a Shopify product export: pass
    --store-domain and --currency". `product_url` is `https://<store-domain>/products/<handle>`.
  - price: the lowest price a variant can be sold at; a higher compare-at price becomes
    `price`, with the variant's as `sale_price`. A range of prices goes in
    `metadata.price_min` / `price_max`.
  - stock: in stock when any variant can be sold (not tracked, policy continue, or a
    quantity above 0 or none given), else `in_stock` false, `out_of_stock`.
  - `image_urls`: the product's images by position, then variant images, at most 10.
    `description`: the HTML as plain text. `category`: Type, else the taxonomy's last part.
    `metadata`: source `shopify_csv`, vendor, tags, variant_count.
  - Drafts, archived and unlisted products, products not published on the online store
    (their page may not be live), gift cards, and products without a title or a price are
    left out, counted in the output's `shopify` block: `{ rows, products, skipped: { draft,
    archived, unlisted, other_status, unpublished, gift_card, no_title, no_price,
    no_handle }, store_domain, currency }`. With `--full` they are removed from the catalog.
  - No claim (benefit, audience, offer, proof, cta) comes from an export: the benefit falls
    back to the description's first sentence, and the catalog's defaults apply.
    `--full` and `--import-media` work as for any feed.
- **`catalog sync` sends 5,000 rows per request.** Larger feeds go in several batches,
  each reported in `batches` with the counts added up:
  - a batch the server refuses on its own (a bad row, which `row` names, a duplicate SKU
    id, the plan's SKU limit) is listed as `failed`, the next batch still goes, and the
    command exits non-zero;
  - 401, 402, 403 or 404 stops the sync, and the rest are listed as `not_sent`.
- **`catalog import-media`** turns feed image and video URLs into library media (the older
  `catalog import-images` is the same command for images only).
  - It downloads each file the server lists as not yet imported, on this machine (http or
    https), and checks what it is from its bytes: an image at most 20 MB and 45 s, JPEG,
    PNG, WebP, GIF or HEIC; a video at most 500 MB and 15 minutes, MP4, MOV or WebM.
  - Feed downloads require direct internet access: they ignore proxy environment
    variables, including `HTTP_PROXY` and `HTTPS_PROXY`. Each connection, including
    redirects, checks the actual destination IP and refuses private, loopback,
    link-local, CGNAT and other non-public destinations, including private IPv4
    addresses embedded in RFC 6052 NAT64. Backend API calls and uploads keep their
    existing proxy behavior.
  - It uploads each into the catalog's own album (internal, never in the library; videos
    over 64 MB in parts) and records it on the SKU, so `ads draft|generate --catalog --sku`
    use it. Uploads count against storage like library uploads.
  - `--limit N` takes at most N images and N videos this run, including failed
    attempts. The importer advances past pages of already-attempted failures, so
    1,000 broken targets do not hide later URLs when the run's limit permits them.
  - `imported` and `failed` (with the `kind` and the `stage`: download, upload or record)
    list what happened; files that could not be used are skipped, and the exit is 0. A
    video over the server's cap fails with `code` `file_too_large`.
  - A URL is imported once, and a re-sync never imports it again.
  - Storage full, or a permission or catalog refusal, stops it (`stopped`, non-zero exit).
  - **Videos are processed on 5AM's servers after upload** (poster, length, an MP4 for a
    .mov or a source over 1080p), and an ad uses one only once it is ready (a SKU's
    `media[]` entry has `ready`). `--wait` waits for them (the `--sku` SKU's videos, else
    this run's) for at most `--wait-timeout` (default 10m), and prints `wait`: `status`
    ready or timeout, the videos in `ready` and `not_ready`. A timeout exits 0; the videos
    finish on their own. The timeout bounds the whole polling phase, including
    in-flight SKU requests; no new poll starts after the deadline. The lists reflect
    observed video states and can be incomplete if the deadline interrupts polling.
  - `catalog sync --import-media` runs it after a sync with no failed batch, and prints it in
    `media` (the older `--import-images` imports the new images only).
- **`catalog skus`** pages feed content with `--limit` (1..500, default 100) and
  `--offset` (zero or greater, default 0). Increase offset by the returned row count
  until a short page, or use `--all` to gather every page from the start. `--all`
  cannot be combined with a positive `--offset`. Keep filters such as
  `--include-removed` unchanged between pages; concurrent catalog changes can move rows.
- **`catalog sync --full`** says the file is the WHOLE catalog. The batches go as one sync
  session; once every batch went through, the session is finished, which removes the
  catalog's SKUs the file does not have (`session.removed`). If any batch failed or was not
  sent, nothing is removed (`session.status` not_finished, non-zero exit): fix the feed and
  run the full sync again. Without `--full` a sync never removes a SKU.
- **Deletes** (owner only: refused with 403 `cli_token_not_allowed_here` in workflow runs
  and AI character sessions; each asks for confirmation unless `--yes`):
  - `catalog delete-media <catalog-id> <media-id>` deletes one imported photo or video. Its
    feed URL stays recorded as deleted (`excluded`), so it is not imported again while the
    feed lists it (the owner can allow it again on the web). 409 `media_in_use` while an ad
    render uses it.
  - `catalog sku delete <catalog-id> <sku>` removes one product. A removed SKU (here or by
    a full sync): its live, waiting and tired ads pause in every campaign (`paused_reason`
    `sku_removed`, never resumed), it is pending nowhere, render and stage refuse it (409
    `sku_removed`), and its imported media are deleted after a grace period. A later sync
    that lists it brings it back, pending again.
  - `catalog delete <catalog-id>` deletes the catalog and its products. Its imported photos
    and videos move into the library as an ordinary album (`photos_album_id`), or with
    `--delete-media` are deleted (`media_deleted`). Campaign ads albums stay. 409
    `renders_in_progress` while any of its campaigns has an ad render queued or rendering.
  - `catalog skus --include-removed` also lists removed products (each with `removed_at`).
- **A product's ad images are the owner's to choose, on the web** (the catalog page): their
  order, "don't use in ads", and images of their own added from the library or uploaded.
  The choices survive every sync and every campaign's future ads use them; they are not
  claims, so changing them never pauses an ad or makes a SKU pending. In `catalog skus`
  (and a campaign's `campaign skus`) each SKU's `media` is in that order, and each entry
  has `origin` (`feed` or `owner`), `position` (null until the owner orders them),
  `use_in_ads`, `thumbnail_url`, `src` and `excluded`. `--pretty` sums them up per SKU as
  `<used>/<total> in ads, <n> yours`. There is no CLI command to change them.
- **A new version of an ad with new images is the owner's, on the web.** After changing a
  product's images, the campaign page's "Make a new version" makes the SKU pending again
  in that campaign (`campaign skus` shows `new_version_at`); the next run makes the new
  ads, and the old ad stays until the owner approves the new one. The server refuses it to
  workflow runs and AI characters (403 `cli_token_not_allowed_here`), so there is no
  `5am campaign new-version`: an agent asked for one tells the owner to use the campaign
  page.
- **`catalog update`** changes only the flags passed: name, `--locales`, `--brand-kit`
  (a UUID or `default`), `--auto-trigger`, and `--default-audience` / `--default-cta` (the
  fallbacks for SKUs that name none; an empty value clears one). It is the owner's only.

- A catalog holds **feed content only**. One catalog can feed several campaigns, and each
  campaign tracks which SKUs it has rendered, so render state lives on the campaign:
  `5am campaign skus <campaign-id> --pending`.
- `catalog sync` computes a deterministic SHA-256 `content_hash` per SKU. Only new or
  modified SKUs count in `dirty_delta`; each becomes pending again for every campaign that
  has it, and unchanged SKUs are never re-rendered. With the catalog's auto trigger on,
  `triggered_campaigns` lists the running campaigns whose SKU filter matches a changed SKU:
  their workflows are woken. A change outside every filter wakes none.
- `catalog list` reports `sku_count` and `campaign_count` (campaigns that have not ended).

### Ad Campaigns (`5am campaign`)

```sh
5am campaign create --catalog <catalog-id> --name "Summer launch MX" \
  --goal "Launch the summer line in Mexico" --networks meta,google \
  --locales es-MX,en-US --formats 9:16,1:1 --budget meta=5000,google=2500 \
  --category Running --workflow <workflow-id>
5am campaign list                      # running first; --include-ended adds ended ones
5am campaign get <campaign-id>
5am campaign update <campaign-id> --budget meta=8000 --locales es-MX
5am campaign skus <campaign-id> --pending --all      # every pending SKU
5am campaign skus <campaign-id> --all                # every SKU, including rendered/paused/excluded
5am campaign skus <campaign-id> --cursor <next>      # one later page with the same filters
5am campaign render <campaign-id> ad-es-mx.motion.json --sku <sku-id> --locale es-MX --key <retry-key>
5am campaign render-status <campaign-id> --key <retry-key> --include-doc --wait
5am campaign mark-rendered <campaign-id> <sku-id-or-external>
5am campaign pause <campaign-id>
5am campaign resume <campaign-id>      # owner only
5am campaign end <campaign-id> --yes   # owner only, final
5am campaign update <campaign-id> --digest daily     # owner only: off (default), daily or weekly
5am campaign delete <campaign-id> --character keep --yes   # owner only; keep or delete its character
```

- **Campaigns are a store feature.** `create` needs the Business plan (402 with
  `required_plan` business otherwise), and the plan sets how many campaigns that have not
  ended an account may have (409 `too_many_campaigns`).
- **Each campaign gets its own AI character,** created with the campaign. Its chat is where the campaign's ads are
  reviewed: the character reviews each staged ad (`review_status` ok or flagged, with
  `review_notes`) but never approves; the owner approves or rejects in that chat (or with
  `5am campaigns approve|reject`). Ending a campaign archives the character; its chat
  stays readable.
- **The digest** (`update --digest daily|weekly`, off by default): the character posts the
  campaign's numbers for the last UTC day or Monday-to-Monday week into its chat, with a
  push, from 14:00 UTC the day after. Its words are written by the character's model on
  your Gemini access from those numbers only; without access it is a numbers-only text.
- **Deleting a campaign** (`delete --character keep|delete`, the choice is required): a
  running or paused campaign is ended first. Its ads stay as history with no campaign, its
  "ads" album stays, 5AM's campaign program goes with it (your own workflow stays), and the
  character goes with its chat (`delete`) or stays archived (`keep`). 409
  `renders_in_progress` while an ad renders, 409 `run_in_progress` while its program runs.
- **Scope.** `--catalog` is fixed at create. `--category` and `--sku` (repeatable) narrow
  the campaign to part of the catalog; with neither it covers the whole catalog. Defaults:
  networks `meta`, locales `en-US`, formats `9:16`.
- **Budget.** `--budget network=cents` is the campaign's own daily cap per network, on top
  of the account's `campaigns policy` cap. A network without one is bound only by the
  account cap.
- **Google's daily floor.** A Google campaign needs at least $5 a day, or the account's
  local minimum. A Google budget under it is refused with 409
  `budget_below_network_minimum` on `create`, `update --budget`, `campaigns approve` and
  `campaigns resume`. The error names the floor
  ("Google needs a daily budget of at least 5.00 USD (minimum_cents 500) for this
  campaign"), and its `hint` gives the `5am campaign update <campaign-id> --budget
  google=<cents>` that raises it. `--budget` replaces every network's budget, so name the
  others too.
- **`update`** changes only the flags passed. `--budget` replaces every network's budget,
  `--category`/`--sku` replace the whole filter (`--whole-catalog` clears it), and
  `--workflow none` detaches the workflow. An ended campaign is read-only.
  Adding locales, formats or networks clears the campaign's SKU render stamps;
  expanding its product filter also wakes an enabled trigger. Settings, render
  invalidation and the trigger update commit together, so a failed edit is safe to retry.
- **Who may do what.** `create`, `update`, `resume` and `end` are the owner's only:
  refused with 403 `cli_token_not_allowed_here` inside workflow runs and AI character
  sessions. `pause` is also allowed to the campaign's own character, since it only reduces
  spend; it stops the campaign's runs and pauses its active and tired ads. `resume` brings
  back the ads the pause paused, under the caps (`ads.still_paused` counts the ones that
  did not fit).
  Pause and end commit local campaign/deployment changes and queued network pauses in
  one transaction. Repeating the stop reconciles unfinished local work. Network delivery
  is asynchronous: a local pause alone does not confirm that the network stopped spending.
- **`campaign skus`** lists the campaign's SKUs with THIS campaign's state:
  `campaign_status` is `pending` (never rendered here, changed since, or the owner asked
  for a new version: `new_version_at`), `rendered`, `fatigued`, `paused` or `excluded`.
  Each SKU carries its `media` in the order its ads use them (see the catalog's images).
  `--pending` narrows the result to ones to (re)render, never out-of-stock SKUs.
  Both filtered and unfiltered lists support `--limit` (1..500, default 100),
  `--cursor <next>` and `--all`. `next` is null on the last page; `--all` follows
  every page and cannot be combined with `--cursor`. Keep `--pending` and other
  filters unchanged when following a cursor.
- **`campaign render`** posts a MotionDoc and renders it unmarked on 5AM's servers; the MP4
  goes into the campaign's album. It needs the Business plan. Each delivered ad comes out
  of the plan's monthly bundle of catalog ads (`paid_with: "bundle"`, `credits: 0`), then
  costs AI credits at the catalog rate (out of credits: category `credits`, exit 3); a
  failed render is refunded. The film's format must be one of the campaign's, 6 to 60
  seconds, with library photos and clips (at most 4 clips, each processed, else 400
  `clip_not_ready`); a film with clips is charged at the catalog video rate. A SKU out of
  stock or removed from the catalog is refused (409 `sku_out_of_stock`, `sku_removed`). It waits
  until the render is `delivered` (`media_id`, `asset_url`) or `failed` (exit non-zero);
  `--no-wait` returns while it is queued, and `--timeout` bounds the wait. The same
  `--key` answers the existing render (`replayed: true`, no new charge), so a retry never
  pays twice for a non-failed render, and running it again with the key keeps waiting.
  The same SKU, locale and format replay the original doc even if a different doc is
  submitted under that key; use a new key for an intentional new creative. A failed
  render frees its key, so a new POST can render and charge again.
- **`campaign render-status`** reads the latest attempt for an exact `--key`, without
  generation, submission or a charge. `--include-doc` returns its saved MotionDoc;
  `--wait` waits for an existing render within `--timeout`. Missing keys answer
  `{ "render": null }`; a failed render is printed and exits non-zero. Check this before
  importing or generating on a retry. Reuse the saved doc and delivered asset, or wait
  for the queued render, even when the retry runs in a fresh container.
- **`campaign mark-rendered`** is the only render stamp: staging an ad never marks its SKU
  rendered. Call it once per SKU after its whole set of variants is staged, so a run that
  stops partway leaves the SKU pending. A SKU rendered for one campaign stays pending for
  every other campaign that has it.

### Ad Deployment Records & CMO Guardrails (`5am campaigns`)

```sh
5am campaigns policy
5am campaigns policy --network meta --daily-budget-cap-cents 100000 --min-roas 2.5 --max-staged 300
5am campaigns policy --network meta --fatigue-window-days 7 --attribution-days 3 \
  --min-spend-cents 4000 --thumbstop-threshold 0.2
5am campaigns stage --campaign <campaign-id> --network meta --campaign-name "Summer_AeroRun_es-MX_9x16" \
  --sku <sku-id> --locale es-MX --aspect 9:16 \
  --template signature-reveal --hook "4% más rápido" --cta "Comprar Ahora" \
  --asset-url https://... --daily-budget-cents 2500 --mode stage
5am campaigns stage --campaign <campaign-id> --render <render-id> --network meta \
  --campaign-name "Summer_AeroRun_es-MX_9x16" --mode stage --key <retry-key>
5am campaigns list --campaign <campaign-id> --status staged
5am campaigns list --campaign <campaign-id> --status staged --all  # follow every page
5am campaigns list --campaign <campaign-id> --cursor <next>        # one later page
5am campaigns list --campaign <campaign-id> --pretty   # a table: where each ad stands on its network
5am campaigns approve <deployment-id>                   # Human-only: staged -> active
5am campaigns approve <id-1> <id-2> <id-3>              # Human-only: several at once
5am campaigns reject <deployment-id> --note "Off-brand hook"   # Human-only
5am campaigns resume <deployment-id>    # Human-only: paused -> active (or back to review)
5am campaigns pause <deployment-id>
```

- **Every deployment belongs to a campaign.** Pass `--campaign` (400 `campaign_required`
  without it). Inside a workflow run of the campaign's own workflow the campaign is
  inferred; a different `--campaign` there is 409 `campaign_mismatch`. The network must
  be one of the campaign's (409 `network_not_in_campaign`), `--catalog` (optional) must be
  the campaign's catalog (409 `catalog_mismatch`), `--sku` must be in that catalog and
  match the campaign's filter (409 `sku_not_in_campaign`), and an ended campaign takes
  nothing (409 `campaign_ended`).
- **`campaigns list`** returns `{ deployments, next }`, newest first by
  `(updated_at, id)`, with `--limit` as the page size (1..500, default 100).
  Preserve the filters and pass `next` as `--cursor` until it is null, or use `--all`.
  `--all` and `--cursor` cannot be combined.
  Use every page when counting live campaigns, networks or committed budgets. Invalid
  cursors are 400 `invalid_cursor`. Paging is not a snapshot: concurrent updates can
  move rows, so refresh the list when processing live changes.
- **`--render <render-id>`** stages a delivered `campaign render` of the same campaign:
  the server fills the asset, and the SKU when `--sku` is absent. With `--campaign`, a
  `--locale` or `--aspect` you leave out is read from the render; without it, pass both.
- **The daily cap.** The account cap (`daily_budget_cap_cents`, per network) sums the
  daily budgets of the CAMPAIGNS that have an `active` or `fatigued` ad on that network
  (a tired ad keeps spending until paused); an ad of an already-live campaign adds
  nothing. It is checked when an ad goes live (approve, resume, or a stage that goes
  straight to `active`) and answers 400 `budget_cap_exceeded`; a campaign with no daily
  budget for the network answers 409 `campaign_budget_required`. It counts committed
  budgets, not measured spend. Networks may overspend a day's budget: Meta by up to 75%,
  Google up to twice a day's budget (never more than 30.4 times it in a month). A Google
  campaign's budget must also reach Google's daily floor (409
  `budget_below_network_minimum`; see "Google's daily floor" above).
- **Staging spends nothing,** so it is bounded by count instead: at most `max_staged`
  ads waiting for review per network (default 500), else 409 `too_many_staged`.
- **`stage` is safe to retry.** Inside a workflow run the same variant (SKU, network,
  locale, aspect, template) answers the existing deployment with `replayed: true`
  (HTTP 200) instead of a duplicate; outside a run pass `--key <your-key>` for the
  same.
- **An agent's live request is staged instead.** Inside a workflow run or an AI
  character session, `--mode live` becomes `status = "staged"` with
  `guardrail_downgraded: true` and a `downgrade_reason` rather than an error when one of
  these stands in the way: `auto_publish_off` (the owner has not enabled
  `auto_publish_enabled` on that network), `campaign_paused`, `budget_cap`,
  `campaign_budget`, a network's code (`locale_needs_country`, `dsa_required`, ...) or
  `review_flagged` (the automatic review checks flagged the ad: a price or offer the
  SKU does not carry, no call to action, no product link, off brand, a locale outside
  the campaign, a missing asset; its `review_reasons` say which). A person's live
  stage into a paused campaign is 409 `campaign_paused`, and over a cap it is the 400
  above.
- **Every staged ad is checked, never refused for it:** a failed check sets
  `review_status: "flagged"` and `review_reasons` (`[{source, code, text}]`, `source`
  `check` or `ai`). Only the owner can approve a flagged ad.
- **Statuses:**
  - `approve` takes only a `staged` ad; an `active` one answers unchanged, and any
    other status is 409 `not_approvable`. With several ids (at most 200) it approves them
    in order until a cap stops it and prints `approved` and `refused` (each refusal with
    its `code`; a `budget_below_network_minimum` refusal also has `minimum_cents`,
    `currency` and `network`).
  - `reject` takes only a `staged` ad; `--note` is kept as `rejected_note`, and the
    campaign's character reads it. A rejected ad never comes back.
  - `resume` takes only a `paused` ad.
  - `pause` takes staged, active and tired ads; a rejected one is 409 `not_pausable`.
- `campaigns approve`, `reject`, `resume` and `policy` updates are **human-only**: refused
  with 403 `cli_token_not_allowed_here` inside workflow runs and AI character sessions. Do
  not retry them; report that the owner must approve (in the campaign's chat).
  `campaigns pause` is allowed everywhere, since it only reduces spend.
- **Policy values out of range** (a fraction of a cent, an amount above 10^14 cents, a
  CTR above 1, fewer than 100 impressions, a window outside 1 to 30 days, an attribution
  age outside 0 to 30 days, a thumbstop floor above 1) are refused with 400
  `invalid_policy`. Amounts are cents of the account's currency (1/100 of its major
  unit, for every currency): a dong or rupiah account types large numbers.
- **`campaigns policy` prints one of two shapes:** `{policies: [...]}` (meta, then google)
  with neither `--network` nor an update flag, and `{policy: {...}}` (one network) with
  `--network` or after an update.

### Closed-Loop Conversion Telemetry (`5am telemetry`)

```sh
5am telemetry ingest --deployment <deployment-id> --date 2026-10-14 \
  --impressions 12000 --clicks 60 --conversions 2 --spend-cents 15000 --revenue-cents 18000 \
  --video-3s-views 3000
5am telemetry ingest --from-file telemetry.json    # [{ "deployment_id": ..., "date": "2026-10-14", "impressions": ... }]
5am telemetry report --campaign <campaign-id>
5am telemetry fatigued --campaign <campaign-id> --all
```

- **Published ads need no uploads.** An ad published on a connected Meta or Google account
  has its results pulled from the network every hour. `telemetry ingest` is for simulated
  ads, or numbers from elsewhere.
- **Every event is ONE UTC DAY's numbers** for one deployment, never lifetime totals:
  `date` is `YYYY-MM-DD` (default today, UTC; at most 1 day ahead or 90 days back, else
  400 `invalid_telemetry` naming the event). An event SETS that day's value of each field
  it carries (`"replace": false` in a file adds to it instead); a field it leaves out keeps
  the day's value. A deployment's `impressions`, `clicks`, ... are the sum of its days.
  To backfill, send one event per day.
- `telemetry ingest --deployment` sends only the metric flags you pass; the day keeps
  every metric you leave out.
- **Fatigue reads a rolling window**: the network policy's last `fatigue_window_days` UTC
  days, ending today (default 3). CTR (`fatigue_ctr_threshold`) and thumbstop
  (`video_3s_views` over impressions, against `thumbstop_threshold`, default 0.2) need
  `fatigue_min_impressions` in the window; thumbstop counts only days that report
  3-second views, so it never applies to Google ads (Google reports none). ROAS (`min_roas_threshold`) and CPA (`max_cpa_cents`) wait until the ad
  is `attribution_days` old (default 3) and the window spent `min_spend_cents` (default
  4000), so late conversions do not flag a new ad. Only an `active` deployment can
  become `fatigued`, and it records the `fatigue_window` it was judged on. That marks its SKU fatigued for its own campaign only
  (pending again in that campaign's `campaign skus --pending`, untouched in any other
  campaign) and wakes that campaign's workflow; `triggered_campaigns` lists the campaigns
  woken. Staged, paused, rejected and already-fatigued deployments only get their metrics
  updated, so a replaced ad that keeps reporting poor numbers does not trigger another
  re-render. One unknown deployment id refuses the whole batch (404) before anything is
  written.
- `telemetry report` returns `summary` (with `blended_thumbstop` and `fatigue_windows`, the
  window each network judges on now), `winning_patterns` (top template/hook/aspect_ratio
  combinations by ROAS, with `thumbstop`), and `fatigued_deployments` (each with its
  `fatigue_window`) so a re-render can reuse proven winning templates. Filter it with
  `--campaign`, `--catalog` or `--network`.
- A winning pattern clears its network policy's own bars, listed in `thresholds`: ROAS at
  least `min_roas` (the policy's `min_roas_threshold`) or CTR at least `min_ctr` (twice its
  `fatigue_ctr_threshold`).
- `telemetry report` returns one page of `fatigued_deployments` (`--limit` 1..500,
  default 100); pass the answer's `next` as `--cursor` until it is null.
  `summary.fatigued_count` counts them all. The report has no `--all` option.
- `telemetry fatigued` returns `{ deployments, next }` and accepts `--limit`
  (1..500, default 100), `--cursor <next>` or `--all` to collect every page.
  `--all` and `--cursor` cannot be combined. Preserve filters when following cursors.
- **Money is in the account's currency**: `currency` on the report, on every deployment and
  on every policy (the connected Meta ad account's, else `USD`). Every `*_cents` field is
  1/100 of that currency's major unit, for every currency (1,234 yen is `123400`), so read
  amounts in it and never assume dollars. A report whose scope holds money in two
  currencies answers `currency: null`, with null money totals and each network's own in
  `summary.by_network`.

### The campaign-centred flow

A workflow program builds one campaign's ads. The campaign names it with `--workflow`,
and the campaign's trigger runs it when the campaign has pending work (a member SKU
changed in a sync, or one of its ads went tired).

1. The program declares a required string input named `campaign_id`; a campaign trigger
   fills it. Read the campaign's networks, locales and formats with
   `5am campaign get <campaign_id>`.
2. Read the work with `5am campaign skus <campaign_id> --pending --all`: only SKUs never
   rendered for this campaign, changed since, or tired, every page. Process that list
   once; do not loop until it is empty.
3. For each SKU, import its images and videos with
   `5am catalog import-media <catalog_id> --sku <sku> --limit 4 --wait --wait-timeout 5m`.
   Never download them yourself.
4. Build each ad with `5am ads draft --catalog <catalog_id> --sku <sku>` (code templates,
   no model call) and, to localize or adapt it,
   `5am ads generate --adapt ... --locale <locale> --catalog <catalog_id> --sku <sku>`.
   The claims come from the SKU; never write them. `ads generate` adds the SKU's ready
   videos as clips. Skip and report a SKU refused with `missing_benefit`,
   `sku_out_of_stock` or `sku_removed` (exit 2).
5. Render each film with `5am campaign render` (unmarked, on 5AM's servers). A 409
   `sku_out_of_stock` or `sku_removed` here, or from the stage (also `sku_changed`), skips
   the SKU: report it and never mark it rendered.
6. Stage each variant with `5am campaigns stage --campaign <campaign_id> ...` (inside the
   campaign's own workflow run the campaign is inferred anyway).
7. After a SKU's whole set of variants (every network, locale and format) is staged, run
   `5am campaign mark-rendered <campaign_id> <sku>`.
8. The campaign's AI character reviews the staged ads in its chat, and the owner approves
   them there. The program never approves.
