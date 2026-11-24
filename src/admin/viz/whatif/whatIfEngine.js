/**
 * Flood What-If engine (D-199, D-200): a plain JavaScript copy of the Python benefit model.
 *
 *   levels, eventLoss, eyd  <- "Modelling Data from Web/scripts/benefit/module_b_eyd.py"
 *   curveKey, floodedShare  <- ".../baseline_risk.py"
 *   seawall, elevate        <- ".../module_c_projects.py" (Model.seawall, Model.elevate)
 *
 * Inputs are the per-building tiles written by ".../export_what_if.py". Every rule here must match
 * the Python; whatIfParity.test.js checks that against every Part 2 run (damage avoided within 1%).
 * Pure functions only: no DOM, no network, so the same code runs in the browser and in tests.
 */

export const CASES = {
  low: { stat: 'low', whole: false, shiftKey: 'low' },
  mid: { stat: 'mean', whole: false, shiftKey: 'mid' },
  high: { stat: 'high', whole: true, shiftKey: 'high' },
};
const CASE_NAMES = ['low', 'mid', 'high'];
const FLOOR_HEIGHT_FT = 10;

// ------------------------------------------------------------------ tile reading

/**
 * Read one tile (already gunzipped). Layout: "WIF1", uint32 header length, JSON header, column buffers.
 * @param {ArrayBuffer} buf
 * @returns {{n: number, origin: [number, number], cols: Record<string, Float32Array|Int32Array|Uint8Array>}}
 */
export function readTile(buf) {
  const u8 = new Uint8Array(buf);
  if (String.fromCharCode(u8[0], u8[1], u8[2], u8[3]) !== 'WIF1') throw new Error('Not a What-If tile');
  const h = new DataView(buf).getUint32(4, true);
  const head = JSON.parse(new TextDecoder().decode(u8.subarray(8, 8 + h)));
  const base = 8 + h;
  const cols = {};
  for (const c of head.columns) {
    const off = base + c.offset;
    // copy into aligned buffers (the data block starts at a multiple of 8, but be safe)
    if (c.type === 'f32') cols[c.name] = new Float32Array(buf.slice(off, off + c.count * 4));
    else if (c.type === 'i32') cols[c.name] = new Int32Array(buf.slice(off, off + c.count * 4));
    else cols[c.name] = new Uint8Array(buf.slice(off, off + c.count));
  }
  return { n: head.n, origin: head.origin, cols };
}

// ------------------------------------------------------------------ curves

/**
 * Prepare curves for fast lookup.
 * @param {Record<string, {x:number[], mean:number[], low:number[], high:number[], egm:boolean}>} curvesJson
 * @param {{occtype: string[], found_type: string[]}} lists
 */
export function prepareCurves(curvesJson, lists) {
  const has = (k) => Object.prototype.hasOwnProperty.call(curvesJson, k);
  // pair[occIndex][foundIndex][salt 0/1] -> {s, c} or null, as baseline_risk.curve_key
  const pair = lists.occtype.map((occ) => lists.found_type.map((found) => [false, true].map((salt) => {
    let o = occ;
    let w = 'fresh';
    if (salt) {
      if (found === 'P' && has(`${occ}-PIER|structure|salt`)) { o = `${occ}-PIER`; w = 'salt'; }
      else if (has(`${occ}|structure|salt`)) { o = occ; w = 'salt'; }
    }
    const s = curvesJson[`${o}|structure|${w}`];
    const c = curvesJson[`${o}|contents|${w}`];
    return s && c ? { s, c, egm: !!c.egm } : null;
  })));
  return { pair, res1: lists.occtype.map((o) => o.startsWith('RES1')) };
}

/** np.interp: straight line between points, held flat beyond the ends. */
export function interp(v, xs, ys) {
  const n = xs.length;
  if (v <= xs[0]) return ys[0];
  if (v >= xs[n - 1]) return ys[n - 1];
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (xs[m] <= v) lo = m; else hi = m;
  }
  const t = (v - xs[lo]) / (xs[hi] - xs[lo]);
  return ys[lo] + t * (ys[hi] - ys[lo]);
}

// ------------------------------------------------------------------ damage

/** Running maximum then the trapezoid rule over the storms (module_b_eyd.eyd). */
export function eydFromLosses(L, P) {
  let body = 0;
  let run = L[0];
  let prev = run;
  for (let j = 1; j < L.length; j += 1) {
    run = Math.max(run, L[j]);
    body += 0.5 * (prev + run) * (P[j - 1] - P[j]);
    prev = run;
  }
  return { body, tail: prev * P[P.length - 1] };
}

/**
 * Expected yearly damage for chosen rows of one tile under one scenario (module_b_eyd.compute).
 * @param {object} tile from readTile
 * @param {number[]} rows row indexes within the tile
 * @param {object} ctx {events: string[], P: number[], curves, shift: {low, mid, high}}
 * @param {object} [opt] {ffeAdd: number, coastalOff: (ev, row) => boolean}
 * @returns {{low: Float64Array, mid: Float64Array, high: Float64Array, tailLow: Float64Array, tailMid: Float64Array, tailHigh: Float64Array}}
 */
export function computeRows(tile, rows, ctx, opt = {}) {
  const c = tile.cols;
  const { events, P, curves, shift } = ctx;
  const ffeAdd = opt.ffeAdd || 0;
  const out = {};
  for (const k of CASE_NAMES) {
    out[k] = new Float64Array(rows.length);
    out[`tail${k[0].toUpperCase()}${k.slice(1)}`] = new Float64Array(rows.length);
  }
  const ne = events.length;
  if (opt.keepLosses) out.lossMid = new Float64Array(rows.length * ne);
  const L = { low: new Float64Array(ne), mid: new Float64Array(ne), high: new Float64Array(ne) };
  const wcs = events.map((e) => c[`wc_${e}`]);
  const wos = events.map((e) => c[`wo_${e}`]);
  for (let r = 0; r < rows.length; r += 1) {
    const i = rows[r];
    const ground = c.ground[i];
    const vs = c.val_struct[i];
    const vc = c.val_cont[i];
    const ve = (c.flags[i] & 1) === 1;
    const est = c.ffe_est[i] === 1;
    const occ = c.occ[i];
    const isRes1 = curves.res1[occ];
    const stories = c.stories[i];
    const pairs = curves.pair[occ][c.found[i]];
    for (let j = 0; j < ne; j += 1) {
      let coast = wcs[j][i];
      if (Number.isNaN(coast)) coast = -Infinity;
      let other = wos[j][i];
      if (Number.isNaN(other)) other = -Infinity;
      if (opt.coastalOff && opt.coastalOff(events[j], i)) coast = -Infinity;
      const w = Math.max(coast, other);
      const wet = w > ground;
      const pr = wet ? pairs[(coast >= other || ve) ? 1 : 0] : null;
      for (const k of CASE_NAMES) {
        if (!pr) { L[k][j] = 0; continue; }
        const cs = CASES[k];
        const ffe = c.ffe[i] + ffeAdd + (est ? shift[cs.shiftKey] : 0);
        const din = w - ffe;
        const fs = interp(din, pr.s.x, pr.s[cs.stat]);
        const fc = interp(din, pr.c.x, pr.c[cs.stat]);
        const baseC = pr.egm ? vs : vc;
        let share = 1;
        if (!cs.whole && !isRes1) share = Math.min(1, (1 + Math.floor(Math.max(din, 0) / FLOOR_HEIGHT_FT)) / stories);
        L[k][j] = (fs * vs + fc * baseC) * share;
      }
    }
    if (opt.keepLosses) for (let j = 0; j < ne; j += 1) out.lossMid[r * ne + j] = L.mid[j];
    for (const k of CASE_NAMES) {
      const { body, tail } = eydFromLosses(L[k], P);
      out[k][r] = body;
      out[`tail${k[0].toUpperCase()}${k.slice(1)}`][r] = tail;
    }
  }
  return out;
}

// ------------------------------------------------------------------ geometry (UTM 17N, metres)

/**
 * WGS84 / NAD83 longitude, latitude to UTM zone 17N (EPSG:26917), Krüger series (Karney 2011), GRS80.
 * Matches pyproj to well under 1 cm in Miami-Dade.
 */
export function toUtm17(lon, lat) {
  const a = 6378137;
  const f = 1 / 298.257222101;
  const k0 = 0.9996;
  const lon0 = (-81 * Math.PI) / 180;
  const n = f / (2 - f);
  const A = (a / (1 + n)) * (1 + (n * n) / 4 + (n ** 4) / 64);
  const al = [
    n / 2 - (2 / 3) * n * n + (5 / 16) * n ** 3,
    (13 / 48) * n * n - (3 / 5) * n ** 3,
    (61 / 240) * n ** 3,
  ];
  const phi = (lat * Math.PI) / 180;
  const lam = (lon * Math.PI) / 180 - lon0;
  const e = Math.sqrt(f * (2 - f));
  const t = Math.sinh(Math.atanh(Math.sin(phi)) - e * Math.atanh(e * Math.sin(phi)));
  const xi = Math.atan2(t, Math.cos(lam));
  const eta = Math.atanh(Math.sin(lam) / Math.sqrt(1 + t * t));
  let x = eta;
  let y = xi;
  for (let j = 1; j <= 3; j += 1) {
    x += al[j - 1] * Math.cos(2 * j * xi) * Math.sinh(2 * j * eta);
    y += al[j - 1] * Math.sin(2 * j * xi) * Math.cosh(2 * j * eta);
  }
  return [500000 + k0 * A * x, k0 * A * y];
}

function segSegDist2(ax, ay, bx, by, cx, cy, dx, dy) {
  // squared distance between segments AB and CD (0 if they cross)
  const orient = (px, py, qx, qy, rx, ry) => (qx - px) * (ry - py) - (qy - py) * (rx - px);
  const o1 = orient(ax, ay, bx, by, cx, cy);
  const o2 = orient(ax, ay, bx, by, dx, dy);
  const o3 = orient(cx, cy, dx, dy, ax, ay);
  const o4 = orient(cx, cy, dx, dy, bx, by);
  if (((o1 > 0 && o2 < 0) || (o1 < 0 && o2 > 0)) && ((o3 > 0 && o4 < 0) || (o3 < 0 && o4 > 0))) return 0;
  const pd = (px, py, qx, qy, rx, ry) => {
    const vx = rx - qx; const vy = ry - qy;
    const L2 = vx * vx + vy * vy;
    let u = L2 > 0 ? ((px - qx) * vx + (py - qy) * vy) / L2 : 0;
    u = Math.max(0, Math.min(1, u));
    const ex = qx + u * vx - px; const ey = qy + u * vy - py;
    return ex * ex + ey * ey;
  };
  return Math.min(pd(ax, ay, cx, cy, dx, dy), pd(bx, by, cx, cy, dx, dy), pd(cx, cy, ax, ay, bx, by), pd(dx, dy, ax, ay, bx, by));
}

/** Shortest distance from a point to a polyline (UTM). */
export function pointLineDist(x, y, line) {
  let best = Infinity;
  for (let k = 0; k + 1 < line.length; k += 1) {
    best = Math.min(best, segSegDist2(x, y, x, y, line[k][0], line[k][1], line[k + 1][0], line[k + 1][1]));
  }
  return Math.sqrt(best);
}

export function lineLength(line) {
  let s = 0;
  for (let k = 0; k + 1 < line.length; k += 1) s += Math.hypot(line[k + 1][0] - line[k][0], line[k + 1][1] - line[k][1]);
  return s;
}

/** Keys "ix_iy" of the tiles whose squares meet a box (UTM). */
export function tilesForBox(minx, miny, maxx, maxy, tileM) {
  const out = [];
  for (let ix = Math.floor(minx / tileM); ix <= Math.floor(maxx / tileM); ix += 1) {
    for (let iy = Math.floor(miny / tileM); iy <= Math.floor(maxy / tileM); iy += 1) out.push(`${ix}_${iy}`);
  }
  return out;
}

/** Tiles a seawall can reach: its box widened by the reach to the shore (2 km). */
export function seawallTileKeys(lineLonLat, man) {
  const u = lineLonLat.map(([lo, la]) => toUtm17(lo, la));
  const r = man.seawall.max_distance_to_shore_m;
  const xs = u.map((p) => p[0]); const ys = u.map((p) => p[1]);
  return tilesForBox(Math.min(...xs) - r, Math.min(...ys) - r, Math.max(...xs) + r, Math.max(...ys) + r, man.tile_m);
}

// ------------------------------------------------------------------ projects

export function makeContext(man, curvesJson) {
  return {
    events: man.events.map((e) => e.name),
    P: man.events.map((e) => e.annual_chance),
    curves: prepareCurves(curvesJson, man.lists),
    shift: man.range.ffe_shift_estimated_ft,
    man,
  };
}

function emptyResult() {
  return {
    buildingsAffected: 0, buildingsProtected: 0, residentsProtected: 0,
    before: { low: 0, mid: 0, high: 0 }, avoided: { low: 0, mid: 0, high: 0 },
    valueChangePublished: 0, valueBasePublished: 0, perBuilding: [],
  };
}

/**
 * Add one tile's rows to a result: baseline and project EYD by the same code, so untouched rows give 0.
 * Property value (published Miami discount scenario, D-187, assumption): value x (exp(beta x dRate) - 1),
 * dRate = change in (middle EYD + tail) / structure value x 1000; single-family and condo buildings only.
 */
function accumulate(res, tile, rows, ctx, opt, keepPer, key) {
  const protectedRows = [];
  if (!rows.length) return protectedRows;
  const c = tile.cols;
  const base = computeRows(tile, rows, ctx);
  const scen = computeRows(tile, rows, ctx, opt);
  const betas = ctx.man.property_value_published_miami || {};
  const segBeta = [null, betas.single_family?.beta_per_rate_unit, betas.condo?.beta_per_rate_unit];
  res.buildingsAffected += rows.length;
  for (let r = 0; r < rows.length; r += 1) {
    const i = rows[r];
    for (const k of CASE_NAMES) {
      res.before[k] += base[k][r];
      res.avoided[k] += base[k][r] - scen[k][r];
    }
    const red = base.mid[r] - scen.mid[r];
    if (red > 0) {
      res.buildingsProtected += 1;
      res.residentsProtected += c.residents[i];
      protectedRows.push(i);
    }
    const beta = segBeta[c.segment[i]];
    const vs = c.val_struct[i];
    if (beta != null && vs > 0) {
      const dRate = ((scen.mid[r] + scen.tailMid[r]) - (base.mid[r] + base.tailMid[r])) / vs * 1000;
      res.valueChangePublished += c.jv[i] * (Math.exp(beta * dRate) - 1);
      if (dRate !== 0) res.valueBasePublished += c.jv[i];
    }
    if (keepPer) res.perBuilding.push({ key, i, fd_id: c.fd_id[i], lon: c.lon[i], lat: c.lat[i], before: base.mid[r], after: scen.mid[r] });
  }
  return protectedRows;
}

/**
 * Seawall (Model.seawall): buildings with a coastal level, within 2 km of the shore, ground below the crest,
 * whose straight line to their nearest shoreline point passes within 5 m of the wall. For those, the coastal
 * level is removed in every storm whose highest coastal level (all coastal sources) is below the crest.
 * Water going around the ends is not modelled.
 * @param {Map<string, object>} tiles loaded tiles by key
 * @param {[number, number][]} lineLonLat
 * @param {number} crestFt ft NAVD88
 */
export function seawall(tiles, lineLonLat, crestFt, ctx, { keepPer = false } = {}) {
  const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
  const cfg = ctx.man.seawall;
  const wall = lineLonLat.map(([lo, la]) => toUtm17(lo, la));
  const tol2 = cfg.snap_tolerance_m ** 2;
  const reach = cfg.max_distance_to_shore_m;
  const xs = wall.map((p) => p[0]); const ys = wall.map((p) => p[1]);
  const minx = Math.min(...xs) - reach; const maxx = Math.max(...xs) + reach;
  const miny = Math.min(...ys) - reach; const maxy = Math.max(...ys) + reach;
  const res = emptyResult();
  const dists = [];
  let candidates = 0;
  let behindBefore = 0; let removedWater = 0; let removedCap = 0;
  for (const key of tilesForBox(minx, miny, maxx, maxy, ctx.man.tile_m)) {
    const tile = tiles.get(key);
    if (!tile) continue;
    const c = tile.cols;
    const [x0, y0] = tile.origin;
    const rows = [];
    for (let i = 0; i < tile.n; i += 1) {
      const x = c.x[i] + x0; const y = c.y[i] + y0;
      if (x < minx || x > maxx || y < miny || y > maxy) continue;
      if ((c.flags[i] & 2) === 0 || !(c.shore_dist[i] <= reach) || !(c.ground[i] < crestFt)) continue;
      candidates += 1;
      const sx = c.shore_x[i] + x0; const sy = c.shore_y[i] + y0;
      let hit = false;
      for (let k = 0; k + 1 < wall.length && !hit; k += 1) {
        hit = segSegDist2(x, y, sx, sy, wall[k][0], wall[k][1], wall[k + 1][0], wall[k + 1][1]) <= tol2;
      }
      if (!hit) continue;
      behindBefore += 1;
      // waterway rule (D-202): a canal, creek or inner waterway nearer than the coastal shoreline lets water around the wall
      if (cfg.inner_water_rule && c.inner_water && c.inner_water[i] < c.shore_dist[i]) { removedWater += 1; continue; }
      // safety cap: within 1 km of the wall (D-202)
      if (cfg.max_distance_from_wall_m && pointLineDist(x, y, wall) > cfg.max_distance_from_wall_m) { removedCap += 1; continue; }
      rows.push(i);
    }
    const ww = Object.fromEntries(ctx.events.map((e) => [e, c[`ww_${e}`]]));
    const coastalOff = (ev, i) => {
      const v = ww[ev][i];
      return Number.isNaN(v) || v < crestFt;
    };
    for (const i of accumulate(res, tile, rows, ctx, { coastalOff }, keepPer, key)) {
      dists.push(pointLineDist(c.x[i] + x0, c.y[i] + y0, wall));
    }
  }
  res.candidates = candidates;
  res.behindBeforeRules = behindBefore;
  res.removedByInnerWater = removedWater;
  res.removedByCapOnly = removedCap;
  // how far the protected buildings are from the wall: a check on the "behind the wall" rule (D-200)
  dists.sort((p, q) => p - q);
  res.protectedMedianDistM = dists.length ? dists[Math.floor(dists.length / 2)] : null;
  res.protectedShareFarM = dists.length ? dists.filter((d) => d > 300).length / dists.length : 0;
  res.lengthM = lineLength(wall);
  res.ms = typeof performance !== 'undefined' ? performance.now() - t0 : 0;
  return res;
}

/**
 * Building elevation (Model.elevate): the chosen buildings' first floor is raised by raiseFt.
 * @param {Map<string, object>} tiles
 * @param {{key: string, i: number}[]} picks rows to raise
 */
export function elevate(tiles, picks, raiseFt, ctx, { keepPer = false } = {}) {
  const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
  const byTile = new Map();
  for (const p of picks) {
    if (!byTile.has(p.key)) byTile.set(p.key, []);
    byTile.get(p.key).push(p.i);
  }
  const res = emptyResult();
  for (const [key, rows] of byTile) {
    const tile = tiles.get(key);
    if (tile) accumulate(res, tile, rows, ctx, { ffeAdd: raiseFt }, keepPer, key);
  }
  res.ms = typeof performance !== 'undefined' ? performance.now() - t0 : 0;
  return res;
}

/** Rows for a list of NSI building IDs. */
export function picksForIds(tiles, ids) {
  const want = new Set(ids);
  const out = [];
  for (const [key, tile] of tiles) {
    for (let i = 0; i < tile.n; i += 1) if (want.has(tile.cols.fd_id[i])) out.push({ key, i });
  }
  return out;
}

/** Point in polygon (lon/lat ring). */
export function inRing(lon, lat, ring) {
  let inside = false;
  for (let a = 0, b = ring.length - 1; a < ring.length; b = a, a += 1) {
    const [xa, ya] = ring[a]; const [xb, yb] = ring[b];
    if ((ya > lat) !== (yb > lat) && lon < ((xb - xa) * (lat - ya)) / (yb - ya) + xa) inside = !inside;
  }
  return inside;
}

/**
 * The N single-family homes (RES1) with the highest expected yearly damage today inside an area
 * (the Part 2 rule, D-197).
 */
export function topHomes(tiles, ring, n, ctx) {
  const cand = [];
  for (const [key, tile] of tiles) {
    const c = tile.cols;
    for (let i = 0; i < tile.n; i += 1) {
      if (!ctx.curves.res1[c.occ[i]] || !(c.eyd_mid[i] > 0)) continue;
      if (inRing(c.lon[i], c.lat[i], ring)) cand.push({ key, i, eyd: c.eyd_mid[i] });
    }
  }
  cand.sort((p, q) => q.eyd - p.eyd);
  const out = cand.slice(0, n);
  out.available = cand.length;
  out.ranked = cand;     // every candidate in order, for the explanation cards (D-204)
  return out;
}

// ------------------------------------------------------------------ money

export const SETTINGS = {
  seawall: { life: 50, maint: 0.01, unitCost: 3500, unit: 'ft' },
  elevation: { life: 30, maint: 0, unitCost: 254000, unit: 'home' },
  rates: { main: 0.07, sensitivity: 0.03 },
};

export function annuity(years, rate) {
  return (1 - (1 + rate) ** -years) / rate;
}

/** Benefit per dollar: present value of losses avoided / (cost + present value of maintenance). */
export function benefitPerDollar(kind, avoidedPerYear, cost, rate) {
  const s = SETTINGS[kind];
  if (!(cost > 0)) return NaN;
  const af = annuity(s.life, rate);
  return (avoidedPerYear * af) / (cost * (1 + s.maint * af));
}

// ------------------------------------------------------------------ placing a drawn wall on the shoreline

function along(lineUtm) {
  const cum = [0];
  for (let k = 0; k + 1 < lineUtm.length; k += 1) {
    cum.push(cum[k] + Math.hypot(lineUtm[k + 1][0] - lineUtm[k][0], lineUtm[k + 1][1] - lineUtm[k][1]));
  }
  return cum;
}

function nearestOnLine(x, y, lineUtm, cum) {
  let best = { d: Infinity, s: 0 };
  for (let k = 0; k + 1 < lineUtm.length; k += 1) {
    const [ax, ay] = lineUtm[k]; const [bx, by] = lineUtm[k + 1];
    const vx = bx - ax; const vy = by - ay;
    const L2 = vx * vx + vy * vy;
    const u = L2 > 0 ? Math.max(0, Math.min(1, ((x - ax) * vx + (y - ay) * vy) / L2)) : 0;
    const d = Math.hypot(ax + u * vx - x, ay + u * vy - y);
    if (d < best.d) best = { d, s: cum[k] + u * (cum[k + 1] - cum[k]) };
  }
  return best;
}

function pointAtUtm(lineUtm, cum, s) {
  let k = 0;
  while (k + 2 < cum.length && cum[k + 1] < s) k += 1;
  const seg = cum[k + 1] - cum[k];
  const u = seg > 0 ? (s - cum[k]) / seg : 0;
  return [lineUtm[k][0] + u * (lineUtm[k + 1][0] - lineUtm[k][0]), lineUtm[k][1] + u * (lineUtm[k + 1][1] - lineUtm[k][1]), k, u];
}

/**
 * Place a drawn wall on FEMA's coastal shoreline (the transect baseline), as Part 2 placed real walls
 * (typical_projects_part2.Engine.wall_line): centred on the point of the shoreline nearest the middle of the
 * drawn line, with the drawn length, kept within the shoreline line. The "behind the wall" test only works
 * for a wall on that line: a wall drawn even 10 m out in the water is crossed by no building's line to the shore.
 * @param {[number, number][]} drawnLonLat
 * @param {[number, number][][]} shoreLonLat shoreline lines, lon/lat
 * @param {[number, number][][]} shoreUtm the same lines in UTM, vertex for vertex
 * @param {number} maxM farthest the wall may be moved; beyond this it is left where drawn
 * @returns {{line: [number, number][], movedM: number} | null}
 */
export function snapToShore(drawnLonLat, shoreLonLat, shoreUtm, maxM) {
  if (drawnLonLat.length < 2 || !shoreUtm.length) return null;
  const du = drawnLonLat.map(([lo, la]) => toUtm17(lo, la));
  const dcum = along(du);
  const L = dcum[dcum.length - 1];
  const [mx, my] = pointAtUtm(du, dcum, L / 2);
  let best = null;
  shoreUtm.forEach((line, j) => {
    const cum = along(line);
    const n = nearestOnLine(mx, my, line, cum);
    if (!best || n.d < best.d) best = { ...n, j, cum };
  });
  if (!best || best.d > maxM) return null;
  const line = shoreUtm[best.j]; const ll = shoreLonLat[best.j]; const { cum } = best;
  const total = cum[cum.length - 1];
  const len = Math.min(L, total);
  const a = Math.min(Math.max(best.s - len / 2, 0), total - len);
  const b = a + len;
  const toLL = (s) => {
    const [, , k, u] = pointAtUtm(line, cum, s);
    return [ll[k][0] + u * (ll[k + 1][0] - ll[k][0]), ll[k][1] + u * (ll[k + 1][1] - ll[k][1])];
  };
  const out = [toLL(a)];
  for (let k = 0; k < cum.length; k += 1) if (cum[k] > a && cum[k] < b) out.push(ll[k]);
  out.push(toLL(b));
  return { line: out, movedM: best.d };
}


// ------------------------------------------------------------------ explanation layer (D-204)

/** UTM zone 17N (EPSG:26917) back to longitude, latitude; Krüger series, GRS80. Matches pyproj to under 1 cm. */
export function fromUtm17(x, y) {
  const a = 6378137;
  const f = 1 / 298.257222101;
  const k0 = 0.9996;
  const n = f / (2 - f);
  const A = (a / (1 + n)) * (1 + (n * n) / 4 + (n ** 4) / 64);
  const be = [n / 2 - (2 / 3) * n * n + (37 / 96) * n ** 3, (1 / 48) * n * n + (1 / 15) * n ** 3, (17 / 480) * n ** 3];
  const de = [2 * n - (2 / 3) * n * n - 2 * n ** 3, (7 / 3) * n * n - (8 / 5) * n ** 3, (56 / 15) * n ** 3];
  const xi = y / (k0 * A);
  const eta = (x - 500000) / (k0 * A);
  let xp = xi;
  let ep = eta;
  for (let j = 1; j <= 3; j += 1) {
    xp -= be[j - 1] * Math.sin(2 * j * xi) * Math.cosh(2 * j * eta);
    ep -= be[j - 1] * Math.cos(2 * j * xi) * Math.sinh(2 * j * eta);
  }
  const chi = Math.asin(Math.sin(xp) / Math.cosh(ep));
  let phi = chi;
  for (let j = 1; j <= 3; j += 1) phi += de[j - 1] * Math.sin(2 * j * chi);
  const lam = Math.atan2(Math.sinh(ep), Math.cos(xp));
  return [-81 + (lam * 180) / Math.PI, (phi * 180) / Math.PI];
}

export const REASONS = ['protected', 'overtopped', 'inner_water', 'bay_beyond_ends', 'beyond_1km', 'rain_only'];

/**
 * Why each flooding building near a wall is or is not protected: the same rule, in the same order, as
 * module_c_projects.Model.seawall_reasons (checked by whatIfParity.test.js).
 * @returns {{res: object, items: {key: string, i: number, reason: string, distWallM: number}[], counts: Record<string, number>}}
 */
export function seawallReasons(tiles, lineLonLat, crestFt, ctx) {
  const res = seawall(tiles, lineLonLat, crestFt, ctx, { keepPer: true });
  const reduced = new Set(res.perBuilding.filter((q) => q.before - q.after > 0).map((q) => `${q.key}|${q.i}`));
  const cfg = ctx.man.seawall;
  const wall = lineLonLat.map(([lo, la]) => toUtm17(lo, la));
  const tol2 = cfg.snap_tolerance_m ** 2;
  const reach = cfg.max_distance_to_shore_m;
  const cap = cfg.max_distance_from_wall_m || Infinity;
  const xs = wall.map((p) => p[0]); const ys = wall.map((p) => p[1]);
  const minx = Math.min(...xs) - reach; const maxx = Math.max(...xs) + reach;
  const miny = Math.min(...ys) - reach; const maxy = Math.max(...ys) + reach;
  const items = [];
  const counts = Object.fromEntries(REASONS.map((r) => [r, 0]));
  for (const key of tilesForBox(minx, miny, maxx, maxy, ctx.man.tile_m)) {
    const tile = tiles.get(key);
    if (!tile) continue;
    const c = tile.cols;
    const [x0, y0] = tile.origin;
    const wcs = ctx.events.map((e) => c[`wc_${e}`]);
    for (let i = 0; i < tile.n; i += 1) {
      const x = c.x[i] + x0; const y = c.y[i] + y0;
      if (x < minx || x > maxx || y < miny || y > maxy) continue;
      const dw = pointLineDist(x, y, wall);
      const sx = c.shore_x[i] + x0; const sy = c.shore_y[i] + y0;
      let cross = false;
      if (Number.isFinite(sx) && Number.isFinite(sy)) {
        for (let k = 0; k + 1 < wall.length && !cross; k += 1) {
          cross = segSegDist2(x, y, sx, sy, wall[k][0], wall[k][1], wall[k + 1][0], wall[k + 1][1]) <= tol2;
        }
      }
      let coastalWet = false;
      for (const w of wcs) if (w[i] > c.ground[i]) { coastalWet = true; break; }
      const sd = c.shore_dist[i];
      const inner = c.inner_water[i] < sd;
      const behind = cross && sd <= reach;
      let reason;
      if (!coastalWet) reason = 'rain_only';
      else if (inner) reason = 'inner_water';
      else if (!behind) reason = 'bay_beyond_ends';
      else if (dw > cap) reason = 'beyond_1km';
      else if (reduced.has(`${key}|${i}`)) reason = 'protected';
      else reason = 'overtopped';
      if (dw <= cap || reason === 'beyond_1km') {
        items.push({ key, i, reason, distWallM: dw });
        counts[reason] += 1;
      }
    }
  }
  return { res, items, counts };
}

/**
 * Storm-by-storm explanation for one building (middle damage curve): water level, whether it is above the
 * first floor, whether the project removes it, and the damage before and after.
 * @param {object} opt for a seawall {crestFt}, for elevation {raiseFt}
 */
export function explainBuilding(tile, i, ctx, opt) {
  const c = tile.cols;
  const before = computeRows(tile, [i], ctx, { keepLosses: true });
  let scenOpt = {};
  if (opt.raiseFt) scenOpt = { ffeAdd: opt.raiseFt };
  if (opt.crestFt != null && opt.protectedRow) {
    scenOpt = { coastalOff: (ev, j) => { const v = c[`ww_${ev}`][j]; return Number.isNaN(v) || v < opt.crestFt; } };
  }
  const after = computeRows(tile, [i], ctx, { ...scenOpt, keepLosses: true });
  const ne = ctx.events.length;
  const ffe = c.ffe[i] + (opt.raiseFt || 0);
  const storms = ctx.events.map((ev, j) => {
    const wc = c[`wc_${ev}`][i]; const wo = c[`wo_${ev}`][i]; const ww = c[`ww_${ev}`][i];
    const coast = Number.isNaN(wc) ? -Infinity : wc; const other = Number.isNaN(wo) ? -Infinity : wo;
    const level = Math.max(coast, other);
    const blocked = opt.crestFt != null ? (coast > -Infinity && (Number.isNaN(ww) || ww < opt.crestFt)) : false;
    return {
      ev, chance: ctx.P[j], level: Number.isFinite(level) ? level : null, source: coast >= other ? 'sea' : 'rain or canal',
      wet: level > c.ground[i], aboveFloorBefore: level > c.ffe[i], aboveFloorAfter: level > ffe,
      blocked: blocked && !!opt.protectedRow, overWall: opt.crestFt != null && coast > -Infinity && !(Number.isNaN(ww) || ww < opt.crestFt),
      lossBefore: before.lossMid[j], lossAfter: after.lossMid[j],
    };
  });
  return { storms, eydBefore: before.mid[0], eydAfter: after.mid[0], ne };
}
