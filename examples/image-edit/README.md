# IEDL visual field guide

Open [`index.html`](index.html) after cloning this repository. GitHub displays HTML source; to see the interactive gallery, open the local file in a browser or serve the repository:

```sh
python3 -m http.server 8000
# Visit http://localhost:8000/examples/image-edit/
```

The page has category/search filters, before/after sliders, copyable recipes, rendered image downloads, grayscale masks, and resolved reports. Imported-mask and magic-wand examples also include replay bundles containing their raster assets. No external scripts, fonts, analytics, or API calls are needed to view it.

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

The builder is Python standard library only. From this directory:

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
```

`--cli`, `--runtime`, and `--browser` accept explicit executable/runtime paths. The builder never executes remote recipes or calls a model. It validates recipes, records failures in `results.json`, writes real local renders, and exits nonzero if any local example fails. Existing output files require `--overwrite`. `capabilities.json` snapshots the source registry and preset catalog; the HTML builder checks that every registered command appears in the recipe collection.

Rendering uses the shared browser/CLI engine. GPU, browser, fonts, runtime versions, and image dimensions can affect pixels. Inspect mask boundaries, halos, clipped lights, and skin detail rather than treating every preset as a photographic recommendation.

## Photo and license

The repository maintainer supplied the concert photograph for these examples. The gallery uses a 640 × 960 JPEG derivative of the 1980 × 2970 original; it was resized using `5am media resize`, with metadata omitted. It does not identify the performers. The repository's Apache 2.0 code license does not grant a separate license to the photograph.

The scripts, recipes, and HTML are examples under the repository license. `results.json` records the sample's SHA-256; each resolved report records engine provenance and actual resolved edits. No customer credentials, library media IDs, or paid-service results are included.
