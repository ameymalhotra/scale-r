import React, { useEffect, useRef, useState } from 'react';
import { buildMapboxLayers, geojsonBounds, mapLayerIds } from '../layers/layerConfig.js';
import { registerLayerSymbols } from '../layers/layerSymbols.js';
import { builtinColor, builtinPreviewStats, builtinVectorSource } from '../layers/builtinMap.js';
import { builtinDefinition } from '../layers/builtinRegistry.js';

const SOURCE_ID = 'preview-layer';
const MIAMI_DADE_CENTER = [-80.45, 25.6];

/** A small Mapbox map that draws one uploaded layer with the draft symbology. */
export default function LayerPreviewMap({ layer, geojson }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const drawnRef = useRef({ ids: [], data: null });
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    if (!token) {
      setError('Set VITE_MAPBOX_ACCESS_TOKEN to see the map preview.');
      return undefined;
    }
    let cancelled = false;
    let resizeObserver = null;
    import('mapbox-gl')
      .then(async ({ default: mapboxgl }) => {
        await import('mapbox-gl/dist/mapbox-gl.css').catch(() => null);
        if (cancelled || !containerRef.current) return;
        mapboxgl.accessToken = token;
        const map = new mapboxgl.Map({
          container: containerRef.current,
          style: 'mapbox://styles/mapbox/light-v11',
          center: MIAMI_DADE_CENTER,
          zoom: 8.3,
          attributionControl: false,
        });
        map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
        map.on('load', () => {
          if (cancelled) return;
          map.resize();
          setReady(true);
        });
        mapRef.current = map;
        if (typeof ResizeObserver !== 'undefined') {
          resizeObserver = new ResizeObserver(() => mapRef.current?.resize());
          resizeObserver.observe(containerRef.current);
        }
      })
      .catch(() => {
        if (!cancelled) setError('The map preview could not start in this browser.');
      });
    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of drawnRef.current.ids) if (map.getLayer(id)) map.removeLayer(id);
    drawnRef.current.ids = [];
    if (!layer || !geojson) {
      map.getSource(SOURCE_ID)?.setData?.({ type: 'FeatureCollection', features: [] });
      return;
    }

    const definition = builtinDefinition(layer.id);
    const vector = definition?.sourceType === 'vector';
    if (map.getSource(SOURCE_ID) && drawnRef.current.file !== layer.file) map.removeSource(SOURCE_ID);
    drawnRef.current.file = layer.file;
    if (!map.getSource(SOURCE_ID)) {
      map.addSource(SOURCE_ID, vector ? builtinVectorSource(definition, window.location.origin) : { type: 'geojson', data: geojson });
    } else if (!vector && drawnRef.current.data !== geojson) {
      map.getSource(SOURCE_ID).setData(geojson);
    }
    if (drawnRef.current.data !== geojson) {
      drawnRef.current.data = geojson;
      const bounds = vector ? [[-80.9, 25], [-80.1, 26]] : geojsonBounds(geojson);
      if (bounds) map.fitBounds(bounds, { padding: 24, maxZoom: 14, duration: 0 });
    }
    if (layer.geometry === 'point') registerLayerSymbols(map);
    for (const spec of buildMapboxLayers({ ...layer, visible: true }, SOURCE_ID)) {
      if (spec.type === 'fill' && layer.id === 'pred3pe') spec.paint['fill-color'] = builtinColor(layer, builtinPreviewStats(layer, geojson));
      map.addLayer(spec);
    }
    drawnRef.current.ids = mapLayerIds(layer);
  }, [ready, layer, geojson]);

  return (
    <div className="admin-layer-map">
      <div ref={containerRef} className="admin-layer-map__canvas" aria-label="Layer preview map" role="img" />
      {error && <p className="admin-muted admin-layer-map__message">{error}</p>}
      {!error && layer && !geojson && <p className="admin-muted admin-layer-map__message">Loading the layer data…</p>}
    </div>
  );
}
