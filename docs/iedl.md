# Image Edit DSL (IEDL 1)

IEDL constructs the same editable document used by the web image editor. The
TypeScript core lives in `Web-Frontend/lib/image-editor/iedl`; the Go CLI invokes
its packaged Node/Chromium runner. Filters are never translated into Go or FFmpeg.

## Quick start

```iedl
iedl 1
input image
param warmth number default=6
auto white-balance id=balance
auto exposure id=lighting
mask portrait
component portrait oval ellipse points=[{"x":"20%w","y":"10%h"},{"x":"80%w","y":"90%h"}]
refine portrait feather=3px density=0.9
layer tone adjustment mask=portrait
adjust tone exposure=0.2 temperature=$warmth shadows=12
curve tone rgb points=[{"x":0,"y":0},{"x":0.5,"y":0.54},{"x":1,"y":1}]
hsl tone orange saturation=-5 luminance=3
crop aspect=4:5 anchor=center
output format=jpeg quality=0.92
```

```sh
5am media image-edit validate portrait.iedl
5am media image-edit inspect portrait.iedl --input photo.jpg
5am media image-edit render portrait.iedl --input photo.jpg -o edited.jpg \
  --param warmth=8 --resolved edited.iedl-resolved.json --bundle edited.iedl.zip
5am media image-edit render edited.iedl.zip --input photo.jpg -o replay.jpg
5am media image-edit batch portrait.iedl --input-dir photos --output-dir edited --report batch.json
5am media image-edit generate --brief "Warm portrait, gentle contrast, 4:5 crop" -o portrait.iedl
```

The editor's **IEDL** button opens import, preview, apply, and resolved export.
Preview starts from the original. Apply replaces the document with one undoable
action. A stale preview must be regenerated. Imported asset IDs are remapped so
undo/redo keeps its own immutable asset bytes. Downloads remain local; Save copy
and library uploads keep their existing behavior.

## Grammar and values

```text
recipe     = "iedl 1" newline { statement newline }
statement  = command { positional-name } { field "=" value } [ comment ]
value      = JSON-value | bare-string
dimension  = finite-decimal ("px" | "%w" | "%h" | "%s")
reference  = "$" parameter-name
```

One statement per line. Commands are case-insensitive; names and fields are
case-sensitive. Identifiers begin with an ASCII letter, followed by letters,
digits, `_` or `-`, up to 128 characters. Declarations must precede references.
Identifiers are unique across layers, masks, assets, components and strokes and
cannot be reused after deletion. `none` detaches a layer mask/freeze reference.

Double-quoted strings use JSON escaping. `#` starts a comment outside strings
and JSON when preceded by whitespace or at the beginning of a line. Thus
`color=#ffee00` is a value. Nested arrays/objects use JSON; spatial strings inside
them must be quoted. Curve points use unitless normalized numbers. Spatial points
use objects `{ "x": "10%w", "y": "20%h", "pressure": 0.5 }`.

Parameters: `param NAME TYPE [default=VALUE] [min=N max=N] [values=[...]]`.
Types are `number`, `boolean`, `string`, `dimension`, and `enum`; enums require a
nonempty string `values` array. Only numbers accept min/max. Missing defaults
require runner bindings. CLI `--param name=value` parses JSON values, otherwise
treating the value as a string. Substitution replaces complete typed values,
including values nested inside JSON. There is no string interpolation or code.

`.iedl.json` is `{ "version": 1, "operations": [{ "op": "input",
"args": ["image"], "fields": {} }] }`. Every operation uses the same model and
validation as text. `jsonSchema()` exports the registry-derived structural
schema; binding adds semantic checks. Canonical printing sorts fields and does
not retain comments or whitespace. Invalid input is rejected, never repaired.

Diagnostics include a stable code, line, column, operation and suggestion; JSON
operations may carry source locations. Codes distinguish invalid input,
unsupported capability/version, missing bindings, source mismatch and limits.

## Capability reference

The exported `registry` is authoritative for field types and numerical ranges.
Unknown fields fail rather than being ignored. Omitted fields use the existing
document defaults: zero adjustments, identity curves, neutral HSL, enabled layers,
normal blend/opacity 1; empty masks have density 1 and no refinement.

| Command / arguments | Fields / behavior | Document mapping |
|---|---|---|
| `input image` | Exactly once | Source binding |
| `asset ID` | Explicit `--asset ID=path`, or bound browser file | `assets` |
| `layer ID KIND` | `name enabled opacity blend mask freeze asset text color fontSize x y width height rotation frequencyRadius frequencyLow frequencyHigh` | New layer appended above existing layers |
| `set LAYER` | Same fields as layer | Replace specified properties |
| `adjust LAYER` | `exposure contrast highlights shadows whites blacks temperature tint saturation vibrance texture clarity dehaze sharpening denoise colorNoise` | `adjustments` |
| `curve LAYER CHANNEL` | `points`; channel rgb/r/g/b; increasing x from 0 to 1 | `curves` |
| `hsl LAYER BAND` | `hue saturation luminance`, each −100…100 | Eight HSL entries |
| `mask ID` / `refine ID` | `name enabled inverted density feather expand contrast smooth refine` | Create/update mask |
| `component MASK ID KIND` | `operation points brush range color tolerance asset edgeAware` | Append ordered mask component |
| `stroke LAYER ID KIND` | `points source brush sourceRevision` | Append ordered stroke |
| `duplicate layer\|mask SOURCE ID` | Copy layer or mask; layer keeps shared mask/asset references | Deep copy with fresh component/stroke IDs |
| `delete layer\|mask\|asset ID` | Reject deletion of referenced masks/assets | Remove document entry |
| `order LAYER` | Exactly one of `before=ID`, `after=ID` | Layer order |
| `crop` | `x y width height`, or `aspect=W:H anchor=center` | Reversible crop |
| `rotate` | `degrees=0\|90\|180\|270` replaces presentation rotation | `rotation` |
| `flip` | `x=true\|false y=true\|false` replaces flags | `flipX`, `flipY` |
| `analyze NAME image\|mask` | Image: `input=current\|original`, optional `mask=NAME` with original input; mask: required `mask=NAME`, original only | Named local findings, immutable snapshot, execution report |
| `auto exposure\|white-balance\|vibrance\|baseline` | Required layer `id`; optional earlier image `analysis=NAME` (required for vibrance/baseline); optional matching `mask=NAME` | Worker analysis or reuse named findings, concrete adjustments |
| `wand MASK` | Required `x y tolerance` | Original-image contiguous selection → raster mask |
| `select MASK subject\|background\|sky\|object\|skin` | Object requires `x y`; experimental skin forbids coordinates | Remote original-image segmentation → raster mask |
| `erase MASK` | Required `id` for raster layer | Existing Magic Eraser integration |
| `generative-edit` | Required `id`, `mask`, `prompt` (1–4000 characters, nonblank) | Prompt-guided masked edit through the existing Magic Eraser backend |
| `output` | `format=jpeg\|png\|webp quality=0.1…1` | Export request |

Layer kinds: adjustment, retouch, raster, text, frequency. Blend modes: normal,
multiply, screen, overlay, soft-light, luminosity. HSL bands: red, orange, yellow,
green, aqua, blue, purple, magenta.

Mask kinds: brush, linear, radial, rectangle, ellipse, lasso, polygon, color,
luminance, raster. Components use add/subtract/intersect. The first component
establishes coverage regardless of its stored operation. Subsequent coverage
uses max(a,b), a×(1−b), or a×b respectively. Bypassing a mask (`enabled=false`)
applies the layer everywhere. Raster masks must match original dimensions.
Edge-aware brushes require their explicitly sampled RGB `color` and tolerance.

Stroke kinds: clone, heal, spot, patch, dodge, burn, red-eye, liquify,
liquify-smooth, reconstruct. Clone/heal/patch require a `source` point; patch
also requires a layer mask. Brushes expose `size hardness opacity flow spacing
pressure smoothing`. Pressure is 0…1. Defaults match `defaultBrush`; spacing is
0.01…1. Scalar dimensions include brush size, feather, expansion, font size and
frequency radius. Frequency controls remain strengths on a single layer.

## Coordinates and execution

The original is decoded with EXIF orientation before binding. Coordinates are
continuous original pixels, top-left origin. Horizontal dimensions accept px or
%w; vertical dimensions px or %h; scalar sizes px or %s (percentage of the
original's shorter side). Fractional geometry is preserved until worker rounding.
Crop rectangles must be inside the original and at least one pixel in each axis.
Stroke/source coordinates retain the worker's existing edge sampling behavior.

Aspect crop fits the largest requested ratio inside the current crop, accounting
for presentation rotation at that statement. Anchors are in original-image axes:
center, top/bottom/left/right and hyphenated corner combinations. Rotation and
flips do not rewrite masks/strokes. Mask PNG export is always original-space.

Statements build state in order. Repeated field assignment replaces a value.
Within each layer the worker still applies its fixed rendering pipeline, so
statement order is not an arbitrary filter graph. Use separate layers for
sequential effects. Clone/heal always sample the original at render resolution;
`sourceRevision` is provenance, not a historical sampling selector.

Auto operations without `analysis` analyze immutable preceding snapshots, using the rendered crop
with `maxSize=512` and the existing power-of-two preview scale. The result is
appended as a named, unmasked adjustment layer. A zero correction is reported as
`noop`; the named identity layer remains available for subsequent assignments.
Analysis failures stop the transaction. Later edits do not recompute prior autos.

### Reusable local analysis

```iedl
iedl 1
input image
analyze scene image input=original
auto exposure id=lighting analysis=scene
auto vibrance id=color analysis=scene
apply family-natural@1 strength=0.5 id=look
analyze result image input=current
output format=jpeg quality=0.92
```

`analyze` records findings without changing the document. Image analysis defaults
to `input=current`: the preceding composite including crop, rotation and flips.
`input=original` measures the EXIF-oriented original without edits or presentation
transforms. Named findings are immutable and must precede consumers; multiple
adjustments can use the same snapshot without another scan. White balance supports
`auto white-balance id=balance analysis=scene`. To measure after a correction, declare
a new analysis. Applying the same exposure recommendation twice adds two layers;
the runner does not infer the author's intent or silently recompute it.

The `local-image-v1` profile provides:

| Findings | Definition |
| --- | --- |
| Light | Linear Rec.709 luminance mean, 5th/50th/95th percentiles, percentile spread, 98th-percentile maximum channel, shadow/highlight clipping fractions |
| Color | Mean encoded RGB, mean HSV saturation, neutral-candidate fraction, twelve 30° hue-bin fractions starting at red |
| Appearance | Descriptive brightness, contrast and saturation labels; no semantic occasion/subject classification |
| Recommendations | Exposure within ±2 stops, temperature/tint within ±100, vibrance within ±12 |

Pixels with alpha below 128 are excluded. Luminance/max-channel percentiles use
1024 fixed bins. Shadow clipping means all encoded channels ≤2; highlight clipping
means any channel ≥253. Hue fractions exclude saturation <0.1 or maximum channel
<0.05 and normalize over remaining chromatic pixels. Neutral candidates have minimum
channel ≥0.06, maximum ≤0.94 and saturation ≤0.4; white balance requires at least
eight total weighted samples, with weight `(1-saturation)^2`.

Exposure targets median linear luminance 0.18, limits brightening against the
98th-percentile maximum channel, and rounds to 0.05 stops. Vibrance nudges mean
saturation toward 0.3 with a small bounded correction. These are preview heuristics,
not RAW metering or universal creative decisions. Empty/all-black samples omit
exposure and vibrance suggestions; insufficient neutral samples omit white balance.
Requested exposure/white-balance/vibrance operations fail explicitly if their
recommendation is unavailable. Smart baseline instead records a no-op when it
cannot safely suggest changes.
Legacy autos without a named analysis retain their existing algorithm.

An existing mask can also be measured locally:

```iedl
iedl 1
input image
mask region
component region box rectangle points=[{"x":"25%w","y":"25%h"},{"x":"75%w","y":"75%h"}]
analyze shape mask mask=region
```

Mask analysis always uses original coordinates and measures the rendered mask,
including refinement. It returns soft coverage, a weighted centroid, and a bounding
box at 50% coverage, normalized to [0,1]. Empty centroids/bounds are null. It does
not detect people or count subjects. Imported, geometric and existing AI masks
work; creating an AI mask still uses the explicitly requested authenticated service.
Mask findings cannot drive image auto adjustments.

The shared worker scans a preview no larger than 512×512 once, using fixed-size
histograms and a linear-RGB lookup table. Whole-image and mask-geometry requests return small typed findings. Masked image
metering reads matching bounded image/mask bitmaps in the shared browser runtime,
excludes image pixels below 50% effective mask coverage, then scans them locally.
Each analysis report entry is limited to 16 KiB. Analysis needs no network, model
download or Python deployment. The existing local Chromium CLI runtime uses the
same implementation. Source decoding and rendering preceding edits still have
their normal image/document costs; the 512 limit bounds the analysis scan/readback.

A 16-entry LRU caches findings by source hash, snapshot document, referenced asset
hashes, analysis profile and renderer environment. The lab shares it across recipe
runs and clears it on disposal. Findings, provenance, cache status and concrete auto
values persist in execution reports, saved experiments, collection reviews and
resolved bundles. Replay uses recorded edits without recomputing findings. Changes
to the analysis algorithm require a new profile identifier.

The lab's **Analyze & Auto Tone** starter displays these findings and includes them
in downloaded observations. Typed results are exported from the shared library for
future adaptive functions. IEDL currently exposes them through the three `auto`
consumers above; arbitrary field expressions, conditional presets and semantic
classification are not implemented. Collection scope tags remain human-authored.

Wand and AI selections sample the original. Magic Eraser receives the preceding
composite at full original dimensions with presentation transforms reset, and its
original-space mask; its result becomes a masked raster layer. Freeze masks retain
the worker's current compositing semantics.

## Resolved edits, assets and replay

`.iedl-resolved.json` contains `kind`, language `version`, `runtime`, `source`,
`document`, `assets`, `output`, `report` and `environment`. Source and asset
identities use SHA-256; dimensions are oriented decoded dimensions. The document
schema remains independently versioned. Replay rejects different source bytes,
dimensions, missing assets, invalid fields and unsupported runtime versions.

Generated selections and adjustments are materialized; replay does not call AI
or run auto analysis. Editor export does not infer a subject, blemish or clean
clone source from painted geometry. `documentRecipe()` explicitly converts literal
document geometry into an authoring recipe for callers that want that operation.

`.iedl.zip` is a ZIP STORE archive containing `manifest.json` and
`assets/SHA256` bytes. Exported bundles omit the original, which must be bound
explicitly on import. Only this unencrypted, uncompressed bundle format is
accepted; ZIP64, compressed entries, unsafe paths, duplicates, CRC/hash failures
and oversized inputs fail. Temporary remote URLs are never durable asset identity.

Environment reports include browser, rendering backend, runtime and packaged
worker/WASM hashes. Text currently uses system sans-serif. The same runtime on
different operating systems, GPUs or codecs can produce different pixels. Replay
preserves edit intent and inputs; it does not promise universal byte identity.

## Runtime, security and CLI behavior

Build with `cd Web-Frontend && npm run build:image-editor`. The worker, WASM,
`runtime.js`, `core.mjs`, `runner.mjs` and `manifest.json` are one release unit.
The runtime needs Node.js 20+; rendering and input-bound inspection also need
`puppeteer-core` and installed Chrome. Install the matching optional runtime with
`5am update --runtime-only`; ordinary CLI usage needs none of these dependencies.
`--runtime` or `IEDL_RUNTIME` selects an explicitly managed runner; otherwise the
CLI discovers the versioned installed runtime, legacy adjacent runtime, or source
checkout. Chrome remains an explicit system dependency. No Next.js server is required.

Recipe generation uses two credential-free runtime actions (`generate-prepare`
and `generate-finish`, generation protocol 1). Shared JS owns the prompt, schema,
response decoding, validation and printing. Go sends the Interactions HTTP request
using the normal proxy/BYOK resolver and token-only retry wrapper. No Gemini SDK
is packaged in the image runtime. One two-minute deadline covers preparation,
access resolution, HTTP/retry and validation; responses are bounded to 1 MB.
The subprocess receives an allowlist of OS/browser environment settings, excluding
provider/CLI credentials and Node injection flags. This is not an OS sandbox:
explicit runtime executables and local filesystem access remain trusted.
Update the CLI and runtime together; an incompatible prepare action fails before
any model request. The website continues using the same language/compiler code.
`--browser` or `CHROME_PATH` selects Chrome. No browser is silently downloaded.

Validation of text/resolved JSON needs no browser, login or network. Inspect
decodes/binds inputs and reports unresolved operations without calling AI. Render
accepts text, structured JSON, resolved JSON or a bundle. Output files are staged
and individually committed atomically. Existing destinations fail unless
`--overwrite` is supplied. `--format`/`--quality` override recipe output settings;
`--mask ID` produces original-space PNG. Reports and bundles are explicit outputs.

Batch is nonrecursive and sorted, accepts PNG/JPEG/WebP, and uses one fresh browser
per image. Output names include the complete input filename to avoid extension
collisions. Each successful item gets a resolved sidecar. Item failures are
reported and processing continues; any failure yields a nonzero exit status.

Remote operations use `--media-id`, mutually exclusive with `--input` and batch.
The CLI downloads that library original and hosts only the existing segmentation
and Magic Eraser routes through an authenticated adapter. Credentials stay out of
Chromium and recipes. Uploads remain a separate library command. Segmentation
retains backend Standard-plan checks; browser jobs use shared SSE and reconnect
reconciliation, CLI jobs use bounded status backoff. Accepted ambiguous operations
are never automatically resubmitted. Cancellation can stop local work and request
job cancellation; it cannot reverse a completed remote operation or charge.

Limits: 4 million script characters, 10,000 operations, 256 layers, 256 masks,
128 assets, 100,000 points, one million interpolated dabs, 60MP input images,
256MiB decoded assets, 384MiB bundles. Worker device budgets may be lower. Default
execution deadline is two minutes (`--timeout` per CLI image). Batch concurrency
is one. Tile-cache budgets are not total-memory limits; export assembles a full
canvas. No scripts can read arbitrary files, fetch URLs, run code or loop.

Generation uses the existing CLI Gemini credential resolution, schema-constrained
Interactions output, `store=false`, and the same validator/printer. It does not
render or execute remote edits. Validation errors surface instead of silently
repairing model output. See the [official structured-output contract](https://ai.google.dev/gemini-api/docs/structured-output).

## Verification

- `iedl.test.ts`: parser/printer stability, invalid inputs, all local operation
  families, typed bindings, dynamic snapshots, document conversion and limits.
- Browser IEDL regressions: real workers, parity, auto/wand resolution, bundles,
  corrupt assets and replay; existing editor regressions cover CPU/GPU/WASM,
  filter/retouch/liquify seams, masks, EXIF/geometry and UI history.
- Go tests cover command binding, runtime protocol, remote host and batch behavior.
- `node scripts/build-image-editor.mjs --check` checks all runtime artifacts.

Remote model quality and paid generation need authenticated acceptance testing;
automated tests must not incur paid calls. Real 24–50MP sessions and Safari/Firefox
remain necessary device-level acceptance checks, as documented in IMAGE_EDITOR.md.

The browser recipe lab (see repository `docs/IMAGE_EDITOR.md`, “Recipe lab and skin selection”) at `/image-editor/lab` provides starter recipes, parameter tuning, cached selections, comparisons and saved experiments. `select skin skin` is experimental soft coverage; inspect facial details and edges before smoothing.

## Versioned presets

`apply skin-smooth@1 mask=MASK [strength=0.4] [id=LAYER]` is an experimental,
immutable preset. `strength` is a finite number in [0,1], and `mask` must reference
an existing selection. It expands into an adjustment layer (opacity=strength),
then `denoise=18 texture=-10`. Default layer IDs derive from statement position;
use `id` to reference the layer later. Collisions are rejected. Selection itself
is never implicit or included in the preset. Expanded operations count toward
normal operation/layer budgets and retain the invocation's diagnostic location.
Resolved reports contain the version and expansion; replay uses the ordinary
resolved document. Human approval and proposal export live in the
collection feedback workflow in repository `docs/IMAGE_EDITOR.md`.

### Look catalog

All looks below are experimental version 1 candidates for lab evaluation. Global
looks accept an optional `mask`; Subject Pop and Skin Smooth require one. `strength`
controls adjustment-layer opacity from 0 to 1. At zero the source pixels are unchanged;
at one the full look is applied. Optional `id` names the resulting editable layer.

| Preset | Default strength | Behavior |
| --- | ---: | --- |
| `subject-pop@1` | 0.65 | Explicit subject mask; exposure +0.2, clarity, texture and vibrance |
| `bw-classic@1` | 1 | Neutral monochrome, moderate contrast and highlight protection |
| `bw-high-contrast@1` | 1 | Neutral monochrome, deeper blacks and stronger contrast |
| `bw-matte@1` | 1 | Neutral monochrome, lifted blacks and softened highlights |
| `teal-orange@1` | 0.65 | Channel curves for teal shadows and orange highlights |
| `cinematic@1` | 0.7 | Restrained saturation, soft blacks, cool shadows and warm highlights |
| `dark-moody@1` | 0.65 | Lower exposure, deeper blacks and subdued green/blue bands |

B&W strengths below 1 blend the original color back in. The tonal color looks do
not detect faces or protect skin automatically. Cinematic does not crop, add borders,
or change the aspect ratio. Subject Pop only edits inside its mask and does not
blur or darken the background. All global looks run locally without paid services.

```iedl
iedl 1
input image
apply teal-orange@1 strength=0.55 id=grade
```

```iedl
iedl 1
input image
select subject subject
refine subject feather=2px
apply subject-pop@1 mask=subject strength=0.65 id=pop
```

Each preset has a lab starter and frozen expansion fixtures. New versions must
use new identifiers; approved proposals cannot reuse any registered version.

### Occasion and scene looks

These additional version 1 presets are experimental candidates for tagged collection
reviews. All accept `strength` in [0,1] and optional `id`. Only Milky Way Definition
requires a mask; other looks can optionally be restricted with `mask`.

| Preset | Default strength | Intended look |
| --- | ---: | --- |
| `wedding-clean@1` | 0.7 | Neutral whites, gentle contrast, restrained color |
| `wedding-airy@1` | 0.6 | Brighter midtones and softer shadows |
| `golden-romance@1` | 0.6 | Warm highlights and softened greens |
| `editorial-portrait@1` | 0.65 | Clean color, deeper blacks, defined midtones |
| `soft-pastel@1` | 0.65 | Soft contrast and subdued colors without an added pink cast |
| `indoor-celebration@1` | 0.65 | Lifted shadows and controlled highlights |
| `family-natural@1` | 0.7 | Gentle contrast and vibrance |
| `autumn-warmth@1` | 0.6 | Warm earth tones and restrained greens |
| `landscape-crisp@1` | 0.65 | Moderate dehaze/texture and richer blues/greens |
| `woodland-soft@1` | 0.65 | Soft highlights, muted greens, subtle warmth |
| `night-sky-natural@1` | 0.5 | Restrained tonal contrast and color |
| `milky-way-definition@1` | 0.5 | Gentle clarity/dehaze inside an explicit sky mask |

Exposure and white-balance correction remain separate, explicit steps. None of these
looks performs skin smoothing. Both astro presets omit denoise and sharpening; they
do not perform stacking, RAW calibration, star reduction or light-pollution removal.
Use full-resolution review for star detail. Sky segmentation may fail on night scenes;
a manually defined/imported sky mask can be used instead.

```iedl
iedl 1
input image
apply family-natural@1 strength=0.7 id=look
```

```iedl
iedl 1
input image
select sky sky
refine sky feather=2px
apply milky-way-definition@1 mask=sky strength=0.5 id=sky-detail
```

The catalog exposes each preset's explicit selection kind so generated lab starters
and structured recipe generation use the correct mask. Existing version expansions
are unchanged and verified against their saved fixtures.

### Prompt-guided masked generation

```iedl
iedl 1
input image
param instruction string default="Create a soft sunset matching the existing lighting."
select sky sky
refine sky feather=3px
generative-edit id=sunset mask=sky prompt=$instruction
```

`mask` references a previously declared mask: AI, painted, geometric or imported.
`id` names a new raster layer. The runner sends the preceding composite at full
original dimensions (crop, rotation and flips reset), the rendered mask, and the
exact prompt to the authenticated Node Magic Eraser route. Python uses the server's
configured image-generation model and blends the result; IEDL adds it through the
same mask. Presentation transforms remain in the final document. Soft edges may
be blended by both the backend and layer mask.

A library media ID and the existing Magic Eraser credentials/credits access are
required. This is remote generation, not local image analysis. No new Python API
or deployment is needed for prompt forwarding. Existing `erase MASK id=cleanup`
continues to use the backend's default removal prompt. Neither command selects a
mask implicitly. Missing/unknown masks, missing IDs, blank/oversized prompts and
unsupported fields fail before submitting the operation. The runner does not retry
an ambiguous paid request. Lab automatic previews do not initiate generation;
press Run explicitly. Each explicit run can generate a new result, even if a prior
semantic selection was cached. Resolved bundles preserve generated assets so replay
does not invoke the model again. Aborting the client does not guarantee cancellation
of an already-running backend generation.


### Installed browser discovery

The CLI runner locates an executable Chrome/Chromium using `--browser`, then
`CHROME_PATH`, then common browser names on `PATH`, then platform installation
locations. An invalid explicit override fails with an actionable error. Paths
containing spaces are supported; discovery never invokes a shell, downloads a
browser, or executes a candidate to probe it. `generate` and ordinary recipe
`validate` do not need Chromium; rendering and input-bound inspection do. Node
and the packaged runtime are still required. Provision a browser compatible with
the bundle's pinned Puppeteer Core version. The bundle now includes `browser.mjs`.

### Comprehensive verification

See [IEDL_TEST_HARNESS.md](IEDL_TEST_HARNESS.md) for the command/preset coverage
matrix, `npm run test:iedl`, full browser/CLI checks and optional local image-gallery
review. Synthetic checks are deterministic and paid operations are mocked; photographic
quality is reviewed separately against real images.


## Smart baseline and local metering (experimental)

Prefer explicit local masks when a subject and background need different corrections:

```iedl
iedl 1
input image
select subject subject
refine subject feather=2px
analyze region image input=original mask=subject
auto baseline id=subject-baseline analysis=region mask=subject
output format=jpeg quality=0.92
```

`select` is an explicit authenticated AI operation. A manual or imported mask can
replace it; analyzing and rendering those masks stays local. `analyze NAME image
mask=MASK input=original` meters source pixels at effective mask coverage >=0.5,
including mask density/refinement. It uses bounded previews (maximum 512 px), so
small features may have insufficient samples. Current/cropped masked image analysis
is rejected for now. This differs from `analyze NAME mask`, which measures mask
geometry rather than photograph light/color.

An `auto` consuming masked image findings must specify the same `mask`; the
resulting adjustment layer is masked. A mismatched or missing mask is rejected.
This also works for exposure, white balance and vibrance. Whole-image analysis
must feed unmasked auto adjustments. Mask edits after analysis do not re-meter:
create a new analysis when changing a mask before its consumer.

`auto baseline` always requires named image analysis. `smart-baseline-v1` proposes
at most ±0.5 EV, modest shadow/highlight changes, and partial white balance only
with sufficient neutral evidence and a modest estimated cast. Very dark scenes
preserve their exposure; empty/small samples produce no changes and review notes.
The local lab shows reasons and unresolved decisions. A global fallback is:

```iedl
iedl 1
input image
analyze scene image input=original
auto baseline id=baseline analysis=scene
output format=jpeg quality=0.92
```

This is an experimental starting point, not a scene/face classifier or calibrated
confidence score. It does not automatically smooth skin, crop, sharpen or perform
creative color grading. The resolved report records the profile and concrete
values; resolved replay does not recompute suggestions.


## Mask review in the lab

Run a recipe and choose its mask under **Inspect a mask…**. **Review facial
features** opens an original-resolution annotation panel using the loaded original
and resolved refined mask. **Download full-resolution mask** exports its grayscale
PNG directly, including after restoring a saved experiment, without another AI call.
The review can export regional coverage metrics, polygons and provenance. Annotations
are transient until downloaded; changing the source/mask/recipe clears the review.
The panel supports up to 40 MP. The compact mask preview remains a 1024 px preview.
