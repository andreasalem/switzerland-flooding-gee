# Data manifest — `data/`

Every raster in this directory is a Google Earth Engine export produced by a script in this
repository. Nothing here is an original data source: all files derive from Copernicus
Sentinel-1/2 collections in the GEE public catalog (accessed at export time via the
`earthengine-api` version pinned in `../requirements.txt`). Exports go to Google Drive
(folder `GEE_exports`) and are downloaded and committed manually.

| File | Size | Script | Source collection | Composite window | Scale | Committed |
|---|---|---|---|---|---|---|
| `ch_flood_pre2021.tif` | 14 MB | `ch_flood_sentinel1_2021.py` | `COPERNICUS/S1_GRD` (VV, dB) | 2021-06-01 → 2021-06-30 | 100 m | 2026-02-28 (`4304737`) |
| `ch_flood_post2021.tif` | 14 MB | `ch_flood_sentinel1_2021.py` | `COPERNICUS/S1_GRD` (VV, dB) | 2021-07-12 → 2021-07-22 | 100 m | 2026-02-28 (`4304737`) |
| `ch_flood_mask2021.tif` | 28 KB | `ch_flood_sentinel1_2021.py` | derived: VV backscatter drop → binary mask | pre vs. post windows above | 100 m | 2026-02-28 (`4304737`) |
| `ch_s2_before_brienz.tif` | 17 MB | `ch_brienz_sentinel2_rgb.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2021-06-10 → 2021-06-25 | 10 m | 2026-02-28 (`4304737`) |
| `ch_s2_after_brienz.tif` | 18 MB | `ch_brienz_sentinel2_rgb.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2021-07-18 → 2021-08-15 | 10 m | 2026-02-28 (`4304737`) |
| `ch_blatten_before.tif` | 1.5 MB | `ch_blatten_sentinel2.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | **TODO-verify — see below** | 10 m | 2026-03-12 (`9257e1d`) |
| `ch_blatten_after.tif` | 6.3 MB | `ch_blatten_sentinel2.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2025-06-01 → 2025-08-31 | 10 m | 2026-03-12 (`9257e1d`) |

## TODO-verify: `ch_blatten_before.tif`

`ch_blatten_sentinel2.py` now specifies a **summer 2024** before-window
(2024-07-15 → 2024-09-15; the earlier April 2025 window produced an over-exposed
snow/glacier composite). The committed TIFF predates that change (2026-03-12) and may still
be the April 2025 composite. **Re-run the script and replace this file before trusting the
"Summer 2024" label on `blatten.html`.**

## Reproduction

```bash
pip install -r ../requirements.txt
earthengine authenticate
EE_PROJECT=<your-ee-enabled-gcp-project> python ch_flood_sentinel1_2021.py
# then download from Google Drive: GEE_exports/ and place the .tif files here
```

Exports are deterministic given the collection, window, region, and scale in each script,
up to upstream reprocessing of the Sentinel archive by ESA/Google.
