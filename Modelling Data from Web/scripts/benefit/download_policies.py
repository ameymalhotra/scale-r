"""Download FEMA NFIP Redacted Policies for Miami-Dade (prompt 27 Stage 1, D-120).

Standard library only. Run with an isolated interpreter:
    python3 -I scripts/benefit/download_policies.py

Why it is done this way:
- OpenFEMA's `NfipPolicies` v3 (74.7 million rows nationally) has no county
  field, and a prefix or range filter on `censusGeoid` times out. So the
  policies are pulled one NFIP community at a time (`nfipRatedCommunityNumber`,
  an indexed field), for every community number that appears in the Miami-Dade
  claims file, and then kept only where `censusGeoid` starts with 12086.
- Only the fields needed to turn claims into rates are kept (the full record
  has 80 fields).
Each community's saved row count must equal the API count, and ids must be unique.
Resumable: every page is saved under data/raw/fema/nfip_policies_parts/<community>/
as soon as it arrives, so a rerun after a failure continues at the next page.
"""
import csv
import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

BASE = "https://www.fema.gov/api/open/v3/NfipPolicies"
PAGE = 10000
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


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(12):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network hiccup: wait and retry
            if attempt == 11:
                raise
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep(min(30 * (attempt + 1), 300))  # FEMA returns 503 for long spells


# The 37 NFIP community numbers in Miami-Dade (D-120): the county (current 120635 and
# the old Metropolitan Dade County number 125098) and every municipality, as
# named in the claims file. Other community numbers on Miami-Dade claims are a
# handful of mis-coded records (Dade City in Pasco County, Monroe, Broward,
# out-of-state numbers) and are left out.
MIAMI_DADE_COMMUNITIES = [
    "120041", "120218", "120345", "120425", "120635", "120636", "120637", "120638", "120639",
    "120640", "120641", "120642", "120643", "120644", "120645", "120646", "120647", "120648",
    "120649", "120650", "120651", "120652", "120653", "120654", "120655", "120656", "120657",
    "120658", "120659", "120660", "120661", "120662", "120676", "120686", "120687", "120688",
    "125098",
]


def community_numbers():
    """Check the fixed list against the claims file and report what it covers."""
    nums = Counter()
    with open(paths.NFIP_CLAIMS_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if (r.get("censusGeoid") or "").startswith("12086"):
                nums[r["nfipRatedCommunityNumber"]] += 1
    covered = sum(nums[n] for n in MIAMI_DADE_COMMUNITIES)
    print(f"list covers {covered} of {sum(nums.values())} Miami-Dade claims", flush=True)
    return MIAMI_DADE_COMMUNITIES


def fetch_page(comm, skip):
    q = {"$filter": f"nfipRatedCommunityNumber eq '{comm}'", "$select": ",".join(FIELDS), "$top": PAGE,
         "$skip": skip, "$orderby": "id", "$count": "true"}
    return get(BASE + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote))


def download_community(comm):
    """Fetch one community page by page. Each page is saved as its own file (written to a temporary
    name, then renamed), with a small JSON of its counts, so a failed run resumes at the next page."""
    cdir = PARTS / comm
    cdir.mkdir(parents=True, exist_ok=True)
    if (cdir / "done.json").exists():
        return json.loads((cdir / "done.json").read_text())
    skip = 0
    while (cdir / f"{skip:09d}.json").exists():
        skip += PAGE
    total = rundate = None
    while True:
        d = fetch_page(comm, skip)
        total, rundate = d["metadata"]["count"], d["metadata"]["rundate"]
        page = d["NfipPolicies"]
        keep = [r for r in page if (r.get("censusGeoid") or "").startswith("12086")]
        tmp = cdir / f"{skip:09d}.csv.gz.tmp"
        with gzip.open(tmp, "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(keep)
        tmp.rename(cdir / f"{skip:09d}.csv.gz")
        (cdir / f"{skip:09d}.json").write_text(json.dumps({"rows": len(page), "kept": len(keep),
                                                           "ids": [r["id"] for r in page]}))
        if len(page) < PAGE:
            break
        skip += PAGE
        if (skip // PAGE) % 10 == 0:
            print(f"  {comm}: {skip:,} of {total:,}", flush=True)
    pages = sorted(cdir.glob("*.json"))
    pages = [x for x in pages if x.name != "done.json"]
    got = sum(json.loads(x.read_text())["rows"] for x in pages)
    kept = sum(json.loads(x.read_text())["kept"] for x in pages)
    assert got == total, f"{comm}: got {got} but API count {total}"
    info = {"api_count": total, "kept_12086": kept, "pages": len(pages), "rundate": rundate}
    (cdir / "done.json").write_text(json.dumps(info))
    return info


def main():
    out = paths.NFIP_POLICIES_CSV
    out.parent.mkdir(parents=True, exist_ok=True)
    comms = community_numbers()
    print(f"{len(comms)} community numbers: {comms}", flush=True)
    log = {"entity": "NfipPolicies", "version": "v3", "endpoint": BASE, "fields_kept": FIELDS,
           "finished": None, "communities": {}}
    for comm in comms:
        info = download_community(comm)
        log["communities"][comm] = info
        print(f"{comm}: API {info['api_count']}, kept {info['kept_12086']}", flush=True)
    # assemble: every id once across all communities, rows in community then id order
    seen, kept = set(), 0
    tmp = out.with_suffix(".tmp.gz")
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for comm in comms:
            for meta in sorted((PARTS / comm).glob("0*.json")):
                ids = json.loads(meta.read_text())["ids"]
                assert not seen.intersection(ids), f"duplicate ids in {meta}"
                seen.update(ids)
                with gzip.open(meta.with_suffix(".csv.gz"), "rt", newline="") as f:
                    for r in csv.DictReader(f):
                        w.writerow(r)
                        kept += 1
    tmp.rename(out)
    total = sum(c["api_count"] for c in log["communities"].values())
    log.update({"finished": datetime.now(timezone.utc).isoformat(), "rows_kept": kept,
                "rows_fetched": len(seen), "api_count_total": total,
                "rows_outside_12086": len(seen) - kept, "file": str(out.relative_to(paths.ROOT))})
    assert len(seen) == total
    paths.NFIP_POLICIES_LOG.write_text(json.dumps(log, indent=2))
    print(f"done: kept {kept}, dropped {len(seen) - kept} outside Miami-Dade")


if __name__ == "__main__":
    main()
