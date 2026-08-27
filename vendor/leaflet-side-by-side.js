/*
 * leaflet-side-by-side — local rewrite for this repo.
 * Based on digidem/leaflet-side-by-side v2.0.0 (MIT, © Digital Democracy);
 * divider/range CSS and the control API are preserved from upstream.
 *
 * Local changes (2026-08-27):
 *  1. Clips EVERY layer on each side. Upstream clipped only the last layer
 *     of each side's array, so a stacked side (e.g. SAR + flood mask) leaked
 *     across the divider.
 *  2. Works with any layer type — including L.ImageOverlay — by clipping the
 *     layer's PANE when the layer sits in a dedicated pane. ImageOverlay
 *     elements are positioned at the image corner, so clipping the element
 *     itself (upstream behaviour) mis-registers; panes sit at the map origin,
 *     where the rect() coordinates are valid. Pages must therefore create one
 *     pane per swipe side (e.g. 'sbs-left' / 'sbs-right') and pass
 *     `{pane: ...}` when constructing the overlays. Tile layers still work
 *     without a dedicated pane via getContainer().
 */
(function () {
  var css =
    ".leaflet-sbs-range{position:absolute;top:50%;width:100%;z-index:999;" +
    "-webkit-appearance:none;display:inline-block!important;vertical-align:middle;" +
    "height:0;padding:0;margin:0;border:0;background:rgba(0,0,0,0.25);" +
    "min-width:100px;cursor:pointer;pointer-events:none}" +
    ".leaflet-sbs-divider{position:absolute;top:0;bottom:0;left:50%;margin-left:-2px;" +
    "width:4px;background-color:#fff;pointer-events:none;z-index:999}" +
    ".leaflet-sbs-range::-moz-range-track{opacity:0}" +
    ".leaflet-sbs-range::-webkit-slider-thumb{" +
    "-webkit-appearance:none;margin:0;padding:0;background:#fff;height:40px;width:40px;" +
    "border-radius:20px;cursor:ew-resize;pointer-events:auto;border:1px solid #ddd;" +
    "background-image:url(\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAMAAAC5zwKfAAAABlBMVEV9fX3///+Kct39AAAAAnRSTlP/AOW3MEoAAAA9SURBVFjD7dehDQAwDANBZ/+l2wmKoiqR7pHRcaeaCxAIBAL/g7k9JxAIBAKBQCAQCAQC14H+MhAIBE4CD3fOFvGVBzhZAAAAAElFTkSuQmCC\");" +
    "background-position:50% 50%;background-repeat:no-repeat;background-size:40px 40px}" +
    ".leaflet-sbs-range::-moz-range-thumb{" +
    "margin:0;padding:0;background:#fff;height:40px;width:40px;" +
    "border-radius:20px;cursor:ew-resize;pointer-events:auto;border:1px solid #ddd;" +
    "background-image:url(\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAMAAAC5zwKfAAAABlBMVEV9fX3///+Kct39AAAAAnRSTlP/AOW3MEoAAAA9SURBVFjD7dehDQAwDANBZ/+l2wmKoiqR7pHRcaeaCxAIBAL/g7k9JxAIBAKBQCAQCAQC14H+MhAIBE4CD3fOFvGVBzhZAAAAAElFTkSuQmCC\");" +
    "background-position:50% 50%;background-repeat:no-repeat;background-size:40px 40px}" +
    ".leaflet-sbs-range:focus{outline:none!important}" +
    ".leaflet-sbs-range::-moz-focus-outer{border:0}";
  var style = document.createElement("style");
  style.innerHTML = css;
  document.head.appendChild(style);

  function asArray(a) { return a === undefined ? [] : Array.isArray(a) ? a : [a]; }

  // Drag latch lives on the control instance (not module globals) so a second
  // touchstart cannot overwrite the saved state, and uncancel is bound to
  // touchcancel too so an interrupted touch (incoming call, edge swipe) cannot
  // leave the map permanently un-pannable. Both mouse and touch events are
  // bound unconditionally: Leaflet 1.9 reports Browser.touch=true on desktops
  // with PointerEvent, so modality sniffing here picks the wrong event.
  function cancelMapDrag() {
    if (this._dragLatched) return;
    this._dragLatched = true;
    this._mapWasDragEnabled = this._map.dragging.enabled();
    this._mapWasTapEnabled = this._map.tap && this._map.tap.enabled();
    this._map.dragging.disable();
    this._map.tap && this._map.tap.disable();
  }
  function uncancelMapDrag(e) {
    if (!this._dragLatched) return;
    this._dragLatched = false;
    this._refocusOnMap(e);
    if (this._mapWasDragEnabled) this._map.dragging.enable();
    if (this._mapWasTapEnabled) this._map.tap.enable();
  }

  L.Control.SideBySide = L.Control.extend({
    options: { thumbSize: 42, padding: 0 },

    initialize: function (leftLayers, rightLayers, options) {
      this._leftLayers = asArray(leftLayers);
      this._rightLayers = asArray(rightLayers);
      L.setOptions(this, options);
    },

    getPosition: function () {
      var v = this._range.value;
      var offset = (0.5 - v) * (2 * this.options.padding + this.options.thumbSize);
      return this._map.getSize().x * v + offset;
    },

    setPosition: function () {},

    includes: L.Evented.prototype,

    addTo: function (map) {
      this.remove();
      this._map = map;
      var container = (this._container = L.DomUtil.create("div", "leaflet-sbs", map._controlContainer));
      this._divider = L.DomUtil.create("div", "leaflet-sbs-divider", container);
      var range = (this._range = L.DomUtil.create("input", "leaflet-sbs-range", container));
      range.type = "range";
      range.min = 0;
      range.max = 1;
      range.step = "any";
      range.value = 0.5;
      range.style.paddingLeft = range.style.paddingRight = this.options.padding + "px";
      this._addEvents();
      this._updateClip();
      return this;
    },

    remove: function () {
      if (!this._map) return this;
      this._clipTargets(this._leftLayers).concat(this._clipTargets(this._rightLayers))
        .forEach(function (el) { el.style.clip = ""; });
      this._removeEvents();
      L.DomUtil.remove(this._container);
      this._map = null;
      return this;
    },

    // Unique DOM elements to clip for a side: a dedicated pane when the layer
    // has one, else the tile container, else the layer element (last resort —
    // correct only for layers whose element sits at the map origin).
    _clipTargets: function (layers) {
      var map = this._map, seen = [], els = [];
      var defaultPanes = ["tilePane", "overlayPane", "shadowPane", "markerPane", "tooltipPane", "popupPane", "mapPane"];
      layers.forEach(function (layer) {
        var el = null;
        var pane = layer.options && layer.options.pane;
        if (pane && defaultPanes.indexOf(pane) === -1 && map.getPane(pane)) el = map.getPane(pane);
        else if (layer.getContainer) el = layer.getContainer();
        else if (layer.getElement) el = layer.getElement();
        if (el && seen.indexOf(el) === -1) { seen.push(el); els.push(el); }
      });
      return els;
    },

    _updateClip: function () {
      var map = this._map;
      if (!map) return;
      var nw = map.containerPointToLayerPoint([0, 0]);
      var se = map.containerPointToLayerPoint(map.getSize());
      var clipX = nw.x + this.getPosition();
      var dividerX = this.getPosition();
      this._divider.style.left = dividerX + "px";
      this.fire("dividermove", { x: dividerX });
      var clipLeft = "rect(" + [nw.y, clipX, se.y, nw.x].join("px,") + "px)";
      var clipRight = "rect(" + [nw.y, se.x, se.y, clipX].join("px,") + "px)";
      this._clipTargets(this._leftLayers).forEach(function (el) { el.style.clip = clipLeft; });
      this._clipTargets(this._rightLayers).forEach(function (el) { el.style.clip = clipRight; });
    },

    _addEvents: function () {
      var range = this._range, map = this._map;
      if (!map || !range) return;
      map.on("move zoomend", this._updateClip, this);
      map.on("layeradd layerremove", this._updateClip, this);
      L.DomEvent.on(range, "oninput" in range ? "input" : "change", this._updateClip, this);
      L.DomEvent.on(range, "mousedown touchstart", cancelMapDrag, this);
      L.DomEvent.on(range, "mouseup touchend touchcancel", uncancelMapDrag, this);
    },

    _removeEvents: function () {
      var range = this._range, map = this._map;
      if (range) {
        L.DomEvent.off(range, "oninput" in range ? "input" : "change", this._updateClip, this);
        L.DomEvent.off(range, "mousedown touchstart", cancelMapDrag, this);
        L.DomEvent.off(range, "mouseup touchend touchcancel", uncancelMapDrag, this);
      }
      if (map) {
        map.off("move zoomend", this._updateClip, this);
        map.off("layeradd layerremove", this._updateClip, this);
      }
    }
  });

  L.control.sideBySide = function (leftLayers, rightLayers, options) {
    return new L.Control.SideBySide(leftLayers, rightLayers, options);
  };
})();
