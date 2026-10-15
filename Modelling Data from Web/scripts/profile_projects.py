"""Steps 1-3: inventory, core-field profile, and evidence for the three
open decisions (corridor handling, muni/county scale, physical risk layer).

Reports only. Nothing is cleaned, dropped, or aggregated.
Usage:  python scripts/profile_projects.py            # human-readable to stdout
        python scripts/profile_projects.py --json     # also dump output/profile.json
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import (  # noqa: E402
    BASE, COST_COL, LAT_COL, LON_COL, MD_LAT_MAX, MD_LAT_MIN, MD_LON_MAX,
    MD_LON_MIN, PROJECT_CSV, SCALE_COL, YEAR_COL, ensure_output_dir,
    load_raw, load_typed,
)

RISK_WORDS = ["risk", "hazard", "flood", "surge", "elev", "expos", "inundat",
              "slr", "sea level", "storm", "vulnerab", "depth", "zone"]
# file names use product acronyms the column-name list would miss
FILE_RISK_WORDS = RISK_WORDS + ["nri", "fema", "nfip", "firm", "lidar", "dem",
                                "slosh", "sovi", "cre"]
GEOMETRY_WORDS = ["geom", "line", "length", "shape", "wkt", "polyline", "route",
                  "segment", "from", "to", "start", "end", "extent", "miles",
                  "feet", "path", "corridor", "tract", "block", "area", "polygon"]


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def inventory(raw, typed):
    section("STEP 1 - INVENTORY")
    print(f"file      : {PROJECT_CSV.relative_to(BASE)}")
    print(f"rows      : {len(raw)}")
    print(f"columns   : {len(raw.columns)}")
    print("\ncolumn dtypes (as stored on disk everything is text; inferred type"
          " is what pandas would pick with default parsing):")
    inferred = pd.read_csv(PROJECT_CSV, encoding="utf-8-sig")
    rows = []
    for c in raw.columns:
        rows.append({
            "column": c,
            "inferred_dtype": str(inferred[c].dtype),
            "n_null": int(raw[c].isna().sum()),
            "n_unique": int(raw[c].nunique(dropna=True)),
            "example": (raw[c].dropna().iloc[0][:48] if raw[c].notna().any() else ""),
        })
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n5 sample rows (transposed for readability):")
    with pd.option_context("display.max_colwidth", 90):
        print(raw.head(5).T.to_string())
    return {"n_rows": len(raw), "columns": rows}


def profile_cost(df):
    section("STEP 2a - INVESTMENT AMOUNT (Estimated_Cost)")
    c = df["cost_num"]
    unparsed = df[COST_COL].notna() & c.isna()
    print(f"unparseable as number : {int(unparsed.sum())}")
    print(f"null / blank          : {int(df[COST_COL].isna().sum())}")
    print(f"exactly zero          : {int((c == 0).sum())}")
    print(f"negative              : {int((c < 0).sum())}")
    print(f"total dollars         : ${c.sum():,.0f}")
    q = c.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    print("\ndistribution:")
    print(q.apply(lambda v: f"{v:,.2f}").to_string())
    print(f"\nskewness              : {c.skew():.2f}")
    print(f"log10(max/median)     : {(c.max() / c.median()):,.0f}x median")
    print("\nmagnitude bands (units check - dollars vs thousands):")
    bands = [(0, 0), (1, 999), (1000, 9999), (10_000, 99_999),
             (100_000, 999_999), (1_000_000, 9_999_999),
             (10_000_000, 99_999_999), (100_000_000, 999_999_999),
             (1_000_000_000, float("inf"))]
    for lo, hi in bands:
        n = int(((c >= lo) & (c <= hi)).sum())
        print(f"  {lo:>15,.0f} - {hi if hi != float('inf') else 'inf':>15} : {n:5d}")
    print("\n15 largest records:")
    big = df.nlargest(15, "cost_num")[["Project_ID", "Project_Name", "Jurisdiction",
                                       "scale", "cost_num", YEAR_COL]]
    with pd.option_context("display.max_colwidth", 55):
        print(big.to_string(index=False))
    print("\n15 smallest non-null records:")
    small = df[c.notna()].nsmallest(15, "cost_num")[
        ["Project_ID", "Project_Name", "scale", "cost_num"]]
    with pd.option_context("display.max_colwidth", 55):
        print(small.to_string(index=False))

    print("\nrepeated cost values (top 12) - round numbers are expected for"
          " budget estimates, but flag any that look like a fill value:")
    print(c.value_counts().head(12).to_string())

    print("\npossible duplicate project records (same name + same cost):")
    dup_mask = df.duplicated(subset=["Project_Name", COST_COL], keep=False)
    print(f"  rows in a name+cost duplicate group : {int(dup_mask.sum())}")
    dup2 = df.duplicated(subset=["Project_Name"], keep=False)
    print(f"  rows sharing a Project_Name         : {int(dup2.sum())}")
    dup3 = df.duplicated(subset=["Project_Description"], keep=False)
    print(f"  rows sharing a Project_Description  : {int(dup3.sum())}")
    if dup3.sum():
        with pd.option_context("display.max_colwidth", 45):
            print(df[dup3].sort_values("Project_Description")[
                ["Project_ID", "Project_Name", "Jurisdiction", "scale",
                 "cost_num"]].head(20).to_string(index=False))
    dup4 = df.duplicated(subset=["Project_Name", "Latitude", "Longitude", COST_COL],
                         keep=False)
    print(f"  rows sharing name+coords+cost       : {int(dup4.sum())}")
    return {
        "total": float(c.sum()), "n_zero": int((c == 0).sum()),
        "n_null": int(c.isna().sum()), "n_negative": int((c < 0).sum()),
        "skew": float(c.skew()),
        "describe": {k: float(v) for k, v in q.items()},
    }


def profile_scale(df):
    section("STEP 2b - SCALE TAG (Spatial_Resolution)")
    g = df.groupby("scale", dropna=False)
    tab = pd.DataFrame({
        "n_records": g.size(),
        "pct_records": g.size() / len(df) * 100,
        "total_cost": g["cost_num"].sum(),
        "median_cost": g["cost_num"].median(),
        "mean_cost": g["cost_num"].mean(),
        "min_cost": g["cost_num"].min(),
        "max_cost": g["cost_num"].max(),
        "n_zero_cost": g["cost_num"].apply(lambda s: int((s == 0).sum())),
        "n_null_cost": g["cost_num"].apply(lambda s: int(s.isna().sum())),
    }).sort_values("total_cost", ascending=False)
    tab["pct_dollars"] = tab["total_cost"] / df["cost_num"].sum() * 100
    print("raw distinct values, exactly as stored:")
    print(df[SCALE_COL].value_counts(dropna=False).to_string())
    print("\ncross-tab: records and investment dollars by scale")
    fmt = tab.copy()
    for col in ["total_cost", "median_cost", "mean_cost", "min_cost", "max_cost"]:
        fmt[col] = fmt[col].map(lambda v: f"{v:,.0f}" if pd.notna(v) else "")
    for col in ["pct_records", "pct_dollars"]:
        fmt[col] = fmt[col].map(lambda v: f"{v:.1f}%")
    print(fmt.to_string())
    print("\ncasing / whitespace variants present:", sorted(df[SCALE_COL].unique()))
    print("\nscale x status:")
    print(pd.crosstab(df["scale"], df["Project_Status"]).to_string())
    return tab


def profile_coords(df):
    section("STEP 2c - COORDINATES")
    print(f"columns              : {LAT_COL}, {LON_COL}")
    print(f"null lat or lon      : {int((~df['coord_ok']).sum())}")
    print(f"unparseable numeric  : "
          f"{int((df[LAT_COL].notna() & df['lat_num'].isna()).sum())} lat, "
          f"{int((df[LON_COL].notna() & df['lon_num'].isna()).sum())} lon")
    print(f"lat range            : {df['lat_num'].min():.6f} to {df['lat_num'].max():.6f}")
    print(f"lon range            : {df['lon_num'].min():.6f} to {df['lon_num'].max():.6f}")
    print(f"\nMiami-Dade bbox      : lat {MD_LAT_MIN}-{MD_LAT_MAX}, "
          f"lon {MD_LON_MIN} to {MD_LON_MAX}")
    inside = int(df["in_bbox"].sum())
    print(f"inside bbox          : {inside}")
    print(f"outside bbox         : {int((df['coord_ok'] & ~df['in_bbox']).sum())}")
    out = df[df["coord_ok"] & ~df["in_bbox"]]
    if len(out):
        print("\nrecords outside the bbox:")
        with pd.option_context("display.max_colwidth", 50):
            print(out[["Project_ID", "Project_Name", "Jurisdiction", "scale",
                       "lat_num", "lon_num", "cost_num"]].to_string(index=False))
        print(f"\ndollars outside bbox : ${out['cost_num'].sum():,.0f}")

    print("\nCRS: no CRS column is present in the file. Decimal-degree lat/long"
          " in this range is WGS84 / EPSG:4326 by convention - unstated, assumed.")

    coords = df[df["coord_ok"]].copy()
    coords["pt"] = list(zip(coords["lat_num"].round(8), coords["lon_num"].round(8)))
    vc = coords["pt"].value_counts()
    shared = vc[vc > 1]
    print(f"\ndistinct exact points : {len(vc)}")
    print(f"points used >1 time   : {len(shared)}")
    print(f"records on a shared point : {int(shared.sum())}")
    print(f"records on a unique point : {int((vc == 1).sum())}")
    if len(shared):
        print("\ntop shared points (possible geocoding to an office address):")
        rows = []
        for pt, n in shared.head(12).items():
            sub = coords[coords["pt"] == pt]
            rows.append({
                "lat": pt[0], "lon": pt[1], "n_records": n,
                "jurisdictions": ", ".join(sorted(sub["Jurisdiction"].unique()))[:40],
                "scales": ",".join(sorted(sub["scale"].unique())),
                "dollars": f"{sub['cost_num'].sum():,.0f}",
            })
        print(pd.DataFrame(rows).to_string(index=False))
    # rounded-precision check: low-precision coords suggest hand-typed centroids
    dec = df[LAT_COL].dropna().str.split(".").str[-1].str.len()
    print("\ndecimal places in Latitude (precision tell):")
    print(dec.value_counts().sort_index().to_string())
    return {"inside_bbox": inside, "shared_point_records": int(shared.sum())}


def profile_dates(df):
    section("STEP 2d - DATE / TIME COLUMNS")
    date_like = [c for c in df.columns
                 if re.search(r"year|date|time|fy|month", c, re.I)]
    print("date-like columns found:", date_like)
    y = df["year_num"]
    print(f"\n{YEAR_COL}: min {y.min():.0f}  max {y.max():.0f}  "
          f"median {y.median():.0f}  nulls {int(y.isna().sum())}")
    print("\nfull year frequency:")
    print(y.value_counts().sort_index().to_string())
    print("\ndollars by year:")
    print(df.groupby("year_num")["cost_num"].agg(["size", "sum"]).rename(
        columns={"size": "n", "sum": "dollars"}).to_string(
        float_format=lambda v: f"{v:,.0f}"))
    print("\nNOTE: Reported_Year is a single year per record with no month/day"
          " and no start/end pair - it is the year the project was reported in"
          " its source document, not a construction or spend date.")
    return {"min_year": float(y.min()), "max_year": float(y.max())}


def profile_categories(df):
    section("STEP 2e - PROJECT TYPE / CATEGORY COLUMNS")
    for col in ["Infrastructure_Type", "Hazard_Focus", "Project_Status",
                "Jurisdiction"]:
        print(f"\n--- {col} ---")
        t = df.groupby(col).agg(n=("Project_ID", "size"),
                                dollars=("cost_num", "sum")).sort_values(
            "dollars", ascending=False)
        t["pct_dollars"] = t["dollars"] / df["cost_num"].sum() * 100
        print(t.to_string(float_format=lambda v: f"{v:,.1f}"))
    print("\nFLAG - Jurisdiction has spacing variants that are the same place"
          " (e.g. 'Miami Beach' vs 'MiamiBeach'). Reported, not merged.")


def decision_a_corridor(df, raw):
    section("STEP 3a - CORRIDOR HANDLING: EVIDENCE")
    corr = df[df["scale"].str.lower() == "corridor"]
    total = df["cost_num"].sum()
    print(f"corridor records        : {len(corr)}  ({len(corr)/len(df)*100:.1f}% of rows)")
    print(f"corridor dollars        : ${corr['cost_num'].sum():,.0f} "
          f"({corr['cost_num'].sum()/total*100:.1f}% of all dollars)")
    print(f"corridor median cost    : ${corr['cost_num'].median():,.0f}")
    print("\nIs there ANY geometry beyond the single point?")
    hits = [c for c in raw.columns
            if any(w in c.lower() for w in GEOMETRY_WORDS)]
    print(f"  columns whose NAME suggests geometry/extent : {hits or 'NONE'}")
    print(f"  total columns in file                       : {len(raw.columns)}")
    print("  columns present:", list(raw.columns))
    # does free text carry a length / endpoint pair?
    txt = (corr["Project_Name"].fillna("") + " || " + corr["Project_Description"].fillna(""))
    pat_len = txt.str.contains(r"\b\d+(?:\.\d+)?\s*(?:mile|mi\.|km|kilometer|linear\s*f|lf\b|feet|ft\b)",
                               case=False, regex=True, na=False)
    pat_between = txt.str.contains(r"\b(?:from|between)\b.{0,60}\b(?:to|and)\b",
                                   case=False, regex=True, na=False)
    print(f"\n  corridor rows whose free text states a LENGTH      : {int(pat_len.sum())}"
          f" / {len(corr)}")
    print(f"  corridor rows whose free text names an ENDPOINT PAIR: {int(pat_between.sum())}"
          f" / {len(corr)}")
    if pat_between.sum():
        print("\n  examples of endpoint-pair text (unstructured, would need parsing):")
        with pd.option_context("display.max_colwidth", 110):
            print(corr[pat_between][["Project_ID", "Project_Name"]].head(8).to_string(index=False))
    print("\n  geometry columns beyond lat/long: NONE. Each corridor is one"
          " (lat, lon) pair only.")
    return {"n": len(corr), "dollars": float(corr["cost_num"].sum()),
            "pct_dollars": float(corr["cost_num"].sum() / total * 100)}


def decision_b_large_scale(df):
    section("STEP 3b - MUNICIPALITY / COUNTY (and NEIGHBORHOOD) SCALE: EVIDENCE")
    total = df["cost_num"].sum()
    order = ["Parcel", "Corridor", "Neighborhood", "Municipality", "County"]
    rows = []
    for s in order:
        sub = df[df["scale"] == s]
        c = sub["cost_num"]
        rows.append({
            "scale": s, "n": len(sub),
            "pct_rows": f"{len(sub)/len(df)*100:.1f}%",
            "dollars": f"{c.sum():,.0f}",
            "pct_dollars": f"{c.sum()/total*100:.1f}%",
            "min": f"{c.min():,.0f}", "p25": f"{c.quantile(.25):,.0f}",
            "median": f"{c.median():,.0f}", "p75": f"{c.quantile(.75):,.0f}",
            "p95": f"{c.quantile(.95):,.0f}", "max": f"{c.max():,.0f}",
        })
    print(pd.DataFrame(rows).to_string(index=False))
    big = df[df["scale"].isin(["Municipality", "County"])]
    print(f"\nMunicipality + County combined : {len(big)} records "
          f"({len(big)/len(df)*100:.1f}% of rows), "
          f"${big['cost_num'].sum():,.0f} ({big['cost_num'].sum()/total*100:.1f}% of dollars)")
    withn = df[df["scale"].isin(["Neighborhood", "Municipality", "County"])]
    print(f"+ Neighborhood                 : {len(withn)} records "
          f"({len(withn)/len(df)*100:.1f}% of rows), "
          f"${withn['cost_num'].sum():,.0f} ({withn['cost_num'].sum()/total*100:.1f}% of dollars)")
    parcel = df[df["scale"] == "Parcel"]["cost_num"]
    print(f"\nparcel-scale dollars           : ${parcel.sum():,.0f} "
          f"({parcel.sum()/total*100:.1f}%)")
    print("\ntop 10 records by cost, with their scale (who carries the tail):")
    with pd.option_context("display.max_colwidth", 50):
        print(df.nlargest(10, "cost_num")[
            ["Project_ID", "Project_Name", "scale", "Jurisdiction", "cost_num"]
        ].to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    print("\nshare of the top-50 dollar records held by each scale:")
    print(df.nlargest(50, "cost_num")["scale"].value_counts().to_string())
    return None


def decision_c_risk(df, raw):
    section("STEP 3c - PHYSICAL RISK LAYER: IS IT HERE?")
    print("columns whose NAME matches a risk/hazard/flood/surge/elevation/"
          "exposure term:")
    hits = [c for c in raw.columns if any(w in c.lower() for w in RISK_WORDS)]
    print("  ", hits)
    print("\nHazard_Focus is the only match. Its values are a CATEGORICAL TAG of"
          " what hazard the project addresses - not a measured risk value:")
    print(df["Hazard_Focus"].value_counts().to_string())
    print("\nNo column carries a flood depth, surge height, elevation, SLR"
          " scenario, FEMA zone, loss estimate, or any continuous exposure"
          " measure.")
    print("\nsearch for risk-bearing FILES in the data directory"
          " (excluding the census/ACS/SVI/EJScreen folders):")
    pat = re.compile("|".join(FILE_RISK_WORDS), re.I)
    found = []
    for p in sorted(BASE.rglob("*")):
        if p.is_dir() or p.name.startswith("."):
            continue
        rel = str(p.relative_to(BASE))
        if pat.search(p.name):
            found.append(rel)
    if found:
        for f in found:
            print("  ", f)
    else:
        print("   NONE")
    print("\nrisk-named files one level UP, in the repo root (outside this data"
          " directory - listed because they answer the same question):")
    up = BASE.parent
    for p in sorted(up.iterdir()):
        if not pat.search(p.name):
            continue
        if p.is_symlink():
            print(f"   ../{p.name} -> {p.resolve()} "
                  f"(exists: {p.resolve().exists()})")
        elif p.is_file():
            print(f"   ../{p.name}")

    print("\nall data files in the directory tree, by folder:")
    for sub in sorted({str(p.relative_to(BASE).parent) for p in BASE.rglob("*")
                       if p.is_file() and p.suffix.lower() in
                       (".csv", ".xlsx", ".shp", ".geojson", ".zip", ".gpkg")}):
        n = len([p for p in (BASE / sub).glob("*")
                 if p.suffix.lower() in (".csv", ".xlsx", ".shp", ".geojson",
                                         ".zip", ".gpkg")])
        print(f"   {sub:<70} {n} file(s)")


def main():
    raw = load_raw()
    df = load_typed()
    out = {}
    out["inventory"] = inventory(raw, df)
    out["cost"] = profile_cost(df)
    profile_scale(df)
    out["coords"] = profile_coords(df)
    out["dates"] = profile_dates(df)
    profile_categories(df)
    out["corridor"] = decision_a_corridor(df, raw)
    decision_b_large_scale(df)
    decision_c_risk(df, raw)
    if "--json" in sys.argv:
        p = ensure_output_dir() / "profile.json"
        p.write_text(json.dumps(out, indent=2, default=str))
        print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
