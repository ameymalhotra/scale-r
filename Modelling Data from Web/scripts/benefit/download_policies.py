"""Download FEMA NFIP Redacted Policies for Miami-Dade (prompt 27 Stage 1, D-120, D-135).

Standard library only. Run with an isolated interpreter:
    python3 -I scripts/benefit/download_policies.py

How (D-135, the user's settings of 11 Nov 2026):
- Entity `NfipPolicies` v3. It has no county field, so the filter is
  `propertyState eq 'FL' and startswith(censusGeoid,'12086')`.
- Large pages: 200,000 rows (a 1,000,000-row page timed out with 503; 200,000
  rows with the kept fields took about 2 minutes). If a page fails, the same
  page is retried at 100,000 and then 50,000 rows.
- No $count on the pages (it is slow). The rows saved are counted, and the
  API total is asked once at the end to check them.
- Only the 26 fields needed to turn claims into rates are kept (of 80).
- Resumable: each page is saved under data/raw/fema/nfip_policies_parts/ as
  soon as it arrives (temporary name, then renamed); a rerun continues after
  the last saved page. Rows are ordered by id, so offsets are stable.
- If 503 errors persist after the retries, the script stops with a message
  (the user will then download the full Parquet file by hand).
"""
import csv
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

BASE = "https://www.fema.gov/api/open/v3/NfipPolicies"
FILTER = "propertyState eq 'FL' and startswith(censusGeoid,'12086')"
PAGE_SIZES = [200000, 100000, 50000]
UA = "SCALE-R research data download (python urllib)"
PARTS = paths.FEMA_RAW_DIR / "nfip_policies_parts"
FIELDS = [
    "id", "censusGeoid", "reportedZipCode", "nfipRatedCommunityNumber", "nfipCommunityName",
    "policyEffectiveDate", "policyTerminationDate", "cancellationDateOfFloodPolicy", "policyCount",
    "policyTermIndicator", "ratedFloodZone", "floodZoneCurrent", "occupancyType", "buildingDescriptionCode",
    "primaryResidenceIndicator", "elevatedBuildingIndicator", "foundationType", "originalConstructionDate",
    "baseFloodElevation", "lowestFloorElevation", "totalBuildingInsuranceCoverage",
    "totalContentsInsuranceCoverage", "buildingReplacementCost", "totalInsurancePremiumOfThePolicy",
    "crsClassCode", "asOfDate",
]


class Stop(Exception):
    pass


def get(params, timeout=600):
    url = BASE + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_page(skip):
    """One page at `skip`; smaller pages on failure; Stop if every size fails."""
    last = None
    for size in PAGE_SIZES:
        for attempt in range(2):
            try:
                d = get({"$filter": FILTER, "$select": ",".join(FIELDS), "$top": size, "$skip": skip,
                         "$orderby": "id"})
                return size, d["NfipPolicies"], d["metadata"]["rundate"]
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = e
                print(f"  skip {skip:,}, page {size:,}, try {attempt + 1}: {e}", flush=True)
                time.sleep(30)
    raise Stop(f"FEMA API kept failing at offset {skip:,} ({last}). Stopping as instructed.")


def saved_pages():
    return sorted(PARTS.glob("p*.json"))


def main():
    PARTS.mkdir(parents=True, exist_ok=True)
    pages = saved_pages()
    skip = 0
    if pages:
        m = json.loads(pages[-1].read_text())
        skip = None if m["last"] else m["skip"] + m["rows"]
    t0 = time.time()
    while skip is not None:
        size, rows, rundate = fetch_page(skip)
        name = PARTS / f"p{skip:010d}"
        tmp = PARTS / f"p{skip:010d}.csv.gz.tmp"
        with gzip.open(tmp, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        tmp.rename(PARTS / f"p{skip:010d}.csv.gz")
        last = len(rows) < size
        (PARTS / f"p{skip:010d}.json").write_text(json.dumps({
            "skip": skip, "rows": len(rows), "page_size": size, "last": last, "rundate": rundate,
            "first_id": rows[0]["id"] if rows else None, "last_id": rows[-1]["id"] if rows else None}))
        print(f"saved {skip:,} + {len(rows):,} rows ({time.time() - t0:.0f}s)", flush=True)
        skip = None if last else skip + len(rows)

    # assemble and check
    out = paths.NFIP_POLICIES_CSV
    seen, n, bad_geo = set(), 0, 0
    tmp = out.with_suffix(".tmp.gz")
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for meta in saved_pages():
            with gzip.open(PARTS / (meta.stem + ".csv.gz"), "rt", newline="") as f:
                for r in csv.DictReader(f):
                    assert r["id"] not in seen, f"duplicate id {r['id']}"
                    seen.add(r["id"])
                    bad_geo += not r["censusGeoid"].startswith("12086")
                    w.writerow(r)
                    n += 1
    total = get({"$filter": FILTER, "$select": "id", "$top": 1, "$count": "true"}, timeout=900)["metadata"]["count"]
    assert bad_geo == 0
    assert n == total, f"saved {n:,} rows but API count {total:,}"
    tmp.rename(out)
    log = {"entity": "NfipPolicies", "version": "v3", "endpoint": BASE, "filter": FILTER,
           "page_sizes": PAGE_SIZES, "fields_kept": FIELDS, "rows": n, "api_count": total,
           "pages": len(saved_pages()), "finished": datetime.now(timezone.utc).isoformat(),
           "file": str(out.relative_to(paths.ROOT))}
    paths.NFIP_POLICIES_LOG.write_text(json.dumps(log, indent=2))
    print(f"done: {n:,} rows, equal to the API count")


if __name__ == "__main__":
    try:
        main()
    except Stop as e:
        print(f"STOPPED: {e}", flush=True)
        sys.exit(2)
