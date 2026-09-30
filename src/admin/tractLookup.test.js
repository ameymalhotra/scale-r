import { describe, expect, it } from 'vitest';
import { buildTractIndex, lngLatToWebMercator } from './tractLookup.js';

const square = (minLng, minLat, maxLng, maxLat) => {
  const corners = [
    [minLng, minLat],
    [minLng, maxLat],
    [maxLng, maxLat],
    [maxLng, minLat],
    [minLng, minLat],
  ];
  return corners.map(([lng, lat]) => lngLatToWebMercator(lng, lat));
};

describe('lngLatToWebMercator', () => {
  it('matches known EPSG:3857 coordinates', () => {
    const [x, y] = lngLatToWebMercator(-80.19, 25.76);
    expect(x).toBeCloseTo(-8926709.97, 1);
    expect(y).toBeCloseTo(2969386.15, 1);
  });
});

describe('buildTractIndex', () => {
  // Esri JSON in Web Mercator, like public/censuscommunityresilience.geojson.
  const collection = {
    spatialReference: { wkid: 102100, latestWkid: 3857 },
    features: [
      {
        attributes: { GEOID: '12086000100' },
        // Outer ring plus a hole in the middle.
        geometry: { rings: [square(-80.3, 25.7, -80.2, 25.8), square(-80.26, 25.74, -80.24, 25.76)] },
      },
      {
        attributes: { STATE: '12', COUNTY: '86', TRACT: '200' },
        geometry: { rings: [square(-80.2, 25.7, -80.1, 25.8)] },
      },
    ],
  };
  const lookup = buildTractIndex(collection);

  it('returns the GEOID of the containing tract', () => {
    expect(lookup(-80.28, 25.72)).toBe('12086000100');
  });

  it('builds the GEOID from STATE/COUNTY/TRACT when GEOID is missing', () => {
    expect(lookup(-80.15, 25.75)).toBe('12086000200');
  });

  it('treats holes as outside the tract', () => {
    expect(lookup(-80.25, 25.75)).toBeNull();
  });

  it('returns null outside every tract or for missing coordinates', () => {
    expect(lookup(-81.5, 26.5)).toBeNull();
    expect(lookup(null, 25.7)).toBeNull();
  });

  it('works with plain lon/lat GeoJSON polygons too', () => {
    const plain = buildTractIndex({
      features: [
        {
          properties: { GEOID: '12086009900' },
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [-80.3, 25.7],
                [-80.3, 25.8],
                [-80.2, 25.8],
                [-80.2, 25.7],
                [-80.3, 25.7],
              ],
            ],
          },
        },
      ],
    });
    expect(plain(-80.25, 25.75)).toBe('12086009900');
  });
});
