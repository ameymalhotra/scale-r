// @vitest-environment node
import { SETTINGS, fromUtm17, annuity, benefitPerDollar, eydFromLosses, inRing, interp, lineLength, pointLineDist, prepareCurves, snapToShore, toUtm17 } from './whatIfEngine.js';

describe('What-If engine building blocks', () => {
  it('interpolates like numpy, held flat beyond the ends', () => {
    expect(interp(-1, [0, 1, 2], [0, 10, 20])).toBe(0);
    expect(interp(0.5, [0, 1, 2], [0, 10, 20])).toBe(5);
    expect(interp(9, [0, 1, 2], [0, 10, 20])).toBe(20);
  });

  it('applies the running maximum and the trapezoid rule', () => {
    const P = [0.1, 0.04, 0.02, 0.01, 0.002];
    // a dip at the 2% storm is lifted to the 4% loss
    const { body, tail } = eydFromLosses([0, 100, 50, 200, 300], P);
    const expected = 0.5 * 100 * 0.06 + 0.5 * 200 * 0.02 + 0.5 * 300 * 0.01 + 0.5 * 500 * 0.008;
    expect(body).toBeCloseTo(expected, 10);
    expect(tail).toBeCloseTo(300 * 0.002, 10);
  });

  it('projects to UTM 17N like pyproj (under 1 cm)', () => {
    const ref = [[-80.13, 25.79, 587223.8863867444, 2852716.132674134],
      [-80.45, 25.47, 555287.8900246085, 2817105.9485869464],
      [-80.19, 25.95, 581098.8744246947, 2870397.5333791315]];
    for (const [lon, lat, x, y] of ref) {
      const [ux, uy] = toUtm17(lon, lat);
      expect(Math.abs(ux - x)).toBeLessThan(0.01);
      expect(Math.abs(uy - y)).toBeLessThan(0.01);
    }
  });

  it('chooses salt pier curves the way Module B does', () => {
    const c = (egm = false) => ({ x: [0, 1], mean: [0, 1], low: [0, 1], high: [0, 1], egm });
    const curves = { 'RES1-1SNB|structure|fresh': c(), 'RES1-1SNB|contents|fresh': c(),
      'RES1-1SNB-PIER|structure|salt': c(), 'RES1-1SNB-PIER|contents|salt': c(true) };
    const p = prepareCurves(curves, { occtype: ['RES1-1SNB'], found_type: ['P', 'S'] });
    expect(p.pair[0][0][1].egm).toBe(true);              // pier, salt: pier salt curve
    expect(p.pair[0][1][1].egm).toBe(false);             // slab, salt: no salt curve, fresh
    expect(p.res1[0]).toBe(true);
  });

  it('measures distance and point in area', () => {
    expect(pointLineDist(0, 5, [[-10, 0], [10, 0]])).toBeCloseTo(5);
    expect(inRing(0.5, 0.5, [[0, 0], [1, 0], [1, 1], [0, 1]])).toBe(true);
    expect(inRing(2, 0.5, [[0, 0], [1, 0], [1, 1], [0, 1]])).toBe(false);
  });

  it('computes benefit per dollar with FEMA lives and maintenance', () => {
    expect(annuity(50, 0.07)).toBeCloseTo(13.8007, 3);
    expect(annuity(30, 0.07)).toBeCloseTo(12.409, 3);
    // Part 2 S2: $228,964 a year, $1.76M, seawall -> 1.58 at 7%, 2.66 at 3%
    expect(benefitPerDollar('seawall', 228964, 1.76e6, 0.07)).toBeCloseTo(1.578, 2);
    expect(benefitPerDollar('seawall', 228964, 1.76e6, 0.03)).toBeCloseTo(2.66, 2);
    // the view's comparison rate is FEMA's 2023 and 2024 rate, 3.1% (D-210)
    expect(SETTINGS.rates).toEqual({ main: 0.07, sensitivity: 0.031 });
    expect(benefitPerDollar('seawall', 228964, 1.76e6, 0.031)).toBeCloseTo(2.62, 2);
  });

  it('places a wall drawn out in the water onto the shoreline, keeping its length', () => {
    // a straight east-west shoreline at lat 25.80, and a wall drawn about 30 m north of it
    const shoreLL = [[[-80.150, 25.80], [-80.140, 25.80], [-80.130, 25.80]]];
    const shoreUtm = shoreLL.map((l) => l.map(([lo, la]) => toUtm17(lo, la)));
    const drawn = [[-80.1425, 25.80027], [-80.1375, 25.80027]];
    const r = snapToShore(drawn, shoreLL, shoreUtm, 500);
    expect(r.movedM).toBeGreaterThan(25);
    expect(r.movedM).toBeLessThan(35);
    for (const [, la] of r.line) expect(la).toBeCloseTo(25.80, 6);
    const len = (l) => lineLength(l.map(([lo, la]) => toUtm17(lo, la)));
    expect(Math.abs(len(r.line) - len(drawn))).toBeLessThan(1);
    // too far away: left where drawn
    expect(snapToShore([[-80.14, 25.81], [-80.135, 25.81]], shoreLL, shoreUtm, 500)).toBeNull();
  });

  it('projects back from UTM 17N like pyproj (under 1 cm)', () => {
    for (const [lon, lat] of [[-80.13, 25.79], [-80.45, 25.47], [-80.19, 25.95]]) {
      const [x, y] = toUtm17(lon, lat);
      const [lo, la] = fromUtm17(x, y);
      expect(Math.abs(lo - lon) * 100000).toBeLessThan(0.01);   // degrees x 100 km, about metres
      expect(Math.abs(la - lat) * 111000).toBeLessThan(0.01);
    }
  });
});
