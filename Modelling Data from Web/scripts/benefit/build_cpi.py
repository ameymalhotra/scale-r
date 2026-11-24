"""Annual CPI-U (US city average, all items, not seasonally adjusted) for 1978 to 2025 (D-144).

Download (done once, 11 Nov 2026, BLS Public Data API v1, POST, series CUUR0000SA0,
ten years per request) into data/raw/bls/cpiu_<start>_<end>.json. Then:

    ../.venv/bin/python -I scripts/benefit/build_cpi.py

Annual value = mean of the monthly values. October 2025 was not published
("Data unavailable due to the 2025 lapse in appropriations"), so 2025 uses the
other 11 months; the count of months is kept in the table.
Writes data/reference/cpi_u_annual.csv with a factor to 2025 dollars.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402


def main():
    rows = []
    for f in sorted(paths.BLS_DIR.glob("cpiu_*.json")):
        d = json.loads(f.read_text())
        assert d["status"] == "REQUEST_SUCCEEDED", f
        s = d["Results"]["series"][0]
        assert s["seriesID"] == "CUUR0000SA0"
        for r in s["data"]:
            if r["period"].startswith("M") and r["period"] != "M13" and r["value"] not in ("-", ""):
                rows.append((int(r["year"]), int(r["period"][1:]), float(r["value"])))
    m = pd.DataFrame(rows, columns=["year", "month", "cpi"]).drop_duplicates()
    a = m.groupby("year").agg(cpi_u_annual=("cpi", "mean"), months=("cpi", "size")).reset_index()
    assert a.year.min() == 1978 and a.year.max() == 2025 and len(a) == 48
    assert (a.months[a.year < 2025] == 12).all() and int(a.months[a.year == 2025].iloc[0]) == 11
    base = float(a.loc[a.year == 2025, "cpi_u_annual"].iloc[0])
    a["factor_to_2025"] = base / a.cpi_u_annual
    a["series"] = "CUUR0000SA0 (CPI-U, US city average, all items, 1982-84=100, not seasonally adjusted)"
    a["source"] = "US Bureau of Labor Statistics, Public Data API v1, downloaded 11 Nov 2026"
    a.round({"cpi_u_annual": 3, "factor_to_2025": 4}).to_csv(paths.CPI_ANNUAL_CSV, index=False)
    print(a[["year", "cpi_u_annual", "months", "factor_to_2025"]].iloc[[0, 14, 22, 39, 47]].round(3))


if __name__ == "__main__":
    main()
