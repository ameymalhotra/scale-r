"""Millage rates by taxing district code, 2026 adopted (prompt 28 Part 1, D-164).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/build_millage.py

Reads the Miami-Dade Property Appraiser's 2026 adopted millage chart (PDF, text
layer via pdftotext -layout) and writes data/reference/millage_2026_by_code.csv
with one row per millage code (the tax roll's TAX_AUTH_CD). Each number is
assigned to its column by where it ends on the line; every row is checked
against the chart's own 2026 total. School millage applies to school taxable
value (TV_SD) and the rest to non-school taxable value (TV_NSD).
Also cross-checks the 2025 adopted rates in the Florida DOR file against the
chart's 2025 total column, and lists tax roll codes with no millage row.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

COLS = ["city_umsa", "city_debt", "city_misc", "school_operating", "school_voted", "school_debt", "sfwmd",
        "everglades", "okeechobee", "find", "county", "county_debt", "fire_rescue", "library", "childrens_trust",
        "total_this_year", "total_last_year"]
SCHOOL = ["school_operating", "school_voted", "school_debt"]
ROW = re.compile(r"^\s*(\d{4})\s+(.+?)\s{2,}(?=[\d.])")
NUM = re.compile(r"\d+\.\d{4}")


def parse(pdf):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    rows = []
    for line in txt.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        toks = [(t.group(), t.end()) for t in NUM.finditer(line, m.end() - 1)]
        rows.append((m.group(1), m.group(2).strip(" *"), toks))
    # column end positions from the row with the most numbers, then the union of all rows
    ends = sorted({e for _, _, t in rows for _, e in t})
    centres = []
    for e in ends:
        if centres and e - centres[-1][-1] <= 3:
            centres[-1].append(e)
        else:
            centres.append([e])
    centres = [int(np.median(c)) for c in centres]
    assert len(centres) == len(COLS), f"found {len(centres)} column positions, expected {len(COLS)}"
    out = []
    for code, name, toks in rows:
        r = dict.fromkeys(COLS, 0.0)
        for v, e in toks:
            r[COLS[int(np.argmin([abs(e - c) for c in centres]))]] = float(v)
        out.append({"code": code, "area": name, **r})
    d = pd.DataFrame(out)
    parts = d[COLS[:-2]].sum(axis=1)
    d["check_diff"] = (parts - d.total_this_year).round(4)
    return d


def main():
    d = parse(paths.MILLAGE_DIR / "2026_adopted_millage_chart.pdf")
    bad = d[d.check_diff.abs() > 0.0002]
    d["school_total"] = d[SCHOOL].sum(axis=1).round(4)
    d["nonschool_total"] = (d.total_this_year - d.school_total).round(4)
    d.drop(columns="check_diff").to_csv(paths.MILLAGE_2026_CSV, index=False)
    d25 = parse(paths.MILLAGE_DIR / "2025_Miami-Dade_TACD.pdf")
    j = d.merge(d25[["code", "total_this_year"]].rename(columns={"total_this_year": "dor_2025"}), on="code", how="outer")
    nal = pd.read_csv(paths.DOR_DIR / "extract" / "NAL23F202601.csv", usecols=["TAX_AUTH_CD", "JV"], dtype={"TAX_AUTH_CD": str})
    nal["code"] = nal.TAX_AUTH_CD.str.zfill(4)
    cnt = nal.groupby("code").size()
    R = {"rows": len(d), "rows_failing_total_check": bad[["code", "area", "check_diff"]].to_dict("records"),
         "dor_2025_vs_chart_2025_max_abs_diff": round(float((j.dor_2025 - j.total_last_year).abs().max()), 4),
         "tax_roll_codes": int(cnt.size),
         "tax_roll_codes_without_millage": {k: int(v) for k, v in cnt[~cnt.index.isin(d.code)].items()},
         "total_millage_2026_range": [float(d.total_this_year.min()), float(d.total_this_year.max())]}
    (paths.OUT_BENEFIT / "spec_alignment" / "millage_check.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
