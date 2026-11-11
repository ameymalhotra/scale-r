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
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network hiccup: wait and retry
            if attempt == 5:
                raise
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep(10 * (attempt + 1))


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


def main():
    out = paths.NFIP_POLICIES_CSV
    out.parent.mkdir(parents=True, exist_ok=True)
    comms = community_numbers()
    print(f"{len(comms)} community numbers: {comms}", flush=True)
    log = {"entity": "NfipPolicies", "version": "v3", "endpoint": BASE, "fields_kept": FIELDS,
           "started": datetime.now(timezone.utc).isoformat(), "communities": {}}
    seen, kept, outside = set(), 0, 0
    tmp = out.with_suffix(".tmp.gz")
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for comm in comms:
            skip, total, got, ckept = 0, None, 0, 0
            flt = f"nfipRatedCommunityNumber eq '{comm}'"
            while True:
                q = {"$filter": flt, "$select": ",".join(FIELDS), "$top": PAGE, "$skip": skip,
                     "$orderby": "id", "$count": "true"}
                d = get(BASE + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote))
                if total is None:
                    total = d["metadata"]["count"]
                    rundate = d["metadata"]["rundate"]
                page = d["NfipPolicies"]
                for r in page:
                    assert r["id"] not in seen, f"duplicate id {r['id']}"
                    seen.add(r["id"])
                    if (r.get("censusGeoid") or "").startswith("12086"):
                        w.writerow(r)
                        ckept += 1
                    else:
                        outside += 1
                got += len(page)
                if len(page) < PAGE:
                    break
                skip += PAGE
            assert got == total, f"{comm}: got {got} but API count {total}"
            kept += ckept
            log["communities"][comm] = {"api_count": total, "kept_12086": ckept, "rundate": rundate}
            print(f"{comm}: API {total}, kept {ckept} (running total {kept})", flush=True)
    tmp.rename(out)
    log.update({"finished": datetime.now(timezone.utc).isoformat(), "rows_kept": kept,
                "rows_outside_12086": outside, "file": str(out.relative_to(paths.ROOT))})
    paths.NFIP_POLICIES_LOG.write_text(json.dumps(log, indent=2))
    print(f"done: kept {kept}, dropped {outside} outside Miami-Dade")


if __name__ == "__main__":
    main()
