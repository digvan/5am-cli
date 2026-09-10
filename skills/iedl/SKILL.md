---
name: iedl
description: Generate and validate IEDL recipes for editable image adjustments, versioned presets, local image analysis, masks, retouching, and prompt-guided masked AI edits through the 5am image-edit runtime. Use when directly authoring image-edit recipes; workflows delegate generation to the CLI.
---

# IEDL image editing

Create `.iedl` recipes that compile to the existing image editor. Read the
[IEDL 1 language contract](references/IMAGE_EDIT_DSL.md) before writing commands;
it contains exact fields, ranges, units, preset identifiers and CLI behavior.
Use that contract rather than illustrative syntax from older planning documents.
The caller supplies the creative brief, inputs, output requirements and runtime
availability. An installed `5am` binary alone does not imply rendering is available.

## Generate an edit

- Begin with `iedl 1` and `input image`. One operation per line. Use JSON double
  quotes for prompts/text; `#` comments are outside quoted strings and JSON.
- Declare typed parameters with useful defaults for reusable choices. References
  are `$name`, not JavaScript expressions. Declare masks/assets/layers before use;
  IDs are unique. No loops, arbitrary code, file reads or URLs inside IEDL.
- Coordinates refer to the EXIF-oriented original. Use `%w` horizontally, `%h`
  vertically, `%s` for scalar brush/feather sizes, or explicit `px`. Relative
  geometry does not locate a face or blemish in unrelated photographs.
- Prefer moderate, editable changes. Versioned presets use `apply name@1`, not
  invented functions such as `skinSmooth()`. Consult the catalog for required
  masks and default strengths. Presets are experimental looks, not universal
  corrections. Keep exposure/white balance separate from the creative look.
- Named local `analyze` findings can drive exposure, white balance, vibrance and
  experimental Smart baseline. Prefer explicit local masks for subject/background
  corrections. `analyze ID image input=original mask=MASK` meters that region; its
  auto consumer must use the same `mask`. Baseline requires named image analysis.
  `input=original` ignores edits; `input=current` measures preceding edits.
  Findings are immutable. Reusing an exposure correction twice adds two layers.
  Appearance labels are not semantic categories or occasion detection.
- Choose remote selection/generation when the user's requested edit calls for it.
  Do not add paid AI operations merely to reproduce a local color preset. Use an
  explicit existing mask for generative editing. Never guess a cloning source or
  promise semantic portability for a painted repair.
- Return recipe text when directly asked for a recipe. Workflow Python must instead
  invoke `5am media image-edit generate --brief ... -o recipe.iedl`, then validate
  and render through subprocess argument lists. An explicitly supplied approved
  recipe can instead be copied verbatim from its attachment and validated/rendered;
  do not regenerate it without a request to change the look. Do not embed this language spec,
  author IEDL in workflow Python, or call model/browser APIs directly.

## Local analysis and a creative look

```iedl
iedl 1
input image
param strength number default=0.5 min=0 max=1
analyze scene image input=original
auto exposure id=lighting analysis=scene
auto vibrance id=color analysis=scene
apply family-natural@1 strength=$strength id=look
output format=jpeg quality=0.92
```

White balance can consume `analysis=scene` too, but fails when neutral samples are
insufficient. Do not hide that failure or replace a user's correction silently.
Manual masks can be measured with `analyze shape mask mask=region`; those findings
provide coverage/geometry, not subject detection or image auto adjustments.

## Masked AI modification

```iedl
iedl 1
input image
param instruction string default="Create a soft sunset matching the existing lighting."
select sky sky
refine sky feather=3px
generative-edit id=sunset mask=sky prompt=$instruction
output format=png
```

`generative-edit` requires a new layer `id`, an existing `mask`, and a nonblank
`prompt` of at most 4000 characters. Any supported mask kind can be referenced.
`erase MASK id=cleanup` instead uses the backend's default removal prompt.
Both preserve generated pixels as masked raster layers. Prompt-guided generation
is remote; local analysis is not. Remote operations require a library media ID
bound to the matching source and the existing authenticated access/credits flow.
Never put tokens, endpoint URLs or model credentials in a recipe. Each explicit
execution may incur a new request; do not retry an ambiguous generation failure.

## Validate, render and preserve evidence

With a provisioned IEDL runtime:

```sh
5am media image-edit validate recipe.iedl
5am media image-edit inspect recipe.iedl --input input.jpg
5am media image-edit render recipe.iedl --input input.jpg -o edited.jpg --resolved edited.iedl-resolved.json --bundle edited.iedl.zip
```

For remote edits, use `--media-id` with the actual library ID **instead of**
`--input`; the CLI downloads the matching library original. Bind imported assets
with repeated `--asset name=path`, and parameters with `--param name=value`.
`inspect` binds/decodes and reports unresolved operations; it does not generate
masks or execute local analysis. Validate before invoking paid services. Repair
invalid generated syntax using diagnostics, then validate again. Do not silently
change the user's intended edit to bypass an error.

Inspect the rendered image and masks at useful resolution before claiming visual
quality. Record source/asset hashes and resolved values through the standard report
and bundle. Bundle replay uses stored generated assets rather than another model
call. Reusable recipes recalculate dynamic operations for each new input. Use the
normal CLI upload/artifact commands only for the outputs requested by the workflow;
rendering itself writes local files. Do not overwrite the source.

## Runtime availability

Validation needs Node (20 or newer) and the packaged core/runner. Rendering and
input-bound inspection also need Chromium and the package's `puppeteer-core`
dependency. The complete bundle includes worker, WASM kernels, runtime, core,
runner, browser-discovery helper, package manifest and hash manifest. `IEDL_RUNTIME` locates `runner.mjs`;
`CHROME_PATH` locates Chromium. Use the caller's installed runtime; do not install
browsers/dependencies or fetch arbitrary runtime bundles during a managed run.

Managed workflows must advertise this capability explicitly. If absent, explain the missing rendering capability; direct recipe authoring may
still return text, but do not produce a workflow
that claims it can execute the edit. Batch concurrency must respect memory limits;
start serially for large originals and never derive concurrency from CPU count
alone. The 512-pixel analysis preview does not bound full-image decode/render cost.
