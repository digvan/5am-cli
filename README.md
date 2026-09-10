# 5am CLI — recipes, examples & guides

Use the [5AM CLI](https://5am.app/cli) to manage media, edit images, create video/audio pipelines, and automate work through AI agents and managed workflows. This repository contains public documentation, agent skills, and runnable examples; it is not the CLI source distribution.

**New: [IEDL visual field guide](examples/image-edit/README.md)** — 113 examples using one concert photograph: before/after comparisons, 20 presets, mask previews, and downloadable recipes. Clone the repo and open [`examples/image-edit/index.html`](examples/image-edit/index.html) in a browser; GitHub itself shows HTML source.

![A concert photograph edited through IEDL](examples/image-edit/images/stage-balance.jpg)

## Install and update

macOS and Linux:

```sh
curl -fsSL https://cli.5am.app/cli/latest/install.sh | sh
5am --version
5am update --check
5am update
```

Windows PowerShell:

```powershell
Invoke-WebRequest https://cli.5am.app/cli/latest/5am-windows-amd64.exe -OutFile 5am.exe
.\5am.exe --version
```

Release checksums and metadata are available in the [release manifest](https://cli.5am.app/cli/latest/manifest.json). Core CLI installation needs no Node.js, Chromium, or image-edit runtime. Individual media tools have their own dependencies, such as FFmpeg for video.

For library access, create a personal access token in [Settings → CLI Access Tokens](https://5am.app/settings#keys), then run:

```sh
5am login
5am whoami
```

Choose scopes for the work: server-agent queries can use `read`; library writes and AI-credit proxy access require `write`. Local image validation and local-only rendering do not require login. Gemini features use the normal access resolver: AI credits through the metered proxy, or the user's own Gemini key where configured. Proxy refusals are not a reason to bypass account limits.

## Image editing: generate → validate → render

Image editing is optional. Install Node.js 20+ and Chrome/Chromium separately, then install the runtime matched to your CLI release:

```sh
5am update --runtime-only
5am media image-edit generate \
  --brief "Warm portrait, gentle contrast, 4:5 crop. Local adjustments only; no AI selections or generative edits." \
  -o portrait.iedl
5am media image-edit validate portrait.iedl
5am media image-edit render portrait.iedl --input photo.jpg \
  -o edited.jpg --resolved edited.iedl-resolved.json --bundle edited.iedl.zip
```

`generate` uses model quota. Go handles the Gemini request and credentials; the shared JS runtime prepares the prompt/schema and validates/prints the recipe. `generate` and `validate` need Node and the runtime, but no browser. Rendering and input-bound `inspect` need Chromium. Runtime installation downloads neither Node nor Chrome. Normal updates keep an opted-in managed runtime synchronized with the CLI.

To edit entirely locally, start from one of the checked-in recipes:

```sh
cd examples/image-edit
5am media image-edit render recipes/stage-balance.iedl --input source.jpg \
  -o concert.jpg --bundle concert.iedl.zip
5am media image-edit render concert.iedl.zip --input source.jpg -o replay.jpg
```

IEDL supports adjustments, curves/HSL, masks, editable layers, retouching, liquify, presets, local analysis, and smart baseline edits. See the [language reference](docs/iedl.md), [visual gallery guide](examples/image-edit/README.md), and [focused authoring skill](skills/iedl/SKILL.md).

- Use `--runtime`/`IEDL_RUNTIME`, `--node`, or `--browser`/`CHROME_PATH` for explicit paths.
- Reusable recipes resolve edits for each input. Resolved bundles preserve one result and require its matching source.
- Hand-drawn masks transfer geometry, not subject recognition. Review them on every new photograph.
- AI selections and masked generative edits use `--media-id` instead of `--input`, with authenticated backend access. They may incur credits. Do not automatically repeat an ambiguous paid edit.
- Rendering writes local files. Uploading them is a separate operation. Existing output files require `--overwrite`.

Directory batches are serial and nonrecursive, accept PNG/JPEG/WebP, save resolved sidecars, and report per-image failures:

```sh
5am media image-edit batch portrait.iedl --input-dir photos --output-dir edited --report batch.json
```

Use local-only recipes for directory batches. `--media-id` is not supported by `batch`. Inspect the report before publishing results; the command exits nonzero if any image fails.

## Make your own visual gallery

The Apache 2.0 gallery builder accepts your own photo and creates a standalone HTML gallery with local renders and editable recipes:

```sh
python3 examples/image-edit/build_gallery.py \
  --input "/path/to/photo.jpg" --output-dir /tmp/my-iedl-gallery
```

Open `/tmp/my-iedl-gallery/index.html`. See the [builder guide](examples/image-edit/README.md#build-a-gallery-with-your-own-image) for setup, preview size, selective rendering, and adapting the sample masks.

## What's here

| Path | Purpose |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Current CLI command guidance for agents and workflow generation. |
| [`skills/iedl/SKILL.md`](skills/iedl/SKILL.md) | Focused IEDL authoring instructions, with the portable language specification. |
| [`docs/iedl.md`](docs/iedl.md) | IEDL grammar, capabilities, presets, coordinate semantics, and runtime contract. |
| [`examples/image-edit/`](examples/image-edit/README.md) | Interactive HTML field guide, sample image, 113 recipes, real renders, masks, reports, and rebuild script. |
| [`docs/server-agent.md`](docs/server-agent.md) | Server-agent architecture, datasets, query operations, systemd deployment, and security. |
| [`examples/install-agent.sh`](examples/install-agent.sh) | Install a persistent server agent under systemd. |
| [`examples/sysmetrics.sh`](examples/sysmetrics.sh) | Linux/macOS CPU, memory, and disk samples as JSON lines. |
| [`examples/sysmetrics.schema.json`](examples/sysmetrics.schema.json) | Schema for the system metrics sampler. |
| [`examples/nginx-requests.schema.json`](examples/nginx-requests.schema.json) | Schema for nginx/Apache access logs. |
| [`examples/podcast_to_video.py`](examples/podcast_to_video.py) | Podcast audio → MP4 using a waveform or AI b-roll, with optional captions. |
| [`examples/test_podcast_to_video.py`](examples/test_podcast_to_video.py) | Offline tests for the podcast example. |

## AI agents and managed workflows

Use [`SKILL.md`](SKILL.md) to teach an agent how to invoke `5am`. Download the current release copy with:

```sh
curl -fsSL https://cli.5am.app/cli/latest/SKILL.md -o SKILL.md
```

For direct IEDL authoring, provide the entire [`skills/iedl/`](skills/iedl/SKILL.md) directory, including `references/`; the entrypoint alone is not the full specification. Add it through your agent's supported skill mechanism, or reference it from project instructions.

**Workflow Python should delegate recipe creation to `5am media image-edit generate --brief …`.** It then validates and renders through subprocess argument lists, checking each exit status. It does not need the full IEDL spec. When a user supplies an approved recipe, preserve it unchanged rather than generating a replacement.

Managed runs need an explicitly provisioned image-edit runner. Machine size alone does not install Node, Chromium, or the runtime. Missing capabilities should produce diagnostics, not dependency installation or a substitute rendering engine during the run.

Most CLI commands return JSON on stdout; progress and errors use stderr. Some commands, such as `--version`, help, and default character chat, return text. Check the individual command contract in the skill rather than treating every stdout stream as JSON.

## Server agents: make logs askable

Server agents answer structured queries over data stored locally; they return results instead of uploading raw logs. Use a read-scoped token for this role.

From this repository's root, on your server:

```sh
5am data ingest --dataset requests \
  --schema examples/nginx-requests.schema.json \
  --file /var/log/nginx/access.log --format combined
5am data query --dataset requests --op count_distinct --field ip --since -24h
sudo AGENT_NAME=web-1 ./examples/install-agent.sh
```

Enable **Query Server Agent** on your character in the web UI, then ask about the data. [`docs/server-agent.md`](docs/server-agent.md) covers deployment and custom datasets.

`5am serve agent` is a foreground daemon; use systemd for persistence. Datasets retain their schemas. Changing fields requires an explicit rebuild with `--replace`, not a silent schema merge.

## Podcast audio → shareable video

The Python example is standard-library-only and requires FFmpeg. Its b-roll mode also needs Gemini access:

```sh
# Animated waveform and captions; no AI generation.
python3 examples/podcast_to_video.py -i episode.wav --visualize \
  --cover cover.jpg -s episode.srt

# AI b-roll; uses model quota.
python3 examples/podcast_to_video.py -i episode.wav -s episode.srt -a 9:16

python3 examples/test_podcast_to_video.py
```

See [Podcast Studio](https://5am.app/podcast) and the [public CLI docs](https://5am.app/cli/docs) for related workflows, video clips/highlights, VEDL, and audio tools.

## License

Code and documentation: Apache 2.0; see [LICENSE](LICENSE). The supplied photograph has separate rights; see [photo provenance](examples/image-edit/README.md#photo-and-license).
