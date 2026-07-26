# 5am CLI — examples & guides

Runnable examples and deployment guides for the [5am](https://5am.app/cli) command-line
tool — **Server Agents** (running the CLI on your own machines so your AI
characters can answer questions about them) and **media pipelines** (turning a
podcast episode into a shareable video).

> **You:** how many unique visitors did the portfolio get in the last 24 hours?
>
> **Your character:** 1,284 unique visitors since this time yesterday.

The data stays on your machine. The agent answers structured queries against a
local SQLite store and returns only the result — a number, a top-ten list, an
average — never your raw logs. The [announcement post][sa-post] covers the
design and the use cases; this repo is the runnable half.

[sa-post]: https://5am.app/blog/server-agents-ask-your-infrastructure

## Install the CLI

```sh
curl -fsSL https://cli.5am.app/cli/latest/install.sh | sh
5am --version
```

Then `5am login`, and mint a **read-only** token at
[5am.app/settings#keys](https://5am.app/settings#keys). Every server-agent
endpoint is designed to need nothing more than `read`, so a token left on a
server can't touch your media library.

## What's here

| Path | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | Full CLI reference written for **AI agents** — every command, its JSON shape, exit codes, and the gotchas. Drop it into your agent's skills directory. |
| [`docs/server-agent.md`](docs/server-agent.md) | The full guide: architecture, datasets, query operations, custom skills, a step-by-step Ubuntu/Debian deployment, and the security model. |
| [`examples/install-agent.sh`](examples/install-agent.sh) | Puts the agent under systemd — writes and starts the units so it survives reboots and closed SSH sessions. |
| [`examples/sysmetrics.sh`](examples/sysmetrics.sh) | Emits one CPU/memory/disk/load sample as a JSON line. Linux and macOS. |
| [`examples/sysmetrics.schema.json`](examples/sysmetrics.schema.json) | Matching schema for the sampler above. |
| [`examples/nginx-requests.schema.json`](examples/nginx-requests.schema.json) | Schema for nginx/Apache access logs (`--format combined`). |
| [`examples/podcast_to_video.py`](examples/podcast_to_video.py) | Turns a podcast audio file into a shareable MP4 — AI b-roll or an animated waveform, with optional burned-in captions. |
| [`examples/test_podcast_to_video.py`](examples/test_podcast_to_video.py) | Its test suite. Stdlib `unittest`, no API calls — run it after adapting the script. |

## Quick start: make your access log askable

On the server, with the CLI installed and logged in:

```sh
# 1. Load the access log into a dataset (re-runnable: it resumes where it left off)
5am data ingest --dataset requests \
    --schema nginx-requests.schema.json \
    --file /var/log/nginx/access.log --format combined

# 2. Check it locally — the same query engine your character will use
5am data query --dataset requests --op count_distinct --field ip --since -24h

# 3. Run the agent under systemd so it stays up
sudo AGENT_NAME=web-1 ./examples/install-agent.sh
```

Then enable the **Query Server Agent** skill on a character in the web UI and
ask away. Full detail, including the parts that are easy to get wrong, is in
[`docs/server-agent.md`](docs/server-agent.md).

## Two things worth knowing before you run an agent

**`5am serve agent` is a foreground daemon.** Start it in an SSH session and it
dies with the session — `5am agent list` will then show your agent registered
but `"online": false`. That's what `install-agent.sh` is for.

**A dataset remembers its schema.** Re-ingesting with a *different* set of
fields is refused rather than silently merged, so take all the fields you might
want up front. Adding them later means rebuilding with `--replace`.

## Podcast audio → shareable video

Platforms like YouTube, TikTok and Instagram want video, not a WAV.
[`podcast_to_video.py`](examples/podcast_to_video.py) wraps the whole pipeline in
one command. Stdlib-only Python — nothing to `pip install`, and it runs the same
on macOS, Linux and Windows.

It pairs with [Podcast Studio](https://5am.app/podcast), which generates the WAV
and a sample-accurate `.srt`/`.vtt` transcript — see
[the announcement post](https://5am.app/blog/introducing-podcast-studio) for the
full workflow.

```sh
# Animated waveform over your cover art, captions burned in — instant, no API calls
python3 examples/podcast_to_video.py -i episode.wav --visualize \
    --cover cover.jpg -s episode.srt

# AI b-roll instead: generates Veo clips to cover the audio, stitches, muxes
python3 examples/podcast_to_video.py -i episode.wav -s episode.srt -a 9:16
```

Give the b-roll mode a transcript and it asks Gemini to write one cinematic
scene per clip, in narrative order, so the visuals track what's actually being
said rather than looping generic stock footage.

Needs `ffmpeg` on PATH. The waveform mode is free and instant; the b-roll mode
uses Gemini quota and takes minutes. Run the tests with
`python3 examples/test_podcast_to_video.py` — 42 of them, no network required.

## Using the CLI from an AI agent

[`SKILL.md`](SKILL.md) is the whole CLI written up for a coding agent rather
than a person: every command with its flags, the JSON each one returns, what the
exit codes mean, and the traps worth knowing before you script against it.

It's plain markdown with a few lines of YAML frontmatter, so every assistant
can use it — the only difference is where the file goes.

Download it first:

```sh
curl -fsSLO https://raw.githubusercontent.com/digvan/5am-cli/main/SKILL.md
```

**Claude Code** — [Agent Skills](https://code.claude.com/docs/en/skills) are
loaded from a per-skill directory, and the frontmatter is what makes Claude
pick it up automatically when you mention the CLI:

```sh
mkdir -p ~/.claude/skills/5am && mv SKILL.md ~/.claude/skills/5am/SKILL.md
```

Use `.claude/skills/5am/` inside a project instead if you only want it there.

**Gemini CLI** — put it where the assistant reads project context, so it's in
scope for every session in that directory:

```sh
mkdir -p .gemini && mv SKILL.md .gemini/5am-cli.md
```

Then reference it from your `GEMINI.md` (for example: *"For any `5am` command,
follow .gemini/5am-cli.md"*), or paste it in directly.

**Codex** — same idea: keep it in the repo and point `AGENTS.md` at it.

```sh
mkdir -p docs && mv SKILL.md docs/5am-cli.md
```

**Anything else** — it is just a markdown file. Attach it, paste it, or add it
to whatever context mechanism your tool has; the frontmatter is inert if unused.

Whichever you use, the thing that makes this work is the CLI's design rather
than the document: **stdout is always JSON**, stderr carries progress, and exit
codes are specific (`2` auth, `3` validation, `4` network, `5` server), so an
agent can branch on a failure instead of scraping error text.

## Adding your own

The only contract is **one JSON object per line**, with types matching a schema
you write once. Anything that can print that is a dataset: a nightly `find`
inventory of an archive, a backup script's log, an offload station's per-file
records, `journalctl -o json`. See the "any script → dataset" section of the
guide.

## Links

- [5am.app](https://5am.app) · [CLI docs](https://5am.app/cli/docs) · [Blog](https://5am.app/blog)

## License

Apache 2.0 — see [LICENSE](LICENSE).
