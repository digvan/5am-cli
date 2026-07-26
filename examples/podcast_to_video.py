#!/usr/bin/env python3
"""podcast_to_video.py — turn a podcast audio file into a shareable video.

A single stdlib-only Python script (no pip install) that wraps the full 5am CLI
flow. Cross-platform on purpose — it runs the same on macOS, Linux, and
Windows.

Two modes, both wrapping the 5am CLI in one command:

  Veo b-roll (default): generate enough short (~8s) Veo clips to cover the
    audio, concatenate them, lay the audio on top, and optionally burn in a
    transcript. AI-generated visuals — costs Gemini quota, takes minutes.
    When a transcript (-s) is supplied, the Veo prompts are written by Gemini
    from that transcript (one cinematic scene per clip, in narrative order) so
    the b-roll visually tracks the conversation. Pass -p to override with your
    own prompts, or --no-scene-prompts to use the generic rotation instead.

  Waveform (--visualize): skip Veo entirely and render an animated waveform
    over a cover image (or a solid slate background), with the audio embedded
    and an optional transcript. Instant, free, no API calls — just ffmpeg.

Either way the result is an MP4 ready for YouTube / X / Instagram / TikTok.

Pairs with 5AM's Podcast Studio, which produces the WAV and a sample-accurate
.srt/.vtt transcript to feed this script:
  https://5am.app/podcast   ·   https://5am.app/blog/introducing-podcast-studio

Needs a local ffmpeg, and `5am login` for the Veo b-roll mode (the waveform
mode is entirely local — no API calls, no quota).

Usage:
  python3 podcast_to_video.py -i episode.wav [options]
  python3 podcast_to_video.py -i episode.wav --visualize --cover cover.jpg [options]

Examples:
  python3 podcast_to_video.py -i episode.wav
  python3 podcast_to_video.py -i episode.wav -a 9:16 -o reel.mp4
  python3 podcast_to_video.py -i episode.wav -s episode.srt           # burn in captions
  python3 podcast_to_video.py -i episode.wav --visualize --cover cover.jpg -s episode.srt
  python3 podcast_to_video.py -i episode.wav \
      -p "cozy dev desk at night, terminal glow, rain on the window" \
      -p "close-up of a glowing mechanical keyboard, scrolling code, bokeh"
"""

import argparse
import json
import math
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROG = "podcast-to-video"

# Veo preview models occasionally return a transient "no videos in response".
# Each clip is expensive, so retry a couple times before failing the whole run.
CLIP_RETRIES = 3
# Base backoff (seconds) before a retry, doubled each attempt and jittered.
# Under parallel generation (-j > 1) a burst of clips can trip Veo rate limits;
# a randomized backoff spreads the retries out instead of re-firing them all at
# once. Attempt 2 waits ~CLIP_RETRY_BACKOFF, attempt 3 ~2× that (± jitter).
CLIP_RETRY_BACKOFF = 4.0


def retry_backoff_seconds(attempt):
    """Backoff before the given (1-based) attempt. Attempt 1 is the first try,
    so it never waits; later attempts wait an exponentially growing, jittered
    delay: base * 2^(attempt-2) ± up to 50% jitter."""
    if attempt <= 1:
        return 0.0
    base = CLIP_RETRY_BACKOFF * (2 ** (attempt - 2))
    return base * (0.5 + random.random())  # 0.5×–1.5× → spreads concurrent retries

# Default prompt set if the caller gives none. These rotate across clips so a
# multi-clip video has visual variety rather than N copies of one scene.
# These deliberately avoid any legible on-screen text — monitors show abstract
# glow/blur, not readable code/UI — because Veo renders text as garbled
# gibberish. NO_TEXT_SUFFIX below reinforces this on every clip.
DEFAULT_PROMPTS = [
    "Cozy software developer's desk at night, warm lamp glow, an out-of-focus monitor emitting a soft green glow (no readable text), a steaming coffee mug, gentle rain on the window behind. Slow calm camera push-in. Lo-fi, atmospheric, no people.",
    "Close-up of a glowing mechanical keyboard under a desk lamp, a heavily blurred monitor with abstract colored light in the background (no legible characters), rising coffee steam, warm amber and teal bokeh, rain on a window. Slow drifting camera. Calm lo-fi, no people.",
    "Abstract glowing data streams and flowing particle graphs in a dark server room, soft blue and cyan light, drifting motes. Slow cinematic dolly. No text, no people.",
    "A tidy desk with an open laptop showing only soft abstract color (screen out of focus, no readable UI), plants, soft morning light through a window, a notebook and pen. Gentle slow pan. Calm and minimal, no text, no people.",
]

# Appended to every Veo prompt so the model avoids rendering text — Veo is
# notoriously bad at it and produces misspelled, garbled words. We append to the
# prompt rather than using --negative-prompt because the lite/fast Veo models
# reject `negativePrompt` (HTTP 400); a positive in-prompt instruction works on
# every model.
NO_TEXT_SUFFIX = (
    "Important: absolutely no text, words, letters, numbers, captions, signage, "
    "logos, or readable UI anywhere in the frame — any screens, books, or signs "
    "must be blank, abstract, blurred, or out of focus."
)


def log(msg):
    print(f"[{PROG}] {msg}", file=sys.stderr)


def err(msg):
    print(f"[{PROG}] error: {msg}", file=sys.stderr)
    sys.exit(1)


class ClipJobs:
    """Tracks the live `5am media generate video` child processes so the run can
    truly fail fast under -j: when one clip fails, we cancel the rest.

    `with ThreadPoolExecutor(...)` calls shutdown(wait=True) on exit, which would
    otherwise block until every in-flight (minutes-long, quota-burning) Veo
    generation finishes before the script exits. Worker threads can't be killed
    in Python, but the *expensive* work is the child subprocess — so on failure
    we set the cancel flag (queued/retrying clips bail out without firing new
    requests) and terminate the running children (stops the quota burn). The
    ThreadPoolExecutor then drains near-instantly because its workers exit as
    soon as their now-killed subprocess returns."""

    def __init__(self):
        self._lock = threading.Lock()
        self._procs = {}            # id(proc) -> Popen
        self.cancelled = False

    def register(self, proc):
        with self._lock:
            self._procs[id(proc)] = proc

    def unregister(self, proc):
        with self._lock:
            self._procs.pop(id(proc), None)

    def cancel(self):
        """Mark the run cancelled and terminate every live child process. Safe
        to call from any thread; idempotent.

        We kill the whole process *group* (the children are started with
        start_new_session=True so each is its own group leader) — the `5am`
        binary may spawn its own children, and SIGTERM to just the immediate
        child wouldn't reap those grandchildren, leaving the worker blocked in
        proc.wait() and the script unable to exit. Falls back to proc.kill() on
        platforms without process groups (Windows)."""
        with self._lock:
            self.cancelled = True
            procs = list(self._procs.values())
            self._procs.clear()
        for proc in procs:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, AttributeError, OSError):
                try:
                    proc.kill()
                except Exception:
                    pass


def is_executable(path):
    return path and os.path.isfile(path) and os.access(path, os.X_OK)


def resolve_cli_bin(flag_value):
    """Resolve the 5am binary: --bin, then ./bin/5am relative to this script's
    repo, then PATH. On Windows also try the .exe suffix."""
    if flag_value:
        if not is_executable(flag_value):
            err(f"5am binary not executable: {flag_value}")
        return flag_value

    # A ./bin/5am sitting one level up from this script (handy if you keep the
    # binary alongside a checkout); otherwise fall through to PATH.
    script_dir = Path(__file__).resolve().parent
    for name in ("5am", "5am.exe"):
        candidate = script_dir.parent / "bin" / name
        if is_executable(str(candidate)):
            return str(candidate)

    found = shutil.which("5am")
    if found:
        return found
    err("5am binary not found — pass --bin <path>, or put it on PATH")


def resolve_ffmpeg(flag_value):
    """Resolve ffmpeg: --ffmpeg / $FFMPEG, then PATH. The 5am CLI resolves it
    the same way internally; we resolve here too so we can read the audio
    duration."""
    candidate = flag_value or os.environ.get("FFMPEG", "")
    if candidate:
        if not is_executable(candidate):
            err(f"ffmpeg not executable: {candidate}")
        return candidate

    found = shutil.which("ffmpeg")
    if found:
        return found
    err("ffmpeg not found — pass --ffmpeg <path> or set $FFMPEG (brew install ffmpeg / apt install ffmpeg)")


def measure_audio_seconds(ffmpeg_bin, input_path):
    """Parse 'Duration: HH:MM:SS.ss' out of ffmpeg's stderr — avoids a hard
    dependency on ffprobe (ffmpeg always prints this for a readable input).
    Returns ceil(duration) as an int (rounded up to a whole second)."""
    proc = subprocess.run(
        [ffmpeg_bin, "-i", input_path],
        capture_output=True, text=True,
    )
    # ffmpeg writes the banner+metadata (including Duration) to stderr and
    # exits non-zero because no output file was given; that's expected.
    combined = proc.stderr + proc.stdout
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", combined)
    if not m:
        err(f"could not read audio duration from: {input_path}")
    hours, minutes, seconds = int(m.group(1)), int(
        m.group(2)), float(m.group(3))
    total = hours * 3600 + minutes * 60 + seconds
    audio_secs = math.ceil(total)
    if audio_secs <= 0:
        err("audio duration computed as 0s — is the file valid?")
    return audio_secs


def run_cli(cli_bin, args):
    """Run the 5am CLI, discarding stdout (JSON we don't need here) but letting
    stderr pass through so the user sees progress. Returns True on success."""
    proc = subprocess.run([cli_bin, *args], stdout=subprocess.DEVNULL)
    return proc.returncode == 0


def run_cli_tracked(cli_bin, args, jobs):
    """Like run_cli, but registers the child process with `jobs` so it can be
    terminated if another clip fails (true fail-fast under -j). Returns True on
    success. Returns False immediately if the run is already cancelled, so a
    queued clip doesn't fire a fresh quota-consuming request."""
    if jobs.cancelled:
        return False
    # start_new_session=True puts the child in its own process group so cancel()
    # can SIGTERM the whole tree (the `5am` binary may spawn its own children).
    proc = subprocess.Popen(
        [cli_bin, *args], stdout=subprocess.DEVNULL, start_new_session=True)
    jobs.register(proc)
    try:
        proc.wait()
    finally:
        jobs.unregister(proc)
    return proc.returncode == 0


def run_ffmpeg(ffmpeg_bin, args):
    """Run ffmpeg with stderr passed through (progress/diagnostics) and stdout
    discarded. Raises on failure."""
    proc = subprocess.run([ffmpeg_bin, *args])
    if proc.returncode != 0:
        err("ffmpeg failed")


def escape_subtitle_path(path):
    """Escape a path for ffmpeg's filtergraph `subtitles=filename=` value:
    backslash first (so our escapes aren't re-escaped), then the colon (option
    separator) and comma (filter separator) so a path like `episode, part 1.srt`
    doesn't split the filtergraph. Matches what `5am media visualize` does
    internally. A single quote is NOT escaped — ffmpeg's subtitles filter can't
    round-trip one, so the caller rejects such paths up front."""
    path = path.replace("\\", "\\\\")
    path = path.replace(":", "\\:")
    path = path.replace(",", "\\,")
    return path


def subtitle_path_has_unsupported_chars(path):
    """Whether the subtitle path contains a character ffmpeg's subtitles filter
    can't consume via filename= regardless of escaping. The single quote is the
    practical case — reject it with a clear message rather than a cryptic render
    failure."""
    return "'" in path


# --- transcript-driven scene prompts ---------------------------------------
# When a transcript is supplied (-s), we can make the Veo b-roll *about the
# content* instead of generic stock loops: extract the spoken text and ask
# Gemini (via `5am media generate text`) to write one cinematic scene prompt
# per clip, in order, so each clip visually tracks what's being said.

_VTT_TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})"
)


def transcript_text(subtitle_path):
    """Extract the plain spoken text from a .srt/.vtt file, in order, as a single
    string. Drops cue numbers, timestamp lines, the WEBVTT header, and inline
    `<v Speaker>` / other tags so only dialogue remains."""
    lines = []
    with open(subtitle_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line == "WEBVTT" or line.isdigit():
                continue
            if _VTT_TS.search(line):
                continue
            # Strip <v Speaker> and any other angle-bracket tags.
            line = re.sub(r"<[^>]*>", "", line).strip()
            if line:
                lines.append(line)
    return " ".join(lines)


def generate_scene_prompts(cli_bin, subtitle_path, count, aspect):
    """Ask Gemini (via the CLI's `media generate text`) to write `count` cinematic
    b-roll scene prompts tailored to the transcript, one per line, in narrative
    order. Returns a list of prompt strings (best-effort length), or None if the
    call fails / yields nothing usable — callers fall back to DEFAULT_PROMPTS."""
    body = transcript_text(subtitle_path)
    if not body:
        return None

    instruction = (
        f"You are a visual storyteller directing the footage for a podcast video "
        f"in a {aspect} aspect ratio. The goal is NOT pretty wallpaper — it is to "
        f"make someone keep watching because the visuals TELL THE STORY of the "
        f"conversation. Read the transcript and write exactly {count} scene "
        f"descriptions, ONE PER LINE, in chronological order so that scene N maps "
        f"to the part of the conversation playing during clip N.\n\n"
        "Make each scene EARN the viewer's attention:\n"
        "- ILLUSTRATE THE ACTUAL IDEA. Each scene should visually explain or "
        "symbolize the specific thing being discussed at that moment (a concept, "
        "a claim, an example, the 'kicker'), so a muted viewer still follows the "
        "argument. Concrete and literal beats vague and abstract.\n"
        "- MIRROR THE EMOTION. Match the speaker's beat at that point — curiosity, "
        "skepticism, the build-up, the surprise reveal, the confident payoff — "
        "through pacing, lighting, and camera energy.\n"
        "- TELL ONE STORY ACROSS THE SET. Treat the scenes as a single narrative "
        "arc with a hook, a build, and a satisfying payoff on the closing line — "
        "not interchangeable loops. Let motifs evolve and recur so it feels "
        "authored, not stock.\n"
        "- Be cinematic and specific: name the subject, the camera move, the "
        "lighting, the mood. Real, filmable scenes. Avoid logos and recognizable "
        "faces.\n"
        "- ABSOLUTELY NO TEXT IN THE FRAME. The video model cannot render words — "
        "it produces garbled, misspelled gibberish. Never describe anything with "
        "readable text, letters, numbers, code, signs, labels, captions, titles, "
        "or UI text. Convey ideas through objects, action, motion, and symbolism "
        "instead. If a concept seems to need words (a screen, a book, a sign, a "
        "chart), render it as abstract glow, blur, shapes, or out-of-focus so "
        "nothing legible appears.\n\n"
        "Output rules (strict):\n"
        "- Output ONLY the scene descriptions, one per line. No numbering, no "
        "bullets, no commentary, no blank lines, no scene labels.\n"
        "- Exactly one vivid scene per line (1-2 sentences).\n"
        "- No scene may contain any readable text, letters, or numbers in the "
        "frame.\n\n"
        f"Transcript:\n{body}"
    )

    proc = subprocess.run(
        [cli_bin, "media", "generate", "text", "--prompt", instruction],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        log("scene-writer: `media generate text` failed; falling back to default prompts")
        if proc.stderr.strip():
            log(f"scene-writer stderr: {proc.stderr.strip().splitlines()[-1]}")
        return None

    prompts = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    # Drop any accidental leading numbering/bullets the model may add.
    prompts = [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", p) for p in prompts]
    prompts = [p for p in prompts if p]
    if not prompts:
        log("scene-writer: model returned no usable lines; falling back to default prompts")
        return None
    return prompts


def parse_args(argv):
    # Repeated -p accumulates into a rotating list of scene prompts.
    p = argparse.ArgumentParser(
        prog="podcast_to_video.py",
        description="Turn a podcast audio file into a shareable video (Veo b-roll or waveform).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 podcast_to_video.py -i episode.wav\n"
            "  python3 podcast_to_video.py -i episode.wav -a 9:16 -o reel.mp4\n"
            "  python3 podcast_to_video.py -i episode.wav -s episode.srt\n"
            "  python3 podcast_to_video.py -i episode.wav --visualize --cover cover.jpg -s episode.srt\n"
        ),
    )
    p.add_argument("-i", "--input", required=True,
                   help="Podcast audio file (WAV/MP3/M4A/FLAC/OGG — anything ffmpeg reads)")
    p.add_argument("-a", "--aspect", default="16:9",
                   help="Output aspect ratio: 16:9 (default) or 9:16. 1:1 is also allowed in --visualize mode.")
    p.add_argument("-o", "--output", default="",
                   help="Output MP4 (default: <input-basename>-video.mp4)")
    p.add_argument("-s", "--subtitles", default="",
                   help="Transcript (.srt or .vtt) to burn in as captions")
    # Waveform mode
    p.add_argument("--visualize", action="store_true",
                   help="Render a waveform visualization instead of Veo b-roll")
    p.add_argument("-c", "--cover", default="",
                   help="Cover image (PNG/JPEG/WebP) behind the waveform (visualize mode)")
    p.add_argument("--style", default="showwaves",
                   help="Waveform style: showwaves (default), showfreqs, showcqt, showspectrum")
    # Veo b-roll mode
    p.add_argument("-m", "--model", default="veo-3.1-lite-generate-preview",
                   help="Veo model (default: veo-3.1-lite-generate-preview)")
    p.add_argument("-p", "--prompt", action="append", default=[], dest="prompts",
                   help="Base visual prompt for the clips. Repeat -p for rotating scenes.")
    p.add_argument("-n", "--clips", type=int, default=None, dest="force_clips",
                   help="Force exactly N clips (default: enough to cover the audio)")
    p.add_argument("-d", "--duration", type=int, default=8, dest="clip_duration",
                   help="Seconds per clip (default: 8)")
    p.add_argument("--max-clips", type=int, default=30, dest="max_clips",
                   help="Safety cap on auto-computed clip count (default: 30)")
    p.add_argument("--no-scene-prompts", action="store_true", dest="no_scene_prompts",
                   help="Disable transcript-driven scene prompts; use the default rotating set "
                        "(scene prompts are auto-used when -s/--subtitles is given and no -p is set)")
    p.add_argument("-j", "--jobs", type=int, default=1,
                   help="Parallel clip generations (default: 1, sequential)")
    # Plumbing
    p.add_argument("-b", "--bin", default="", dest="cli_bin",
                   help="Path to the 5am binary (default: ./bin/5am, then PATH)")
    p.add_argument("--ffmpeg", default="", dest="ffmpeg_bin",
                   help="Path to ffmpeg (default: $FFMPEG, then PATH)")
    p.add_argument("--workdir", default="",
                   help="Where to write intermediate clips (default: a temp dir, auto-cleaned)")
    p.add_argument("--keep", action="store_true",
                   help="Keep intermediate clips instead of deleting them")
    p.add_argument("-y", "--yes", action="store_true", dest="overwrite",
                   help="Overwrite the output if it exists")
    return p.parse_args(argv)


def validate(args):
    if not os.path.isfile(args.input):
        err(f"input file not found: {args.input}")

    # Veo only generates 16:9 / 9:16; the waveform path additionally supports 1:1.
    if args.visualize:
        if args.aspect not in ("16:9", "9:16", "1:1"):
            err(
                f"--aspect must be 16:9, 9:16, or 1:1 in --visualize mode (got: {args.aspect})")
    else:
        if args.aspect not in ("16:9", "9:16"):
            err(
                f"--aspect must be 16:9 or 9:16 (got: {args.aspect}). 1:1 is only available with --visualize.")

    if args.subtitles:
        if not os.path.isfile(args.subtitles):
            err(f"subtitles file not found: {args.subtitles}")
        if os.path.splitext(args.subtitles)[1].lower() not in (".srt", ".vtt"):
            err(f"--subtitles must be .srt or .vtt (got: {args.subtitles}). "
                "The Podcast Studio's .json transcript is not a subtitle format — "
                "export the .srt or .vtt instead.")
        if subtitle_path_has_unsupported_chars(args.subtitles):
            err(f"--subtitles path {args.subtitles!r}: a single quote (') can't be "
                "passed to ffmpeg's subtitles filter — rename or copy the file to a "
                "path without one.")

    if args.visualize:
        if args.cover and not os.path.isfile(args.cover):
            err(f"cover image not found: {args.cover}")
        # Warn about Veo-only flags that have no effect in waveform mode rather
        # than silently ignoring them (the user may think they're getting b-roll).
        if args.prompts or args.force_clips is not None or args.jobs != 1:
            log("note: --prompt/--clips/--jobs/--model are Veo b-roll options and are ignored in --visualize mode")
    elif args.cover:
        err("--cover only applies in --visualize mode. For Veo b-roll, the visuals come from --prompt scenes.")


def default_output(input_path):
    base = os.path.basename(input_path)
    stem = os.path.splitext(base)[0]
    return f"{stem}-video.mp4"


def run_visualize(args, cli_bin, ffmpeg_bin, output):
    """Waveform mode: `5am media visualize` does the waveform render, cover
    letterboxing, audio embedding, and subtitle burn-in in a single call. (It
    applies the same PlayResY=288 caption styling the b-roll path uses,
    positioned above the waveform strip — so transcripts render identically.)"""
    log(f"input:        {args.input}")
    log(f"mode:         waveform visualization (--style {args.style})")
    log(f"aspect:       {args.aspect}")
    log(f"cover:        {args.cover}" if args.cover else "cover:        (none — solid slate background)")
    if args.subtitles:
        log(f"subtitles:    {args.subtitles} (burned in)")
    log(f"output:       {output}")
    log(f"ffmpeg:       {ffmpeg_bin}")

    viz_args = [
        "media", "visualize", args.input,
        "--style", args.style,
        "--aspect", args.aspect,
        "--ffmpeg", ffmpeg_bin,
        "--output", output,
    ]
    if args.cover:
        viz_args += ["--cover", args.cover]
    if args.subtitles:
        viz_args += ["--subtitles", args.subtitles]
    if args.overwrite:
        viz_args += ["--yes"]

    log("rendering waveform visualization...")
    if not run_cli(cli_bin, viz_args):
        err("5am media visualize failed")
    if not (os.path.isfile(output) and os.path.getsize(output) > 0):
        err(f"output not produced: {output}")
    log(f"done → {output}")
    print(json.dumps({
        "output": output,
        "mode": "visualize",
        "style": args.style,
        "aspect": args.aspect,
        "cover": args.cover,
        "subtitles": args.subtitles,
    }))


def run_broll(args, cli_bin, ffmpeg_bin, output):
    """Veo b-roll mode: measure duration → generate clips → concat → mux audio
    → optional subtitle burn-in."""
    audio_secs = measure_audio_seconds(ffmpeg_bin, args.input)

    # Decide clip count: forced, or ceil(audio / clip_duration) capped at max.
    if args.force_clips is not None:
        clip_count = args.force_clips
    else:
        clip_count = math.ceil(audio_secs / args.clip_duration)
        if clip_count > args.max_clips:
            log(f"audio is {audio_secs}s → {clip_count} clips, capping at "
                f"--max-clips={args.max_clips} (video will loop short of the full "
                "audio; raise --max-clips to cover it all)")
            clip_count = args.max_clips
    if clip_count < 1:
        err(f"clip count computed as {clip_count}")

    # Choose the per-clip visual prompts. Priority:
    #   1. Explicit -p/--prompt from the user → use verbatim (rotated).
    #   2. A transcript (-s) with scene prompts enabled → ask Gemini to write
    #      `clip_count` scene prompts that track the conversation. Each clip then
    #      visually illustrates what's being said at that moment.
    #   3. Otherwise → the generic DEFAULT_PROMPTS rotation.
    scene_driven = False
    if args.prompts:
        prompts = args.prompts
    elif args.subtitles and not args.no_scene_prompts:
        log("scene-writer: deriving b-roll prompts from the transcript via Gemini...")
        scene_prompts = generate_scene_prompts(
            cli_bin, args.subtitles, clip_count, args.aspect)
        if scene_prompts:
            prompts = scene_prompts
            scene_driven = True
            log(f"scene-writer: got {len(prompts)} scene prompt(s) for {clip_count} clip(s)")
        else:
            prompts = DEFAULT_PROMPTS
    else:
        prompts = DEFAULT_PROMPTS

    # Set up workdir (temp + auto-clean, or user-supplied + kept).
    cleanup_workdir = False
    if args.workdir:
        workdir = args.workdir
        os.makedirs(workdir, exist_ok=True)
    else:
        workdir = tempfile.mkdtemp(prefix="podcast-video.")
        cleanup_workdir = not args.keep

    try:
        log(f"input:        {args.input} ({audio_secs}s)")
        log(f"aspect:       {args.aspect}")
        log(f"model:        {args.model}")
        log(f"clips:        {clip_count} × {args.clip_duration}s")
        log(f"prompts:      {'transcript-driven (Gemini scene-writer)' if scene_driven else 'default/-p rotation'}")
        if args.subtitles:
            log(f"subtitles:    {args.subtitles} (burned in)")
        log(f"output:       {output}")
        log(f"workdir:      {workdir}")
        log(f"ffmpeg:       {ffmpeg_bin}")

        clip_paths = [os.path.join(
            workdir, f"clip_{i:03d}.mp4") for i in range(1, clip_count + 1)]

        jobs = ClipJobs()

        def gen_clip(idx, out_path):
            prompt = prompts[(idx - 1) % len(prompts)]
            gen_args = [
                "media", "generate", "video",
                "--model", args.model,
                "--prompt", f"{prompt} {NO_TEXT_SUFFIX}",
                "--aspect-ratio", args.aspect,
                "--duration", str(args.clip_duration),
                "--output", out_path, "--yes",
            ]
            # Each Veo clip is expensive, and the preview models occasionally
            # return a transient "no videos in response" (or, under -j, a rate
            # limit) — so retry a few times before failing the whole run, with a
            # jittered backoff between attempts so concurrent retries don't all
            # re-fire at once. (Verified: re-running the same prompt succeeds.)
            for attempt in range(1, CLIP_RETRIES + 1):
                if jobs.cancelled:  # another clip already failed — don't burn quota
                    return
                wait = retry_backoff_seconds(attempt)
                if wait > 0:
                    log(f"clip {idx}: retrying in {wait:.1f}s "
                        f"(attempt {attempt}/{CLIP_RETRIES})...")
                    time.sleep(wait)
                else:
                    log(f"generating clip {idx}/{clip_count}...")
                if run_cli_tracked(cli_bin, gen_args, jobs):
                    return
                if jobs.cancelled:  # our child was terminated by a sibling failure
                    return
            err(f"clip {idx} generation failed after {CLIP_RETRIES} attempts")

        if args.jobs <= 1:
            # Sequential — simplest and safest. Each generation runs in the
            # foreground so it inherits the parent's auth context (the CLI reads
            # its token from the OS keychain, which forked children may not reach).
            for i, out_path in enumerate(clip_paths, start=1):
                gen_clip(i, out_path)
        else:
            # Parallel — faster, but each child must resolve auth on its own.
            # If your token lives only in the OS keychain, concurrent children
            # can hit "no token configured"; export 5AM_TOKEN (and optionally
            # 5AM_DISABLE_KEYRING=1) before running with --jobs > 1.
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                futures = [pool.submit(gen_clip, i, out_path)
                           for i, out_path in enumerate(clip_paths, start=1)]
                # as_completed yields futures the moment each finishes, so we
                # surface a failure as soon as ANY clip fails. gen_clip → err()
                # raises SystemExit, captured by the future and re-raised here.
                #
                # True fail-fast: on a failure, cancel the run BEFORE leaving the
                # `with` block. jobs.cancel() terminates the live Veo child
                # subprocesses (the actual quota cost) and flips the cancel flag
                # so queued/retrying clips bail out. Without this, the implicit
                # shutdown(wait=True) on `with` exit would block for minutes
                # waiting on in-flight generations we're about to discard.
                try:
                    for f in as_completed(futures):
                        f.result()
                except BaseException:
                    jobs.cancel()
                    pool.shutdown(wait=False)
                    raise

        for p in clip_paths:
            if not (os.path.isfile(p) and os.path.getsize(p) > 0):
                err(f"expected clip not produced: {p}")
        log(f"all {clip_count} clips generated")

        # Concat + mux audio. When burning in subtitles, write to an
        # intermediate file and burn captions in a final pass; otherwise write
        # straight to OUTPUT. (media concat stream-copies, can't burn subtitles.)
        mux_target = os.path.join(
            workdir, "muxed.mp4") if args.subtitles else output

        if len(clip_paths) == 1:
            # media concat needs >= 2 inputs; mux audio onto the lone clip directly.
            log("single clip — muxing audio directly with ffmpeg")
            ff = []
            if args.overwrite or args.subtitles:
                ff.append("-y")
            ff += [
                "-hide_banner", "-loglevel", "warning", "-stats",
                "-i", clip_paths[0], "-i", args.input,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-shortest",
                "-movflags", "+faststart", mux_target,
            ]
            run_ffmpeg(ffmpeg_bin, ff)
        else:
            log(f"concatenating {len(clip_paths)} clips and muxing audio...")
            concat_args = ["media", "concat", *clip_paths,
                           "--audio", args.input,
                           "--ffmpeg", ffmpeg_bin,
                           "--output", mux_target]
            if args.overwrite or args.subtitles:
                concat_args.append("--yes")
            if not run_cli(cli_bin, concat_args):
                err("5am media concat failed")

        if not (os.path.isfile(mux_target) and os.path.getsize(mux_target) > 0):
            err(f"muxed video not produced: {mux_target}")

        # Burn in subtitles (optional). Final re-encode that draws the captions
        # over the muxed video, bottom-center with a translucent box.
        if args.subtitles:
            log(f"burning in subtitles from {args.subtitles}...")
            # ffmpeg's subtitles filter converts SRT/VTT to an ASS with a FIXED
            # PlayResY=288; libass interprets MarginV/Fontsize in that 288-tall
            # space (scaled to the output), NOT in output pixels. So the style
            # values are constants in 288-units — resolution-independent. No
            # waveform strip in the b-roll video, so a small bottom inset is
            # enough. Studio cues are whole speaker turns (often 15-24s) that
            # wrap to many lines, so Fontsize=12 keeps even the longest on-screen.
            margin_v = 24    # ~8% of 288, inset from the bottom
            font_size = 12
            esc_sub = escape_subtitle_path(args.subtitles)
            sub_style = (f"Alignment=2,MarginV={margin_v},Fontsize={font_size},"
                         "PrimaryColour=&H00FFFFFF&,BorderStyle=4,BackColour=&H99000000&,"
                         "Outline=0,Shadow=0")
            ff = []
            if args.overwrite:
                ff.append("-y")
            ff += [
                "-hide_banner", "-loglevel", "warning", "-stats",
                "-i", mux_target,
                "-vf", f"subtitles=filename={esc_sub}:force_style='{sub_style}'",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
                "-movflags", "+faststart", output,
            ]
            run_ffmpeg(ffmpeg_bin, ff)

        if not (os.path.isfile(output) and os.path.getsize(output) > 0):
            err(f"output not produced: {output}")
        log(f"done → {output}")
        print(json.dumps({
            "output": output,
            "clips": clip_count,
            "clip_duration": args.clip_duration,
            "aspect": args.aspect,
            "model": args.model,
            "audio_seconds": audio_secs,
            "subtitles": args.subtitles,
            "scene_driven": scene_driven,
        }))
    finally:
        if cleanup_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validate(args)

    cli_bin = resolve_cli_bin(args.cli_bin)
    ffmpeg_bin = resolve_ffmpeg(args.ffmpeg_bin)

    output = args.output or default_output(args.input)
    if os.path.exists(output) and not args.overwrite:
        err(f"output {output} already exists — pass --yes to overwrite")

    if args.visualize:
        run_visualize(args, cli_bin, ffmpeg_bin, output)
    else:
        run_broll(args, cli_bin, ffmpeg_bin, output)


if __name__ == "__main__":
    main()
