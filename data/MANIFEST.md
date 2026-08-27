# Data manifest

Every raster is a Google Earth Engine export produced by a script in this repository.
Nothing here is an original data source: all files derive from Copernicus Sentinel-1/2
collections in the GEE public catalog (accessed at export time via the `earthengine-api`
version pinned in `../requirements.txt`).

**The GeoTIFFs live as [GitHub Release assets](https://github.com/andreasalem/switzerland-flooding-gee/releases/tag/data-2026-08-27),
not in the git tree** (migrated 2026-08-27; they were tracked in-tree until then, so they
remain in git history). The web pages do not read the TIFFs: they render pre-styled
PNG/JPEG overlays from `../assets/`, generated from these TIFFs by `../render_overlays.py`.

Release: `data-2026-08-27` — download any file with

```bash
gh release download data-2026-08-27 -p '<name>.tif' -D data/
```

| File | Size | Script | Source collection | Composite window | Scale | First committed |
|---|---|---|---|---|---|---|
| `ch_flood_pre2021.tif` | 14 MB | `ch_flood_sentinel1_2021.py` | `COPERNICUS/S1_GRD` (VV, dB) | 2021-06-01 → 2021-06-30 | 100 m | 2026-02-28 (`4304737`) |
| `ch_flood_post2021.tif` | 14 MB | `ch_flood_sentinel1_2021.py` | `COPERNICUS/S1_GRD` (VV, dB) | 2021-07-12 → 2021-07-22 | 100 m | 2026-02-28 (`4304737`) |
| `ch_flood_mask2021.tif` | 28 KB | `ch_flood_sentinel1_2021.py` | derived: VV backscatter drop → binary mask | pre vs. post windows above | 100 m | 2026-02-28 (`4304737`) |
| `ch_s2_before_brienz.tif` | 17 MB | `ch_brienz_sentinel2_rgb.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2021-06-10 → 2021-06-25 | 10 m | 2026-02-28 (`4304737`) |
| `ch_s2_after_brienz.tif` | 18 MB | `ch_brienz_sentinel2_rgb.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2021-07-18 → 2021-08-15 | 10 m | 2026-02-28 (`4304737`) |
| `ch_blatten_before.tif` | 1.6 MB | `ch_blatten_sentinel2.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | **superseded** April-2025 composite (over-exposed snow); kept for the record | 10 m | 2026-03-12 (`9257e1d`) |
| `ch_blatten_before_summer2024.tif` | 4.4 MB | `ch_blatten_sentinel2.py` windows, exported 2026-08-27 via `ee.Image.getDownloadURL` on project `flooding-506820` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2024-07-15 → 2024-09-15 | 10 m | release only |
| `ch_blatten_after.tif` | 6.3 MB | `ch_blatten_sentinel2.py` | `COPERNICUS/S2_SR_HARMONIZED` (B4/B3/B2) | 2025-06-01 → 2025-08-31 | 10 m | 2026-03-12 (`9257e1d`) |

The 2026-03-12 `ch_blatten_before.tif` TODO-verify is **resolved**: it was indeed the
over-exposed April-2025 composite (visually confirmed against the summer-2024 re-export,
2026-08-27), and `ch_blatten_before_summer2024.tif` replaces it everywhere
(see `../render_overlays.py`).

## Reproduction

All commands run from the **repository root**:

```bash
pip install -r requirements.txt
earthengine authenticate
EE_PROJECT=<your-ee-enabled-gcp-project> python ch_flood_sentinel1_2021.py
# then download from Google Drive: GEE_exports/ and place the .tif files in data/
# (or skip the re-export: gh release download data-2026-08-27 -D data/)
python render_overlays.py   # regenerates assets/ from data/*.tif
```

Exports are deterministic given the collection, window, region, and scale in each script,
up to upstream reprocessing of the Sentinel archive by ESA/Google.
