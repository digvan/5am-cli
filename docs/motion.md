# Motion graphics with `5am motion`

`5am motion` makes motion-graphics films from a brief: kinetic type, shapes,
counters, dials, charts, 3D point clouds and your own photos and video clips, cut on
a beat grid with a composed score and, if you like, a narrator. It runs the same engine as [Motion Studio](https://5am.app/ai-studio?mode=motion)
on 5am.app, so a film made in the terminal is the same document, and renders the
same pixels, as one made on the web.

A film is a **MotionDoc**: a small JSON file (`*.motion.json`). You can generate one,
revise it in plain language, edit it by hand, narrate it, watch it play in your
browser and look at it frame by frame for free, and export it as an MP4. Sample films with contact sheets: [`examples/motion/`](../examples/motion/README.md).

Requires CLI **v1.5.0** or later.

## Setup

```sh
5am update                    # the CLI
5am update --runtime-only     # the optional runtime (shared with image editing)
5am login                     # a token with write scope to export
```

| Command | Needs |
|---|---|
| `lint`, `fonts` | the runtime and Node.js 20+ |
| `generate`, `revise`, `narrate` | the above, a login, and Gemini access (your own key or AI credits); `--clip` also Chrome or Chromium, and FFmpeg for clips Chrome cannot play |
| `stills`, `sheet` | the runtime, Node.js 20+, Chrome or Chromium, and FFmpeg (a login only for library photos and clips) |
| `preview` | the runtime, Node.js 20+, and a browser to watch in |
| `render`, `finalize` | all of the above, and a login with **write** scope |

The CLI finds Chrome through `--browser`, `CHROME_PATH` or the usual install
locations, and FFmpeg through `--ffmpeg`, `$FFMPEG` or `PATH`. It downloads neither.
Fonts download from the 5AM fonts CDN on first use, checked against a hash, and are
cached in `~/.5am/cache/motion/fonts`. To render without a network connection,
download them all once and name the folder:

```sh
5am motion fonts --dir ~/motion-fonts            # every font a film can use, about 45 MB
export FIVEAM_MOTION_FONTS=~/motion-fonts
```

## Quick start

```sh
5am motion generate --brief "A 10 second launch film for a coffee app: bold type, a counter to 10,000 cups, an end card" \
  --format 9:16 --duration 10 -o coffee.motion.json
5am motion lint coffee.motion.json
5am motion sheet coffee.motion.json -o coffee.png
5am motion revise coffee.motion.json "warmer colours, slower ending" --in-place
5am motion narrate coffee.motion.json --script "Mornings, sorted. Order ahead and skip the line."
5am motion preview coffee.motion.json
5am motion render coffee.motion.json -o coffee.mp4 --dry-run
5am motion render coffee.motion.json -o coffee.mp4 --fps 30
```

Every command prints one JSON document on stdout; progress goes to stderr. No
command overwrites a file without `--overwrite`.

## What it costs

| Command | Cost |
|---|---|
| `generate`, `revise` | Gemini access: one model call, two when the layout needs a repair |
| `narrate` | Gemini access: one speech call |
| `lint`, `stills`, `sheet`, `preview`, `fonts` | free |
| `render` | **20 AI credits** per export, on every account, including accounts with their own Gemini key |

Local photos are described with Gemini once (one small call each, cached), unless
you pass `--no-describe`.

## Commands

### `generate`

```sh
5am motion generate --brief "..." [--format 16:9|9:16|1:1] [--duration 6-60] \
  [--sound pulse|house|ambient|minimal|none] [--tempo 84-160] [--photo ...] -o film.motion.json
```

Writes a new film. The brief can come from `--brief-file` instead (`-` reads stdin).
The model composes the film; a checker then looks for layout problems (text running
into text or photos, unreadable timing, low contrast), asks for one repair when it
finds some, and settles what it can in code. The result reports what is left:

```json
{ "output": "coffee.motion.json", "title": "…", "format": "9:16", "duration": 10, "scenes": 5,
  "photos": 0, "model": "gemini-3.8-flash", "calls": 1, "repaired": false, "tidied": [],
  "fixes": 0, "issues": [], "warnings": [] }
```

A film with `fixes` left still renders; a `revise` that names the issues usually
clears them.

### `revise`

```sh
5am motion revise film.motion.json "make the headline shorter and the colours warmer" -o v2.motion.json
5am motion revise film.motion.json "slower ending" --in-place
```

Sends the film and your request to the model. `--format` and `--duration` re-lay
out or retime the film (positions are relative, so a 16:9 film becomes a 9:16 one
without edits). `--sound` swaps the music bed.

### Photos

`--photo` adds your photos to a film (up to 12), on `generate` or `revise`:

```sh
5am motion generate --brief "Our wedding day in five beats" --photo ./ceremony.jpg --photo ./dance.heic -o wedding.motion.json
5am motion generate --brief "Trip highlights" --photo media:<library-media-id> -o trip.motion.json
```

- **Formats:** JPEG, PNG, WebP, GIF and HEIC (HEIC is converted on your machine).
- **Local photos** are stored in the film as paths relative to it
  (`"src": "file:photos/ceremony.jpg"`): keep them beside the film when you move it.
- **Library photos** (`media:<id>`) are stored by their library id, as Motion
  Studio stores them, and downloaded when the film renders.
- **On `revise`**, `--photo` replaces the film's photos. A photo already in the film
  keeps its place in the layers.

### Video clips

`--clip` adds video clips (up to 4), on `generate` or `revise`, from files or your
library:

```sh
5am motion generate --brief "A product demo built around the screen recording" --clip ./demo.mov -o demo.motion.json
5am motion revise demo.motion.json "open on the dashboard close-up" --clip ./demo.mov --clip media:<library-media-id> --in-place
```

- **Any format FFmpeg reads.** The CLI opens each clip in Chrome first. A clip
  Chrome cannot play as it is (ProRes, some HEVC, an unusual sound track) gets a copy
  made with FFmpeg, cached in `~/.5am/cache/motion/proxies`; the film still names
  your file.
- **Stored like photos:** local clips as paths relative to the film, library clips
  by their id.
- **On `revise`**, `--clip` replaces the film's clips.
- **Their sound** is muted unless the clip's layer sets a `volume` (0 to 1), as in
  Motion Studio: ask for it in the brief or a `revise`, or edit the film.

### `narrate`

```sh
5am motion narrate film.motion.json --script "..." [--voice Kore] [--mood "bright and quick"]
5am motion narrate film.motion.json --script-file script.txt --overwrite
```

Speaks the script with the same voices and speech model as Motion Studio's Sound
tab, and saves the take beside the film: `film.narration.wav` and
`film.narration.json`. From then on `lint`, `stills`, `sheet`, `preview` and `render`
include it (pass `--no-narration` to leave it out, or `--narration other.narration.json`
for another take). The music lowers under the voice in the export, as on the web.

- **Fit the film.** A take longer than the film is refused, never cut or sped up:
  shorten the script or lengthen the film. About 45 to 65 words fill 30 seconds.
  The speech call is made either way.
- **Settle the film's length first.** After a `revise`, the old take still plays;
  narrate again with `--overwrite` if the words should change.
- **Voices:** Kore (the default), Puck, Charon, Zephyr, Aoede, Sulafat and the other
  Gemini voices; a wrong name lists them all.

### `lint`

```sh
5am motion lint film.motion.json [--format 9:16] [--duration 12] [--fps 30] [--resolution 1440p]
```

Free and offline. It prints:

- what the normalizer would change (`warnings`);
- layout issues: `issues`, each of level `fix` or `note`, and `fixes`, the count of
  `fix` ones;
- the frame count, the render size and the fonts the film loads.

It exits 0 even with issues; read `fixes`.

### `stills` and `sheet`

```sh
5am motion stills film.motion.json --times 0.5,4,9.5 --out-dir stills
5am motion stills film.motion.json --frames 0,120,240 --out-dir stills --fps 30
5am motion sheet film.motion.json -o sheet.png --count 24
```

Free PNGs drawn exactly as the export would draw them, watermark included: chosen
frames (up to 48), or a contact sheet of evenly spaced ones. Look at a sheet before
you export. A checker cannot judge a weak contrast or a word on a busy part of a
photo; your eyes can.

### `preview`

```sh
5am motion preview film.motion.json [--no-open]
```

Opens the film in your browser with its sound: play, pause, scrub and loop (space and
the arrow keys work too). Leave it open while you edit: whenever you save the film,
or narrate it again, the page updates in place. A save that does not load keeps the
last good film playing and shows the error. The preview draws at your window's size,
without the export's motion blur; `sheet` shows exact frames. Stop it with Ctrl-C.

### `render`

```sh
5am motion render film.motion.json -o film.mp4 [--fps 60|30] [--resolution 1080p|1440p] [--album <name-or-id> | --new-album <name>]
5am motion render film.motion.json -o film.mp4 --dry-run
```

An export, in this order:

1. The CLI loads every font, photo, clip and the narration. A film that cannot
   render stops here, and nothing is charged.
2. It reserves the export (20 AI credits). Without enough credits it stops here,
   and nothing is rendered.
3. It renders every frame and composes the sound.
4. It charges the reservation and writes the MP4. `--album` / `--new-album` also
   upload it to your library.

Ctrl-C or a failed render releases the reservation.

`--dry-run` does step 1 and prints the price, size, frame count and whether the film
has sound, without rendering or charging anything.

The MP4 is H.264 and AAC, 1080 pixels on the short side by default (1440 with
`--resolution 1440p`), at 60 fps by default. Every frame has motion blur, film
grain and a small "Made with 5AM" mark. On a recent Mac, rendering runs at about 28
frames a second at 1080x1920, so a 15-second film takes about 30 seconds at 60 fps,
and half that at 30. `--workers` sets how many browser pages draw at once; the
default suits the machine's cores and memory.

### `finalize`

If the charge in step 4 is refused (credits ran out while rendering), the MP4 is
kept for 24 hours and the error names the command that pays for it:

```sh
5am credits buy                          # a payment link (pay on any device), then waits
5am motion finalize <requestId>          # pays and saves the MP4
5am motion finalize                      # lists renders waiting for payment
```

Do not render again to recover: a second render is a second export. `finalize`
never charges twice, so it is also safe after an uncertain outcome.

## The film file

A MotionDoc is plain JSON. The samples in [`examples/motion/`](../examples/motion/README.md)
are a good start, and `lint` checks a hand edit.

```json
{
  "version": 1,
  "title": "Quarter in motion",
  "format": "1:1",
  "duration": 6,
  "tempo": 120,
  "palette": { "bg": "#060D0C", "ink": "#060D0C", "paper": "#EFEAE0", "accent": "#EA580C", "accent2": "#5EEAD4", "muted": "#0D9488" },
  "fonts": { "display": "inter", "body": "inter", "mono": "jetbrains-mono" },
  "sound": { "style": "minimal" },
  "scenes": [
    { "id": "bars", "beats": 12, "bg": "bg", "layers": [
      { "kind": "graph", "style": "bars", "values": [12, 19, 27, 41], "labels": ["Q1", "Q2", "Q3", "Q4"], "draw": [0.3, 1.8] }
    ] }
  ]
}
```

(That palette is the built-in `dawn`, the one the sample films use.)

- **Time is in beats**, counted within each scene. The tempo is adjusted so a whole
  number of bars fills the duration exactly (10 s at 120 BPM is 5 bars, 20 beats).
- **Sizes** are design units, where the frame's short side is 1000.
- **Positions:** `x` and `y` are fractions of the half-frame (`x: -1` is the left
  edge, `y: 1` the bottom), so a layout carries across 16:9, 9:16 and 1:1.
  `dx`/`dy` add offsets in design units.
- **Animation:** any number can be animated with keyframes,
  `[[beat, value, ease], ...]`.
- **Colours** name a palette token (`bg`, `ink`, `paper`, `accent`, `accent2`,
  `muted`) or a hex value.
- **Layers:** `text` (kinetic type), `shape` (morphing shapes), `path` (ribbons),
  `grid` (dot fields), `mesh` (3D points), `particles`, `rings` (text rings),
  `counter`, `clock`, `lines`, `note` (handwritten notes), `dial`, `graph` (curves
  and charts), `pill` (buttons and chips), `cursor`, `image` and `photos` (your
  photos), `video` (your clips), and `group`.
- **Scene transitions** (`enter`): `cut`, `circle`, `wipe`, `push`, `whip`, `zoom`,
  `split`, `blinds`, `tiles`, `shutter`, `glitch`, `morph`, `flood`, `iris`.
- **Fonts:** `inter`, `jetbrains-mono`, or a font from the 5AM catalog (Latin
  display faces, serif, handwriting, Japanese, Korean, Arabic and Persian).

The engine is forgiving: unknown fields are dropped, numbers are clamped and beat
totals are rescaled, and `lint` reports each repair as a warning.

## Agents and scripts

- **Iterate on the film, not the MP4.** `lint` and `sheet` are free; `revise` makes
  changes; `render` once at the end.
- **Read the JSON.** For `generate`, the film path is `.output`. For `render`, the
  MP4 path is `.output` and the charge is `.credits`. A dry run has `.dryRun: true`
  and no `.output`.
- **Never repeat a paid render after an error.** A refused final charge is recovered
  with `5am motion finalize <requestId>`.
- **AI-character tokens cannot export.** Use a personal access token with write scope.
- **Never run `preview` unattended.** It waits for a person and never exits on its
  own; look at a film with `sheet`.
- **Managed cloud workflows** have the runtime and every font installed: generate,
  narrate, check and render there as anywhere else.

## Not in the CLI

Exports without the "Made with 5AM" mark (Ad Maker on 5am.app), and sending a film
to Motion Studio on the web.

## Troubleshooting

| Message | What to do |
|---|---|
| `Motion needs the image-edit runtime` | `5am update --runtime-only` |
| `the installed runtime has no Motion support` / `incompatible motion runtime` | Update the CLI and the runtime together: `5am update`, then `5am update --runtime-only` |
| `Motion Studio is not enabled on this server` | Motion Studio is not available on that server |
| `insufficient_scope` | Your token is read-only; create one with write scope in Settings → CLI Access Tokens |
| `not enough AI credits: this export costs 20 credits and you have …` | `5am credits buy` (a payment link you can pay on your phone without signing in), then render; nothing was rendered or charged |
| `AI credits are paused right now, so exports cannot be paid for` | AI credits are paused for a while on 5am.app; nothing was charged, try again later |
| `ffmpeg not found` | Install FFmpeg, or pass `--ffmpeg /path/to/ffmpeg` |
| Chrome not found | Install Chrome or Chromium, or pass `--browser` / set `CHROME_PATH` |
| `video clips in Motion films are not enabled on this server` | Video clips are not available on that server yet; use photos |
| `a clip this browser cannot decode needs a proxy made with ffmpeg` | Install FFmpeg, or pass `--ffmpeg` |
| `The voice is …s long. Shorten the script to fit …s` | Shorten the script, or lengthen the film, and narrate again |
| `The narration is …s long and the film …s` | The film got shorter after the take: `narrate --overwrite`, or `--no-narration` |
| Frames with wrong colours or stripes | A graphics driver problem: render with `FIVEAM_MOTION_PIXELS=rgba` |
