// ============================================================
// Switzerland 2021 Flood Detection — GEE Earth Engine App
// Sentinel-1 SAR change detection · Aare/Reuss basin
//
// HOW TO USE:
//   1. Open https://code.earthengine.google.com
//   2. Paste this entire script into the editor
//   3. Click "Run" to preview
//   4. Click "Apps" → "New App" to publish publicly
// ============================================================

// ── Region & Data ────────────────────────────────────────────
var roi = ee.Geometry.Rectangle([7.0, 46.7, 8.5, 47.5]);

var S1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
  .select('VV');

var pre  = S1.filterDate('2021-06-01', '2021-06-30').mean();
var post = S1.filterDate('2021-07-12', '2021-07-22').mean();
var diff = post.subtract(pre);

var permanentWater = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
  .select('seasonality').gte(10);

var floodMask = diff.lt(-3).where(permanentWater, 0).selfMask();

// ── Visualisation params ─────────────────────────────────────
var sarVis   = { min: -25, max: 0,   palette: ['000000', 'ffffff'] };
var floodVis = { min: 1,   max: 1,   palette: ['4a90d9'] };

// ── Split-panel map ──────────────────────────────────────────
var leftMap  = ui.Map();
var rightMap = ui.Map();

leftMap.addLayer(pre,       sarVis,   'Pre-flood VV (Jun 2021)');
leftMap.addLayer(floodMask, floodVis, 'Flood extent', true, 0.8);

rightMap.addLayer(post,      sarVis,   'Post-flood VV (Jul 2021)');
rightMap.addLayer(floodMask, floodVis, 'Flood extent', true, 0.8);

// Link maps so they pan/zoom together
var linker = ui.Map.Linker([leftMap, rightMap]);
leftMap.setCenter(7.75, 47.1, 9);

var splitPanel = ui.SplitPanel({
  firstPanel:  leftMap,
  secondPanel: rightMap,
  orientation: 'horizontal',
  wipe: true,   // ← this is the swipe bar
});

// ── Title & description panel ────────────────────────────────
var title = ui.Label('Switzerland — July 2021 Flood Detection', {
  fontSize: '18px', fontWeight: 'bold', margin: '8px 8px 2px 8px'
});

var subtitle = ui.Label(
  'Sentinel-1 SAR change detection · Aare/Reuss basin · ~60.8 km² detected', {
  fontSize: '12px', color: '#555', margin: '0 8px 6px 8px'
});

var desc = ui.Label(
  '← Drag the centre bar to compare pre-flood (Jun 2021) and post-flood (Jul 2021). ' +
  'Blue = detected flood extent (VV backscatter drop > 3 dB). Permanent water excluded.', {
  fontSize: '11px', color: '#777', margin: '0 8px 8px 8px'
});

// ── Legend ───────────────────────────────────────────────────
function makeRow(color, label) {
  var box = ui.Label({ style: {
    backgroundColor: color, padding: '8px', margin: '2px 6px 2px 0'
  }});
  var text = ui.Label(label, { fontSize: '11px', margin: '4px 0' });
  return ui.Panel([box, text], ui.Panel.Layout.flow('horizontal'));
}

var legend = ui.Panel({
  widgets: [
    ui.Label('Legend', { fontWeight: 'bold', fontSize: '12px', margin: '6px 0 4px 0' }),
    makeRow('#4a90d9', 'Detected flood extent'),
    makeRow('#ffffff', 'High backscatter (dry land)'),
    makeRow('#000000', 'Low backscatter (shadow / water)'),
  ],
  style: { margin: '0 8px 8px 8px' }
});

// ── Assemble UI ───────────────────────────────────────────────
var controlPanel = ui.Panel({
  widgets: [title, subtitle, desc, legend],
  style: { width: '320px' }
});

ui.root.clear();
ui.root.add(ui.Panel([
  controlPanel,
  splitPanel
], ui.Panel.Layout.flow('horizontal'), { stretch: 'both' }));
