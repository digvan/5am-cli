# IEDL visual field guide

**[Browse the visual gallery directly on GitHub →](GALLERY.md)** — side-by-side original/edited images for every rendered example, grouped by category, with recipe and mask links.

Open [`index.html`](index.html) after cloning this repository. GitHub displays HTML source; to see the interactive gallery, open the local file in a browser or serve the repository:

```sh
python3 -m http.server 8000
# Visit http://localhost:8000/examples/image-edit/
```

The interactive HTML page has category/search filters, before/after sliders, copyable recipes, rendered image downloads, grayscale masks, and resolved reports. Imported-mask and magic-wand examples also include replay bundles containing their raster assets. No external scripts, fonts, analytics, or API calls are needed to view it.

## Build a gallery with your own image

The gallery builder is open source under Apache 2.0. It uses Python 3.9+ standard library and the installed `5am` CLI, Node.js, image-edit runtime, and Chrome/Chromium. No Python packages are needed.

From the repository root:

```sh
5am update --runtime-only
python3 examples/image-edit/build_gallery.py \
  --input "/path/to/your photo.jpg" \
  --output-dir /tmp/my-iedl-gallery
# Open /tmp/my-iedl-gallery/index.html in a browser.
```

JPEG, PNG, and WebP inputs are converted to a resized JPEG preview (640 pixels wide by default); transparency is flattened. Use `--width 960` to increase preview resolution, up to 2048. Use an oriented export for predictable composition. The original file is never changed. The destination must be new or empty, even with `--overwrite`. Gallery generation uses local operations only; remote recipes remain recipe-only.

For a quick first experiment, append `--only auto-exposure,auto-white-balance,preset-cinematic-1` (see `cases.json` for IDs). Unselected cards remain “Not rendered.” To continue rendering, omit `--input`:

```sh
python3 examples/image-edit/build_gallery.py \
  --output-dir /tmp/my-iedl-gallery --render --overwrite
```

Edit the copied `recipes/*.iedl` files and rerun selected cases using `--only`. Imported masks are generated from the copied `stage-balance` subject region. **All sample geometric masks and retouch coordinates were drawn for the concert photograph. Adapt them to your image; they are not automatic subject/skin/sky detection.** Case notes describe the original demonstration. If you change `source.jpg`, the builder refuses to reuse stale results; create a new gallery instead.

Share the generated directory to share your experiments, including its image and reports. Your photographs retain their own rights; the sample photo provenance below applies only to the checked-in concert example.

## Coverage

113 examples cover all 26 IEDL commands: every adjustment slider, all 20 versioned presets, four curve channels, eight HSL bands, ten mask component kinds, mask composition/refinement, all layer kinds and blend modes, geometry, all retouch/liquify stroke kinds, local analysis, four automatic adjustments, explicit assets/parameters, and output codecs.

Seven authenticated examples are **recipe-only**: five AI selections, Magic Eraser, and prompt-guided masked editing. They were validated but not executed. Their cards show the original photograph, never an invented AI result. Use a real library media ID with the provided commands to run them.

The three mask-requiring presets use explicit **hand-drawn demonstration regions**. The skin example covers selected arm regions, not every skin pixel. The sky preset uses a dark background region; this concert photo is not a suitable astrophotography benchmark. Red-eye has no appropriate target here. Noise reduction and some HSL bands may show little change. Tool coverage is not proof of quality on every type of photograph.

## Run an example

Install a current `5am` CLI, Node.js 20+, and compatible Chrome/Chromium, then install the optional runtime:

```sh
5am update --runtime-only
cd examples/image-edit
5am media image-edit validate recipes/stage-balance.iedl
5am media image-edit render recipes/stage-balance.iedl --input source.jpg \
  -o stage.jpg --resolved stage.json --bundle stage.iedl.zip
5am media image-edit render stage.iedl.zip --input source.jpg -o replay.jpg
```

Imported masks/assets need explicit bindings. For example:

```sh
5am media image-edit render recipes/mask-raster.iedl --input source.jpg \
  --asset imported=assets/subject-mask.png -o masked.jpg
```

Recipes use relative geometry, but the hand-drawn regions are specific to this composition. Re-draw them for another photograph. The resolved reports bind the exact `source.jpg` bytes; they cannot be replayed against the original full-resolution file.

## Regenerate the gallery

Every build writes both `index.html` and `GALLERY.md`. Markdown uses the same saved images without additional rendering; upload the entire generated directory to a GitHub repository to view it there. The builder is Python standard library only. From this directory:

```sh
python3 build_gallery.py --render --overwrite
# Optional: two browsers for this small source; default is serial.
python3 build_gallery.py --render --overwrite --jobs 2
# Rerun selected cases only.
python3 build_gallery.py --render --overwrite --only stage-balance,auto-white-balance
# Rebuild HTML from saved results without rendering.
python3 build_gallery.py
# Check source hashes, artifacts, coverage, and links offline.
python3 check_gallery.py
# For an intentionally partial custom gallery:
python3 check_gallery.py --allow-partial
# Builder regression tests (from the repository example directory):
python3 test_gallery_builder.py
```

`--cli`, `--runtime`, and `--browser` accept explicit executable/runtime paths. The builder never executes remote recipes or calls a model. It validates recipes, records failures in `results.json`, writes real local renders, and exits nonzero if any local example fails. Existing output files require `--overwrite`. `capabilities.json` snapshots the source registry and preset catalog; the HTML builder checks that every registered command appears in the recipe collection.

Rendering uses the shared browser/CLI engine. GPU, browser, fonts, runtime versions, and image dimensions can affect pixels. Inspect mask boundaries, halos, clipped lights, and skin detail rather than treating every preset as a photographic recommendation.

## Photo and license

The repository maintainer supplied the concert photograph for these examples. The gallery uses a 640 × 960 JPEG derivative of the 1980 × 2970 original; it was resized using `5am media resize`, with metadata omitted. It does not identify the performers. The repository's Apache 2.0 code license does not grant a separate license to the photograph.

The scripts, recipes, and HTML are examples under the repository license. `results.json` records the sample's SHA-256; each resolved report records engine provenance and actual resolved edits. No customer credentials, library media IDs, or paid-service results are included.
