# switzerland-flooding-gee

Satellite mapping of recent Swiss natural disasters with Google Earth Engine:

- **July 2021 floods** (Aare/Reuss catchments) — Sentinel-1 SAR backscatter change
  detection with a binary flood mask (`index.html`, `ch_flood_sentinel1_2021.py`)
- **Brienz (BE) flood, July 2021** — Sentinel-2 true-color before/after
  (`brienz.html`, `ch_brienz_sentinel2_rgb.py`)
- **Blatten (VS) glacier collapse, May 2025** — Sentinel-2 true-color before/after
  (`blatten.html`, `ch_blatten_sentinel2.py`)

Live pages: <https://andreasalem.github.io/switzerland-flooding-gee/overview.html>
Method details: [`METHODOLOGY.md`](METHODOLOGY.md)

Part of a PhD research agenda on disaster exposure: these hazard layers feed a
disaster-exposure → climate-referendum-voting project.

## Repository layout

| Path | What it is |
|---|---|
| `ch_flood_sentinel1_2021.py` | S1 VV composites (pre/post) + flood mask → 3 GeoTIFF exports |
| `ch_brienz_sentinel2_rgb.py` | S2 RGB composites for Brienz before/after → 2 exports |
| `ch_blatten_sentinel2.py` | S2 RGB composites for Blatten before/after → 2 exports |
| `check_brienz_coverage.py` | Diagnostic: scene availability / cloud-free coverage for the Brienz ROI |
| `gee_app_flood2021.js` | EE Code Editor version of the 2021 flood analysis. **Caveat:** uses mean compositing where the Python pipeline uses median; the Python pipeline is canonical. |
| `data/` | Committed GeoTIFF exports — provenance in [`data/MANIFEST.md`](data/MANIFEST.md) |
| `index.html`, `brienz.html`, `blatten.html`, `overview.html` | Leaflet swipe-map pages (GitHub Pages) |
| `vendor/` | Vendored `leaflet-side-by-side` plugin (the gh-pages CDN build is unversioned; vendoring pins it) |

## Reproducing the exports

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # earthengine-api, pinned
earthengine authenticate
export EE_PROJECT=<your-EE-enabled-Google-Cloud-project>   # defaults to the author's
python ch_flood_sentinel1_2021.py      # exports land in Google Drive: GEE_exports/
```

Each script prints its export tasks; monitor at <https://code.earthengine.google.com/tasks>,
then download the GeoTIFFs into `data/`. Collections, date windows, regions, and scales are
fixed in the scripts, so exports are reproducible up to upstream reprocessing of the
Sentinel archive.

The web pages are static: any HTTP server (`python3 -m http.server`) serves them locally.
All JS libraries are version-pinned (CDN) or vendored.

## Known issues / TODO

- `data/ch_blatten_before.tif` needs re-export with the summer-2024 window — see the
  TODO-verify note in [`data/MANIFEST.md`](data/MANIFEST.md).
- The pages fetch 14–18 MB uncompressed GeoTIFFs client-side; converting to
  cloud-optimized GeoTIFFs or pre-rendered PNG overlays would cut load times.

## License and attribution

Code: MIT. Page text, methodology docs, and derived rasters: CC BY 4.0 (see `LICENSE`).
Contains modified Copernicus Sentinel data (2021–2025). Basemaps on the pages are
© their respective providers (OpenStreetMap contributors; Esri World Imagery where used).
