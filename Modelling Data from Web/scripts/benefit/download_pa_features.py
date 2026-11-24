"""House features from the county "Property Point View" layer (prompt 28 Part 2, D-169).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/download_pa_features.py

Source: Miami-Dade County open data, Property Appraiser layer PaGISView
(services.arcgis.com/8Pc9XBTAsYuxx9Ny/.../PaGISView_gdb/FeatureServer/0).

Privacy: only the fields in KEEP are requested from the server, so owner
names, mailing addresses, site addresses and coordinates are never sent to
this machine, never held in memory and never written to disk. A check after
loading fails the run if any other field appears.

Kept: folio (parcel ID), bedrooms, full and half bathrooms, heated living
area, latest sale price and date. The layer has no sale qualification code;
it is taken from the 2026 tax roll where the same sale (same parcel, year,
month and price) is there, and left blank otherwise.
Writes data/processed/benefit/pa_features.parquet (gitignored) and a summary.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

URL = "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/PaGISView_gdb/FeatureServer/0/query"
KEEP = ["OBJECTID", "FOLIO", "BEDROOM_COUNT", "BATHROOM_COUNT", "HALF_BATHROOM_COUNT", "BUILDING_HEATED_AREA",
        "PRICE_1", "DOS_1"]
PAGE = 2000


def get(params):
    q = urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(URL + "?" + q, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))


def page(lo):
    d = get({"where": f"OBJECTID>{lo} AND OBJECTID<={lo + PAGE}", "outFields": ",".join(KEEP),
             "returnGeometry": "false", "f": "json"})
    rows = [f["attributes"] for f in d.get("features", [])]
    for r in rows:
        extra = set(r) - set(KEEP)
        if extra:
            raise RuntimeError(f"server returned unrequested fields {sorted(extra)}; stopping")
    return rows


def main():
    t0 = time.time()
    st = get({"where": "1=1", "outStatistics": json.dumps([{"statisticType": "max", "onStatisticField": "OBJECTID",
                                                          "outStatisticFieldName": "mx"},
                                                         {"statisticType": "count", "onStatisticField": "OBJECTID",
                                                          "outStatisticFieldName": "n"}]), "f": "json"})
    mx = st["features"][0]["attributes"]["mx"]
    n_server = st["features"][0]["attributes"]["n"]
    rows = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for k, part in enumerate(ex.map(page, range(0, mx, PAGE))):
            rows.extend(part)
            if (k + 1) % 100 == 0:
                print(f"{len(rows):,} rows, {time.time() - t0:.0f}s", flush=True)
    d = pd.DataFrame(rows, columns=KEEP)
    assert list(d.columns) == KEEP
    assert len(d) == n_server, f"got {len(d):,} rows, server has {n_server:,}"
    d = d.drop(columns="OBJECTID").rename(columns={
        "FOLIO": "parcel_id", "BEDROOM_COUNT": "bedrooms", "BATHROOM_COUNT": "bathrooms_full",
        "HALF_BATHROOM_COUNT": "bathrooms_half", "BUILDING_HEATED_AREA": "living_area_sqft",
        "PRICE_1": "sale_price", "DOS_1": "sale_date"})
    d["sale_date"] = pd.to_datetime(d.sale_date.astype("string"), format="%Y%m%d", errors="coerce")
    d["sale_price"] = pd.to_numeric(d.sale_price, errors="coerce")
    d.loc[d.sale_price <= 0, "sale_price"] = np.nan

    # qualification code from the 2026 tax roll where the same sale is listed there
    nal = pd.read_csv(paths.DOR_DIR / "extract" / "NAL23F202601.csv",
                      usecols=["PARCEL_ID", "DOR_UC", "QUAL_CD1", "SALE_PRC1", "SALE_YR1", "SALE_MO1",
                               "QUAL_CD2", "SALE_PRC2", "SALE_YR2", "SALE_MO2"],
                      dtype={"PARCEL_ID": str, "DOR_UC": str})
    s = []
    for k in ("1", "2"):
        x = nal[["PARCEL_ID", f"QUAL_CD{k}", f"SALE_PRC{k}", f"SALE_YR{k}", f"SALE_MO{k}"]].dropna()
        x.columns = ["parcel_id", "qual_cd", "price", "yr", "mo"]
        s.append(x)
    s = pd.concat(s).drop_duplicates(["parcel_id", "yr", "mo", "price"])
    d["yr"] = d.sale_date.dt.year
    d["mo"] = d.sale_date.dt.month
    d = d.merge(s, left_on=["parcel_id", "yr", "mo", "sale_price"], right_on=["parcel_id", "yr", "mo", "price"],
                how="left").drop(columns=["price"])
    d["qual_cd"] = d.qual_cd.astype("Int64")
    uc = nal.set_index("PARCEL_ID").DOR_UC.str.zfill(3)
    seg = d.parcel_id.map(uc).map({"001": "single_family", "004": "condo"})
    d.drop(columns=["yr", "mo"]).to_parquet(paths.PA_FEATURES_PARQUET, index=False)

    yr = d.sale_date.dt.year
    R = {"rows": len(d), "seconds": round(time.time() - t0), "fields_kept": list(d.drop(columns=["yr", "mo"]).columns),
         "with_bedrooms": int((d.bedrooms > 0).sum()), "with_bathrooms": int((d.bathrooms_full > 0).sum()),
         "matched_to_tax_roll": int(d.parcel_id.isin(uc.index).sum()),
         "latest_sale_by_year_2015_on": yr[yr >= 2015].value_counts().sort_index().astype(int).to_dict(),
         "sales_2021_2024_by_segment": {k: int(((yr >= 2021) & (yr <= 2024) & (seg == k)).sum())
                                        for k in ["single_family", "condo"]},
         "sales_2021_on_with_tax_roll_qual_code": int(((yr >= 2021) & d.qual_cd.notna()).sum())}
    (paths.OUT_BENEFIT / "spec_alignment" / "pa_features_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
