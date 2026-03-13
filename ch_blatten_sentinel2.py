"""
Sentinel-2 true-color before/after — Blatten glacier collapse, May 2025
Lötschental valley, Valais, Switzerland

The hanging glacier and rock mass above Blatten village collapsed in May 2025,
burying part of the valley floor. Before: green valley + glacier.
After: grey debris field.

Exports to Google Drive → GEE_exports/:
  - ch_blatten_before : Sentinel-2 RGB, Apr 2025 (pre-collapse)
  - ch_blatten_after  : Sentinel-2 RGB, Jun–Jul 2025 (post-collapse)

Run: python ch_blatten_sentinel2.py
Check: https://code.earthengine.google.com/tasks
"""

import ee
ee.Initialize(project="ksm-rch-global-poverty")

# ROI: Lötschental valley around Blatten village
roi = ee.Geometry.Rectangle([7.72, 46.38, 7.95, 46.48])

# Cloud masking
def mask_clouds(image):
    qa = image.select("QA60")
    mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
    return image.updateMask(mask).divide(10000)

# Base collection — no date filter; apply filterDate BEFORE map to avoid GEE limits
S2_base = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)

BEFORE_START, BEFORE_END = "2025-03-01", "2025-05-14"
AFTER_START,  AFTER_END  = "2025-06-01", "2025-08-31"

def make_composite(start, end):
    return (S2_base
            .filterDate(start, end)
            .map(mask_clouds)
            .select(["B4", "B3", "B2"])
            .median())

# ── Diagnostic: scene counts ──────────────────────────────────────────────────
import datetime
raw = S2_base.filterDate("2025-01-01", "2025-08-31")
n_total = raw.size().getInfo()
print(f"Total S2 scenes Jan–Aug 2025: {n_total}")

for label, start, end in [
    (f"Before ({BEFORE_START}–{BEFORE_END})", BEFORE_START, BEFORE_END),
    (f"After  ({AFTER_START}–{AFTER_END})",   AFTER_START,  AFTER_END),
]:
    n = S2_base.filterDate(start, end).size().getInfo()
    print(f"  {label}: {n} scenes")

# ── Composites ────────────────────────────────────────────────────────────────
before = make_composite(BEFORE_START, BEFORE_END).rename(["R", "G", "B"])
after  = make_composite(AFTER_START,  AFTER_END).rename(["R", "G", "B"])

# Scale reflectance to uint8 (0-255) for display
before_uint8 = before.multiply(255 * 3.5).clamp(0, 255).uint8()
after_uint8  = after.multiply(255 * 3.5).clamp(0, 255).uint8()

export_params = dict(
    region    = roi,
    scale     = 10,           # native 10m Sentinel-2
    crs       = "EPSG:4326",
    fileFormat= "GeoTIFF",
    folder    = "GEE_exports",
    maxPixels = 1e9,
)

tasks = [
    ee.batch.Export.image.toDrive(image=before_uint8, description="ch_blatten_before", **export_params),
    ee.batch.Export.image.toDrive(image=after_uint8,  description="ch_blatten_after",  **export_params),
]

print("\nStarting export tasks...")
for t in tasks:
    t.start()
    print(f"  ✓ {t.config['description']} — started")

print("\nCheck: https://code.earthengine.google.com/tasks")
