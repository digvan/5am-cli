<!-- Purpose: Comprehensive performance and pixel-parity benchmark report comparing the IEDL Native Skia (skia/simd) engine against Headless Chrome across 1 MP–24 MP synthetic workloads, batch/conformance suites, and all 106 local rendered examples in the IEDL visual field guide. -->
# IEDL Engine Benchmark: Native Skia (`skia/simd`) vs. Headless Chrome

This document records the performance, memory footprint, and pixel-level parity benchmarks comparing the default **Native Skia (`@napi-rs/canvas` 1.0.11 + Node WebAssembly SIMD, `skia/simd`)** engine against **Headless Chrome (`puppeteer-core`, `webgl2+cpu/simd` / `--disable-gpu`)** for the 5AM IEDL (`5am media image-edit`) runtime.

---

## 1. Executive Summary & Environment

- **Runtime Version**: `iedl-1.1.0`
- **Native Engine (Default)**: `Node.js/24.15.0 (@napi-rs/canvas 1.0.11; skia)`, backend `skia/simd` (`kernels-simd.wasm` + `node:worker_threads`)
- **Browser Engine (`--engine chrome`)**: `HeadlessChrome/152.0.0.0`, backend `webgl2+cpu/simd` (desktop GPU) and `--disable-gpu` (Cloud Run container parity)
- **Key Architectural & CPU Optimizations**:
  1. **Zero Browser Startup & IPC**: Running `worker.ts` inside `node:worker_threads` with `@napi-rs/canvas` 1.0.11 eliminates Chromium process tree startup (`~0.8–1.5 s`), loopback HTTP staging, and DevTools WebSocket serialization.
  2. **4,096-Entry Linear/WB/sRGB Transfer LUT & Identity-Curve Fast Path (`processing.ts`)**: Replaces 6 per-pixel `Math.pow` calls in `applyAdjustments` with 4,096-entry linearly interpolated `Float32Array` lookup tables (`buildGainLut`, max error `< 8e-8` or `0.00002` of an 8-bit code value, **8.25× faster**) plus `isIdentityCurve` bypass.
  3. **Lazy Multi-Scale Box Blur & Single-Pass Luma Detail (`processing.ts`)**: Evaluates `fine`, `medium`, and `broad` box blurs in `applyDetail` only for non-zero detail sliders and uses a single RGB pass when `colorNoise === 0` (**up to 10.5× faster**, zero numerical difference).
  4. **Cache-Friendly Vertical Box Blur & Mask Geometry (`masks.ts`)**: Uses a row-major `Float64Array` sliding-window accumulator for the vertical pass in `boxBlur` (**1.76× faster**) and hoisted row constants in radial/linear mask evaluation.
  5. **Tile Float/Byte Packing (`worker.ts`)**: Replaces division by `255` with `* (1 / 255)` and uses a direct clamping fast path when `!request.maskOnly && !overlay`.

---

## 2. Multi-Resolution End-to-End Render & Batch Benchmarks

### 2.1 Single-Image End-to-End Render Latency & Memory

Workload: `analyze` + `auto exposure` + radial feathered mask + `family-natural@1` preset + `4:5` crop + JPEG `0.92` export.

| Resolution | Native Skia (Before Opt) | Native Skia (After Opt) | Skia Opt Speedup | Cloud Run Chrome (`--disable-gpu`) | Desktop Chrome (WebGL2 GPU) | Native Skia vs. Cloud Run Chrome | Native Skia vs. Desktop GPU Chrome | Native Skia Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1 MP (`1000×1000`)** | 1,372 ms | **560–745 ms** | **1.84–2.45×** | 3,740–4,600 ms | 2,412–2,761 ms | **5.0–6.2× faster** | **3.2–4.9× faster** | **220.7 MiB** |
| **12 MP (`4000×3000`)** | 9,276–10,271 ms | **1,519–1,651 ms** | **6.1–6.76×** | 3,293–9,422 ms | 3,540–3,701 ms | **2.0–5.7× faster** | **2.24–2.33× faster** | **546.9 MiB** |
| **24 MP (`6000×4000`)** | 13,721–14,258 ms | **2,117–2,362 ms** | **6.0–6.73×** | 4,091–12,935 ms | 4,341–4,867 ms | **1.73–5.5× faster** | **2.05–2.06× faster** | **731.0 MiB** |

### 2.2 Batch & Conformance Harness Latency

| Workload | Native Skia (Before Opt) | Native Skia (After Opt) | Headless Chrome | Result |
| --- | ---: | ---: | ---: | --- |
| **8× 2 MP Batch (`concurrency=4`)** | 4,119 ms | **2,290 ms** (745 MiB RSS) | 6,625 ms | **2.89× faster than Chrome** |
| **4-Item Batch (`test-iedl-batch.mjs`)** | 1,485 ms | **1,360 ms** | 11,814 ms | **8.68× faster than Chrome** |
| **Worker Integration (`test-iedl-browser.mjs`)** | 20,432 ms | **7,260 ms** | 6,536 ms | **2.81× faster than before** |
| **829-Case Conformance (`test-iedl-conformance.mjs`)** | 35,428 ms | **17,781 ms** | 16,308 ms | **2.0× faster than before** (829/829 pass) |
| **24 MP Browser Export (`test-image-editor-large.mjs`)** | ~8,400 ms | **1,944 ms** | — | **4.3× faster** in browser worker |

---

## 3. 113-Example Visual Field Guide Benchmark (`examples/image-edit`)

The IEDL visual field guide (`examples/image-edit`) exercises all **26 IEDL commands** and **20 photographic presets** across **113 examples** (**106 local rendered cases** + **39 exported grayscale masks** via `.iedl.zip` bundle replay + **7 remote recipe validations**) on the `640×960` concert photograph (`source.jpg`, SHA-256 `acdc2ad9823809819cc34ccb2fea99ea8abd3678a14634355091841a73cb3577`).

In `build_gallery.py`, each local case executes 2–3 separate CLI subprocess invocations:
1. `5am media image-edit validate recipes/<id>.iedl`
2. `5am media image-edit render recipes/<id>.iedl --input source.jpg -o images/<id>.<ext> --resolved resolved/<id>.json [--bundle bundles/<id>.iedl.zip]`
3. *(For the 39 masked cases)* `5am media image-edit render bundles/<id>.iedl.zip --input source.jpg --mask <mask> -o masks/<id>.png`

### 3.1 Overall Gallery Timing Summary (106 Local Rendered Cases)

| Metric (`results.json`) | Headless Chrome (`webgl2+cpu/simd`) | Native Skia (`skia/simd`) | Speedup |
| --- | ---: | ---: | ---: |
| **Cumulative Per-Case Time (`sum(seconds)`)** | **169.61 s** | **59.09 s** | **2.87× faster** |
| **Full Gallery Wall-Clock (`--jobs 2`)** | ~88.0 s | **41.0 s** | **2.15× faster** |
| **Mean Time per Case** | 1.600 s | **0.557 s** | **2.87× faster** |
| **Median (P50) Time per Case** | 1.59 s | **0.54 s** | **2.94× faster** |
| **P95 Time per Case** | 1.80 s | **0.68 s** | **2.65× faster** |
| **Min / Max Time per Case** | 1.33 s / 2.14 s | **0.44 s / 0.84 s** | — |

### 3.2 Timing & Pixel Parity by Category

| Category | Local Cases | Avg Chrome (s) | Avg Skia (s) | Speedup | Mean MAE (`0..255`) | Max Channel Delta (`0..255`) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Start here** (`stage-balance`) | 1 | 1.74 s | **0.55 s** | **3.16×** | `0.001` | `4` |
| **Adjustments** | 16 | 1.57 s | **0.49 s** | **3.18×** | `0.000` | `3` |
| **Presets** | 20 | 1.60 s | **0.64 s** | **2.48×** | `0.000` | `4` |
| **Curves & HSL** | 12 | 1.74 s | **0.55 s** | **3.18×** | **`0.000`** | **`0`** |
| **Masks** | 20 | 1.62 s | **0.55 s** | **2.94×** | `0.001` | `9` |
| **Layers** | 10 | 1.56 s | **0.52 s** | **2.99×** | `0.059` | `244` *(text antialiasing)* |
| **Geometry** | 6 | 1.48 s | **0.49 s** | **3.01×** | `0.187` | `57` *(2.5° rotation)* |
| **Retouch & liquify** | 11 | 1.58 s | **0.57 s** | **2.80×** | `0.000` | `5` |
| **Analysis & automation** | 8 | 1.59 s | **0.58 s** | **2.77×** | `0.001` | `3` |
| **Output & assets** | 2 | 1.46 s | **0.60 s** | **2.42×** | `0.071` | `11` *(WebP encoder)* |

### 3.3 Pixel-Level & Mask-Level Parity Summary

| Parity Metric | Result Across 106 Rendered Images | Result Across 39 Exported Mask PNGs |
| --- | --- | --- |
| **Overall Mean Absolute Error (MAE, `0..255`)** | **`0.0179`** | **`0.0006`** |
| **Bit/Pixel-Identical (`maxDelta == 0`, `PSNR = ∞`)** | **62 / 106 (`58.5%`)** | **17 / 39 (`43.6%`)** |
| **Sub-Half-LSB (`MAE <= 0.5 / 255`)** | **105 / 106 (`99.1%`)** | **39 / 39 (`100.0%`)** |
| **Sub-1-LSB (`MAE <= 1.0 / 255`)** | **105 / 106 (`99.1%`)** | **39 / 39 (`100.0%`)** |
| **All Cases (`MAE <= 1.12 / 255`)** | **106 / 106 (`100.0%`)** | **39 / 39 (`100.0%`, max MAE `0.016`)** |

#### Root-Cause Breakdown of the Only 4 Cases with `MAE > 0.02 / 255`

1. **`geometry-rectangle`** (`MAE = 1.120`, `PSNR = 41.49 dB`, `maxDelta = 57`): Applies an arbitrary `rotate 2.5` degree 2D canvas transform before cropping. Standalone Skia (`@napi-rs/canvas`) and Chromium Blink/Skia differ slightly in bilinear subpixel sampling during angled image rotation, compounded by `quality = 0.9` JPEG quantization.
2. **`layer-text`** (`MAE = 0.494`, `PSNR = 29.06 dB`, `maxDelta = 244`, only `0.65%` of pixels differ by `> 2`): Renders a system sans-serif text layer (`fillText`). Subpixel glyph edge antialiasing differs slightly along glyph boundaries.
3. **`output-webp`** (`MAE = 0.142`, `PSNR = 53.15 dB`, `maxDelta = 11`): Lossy WebP quantization difference at `quality = 0.9` between `@napi-rs/canvas` and Chromium `libwebp`.
4. **`layer-raster`** (`MAE = 0.091`, `PSNR = 53.87 dB`, `maxDelta = 15`): 2D canvas `drawImage` scaling of the composited raster overlay asset.

---

## 4. Complete 106-Case Field Guide Benchmark Table

| # | Case ID | Category | Mask Replay | Chrome (s) | Skia (s) | Speedup | MAE (`0..255`) | PSNR (dB) | Max Delta (`0..255`) | Pixels `> 2` (%) |
| ---: | --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `stage-balance` | Start here | Yes | 1.74 | **0.55** | **3.16×** | `0.0006` | 77.98 | `4` | 0.00% |
| 2 | `adjust-exposure` | Adjustments | No | 1.59 | **0.47** | **3.38×** | `0.0000` | ∞ | `0` | 0.00% |
| 3 | `adjust-contrast` | Adjustments | No | 1.53 | **0.44** | **3.48×** | `0.0000` | ∞ | `0` | 0.00% |
| 4 | `adjust-highlights` | Adjustments | No | 1.57 | **0.50** | **3.14×** | `0.0001` | 90.96 | `1` | 0.00% |
| 5 | `adjust-shadows` | Adjustments | No | 1.54 | **0.49** | **3.14×** | `0.0000` | ∞ | `0` | 0.00% |
| 6 | `adjust-whites` | Adjustments | No | 1.63 | **0.48** | **3.40×** | `0.0000` | ∞ | `0` | 0.00% |
| 7 | `adjust-blacks` | Adjustments | No | 1.52 | **0.49** | **3.10×** | `0.0003` | 83.84 | `1` | 0.00% |
| 8 | `adjust-temperature` | Adjustments | No | 1.54 | **0.49** | **3.14×** | `0.0000` | ∞ | `0` | 0.00% |
| 9 | `adjust-tint` | Adjustments | No | 1.41 | **0.45** | **3.13×** | `0.0000` | ∞ | `0` | 0.00% |
| 10 | `adjust-saturation` | Adjustments | No | 1.53 | **0.49** | **3.12×** | `0.0000` | ∞ | `0` | 0.00% |
| 11 | `adjust-vibrance` | Adjustments | No | 1.54 | **0.48** | **3.21×** | `0.0000` | ∞ | `0` | 0.00% |
| 12 | `adjust-texture` | Adjustments | No | 1.67 | **0.53** | **3.15×** | `0.0000` | 91.54 | `1` | 0.00% |
| 13 | `adjust-clarity` | Adjustments | No | 1.79 | **0.54** | **3.31×** | `0.0001` | 87.98 | `1` | 0.00% |
| 14 | `adjust-dehaze` | Adjustments | No | 1.52 | **0.47** | **3.23×** | `0.0000` | ∞ | `0` | 0.00% |
| 15 | `adjust-sharpening` | Adjustments | No | 1.51 | **0.52** | **2.90×** | `0.0001` | 86.42 | `2` | 0.00% |
| 16 | `adjust-denoise` | Adjustments | No | 1.58 | **0.47** | **3.36×** | `0.0045` | 71.33 | `3` | 0.00% |
| 17 | `adjust-colorNoise` | Adjustments | No | 1.60 | **0.57** | **2.81×** | `0.0000` | ∞ | `0` | 0.00% |
| 18 | `preset-skin-smooth-1` | Presets | Yes | 1.69 | **0.58** | **2.91×** | `0.0000` | ∞ | `0` | 0.00% |
| 19 | `preset-subject-pop-1` | Presets | Yes | 1.59 | **0.65** | **2.45×** | `0.0000` | 91.34 | `1` | 0.00% |
| 20 | `preset-bw-classic-1` | Presets | No | 1.50 | **0.67** | **2.24×** | `0.0002` | 84.08 | `2` | 0.00% |
| 21 | `preset-bw-high-contrast-1` | Presets | No | 1.42 | **0.70** | **2.03×** | `0.0001` | 87.15 | `1` | 0.00% |
| 22 | `preset-bw-matte-1` | Presets | No | 1.53 | **0.66** | **2.32×** | `0.0006` | 80.23 | `2` | 0.00% |
| 23 | `preset-teal-orange-1` | Presets | No | 1.45 | **0.65** | **2.23×** | `0.0002` | 84.67 | `1` | 0.00% |
| 24 | `preset-cinematic-1` | Presets | No | 1.54 | **0.84** | **1.83×** | `0.0010` | 77.86 | `2` | 0.00% |
| 25 | `preset-wedding-clean-1` | Presets | No | 1.54 | **0.53** | **2.91×** | `0.0000` | 94.77 | `1` | 0.00% |
| 26 | `preset-wedding-airy-1` | Presets | No | 1.59 | **0.67** | **2.37×** | `0.0001` | 85.94 | `2` | 0.00% |
| 27 | `preset-golden-romance-1` | Presets | No | 1.73 | **0.68** | **2.54×** | `0.0000` | ∞ | `0` | 0.00% |
| 28 | `preset-editorial-portrait-1` | Presets | No | 1.62 | **0.76** | **2.13×** | `0.0007` | 79.22 | `4` | 0.00% |
| 29 | `preset-soft-pastel-1` | Presets | No | 1.45 | **0.66** | **2.20×** | `0.0006` | 78.67 | `2` | 0.00% |
| 30 | `preset-indoor-celebration-1` | Presets | No | 1.73 | **0.44** | **3.93×** | `0.0001` | 87.50 | `1` | 0.00% |
| 31 | `preset-family-natural-1` | Presets | No | 1.50 | **0.46** | **3.26×** | `0.0000` | ∞ | `0` | 0.00% |
| 32 | `preset-autumn-warmth-1` | Presets | No | 1.70 | **0.55** | **3.09×** | `0.0000` | ∞ | `0` | 0.00% |
| 33 | `preset-landscape-crisp-1` | Presets | No | 1.59 | **0.61** | **2.61×** | `0.0000` | ∞ | `0` | 0.00% |
| 34 | `preset-woodland-soft-1` | Presets | No | 1.66 | **0.72** | **2.31×** | `0.0000` | 93.71 | `1` | 0.00% |
| 35 | `preset-night-sky-natural-1` | Presets | No | 1.45 | **0.62** | **2.34×** | `0.0000` | ∞ | `0` | 0.00% |
| 36 | `preset-milky-way-definition-1` | Presets | Yes | 1.89 | **0.64** | **2.95×** | `0.0000` | ∞ | `0` | 0.00% |
| 37 | `preset-dark-moody-1` | Presets | No | 1.76 | **0.77** | **2.29×** | `0.0000` | ∞ | `0` | 0.00% |
| 38 | `curve-rgb` | Curves & HSL | No | 1.61 | **0.64** | **2.52×** | `0.0000` | ∞ | `0` | 0.00% |
| 39 | `curve-r` | Curves & HSL | No | 2.14 | **0.52** | **4.12×** | `0.0000` | ∞ | `0` | 0.00% |
| 40 | `curve-g` | Curves & HSL | No | 2.14 | **0.55** | **3.89×** | `0.0000` | ∞ | `0` | 0.00% |
| 41 | `curve-b` | Curves & HSL | No | 1.56 | **0.54** | **2.89×** | `0.0000` | ∞ | `0` | 0.00% |
| 42 | `hsl-red` | Curves & HSL | No | 1.66 | **0.52** | **3.19×** | `0.0000` | ∞ | `0` | 0.00% |
| 43 | `hsl-orange` | Curves & HSL | No | 1.67 | **0.54** | **3.09×** | `0.0000` | ∞ | `0` | 0.00% |
| 44 | `hsl-yellow` | Curves & HSL | No | 1.57 | **0.56** | **2.80×** | `0.0000` | ∞ | `0` | 0.00% |
| 45 | `hsl-green` | Curves & HSL | No | 1.75 | **0.54** | **3.24×** | `0.0000` | ∞ | `0` | 0.00% |
| 46 | `hsl-aqua` | Curves & HSL | No | 1.71 | **0.54** | **3.17×** | `0.0000` | ∞ | `0` | 0.00% |
| 47 | `hsl-blue` | Curves & HSL | No | 1.74 | **0.53** | **3.28×** | `0.0000` | ∞ | `0` | 0.00% |
| 48 | `hsl-purple` | Curves & HSL | No | 1.70 | **0.54** | **3.15×** | `0.0000` | ∞ | `0` | 0.00% |
| 49 | `hsl-magenta` | Curves & HSL | No | 1.62 | **0.55** | **2.95×** | `0.0000` | ∞ | `0` | 0.00% |
| 50 | `mask-brush` | Masks | Yes | 1.54 | **0.52** | **2.96×** | `0.0200` | 63.15 | `9` | 0.06% |
| 51 | `mask-linear` | Masks | Yes | 1.42 | **0.53** | **2.68×** | `0.0000` | 93.01 | `1` | 0.00% |
| 52 | `mask-radial` | Masks | Yes | 1.58 | **0.51** | **3.10×** | `0.0002` | 84.85 | `3` | 0.00% |
| 53 | `mask-rectangle` | Masks | Yes | 1.73 | **0.54** | **3.20×** | `0.0000` | ∞ | `0` | 0.00% |
| 54 | `mask-ellipse` | Masks | Yes | 1.80 | **0.51** | **3.53×** | `0.0011` | 75.48 | `7` | 0.00% |
| 55 | `mask-lasso` | Masks | Yes | 1.79 | **0.58** | **3.09×** | `0.0009` | 77.28 | `3` | 0.00% |
| 56 | `mask-polygon` | Masks | Yes | 1.65 | **0.54** | **3.06×** | `0.0009` | 77.28 | `3` | 0.00% |
| 57 | `mask-color` | Masks | Yes | 1.54 | **0.54** | **2.85×** | `0.0000` | ∞ | `0` | 0.00% |
| 58 | `mask-luminance` | Masks | Yes | 1.60 | **0.58** | **2.76×** | `0.0004` | 80.24 | `3` | 0.00% |
| 59 | `mask-raster` | Masks | Yes | 2.03 | **0.57** | **3.56×** | `0.0005` | 79.85 | `4` | 0.00% |
| 60 | `mask-add` | Masks | Yes | 1.70 | **0.54** | **3.15×** | `0.0000` | ∞ | `0` | 0.00% |
| 61 | `mask-subtract` | Masks | Yes | 1.67 | **0.56** | **2.98×** | `0.0000` | ∞ | `0` | 0.00% |
| 62 | `mask-intersect` | Masks | Yes | 1.55 | **0.62** | **2.50×** | `0.0000` | ∞ | `0` | 0.00% |
| 63 | `refine-feather` | Masks | Yes | 1.64 | **0.56** | **2.93×** | `0.0008` | 78.85 | `3` | 0.00% |
| 64 | `refine-expand` | Masks | Yes | 1.59 | **0.58** | **2.74×** | `0.0004` | 80.96 | `3` | 0.00% |
| 65 | `refine-contract` | Masks | Yes | 1.53 | **0.57** | **2.68×** | `0.0004` | 80.65 | `3` | 0.00% |
| 66 | `refine-smooth` | Masks | Yes | 1.54 | **0.61** | **2.52×** | `0.0006` | 78.96 | `2` | 0.00% |
| 67 | `refine-density` | Masks | Yes | 1.59 | **0.54** | **2.94×** | `0.0003` | 81.78 | `4` | 0.00% |
| 68 | `refine-invert` | Masks | Yes | 1.49 | **0.54** | **2.76×** | `0.0006` | 79.40 | `3` | 0.00% |
| 69 | `refine-bypass` | Masks | Yes | 1.49 | **0.51** | **2.92×** | `0.0000` | ∞ | `0` | 0.00% |
| 70 | `blend-normal` | Layers | No | 1.49 | **0.51** | **2.92×** | `0.0000` | ∞ | `0` | 0.00% |
| 71 | `blend-multiply` | Layers | No | 1.55 | **0.50** | **3.10×** | `0.0000` | ∞ | `0` | 0.00% |
| 72 | `blend-screen` | Layers | No | 1.52 | **0.52** | **2.92×** | `0.0000` | ∞ | `0` | 0.00% |
| 73 | `blend-overlay` | Layers | No | 1.56 | **0.48** | **3.25×** | `0.0000` | ∞ | `0` | 0.00% |
| 74 | `blend-soft-light` | Layers | No | 1.50 | **0.50** | **3.00×** | `0.0000` | ∞ | `0` | 0.00% |
| 75 | `blend-luminosity` | Layers | No | 1.50 | **0.50** | **3.00×** | `0.0000` | ∞ | `0` | 0.00% |
| 76 | `layer-text` | Layers | No | 1.61 | **0.56** | **2.88×** | `0.4938` | 29.06 | `244` | 0.65% |
| 77 | `layer-raster` | Layers | No | 1.79 | **0.57** | **3.14×** | `0.0910` | 53.87 | `15` | 1.13% |
| 78 | `layer-frequency` | Layers | Yes | 1.59 | **0.56** | **2.84×** | `0.0034` | 69.95 | `6` | 0.03% |
| 79 | `layer-lifecycle` | Layers | No | 1.46 | **0.51** | **2.86×** | `0.0000` | ∞ | `0` | 0.00% |
| 80 | `geometry-square` | Geometry | No | 1.55 | **0.47** | **3.30×** | `0.0000` | ∞ | `0` | 0.00% |
| 81 | `geometry-portrait` | Geometry | No | 1.47 | **0.50** | **2.94×** | `0.0000` | ∞ | `0` | 0.00% |
| 82 | `geometry-rotate` | Geometry | No | 1.40 | **0.48** | **2.92×** | `0.0000` | ∞ | `0` | 0.00% |
| 83 | `geometry-flip-x` | Geometry | No | 1.63 | **0.50** | **3.26×** | `0.0000` | ∞ | `0` | 0.00% |
| 84 | `geometry-flip-y` | Geometry | No | 1.46 | **0.51** | **2.86×** | `0.0000` | ∞ | `0` | 0.00% |
| 85 | `geometry-rectangle` | Geometry | No | 1.38 | **0.49** | **2.82×** | `1.1201` | 41.49 | `57` | 10.91% |
| 86 | `retouch-clone` | Retouch & liquify | Yes | 1.49 | **0.54** | **2.76×** | `0.0000` | ∞ | `0` | 0.00% |
| 87 | `retouch-heal` | Retouch & liquify | Yes | 1.47 | **0.55** | **2.67×** | `0.0000` | ∞ | `0` | 0.00% |
| 88 | `retouch-spot` | Retouch & liquify | Yes | 1.58 | **0.56** | **2.82×** | `0.0000` | ∞ | `0` | 0.00% |
| 89 | `retouch-patch` | Retouch & liquify | Yes | 1.51 | **0.55** | **2.75×** | `0.0000` | ∞ | `0` | 0.00% |
| 90 | `retouch-dodge` | Retouch & liquify | Yes | 1.56 | **0.53** | **2.94×** | `0.0000` | ∞ | `0` | 0.00% |
| 91 | `retouch-burn` | Retouch & liquify | Yes | 1.60 | **0.55** | **2.91×** | `0.0000` | ∞ | `0` | 0.00% |
| 92 | `retouch-red-eye` | Retouch & liquify | Yes | 1.56 | **0.55** | **2.84×** | `0.0000` | ∞ | `0` | 0.00% |
| 93 | `retouch-liquify` | Retouch & liquify | Yes | 1.63 | **0.57** | **2.86×** | `0.0000` | ∞ | `0` | 0.00% |
| 94 | `retouch-liquify-smooth` | Retouch & liquify | Yes | 1.62 | **0.60** | **2.70×** | `0.0002` | 80.43 | `5` | 0.00% |
| 95 | `retouch-reconstruct` | Retouch & liquify | Yes | 1.61 | **0.66** | **2.44×** | `0.0002` | 80.43 | `5` | 0.00% |
| 96 | `liquify-freeze` | Retouch & liquify | Yes | 1.80 | **0.56** | **3.21×** | `0.0000` | 94.35 | `1` | 0.00% |
| 97 | `auto-exposure` | Analysis & automation | No | 1.61 | **0.59** | **2.73×** | `0.0000` | ∞ | `0` | 0.00% |
| 98 | `auto-white-balance` | Analysis & automation | No | 1.67 | **0.61** | **2.74×** | `0.0000` | ∞ | `0` | 0.00% |
| 99 | `auto-vibrance` | Analysis & automation | No | 1.60 | **0.55** | **2.91×** | `0.0000` | ∞ | `0` | 0.00% |
| 100 | `auto-baseline` | Analysis & automation | No | 1.58 | **0.54** | **2.93×** | `0.0098` | 68.04 | `3` | 0.00% |
| 101 | `auto-local` | Analysis & automation | Yes | 1.66 | **0.68** | **2.44×** | `0.0006` | 79.55 | `3` | 0.00% |
| 102 | `analysis-mask` | Analysis & automation | Yes | 1.59 | **0.51** | **3.12×** | `0.0000` | ∞ | `0` | 0.00% |
| 103 | `wand` | Analysis & automation | Yes | 1.62 | **0.61** | **2.66×** | `0.0000` | ∞ | `0` | 0.00% |
| 104 | `parameters` | Analysis & automation | No | 1.40 | **0.51** | **2.75×** | `0.0000` | ∞ | `0` | 0.00% |
| 105 | `output-png` | Output & assets | No | 1.58 | **0.65** | **2.43×** | `0.0000` | 95.87 | `1` | 0.00% |
| 106 | `output-webp` | Output & assets | No | 1.33 | **0.55** | **2.42×** | `0.1415` | 53.15 | `11` | 1.25% |

---

## 5. Exported Mask PNG Parity Table (39 Masked Cases)

Each mask below was exported by replaying the generated `.iedl.zip` bundle (`5am media image-edit render bundles/<id>.iedl.zip --input source.jpg --mask <mask> -o masks/<id>.png`).

| # | Case ID | Category | Mask MAE (`0..255`) | Mask PSNR (dB) | Max Delta (`0..255`) | Pixels `> 2` (%) |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `stage-balance` | Start here | `0.0004` | 81.69 | `1` | 0.00% |
| 2 | `preset-skin-smooth-1` | Presets | `0.0002` | 84.98 | `1` | 0.00% |
| 3 | `preset-subject-pop-1` | Presets | `0.0004` | 81.69 | `1` | 0.00% |
| 4 | `preset-milky-way-definition-1` | Presets | `0.0000` | ∞ | `0` | 0.00% |
| 5 | `mask-brush` | Masks | `0.0161` | 65.89 | `2` | 0.00% |
| 6 | `mask-linear` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 7 | `mask-radial` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 8 | `mask-rectangle` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 9 | `mask-ellipse` | Masks | `0.0005` | 79.80 | `8` | 0.00% |
| 10 | `mask-lasso` | Masks | `0.0004` | 81.75 | `1` | 0.00% |
| 11 | `mask-polygon` | Masks | `0.0004` | 81.75 | `1` | 0.00% |
| 12 | `mask-color` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 13 | `mask-luminance` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 14 | `mask-raster` | Masks | `0.0004` | 81.69 | `1` | 0.00% |
| 15 | `mask-add` | Masks | `0.0000` | 85.48 | `8` | 0.00% |
| 16 | `mask-subtract` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 17 | `mask-intersect` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 18 | `refine-feather` | Masks | `0.0005` | 81.23 | `1` | 0.00% |
| 19 | `refine-expand` | Masks | `0.0005` | 81.10 | `1` | 0.00% |
| 20 | `refine-contract` | Masks | `0.0004` | 82.12 | `1` | 0.00% |
| 21 | `refine-smooth` | Masks | `0.0005` | 81.16 | `1` | 0.00% |
| 22 | `refine-density` | Masks | `0.0002` | 86.28 | `1` | 0.00% |
| 23 | `refine-invert` | Masks | `0.0004` | 81.64 | `1` | 0.00% |
| 24 | `refine-bypass` | Masks | `0.0000` | ∞ | `0` | 0.00% |
| 25 | `layer-frequency` | Layers | `0.0004` | 81.67 | `1` | 0.00% |
| 26 | `retouch-clone` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 27 | `retouch-heal` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 28 | `retouch-spot` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 29 | `retouch-patch` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 30 | `retouch-dodge` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 31 | `retouch-burn` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 32 | `retouch-red-eye` | Retouch & liquify | `0.0000` | ∞ | `0` | 0.00% |
| 33 | `retouch-liquify` | Retouch & liquify | `0.0001` | 90.45 | `1` | 0.00% |
| 34 | `retouch-liquify-smooth` | Retouch & liquify | `0.0001` | 89.29 | `1` | 0.00% |
| 35 | `retouch-reconstruct` | Retouch & liquify | `0.0001` | 89.29 | `1` | 0.00% |
| 36 | `liquify-freeze` | Retouch & liquify | `0.0001` | 89.29 | `1` | 0.00% |
| 37 | `auto-local` | Analysis & automation | `0.0004` | 81.64 | `1` | 0.00% |
| 38 | `analysis-mask` | Analysis & automation | `0.0004` | 81.64 | `1` | 0.00% |
| 39 | `wand` | Analysis & automation | `0.0000` | ∞ | `0` | 0.00% |
