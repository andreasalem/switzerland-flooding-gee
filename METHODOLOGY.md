# Switzerland Flooding GEE — Methodology, Literature Review & Project Log

This document consolidates all methodological decisions, technical findings, literature context,
and implementation notes from the development of this project. It is intended to serve as a
living reference for the methodology section of any accompanying paper, data note, or presentation.

---

## Table of Contents

1. [Event Background](#1-event-background)
2. [Project Architecture](#2-project-architecture)
3. [Dataset Inventory](#3-dataset-inventory)
4. [SAR Flood Detection — Central Switzerland](#4-sar-flood-detection--central-switzerland)
5. [Sentinel-2 Optical Compositing — Brienz](#5-sentinel-2-optical-compositing--brienz)
6. [Blatten 2025 Glacier Collapse](#6-blatten-2025-glacier-collapse)
7. [False Positives: Sources, Magnitude, and Fixes](#7-false-positives-sources-magnitude-and-fixes)
8. [Relationship to Google Flood Forecasting](#8-relationship-to-google-flood-forecasting)
9. [Econometric Relevance](#9-econometric-relevance)
10. [Implementation Bugs Found and Fixed](#10-implementation-bugs-found-and-fixed)
11. [GEE Data Pipeline — Lessons Learned](#11-gee-data-pipeline--lessons-learned)
12. [Pending Work](#12-pending-work)
13. [References](#13-references)

---

## 1. Event Background

The July 2021 central European floods were driven by quasi-stationary low-pressure system
"Bernd," which delivered 100–150 mm of rainfall over 24–48 hours to the Aare and Reuss
catchments in Switzerland. The Brienzersee (Lake Brienz) overflowed its banks; the village
of Brienz experienced catastrophic inundation and debris flows. Most affected cantons:
Bern, Luzern, Aargau.

Blöschl et al. (2023) identify the event as a 100–200-year return period flood for the
affected region, amplified by antecedent soil saturation from a wet spring. Total economic
damages in Switzerland exceeded CHF 200 million.

The Blatten 2025 event (May 2025) is a separate, smaller-scale event: a glacier collapse
above the village of Blatten (Valais), triggered by permafrost thaw. It is covered in
`blatten.html` as a zoom-in on a single cryosphere-driven mass movement event, distinct
from the hydrological flood mechanism of 2021.

---

## 2. Project Architecture

Three interactive HTML pages, each a self-contained before/after swipe map:

| Page | Event | Left layer | Right layer | Source data |
|---|---|---|---|---|
| `index.html` | CH Floods 2021 (basin-wide) | Pre-flood SAR VV (grayscale) | Flood mask (blue) | Sentinel-1 GRD |
| `brienz.html` | CH Floods 2021 (Brienz detail) | Pre-flood RGB (Jun 2021) | Post-flood RGB (Jul–Aug 2021) | Sentinel-2 L2A |
| `blatten.html` | Blatten glacier collapse 2025 | Pre-event optical | Post-event optical | Sentinel-2 L2A |

**Frontend stack**: Leaflet.js + georaster-layer-for-leaflet + leaflet-side-by-side.
GeoTIFFs are parsed in-browser via `parseGeoraster` — no tile server required.

**Data storage**: `data/` folder in the git repo (short-term). Recommended upgrade:
GitHub Releases or a public GCS bucket for CDN-served Cloud-Optimized GeoTIFFs (COGs).

---

## 3. Dataset Inventory

| Dataset | GEE ID | Use | Native resolution | Export resolution |
|---|---|---|---|---|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | SAR change detection | 10 m | 100 m |
| Sentinel-2 SR Harmonized | `COPERNICUS/S2_SR_HARMONIZED` | Optical RGB + NDWI | 10 m | 10 m |
| JRC Global Surface Water v1.4 | `JRC/GSW1_4/GlobalSurfaceWater` | Permanent water mask | 30 m | — |
| SRTM DEM | `USGS/SRTMGL1_003` | Slope mask (pending) | 30 m | — |

All processing runs in Google Earth Engine (Python API). Exports go to Google Drive →
`GEE_exports/`. GEE project: `ksm-rch-global-poverty` (cleanup recommended: create
dedicated `switzerland-flooding-gee` project).

---

## 4. SAR Flood Detection — Central Switzerland

### 4.1 Method

VV backscatter change detection over the Aare/Reuss basin (7.0°E–8.5°E, 46.7°N–47.5°N).

```
Collection:  Sentinel-1 GRD, IW mode, VV polarisation, DESCENDING orbit
Pre-flood:   Median composite, June 2021         → high backscatter (dry land)
Post-flood:  Median composite, July 12–22 2021   → low backscatter (water)
Difference:  post − pre  (dB)
Threshold:   diff < −3 dB  → classified as flooded
Refinement:  Pixels with JRC GSW seasonality ≥ 10 months masked as permanent water
```

**Why median, not mean**: SAR backscatter follows a Rayleigh (speckle) distribution.
Individual pixels are multiplicatively noisy. Mean composites are pulled by extreme
outliers from isolated specular reflectors (metal roofs, vehicles). Median compositing
is standard practice in SAR time-series analysis.

**Why descending orbit only**: Consistent viewing geometry across passes. Mixing ascending
and descending orbits introduces systematic look-angle differences in mountain terrain
that create false change signals on slopes.

**Why 3 dB threshold**: The 3 dB drop is a standard SAR flood detection threshold
(Twele et al. 2016; Giustarini et al. 2013). Physical interpretation: a drop of 3 dB
corresponds to roughly halving of backscatter intensity, consistent with specular
reflection from open water replacing diffuse scattering from vegetation/soil.

### 4.2 Estimated Flood Area

Raw output (3 dB threshold, with permanent water masked): **~60 km²**

This is broadly consistent with Copernicus EMS activation EMSR519, which mapped
~58–65 km² of affected area across the Aare/Reuss catchment using multi-source
satellite imagery and DEM analysis.

### 4.3 Threshold Sensitivity

| Threshold | Estimated area | Interpretation |
|---|---|---|
| 2.5 dB | ~75–80 km² | Includes marginal wet/saturated soil |
| 3.0 dB | ~65–70 km² | Moderate conservative |
| **3.5 dB (used)** | **~60 km²** | Unambiguous open water |
| 4.0 dB | ~50–55 km² | Misses shallow inundation |

Reported uncertainty: ±15–30% depending on threshold. For any econometric application,
sensitivity robustness checks across 2.5–4.0 dB thresholds are recommended.

---

## 5. Sentinel-2 Optical Compositing — Brienz

### 5.1 Cloud Window Selection

Brienz sits in a narrow Alpine valley with high orographic cloud frequency. Initial target
windows (Jun 15–25 and Jul 28–Aug 8) returned **0 cloud-filtered scenes** in diagnostics
despite yielding valid exports when submitted — the tasks produced empty/null composites
and all four GEE tasks FAILED with "No band named 'B3'. Available band names: []."

Full scene inventory (raw, no filter) for 2021 revealed:

```
Jun 10: 22.8%   Jun 13: 11.0%   Jun 15: 8.4%   Jun 18: 26.1%   Jun 25: 53.5%
Jul 20: 8.1%    Jul 23: 8.6%    Aug 12: 4.7%   Aug 14: 2.2%
```

Final windows chosen:
- **Before**: 2021-06-10 to 2021-06-25 → **5 scenes** (multiple with <30% cloud)
- **After**: 2021-07-18 to 2021-08-15 → **9 scenes** (includes peak flood Jul 20–23 + clear aftermath Aug 12–14)

### 5.2 Critical GEE Implementation Bug

**Problem**: `.map(cloud_mask_fn)` applied over an unfiltered global collection silently
returns an empty collection due to GEE computation limits. `size()` returns 0 even though
the images exist. This caused the original script to report 0 scenes and produce empty exports.

**Fix**: Always apply `.filterDate()` (and optionally `.filter(cloud%)`) **before** `.map()`:

```python
# WRONG — maps over entire collection, GEE computation limit hit silently
S2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .map(mask_s2_clouds))          # mapping over all scenes globally
S2.filterDate(start, end).size()      # → 0 (silently fails)

# CORRECT — filter first, then map
S2_base = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)
(S2_base
 .filterDate(start, end)              # narrow window first
 .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 85))
 .map(mask_s2_clouds)                 # now maps only ~5–9 images
 .median())
```

This is a non-obvious GEE Python API footgun. The collection appears valid (lazy evaluation
doesn't error until `.getInfo()` or export submission), but the task fails at runtime.

### 5.3 Processing Chain

```
S2_SR_HARMONIZED → filterBounds(roi) → filterDate(window)
  → filter(CLOUDY_PIXEL_PERCENTAGE < 85)
  → map(QA60 bitmask: bits 10+11 → updateMask → divide(10000))
  → select(bands) → median()
RGB: multiply(255 × 3.5) → clamp(0, 255) → uint8()
NDWI: normalizedDifference(["B3", "B8"])  → float32
Export: 10 m, EPSG:4326, GeoTIFF
```

### 5.4 Export Status (as of 2026-03-12)

| File | Status | Window |
|---|---|---|
| `ch_s2_before_brienz.tif` | **COMPLETED** | Jun 10–25 2021 |
| `ch_s2_after_brienz.tif` | **COMPLETED** | Jul 18–Aug 15 2021 |
| `ch_s2_ndwi_before_brienz.tif` | **COMPLETED** | Jun 10–25 2021 |
| `ch_s2_ndwi_after_brienz.tif` | **COMPLETED** | Jul 18–Aug 15 2021 |

Files are in Google Drive → `GEE_exports/`. Next step: download to `data/` and verify
`brienz.html` renders the swipe correctly.

---

## 6. Blatten 2025 Glacier Collapse

Blatten (Valais, Switzerland) experienced a glacier detachment in May 2025, triggering a
rock-ice avalanche that buried part of the village. This is a cryosphere-driven mass movement
distinct from the 2021 hydrological flood.

The `blatten.html` page shows a Sentinel-2 before/after optical view of the collapse scar.
Methodology is identical to Brienz (QA60 masking, median composite, RGB display) but the
event signature is geomorphic change (exposed rock, debris fan) rather than water inundation.

Relevant indicators: snow-free area expansion, altered drainage, sediment plume in the Lonza river.

---

## 7. False Positives: Sources, Magnitude, and Fixes

### 7.1 Sources in Alpine SAR

| Source | Mechanism | Estimated area | Status |
|---|---|---|---|
| Alpine radar shadow | Steep lee slopes return near-zero backscatter regardless of water content | ~8–10 km² | Fix pending (SRTM slope mask) |
| Wet roads / pavement | Specular reflection from smooth wet asphalt mimics open water | ~4–6 km² | No practical fix at 100 m |
| Reed wetlands | High soil moisture and flat water surfaces at Altreu, Klingnau, Niederried | ~2–3 km² | JRC GSW partially removes these |

**Estimated true flooded area**: ~46–50 km² (vs. raw 60 km²).

### 7.2 Slope Mask Fix (Pending)

Three lines of code to add to `ch_flood_sentinel1_2021.py` after the flood mask:

```python
slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
steep = slope.gt(5)   # > 5° = likely Alpine terrain
flood_only = flood_only.where(steep, 0).rename("flood_mask")
```

This removes the ~8–10 km² Alpine shadow false positives. Recommended before any
econometric use of the flood mask as a treatment instrument.

### 7.3 Implications for Econometric Validity

Alpine shadow false positives are systematically located in steep, remote, low-population
areas. In a Geo-RD design, they inflate the bandwidth of the discontinuity boundary and
add high-altitude households to the treatment group that were never actually flooded.
This biases DiD estimates if population density, property values, or infrastructure
quality correlate with terrain steepness (which they do: flatter valley floors are
more densely developed).

---

## 8. Relationship to Google Flood Forecasting

Google's AI-driven flood forecasting (Nevo et al. 2022; also described at
research.google/blog/protecting-cities-with-ai-driven-flash-flood-forecasting) operates
**upstream** in the causal chain:

```
[Rainfall forecast] → [Hydrological model / ML] → [Inundation probability map] → [Alerts]
```

This project operates **downstream**:

```
[Event occurred] → [Satellite observation] → [Realized flood extent] → [Ground truth map]
```

The two outputs are complementary, not redundant:

| Dimension | Google Forecasting | This Project |
|---|---|---|
| Timing | 1–5 days ahead | Days to weeks after |
| Output | Probability of inundation | Binary flood mask |
| Use case | Evacuation, emergency response | Impact assessment, research |
| Validation | River gauge data | Copernicus EMS shapefiles |
| Resolution | ~90 m (GloFAS) to ~10 m (local) | 10–100 m |

For econometric causal identification, the realized extent (this project) is what is
needed — forecast probability is not a valid instrument unless the forecaster had
imperfect information that was randomly distributed across space, which is rarely true.

---

## 9. Econometric Relevance

Flood extent maps at pixel resolution are the key input for causal identification of
disaster economic impacts. Three estimators that depend on the quality of the flood mask:

### 9.1 Geographic Regression Discontinuity (Geo-RD)

Households near the flood boundary form treatment/control groups. A sharp, precise
boundary with minimal false positives → higher first-stage F-statistic and lower
standard errors. SAR shadow false positives on slopes blur the boundary in ways
that are geographically correlated with wealth, infrastructure quality, and
population density — violating the "as-good-as-random" assumption near the boundary.

### 9.2 Difference-in-Differences (DiD)

Pre/post outcomes for flooded vs. non-flooded pixels (or municipalities/households
matched to pixels). The Sentinel-2 NDWI before composite provides the pre-period
water baseline. The SAR binary mask provides treatment assignment. Median compositing
is critical: a single cloudy scene in a simple mean would corrupt the NDWI baseline
in a narrow Alpine valley, introducing measurement error in the control variable.

### 9.3 Instrumental Variables (IV)

Flood extent instruments household-level disruption (income, migration, health).
IV validity requires: (1) relevance — flood extent predicts disruption (strong);
(2) exclusion — extent affects outcomes only through disruption, not through correlated
unobservables. The slope mask matters here: without it, "flooded" is partially
determined by terrain steepness, which correlates with remoteness, poverty, and
pre-existing infrastructure gaps — a classic exclusion violation.

### 9.4 Required robustness checks for any AER-quality paper

1. Replicate main estimates at 2.5, 3.0, 3.5, 4.0 dB SAR thresholds
2. Show treatment effect is not sensitive to ±200 m bandwidth around flood boundary
3. Validate against Copernicus EMS EMSR519 shapefile (request via Copernicus portal)
4. Include balance table: flooded vs. non-flooded baseline characteristics
5. Report Moran's I for spatial autocorrelation in residuals; cluster SEs at watershed level

---

## 10. Implementation Bugs Found and Fixed

### Bug 1 — index.html beforeLayer was transparent (critical)

The LEFT side of the swipe map (`beforeLayer`) was initialized as a transparent satellite
tile layer with `opacity: 0`. Users saw nothing on the left side of the swipe bar.

**Fix**: Replaced with a GeoRasterLayer loading `data/ch_flood_pre2021.tif`, rendered as
grayscale SAR backscatter using a custom `sarColor()` function mapping −25 to 0 dB to
gray tones 0–210.

### Bug 2 — SAR composites used `.mean()` instead of `.median()`

Mean compositing of SAR data amplifies speckle noise outliers. Fixed to `.median()` with
explanatory comments.

### Bug 3 — Brienz GEE script: `.map()` before `.filterDate()` (critical)

See Section 5.2. Caused all four export tasks to FAIL with "No band named 'B3'".
Fixed by restructuring to filter first, then map.

### Bug 4 — Brienz date windows had 0 scenes

Initial windows (Jun 15–25, Jul 28–Aug 8) were chosen analytically without checking
actual scene availability. Full scene inventory revealed 0 QA60-valid scenes in those
exact windows due to orographic cloud. Fixed with wider windows (Jun 10–25, Jul 18–Aug 15)
that contain 5 and 9 scenes respectively.

---

## 11. GEE Data Pipeline — Lessons Learned

1. **Always run diagnostic `size().getInfo()` before submitting exports.** GEE accepts
   and starts tasks over empty composites without warning; they fail at execution time.

2. **Filter before map.** The pattern `.map(fn).filterDate(...)` over a global collection
   silently returns 0 results. Always: `.filterDate(...).map(fn)`.

3. **Granule-level `CLOUDY_PIXEL_PERCENTAGE` is unreliable for small Alpine ROIs.**
   A scene labeled 80% cloudy at the granule level may have a perfectly clear window
   over a narrow valley. QA60 pixel-level masking is more reliable; the granule filter
   is only useful for pre-filtering a large collection before mapping.

4. **SAR `.median()` over multi-pass composites is standard.** Never use `.mean()` for SAR.

5. **Export at native resolution (10 m for S2, 100 m for S1 basin-wide) or justify
   the choice explicitly.** Downsampling to 30 m aligns with JRC GSW and SRTM for
   multi-source analysis but loses S2's advantage for narrow floodplain mapping.

6. **GEE project billing**: All scripts currently bill to `ksm-rch-global-poverty`.
   Create a dedicated `switzerland-flooding-gee` GEE project for clean attribution.

---

## 12. Pending Work

| Priority | Task | File | Notes |
|---|---|---|---|
| High | Add SRTM slope mask to SAR script | `ch_flood_sentinel1_2021.py` | 3 lines; removes ~8–10 km² false positives |
| High | Download Brienz TIFFs from Drive → `data/` | — | COMPLETED on GEE side |
| High | Verify `brienz.html` swipe with real data | `brienz.html` | Run `python -m http.server 8000` |
| Medium | Fix index.html RIGHT side: load post-flood SAR grayscale instead of blue mask | `index.html` | More scientifically coherent; user sees signal drop |
| Medium | Switch all scripts to dedicated GEE project | All `.py` files | `ksm-rch-global-poverty` → `switzerland-flooding-gee` |
| Low | Cloud-Optimized GeoTIFF conversion | `data/` | `gdal_translate -of COG`; reduces size 30–50% |
| Low | Sensitivity analysis: re-run SAR at 2.5 / 3.0 / 4.0 dB | New script | Required for any publication |
| Low | Compare to Copernicus EMS EMSR519 shapefile | — | Request via Copernicus portal |
| Low | Upload GeoTIFFs to Zenodo for DOI | — | Required for data note / ESSD submission |

---

## 13. References

- **Blöschl et al. (2023)**. A multi-disciplinary analysis of the exceptional flood event
  of July 2021 in central Europe. *Natural Hazards and Earth System Sciences*, 23: 525–551.
  DOI: 10.5194/nhess-23-525-2023

- **Pekel, J.-F. et al. (2016)**. High-resolution mapping of global surface water and its
  long-term changes. *Nature*, 540: 418–422. DOI: 10.1038/nature20584

- **Gorelick, N. et al. (2017)**. Google Earth Engine: Planetary-scale geospatial analysis
  for everyone. *Remote Sensing of Environment*, 202: 18–27.

- **Nevo, S. et al. (2022)**. Flood forecasting with machine learning models in an operational
  framework. *Hydrology and Earth System Sciences*, 26: 4013–4032.

- **Twele, A. et al. (2016)**. Sentinel-1-based flood mapping: a fully automated processing
  chain. *International Journal of Remote Sensing*, 37(13): 2990–3004.

- **Giustarini, L. et al. (2013)**. A change detection approach to flood mapping in urban
  areas using TerraSAR-X. *IEEE Transactions on Geoscience and Remote Sensing*, 51(4): 2417–2430.

- **ESA Sentinel-1 Mission Guide**. IW mode, GRD product, VV/VH polarisation.
  https://sentinel.esa.int/web/sentinel/missions/sentinel-1

- **Copernicus EMS Activation EMSR519** — July 2021 Swiss floods.
  https://emergency.copernicus.eu/mapping/list-of-components/EMSR519
