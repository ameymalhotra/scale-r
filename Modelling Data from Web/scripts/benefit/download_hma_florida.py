"""Download the Florida rows of OpenFEMA HMA Subapplications v2 (prompt 29 Part 2, D-197).

    python3 -I scripts/benefit/download_hma_florida.py

The dataset the user first approved, "Hazard Mitigation Assistance Projects"
(v4), no longer exists on OpenFEMA (404, not in the DataSets catalogue on
16 Nov 2026). The user approved its replacement, HmaSubapplications v2, for
Florida. Standard library only; all fields; paged by id. Rows are untrusted
data and are only parsed as CSV/JSON.
"""
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

BASE = "https://www.fema.gov/api/open/v2/HmaSubapplications"
FILTER = "subapplicantStateAbbreviation eq 'FL'"
UA = "SCALE-R research data download (python urllib)"
PAGE = 5000


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    out = paths.HMA_SUBAPPS_FL_CSV
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, skip, count = [], 0, None
    while True:
        q = urllib.parse.urlencode({"$filter": FILTER, "$top": PAGE, "$skip": skip, "$orderby": "id",
                                    **({"$count": "true"} if count is None else {})})
        d = get(f"{BASE}?{q}")
        if count is None:
            count = d["metadata"]["count"]
        page = d["HmaSubapplications"]
        rows += page
        print(f"rows {len(rows)} of {count}", flush=True)
        skip += PAGE
        if len(page) < PAGE:
            break
    cols = sorted({k for r in rows for k in r})
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    tmp.rename(out)
    meta = get("https://www.fema.gov/api/open/v1/DataSets?" + urllib.parse.urlencode(
        {"$filter": "name eq 'HmaSubapplications' and version eq 2"}))["DataSets"][0]
    log = {"downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "dataset": {k: meta.get(k) for k in ("name", "title", "version", "lastRefresh", "recordCount", "webService", "dataDictionary")},
           "filter": FILTER, "api_count": count, "rows_saved": len(rows),
           "note": "Replaces HazardMitigationAssistanceProjects v4, which OpenFEMA no longer serves (D-197)."}
    paths.HMA_SUBAPPS_FL_LOG.write_text(json.dumps(log, indent=2))
    assert len(rows) == count, (len(rows), count)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
