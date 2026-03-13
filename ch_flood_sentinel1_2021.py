"""
Flood extent mapping over Switzerland using Sentinel-1 SAR
Event: July 2021 floods (Aare / Reuss catchments)

Method: SAR backscatter change detection
  - Pre-flood image (dry conditions)  → high backscatter over land
  - Post-flood image (flooded)        → low backscatter over water
  - Large drop in VV backscatter = flooded area

Exports to Google Drive (folder: GEE_exports):
  - ch_flood_pre2021  : pre-flood Sentinel-1 VV composite (dB)
  - ch_flood_post2021 : post-flood Sentinel-1 VV composite (dB)
  - ch_flood_mask2021 : binary flood mask (1 = flooded, 0 = dry)

Run: python ch_flood_sentinel1_2021.py
Check progress: https://code.earthengine.google.com/tasks
"""

import ee

ee.Initialize(project="ksm-rch-global-poverty")

# ── Region of interest: central Switzerland (Aare / Reuss basin) ──────────────
# Covers cantons Bern, Luzern, Aargau — most affected in July 2021
roi = ee.Geometry.Rectangle([7.0, 46.7, 8.5, 47.5])

# ── Sentinel-1 GRD collection ─────────────────────────────────────────────────
# VV polarisation, Interferometric Wide swath, descending orbit
S1 = (ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(roi)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))
        .select("VV"))

# ── Pre-flood composite: June 2021 (dry, before peak flooding) ────────────────
# Median preferred over mean: reduces sensitivity to speckle outliers in SAR data
pre = (S1
       .filterDate("2021-06-01", "2021-06-30")
       .median()
       .rename("VV_pre"))

# ── Post-flood composite: 12–22 July 2021 (peak flooding) ────────────────────
# Median preferred over mean: more robust to speckle noise across passes
post = (S1
        .filterDate("2021-07-12", "2021-07-22")
        .median()
        .rename("VV_post"))

# ── Change detection: difference in backscatter (dB) ─────────────────────────
# Negative values = drop in backscatter = water / flooded area
diff = post.subtract(pre).rename("VV_diff")

# ── Flood mask: threshold drop > 3 dB (standard SAR flood threshold) ─────────
# 1 = flooded, 0 = not flooded
flood_mask = diff.lt(-3).rename("flood_mask")

# ── Refine: exclude permanent water bodies (JRC Global Surface Water) ─────────
permanent_water = (ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
                   .select("seasonality")
                   .gte(10))          # water present ≥10 months/year = permanent

flood_only = flood_mask.where(permanent_water, 0).rename("flood_mask")

# ── Print summary statistics ───────────────────────────────────────────────────
print("\nSentinel-1 SAR — 2021 Swiss flood detection")
print("Region: Aare/Reuss basin (central Switzerland)\n")

def print_mean(image, label):
    val = image.reduceRegion(
        reducer  = ee.Reducer.mean(),
        geometry = roi,
        scale    = 100,
        maxPixels= 1e9
    ).values().get(0).getInfo()
    print(f"  {label}: {val:.4f}")

print("Mean VV backscatter (dB):")
print_mean(pre,  "Pre-flood  (Jun 2021)")
print_mean(post, "Post-flood (Jul 2021)")
print_mean(diff, "Difference (post - pre)")

# Flooded area in km²
flood_area = flood_only.multiply(ee.Image.pixelArea()).reduceRegion(
    reducer  = ee.Reducer.sum(),
    geometry = roi,
    scale    = 100,
    maxPixels= 1e9
).get("flood_mask").getInfo()

print(f"\nEstimated flooded area: {flood_area / 1e6:.1f} km²")
print("(excludes permanent water bodies)\n")

# ── Export to Google Drive ─────────────────────────────────────────────────────
export_params = dict(
    region    = roi,
    scale     = 100,        # 100 m — finer than NO2, coarser than full S1 (10 m)
    crs       = "EPSG:4326",
    fileFormat= "GeoTIFF",
    folder    = "GEE_exports",
    maxPixels = 1e9,
)

tasks = [
    ee.batch.Export.image.toDrive(image=pre,        description="ch_flood_pre2021",  **export_params),
    ee.batch.Export.image.toDrive(image=post,       description="ch_flood_post2021", **export_params),
    ee.batch.Export.image.toDrive(image=flood_only, description="ch_flood_mask2021", **export_params),
]

print("Starting export tasks...")
for t in tasks:
    t.start()
    print(f"  ✓ {t.config['description']} — task started")

print("\nExports running. Check https://code.earthengine.google.com/tasks")
print("Files will appear in Google Drive → GEE_exports/ when done (~5–10 min).")
