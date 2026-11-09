"""Download FEMA NFIP claims and HMA subapplications for Miami-Dade (D-113, D-114).

Standard library only. Run with an isolated interpreter:
    python3 -I scripts/impact/download_fema.py

OpenFEMA renamed or retired the dataset names in the brief:
- "FimaNfipClaims" is now "NfipClaims" v3 (title "NFIP Redacted Claims").
- "HazardMitigationAssistanceProjects" is no longer served; its successor is
  "HmaSubapplications" v2 (title "HMA Subapplications").
Every page is checked: the rows saved must equal the API's reported count and
every record id must be unique.
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

BASE = "https://www.fema.gov/api/open"
PAGE = 10000
UA = "SCALE-R research data download (python urllib)"

# HMA rows with no benefiting county are kept only when the subapplicant is
# plainly a Miami-Dade body (checked by hand against the Florida list, D-114).
HMA_NULL_COUNTY_KEEP = {
    ("City of Opa-locka", "Opa-locka"),
    ("Miami-Dade County", "Miami"),
    ("Miami-Dade County DERM", "Miami"),
    ("University of Miami", "Miami"),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network hiccup: wait and retry
            if attempt == 4:
                raise
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(5 * (attempt + 1))


def fetch_all(entity, version, flt):
    rows, skip, total, rundate = [], 0, None, None
    while True:
        q = {"$filter": flt, "$top": PAGE, "$skip": skip, "$orderby": "id", "$count": "true"}
        url = f"{BASE}/{version}/{entity}?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
        d = get(url)
        meta = d["metadata"]
        if total is None:
            total, rundate = meta["count"], meta["rundate"]
            print(f"{entity} {version}: API count {total}")
        page = d[entity]
        rows.extend(page)
        print(f"  skip {skip}: got {len(page)} (total so far {len(rows)})")
        if len(page) < PAGE:
            break
        skip += PAGE
    ids = [r["id"] for r in rows]
    assert len(rows) == total, f"{entity}: saved {len(rows)} but API count {total}"
    assert len(set(ids)) == len(ids), f"{entity}: duplicate ids"
    return rows, total, rundate, url.replace(f"&%24skip={skip}", "")


def write_csv(rows, path):
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def dataset_meta(name, version):
    flt = f"name eq '{name}' and version eq {version}"
    d = get(f"{BASE}/v1/DataSets?" + urllib.parse.urlencode({"$filter": flt}, quote_via=urllib.parse.quote))
    m = d["DataSets"][0]
    return {k: m.get(k) for k in ("name", "title", "version", "lastRefresh", "lastDataSetRefresh",
                                    "recordCount", "webService", "dataDictionary")}


def main():
    log = {"downloaded_local_date": datetime.now().date().isoformat(),
           "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    # 1. NFIP claims, Miami-Dade
    claims, n, rd, url = fetch_all("NfipClaims", "v3", "countyCode eq '12086'")
    write_csv(claims, paths.NFIP_CLAIMS_CSV)
    log["nfip"] = {"dataset": dataset_meta("NfipClaims", 3), "query": url, "api_count": n,
                   "rows_saved": len(claims), "api_rundate": rd}

    # 2. HMA subapplications, Miami-Dade
    a, na, rda, urla = fetch_all("HmaSubapplications", "v2",
                                 "subapplicantStateAbbreviation eq 'FL' and substringof('Miami-Dade',benefitingCounties)")
    b, nb, _, urlb = fetch_all("HmaSubapplications", "v2",
                               "subapplicantStateAbbreviation eq 'FL' and benefitingCounties eq null")
    b_keep = [r for r in b if (r.get("subapplicantName"), r.get("subapplicantCity")) in HMA_NULL_COUNTY_KEEP]
    hma = a + b_keep
    assert len({r["id"] for r in hma}) == len(hma)
    write_csv(hma, paths.HMA_PROJECTS_CSV)
    log["hma"] = {"dataset": dataset_meta("HmaSubapplications", 2),
                  "query_county": urla, "api_count_county": na,
                  "query_null_county": urlb, "api_count_null_county": nb,
                  "null_county_kept": len(b_keep), "rows_saved": len(hma), "api_rundate": rda}

    paths.FEMA_DOWNLOAD_LOG.write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
