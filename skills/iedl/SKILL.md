---
name: iedl
description: Generate and validate IEDL recipes for editable image adjustments, versioned presets, local image analysis, masks, retouching, and prompt-guided masked AI edits through the 5am image-edit runtime. Use when directly authoring image-edit recipes; workflows delegate generation to the CLI.
---

# IEDL image editing

Create editable `.iedl` recipes using the common patterns below. Consult the
[IEDL 1 language contract](references/IMAGE_EDIT_DSL.md) for operations not shown,
exact ranges, the full preset catalog, retouch/liquify, and bundle semantics.
Do not infer syntax from illustrative plans. The caller supplies the brief,
inputs, output requirements and runtime availability; a `5am` binary alone does
not imply rendering is available.

## Minimal local recipe

For a modest warm edit with a portrait crop, use a named adjustment layer:

```iedl
iedl 1
input image
param warmth number default=6 min=-100 max=100
layer tone adjustment
adjust tone temperature=$warmth contrast=5 highlights=-10
curve tone rgb points=[{"x":0,"y":0},{"x":0.5,"y":0.52},{"x":1,"y":1}]
hsl tone orange saturation=-3 luminance=2
crop aspect=4:5 anchor=center
output format=jpeg quality=0.92
```

Keep crop and color choices tied to the brief; this example is not a default for
every photo. `adjust` updates the named layer; `curve` channels are `rgb/r/g/b`.
HSL bands are `red/orange/yellow/green/aqua/blue/purple/magenta`. Curve points are
normalized JSON objects, not tuple notation. Exposure is in EV; temperature/tint
are editor controls, not Kelvin. Output supports `jpeg`, `png`, and `webp`.

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

Automatic white balance in runtime 1.1 uses conservative confidence checks; mixed
or strong casts can intentionally produce zero correction, with a reason in
analysis findings. Confirm runtime availability before promising that behavior.
White balance can consume `analysis=scene` too, but fails when neutral samples are
insufficient. Do not hide that failure or replace a user's correction silently.
Manual masks can be measured with `analyze shape mask mask=region`; those findings
provide coverage/geometry, not subject detection or image auto adjustments.

## Choose a preset

Use `apply PRESET@1 strength=0.5 id=look` for a global look, or add
`mask=EXISTING_MASK` to restrict it. Strength is 0–1; choose it explicitly when
comparing looks. Consult the reference catalog for defaults and exact effects.

| Intent | Examples | Required mask |
| --- | --- | --- |
| Natural portraits/families | `family-natural@1`, `editorial-portrait@1` | None |
| Weddings/soft color | `wedding-clean@1`, `wedding-airy@1`, `soft-pastel@1` | None |
| Monochrome | `bw-classic@1`, `bw-high-contrast@1`, `bw-matte@1` | None; strength 1 is fully monochrome |
| Stylized color | `teal-orange@1`, `cinematic@1`, `dark-moody@1` | None |
| Subject emphasis | `subject-pop@1` | Explicit subject mask |
| Skin smoothing | `skin-smooth@1` | Explicit skin mask |
| Milky Way detail | `milky-way-definition@1` | Explicit sky mask |

Presets do not create selections. `select skin skin` creates an experimental
remote skin selection; `apply skin-smooth@1 mask=skin strength=0.4 id=smooth`
uses that existing mask. Inspect eyes, teeth, hair, clothing and edges before
accepting smoothing; neither the preset name nor the selection guarantees a
perfect mask. Astro presets need an appropriate image, not just a dark region.

## Local masks and metering

For a user-specified region, use geometric components and feathering. This box is
an example region, not a detected person:

```iedl
iedl 1
input image
mask region
component region box rectangle points=[{"x":"25%w","y":"25%h"},{"x":"75%w","y":"75%h"}]
refine region feather=1%s
analyze meter image input=original mask=region
auto baseline id=base analysis=meter mask=region
layer color adjustment mask=region
adjust color temperature=3
output format=jpeg quality=0.92
```

Use `layer ... mask=region` for local adjustments and `refine region` to change an
existing mask. Component composition uses `operation=add|subtract|intersect`.
Read the reference for shape-specific points and brush fields. For semantic
regions use `select ID subject|background|sky|skin` (remote); object selection
requires `select ID object x=... y=...` with a user-appropriate point.

Imported masks require both a recipe declaration and an explicit file binding:

```iedl
iedl 1
input image
asset supplied
mask region
component region imported raster asset=supplied
layer local adjustment mask=region
adjust local exposure=0.2
output format=jpeg quality=0.92
```

Render that recipe with `--asset supplied=/path/to/mask.png`. Review its alignment
against the original. The mask name alone never loads a file or calls segmentation.

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

For CLI-generated recipes, generate first; for a directly authored or approved
recipe, start with validation. With a provisioned runtime:

```sh
5am media image-edit generate --brief "Warm portrait, gentle contrast, 4:5 crop. Local edits only." -o recipe.iedl
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

## Common authoring errors

- Do not declare a layer before `auto ... id=LAYER` or `apply ... id=LAYER`;
  those operations create it. Likewise, `select MASK ...` creates its mask:
  do not precede it with `mask MASK`. IDs are globally unique and cannot be reused
  after deletion; use `set`, `adjust` or `refine` to update existing objects.
- Use `$warmth` as a complete typed value, not inside a string expression. A number
  parameter needs a numeric default, not a quoted number. Bind missing defaults
  explicitly with `--param name=value`.
- Do not invent `skinSmooth()`, `preset ...`, automatic face coordinates or shell
  commands inside IEDL. Reject unknown fields rather than silently dropping them.
- Statements update document state in order, but each layer has a fixed filter
  pipeline. Use separate layers for sequential effects. New analysis is needed to
  measure after a correction; old findings do not automatically refresh.
- Relative masks transfer geometry, not meaning. A resolved bundle binds one
  source and recorded assets; it is not a reusable semantic recipe.

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

Runtime 1.1 changes temperature/tint rendering to shadow-preserving linear-light
RGB gains, with `local-image-v2` analysis. Manual settings and presets can look
different from 1.0. A 1.0 resolved artifact must be replayed with its original
runtime; 1.1 rejects it. Language `iedl 1` and runtime versions are independent.
Check the installed runtime and release availability; public preview images do
not prove that the user's runtime has been upgraded.
