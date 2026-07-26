#!/usr/bin/env python3
"""Tests for podcast_to_video.py.

Run: python3 examples/test_podcast_to_video.py

Stdlib unittest only — no pytest, nothing to install. Covers the pure helpers
(arg parsing, validation, subtitle-path escaping, duration parsing, output
naming) without invoking ffmpeg, the 5am CLI, or any paid API. Handy if you
adapt the script: edit it, re-run this, and you'll know immediately whether you
broke the plumbing. The end-to-end render is checked by hand.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import podcast_to_video as p2v  # noqa: E402


class EscapeSubtitlePathTests(unittest.TestCase):
    def test_plain_path_unchanged(self):
        self.assertEqual(p2v.escape_subtitle_path("episode.srt"), "episode.srt")
        self.assertEqual(p2v.escape_subtitle_path("/a/b/ep.srt"), "/a/b/ep.srt")

    def test_windows_drive_colon_and_backslashes(self):
        # Matches the escaping `5am media visualize` does internally.
        self.assertEqual(
            p2v.escape_subtitle_path(r"C:\videos\ep.srt"),
            r"C\:\\videos\\ep.srt",
        )

    def test_colon_is_escaped(self):
        self.assertEqual(p2v.escape_subtitle_path("/has:colon/ep.srt"), r"/has\:colon/ep.srt")

    def test_comma_is_escaped(self):
        # The filtergraph filter-separator — without escaping the path splits and
        # the render fails. (Verified end-to-end against real ffmpeg.)
        self.assertEqual(
            p2v.escape_subtitle_path("/dir/episode, part 1.srt"),
            r"/dir/episode\, part 1.srt",
        )
        self.assertEqual(
            p2v.escape_subtitle_path(r"C:\My Pods\ep, 2.srt"),
            r"C\:\\My Pods\\ep\, 2.srt",
        )

    def test_single_quote_not_escaped(self):
        # Single quotes are rejected up front (subtitle_path_has_unsupported_chars),
        # so escape_subtitle_path leaves them untouched rather than emitting a
        # path ffmpeg can't consume.
        self.assertEqual(p2v.escape_subtitle_path("/it's/ep.srt"), "/it's/ep.srt")


class SubtitleUnsupportedCharsTests(unittest.TestCase):
    def test_single_quote_flagged(self):
        for p in ("/it's/ep.srt", "ep'.srt", "/a/b'c.srt"):
            self.assertTrue(p2v.subtitle_path_has_unsupported_chars(p), p)

    def test_other_chars_supported(self):
        for p in ("episode.srt", "/dir/ep, part 1.srt", r"C:\vids\ep.srt", "/has space/ep.srt"):
            self.assertFalse(p2v.subtitle_path_has_unsupported_chars(p), p)


class DefaultOutputTests(unittest.TestCase):
    def test_strips_extension_and_appends_suffix(self):
        self.assertEqual(p2v.default_output("episode.wav"), "episode-video.mp4")
        self.assertEqual(p2v.default_output("/tmp/My Show.mp3"), "My Show-video.mp4")
        self.assertEqual(p2v.default_output("noext"), "noext-video.mp4")


class MeasureAudioSecondsTests(unittest.TestCase):
    def _fake_ffmpeg(self, stderr):
        cp = mock.Mock()
        cp.stderr = stderr
        cp.stdout = ""
        return cp

    def test_parses_duration_and_ceils(self):
        # 94.28s must round UP to 95 (matches the bash `+ 0.999` ceil trick).
        with mock.patch("subprocess.run", return_value=self._fake_ffmpeg(
                "  Duration: 00:01:34.28, bitrate: 384 kb/s\n")):
            self.assertEqual(p2v.measure_audio_seconds("ffmpeg", "x.wav"), 95)

    def test_hours_minutes_seconds(self):
        with mock.patch("subprocess.run", return_value=self._fake_ffmpeg(
                "  Duration: 01:02:03.00, ...\n")):
            self.assertEqual(p2v.measure_audio_seconds("ffmpeg", "x.wav"), 3723)

    def test_missing_duration_errors(self):
        with mock.patch("subprocess.run", return_value=self._fake_ffmpeg("no duration here")):
            with self.assertRaises(SystemExit):
                p2v.measure_audio_seconds("ffmpeg", "x.wav")


class ValidateTests(unittest.TestCase):
    """validate() calls err() (→ SystemExit) on bad input. We build a namespace
    that mirrors argparse's output and exercise each guard."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.audio = os.path.join(self.tmp, "ep.wav")
        open(self.audio, "w").close()
        self.srt = os.path.join(self.tmp, "ep.srt")
        open(self.srt, "w").close()
        self.cover = os.path.join(self.tmp, "cover.png")
        open(self.cover, "w").close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _args(self, **over):
        ns = mock.Mock()
        ns.input = over.get("input", self.audio)
        ns.aspect = over.get("aspect", "16:9")
        ns.subtitles = over.get("subtitles", "")
        ns.visualize = over.get("visualize", False)
        ns.cover = over.get("cover", "")
        ns.prompts = over.get("prompts", [])
        ns.force_clips = over.get("force_clips", None)
        ns.jobs = over.get("jobs", 1)
        return ns

    def test_ok_broll_minimal(self):
        p2v.validate(self._args())  # no raise

    def test_ok_visualize_with_cover_and_srt(self):
        p2v.validate(self._args(visualize=True, cover=self.cover, subtitles=self.srt))

    def test_missing_input(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(input="/nope.wav"))

    def test_aspect_1to1_rejected_in_broll(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(aspect="1:1"))

    def test_aspect_1to1_ok_in_visualize(self):
        p2v.validate(self._args(visualize=True, aspect="1:1"))

    def test_bad_aspect_rejected(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(aspect="4:3"))

    def test_json_subtitles_rejected(self):
        j = os.path.join(self.tmp, "ep.json")
        open(j, "w").close()
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(subtitles=j))

    def test_missing_subtitles_file(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(subtitles=os.path.join(self.tmp, "missing.srt")))

    def test_single_quote_subtitles_rejected(self):
        # A real file whose path contains a single quote — ffmpeg can't consume
        # it, so validate() must reject it up front (not fail at render time).
        q = os.path.join(self.tmp, "it's.srt")
        open(q, "w").close()
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(subtitles=q))

    def test_comma_subtitles_accepted(self):
        # A comma in the path is fine (escape_subtitle_path handles it) — must NOT
        # be rejected by validate().
        c = os.path.join(self.tmp, "ep, part 1.srt")
        open(c, "w").close()
        p2v.validate(self._args(subtitles=c))  # no raise

    def test_cover_without_visualize_rejected(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(cover=self.cover))

    def test_missing_cover_in_visualize(self):
        with self.assertRaises(SystemExit):
            p2v.validate(self._args(visualize=True, cover="/nope.png"))

    def test_vtt_extension_accepted_case_insensitive(self):
        vtt = os.path.join(self.tmp, "EP.VTT")
        open(vtt, "w").close()
        p2v.validate(self._args(subtitles=vtt))  # no raise


class ArgParseTests(unittest.TestCase):
    def test_repeated_prompt_accumulates(self):
        a = p2v.parse_args(["-i", "x.wav", "-p", "scene one", "-p", "scene two"])
        self.assertEqual(a.prompts, ["scene one", "scene two"])

    def test_defaults(self):
        a = p2v.parse_args(["-i", "x.wav"])
        self.assertEqual(a.aspect, "16:9")
        self.assertEqual(a.style, "showwaves")
        self.assertEqual(a.model, "veo-3.1-lite-generate-preview")
        self.assertEqual(a.clip_duration, 8)
        self.assertEqual(a.max_clips, 30)
        self.assertEqual(a.jobs, 1)
        self.assertFalse(a.visualize)
        self.assertFalse(a.overwrite)
        self.assertFalse(a.no_scene_prompts)

    def test_input_required(self):
        # argparse exits (code 2) when a required arg is missing.
        with self.assertRaises(SystemExit):
            p2v.parse_args([])


class TranscriptTextTests(unittest.TestCase):
    def _write(self, content):
        path = os.path.join(tempfile.mkdtemp(), "t.vtt")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_strips_header_timestamps_numbers_and_tags(self):
        vtt = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:02.000\n"
            "<v Paul>Hello there, welcome back.\n\n"
            "00:00:02.000 --> 00:00:04.000\n"
            "<v Elena>Great to be here!\n"
        )
        out = p2v.transcript_text(self._write(vtt))
        self.assertEqual(out, "Hello there, welcome back. Great to be here!")

    def test_handles_srt_numbering_and_comma_timestamps(self):
        srt = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "First line.\n\n"
            "2\n"
            "00:00:02,000 --> 00:00:04,000\n"
            "Second line.\n"
        )
        out = p2v.transcript_text(self._write(srt))
        self.assertEqual(out, "First line. Second line.")


class SceneWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vtt = os.path.join(self.tmp, "ep.vtt")
        with open(self.vtt, "w") as f:
            f.write("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<v A>Talking about databases.\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _proc(self, returncode=0, stdout="", stderr=""):
        m = mock.Mock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = stderr
        return m

    def test_parses_one_prompt_per_line(self):
        out = "Scene one, glowing server room.\nScene two, a calm desk at dawn.\n"
        with mock.patch("subprocess.run", return_value=self._proc(stdout=out)):
            prompts = p2v.generate_scene_prompts("5am", self.vtt, 2, "9:16")
        self.assertEqual(prompts, ["Scene one, glowing server room.", "Scene two, a calm desk at dawn."])

    def test_strips_accidental_numbering_and_bullets(self):
        out = "1. First scene.\n2) Second scene.\n- Third scene.\n"
        with mock.patch("subprocess.run", return_value=self._proc(stdout=out)):
            prompts = p2v.generate_scene_prompts("5am", self.vtt, 3, "16:9")
        self.assertEqual(prompts, ["First scene.", "Second scene.", "Third scene."])

    def test_returns_none_on_cli_failure(self):
        with mock.patch("subprocess.run", return_value=self._proc(returncode=1, stderr="boom")):
            self.assertIsNone(p2v.generate_scene_prompts("5am", self.vtt, 2, "9:16"))

    def test_returns_none_on_empty_output(self):
        with mock.patch("subprocess.run", return_value=self._proc(stdout="   \n\n")):
            self.assertIsNone(p2v.generate_scene_prompts("5am", self.vtt, 2, "9:16"))


class RetryBackoffTests(unittest.TestCase):
    """Jittered exponential backoff between clip-generation retries. The first
    attempt never waits; later attempts grow and are jittered so concurrent
    retries (under -j) don't all re-fire at the same instant."""

    def test_first_attempt_no_wait(self):
        self.assertEqual(p2v.retry_backoff_seconds(1), 0.0)
        self.assertEqual(p2v.retry_backoff_seconds(0), 0.0)

    def test_later_attempts_within_jittered_range(self):
        base = p2v.CLIP_RETRY_BACKOFF
        for attempt in (2, 3, 4):
            expected = base * (2 ** (attempt - 2))
            lo, hi = expected * 0.5, expected * 1.5
            for _ in range(50):
                w = p2v.retry_backoff_seconds(attempt)
                self.assertGreaterEqual(w, lo)
                self.assertLessEqual(w, hi)

    def test_backoff_grows_with_attempt(self):
        # Mean of attempt 3 should exceed mean of attempt 2 (exponential growth),
        # even with jitter — average a handful of samples to smooth randomness.
        def mean(attempt, n=200):
            return sum(p2v.retry_backoff_seconds(attempt) for _ in range(n)) / n
        self.assertGreater(mean(3), mean(2))

    def test_jitter_produces_distinct_values(self):
        # Two draws for the same attempt should (almost surely) differ — proves
        # the jitter is live, so concurrent retries spread out.
        vals = {p2v.retry_backoff_seconds(2) for _ in range(20)}
        self.assertGreater(len(vals), 1)


class ParallelFailFastTests(unittest.TestCase):
    """The parallel clip-generation path (run_broll, --jobs > 1) must surface a
    failure as soon as ANY clip fails — not only after the first-submitted one
    returns. That relies on as_completed; this test pins the contract so a
    regression back to `for f in futures` (which blocks in submission order)
    can't slip through. We exercise the same primitive run_broll uses rather
    than the whole closure, which would need ffmpeg + the CLI."""

    def test_as_completed_is_imported(self):
        # The fix hinges on this import existing in the module.
        self.assertTrue(hasattr(p2v, "as_completed"))

    def test_failure_surfaces_before_slow_sibling_finishes(self):
        import time
        from concurrent.futures import ThreadPoolExecutor

        def work(i):
            if i == 3:
                time.sleep(0.02)
                raise SystemExit("clip 3 failed")  # gen_clip → err() does this
            time.sleep(1.0)  # slow siblings
            return i

        # Measure detection time INSIDE the loop. This test pins only the
        # *detection* contract (as_completed surfaces the failure immediately);
        # the actual run additionally cancels in-flight children via ClipJobs so
        # the whole process exits fast (covered by ClipJobsTests below).
        start = time.time()
        detect_elapsed = None
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(work, i) for i in range(1, 5)]
            try:
                for f in p2v.as_completed(futures):
                    f.result()
            except SystemExit:
                detect_elapsed = time.time() - start
        self.assertIsNotNone(detect_elapsed, "expected the failing clip's error to propagate")
        # Detected well before the 1.0s slow siblings — proving we didn't block
        # on the first-submitted future the way `for f in futures` would.
        self.assertLess(detect_elapsed, 0.9,
                        "as_completed should surface the failure fast, not after slow siblings")


class ClipJobsTests(unittest.TestCase):
    """ClipJobs makes the parallel run *truly* fail fast: cancel() must flip the
    flag and terminate the live child subprocesses (the quota cost) so the run
    exits immediately instead of blocking on shutdown(wait=True) for minutes."""

    def test_cancel_sets_flag(self):
        jobs = p2v.ClipJobs()
        self.assertFalse(jobs.cancelled)
        jobs.cancel()
        self.assertTrue(jobs.cancelled)
        jobs.cancel()  # idempotent
        self.assertTrue(jobs.cancelled)

    def test_run_cli_tracked_skips_when_already_cancelled(self):
        # A queued clip must NOT fire a fresh (quota-burning) request once the
        # run is cancelled.
        jobs = p2v.ClipJobs()
        jobs.cancel()
        with mock.patch("subprocess.Popen") as popen:
            self.assertFalse(p2v.run_cli_tracked("5am", ["media", "x"], jobs))
            popen.assert_not_called()

    def test_cancel_terminates_live_child(self):
        # Start a real long-sleeping child via run_cli_tracked in a thread, then
        # cancel() from the main thread — the child must die and the call return
        # quickly (well under the sleep), proving the fail-fast kill works.
        import subprocess as sp
        import threading
        import time

        jobs = p2v.ClipJobs()
        result = {}

        def runner():
            # `sleep 30` stands in for a minutes-long Veo generation.
            result["ok"] = p2v.run_cli_tracked("sleep", ["30"], jobs)

        t = threading.Thread(target=runner)
        start = time.time()
        t.start()
        # Wait for the child to actually register, then cancel.
        deadline = start + 5
        while not jobs._procs and time.time() < deadline:  # noqa: SLF001
            time.sleep(0.02)
        jobs.cancel()
        t.join(timeout=10)
        elapsed = time.time() - start
        self.assertFalse(t.is_alive(), "runner thread should have exited after cancel")
        self.assertLess(elapsed, 8, "cancel() must terminate the child promptly, not wait 30s")
        self.assertFalse(result.get("ok"), "a terminated child is not a success")
        # No leftover sleep processes.
        leftover = sp.run(["pgrep", "-f", "sleep 30"], capture_output=True).stdout.decode().strip()
        self.assertEqual(leftover, "", f"sleep child should be reaped, found: {leftover}")


if __name__ == "__main__":
    unittest.main()
