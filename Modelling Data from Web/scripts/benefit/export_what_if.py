"""Admin Flood What-If, Part 1: per-building export for the browser engine (D-199).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/export_what_if.py

Exports only the buildings that are wet (water above ground) in at least one
of the five storms today. A building that is never wet has zero damage before
and after any seawall or elevation, so leaving it out cannot change a result.

Files (private admin data, D-095; written to a git-ignored folder, never to
src/ or public/):
  outputs/admin_data/what_if/manifest.json      tile index, constants, curve and category lists
  outputs/admin_data/what_if/curves.json        depth-damage curves (USACE, Stage 2)
  outputs/admin_data/what_if/overview.bin.gz    lon, lat, EYD (middle) of every exported building, for the map
  outputs/admin_data/what_if/tiles/X_Y.bin.gz   all engine inputs, 2 km x 2 km UTM grid squares
  outputs/admin_data/what_if/shoreline.geojson  FEMA 2027 coastal shoreline (transect baseline), for the 500 m check
  outputs/admin_data/what_if/rain_basins.geojson outline of the C-8 and C-9 subbasins (rainfall levels exist here only)

Binary layout of a .bin file (little endian, gzip-compressed on disk):
  4 bytes "WIF1", uint32 header length H, H bytes JSON header
  {"n": rows, "origin": [x0, y0], "columns": [{"name", "type", "offset", "count"}]},
  then the column buffers, each starting at a multiple of 8 bytes from the start
  of the data block. Types: f32, i32, u8. Missing water levels are NaN.

Fields per building (no owner names or personal fields; parcel fields are the
2026 just value allocated to the building and the single-family or condo
segment, both from the public tax roll and used only for the property value
scenario):
  fd_id; x, y (m, UTM 17N, offset from the tile origin) and lon, lat;
  shore_x, shore_y (nearest FEMA coastal shoreline point, same offsets), shore_dist;
  ground and first floor (ft NAVD88), ffe_est (1 = estimated floor: the low
  case adds 1 ft and the high case subtracts 1 ft, as in Module B);
  occ, found (indexes into the manifest lists), stories (capped at 60), flags
  (bit 0 FEMA 2027 zone VE, bit 1 has a coastal level for the seawall test,
  bit 2 in the C-8 or C-9 basin), val_struct, val_cont, residents, jv, segment
  (0 none, 1 single-family, 2 condo);
  for each storm (10%, 4%, 2%, 1%, 0.2%): wc (coastal level used for damage),
  wo (rainfall, canal or map level), ww (highest coastal level of all coastal
  sources, used only for "does the wall hold", as Module C);
  eyd_low/mid/high and eyd_tail_low/mid/high today (to check results).
"""
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import module_b_eyd as mb  # noqa: E402
from baseline_risk import load_curves  # noqa: E402
from progress import Progress  # noqa: E402

OUT = paths.ADMIN_WHAT_IF_DIR
TILE_M = 2000.0
TO_LL = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
SEGS = {"001": 1, "004": 2}
P = None


def pack(cols, n, origin):
    """cols: list of (name, numpy array). Returns the bytes of one .bin file."""
    meta, blobs, off = [], [], 0
    for name, a in cols:
        a = np.ascontiguousarray(a)
        t = {np.dtype("float32"): "f32", np.dtype("int32"): "i32", np.dtype("uint8"): "u8"}[a.dtype]
        b = a.astype(a.dtype.newbyteorder("<"), copy=False).tobytes()
        pad = (-off) % 8
        blobs.append(b"\0" * pad)
        off += pad
        meta.append({"name": name, "type": t, "offset": off, "count": int(a.size)})
        blobs.append(b)
        off += len(b)
    head = json.dumps({"n": int(n), "origin": origin, "columns": meta}, separators=(",", ":")).encode()
    head += b" " * ((-(8 + len(head))) % 8)
    return b"WIF1" + np.uint32(len(head)).astype("<u4").tobytes() + head + b"".join(blobs)


def unpack(buf):
    """Reader used by the round-trip check (mirrors the browser reader)."""
    assert buf[:4] == b"WIF1"
    h = int(np.frombuffer(buf[4:8], "<u4")[0])
    head = json.loads(buf[8:8 + h])
    base = 8 + h
    dt = {"f32": "<f4", "i32": "<i4", "u8": "u1"}
    return head, {c["name"]: np.frombuffer(buf, dt[c["type"]], c["count"], base + c["offset"]) for c in head["columns"]}


def build():
    P.start("load Module A, B, coefficients")
    A = mb.load_a()
    B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id"] + [f"eyd_{k}_{c}" if k else f"eyd_{c}"
                                                                     for k in ("", "tail") for c in ("low", "mid", "high")])
    assert (A.fd_id.to_numpy() == B.fd_id.to_numpy()).all()
    C = pd.read_parquet(paths.MODULE_D_COEF_PARQUET, columns=["fd_id", "segment", "jv_alloc"]).set_index("fd_id")
    IW = pd.read_parquet(paths.INNER_WATER_PARQUET, columns=["fd_id", "inner_water_dist_m"]).set_index("fd_id").inner_water_dist_m
    P.end()
    ground = A.ground_elev_ft_navd88.to_numpy(float)
    wc, wo, ww = {}, {}, {}
    wet = np.zeros(len(A), bool)
    for ev in mb.EVENTS:
        w, _ = mb.levels(A, ev)
        wet |= w > ground
        coast = np.full(len(A), -np.inf)
        other = np.full(len(A), -np.inf)
        for name in mb.MAIN:
            v = np.nan_to_num(A[f"wse_{name}_{ev}"].to_numpy(float), nan=-np.inf)
            if name in mb.COASTAL:
                coast = np.fmax(coast, v)
            else:
                other = np.fmax(other, v)
        allc = np.full(len(A), -np.inf)
        for name in mb.COASTAL:
            allc = np.fmax(allc, np.nan_to_num(A[f"wse_{name}_{ev}"].to_numpy(float), nan=-np.inf))
        wc[ev], wo[ev], ww[ev] = (np.where(np.isfinite(v), v, np.nan) for v in (coast, other, allc))
    has_coastal = np.zeros(len(A), bool)
    for name in mb.COASTAL:
        has_coastal |= A[f"wse_{name}_p002"].notna().to_numpy()
    k = np.flatnonzero(wet)
    dry = A.loc[~wet, ["fd_id", "lon", "lat", "x_utm", "y_utm", "occtype", "sqft", "residents_night", "ground_elev_ft_navd88"]].reset_index(drop=True)
    P.log(f"buildings: {len(A)}; wet in at least one storm: {len(k)}")
    A, B = A.iloc[k].reset_index(drop=True), B.iloc[k].reset_index(drop=True)
    wc, wo, ww = ({e: d[e][k] for e in mb.EVENTS} for d in (wc, wo, ww))
    has_coastal = has_coastal[k]
    occs = sorted(A.occtype.unique())
    founds = sorted(A.found_type.unique())
    seg = A.fd_id.map(C.segment).map({"single_family": 1, "condo": 2}).fillna(0).astype("uint8").to_numpy()
    jv = A.fd_id.map(C.jv_alloc).fillna(0).to_numpy()
    flags = (A.zone27.eq("VE").to_numpy().astype(np.uint8) | (has_coastal.astype(np.uint8) << 1) |
             (A.basin.isin(["C-8", "C-9"]).to_numpy().astype(np.uint8) << 2))
    x, y = A.x_utm.to_numpy(), A.y_utm.to_numpy()
    ix, iy = np.floor(x / TILE_M).astype(int), np.floor(y / TILE_M).astype(int)
    f32 = lambda v: np.asarray(v, dtype=np.float32)
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "tiles").glob("*.bin.gz"):
        old.unlink()
    tiles = []
    keys = pd.Series(list(zip(ix, iy)))
    groups = keys.groupby(keys).groups
    P.start("write tiles", total=len(groups))
    raw_total = 0
    for n, ((tx, ty), idx) in enumerate(groups.items(), 1):
        i = np.asarray(idx)
        x0, y0 = tx * TILE_M, ty * TILE_M
        cols = [("fd_id", A.fd_id.to_numpy()[i].astype(np.int32)),
                ("x", f32(x[i] - x0)), ("y", f32(y[i] - y0)),
                ("lon", f32(A.lon.to_numpy()[i])), ("lat", f32(A.lat.to_numpy()[i])),
                ("shore_x", f32(A.shore_x.to_numpy()[i] - x0)), ("shore_y", f32(A.shore_y.to_numpy()[i] - y0)),
                ("shore_dist", f32(A.shore_dist_m.to_numpy()[i])),
                ("ground", f32(A.ground_elev_ft_navd88.to_numpy()[i])), ("ffe", f32(A.ffe_ft_navd88.to_numpy()[i])),
                ("ffe_est", (A.ffe_estimated.to_numpy()[i] == 1).astype(np.uint8)),
                ("occ", A.occtype.map({o: j for j, o in enumerate(occs)}).to_numpy()[i].astype(np.uint8)),
                ("found", A.found_type.map({o: j for j, o in enumerate(founds)}).to_numpy()[i].astype(np.uint8)),
                ("stories", A.stories.to_numpy()[i].astype(np.uint8)), ("flags", flags[i]),
                ("val_struct", f32(A.val_struct.to_numpy()[i])), ("val_cont", f32(A.val_cont.to_numpy()[i])),
                ("residents", f32(A.residents_night.to_numpy()[i])), ("jv", f32(jv[i])), ("segment", seg[i]),
                ("sqft", f32(A.sqft.to_numpy()[i])),
                ("inner_water", f32(A.fd_id.map(IW).to_numpy()[i]))]   # nearest canal, creek or inner waterway, m (D-202)
        for ev in mb.EVENTS:
            cols += [(f"wc_{ev}", f32(wc[ev][i])), (f"wo_{ev}", f32(wo[ev][i])), (f"ww_{ev}", f32(ww[ev][i]))]
        for c in ("low", "mid", "high"):
            cols += [(f"eyd_{c}", f32(B[f"eyd_{c}"].to_numpy()[i])), (f"eyd_tail_{c}", f32(B[f"eyd_tail_{c}"].to_numpy()[i]))]
        buf = pack(cols, len(i), [x0, y0])
        raw_total += len(buf)
        gz = gzip.compress(buf, 6)
        name = f"{tx}_{ty}.bin.gz"
        (OUT / "tiles" / name).write_bytes(gz)
        lo, la = A.lon.to_numpy()[i], A.lat.to_numpy()[i]
        sq = [TO_LL.transform(cx, cy) for cx, cy in ((x0, y0), (x0 + TILE_M, y0), (x0 + TILE_M, y0 + TILE_M), (x0, y0 + TILE_M))]
        tiles.append({"file": f"tiles/{name}", "ix": int(tx), "iy": int(ty), "n": int(len(i)), "bytes": len(gz), "raw_bytes": len(buf),
                      "square": [[round(lo_, 6), round(la_, 6)] for lo_, la_ in sq],
                      "bbox": [round(float(lo.min()), 5), round(float(la.min()), 5), round(float(lo.max()), 5), round(float(la.max()), 5)],
                      "eyd_mid": round(float(B.eyd_mid.to_numpy()[i].sum()))})
        if n % 50 == 0:
            P.update(n)
    P.end()
    ov = pack([("lon", f32(A.lon)), ("lat", f32(A.lat)), ("eyd_mid", f32(B.eyd_mid)), ("tile", (ix * 1000 + iy).astype(np.int32))],
              len(A), [0, 0])
    (OUT / "overview.bin.gz").write_bytes(gzip.compress(ov, 6))
    # buildings the model expects water never to reach (dry in all five storms): positions and a few details,
    # drawn as faint dots so every NSI building is visible (D-200); they cannot change any result
    (OUT / "dry").mkdir(exist_ok=True)
    for old in (OUT / "dry").glob("*.bin.gz"):
        old.unlink()
    dx, dy = np.floor(dry.x_utm / TILE_M).astype(int), np.floor(dry.y_utm / TILE_M).astype(int)
    dkeys = pd.Series(list(zip(dx, dy)))
    dry_tiles = []
    for (tx, ty), idx in dkeys.groupby(dkeys).groups.items():
        i = np.asarray(idx)
        buf = pack([("fd_id", dry.fd_id.to_numpy()[i].astype(np.int32)), ("lon", f32(dry.lon.to_numpy()[i])), ("lat", f32(dry.lat.to_numpy()[i])),
                    ("res1", dry.occtype.str.startswith("RES1").to_numpy()[i].astype(np.uint8)), ("sqft", f32(dry.sqft.to_numpy()[i])),
                    ("residents", f32(dry.residents_night.to_numpy()[i])), ("ground", f32(dry.ground_elev_ft_navd88.to_numpy()[i]))],
                   len(i), [tx * TILE_M, ty * TILE_M])
        gz = gzip.compress(buf, 6)
        (OUT / "dry" / f"{tx}_{ty}.bin.gz").write_bytes(gz)
        dry_tiles.append({"file": f"dry/{tx}_{ty}.bin.gz", "ix": int(tx), "iy": int(ty), "n": int(len(i)), "bytes": len(gz)})
    return A, B, occs, founds, tiles, raw_total, dry_tiles


def write_curves():
    cur = load_curves()
    out = {f"{o}|{c}|{w}": {"x": v["x"].round(4).tolist(), "mean": v["mean"].round(6).tolist(), "low": v["low"].round(6).tolist(),
                             "high": v["high"].round(6).tolist(), "egm": "EGM" in v["source"]} for (o, c, w), v in cur.items()}
    (OUT / "curves.json").write_text(json.dumps(out, separators=(",", ":")))
    return len(out)


def write_geo():
    import geopandas as gpd
    import water_levels as wl
    base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln")[["geometry"]].copy()
    base["geometry"] = base.geometry.simplify(2.0)
    base.to_crs(4326).to_file(OUT / "shoreline.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
    sb = wl.read(paths.FIRM_2027_EXTRACT, "S_Subbasins")
    sb = sb[sb.BASIN_DESC.isin(["C-8", "C-9"])]          # the layer also holds large regional basins
    parts = []
    for name, grp in sb.groupby("BASIN_DESC"):
        one = gpd.GeoDataFrame({"basin": [name]}, geometry=[grp.union_all().buffer(30).buffer(-30).simplify(25)], crs=sb.crs)
        parts.append(one.explode(index_parts=False))
    g = pd.concat(parts, ignore_index=True)
    g = g[g.area > 2e5]
    g.to_crs(4326).to_file(OUT / "rain_basins.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)


def check(A, B):
    """Round trip: read every tile back, rebuild the Module A frame and rerun Module B's compute on it."""
    P.start("round-trip check: rerun Module B on the exported tiles")
    man = json.loads((OUT / "manifest.json").read_text())
    occs, founds = man["lists"]["occtype"], man["lists"]["found_type"]
    parts = []
    t0 = time.time()
    for t in man["tiles"]:
        head, c = unpack(gzip.decompress((OUT / t["file"]).read_bytes()))
        d = {"fd_id": c["fd_id"], "ground_elev_ft_navd88": c["ground"].astype(float), "ffe_ft_navd88": c["ffe"].astype(float),
             "ffe_estimated": c["ffe_est"].astype(int), "occtype": np.array(occs)[c["occ"]],
             "found_type": np.array(founds)[c["found"]], "stories": c["stories"].astype(float),
             "zone27": np.where(c["flags"] & 1, "VE", "X"), "val_struct": c["val_struct"].astype(float),
             "val_cont": c["val_cont"].astype(float)}
        for ev in mb.EVENTS:
            d[f"wse_coastal_{ev}"] = c[f"wc_{ev}"].astype(float)
            d[f"wse_rain_{ev}"] = c[f"wo_{ev}"].astype(float)
            d[f"wse_map_{ev}"] = np.full(head["n"], np.nan)
        for k in ("low", "mid", "high"):
            d[f"x_eyd_{k}"] = c[f"eyd_{k}"].astype(float)
        parts.append(pd.DataFrame(d))
    R = pd.concat(parts, ignore_index=True)
    read_s = time.time() - t0
    cur = load_curves()
    E = mb.compute(R, cur)
    out = {"rows": int(len(R)), "seconds_to_read_all_tiles_python": round(read_s, 1)}
    for k in ("low", "mid", "high"):
        a, b = E[f"eyd_{k}"].to_numpy(), R[f"x_eyd_{k}"].to_numpy()
        out[f"eyd_{k}_total_relative_difference"] = float(abs(a.sum() - b.sum()) / b.sum())
        out[f"eyd_{k}_largest_building_difference_dollars"] = float(np.abs(a - b).max())
    P.end()
    return out


def main():
    global P
    P = Progress("admin what-if export")
    OUT.mkdir(parents=True, exist_ok=True)
    A, B, occs, founds, tiles, raw_total, dry_tiles = build()
    ncur = write_curves()
    P.start("shoreline and rain basin outlines")
    write_geo()
    P.end()
    import module_d_value_tax as md
    pub = md.published_coefficients()
    man = {"version": 1, "created": time.strftime("%Y-%m-%d"), "decision": "D-199",
           "about": "Private admin data (D-095). Buildings wet in at least one storm today; FEMA 2027 levels, Modules A and B.",
           "crs": "EPSG:26917 (UTM 17N, metres); x, y, shore_x, shore_y are offsets from each tile's origin",
           "tile_m": TILE_M, "buildings": int(len(A)),
           "events": [{"name": e, "annual_chance": float(p)} for e, p in zip(mb.EVENTS, mb.P)],
           "range": {"ffe_shift_estimated_ft": mb.CONFIG["range"]["ffe_shift_estimated_ft"], "curve_band": mb.CONFIG["range"]["curve_band"],
                     "whole_building_high": mb.CONFIG["range"]["whole_building_high"], "floor_height_ft": 10.0},
           "seawall": mb.CONFIG["projects"]["seawall"],
           "lists": {"occtype": occs, "found_type": founds, "segment": ["none", "single_family", "condo"]},
           "property_value_published_miami": {s: {"beta_per_rate_unit": v["beta_miami"]} for s, v in pub.items()},
           "files": {"curves": "curves.json", "overview": "overview.bin.gz", "shoreline": "shoreline.geojson",
                     "rain_basins": "rain_basins.geojson"},
           "tiles": tiles, "dry_tiles": dry_tiles}
    (OUT / "manifest.json").write_text(json.dumps(man, separators=(",", ":")))
    chk = check(A, B)
    size = lambda p: p.stat().st_size
    tb = np.array([t["bytes"] for t in tiles])
    S = {"buildings_total_module_a": 627252, "buildings_exported": int(len(A)),
         "dry_buildings": int(sum(t["n"] for t in dry_tiles)), "dry_tiles": len(dry_tiles),
         "dry_gz_total_mb": round(sum(t["bytes"] for t in dry_tiles) / 1e6, 2), "tiles": len(tiles), "curves": ncur,
         "tiles_gz_total_mb": round(tb.sum() / 1e6, 2), "tiles_raw_total_mb": round(raw_total / 1e6, 2),
         "tile_gz_kb": {"median": round(float(np.median(tb)) / 1e3, 1), "p90": round(float(np.percentile(tb, 90)) / 1e3, 1),
                        "max": round(float(tb.max()) / 1e3, 1)},
         "tile_buildings": {"median": int(np.median([t["n"] for t in tiles])), "max": int(max(t["n"] for t in tiles))},
         "overview_gz_mb": round(size(OUT / "overview.bin.gz") / 1e6, 2), "manifest_kb": round(size(OUT / "manifest.json") / 1e3, 1),
         "curves_kb": round(size(OUT / "curves.json") / 1e3, 1), "shoreline_kb": round(size(OUT / "shoreline.geojson") / 1e3, 1),
         "rain_basins_kb": round(size(OUT / "rain_basins.geojson") / 1e3, 1), "check": chk}
    (OUT / "export_summary.json").write_text(json.dumps(S, indent=2))
    print(json.dumps(S, indent=1))
    P.finish()


if __name__ == "__main__":
    main()
