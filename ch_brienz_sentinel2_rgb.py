"""
Title:   Sentinel-2 true-color before/after — Brienz Flood 2021
Event:   July 2021 central Switzerland floods (Aare / Brienzersee overflow)
Dataset: COPERNICUS/S2_SR_HARMONIZED (Level-2A Surface Reflectance)

Before window: 2021-06-10 to 2021-06-25
  - Jun 10: 22.8% cloud, Jun 13: 11.0%, Jun 15: 8.4%, Jun 18: 26.1%
  - Peak pre-flood greenness; ~2–3 weeks before rainfall onset
After window:  2021-07-18 to 2021-08-15
  - Jul 20: 8.1%, Jul 23: 8.6%, Aug 12: 4.7%, Aug 14: 2.2%
  - Peak and immediate aftermath of flood; sediment, brown water, altered channels

Key fix: filter by date BEFORE mapping cloud mask function.
  Mapping over unfiltered global collection exceeds GEE computation limits
  and silently returns an empty collection.

Exports to Google Drive → GEE_exports/:
  - ch_s2_before_brienz     : cloud-free true-color RGB, June 2021 (uint8)
  - ch_s2_after_brienz      : cloud-free true-color RGB, post-flood July–Aug 2021 (uint8)
  - ch_s2_ndwi_before_brienz: NDWI water index, before (float32)
  - ch_s2_ndwi_after_brienz : NDWI water index, after (float32)

Processing:
  Cloud masking:   QA60 bitmask (bits 10=opaque cloud, 11=cirrus)
  Compositing:     Median over window (minimises shadow/cloud artefacts)
  RGB scaling:     Reflectance (0–1 after ÷10000) × 3.5, gamma-corrected, clamped 0–255
  NDWI:            (B3 − B8) / (B3 + B8)  → water positive, land/veg negative

Caveats:
  - Conservative cloud mask (QA60 only; cloud shadows not explicitly masked)
  - Mixed pixel effects at 10 m resolution at water/land boundaries
  - Median composite may miss brief sub-week flood peaks
  - No field validation; optical view complements SAR flood mask

Run: python ch_brienz_sentinel2_rgb.py
Check: https://code.earthengine.google.com/tasks
"""

import ee
ee.Initialize(project="ksm-rch-global-poverty")

# Small ROI around Brienz — manageable file size at 10 m
roi = ee.Geometry.Rectangle([7.85, 46.68, 8.20, 46.84])

# ── Cloud masking for Sentinel-2 ─────────────────────────────────────────────
def mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
    return image.updateMask(cloud_mask).divide(10000)

# Base collection — no date or cloud filter yet
# IMPORTANT: apply filterDate BEFORE .map() to avoid GEE computation limits
S2_base = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)

BEFORE_START, BEFORE_END = "2021-06-10", "2021-06-25"
AFTER_START,  AFTER_END  = "2021-07-18", "2021-08-15"

def make_composite(start, end, bands):
    """Cloud-mask and median-composite a filtered S2 window."""
    return (S2_base
            .filterDate(start, end)                        # date filter FIRST
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 85))
            .map(mask_s2_clouds)
            .select(bands)
            .median())

# ── Diagnostic: confirm scene counts ─────────────────────────────────────────
print("\nAvailable cloud-filtered scenes per window:")
for label, start, end in [
    (f"Before ({BEFORE_START} – {BEFORE_END})", BEFORE_START, BEFORE_END),
    (f"After  ({AFTER_START}  – {AFTER_END})",  AFTER_START,  AFTER_END),
]:
    n = (S2_base
         .filterDate(start, end)
         .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 85))
         .size().getInfo())
    print(f"  {label}: {n} scenes")

# ── Composites ────────────────────────────────────────────────────────────────
before_rgb  = make_composite(BEFORE_START, BEFORE_END, ["B4", "B3", "B2"]).rename(["R", "G", "B"])
after_rgb   = make_composite(AFTER_START,  AFTER_END,  ["B4", "B3", "B2"]).rename(["R", "G", "B"])

before_ndwi = (make_composite(BEFORE_START, BEFORE_END, ["B3", "B8"])
               .normalizedDifference(["B3", "B8"])
               .rename("NDWI_before"))

after_ndwi  = (make_composite(AFTER_START,  AFTER_END,  ["B3", "B8"])
               .normalizedDifference(["B3", "B8"])
               .rename("NDWI_after"))

# ── Export as uint8 GeoTIFF — standard photo format ──────────────────────────
# Sentinel-2 SR reflectance (after ÷10000) is 0–1; scale to 0–255
before_uint8 = before_rgb.multiply(255 * 3.5).clamp(0, 255).uint8()
after_uint8  = after_rgb.multiply(255 * 3.5).clamp(0, 255).uint8()

export_params_rgb = dict(
    region    = roi,
    scale     = 10,          # native 10 m Sentinel-2 resolution
    crs       = "EPSG:4326",
    fileFormat= "GeoTIFF",
    folder    = "GEE_exports",
    maxPixels = 1e9,
)

export_params_ndwi = dict(
    region    = roi,
    scale     = 10,
    crs       = "EPSG:4326",
    fileFormat= "GeoTIFF",
    folder    = "GEE_exports",
    maxPixels = 1e9,
)

tasks = [
    ee.batch.Export.image.toDrive(image=before_uint8,  description="ch_s2_before_brienz",       **export_params_rgb),
    ee.batch.Export.image.toDrive(image=after_uint8,   description="ch_s2_after_brienz",        **export_params_rgb),
    ee.batch.Export.image.toDrive(image=before_ndwi,   description="ch_s2_ndwi_before_brienz",  **export_params_ndwi),
    ee.batch.Export.image.toDrive(image=after_ndwi,    description="ch_s2_ndwi_after_brienz",   **export_params_ndwi),
]

print("\nStarting export tasks...")
for t in tasks:
    t.start()
    print(f"  ✓ {t.config['description']} — started")

print("\nCheck: https://code.earthengine.google.com/tasks")
print("Files in Google Drive → GEE_exports/ when done (~5–15 min)")
print("Expected RGB size: ~5–20 MB each; NDWI: ~5–10 MB each")
