"""Convert the release GeoTIFFs (data/*.tif) to small EPSG:3857-aligned web
overlays in assets/, consumed by the pages via L.imageOverlay.

Styling matches (or deliberately improves, per the 2026-08-27 audit) the retired
in-browser pixelValuesToColorFn logic:
  - SAR dB:   g = clip((v+25)/25, 0, 1) * 210, opaque; nodata transparent (PNG)
  - mask:     v > 0.5 -> (30,120,220, 178); else transparent (PNG)
  - RGB u8:   copied; transparent where nodata or ALL bands are 0 (cloud-masked
              pixels in the GEE export) — fixes the old `r === 0 -> transparent`
              bug that punched holes in legitimately dark pixels. Lossy WebP
              keeps the alpha channel at ~JPEG size.

All-band-0 / NaN pixels are masked to NaN BEFORE the warp so bilinear
resampling cannot bleed black into their neighbors.

Bounds are the warped image corners converted to EPSG:4326, so a linear
imageOverlay stretch on the Mercator map is geometrically exact; they are
written to assets/bounds.json and hardcoded in the three HTML pages.

Run from the repo root, after fetching the TIFFs (see data/MANIFEST.md):
    python render_overlays.py
"""
import json
import os
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from rasterio.transform import Affine
from PIL import Image

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "assets")
MAX_DIM = 3000

JOBS = [
    ("data/ch_flood_pre2021.tif",  "sar",  "flood2021_pre.png"),
    ("data/ch_flood_post2021.tif", "sar",  "flood2021_post.png"),
    ("data/ch_flood_mask2021.tif", "mask", "flood2021_mask.png"),
    ("data/ch_s2_before_brienz.tif", "rgb", "brienz_before.webp"),
    ("data/ch_s2_after_brienz.tif",  "rgb", "brienz_after.webp"),
    ("data/ch_blatten_before_summer2024.tif", "rgb", "blatten_before.webp"),
    ("data/ch_blatten_after.tif",  "rgb", "blatten_after.webp"),
]


def warp_bands(src, nbands, resampling):
    """Read nbands, mask nodata to NaN, warp to EPSG:3857. Returns (array, wgs_bounds)."""
    dst_crs = "EPSG:3857"
    t, w, h = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
    if max(w, h) > MAX_DIM:
        s = max(w, h) / MAX_DIM
        w2, h2 = max(1, round(w / s)), max(1, round(h / s))
        t = t * Affine.scale(w / w2, h / h2)
        w, h = w2, h2

    data = src.read(list(range(1, nbands + 1))).astype("float64")
    if src.nodata is not None:
        data[data == src.nodata] = np.nan
    if nbands >= 3:
        # GEE uint8 RGB exports carry no nodata tag; cloud-masked pixels are
        # written as 0 in every band — mask them before resampling
        allzero = (data == 0).all(axis=0)
        data[:, allzero] = np.nan

    out = np.full((nbands, h, w), np.nan, dtype="float64")
    for b in range(nbands):
        reproject(
            source=data[b], destination=out[b],
            src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
            dst_transform=t, dst_crs=dst_crs, dst_nodata=np.nan,
            resampling=resampling,
        )
    bounds_3857 = rasterio.transform.array_bounds(h, w, t)  # (w, s, e, n)
    wgs = transform_bounds(dst_crs, "EPSG:4326", *bounds_3857)
    return out, wgs


bounds_out = {}
for rel, kind, name in JOBS:
    with rasterio.open(os.path.join(REPO, rel)) as src:
        nb = 1 if kind in ("sar", "mask") else min(3, src.count)
        rs = Resampling.nearest if kind == "mask" else Resampling.bilinear
        arr, (west, south, east, north) = warp_bands(src, nb, rs)
    valid = ~np.isnan(arr).any(axis=0)
    if kind == "sar":
        v = arr[0]
        g = np.clip((v + 25.0) / 25.0, 0, 1) * 210.0
        g = np.nan_to_num(g).astype("uint8")
        rgba = np.dstack([g, g, g, np.where(valid, 255, 0).astype("uint8")])
    elif kind == "mask":
        m = np.nan_to_num(arr[0]) > 0.5
        rgba = np.zeros(arr[0].shape + (4,), dtype="uint8")
        rgba[m] = (30, 120, 220, 178)
    else:  # rgb, already display-scaled uint8 in the tif
        rgb = np.nan_to_num(np.clip(arr[:3], 0, 255)).astype("uint8")
        alpha = np.where(valid, 255, 0).astype("uint8")
        rgba = np.dstack([rgb[0], rgb[1], rgb[2], alpha])
    im = Image.fromarray(rgba, "RGBA")
    if name.endswith(".webp"):
        im.save(os.path.join(OUT, name), quality=82, method=6)
    else:
        im.save(os.path.join(OUT, name), optimize=True)
    bounds_out[name] = [[south, west], [north, east]]
    print(f"{name}: {rgba.shape[1]}x{rgba.shape[0]}  bounds SW={south:.5f},{west:.5f} NE={north:.5f},{east:.5f}")

with open(os.path.join(OUT, "bounds.json"), "w") as f:
    json.dump(bounds_out, f, indent=1)
print("done")
