# Motion graphics with `5am motion`

`5am motion` makes motion-graphics films from a brief: kinetic type, shapes, counters, dials, charts, 3D point clouds and your own photos and video clips, cut on a beat grid with a composed score and, if you like, a narrator. It runs the same engine as [Motion Studio](https://5am.app/ai-studio?mode=motion) on 5am.app, so a film made in the terminal is the same document, and renders the same pixels, as one made on the web.

A film is a **MotionDoc**: a small JSON file (`*.motion.json`). You can generate one, revise it in plain language, edit it by hand, narrate it, watch it play in your browser and look at it frame by frame for free, and export it as an MP4. Sample films with contact sheets: [`examples/motion/`](../examples/motion/README.md).

Requires CLI **v1.5.0** or later. Skia, `motion doctor`, `--engine` and the `lottie` layer are **from CLI v1.7.0**; earlier releases draw every still, sheet and render with Chrome or Chromium.

## Setup

```sh
5am update                    # the CLI
5am update --runtime-only     # the optional runtime (shared with image editing), then Skia, which draws the films
5am login                     # a token with write scope to export
5am motion doctor             # from CLI v1.7.0: checks Skia, the engine, and reports Chrome; free
```

| Command | Needs |
|---|---|
| `lint`, `fonts` | the runtime and Node.js 20+ |
| `generate`, `revise`, `narrate` | the above, a login, and Gemini access (your own key or AI credits); `--clip` also Skia and FFmpeg |
| `stills`, `sheet` | the runtime, Node.js 20+, Skia and FFmpeg (a login only for library photos and clips) |
| `preview` | the runtime, Node.js 20+, and a browser to watch in; films with video clips also Chrome or Chromium |
| `doctor` | the runtime and Node.js 20+; it checks Skia and Chrome, and needs Chrome only with `FIVEAM_MOTION_ENGINE=chrome` |
| `render`, `finalize` | what `stills` needs, and a login with **write** scope |

The CLI finds FFmpeg through `--ffmpeg`, `$FFMPEG` or `PATH`, and Chrome through `--browser`, `CHROME_PATH` or the usual install locations. It downloads neither. On Linux as root (cloud agent VMs and containers), it starts Chrome without Chrome's own sandbox, which Chrome requires there.

### Engines

**Skia draws the films** (from CLI v1.7.0; before it, read Chrome wherever this page says Skia). Stills, sheets and renders are drawn by Skia, a native graphics library that needs no browser. `5am update --runtime-only` installs it for your computer right after the runtime, with the npm that comes with Node.js, and prints what it installed. When it cannot (npm is missing, the computer is offline, or there is no prebuilt Skia for the platform), the runtime is still installed and the command says why and exits 1. Each still, sheet and render then tries the install once more itself, and if that fails too it stops before anything is charged with:

```
Skia isn't installed: <reason>. Run `5am update --runtime-only` again, or render with --engine chrome.
```

Fix the reason and run `5am update --runtime-only` again. Nothing switches to Chrome on its own.

**Chrome is the fallback.** `--engine chrome` on `stills`, `sheet` and `render`, or `FIVEAM_MOTION_ENGINE=chrome` for every command (the flag wins), draws with headless Chrome instead, as CLI v1.6.2 and earlier did. `skia` and `chrome` are the only engines. Whatever the engine, `5am motion preview` plays the film in your browser and opens its video clips in Chrome. Otherwise a computer that renders with Skia needs no Chrome at all.

Fonts download from the 5AM fonts CDN on first use, checked against a hash, and are cached in `~/.5am/cache/motion/fonts`. To render without a network connection, download them all once and name the folder:

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
5am motion podcast episode.mp3 --brief "A minute for people who build with AI agents" -o clip.motion.json
5am motion preview coffee.motion.json
5am motion render coffee.motion.json -o coffee.mp4 --dry-run
5am motion render coffee.motion.json -o coffee.mp4 --fps 30
```

Every command prints one JSON document on stdout; progress goes to stderr. No command overwrites a file without `--overwrite`.

## What it costs

| Command | Cost |
|---|---|
| `generate`, `revise` | Gemini access: one model call, two when the layout needs a repair |
| `narrate` | Gemini access: one speech call |
| `lint`, `stills`, `sheet`, `preview`, `fonts` | free |
| `render` | **20 AI credits** per export, on every account, including accounts with their own Gemini key; a podcast clip from `podcast` is **100 AI credits** (from CLI v1.8.4) |

Local photos are described with Gemini once (one small call each, cached), unless you pass `--no-describe`.

## Commands

### `generate`

```sh
5am motion generate --brief "..." [--format 16:9|9:16|1:1] [--duration 6-90] \
  [--sound pulse|house|ambient|minimal|none] [--tempo 84-160] [--photo ...] \
  [--cues cues.json] [--audio voice.m4a] -o film.motion.json
```

Writes a new film. The brief can come from `--brief-file` instead (`-` reads stdin). The model composes the film; a checker then looks for layout problems (text running into text or photos, unreadable timing, low contrast), asks for one repair when it finds some, and settles what it can in code. The result reports what is left:

```json
{ "output": "coffee.motion.json", "title": "…", "format": "9:16", "duration": 10, "scenes": 5,
  "photos": 0, "model": "gemini-3.8-flash", "calls": 1, "repaired": false, "tidied": [],
  "fixes": 0, "issues": [], "warnings": [] }
```

A film with `fixes` left still renders; a `revise` that names the issues usually clears them.

### `revise`

```sh
5am motion revise film.motion.json "make the headline shorter and the colours warmer" -o v2.motion.json
5am motion revise film.motion.json "slower ending" --in-place
```

Sends the film and your request to the model. `--format` and `--duration` re-lay out or retime the film (positions are relative, so a 16:9 film becomes a 9:16 one without edits). `--sound` swaps the music bed. From CLI v1.8.4, `--cues cues.json` keeps a film on its soundtrack ([On a soundtrack](#on-a-soundtrack-cues-and-fit)).

### Photos

`--photo` adds your photos to a film (up to 12), on `generate` or `revise`:

```sh
5am motion generate --brief "Our wedding day in five beats" --photo ./ceremony.jpg --photo ./dance.heic -o wedding.motion.json
5am motion generate --brief "Trip highlights" --photo media:<library-media-id> -o trip.motion.json
```

- **Formats:** JPEG, PNG, WebP, GIF and HEIC (HEIC is converted on your machine).
- **Local photos** are stored in the film as paths relative to it (`"src": "file:photos/ceremony.jpg"`): keep them beside the film when you move it.
- **Library photos** (`media:<id>`) are stored by their library id, as Motion Studio stores them, and downloaded when the film renders.
- **On `revise`**, `--photo` replaces the film's photos. A photo already in the film keeps its place in the layers.

### Video clips

`--clip` adds video clips (up to 4), on `generate` or `revise`, from files or your library:

```sh
5am motion generate --brief "A product demo built around the screen recording" --clip ./demo.mov -o demo.motion.json
5am motion revise demo.motion.json "open on the dashboard close-up" --clip ./demo.mov --clip media:<library-media-id> --in-place
```

- **Any format FFmpeg reads.** Skia reads each clip through FFmpeg and the `ffprobe` beside it, ProRes and HEVC included. With `--engine chrome`, the CLI opens each clip in Chrome first, and a clip Chrome cannot play as it is (ProRes, some HEVC, an unusual sound track) gets a copy made with FFmpeg, cached in `~/.5am/cache/motion/proxies`; the film still names your file.
- **Stored like photos:** local clips as paths relative to the film, library clips by their id.
- **On `revise`**, `--clip` replaces the film's clips.
- **Their sound** is muted unless the clip's layer sets a `volume` (0 to 1), as in Motion Studio: ask for it in the brief or a `revise`, or edit the film.

### `narrate`

```sh
5am motion narrate film.motion.json --script "..." [--voice Kore] [--mood "bright and quick"]
5am motion narrate film.motion.json --script-file script.txt --overwrite
```

Speaks the script with the same voices and speech model as Motion Studio's Sound tab, and saves the take beside the film: `film.narration.wav` and `film.narration.json`. From then on `lint`, `stills`, `sheet`, `preview` and `render` include it (pass `--no-narration` to leave it out, or `--narration other.narration.json` for another take). The music lowers under the voice in the export, as on the web.

- **Fit the film.** A take longer than the film is refused, never cut or sped up: shorten the script or lengthen the film. About 45 to 65 words fill 30 seconds. The speech call is made either way.
- **Settle the film's length first.** After a `revise`, the old take still plays; narrate again with `--overwrite` if the words should change.
- **Voices:** Kore (the default), Puck, Charon, Zephyr, Aoede, Sulafat and the other Gemini voices; a wrong name lists them all.
- **A recording instead** (from CLI v1.8.4): `--audio voice.m4a` uses a recording you have (any audio or video file) as the take, with no speech call. It stays in stereo at 48 kHz and is mixed the same way.

### On a soundtrack: cues and `fit`

From CLI v1.8.4. When the audio comes first (a voice-over with clips of a podcast between its lines), lay the film out on it instead of timing scenes by hand:

```sh
5am motion generate --brief "A clip for episode 781" --format 9:16 --cues cues.json --audio voice.m4a -o clip.motion.json
5am motion fit clip.motion.json --cues cues.json --in-place
```

The cue sheet says when each scene starts and what it shows; `say` (optional) is what is heard then:

```json
{ "cues": [
  { "at": 0, "show": "Cover: the podcast, episode 781" },
  { "at": 10.3, "show": "Airbnb is building a company brain for AI agents" },
  { "at": 23.4, "show": "EVEREST: the company brain", "say": "we call it Project Everest" }
] }
```

- `generate --cues` writes one scene per cue and starts each exactly on its second (to the frame); `revise --cues` keeps a revision on them. `--audio` makes the recording the film's take and its length (up to 90 seconds).
- `fit` moves an existing film's scenes onto a sheet for free, with no model call; it needs one scene per cue. Its result lists the scenes it stretched by more than half.
- The first cue is at 0; a scene runs at least 1 second and at most 64 beats (about 30 seconds at 128 BPM). Do not render a fitted film with `--duration`: that retimes every scene evenly, off the cues.
- A film on a soundtrack shows only what the cues give: no number, statistic or name they do not state.

### `podcast`: a clip of an episode in one command

From CLI v1.8.4. Real clips of the conversation, joined by narrator lines, with a film laid out on them:

```sh
5am motion podcast episode.mp3 --brief "A minute for people who build with AI agents" -o clip.motion.json
5am motion podcast episode.mp3 --script-only -o clip.motion.json        # write the script and stop
5am motion podcast episode.mp3 --script clip.script.json -o clip.motion.json --overwrite
5am motion render clip.motion.json -o clip.mp4
```

Gemini reads the episode's transcript (made and cached if you do not pass `--transcript`), picks the guest's strongest moments by transcript line, so every cut lands on what was said, and writes a few narrator lines between them, each part with what the screen shows. The narrator lines are spoken (`--voice`, `--mood`), the clips are cut at word boundaries, every part is brought to the same loudness, and the film's scenes start as their parts are heard. The episode's cover art becomes the film's photo when the file has one.

- **The script is yours to edit.** `clip.script.json` lists the parts in seconds: change a narrator line, move a clip's `clip: [from, to]`, reorder, then run again with `--script`. Only the lines whose words changed are spoken again.
- **Beside the film:** the script, the cue sheet (`clip.cues.json`), `clip.parts/` (spoken lines and `soundtrack.wav`) and the take.
- **Cost:** the transcription when it is not cached, one call for the script, one speech call per new line, and the film, all on your Gemini access. The export is **100 AI credits**: `render` prices a film as a podcast clip while its `clip.script.json` is beside it. It carries the "Made with 5AM.app" mark, as every CLI film does.

From CLI v1.8.5:

- **An episode link works too.** Give an HTTPS link to the audio, such as the MP3 in your RSS feed, and it is downloaded first. Links to private addresses, responses that are not audio, files over 512 MB and episodes over three hours are refused.
- **Ask for a change in plain words.** `--from` and `--revise` make a new version of a film you already have:

  ```sh
  5am motion podcast --from clip.motion.json --revise "Use the later version of that quote" -o v2.motion.json
  ```

  A change to the look ("bigger cards") keeps the soundtrack and does not fetch the episode again. A change to the quotes or the narration rewrites the script from the same transcript, and only the lines that changed are spoken again. Ask for a new narrator ("use Puck", "sound brighter") and every line is spoken again in the new voice.
- **Your look.** `--brand-kit default`, or a kit's name or ID, dresses the film in your account's brand kit, its logo included.
- **Never past 90 seconds.** A soundtrack that runs past the film's 90 seconds is planned again once, shorter, and the result says how long the first one ran (`shortenedFrom`).

From CLI v1.8.6:

- **Names spelled as the episode spells them.** A transcript can mishear a name. `--episode-info episode.json` gives the script writer the episode's own facts: `show`, `title`, `number`, `author`, `people` (`[{"name": "...", "role": "guest"}]`) and `notes` (the show notes as text). Without it, the file's own tags stand in (an MP3's title, album, artist and comment). Names are spelled from these facts; every other fact still comes from what is said in the episode, because show notes carry sponsor reads and offer codes. The facts used are saved beside the film as `clip.episode.json`.
- **A fact check before you pay.** The result's `factCheck` lists what the film shows that the episode does not give: a number nobody says (a counter or a dial is read where it lands, and a number said in words, like "two point four million", counts as said), or a name spelled unlike the episode's. It changes nothing: fix the script, or ask for a change with `--revise`, before `motion render`.

  ```json
  "factCheck": {"numbers": 3, "names": 2, "findings": [
    {"kind": "number", "scene": 5, "layer": "dial", "text": "84%", "value": "84%"},
    {"kind": "name", "scene": 1, "layer": "text", "text": "DR. ALISON REYES", "value": "ALISON", "expected": "Allison"}]}
  ```

### `lint`

```sh
5am motion lint film.motion.json [--format 9:16] [--duration 12] [--fps 30] [--resolution 1440p]
```

Free and offline. It prints:

- what the normalizer would change (`warnings`);
- layout issues: `issues`, each of level `fix` or `note`, and `fixes`, the count of `fix` ones;
- the frame count, the render size and the fonts the film loads.

It exits 0 even with issues; read `fixes`.

### `stills` and `sheet`

```sh
5am motion stills film.motion.json --times 0.5,4,9.5 --out-dir stills
5am motion stills film.motion.json --frames 0,120,240 --out-dir stills --fps 30
5am motion sheet film.motion.json -o sheet.png --count 24
```

Free PNGs drawn exactly as the export would draw them, watermark included: chosen frames (up to 48), or a contact sheet of evenly spaced ones. Look at a sheet before you export. A checker cannot judge a weak contrast, a word on a busy part of a photo or a fact the brief never gave; your eyes can.

### `preview`

```sh
5am motion preview film.motion.json [--no-open]
```

Opens the film in your browser with its sound: play, pause, scrub and loop (space and the arrow keys work too). Leave it open while you edit: whenever you save the film, or narrate it again, the page updates in place. A save that does not load keeps the last good film playing and shows the error. The preview draws at your window's size, without the export's motion blur; `sheet` shows exact frames. Stop it with Ctrl-C.

### `render`

```sh
5am motion render film.motion.json -o film.mp4 [--fps 60|30] [--resolution 1080p|1440p] [--album <name-or-id> | --new-album <name>]
5am motion render film.motion.json -o film.mp4 --dry-run
```

An export, in this order:

1. The CLI loads every font, photo, clip and the narration. A film that cannot render stops here, and nothing is charged.
2. It reserves the export (20 AI credits; 100 for a podcast clip). Without enough credits it stops here, and nothing is rendered.
3. It renders every frame and composes the sound.
4. It charges the reservation and writes the MP4. `--album` / `--new-album` also upload it to your library.

Ctrl-C, a stop signal (SIGTERM) or a failed render releases the reservation. A render killed outright (a command timeout that kills the process, a restart) cannot, so its reservation stays for 24 hours; see [`finalize`](#finalize) for releasing it sooner.

`--dry-run` does step 1 and prints the price, size, frame count and whether the film has sound, without rendering or charging anything.

The MP4 is H.264 and AAC, 1080 pixels on the short side by default (1440 with `--resolution 1440p`), at 60 fps by default. Every frame has motion blur, film grain and a small "Made with 5AM.app" mark. With Skia on an Apple M1 Max, a 15-second 9:16 film at 1080x1920 rendered in 42 to 54 seconds at 60 fps (17 to 22 frames a second) and in about 33 seconds at 30 fps, measured while other work was running on the computer; a smaller computer takes longer. `--workers` sets how many workers draw at once (Skia's threads, or Chrome's pages with `--engine chrome`); the default suits the machine's cores and memory.

### `finalize`

If the charge in step 4 is refused (credits ran out while rendering), the MP4 is kept for 24 hours and the error names the command that pays for it:

```sh
5am credits buy                          # a payment link (pay on any device), then waits
5am motion finalize <requestId>          # pays and saves the MP4
5am motion finalize                      # lists the renders kept on this computer
5am motion finalize --unfinished         # releases the reservations of renders that stopped partway
```

Do not render again to recover: a second render is a second export. `finalize` never charges twice, so it is also safe after an uncertain outcome.

From CLI v1.6.1, the list gives each kept render a `state` and what to do next:

| `state` | Meaning | What to do |
|---|---|---|
| `rendered` | every frame is in the kept MP4, waiting for payment | `5am motion finalize <requestId>` |
| `rendering` | another process is still on it | wait for it to finish |
| `stopped` | it ended before its last frame (killed or crashed): there is nothing to pay for | `5am motion finalize --unfinished` releases its reservation |

**Unfinished exports.** An account can hold at most 10 reserved, unpaid exports at a time. Renders that finish, fail or are stopped with Ctrl-C never get near that, but each render killed partway keeps one for 24 hours, and an 11th export is refused with `too_many_pending_exports`. From CLI v1.6.1 the error says how many are held and when the oldest clears; run `5am motion finalize --unfinished` on the computer that made them, or wait for that time.

### `doctor`

```sh
5am motion doctor [--browser /path/to/chrome]
```

From CLI v1.7.0. Free, and it renders nothing. It checks the engine your renders use first, then the other one: it loads Skia and draws one pixel with it, and launches Chrome the way `--engine chrome` does. On a computer with Skia and no Chrome:

```json
{ "browser": "", "ok": true, "engine": "skia",
  "chrome": { "ok": false, "error": "No executable Chrome/Chromium found. ..." },
  "skia": { "ok": true, "nativeCanvasVersion": "1.0.11" } }
```

`engine` is the engine renders use on this computer: `skia`, or `chrome` with `FIVEAM_MOTION_ENGINE=chrome`. Only that engine decides `ok` and the exit code: with Skia, a Chrome that does not launch is reported in `chrome` (and on stderr) and the check still passes; with Chrome, a missing Skia is reported and passes. When the engine renders use fails, `ok` is `false`, its block has the reason in `error`, and the command exits 1. `browser` is the Chrome that launched, or `""`. Run it on a new computer, or in the environment a scheduler or an agent renders in.

## The film file

A MotionDoc is plain JSON, saved as `*.motion.json`. `generate` and `revise` write one; this section is the whole format, so a person or an agent can write or edit a film by hand. Every field is optional unless its table says **required**, and a field left out means its default. After each edit, run `5am motion lint`: it prints what the engine repaired and the layout problems left (see [What the engine repairs](#what-the-engine-repairs)). The [sample films](#sample-films) are worked examples.

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

(That palette is the built-in `dawn`, the one the sample films use. Six seconds at 120 BPM is 3 bars, so the one scene is 12 beats.)

### Units and coordinates

- **Beats.** Time is counted in beats, four to a bar, and each scene counts its own beats from 0. A beat lasts 60 / BPM seconds (0.5 s at 120 BPM).
- **Tempo.** `tempo` is a target. The engine takes the whole number of bars nearest to `duration x tempo / 240`, keeps the tempo between 84 and 160 BPM, and nudges it so those bars fill the duration exactly: 6 s at 120 BPM is 3 bars (12 beats), 10 s at 120 is 5 bars (20 beats), 15 s at 128 is 8 bars (32 beats). The scenes' `beats` should add up to that total. When they do not, every scene is stretched or squeezed to fit, on a half-beat grid, with a warning, and the beat fields inside each scene move with it.
- **Design units.** Sizes, widths, radii and offsets are design units, where the frame's short side is 1000: a 16:9 frame is about 1778 x 1000 units, 9:16 is 1000 x 1778 and 1:1 is 1000 x 1000. The export's resolution never changes a layout.
- **Positions.** `x` and `y` are fractions of the half-frame, measured from the centre: `x: -1` is the left edge, `x: 1` the right, `y: -1` the top and `y: 1` the bottom. The same fractions land in the same place in every format, so a film changes format without edits.
- **Offsets.** `dx` and `dy` add design units after `x` and `y`. Stack lines with them (`"dy": -90` and `"dy": 90`): units keep the same spacing in every format. A `dx` or `dy` between -1 and 1 would move nothing you could see, so the engine reads it as a fraction added to `x` or `y`, with a warning.
- **Safe area.** Text wraps inside the frame less 70 units on each side. Keep anything that matters within 0.85 of the centre in `x` and `y`.
- **Scene beats and layer beats.** Some beat fields count from the scene's first beat, the others from the layer's own `start` (for a layer that starts at 0 they are the same):
  - **Scene beats:** `start` and `end`; the keyframes of positions, `scale`, `rotate`, `opacity`, a picture's `zoom` and `amount`, the camera and a gradient; the camera's `focus[].at` and `shake.beats`; a pill's `states[].at`, a cursor's `moves[].at`, a picture's `frame.at` and a photo set's `reflow[].at`. A click and the change it causes share one clock that way.
  - **Layer beats:** everything else, such as `draw`, `erase`, `count`, `fill`, `sweep`, `write`, `strike`, `playhead`, `morphAt`, `dissolve`, `collapse` and `flyThrough`; the `at` of particles, lines and grid waves, of a text's `dot` and `highlight` and of a note's `arrow`; every `motion` timing; and the keyframes of a grid's `tilt`, `yaw` and `zoom` and of the rings' `bend`.
  - **Seconds:** a video layer's `in` and `out` count seconds of footage, so a tempo change never retimes a clip.

### Animating values

A field whose value is marked *Num* in the tables takes one of three forms:

| Form | Example | What it does |
|---|---|---|
| A number | `"opacity": 0.6` | Holds that value. |
| Keyframes | `"x": [[0, -1.4], [1, 0, "outBack"]]` | Up to 32 `[beat, value, ease]` entries. Before the first key the value is the first key's; after the last, the last key's. |
| An oscillator | `"y": { "osc": "sine", "amp": 0.05, "period": 4 }` | Swings for as long as the layer shows. |

**Keyframes.** The ease belongs to the key it arrives at: it shapes the move from the key before. A key without one eases `inOut`. Keys are sorted by beat and their values clamped to the field's range.

| Ease | The move into the key |
|---|---|
| `linear` | at a constant speed |
| `in`, `out`, `inOut` | starts gently, ends gently, or both (`inOut` is the default) |
| `inExpo`, `outExpo`, `inOutExpo` | the same, much sharper |
| `outQuart` | a long, firm settle |
| `inOutSine` | the softest start and end |
| `outBack` | overshoots and settles back |
| `inBack` | pulls back before it leaves |
| `outElastic` | springs past the value and wobbles in |
| `outBounce` | bounces on arrival |
| `hold` | stays on the previous value, then jumps at the key (a step) |
| `smooth` | from CLI v1.5.1: see below |

Most eases stop at every key. From CLI v1.5.1, `smooth` on every key after the first joins those keys into one continuous move that never stops at the keys in between, never overshoots, and only starts and ends gently: use it for a camera move through three or more keys (`generate` adds it to such camera moves when the model names no ease). On a single key it is a gentle ease in and out.

**Oscillators** are `{ "osc", "base", "amp", "period", "phase" }`, and run on scene beats (on layer beats for a grid's `tilt`, `yaw` and `zoom` and a ring's `bend`, as keys do there):

| Field | Value | Default |
|---|---|---|
| `osc` | `sine`, `triangle`, `saw`, `square` | `sine` |
| `base` | the value it swings around | 0 |
| `amp` | how far it swings either way (**required**) | |
| `period` | beats per cycle, 0.125 to 64 (**required**) | |
| `phase` | the fraction of a cycle it starts at (0.25 is a quarter on) | 0 |

`base` is 0 unless you set it, so an oscillating `scale` needs `"base": 1`.

```json fragment
{ "kind": "shape", "shapes": ["circle"], "size": 24,
  "x": [[0, -1.3], [1.5, 0, "outBack"]],
  "y": { "osc": "sine", "amp": 0.06, "period": 2 },
  "scale": { "osc": "triangle", "base": 1, "amp": 0.1, "period": 1 } }
```

### The document

| Field | Value | Default | What it does |
|---|---|---|---|
| `version` | `1` | `1` | The format's version. |
| `title` | text, up to 80 characters | `Untitled motion` | The film's name. The HUD shows it, and it seeds the randomness when there is no `seed`. |
| `format` | `16:9`, `9:16`, `1:1` | `16:9` | The frame. `revise --format` re-lays a film out. |
| `duration` | seconds, 6 to 90 (6 to 60 before CLI v1.8.4) | 15 | The length; the tempo snaps to it. |
| `tempo` | BPM, 84 to 160 | 128 | The target tempo (see [Units and coordinates](#units-and-coordinates)). |
| `seed` | a whole number | taken from the title | Seeds everything random (particles, jitter, the score): the same seed draws the same frames. |
| `palette` | a preset's name, or six colours | `dawn` | See [Palettes](#palettes). |
| `fonts` | a face per role | see [Fonts](#fonts) | |
| `sound` | `{ "style": ... }`, or the style's name | `pulse` | The score. See [Sound](#sound). |
| `feel` | a feel's name | `punchy` | How every action motion moves. See [Feel](#feel). |
| `hud` | `true`, `false` | `false` | A designer HUD over the film: title, bar counter, timecode and crop marks. From CLI v1.8.4, `generate` leaves it off unless the brief asks for a HUD, a timecode or a bar counter. |
| `chapters` | `true`, `false` | `false` | A chapter scrubber along the bottom: a diamond per chapter, a tick per bar, a playhead, and the current chapter's name written in the `hand` face. Name chapters on the scenes that start them (`chapter`); 3 to 8 short lowercase names suit explainers and tutorials. |
| `photos` | up to 12 photos | none | The photos the film may show. See [Photos and clips](#photos-and-clips). |
| `clips` | up to 4 clips | none | The video clips it may play. |
| `mark` | `{ "photo", "corner", "size" }` (`photo` **required**) | none | A logo held in a corner of every frame, drawn whole (never cropped or graded): `photo` is a photo's id from `photos`, `corner` is `top-left` (the default), `top-right`, `bottom-left` or `bottom-right`, and `size` the height of its box, 40 to 240 units (default 90; a wide logo stops at 320 across). On 5am.app a brand kit sets it. |
| `scenes` | 1 to 48 scenes (24 before CLI v1.8.4) | a title card of the `title` | The film, scene after scene. See [Scenes](#scenes). |

Narration is not part of the film file: `narrate` saves the take beside it. The "Made with 5AM.app" mark is drawn by the renderer, and no field turns it off.

#### Palettes

A palette is six colours, named by token. Wherever a colour goes, give a token or a hex value (`#rgb` or `#rrggbb`); tokens keep a film recolourable with one edit. The values inside a `palette` object itself are hex only.

| Token | Used for |
|---|---|
| `bg` | the default scene background |
| `ink` | the dark colour, for text and lines on light backgrounds |
| `paper` | the light colour, for text and lines on dark backgrounds |
| `accent` | the main highlight: dots, highlighted words, the first shape |
| `accent2` | a second highlight |
| `muted` | a quiet colour, for soft surfaces and gradients |

Text, counters, dials, clocks, rings, grids, lines and meshes without a `color` take `ink` or `paper`, whichever reads on the scene's background. `"palette": "neon"` names a preset; an object sets the tokens itself, and any token it leaves out comes from `dawn`.

| Preset | `bg` | `ink` | `paper` | `accent` | `accent2` | `muted` |
|---|---|---|---|---|---|---|
| `dawn` | #060D0C | #060D0C | #EFEAE0 | #EA580C | #5EEAD4 | #0D9488 |
| `paper` | #EFEAE0 | #111111 | #FBF7EF | #E8453C | #3B3FF0 | #F2C230 |
| `neon` | #0A0A12 | #0A0A12 | #F5F5FF | #FF3D81 | #3DFFD0 | #6B5BFF |
| `mono` | #0E0E0E | #0E0E0E | #F4F4F2 | #F4F4F2 | #9A9A96 | #3A3A38 |
| `citrus` | #FFF4D6 | #1B1A17 | #FFFDF6 | #FF6B1A | #2F6BFF | #FFC21A |
| `ocean` | #04162B | #04162B | #EAF6FF | #35C2FF | #FFB23F | #1B4B8A |

#### Fonts

`fonts` names a face for each of four roles:

| Role | Draws | Default |
|---|---|---|
| `display` | text and counters (their default role) | `inter` |
| `body` | text with `"font": "body"`, and pill labels | `inter` |
| `mono` | text with `"font": "mono"`, and counter labels | `jetbrains-mono` |
| `hand` | notes and the chapter scrubber's names | `caveat-bold` |

A face is a font id, or the face's name as written (`"Bebas Neue"`); anything else falls back to the role's default, with a warning. Two faces are built in: `inter` (a bold grotesk, the default) and `jetbrains-mono` (technical, weights 400 to 600). Every other face is one of the 5AM catalog's, each with one weight: a layer's `weight` cannot make it bolder or lighter. Italic text in `instrument-serif` draws `instrument-serif-italic`; other faces are slanted. `5am motion fonts --dir` downloads them all.

| Category | Font ids |
|---|---|
| Display | `bebas-neue`, `anton` (a tall condensed poster face), `archivo-black`, `bungee`, `russo-one`, `righteous` |
| Sans | `oswald-bold`, `montserrat-extrabold`, `poppins-bold`, `rubik-extrabold` |
| Rounded | `fredoka-bold`, `nunito-black`, `lilita-one` |
| Serif | `playfair-display-extrabold`, `dm-serif-display`, `abril-fatface`, `cinzel-bold`, `instrument-serif` (editorial), `instrument-serif-italic` |
| Script | `pacifico`, `caveat-bold` (handwriting), `permanent-marker`, `kaushan-script` |
| Comic | `bangers`, `luckiest-guy` |
| Retro and tech | `press-start-2p`, `space-mono-bold`, `orbitron-extrabold` |
| Japanese | `noto-sans-jp-black`, `zen-maru-gothic-bold`, `dela-gothic-one`, `mochiy-pop-one`, `reggae-one`, `kosugi-maru`, `yusei-magic`, `shippori-mincho-extrabold`, `hachi-maru-pop` |
| Arabic and Persian | `vazirmatn-extrabold`, `cairo-extrabold`, `rakkas` |
| Korean | `black-han-sans`, `jua` |

Match the face to the brief's voice (a poster face for hype, a serif for editorial, rounded or comic for playful, retro for games and tech); most films need only a display face, with `inter` as body. Text in Japanese, Korean, Arabic or Persian needs a face made for that script in the role that draws it (the display face for a headline in it, the body face for smaller lines): `lint` reports a face that cannot draw its text as a fix. Arabic and Persian run right to left and animate word by word.

#### Sound

`sound.style` is the music bed the score is composed in. In every style but `none` the score also follows the film: hits on entrances, a thump on each bounce, a blip per dial marker.

| Style | Sound |
|---|---|
| `pulse` (default) | a driving four-on-the-floor |
| `house` | fuller and busier |
| `minimal` | half-time and sparse |
| `ambient` | no drums |
| `none` | no music and no sound effects; narration and clip sound still play |

`generate --sound` and `revise --sound` set it.

#### Feel

`feel` is how every action motion moves: entrances, slides, morphs and landings.

| Feel | Motion |
|---|---|
| `punchy` (default) | quick settle, small overshoot, hard slams |
| `snappy` | fast and crisp, no overshoot |
| `bouncy` | big overshoot, springy drops, playful |
| `smooth` | slow eased glides, no overshoot, calm |
| `mechanical` | stop-motion steps, rigid, techy |
| `cinematic` | slow, short travel, long settles, premium |

Pick it from the brief's energy: playful is `bouncy`, calm or luxury `smooth` or `cinematic`, tech `mechanical` or `snappy`. A layer can take its own (see [Layers](#layers)); mix a different one into one layer only, for contrast.

### Scenes

| Field | Value | Default | What it does |
|---|---|---|---|
| `id` | text, up to 40 characters | `s1`, `s2`, ... | Names the scene; a repeated id gets a suffix. |
| `beats` | 0.5 to 64 | 4 | Its length. |
| `bg` | colour | `bg` | Its background. |
| `gradient` | a gradient (below) | none | Blends the background into a second colour. |
| `vignette` | 0 to 1, or `true` (0.35) | none | Darkens the edges toward the background's own hue: 0.2 is subtle on a light scene, 0.5 on a dark one. |
| `chapter` | text, up to 24 characters | none | With `chapters`, the chapter that starts here; scenes without one continue the last. |
| `enter` | a transition | a cut | How this scene arrives over the end of the one before. See [Transitions](#transitions); the first scene's is ignored. |
| `camera` | a camera | still | Moves, zooms and shakes the whole scene. See [Camera](#camera). |
| `layers` | up to 24 layers | none | What the scene draws, in order: later layers draw over earlier ones. See [Layers](#layers). |

A **gradient** is `{ "type", "from", "to", "angle", "x", "y" }`:

| Field | Value | Default |
|---|---|---|
| `type` | `linear`, `radial` | `linear` |
| `from` | colour: the side the angle starts from (linear), or the centre (radial) | the scene's `bg` |
| `to` | colour: the far side, or the edges (**required**) | |
| `angle` | *Num*, degrees: 0 runs left to right, 90 top to bottom (linear) | 90 |
| `x`, `y` | *Num*, the radial centre in half-frame fractions, -1.5 to 1.5 | 0 |

A colour alone is short for `{ "to": colour }`, and `[from, to]` for both. Keep the two colours close in lightness so text reads everywhere on them; a radial gradient from a lighter colour (`paper` on a light scene, `muted` on a dark one) is a soft light behind the subject.

```json fragment
{ "id": "glow", "beats": 4, "bg": "bg", "gradient": { "type": "radial", "from": "muted", "to": "bg" }, "vignette": 0.5, "layers": [] }
```

### Transitions

A scene's `enter` reveals it over the end of the scene before, landing on its first beat: `{ "type", "beats", ... }`, or just the type's name. `beats` is 0.125 to 4 (default 0.5, and 1 for `fly`); 0.25 to 1.6 reads best, and one longer than the scene before it is a lint note. `direction` is the direction of travel: `left`, `right`, `up` or `down`.

| Type | What it does | Options |
|---|---|---|
| `cut` | a plain cut (the default) | |
| `circle` | a circle opens from a point, with a fading ring | `x`, `y` (default the centre), `color` (the ring, default `paper`) |
| `wipe` | a hard edge sweeps across, with a bar on it | `direction` (default `left`), `color` (the bar, default `accent`) |
| `push` | the new scene pushes the old one out | `direction` (default `left`) |
| `whip` | a whip pan: a push that streaks with a heavy motion smear and lands sharp (0.3 to 0.5 beats); energetic, between two ideas that continue each other | `direction` (default `left`) |
| `zoom` | the old scene rushes at the camera and the new one settles in from big: big reveals | |
| `split` | the old scene splits into halves that slide apart: top and bottom with `left` or `right` (the default), left and right with `up` or `down` | `direction` |
| `blinds` | slats open one after another: `left` or `right` sweeps vertical slats that way (default `right`), `up` or `down` horizontal ones | `direction`, `color` (an edge on every moving slat) |
| `tiles` | square tiles pop in from the top-left corner | |
| `shutter` | two bars close from the top and bottom and open on the new scene | `color` (default `accent`) |
| `glitch` | bands of the frame jump between the two scenes | |
| `morph` | one continuous take: every layer with the same `id` as a layer of the previous scene turns into it (a shape into the other shape; anything else moves and resizes into place), and the others leave or arrive on their own. A morph with no shared id is a lint fix | |
| `flood` | a solid shape grows out of a layer until it fills the frame, holds, then contracts into a layer of this scene (1.2 to 1.6 beats) | `from` (a layer's id in the previous scene), `into` (one in this scene), `x`, `y` (where it grows from without `from`), `color` (default `ink`) |
| `iris` | six camera blades close, then open on the new scene (about 1 beat, often right after a click) | `x`, `y` (default the centre), `color` (default `ink`) |
| `fly` | from CLI v1.5.1: one layer of the previous scene flies through the camera while this scene is already in place underneath, so the headline or the logo becomes the cut (0.8 to 1.2 beats) | `from` (the id of a top-level layer of the previous scene; by default its biggest words) |

Give a flying layer room to grow (centred, big) and the new scene something to land on. Morphs and floods carry photos too: an image of the same photo as an image or a tile of the previous scene glides out of it, and a flood `into` a framed image lands as the finished print. Use transitions on about half the scenes; plain cuts are strong.

### Camera

| Field | Value | Default | What it does |
|---|---|---|---|
| `zoom` | *Num*, 0.1 to 20 | 1 | Scales the scene around the frame's centre. |
| `x`, `y` | *Num*, half-frame fractions, -3 to 3 | 0 | The point of the scene at the frame's centre: a pan. |
| `rotate` | *Num*, degrees | 0 | Turns the view. |
| `shake` | `{ "beats": [...], "amount" }` | none | A jolt on each listed scene beat (up to 16); `amount` is 0 to 80 units (default 14; 4 to 30 reads well). |
| `focus` | up to 16 `{ "at", "to", "zoom", "beats" }` (`at` and `to` **required** in each) | none | Flights to a layer or a point, screen-recording style. |

Each `focus` key flies the camera to `to` and arrives at scene beat `at`, after a flight of `beats` (0.1 to 8, default 0.6), zoomed to `zoom` (0.2 to 12; default 1.5 on a layer, 1 on a point). `to` is a layer's id (followed while it moves, a cursor for instance), `"<photo set id>:<photo id>"` for one tile, or `[x, y]`. The camera stays there until the next key; `{ "at": 6, "to": [0, 0], "zoom": 1 }` flies back out. A word d units from the target lands d x zoom from the middle, so end the words a zoom would push past the frame's edge before the flight, or zoom less: `lint` reports them.

```json fragment
{ "camera": { "x": [[0, -0.3], [4, 0, "smooth"], [8, 0.3, "smooth"]], "zoom": [[0, 1.2], [8, 1, "smooth"]], "shake": { "beats": [4], "amount": 12 } } }
```

### Layers

Every layer is an object with a `kind`. These fields work on every kind:

| Field | Value | Default | What it does |
|---|---|---|---|
| `kind` | one of the kinds below (**required**) | | What it draws. |
| `id` | text, up to 40 characters | none | Names it for `morph`, `flood` and `fly`, cursor moves, camera focus and a grid's `repel` wave. |
| `start`, `end` | scene beats | the whole scene | When it shows; `end` must come after `start`. |
| `x`, `y` | *Num*, -3 to 3 | 0 | Its anchor, in half-frame fractions. |
| `dx`, `dy` | *Num*, design units | 0 | Offsets after `x` and `y`. |
| `scale` | *Num*, 0 to 40 | 1 | Its size. |
| `scaleX`, `scaleY` | *Num*, -40 to 40 | 1 | A per-axis scale on top of `scale`: squash and stretch (1.35 and 0.65 on an impact), anticipation, or a mirror (negative). |
| `rotate` | *Num*, degrees | 0 | Its turn. |
| `opacity` | *Num*, 0 to 1 | 1 | |
| `color` | colour | per kind | Its main colour (each kind says what it colours). |
| `enter`, `exit` | `{ "type", "beats" }`, or the type's name | none | A move in at `start`, and out just before `end`; `beats` is 0.05 to 8 (default 0.5). |
| `pulse` | `{ "every", "amount" }` | none | A scale bump every `every` beats (0.25 to 8, default 1) of `amount` (0 to 0.5, default 0.06; 0.02 to 0.2 reads well). |
| `feel` | a feel's name, or `{ "preset", "intensity", "bounce", "speed" }` | the film's | This layer's own feel, tuned: `intensity` (0 to 3) scales travel and wobble, `bounce` (0 to 4) overshoot, and `speed` (0.25 to 4) durations, so 2 is twice as slow. A group passes its feel to its layers. |
| `trail` | `{ "type", "count", "spacing", "color" }`, or the type's name | none | Copies left behind a layer that moves. |
| `motion` | a path or a bounce (below) | none | Moves the layer; the engine does the physics. |

**`enter` and `exit` moves.** A directional move names the side the layer comes from, or leaves back through.

| Move | What it does |
|---|---|
| `fade` | fades |
| `pop` | grows from nothing |
| `rise` | moves up into place |
| `drop` | falls in from above, with a bounce |
| `from-left`, `from-right`, `from-top`, `from-bottom` | enters from that edge of the frame; as an exit, leaves through it |
| `zoom` | shrinks in from big |
| `spin` | spins in |
| `wipe` | is revealed left to right |
| `blur` | settles in from soft |
| `none` | no move |

**Trails** draw the layer at earlier beats: `ghosts` (onion-skin outlines; 6 copies 0.12 beats apart by default), `comet` (a tail of shrinking copies; 14 copies 0.055 beats apart) or `path` (the dashed route it travelled). `count` is 1 to 40, `spacing` 0.01 to 2 beats, and `color` defaults to the layer's. A video cannot leave one.

**Motions** move a layer; their beats count from the layer's `start`.

- `{ "type": "bounce", "from", "to", "floor", "bounces", "elasticity", "squash", "at", "beats" }` drops the layer from `from` (`[x, y]`, default `[-0.8, -0.9]`) onto the ground line `floor` (a `y`, -1.5 to 1.5, default 0.55; a shape's edge lands on it) and bounces `bounces` times (0 to 8, default 3) while it drifts to the `x` of `to`. Each bounce rises `elasticity` (0.05 to 0.9, default 0.45) as high as the one before, and `squash` (0 to 0.6, default 0.35) squashes it on each landing and stretches it in flight. It starts `at` (default 0) and takes `beats` (0.25 to 64, default the rest of the layer), with real falling-body timing and a thump on each landing.
- `{ "type": "path", "path", "points", "scale", "from", "to", "ease", "orient", "loop" }` travels around the layer's own `x`/`y` along a path preset (`path`, below; default `circle`) or `points` (2 to 64 `[x, y]`, where -1 to 1 spans the frame's short side), resized by `scale` (0.05 to 5). It runs from beat `from` to beat `to` (default the layer's whole life), eased by `ease` (default `inOut`); `orient` turns the layer along its direction of travel, and `loop` repeats it.

Pair a motion with a trail: a bouncing ball with ghosts and a path trail, a comet on an infinity path.

```json fragment
{ "kind": "shape", "shapes": ["circle"], "size": 40, "fills": ["accent"],
  "motion": { "type": "bounce", "from": [-0.7, -0.8], "to": [0.6, 0], "floor": 0.5, "bounces": 4 },
  "trail": { "type": "ghosts", "count": 8 } }
```

The kinds follow; `image`, `photos` and `video` are under [Photos and clips](#photos-and-clips). A table lists a kind's own fields: its common ones are above.

#### `text`: kinetic type

Big type that animates by letter, word or line: headlines, subheads, labels and end cards. The workhorse of most films.

| Field | Value | Default | What it does |
|---|---|---|---|
| `text` | up to 160 characters (**required**) | | The words. |
| `font` | `display`, `body`, `mono`, `hand` | `display` | The role whose face draws it. |
| `weight` | 100 to 900 | 900 (`display`), 600 | The weight, where the face has it. |
| `size` | 10 to 600 | 120 | The cap height in units: about 100 to 160 for a headline, 40 to 70 for a subhead, 14 to 26 for a label. |
| `tracking` | em, -0.2 to 1 | -0.025 (`display`), 0.02 | Letter spacing. |
| `lineHeight` | 0.7 to 2.2 | 0.98 (`display`), 1.25 | Line spacing, as a multiple of the font size. |
| `align` | `left`, `center`, `right` | `center` | The edge the layer's point anchors. |
| `maxWidth` | 0.2 to 1 | 0.94 | The longest line, as a fraction of the safe width; longer text wraps. |
| `case` | `upper`, `lower`, `none` | `upper` | `none` keeps the text as written. |
| `italic`, `outline` | `true`, `false` | `false` | Italic; letters drawn as outlines. |
| `split` | `chars`, `words`, `lines`, `none` | `chars` | The unit that animates. |
| `stagger` | beats, 0 to 2 | at most 0.05 (`chars`), 0.25 (`words`), 0.5 (`lines`) | The time between units. |
| `unitEnter` | a unit move (below) | `rise` | How each unit arrives. |
| `unitExit` | a unit move | `none` | How each unit leaves, at the end. |
| `unitBeats` | 0.05 to 4 | 0.5 (0.45 for `from-left` and `from-right`, 0.7 for `drop`) | Each unit's move. |
| `mask` | `true`, `false` | `true` with `rise` | Clips units to their line, so they rise out of the baseline. |
| `highlight` | `{ "word", "style", "color", "at" }` (`word` **required**) | none | Marks one word (`word` counts from 0) with `brackets` (the default), a `box`, an `underline` or its `color`, from beat `at`. The colour defaults to `accent`, except that `brackets` take the text's own colour. |
| `dot` | `{ "color", "at", "hop" }`, or `true` | none | A round period that drops in after the text (default `accent`). With `"hop": true` (one line only) it hops across the letters, each letter entering as the dot reaches it, and lands as the period. |
| `backColor` | colour | | The back face of letters that `spin-y`. |

The unit moves, for `unitEnter` and `unitExit`:

| Move | What each unit does |
|---|---|
| `rise` | rises out of its own baseline |
| `drop` | falls from the top and bounces into place |
| `tumble` | flips and rotates up into place |
| `from-left`, `from-right` | slams in from that edge |
| `scale` | pops up from nothing |
| `type` | appears, one by one, like a typewriter |
| `blur` | settles in from soft and large |
| `flip` | flips open vertically |
| `fade` | fades in |
| `stretch` | arrives stretched wide and snaps back |
| `spin-y` | turns like a card around its vertical axis, its back face in `backColor` |
| `squeeze` | exit only: the letters close into the period like an accordion (give the text a `dot`), then the period glides to the layer's `x`/`y`; start a pill there as the text ends and the dot grows into it |
| `none` | no move |

#### `shape`: morphing shapes

A filled vector shape that morphs from one shape to the next on the beat. For one accent, a logo mark, a ball that bounces, or a tile a cursor clicks (a grid of tiles is several shape layers, each with its own `id`).

| Field | Value | Default | What it does |
|---|---|---|---|
| `shapes` | up to 8 of `circle`, `square`, `rounded`, `triangle`, `play`, `diamond`, `star4`, `star5`, `hexagon`, `heart`, `blob`, `ring`, `cross`, `pill` | `["circle"]` | The shapes it morphs through. |
| `morphAt` | beats | 1, 2, 3, ... | The beat each morph lands on. |
| `fills` | colours, one per shape | `color`, else `accent` then `accent2` | Their fills. |
| `size` | radius, 10 to 700 | 130 | 60 to 260 reads well. |
| `stroke`, `strokeWidth` | colour; 0.5 to 80 units | none; 4% of the radius | An outline. |
| `spin` | degrees per morph, -360 to 360 | 60 | The turn at each morph. |
| `drift` | degrees per beat, -180 to 180 | 11 | A slow turn. |
| `squash` | `true`, `false` | `true` | A wobble on each morph. |
| `ghost` | `true`, `false` | `true` | A faint outline trailing each morph. |
| `gizmo` | `true`, `false` | `false` | An After Effects style bounding box, handles and a live rotation readout. |
| `dissolve` | a beat | none | When it dissolves into a sunflower of dots. |

#### `path`: ribbons

A striped ribbon whose head writes a stroke, then runs off.

| Field | Value | Default | What it does |
|---|---|---|---|
| `preset` | `glyph-5`, `loop`, `wave`, `s-curve`, `spiral`, `infinity`, `zigzag`, `heart`, `underline`, `circle`, `arc` | `loop` | The stroke's shape. |
| `points` | 2 to 64 `[x, y]`, where -1 to 1 spans the frame's short side | none | A shape of your own, smoothed (in place of `preset`). |
| `width` | 4 to 200 | 62 | The stroke's width. |
| `stripes` | up to 6 colours, outermost first | `ink`, `accent`, `paper`, `accent2`, `paper` | Concentric stripes. |
| `draw` | `[start, end]` beats | from 0, for 2 beats or half the layer if that is shorter | The head writes the shape. |
| `erase` | `[start, end]` beats | none (the stroke stays) | Head and tail run off. |
| `shadow` | `true`, `false` | | A soft shadow. |

#### `grid`: dot fields

A field of dots (or squares, crosses, lines) that waves ripple through, and that tilts into 3D terrain.

| Field | Value | Default | What it does |
|---|---|---|---|
| `style` | `dots`, `squares`, `crosses`, `lines` | `dots` | What each point is. |
| `spacing` | 14 to 160 | 37 | Between points. |
| `dot` | radius, 0.5 to 20 | 3 | Each point's size. |
| `heat` | colour | `accent` | The colour the field takes where waves lift it. |
| `waves` | up to 8 waves (below) | none | What moves through it. |
| `tilt` | *Num*, degrees, -85 to 85 (layer beats) | 0 | Lays the field down into 3D. |
| `yaw` | *Num*, degrees, -180 to 180 (layer beats) | 0 | Turns it. |
| `zoom` | *Num*, 0.1 to 6 (layer beats) | 1 | Scales it. |
| `intro` | `burst`, `scan`, `fade`, `none` | `burst` | How it appears; with `none` it is drawn during the scene's transition, so a push or a whip shows it streaking in. |
| `introBeats` | 0.1 to 8 | 0.55 | The intro's length. |

A wave is `{ "type", "at", "beats", "x", "y", "amp", "direction" }`: a `plane` (a band sweeping across in `direction`, default `right`, over `beats`, default 1.5), a `ripple` (a ring spreading from `x`, `y`), `noise` (a churning field) or `terrain` (rolling hills, which read as a landscape once tilted). `amp` is its height, 0 to 300 units (default 70), and `at` its start. Or `{ "type": "repel", "target", "radius", "strength" }`: the dots part around a moving layer of the scene (`target`, its `id`) and heat up; `radius` 20 to 1200 (default 190), `strength` -400 to 400 (default 70).

#### `mesh`: 3D point clouds

A turning 3D form drawn as points, wires or both, that morphs between shapes, words included.

| Field | Value | Default | What it does |
|---|---|---|---|
| `shapes` | up to 6 of `sphere`, `torus`, `cube`, `cylinder`, `helix`, `plane`, `cone`, `octahedron`, or `text:WORD` (1 to 12 characters) | `["sphere"]` | The forms it morphs through. |
| `morphAt` | beats | 1, 2, 3, ... | The beat each morph lands on. |
| `points` | 120 to 3200 | 1400 | How many points (400 to 2400 reads well). |
| `render` | `points`, `wire`, `both` | `both` | How it is drawn. |
| `size` | radius, 40 to 700 | 280 | 180 to 340 reads well. |
| `pointSize` | 0.5 to 10 | 2.4 | Each point's size. |
| `spinX`, `spinY` | degrees per beat, -360 to 360 | 0, 55 | Its turn. |
| `tilt` | degrees, -90 to 90 | 22 | A fixed tilt toward the viewer. |
| `accent` | colour | `accent` | The colour of some of its points. |
| `flyThrough` | `[start, end]` beats | none | The camera flies through it. |

#### `particles`

Deterministic particle systems.

| Field | Value | Default | What it does |
|---|---|---|---|
| `emitter` | `burst`, `fountain`, `orbit`, `rain`, `confetti`, `swarm`, `sunflower` | `burst` | The system. |
| `count` | 1 to 2000 | 120 (`rain` 160, `sunflower` 700) | How many. |
| `colors` | up to 6 colours | `accent`, `accent2`, `paper` | Their colours. |
| `size` | 0.5 to 40 | 7 | Each particle's size. |
| `speed` | 0 to 4000 units a second | 900 | How fast they leave. |
| `gravity` | -4000 to 4000 | 1400 (`confetti`), 500 (`burst`), 0 | The pull down. |
| `at` | a beat | 0 | When a burst goes off. |
| `spread` | degrees, 0 to 360 | 360 | The cone they leave in. |

#### `rings`: text rings

Rows of words turning on concentric rings around a dot.

| Field | Value | Default | What it does |
|---|---|---|---|
| `rows` | 1 to 6 rows (**required**): `{ "text", "size", "weight", "outline" }`, or the text alone | | Short phrases such as `PHOTOS • VIDEO • CLIPS`; 2 or 3 rows read best. `size` 8 to 120 (default 34, smaller for each inner row), `weight` (default 800). |
| `radius` | 80 to 900 | 80% of the short half-frame | The outer ring's radius. |
| `bend` | *Num*, 0 to 1 (layer beats) | opens from marquee rows into rings over its beats 1 to 2 | 0 is straight marquee rows, 1 full rings. |
| `spin` | units of scroll per beat, -2000 to 2000 | 150 | How fast they turn. |
| `collapse` | `[start, end]` beats | none | The rings spin up and implode into the centre dot. |
| `dot` | colour, or `false` | `accent` | The centre dot. |

Set `"bend": 1` unless you want a ticker: below 1 the rows run off both frame edges. Keep the rows solid (an `outline` row is a hairline nobody can read) and the scene free of other words, since the rings fill the middle of the frame. Rings set each letter on its own, which breaks Arabic and Persian: put those words in a text layer.

#### `counter`

A number that counts on the beat, on fixed digit slots so it never jitters.

| Field | Value | Default | What it does |
|---|---|---|---|
| `to` | a number (**required**) | | Where it lands. |
| `from` | a number | 0 | Where it starts. |
| `format` | `0`, `0.0`, `0%`, `00:00`, `$0,000`, `0k` and the like | `0` | The zeros after the point are decimals, a comma groups thousands, `%` adds a percent sign, `k` counts thousands, `$`, `€` or `£` leads, and `00:00` shows seconds as minutes and seconds. |
| `prefix`, `suffix` | up to 6 and 8 characters | none | Text around the number. |
| `font` | `display`, `body`, `mono`, `hand` | `display` | The role whose face draws it. |
| `weight` | 100 to 900 | 900 | |
| `size` | 20 to 700 | 200 | The cap height. |
| `count` | `[start, end]` beats | from 0 to 60% of the layer | When it counts. |
| `ease` | an ease | `outExpo` | How it counts. |
| `label` | up to 40 characters | none | A line under the number, in capitals in the mono face. |

#### `clock`

An analog clock whose markers split out of the centre and whose hands sweep between two times.

| Field | Value | Default | What it does |
|---|---|---|---|
| `from`, `to` | `"H:MM"` | `4:15`, `5:00` | The times it sweeps between. |
| `sweep` | `[start, end]` beats | `[2, 3]` | When the hands move. |
| `radius` | 40 to 480 | 190 | Its size. |
| `readout` | `true`, `false` | `true` | The time, in digits, under it. |
| `accentHour` | 0 to 11 | the hour it lands on | The marker that turns `accent` when the sweep lands. |
| `split` | `true`, `false` | `true` | The markers split out of the centre beat by beat. |

#### `lines`

Graphic line systems that frame or energise a scene.

| Field | Value | Default | What it does |
|---|---|---|---|
| `pattern` | `rays`, `burst`, `stripes`, `scanlines`, `grid`, `corners`, `circles` (**required**) | | Rays from the centre, a burst of dashes, diagonal stripes, travelling scanlines, a grid, crop corners, or circles on the beat. |
| `count` | 1 to 200 | per pattern | How many lines. |
| `width` | 0.5 to 60 | 3 | Line width. |
| `length` | 1 to 2000 | per pattern | Ray, dash or corner length. |
| `at` | a beat | 0 | When it starts. |
| `beats` | 0.1 to 32 | 1 | How long it grows (or a circle's period). |
| `spin` | degrees per beat, -360 to 360 | 6 | The rays' turn. |

#### `wave`: soundwaves

From CLI v1.6.0. A soundwave breathing with its own rhythm, centred on the layer's `x`/`y`: for podcasts, music, a voice, "now playing", a recording. One per scene is plenty; give it room, with no words across its band.

| Field | Value | Default | What it does |
|---|---|---|---|
| `style` | one of the styles below | `ribbon` | Its look. |
| `width` | 40 to 4000 | 820 | Its width in units. |
| `height` | 10 to 1200 | 160 | The band's height; everything scales with it. |
| `colors` | up to 4 colours | per style | The ribbons, or the liquid gradient's stops; the one-colour styles take the first (else the layer's colour), the machines an accent second. |
| `intensity` | 0.15 to 1 | 0.75 | How loud the signal plays. |
| `speed` | 0.1 to 4 | 1 | How fast it moves. |

| Set | Styles |
|---|---|
| Spectrum | `ribbon` (four translucent ribbons, the default), `mono` (a line with its traces), `silk` (eight silk layers), `liquid` (one liquid band), `spectrum` (fine bars) |
| One colour | `sweep` (a phosphor scan), `dust` (a point cloud), `braid` (two strands), `terminal` (box-drawing characters), `contour` (stacked ridges), `teletext` (a mosaic), `scope` (an oscilloscope), `wireframe` (a wire terrain), `ascii` (a text stream), `spectral` (pixel columns) |
| With an accent | `motor` (a harmonic motor whose arms draw the wave), `horizons` (a calibrated floor), `vernier` (two sliding rulers), `broken` (a plotter grid) |

#### `figure`: drawn characters

From CLI v1.6.0. A drawn character moving to the film's beat, centred on the layer's `x`/`y`: for podcasts, music, voice and listening. One per scene; keep words off it.

| Field | Value | Default | What it does |
|---|---|---|---|
| `figure` | one of the figures below (**required**) | | Who. |
| `size` | 40 to 2400 | 480 | Its width in units (the listener is a little taller than wide). |
| `colors` | up to 7 colours, in the figure's own order | its own | Creatures: white, red, blue, mint, violet, dim, tan. Heads: outline, feature, voice, ear, quiet, white. The songbird: bird, branch, sound. The listener: face, earbud, glow. |
| `intensity` | 0.25 to 1.5 | 1 | How hard the music hits it. |
| `speed` | 0.25 to 3 | 1 | Its clock. |
| `mode` | `voice`, `listen` | `voice` | The heads: speaking, or listening. |
| `clip` | `true`, `false` | `true` | The round figures clip to their circle. |

The figures: ten playback creatures, each limb on a drum (`goblin`, a tape goblin; `boxer`, a punch-clock boxer; `eater`, a tape eater; `octopus`; `bird`, a resonant bird; `astronaut`, moonwalking; `moth`, a moth choir; `hound`, an x-ray hound; `snail`, a reel-riding snail; `conductor`, a ghost conductor), two voice heads (`phoneme` leaves a sound packet for each syllable, `echo` excites a resonating cavity), `choir` (a songbird on a branch) and `listener` (a traced profile nodding to the beat, its earbud pulsing).

#### `lottie`: vector animations

From CLI v1.7.0. A small animated accent centred on the layer's `x`/`y`: one of eight built-in presets, or your own Bodymovin (Lottie) JSON.

| Field | Value | Default | What it does |
|---|---|---|---|
| `preset` | one of the presets below | `sparkle` (without `data`) | The built-in animation. |
| `data` | a Bodymovin v5 JSON object | none | Your own animation, drawn in place of the preset. |
| `width`, `height` | 24 to 2400 | 320, and `height` the width | Its box; `data` is fitted inside it, centred. |
| `speed` | 0.1 to 6 | 1 | A preset: how many times it plays between `start` and `end`. `data`: a multiple of its own frame rate. |
| `loop` | `true`, `false` | `true` | `false` plays it once and holds the last pose. |
| `primaryColor`, `secondaryColor` | colours | `color`, else `accent`; `accent2` | A preset's two colours (`data` keeps its own). |

| Preset | What it shows | For |
|---|---|---|
| `sparkle` | a four-point star twinkling with three small ones | new, magic, a launch |
| `confetti` | pieces burst out and fall away | a celebration, a milestone |
| `check` | a ring draws round, then a tick | done, approved, sent |
| `flame` | a flickering flame | hot, trending, a streak |
| `pulse-ring` | rings radiating from a dot | live, recording, a notification |
| `equalizer` | five bouncing bars | music, audio, now playing |
| `arrow-burst` | eight rays shooting out | emphasis, a reveal |
| `star-burst` | a turning twelve-point burst | a badge, a price, "new" |

A preset plays **once across the layer's window**, from `start` to `end`; `speed` repeats it (`"speed": 3` plays it three times). Give the one-shot presets (`confetti`, `check`, `arrow-burst`) a short window at their moment (`"start": 2, "end": 3.5`), and a looping one (`sparkle`, `flame`, `pulse-ring`, `equalizer`, `star-burst`) on a long window a `speed` of about one cycle per two beats (`generate` sets it so). Each looping preset ends its cycle where it began, so repeats never jump. Keep it beside what it accents (width 120 to 320), never under text, at most one per scene, and only when the subject calls for one (a celebration, a launch, music, something live): most films need none.

**Your own Lottie.** `data` is drawn by the engine, not a Lottie player, and takes a subset of Bodymovin v5, with lottie-web's semantics:

- **Layers:** shape (`ty` 4) and solid (`ty` 1) layers, with their transform and in and out points. The composition is clipped to its `w` x `h` and plays at its frame rate `fr` from the layer's `start`, looping unless `loop` is `false`.
- **Shape items:** `gr` (group), `rc` (rectangle), `el` (ellipse), `sr` (star and polygon), `sh` (path; keyframed vertices too, when every keyframe has as many), `fl` (fill; `r: 2` fills even-odd), `st` (stroke, with its caps, joins and miter limit), `tm` (trim paths) and `tr` (group transform).
- **Keyframes:** both forms (a value `s` on every keyframe, and older exports' end values `e`), hold keyframes and per-dimension easing.
- **Not supported:** gradients and every other shape item, masks, mattes, parenting, effects, time remapping, 3D layers and rotations, expressions, blend modes other than normal, time stretch, start offsets, skew, spatial tangents, polystar roundness, stroke dashes, image and text layers. Nor more than 64 nested groups, 100 star points, 20,000 layers and shape items, 100,000 path segments drawn a frame, or numbers past 1,000,000.

A `data` document with anything unsupported is dropped with a warning naming the first problem; the layer then draws its `preset`, or is dropped when it names none.

```json
{
  "version": 1,
  "title": "On air",
  "format": "1:1",
  "duration": 6,
  "tempo": 120,
  "palette": "neon",
  "scenes": [
    { "id": "live", "beats": 12, "bg": "bg", "layers": [
      { "kind": "text", "text": "ON AIR", "size": 130, "dy": -150 },
      { "kind": "lottie", "width": 220, "dy": 170, "data": {
        "v": "5.7.4", "fr": 30, "ip": 0, "op": 60, "w": 200, "h": 200,
        "layers": [{
          "ty": 4, "ip": 0, "op": 60,
          "ks": {
            "p": { "k": [100, 100, 0] },
            "s": { "a": 1, "k": [
              { "t": 0, "s": [60, 60, 100], "o": { "x": [0.4], "y": [0] }, "i": { "x": [0.6], "y": [1] } },
              { "t": 30, "s": [100, 100, 100], "o": { "x": [0.4], "y": [0] }, "i": { "x": [0.6], "y": [1] } },
              { "t": 60, "s": [60, 60, 100] }
            ] }
          },
          "shapes": [
            { "ty": "el", "p": { "k": [0, 0] }, "s": { "k": [140, 140] } },
            { "ty": "fl", "c": { "k": [1, 0.24, 0.5, 1] }, "o": { "k": 100 } }
          ]
        }]
      } }
    ] }
  ]
}
```

#### `note`: handwritten notes

A designer's margin note in the `hand` face: it writes itself on, can point at something with a hand-drawn arrow, strike itself out or underline itself. Annotate a moment ("squash!"), point at what it explains, or cross out a wrong idea and write the right one.

| Field | Value | Default | What it does |
|---|---|---|---|
| `text` | up to 80 characters (**required**) | | The words, in their own case. |
| `size` | 12 to 200 | 44 | 36 to 60 reads well. |
| `align` | `left`, `center`, `right` | `left` | A note runs right from its `x` (about 0.36 x size per character) unless it is centred or right-aligned. |
| `write` | `[start, end]` beats | quick, by its length | When it writes on. |
| `arrow` | `{ "x", "y", "dx", "dy", "bend", "at" }` (`x` and `y` **required**) | none | A hand-drawn arrow to a point (`x`, `y` in half-frame fractions, -1.5 to 1.5, plus unit offsets), curving by `bend` (-1.5 to 1.5), drawn at beat `at` (default when the writing ends). |
| `strike` | a beat | none | A line crosses it out. |
| `underline` | `true`, `false` | `false` | |
| `boil` | `true`, `false` | `true` | A hand-drawn jitter, a few times a second. |

Its `color` defaults to `accent`.

#### `dial`: progress dials

An arc that fills to a percent, with markers inside that light up in turn, a fine tick ring, a centre dot and a readout: loading, uploads, goals, "almost there".

| Field | Value | Default | What it does |
|---|---|---|---|
| `to` | percent, -1000 to 1000 | 100 | Where the fill ends. |
| `from` | percent | 0 | Where it starts. |
| `fill` | `[start, end]` beats | from 0.5 to 80% of the layer | When it fills. |
| `ease` | an ease | `inOut` | How it fills. |
| `radius` | 60 to 480 | 230 | 150 to 320 reads well. |
| `markers` | 0 to 48 | 12 | Markers that light in turn (0 hides them). |
| `ticks` | 0 to 180 | 72 | The fine ticks (0 hides them). |
| `readout` | a counter format, or `false` | `0%` | The number under the dial. |
| `label` | up to 40 characters | none | A line under the readout. |
| `dot` | colour, or `false` | `accent` | The centre dot. |
| `accent` | colour | `accent` | The fill and the lit markers. |

#### `graph`: curves and charts

Two modes: easing curves in a curve editor (`curves`, morphing one into the next, with bezier handles and a playhead), to explain motion ("linear is robotic, ease in-out feels natural"); or a small data chart (`values`, as a line, an area or bars), to show growth or compare numbers. With both, `curves` wins.

| Field | Value | Default | What it does |
|---|---|---|---|
| `curves` | up to 6 ease names | none | The curves it shows, one after another. |
| `morphAt` | beats | 1, 2, 3, ... | When each curve morphs into the next. |
| `values` | up to 24 numbers | none | The data. |
| `labels` | up to 24, of 14 characters | none | A label under each value. |
| `style` | `line`, `area`, `bars` | `line` | How values are drawn. |
| `width`, `height` | 120 to 1800, 80 to 1600 | 640, 400 | The chart's box. |
| `draw` | `[start, end]` beats | `[0.3, 1.3]` | The line draws on, or the bars grow. |
| `playhead` | `[start, end]` beats | none | A dot rides the curve, with a time cursor. |
| `handles` | `true`, `false` | `true` | Bezier handles on easing curves. |
| `axes`, `grid` | `true`, `false` | | Axes and grid lines. |
| `xLabel`, `yLabel` | up to 24 characters | `time` and `position` for curves | Axis titles; leave them out of a chart unless it needs them. |
| `accent` | colour | `accent2` | The handles and the playhead. |
| `lineWidth` | 1 to 24 | 4.5 | |

Its `color` is the curve or the bars (default `accent`).

#### `pill`: buttons and chips

One shape that keeps morphing: a button or a status chip. It grows out of a dot, its width springs to fit each state, labels swap inside its own mask, and every later state reads as a click: "Order print", then "Ordered" with a check, "Printing" with a progress bar, "On its way", and a circle with a check.

| Field | Value | Default | What it does |
|---|---|---|---|
| `states` | 1 to 12 states (**required**) | | Each `{ "at", "text", "icon", "progress", "circle" }`, below. |
| `height` | 24 to 400 | 72 | 110 to 150 for the button a story is about. |
| `size` | 8 to 120 | 24 | The label's cap height (34 to 44 on a hero pill). |
| `fill` | colour | `ink` or `paper`, whichever reads | The pill. |
| `textColor` | colour | whichever reads on the fill | The label. |
| `font` | `display`, `body`, `mono`, `hand` | `body` | The label's role. |

A state: `at` is the **scene** beat it takes over (like cursor clicks; default its index in the list: 0, 1, 2, ...), `text` its label (up to 48 characters, cut at a word), `icon` one of `check`, `spinner`, `arrow`, `play`, `plus`, `dot`, `route` or `none`, `progress: true` fills a thin bar and a percent readout until the next state, and `circle: true` collapses the pill to a circle around the icon. A state needs a label or an icon.

#### `cursor`: a pointer

A pointer that drives the story: it travels to things, clicks, long-presses and drags. Always drawn on top.

| Field | Value | Default | What it does |
|---|---|---|---|
| `moves` | 1 to 32 moves (**required**) | | Each `{ "at", "to", "dx", "dy", "click", "hold", "drag" }` (`at` and `to` **required**), below. |
| `size` | 12 to 120 | 34 | Its height. |
| `style` | `arrow`, `touch` | `arrow` | `touch` is a translucent fingertip, for phone demos. |

A move arrives at **scene** beat `at` on `to`: a layer's id (its anchor at that beat), `"<photo set id>:<photo id>"` for a tile, or `[x, y]`, plus `dx`/`dy` units. `click: true` clicks on arrival, `hold` keeps the button down that many beats (a long press, 0.05 to 8), and `drag: true` holds it while travelling there from the move before. Click exactly when the thing changes: a click at beat 3 means the pill state, the layer `start` or the camera flight it causes is at 3 too, or `lint` reports an idle click. Give the cursor the same `id` in scenes joined by a `morph`, so it glides across the cut.

#### `group`

`{ "kind": "group", "layers": [...] }`: up to 24 layers that share one transform (position, scale, rotation, opacity, entrances) and pass down their `feel`. Groups nest at most 3 deep, and an empty group is dropped. A `fly` takes a top-level layer, never one inside a group.

#### A film that uses them

A 10-second vertical film: a stacked headline, a counter on an accent scene that the headline flies into, a dial under a slow camera, and an end card with a hopping dot and a sparkle (a `lottie` layer, from CLI v1.7.0).

```json
{
  "version": 1,
  "title": "Brew",
  "format": "9:16",
  "duration": 10,
  "tempo": 120,
  "seed": 7,
  "palette": "citrus",
  "fonts": { "display": "anton", "body": "inter", "mono": "jetbrains-mono" },
  "sound": { "style": "house" },
  "feel": "snappy",
  "scenes": [
    { "id": "hook", "beats": 4, "bg": "bg", "layers": [
      { "kind": "text", "text": "SKIP THE", "size": 150, "dy": -120, "unitEnter": "from-left" },
      { "kind": "text", "id": "line", "text": "LINE", "size": 150, "dy": 120, "start": 0.5, "unitEnter": "rise", "highlight": { "word": 0, "style": "underline" } }
    ] },
    { "id": "cups", "beats": 4, "bg": "accent", "enter": { "type": "fly", "from": "line" }, "layers": [
      { "kind": "counter", "from": 0, "to": 10000, "format": "0,000", "size": 220, "count": [0.3, 2.5], "label": "cups this morning" }
    ] },
    { "id": "ready", "beats": 4, "bg": "ink", "enter": { "type": "circle", "beats": 0.75 },
      "camera": { "zoom": [[0, 1.15], [4, 1, "out"]] },
      "layers": [
        { "kind": "dial", "to": 100, "fill": [0.3, 2.6], "radius": 310, "label": "ready in 3 min", "dy": -80 }
      ] },
    { "id": "end", "beats": 8, "bg": "bg", "enter": { "type": "zoom", "beats": 0.5 }, "layers": [
      { "kind": "text", "text": "BREW", "size": 170, "dy": -40, "dot": { "hop": true } },
      { "kind": "text", "text": "Order ahead", "font": "body", "case": "none", "size": 44, "dy": 140, "start": 1.5 },
      { "kind": "lottie", "preset": "sparkle", "width": 160, "x": 0.55, "y": -0.3, "start": 2, "speed": 3 }
    ] }
  ]
}
```

And a product story told as one continuous take: a cursor clicks a button on the beat its state changes, and a morph carries the button into the next scene while the camera flies in.

```json
{
  "version": 1,
  "title": "Order flow",
  "format": "16:9",
  "duration": 8,
  "tempo": 120,
  "palette": "paper",
  "sound": { "style": "minimal" },
  "feel": "smooth",
  "scenes": [
    { "id": "order", "beats": 8, "bg": "bg", "layers": [
      { "kind": "text", "text": "ONE TAP", "size": 110, "dy": -230 },
      { "kind": "pill", "id": "button", "height": 130, "size": 40, "dy": 60, "states": [
        { "at": 0, "text": "Order print" },
        { "at": 3, "text": "Ordered", "icon": "check" },
        { "at": 5, "text": "Printing", "progress": true },
        { "at": 7, "text": "On its way", "icon": "route" }
      ] },
      { "kind": "cursor", "moves": [
        { "at": 1, "to": [0.6, 0.7] },
        { "at": 3, "to": "button", "click": true }
      ] }
    ] },
    { "id": "done", "beats": 8, "bg": "bg", "enter": { "type": "morph", "beats": 1 },
      "camera": { "focus": [{ "at": 2, "to": "button", "zoom": 1.3 }, { "at": 6, "to": [0, 0], "zoom": 1 }] },
      "layers": [
        { "kind": "pill", "id": "button", "height": 130, "size": 40, "dy": 60, "states": [{ "at": 0, "icon": "check", "circle": true }] },
        { "kind": "text", "text": "DELIVERED", "size": 110, "dy": -230, "start": 1, "unitEnter": "type" }
      ] }
  ]
}
```

### Photos and clips

A film can show your own photos and video clips. Each is listed once in a table on the document, under an id, and layers name it by that id; a layer that names one the table does not have is dropped. `--photo` and `--clip` on `generate` and `revise` write these tables for you, measuring each file; by hand, give the same fields.

**`photos`**, up to 12:

| Field | Value | What it is |
|---|---|---|
| `id` | text, up to 24 characters (**required**) | What layers call it: `p1`, `p2`, ... as the CLI numbers them. |
| `src` | `file:<path>` | A local photo (JPEG, PNG, WebP, GIF or HEIC), relative to the film file; keep it beside the film when you move it. |
| `mediaId` | a library media id | A library photo, with `src` its library path (`/api/images/...`): what `--photo media:<id>` writes. |
| `width`, `height` | pixels, as displayed (after EXIF rotation) (**required**) | The photo's shape, which sets its box. |
| `description` | up to 400 characters | What it shows, for the model to cast it by. |

**`clips`**, up to 4, are listed the same way (`v1`, `v2`, ...), plus `duration` (seconds, **required**) and `audio` (`true` when it has a sound track; a clip without one cannot play sound). `width` and `height` are its size after rotation, and `poster` a still shown until its first frame decodes. Clips are a cast of their own: a photo set, a photo morph or a `mark` never shows one.

#### `image`: one photo

A photo in a rounded box: a hero shot, a print on a wall, a before and after.

| Field | Value | Default | What it does |
|---|---|---|---|
| `photo` | a photo's id (**required**) | | Which photo. |
| `width`, `height` | 40 to 2400 | 560 on the long side | Its box; give one side and the other follows the photo (a hero is 800 to 1000 wide where the frame allows). |
| `fit` | `cover`, `contain` | `cover` | How the photo fills the box. |
| `radius` | 0 to 400 | 18 | Corner radius. |
| `focus` | `[fx, fy]`, 0 to 1 across and down | `[0.5, 0.5]` | The point kept in view when the box crops it, a face for instance. |
| `zoom` | *Num*, 0.2 to 6 | 1 | The photo inside its box: `[[0, 1], [8, 1.08]]` is a slow push-in. |
| `grade` | `golden`, `mono`, `cool`, `fade` | none | A colour grade: `golden` relights it toward golden hour, `mono` is black and white. |
| `amount` | *Num*, 0 to 1 | 1 | How much of the grade: `[[1, 0], [3, 1, "inOut"]]` relights it on screen. |
| `frame` | `{ "at", "mat", "molding", "matColor", "color" }`, or `true` | none | A framed print: from scene beat `at` a mat (0 to 400 units, `matColor` default `paper`) and a molding (0 to 200, `color` default `ink`) grow out of the photo's edge. |
| `shadow` | `true`, `false` | `true` | A soft shadow. |

#### `photos`: a photo set

Several photos laid out together as tiles. Each tile is addressable as `"<layer id>:<photo id>"` (for a cursor move or a camera focus), and an `image` of the same photo in the next scene, joined by a `morph`, opens out of its tile: click a tile, then morph into its hero.

| Field | Value | Default | What it does |
|---|---|---|---|
| `photos` | up to 12 photo ids (**required**) | | The tiles, in order. |
| `layout` | `grid`, `bento`, `row`, `stack` | `grid` | A grid; a bento (the first photo big); a row (a film strip); a stack (a loose pile). |
| `reflow` | `[{ "at", "layout" }]` (`at` **required** in each; `layout` defaults to `bento`) | none | At each scene beat `at`, every tile glides to its place in another layout. |
| `width` | 100 to 3000 | 1.5 x the short half-frame | The whole set's width. |
| `gap` | 0 to 200 | 2.5% of the width | Between tiles. |
| `radius` | 0 to 200 | 14 | Tile corners. |
| `intro` | `unfold`, `pop`, `none` | `unfold` | `unfold` opens from the centre tile like a paper map. |

#### `video`: a clip

A clip playing in a box like an image or, with `bleed`, filling the frame as the scene's footage. It plays at real speed from `in` as the layer starts.

| Field | Value | Default | What it does |
|---|---|---|---|
| `clip` | a clip's id (**required**) | | Which clip. |
| `in` | seconds into the clip | 0 | Where it starts playing. |
| `out` | seconds | the clip's end | Where it stops. |
| `speed` | 0.25 to 4 | 1 | 0.5 is slow motion; sound plays only at 1. |
| `after` | `hold`, `loop` | `hold` | Past `out`: hold the last frame, or play again from `in`. |
| `volume` | 0 to 1 | muted | The clip's own sound; leave it out and the clip is silent under the music. |
| `bleed` | `true`, `false` | `false` | Fills the whole frame (then no box, radius, frame or shadow). |
| `scrim` | 0 to 1 | none | Lays the scene's background over full-frame footage so words on it read (0.3 to 0.5). |
| `width`, `height`, `fit`, `radius`, `focus`, `zoom`, `grade`, `amount`, `frame`, `shadow` | as for `image` | | A clip in a box; with `bleed`, only `fit`, `focus`, `zoom`, `grade` and `amount` apply. |

A clip that opens its scene is revealed by the scene's transition, so it needs no `enter` of its own, and a video cannot leave a `trail`.

```json
{
  "version": 1,
  "title": "Weekend",
  "format": "9:16",
  "duration": 10,
  "tempo": 120,
  "palette": "mono",
  "fonts": { "display": "instrument-serif", "body": "inter", "mono": "jetbrains-mono" },
  "sound": { "style": "ambient" },
  "feel": "cinematic",
  "photos": [
    { "id": "p1", "src": "file:photos/dunes.jpg", "width": 4032, "height": 3024 },
    { "id": "p2", "src": "file:photos/campfire.jpg", "width": 3024, "height": 4032 },
    { "id": "p3", "src": "file:photos/stars.jpg", "width": 4032, "height": 3024 }
  ],
  "clips": [
    { "id": "v1", "src": "file:clips/drive.mov", "width": 1080, "height": 1920, "duration": 12.5, "audio": true }
  ],
  "scenes": [
    { "id": "set", "beats": 4, "bg": "bg", "layers": [
      { "kind": "photos", "id": "trip", "photos": ["p1", "p2", "p3"], "layout": "row", "width": 900, "dy": -80 },
      { "kind": "text", "text": "Out west", "case": "none", "italic": true, "size": 90, "dy": 330, "start": 1 }
    ] },
    { "id": "hero", "beats": 8, "bg": "bg", "enter": { "type": "morph", "beats": 1 }, "layers": [
      { "kind": "image", "photo": "p2", "width": 640, "dy": -120,
        "zoom": [[0, 1], [8, 1.08, "linear"]], "grade": "golden", "amount": [[1, 0], [3, 1, "inOut"]], "frame": { "at": 4 } },
      { "kind": "text", "text": "golden hour", "case": "none", "italic": true, "size": 70, "dy": 640, "start": 2 }
    ] },
    { "id": "road", "beats": 8, "bg": "bg", "enter": { "type": "push", "direction": "up" }, "layers": [
      { "kind": "video", "clip": "v1", "in": 2, "bleed": true, "scrim": 0.4 },
      { "kind": "text", "text": "Next stop", "case": "none", "italic": true, "size": 110, "start": 1 }
    ] }
  ]
}
```

### Craft

The rules `generate` follows, for a film that reads well:

- **One idea per bar.** Most scenes are 4 beats; 2-beat scenes make a punchy run, and 8 a hold (usually the end card). Every scene starts on a downbeat, and every bar of a scene brings something new (a click and its change, a pill state, a note, a morph, a camera move).
- **Contrast between scenes.** Alternate the backgrounds (dark, light, accent) so each cut reads as a hit. Text is `ink` on light backgrounds and `paper` on dark ones, and needs at least 3:1 contrast.
- **Huge type, few words.** A headline has at most 4 words, in capitals, weight 900, size 100 to 160 (100 or more even in a UI story; UI labels 20 to 28). Split a long message across scenes, or stack 2 or 3 text layers with `dy` offsets and staggered starts (0, 1, 2).
- **Count the characters.** At size S a line holds about 900 / S characters in 9:16 and 1:1, and 1800 / S in 16:9; about 40% more in a condensed face (`anton`, `bebas-neue`, `instrument-serif`), fewer in a wide one (`archivo-black`). Big type wraps to 3 lines at most.
- **Space stacked words.** A text layer's `y`/`dy` is the centre of its block, and each extra line grows it up and down by 1.35 x size (1.7 x in the body and mono faces). Words on screen together need clear space of at least 0.35 x the bigger size: one-line layers of size S sit at least 1.35 x S apart in `dy` (at size 120, `dy` -85 and 85), and a line of size s under a headline of size H sits at least 0.85 x H + 0.5 x s below it. Widgets draw words of their own: a dial's readout and label reach about 1.5 x its radius below its centre, a clock's time its radius + 100, and a counter's label about its size. Keep other words below those, or use the widget's own `label`.
- **Give words time.** About 0.35 s plus 0.22 s a word on screen before a text leaves.
- **One accent per scene:** a highlighted word, a dot, or one accent-coloured shape.
- **Transitions that fit the energy:** `circle` and `zoom` for big reveals, `fly` when a claim or a logo should carry the cut, `push` and `wipe` for flow, `whip` for speed, `glitch` and `shutter` for tech.
- **The brand early and last:** the message in the first two bars, and an end card (a wordmark with a hopping dot, a tagline, a small credit line) in the last one or two. Never add a "made with" line: the renderer draws its own mark.
- **Keep it light:** 3 or 4 layers a scene.
- **Product and UI stories in one take:** join scenes with `morph` (shared ids), `flood` and `iris` instead of cuts, and let a cursor's clicks trigger each change on its beat.
- **Inside the safe area:** keep what matters within 0.85 of the centre, and words clear of shapes, pills, dials and photos (beside them, or centred inside).
- **Photos breathe:** the hero on screen at least a bar, big, with a slow push-in or a grade move; never text over a face; short words (1 to 4, size 40 to 90) beside or below a photo.
- **Clips are the proof:** a clip that is the point gets its own scene, usually full frame, for long enough to show what it shows; hold any clip at least 2 s; words on full-frame footage are short, over a `scrim`.

### What the engine repairs

The engine turns any JSON into a film it can render and never fails on a document. Before it draws:

- **Unknown fields are dropped, without a warning.** A misspelt field (`"szie": 90`) simply does nothing, so check names against the tables above.
- **Unknown values are dropped or replaced by the default:** a kind, a transition, a colour or a font with a warning; an ease (except in a graph's `curves`), a palette name or a mesh shape without one. A layer that cannot draw without one is dropped: text without `text`, a counter without `to`, a graph with neither `curves` nor `values`, a pill without states, a cursor without moves, rings without rows, lines without a `pattern`, a figure without a `figure`, a picture whose photo or clip is not in the film's tables.
- **Numbers are clamped** to their field's range. A plain number field says so in a warning, but a number in keys or an oscillator's `amp`, a `[start, end]` pair and an `[x, y]` target are clamped without one: check those against the tables. A pair whose end is not after its start becomes `[start, start + 0.5]`.
- **Beats are rescaled** when the scenes do not add up to the film's beats, with a warning.
- **Limits:** 48 scenes (24 before CLI v1.8.4), 24 layers a scene, groups 3 deep, 32 keyframes a value, 12 photos and 4 clips; the rest is dropped.
- **Plain-language names** are read as the engine's: `chart` as `graph`, `button` as `pill`, `photo` as `image`, `clip` as `video`, `skottie` as `lottie` (from CLI v1.7.0), `magic-move` as `morph`, `ease-in-out` as `inOut` (in keys), `typewriter` as `type`, `slide-left` as `from-right`, `calm` as `smooth`. They are there for the model; write the names in the tables.

`5am motion lint` prints the repairs that warn under `warnings` (not the silent ones above), and the layout problems left under `issues` (`fix` or `note`): text on screen too briefly to read, text under 3:1 contrast, big type that wraps past 3 lines, words that collide or crowd, words past the frame's edge (or pushed past it by a camera zoom), words that run into a photo, clip, shape, pill or dial, letters that drop through the words above them, a `morph` with no shared id, a `fly` or `flood` naming a missing layer, a click that changes nothing, words on full-frame footage without a scrim, words on the chapter scrubber, a face that cannot draw its text, and more scenes than the eye can follow. A film with fixes left still renders. `lint` changes nothing; `generate` and `revise` also tidy what the model wrote (words moved clear of photos, clicks snapped to their changes, and from CLI v1.7.0 Lottie loops paced).

## Agents and scripts

- **Iterate on the film, not the MP4.** `lint` and `sheet` are free; `revise` makes changes; `render` once at the end.
- **Edit the film directly when you know the change.** [The film file](#the-film-file) lists every field with its range and default. Lint after each edit: `.warnings` lists the repairs that warn (clamps in keys, pairs and targets do not: see [What the engine repairs](#what-the-engine-repairs)), `.fixes` the layout problems left. A misspelt field is dropped without a warning.
- **Read the JSON.** For `generate`, the film path is `.output`. For `render`, the MP4 path is `.output` and the charge is `.credits`. A dry run has `.dryRun: true` and no `.output`.
- **Never repeat a paid render after an error.** A refused final charge is recovered with `5am motion finalize <requestId>`.
- **Let a render finish.** A minute or two is normal. Give it a timeout that does not kill it, or run it in the background and check on it: a render killed partway keeps its reservation for a day, and ten of them stop every export (see [`finalize`](#finalize)).
- **AI-character tokens cannot export.** Use a personal access token with write scope.
- **Never run `preview` unattended.** It waits for a person and never exits on its own; look at a film with `sheet`.
- **Check a new machine with `doctor`.** It is free and exits 1 when the engine renders use is missing (Skia unless `FIVEAM_MOTION_ENGINE=chrome`); read `.skia.error` or `.chrome.error` for why. A missing Chrome alone does not fail it on a Skia machine.
- **Managed cloud workflows** have the runtime, Skia and every font installed: generate, narrate, check and render there as anywhere else.

## Not in the CLI

Exports without the "Made with 5AM.app" mark ([Ad Maker](https://5am.app/ad-maker) on 5am.app), and sending a film to Motion Studio on the web.

## Troubleshooting

| Message | What to do |
|---|---|
| `Motion needs the image-edit runtime` | `5am update --runtime-only` |
| `the installed runtime has no Motion support` / `incompatible motion runtime` | Update the CLI and the runtime together: `5am update`, then `5am update --runtime-only` |
| `Motion Studio is not enabled on this server` | Motion Studio is not available on that server |
| `insufficient_scope` | Your token is read-only; create one with write scope in [Settings → Keys](https://5am.app/settings#keys) under CLI Access Tokens |
| `not enough AI credits: this export costs 20 credits and you have …` | `5am credits buy` (a payment link you can pay on your phone without signing in), then render; nothing was rendered or charged |
| `AI credits are paused right now, so exports cannot be paid for` | AI credits are paused for a while on 5am.app; nothing was charged, try again later |
| `ffmpeg not found` | Install FFmpeg, or pass `--ffmpeg /path/to/ffmpeg` |
| `No folder for the stills` | Create the `--out-dir` folder first; from CLI v1.7.0, `stills` creates it |
| `too_many_pending_exports`, or `… unfinished exports are reserved on this account` | Renders were killed partway: `5am motion finalize --unfinished` on the computer that ran them (CLI v1.6.1 or later), or wait 24 hours from the oldest |
| `Skia isn't installed: …` | Run `5am update --runtime-only` again: it says why it could not install Skia (no npm beside Node.js, no network, or no prebuilt Skia for the platform). Nothing was charged. To draw with Chrome meanwhile, pass `--engine chrome` or set `FIVEAM_MOTION_ENGINE=chrome` |
| `unknown motion engine "…": use skia or chrome` | Unset `FIVEAM_MOTION_ENGINE`, or set it to `skia` or `chrome` (there is no `auto`) |
| `this motion runtime predates the skia engine` | The runtime is older than the CLI: `5am update --runtime-only` |
| Chrome not found | Chrome is needed only for `--engine chrome` (or `FIVEAM_MOTION_ENGINE=chrome`) and `preview` with video clips; `doctor` reports it otherwise. Install Chrome or Chromium, or pass `--browser` / set `CHROME_PATH`. On Debian, `apt install chromium`; on Ubuntu, `chromium-browser` is only a Snap stub that does not run in containers, so install Google Chrome's .deb instead |
| `Motion needs Node.js 20 or newer` | Install Node.js 20 or newer (Ubuntu 24.04 and Debian 12 ship 18 through `apt`) |
| `video clips in Motion films are not enabled on this server` | Video clips are not available on that server yet; use photos |
| `video clips are read with ffmpeg and the ffprobe beside it` (Skia), or `a clip this browser cannot decode needs a proxy made with ffmpeg` (`--engine chrome`) | Install FFmpeg, or pass `--ffmpeg` |
| `The voice is …s long. Shorten the script to fit …s` | Shorten the script, or lengthen the film, and narrate again |
| `The narration is …s long and the film …s` | The film got shorter after the take: `narrate --overwrite`, or `--no-narration` |
| Frames with wrong colours or stripes with `--engine chrome` | A graphics driver problem: render with `FIVEAM_MOTION_PIXELS=rgba`, or with Skia, the default |
