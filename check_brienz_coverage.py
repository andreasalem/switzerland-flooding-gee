"""
Diagnostic: find valid Sentinel-2 coverage for Brienz ROI
- Check current GEE task status
- Find which months/dates actually have cloud-free scenes
"""

import ee
import os
ee.Initialize(project=os.environ.get("EE_PROJECT", "flooding-506820"))

roi = ee.Geometry.Rectangle([7.85, 46.68, 8.20, 46.84])

# ── 1. Check running tasks ────────────────────────────────────────────────────
print("=== GEE Task Status ===")
tasks = ee.batch.Task.list()
brienz_tasks = [t for t in tasks if "brienz" in t.config.get("description", "").lower()]
if brienz_tasks:
    for t in brienz_tasks[:8]:
        desc  = t.config.get("description", "?")
        state = t.state
        print(f"  {desc}: {state}")
else:
    print("  (no Brienz tasks found in recent list)")

# ── 2. Find actual coverage: scan wider windows ───────────────────────────────
print("\n=== Sentinel-2 scene availability for Brienz ROI ===")
print("(cloud filter < 80%, QA60 cloud-masked)\n")

def mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
    return image.updateMask(cloud_mask).divide(10000)

S2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(mask_s2_clouds))

windows = [
    ("Apr 2021",       "2021-04-01", "2021-04-30"),
    ("May 2021",       "2021-05-01", "2021-05-31"),
    ("Jun 1–14 2021",  "2021-06-01", "2021-06-14"),
    ("Jun 15–25 2021", "2021-06-15", "2021-06-25"),  # target before window
    ("Jun 26–30 2021", "2021-06-26", "2021-06-30"),
    ("Jul 1–11 2021",  "2021-07-01", "2021-07-11"),
    ("Jul 12–27 2021", "2021-07-12", "2021-07-27"),  # peak flood
    ("Jul 28–Aug 8",   "2021-07-28", "2021-08-08"),  # target after window
    ("Aug 9–31 2021",  "2021-08-09", "2021-08-31"),
    ("Sep 2021",       "2021-09-01", "2021-09-30"),
    ("Oct 2021",       "2021-10-01", "2021-10-31"),
]

for label, start, end in windows:
    n = S2.filterDate(start, end).size().getInfo()
    marker = " ◄ target" if "15–25" in label or "Jul 28" in label else ""
    bar = "█" * n + "░" * max(0, 8 - n)
    print(f"  {label:<22} {bar}  {n} scenes{marker}")

# ── 3. Recommend best windows ─────────────────────────────────────────────────
print("\n=== Recommended windows (≥1 scene) ===")
best_before, best_after = None, None
for label, start, end in windows:
    n = S2.filterDate(start, end).size().getInfo()
    if n > 0:
        month = int(start[5:7])
        if month <= 6 and best_before is None:
            best_before = (label, start, end, n)
        elif month >= 7 and best_after is None:
            best_after = (label, start, end, n)

if best_before:
    print(f"  Best BEFORE: {best_before[0]}  ({best_before[3]} scenes)")
else:
    print("  No before scenes found — try relaxing cloud threshold or widening to May")
if best_after:
    print(f"  Best AFTER:  {best_after[0]}  ({best_after[3]} scenes)")
else:
    print("  No after scenes found — try Sep/Oct or relax cloud filter")
