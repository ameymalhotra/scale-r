"""First look at FEMA NFIP claims and HMA subapplications for Miami-Dade.

Descriptive only, no model (D-113 to D-118). Run in the ML environment:
    bash scripts/ml/run_ml.sh -I scripts/impact/fema_first_look.py

Reads the raw downloads from scripts/impact/download_fema.py, the Census
2010-to-2020 tract relationship file, the SCALE-R project database and the
tract table the ML scripts load (ml_common.load_table). Writes
- data/processed/impact/nfip_claims_tract_year.csv (2020 tract GEOIDs)
- data/processed/impact/hma_scaler_matches.csv
- outputs/impact/*.csv and fema_first_look_log.json (numbers for the report)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "common"))
sys.path.insert(0, str(HERE.parents[0] / "ml"))
import paths  # noqa: E402
from ml_common import load_table  # noqa: E402

COUNTY = "12086"
LOG = {}


# ----------------------------------------------------------------------------
# 1. NFIP claims
# ----------------------------------------------------------------------------
def load_claims():
    c = pd.read_csv(paths.NFIP_CLAIMS_CSV, dtype=str, low_memory=False)
    for k in ("amountPaidOnBuildingClaim", "amountPaidOnContentsClaim",
              "amountPaidOnIncreasedCostOfComplianceClaim", "latitude", "longitude"):
        c[k] = pd.to_numeric(c[k], errors="coerce")
    c["yearOfLoss"] = c["yearOfLoss"].astype(int)
    c["paid_bc"] = c.amountPaidOnBuildingClaim.fillna(0) + c.amountPaidOnContentsClaim.fillna(0)
    c["is_paid"] = (c.paid_bc > 0).astype(int)
    return c


def relationship():
    r = pd.read_csv(paths.TRACT_REL_2010_2020, sep="|", dtype=str, encoding="utf-8-sig")
    r = r[r.GEOID_TRACT_20.str.startswith(COUNTY) | r.GEOID_TRACT_10.str.startswith(COUNTY)].copy()
    for k in ("AREALAND_PART", "AREAWATER_PART", "AREALAND_TRACT_10", "AREAWATER_TRACT_10",
              "AREALAND_TRACT_20"):
        r[k] = r[k].astype(float)
    return r


def classify_vintage(c, r):
    """Label each claim's tract code by which census vintage it can belong to (D-115)."""
    g10, g20 = set(r.GEOID_TRACT_10), set(r.GEOID_TRACT_20)
    same = r[r.GEOID_TRACT_10 == r.GEOID_TRACT_20].copy()
    same["s10"] = same.AREALAND_PART / same.AREALAND_TRACT_10
    same["s20"] = same.AREALAND_PART / same.AREALAND_TRACT_20
    unchanged = set(same[(same.s10 >= 0.99) & (same.s20 >= 0.99)].GEOID_TRACT_10)

    def cls(x):
        if pd.isna(x):
            return "missing"
        if not x.startswith(COUNTY):
            return "other_county"
        if x in unchanged:
            return "unchanged"
        a, b = x in g10, x in g20
        return "shared_changed" if a and b else "2010_only" if a else "2020_only" if b else "invalid"

    c["tract_raw"] = c.censusGeoid.str[:11]
    c["vintage_class"] = c.tract_raw.map(cls)
    keep = same.set_index("GEOID_TRACT_10").s10
    return unchanged, keep


def to_2020(c, r):
    """One row per (claim, 2020 tract) with an allocation weight that sums to 1 per claim."""
    direct = c[c.vintage_class.isin(["unchanged", "2020_only", "shared_changed"])].copy()
    direct["GEOID"] = direct.tract_raw
    direct["w"] = 1.0
    conv = c[c.vintage_class == "2010_only"].copy()
    rel = r[r.GEOID_TRACT_20.str.startswith(COUNTY)][["GEOID_TRACT_10", "GEOID_TRACT_20", "AREALAND_PART",
                                                       "AREAWATER_PART"]].copy()
    tot = rel.groupby("GEOID_TRACT_10").AREALAND_PART.transform("sum")
    totall = (rel.AREALAND_PART + rel.AREAWATER_PART).groupby(rel.GEOID_TRACT_10).transform("sum")
    # land share; a tract with no land at all falls back to total area
    rel["w"] = np.where(tot > 0, rel.AREALAND_PART / tot.replace(0, np.nan),
                        (rel.AREALAND_PART + rel.AREAWATER_PART) / totall)
    rel = rel[rel.w > 0]
    conv = conv.merge(rel[["GEOID_TRACT_10", "GEOID_TRACT_20", "w"]], left_on="tract_raw",
                      right_on="GEOID_TRACT_10", how="left").rename(columns={"GEOID_TRACT_20": "GEOID"})
    alloc = pd.concat([direct, conv], ignore_index=True)
    return alloc


def nfip(t):
    c = load_claims()
    r = relationship()
    unchanged, keep_share = classify_vintage(c, r)
    out = {}
    out["claims_total"] = len(c)
    out["claims_paid"] = int(c.is_paid.sum())
    out["years"] = [int(c.yearOfLoss.min()), int(c.yearOfLoss.max())]
    out["paid_bc_total"] = float(c.paid_bc.sum())
    out["paid_building"] = float(c.amountPaidOnBuildingClaim.fillna(0).sum())
    out["paid_contents"] = float(c.amountPaidOnContentsClaim.fillna(0).sum())
    out["negative_payment_rows"] = int(((c.amountPaidOnBuildingClaim < 0) | (c.amountPaidOnContentsClaim < 0)).sum())
    out["asOfDate"] = sorted(c.asOfDate.dropna().unique().tolist())

    # location fields
    loc = {}
    for k in ("censusGeoid", "latitude", "longitude", "reportedZipCode", "reportedCity",
              "nfipCommunityName", "countyCode"):
        s = c[k]
        if k == "reportedCity":
            s = s.where(s != "Currently Unavailable")
        loc[k] = {"filled": int(s.notna().sum()), "share": round(float(s.notna().mean()), 4)}
    loc["censusGeoid_lengths"] = c.censusGeoid.str.len().value_counts(dropna=False).rename(str).to_dict()
    dec = c.latitude.dropna().map(lambda v: len(repr(v).split(".")[1]) if "." in repr(v) else 0)
    loc["lat_decimals"] = dec.value_counts().rename(str).to_dict()
    loc["distinct_latlon_points"] = int(c[["latitude", "longitude"]].drop_duplicates().shape[0])
    out["location"] = loc

    # vintage
    vc = c.vintage_class.value_counts()
    out["vintage_claims"] = vc.to_dict()
    out["vintage_codes"] = c.groupby("vintage_class").tract_raw.nunique().to_dict()
    shared = c[c.vintage_class == "shared_changed"].tract_raw.unique()
    out["shared_changed_land_kept"] = keep_share.reindex(shared).describe().round(3).to_dict()
    yb = pd.cut(c.yearOfLoss, [1977, 1999, 2009, 2019, 2026], labels=["1978-1999", "2000-2009", "2010-2019", "2020-2026"])
    out["vintage_by_period"] = pd.crosstab(yb, c.vintage_class).to_dict(orient="index")

    alloc = to_2020(c, r)
    conv = alloc[alloc.vintage_class == "2010_only"]
    dom = conv.groupby("id").w.max()
    out["converted_claims"] = int(conv.id.nunique())
    out["converted_codes"] = int(conv.tract_raw.nunique())
    out["converted_claims_dominant_ge_0_9"] = int((dom >= 0.9).sum())
    out["converted_target_tracts"] = int(conv.GEOID.nunique())
    assert np.allclose(alloc.groupby("id").w.sum(), 1.0)
    out["unassigned_claims"] = int(len(c) - alloc.id.nunique())

    # sensitivity: shared-changed codes treated as 2010 instead of 2020
    alt = c.copy()
    alt.loc[alt.vintage_class == "shared_changed", "vintage_class"] = "2010_only"
    alloc_alt = to_2020(alt, r)
    moved = alloc_alt[alloc_alt.tract_raw != alloc_alt.GEOID].w.sum() - alloc[alloc.tract_raw != alloc.GEOID].w.sum()
    out["shared_as_2010_claims_moved"] = round(float(moved), 1)

    # tract-by-year table (2020 GEOIDs)
    alloc["n"] = alloc.w
    alloc["n_paid"] = alloc.w * alloc.is_paid
    alloc["bld"] = alloc.w * alloc.amountPaidOnBuildingClaim.fillna(0)
    alloc["cnt"] = alloc.w * alloc.amountPaidOnContentsClaim.fillna(0)
    alloc["direct_n"] = np.where(alloc.vintage_class == "2010_only", 0.0, alloc.w)
    ty = (alloc.groupby(["GEOID", "yearOfLoss"])
          .agg(claims=("n", "sum"), claims_paid=("n_paid", "sum"), paid_building=("bld", "sum"),
               paid_contents=("cnt", "sum"), claims_not_converted=("direct_n", "sum"))
          .reset_index().rename(columns={"yearOfLoss": "year"}))
    ty["paid_building_contents"] = ty.paid_building + ty.paid_contents
    ty["share_converted_from_2010"] = 1 - ty.claims_not_converted / ty.claims
    ty = ty.drop(columns="claims_not_converted")
    for k in ("claims", "claims_paid"):
        ty[k] = ty[k].round(4)
    for k in ("paid_building", "paid_contents", "paid_building_contents"):
        ty[k] = ty[k].round(2)
    ty["share_converted_from_2010"] = ty.share_converted_from_2010.round(4)
    paths.IMPACT_DIR.mkdir(parents=True, exist_ok=True)
    ty.to_csv(paths.NFIP_TRACT_YEAR_CSV, index=False)
    out["tract_year_rows"] = len(ty)
    out["tract_year_tracts"] = int(ty.GEOID.nunique())
    frame = set(t.GEOID)
    out["tracts_outside_frame"] = sorted(set(ty.GEOID) - frame)
    out["claims_outside_frame"] = round(float(ty[~ty.GEOID.isin(frame)].claims.sum()), 1)
    assert abs(ty.claims.sum() - (len(c) - out["unassigned_claims"])) < 0.5

    # county by year, storm years
    by_year = c.groupby("yearOfLoss").agg(claims=("id", "size"), claims_paid=("is_paid", "sum"),
                                         paid_building_contents=("paid_bc", "sum")).reset_index()
    full = pd.DataFrame({"yearOfLoss": range(out["years"][0], out["years"][1] + 1)})
    by_year = full.merge(by_year, how="left").fillna(0)
    ev = (c.assign(ev=c.floodEvent.fillna("(no event name)"))
          .groupby(["yearOfLoss", "ev"]).size().reset_index(name="n")
          .sort_values("n", ascending=False).drop_duplicates("yearOfLoss"))
    by_year = by_year.merge(ev.rename(columns={"ev": "largest_named_event", "n": "event_claims"}),
                            how="left", on="yearOfLoss")
    paths.OUT_IMPACT.mkdir(parents=True, exist_ok=True)
    by_year.to_csv(paths.OUT_IMPACT / "nfip_claims_by_year.csv", index=False)
    events = (c.groupby("floodEvent").agg(claims=("id", "size"), year=("yearOfLoss", "min"),
                                         paid=("paid_bc", "sum")).sort_values("claims", ascending=False))
    out["top_events"] = events.head(10).round(0).reset_index().to_dict(orient="records")
    out["no_event_name_claims"] = int(c.floodEvent.isna().sum())
    out["by_year_top10"] = by_year.sort_values("claims", ascending=False).head(10).to_dict(orient="records")
    return out, ty


# ----------------------------------------------------------------------------
# 2. HMA subapplications and the SCALE-R match
# ----------------------------------------------------------------------------
HMA_JUR = {
    "Aventura": "Aventura", "City of Opa-locka": "Opa-Locka",
    "Opa-locka (corporate name for Opa-Locka)": "Opa-Locka", "Coral Gables": "Coral Gables",
    "Cutler Bay, Town of": "Cutler Bay", "Doral": "Doral", "Florida City": "Florida City",
    "Golden Beach": "Golden Beach", "Hialeah": "Hialeah", "HIALEAH HOUSING AUTHORITY": "Hialeah",
    "Homestead": "Homestead", "Key Biscayne": "Key Biscayne", "Miami": "Miami", "Miami (CCD)": "Miami",
    "Miami Beach": "Miami Beach", "MIAMI SHORES VILLAGE": "Miami Shores",
    "Miami Shores (Arch Creek)": "Miami Shores", "Miami Springs (Country Club Estates)": "Miami Springs",
    "North Bay Village": "North Bay Village", "North Miami": "North Miami",
    "North Miami Beach": "North Miami Beach", "PALMETTO BAY, VILLAGE OF": "Palmetto Bay",
    "Pinecrest": "Pinecrest", "Sweetwater": "Sweetwater", "Virginia Gardens": "Virginia Gardens",
    "West Miami": "West Miami",
    "Dade (County)": "Miami-Dade County", "Miami-Dade (County)": "Miami-Dade County",
    "Miami-Dade County": "Miami-Dade County", "Miami-Dade County DERM": "Miami-Dade County",
    "MIAMI-DADE COUNTY PARK AND RECREATION DEPARTMENT": "Miami-Dade County",
    "DADE COUNTY SEAPORT DEPT": "Miami-Dade County", "CRANDON PARK TENNIS CTR": "Miami-Dade County",
    "Miami-Dade Co. Public Housing & Comm. Dev.": "Miami-Dade County",
    "PUBLIC H HEALTH TRUST": "Miami-Dade County", "PUBLIC HEALTH TRUST": "Miami-Dade County",
    "S FLORIDA WATER MANAGEMENT DISTRICT": "SFWMD", "SOUTH FLORIDA WATER MANAGEMENT": "SFWMD",
}

# keywords in the SCALE-R project name or description that fit each HMA activity
ACTIVITY_WORDS = {
    "Generator": r"generator|backup power|emergency power",
    "Retrofit": r"shutter|window|door|roof|harden|retrofit|wind|impact|storm mitigation",
    "Flood control": r"drain|stormwater|flood|pump|canal|culvert|seawall|swale|well|outfall",
    "Utility and infrastructure protection": r"utility|lift station|pump|water|sewer|harden|power|substation",
    "Elevation": r"elevat|raise",
    "Floodproofing": r"floodproof|flood proof|flood barrier",
    "Acquisition": r"acqui|buyout|purchase",
    "Stabilization and restoration": r"stabiliz|restor|dune|shoreline",
    "Feasibility, engineering and design studies": r"study|plan|design|assessment|feasibility|master plan",
}


def norm_jur(s):
    s = (s or "").strip()
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return s


def is_round(v, step):
    return abs(v / step - round(v / step)) < 1e-9


def hma(t):
    h = pd.read_csv(paths.HMA_PROJECTS_CSV, dtype=str)
    out = {"rows": len(h)}
    out["by_program"] = h.program.value_counts().to_dict()
    out["by_status"] = h.status.value_counts().to_dict()
    out["by_subapplicationType"] = h.subapplicationType.value_counts().to_dict()
    out["by_activity"] = h.primaryActivity.value_counts().to_dict()
    out["by_hazard"] = h.primaryHazard.value_counts(dropna=False).rename(str).to_dict()
    out["fiscal_years"] = [int(h.fiscalYear.astype(int).min()), int(h.fiscalYear.astype(int).max())]
    out["disasters"] = h.disasterNumber.value_counts().head(8).to_dict()
    date_cols = [k for k in h.columns if "date" in k.lower()] + ["fiscalYear", "proposedProjectStartDate",
                                                                   "proposedProjectEndDate", "estimatedTotalDuration"]
    date_cols = list(dict.fromkeys(date_cols))
    out["date_fields"] = {k: round(float(h[k].notna().mean()), 4) for k in date_cols}
    out["title_filled"] = int(h.subapplicationTitle.notna().sum())
    amt = {}
    for k in ("totalSubapplicationAmount", "federalShareAmount", "totalObligatedAmount", "bcaTotalCosts"):
        h[k + "_n"] = pd.to_numeric(h[k], errors="coerce")
        amt[k] = {"filled": int(h[k + "_n"].notna().sum()), "sum": float(h[k + "_n"].sum())}
    out["amounts"] = amt
    h["jur"] = h.subapplicantName.map(HMA_JUR)
    out["jurisdiction_mapped"] = int(h.jur.notna().sum())

    p = pd.read_csv(paths.PROJECT_CSV, dtype=str, encoding="utf-8-sig")
    p["jur"] = p.Jurisdiction.map(norm_jur)
    p["cost"] = pd.to_numeric(p.Estimated_Cost, errors="coerce")
    text = (p.Project_Name.fillna("") + " " + p.Project_Description.fillna("")).str.lower()

    cited = text.map(lambda s: set(re.findall(r"dr-?\s?(\d{4})", s)))

    cand = []
    for _, x in h.iterrows():
        for field in ("totalSubapplicationAmount", "federalShareAmount", "bcaTotalCosts"):
            v = x[field + "_n"]
            if pd.isna(v) or v <= 0:
                continue
            d = (p.cost - v).abs()
            for j in p.index[d <= 0.02 * v]:
                pj = p.at[j, "jur"]
                if not isinstance(x.jur, str):
                    jf = "unknown"
                elif x.jur == pj:
                    jf = "same"
                elif x.jur == "Miami-Dade County" and pj != "SFWMD":
                    jf = "county_agency"   # a county body can work inside a city
                else:
                    jf = "different"
                pat = ACTIVITY_WORDS.get(x.primaryActivity)
                act = "unknown" if pat is None else ("yes" if re.search(pat, text[j]) else "no")
                cand.append({
                    "Project_ID": p.at[j, "Project_ID"], "Project_Name": p.at[j, "Project_Name"],
                    "scaler_jurisdiction": pj, "scaler_cost": p.at[j, "cost"],
                    "scaler_reported_year": p.at[j, "Reported_Year"], "scaler_status": p.at[j, "Project_Status"],
                    "hma_id": x.subapplicationIdentifier, "hma_subapplicant": x.subapplicantName,
                    "hma_jurisdiction": x.jur, "hma_activity": x.primaryActivity, "hma_status": x.status,
                    "hma_program": x.program, "hma_disaster": x.disasterNumber,
                    "hma_amount_field": field, "hma_amount": v,
                    "abs_diff": float(d[j]), "rel_diff": float(d[j] / v), "jurisdiction_fit": jf,
                    "scaler_cites_same_disaster": bool(x.disasterNumber and x.disasterNumber in cited[j]),
                    "activity_fits_name": act,
                    "hma_date_submitted_to_fema": (x.dateSubmittedToFema or "")[:10],
                    "hma_fiscal_year": x.fiscalYear,
                })
    m = pd.DataFrame(cand)
    out["candidates_any_jurisdiction"] = len(m)
    m = m.sort_values("abs_diff").drop_duplicates(["Project_ID", "hma_id"]).reset_index(drop=True)
    exact = m.abs_diff <= 1
    # One-to-one is judged among plausible candidates (same jurisdiction, county agency, or the
    # SCALE-R name cites the same disaster). Exact matches are judged among exact candidates only,
    # and re-filings of one application (same subapplicant and amount under several disasters)
    # count once.
    plaus = m[m.jurisdiction_fit.isin(["same", "county_agency"]) | m.scaler_cites_same_disaster]
    pe = plaus[plaus.abs_diff <= 1]
    m["app_key"] = m.hma_subapplicant + "|" + m.hma_amount.round(2).astype(str)
    pe = pe.assign(app_key=pe.hma_subapplicant + "|" + pe.hma_amount.round(2).astype(str))
    m["n_exact_scaler_for_app"] = m.app_key.map(pe.groupby("app_key").Project_ID.nunique()).fillna(0).astype(int)
    m["n_exact_apps_for_scaler"] = m.Project_ID.map(pe.groupby("Project_ID").app_key.nunique()).fillna(0).astype(int)
    m["n_near_scaler_for_hma"] = m.hma_id.map(plaus.groupby("hma_id").Project_ID.nunique()).fillna(0).astype(int)
    m["n_near_hma_for_scaler"] = m.Project_ID.map(plaus.groupby("Project_ID").hma_id.nunique()).fillna(0).astype(int)
    one2one_exact = (m.n_exact_scaler_for_app == 1) & (m.n_exact_apps_for_scaler == 1)
    one2one = one2one_exact.where(exact, (m.n_near_scaler_for_hma == 1) & (m.n_near_hma_for_scaler == 1))
    hma_specific = ~m.hma_amount.map(lambda v: is_round(v, 1000))
    hma_not_10k = ~m.hma_amount.map(lambda v: is_round(v, 10000))
    scaler_specific = ~m.scaler_cost.map(lambda v: is_round(v, 1000))

    def rule(i):
        r = m.loc[i]
        ok_act = r.activity_fits_name != "no"
        same, county, dr = r.jurisdiction_fit == "same", r.jurisdiction_fit == "county_agency", r.scaler_cites_same_disaster
        if exact[i] and hma_specific[i] and one2one[i] and ok_act and (same or dr):
            return "high", ("H: cost equal to the dollar and not a multiple of $1,000; one-to-one; activity does not "
                            "contradict the name; same jurisdiction or the SCALE-R name cites the same disaster number. "
                            "Re-filings of one application under several disasters count as one; the earliest "
                            "submission date is the one to use")
        if one2one[i] and ok_act and ((same and ((exact[i] and hma_not_10k[i]) or
                                                 (r.rel_diff <= 0.01 and hma_specific[i] and scaler_specific[i])))
                                      or (county and exact[i] and hma_specific[i])):
            return "medium", ("M: one-to-one; activity does not contradict the name; and either same jurisdiction with "
                              "cost equal (a multiple of $1,000 but not $10,000) or within 1% with neither cost a "
                              "multiple of $1,000, or a county agency subapplicant with cost equal to the dollar")
        if same or county or dr:
            return "low", ("L: plausible jurisdiction and cost within 2%, but round cost, not one-to-one, "
                           "or activity contradicts the name")
        if exact[i] and hma_specific[i]:
            return "low", "L: cost equal to the dollar and not round, but jurisdiction differs or is unknown"
        return None, None

    res = [rule(i) for i in m.index]
    m["match_confidence"] = [a for a, _ in res]
    m["match_rule"] = [b for _, b in res]
    m = m[m.match_confidence.notna()].copy()
    order = {"high": 0, "medium": 1, "low": 2}
    m = m.sort_values(["match_confidence", "abs_diff"], key=lambda s: s.map(order) if s.name == "match_confidence" else s)
    m.to_csv(paths.HMA_MATCHES_CSV, index=False)
    out["match_rows"] = m.match_confidence.value_counts().to_dict()
    out["match_scaler_projects"] = m.groupby("match_confidence").Project_ID.nunique().to_dict()
    hm = m[m.match_confidence.isin(["high", "medium"])]
    out["scaler_projects_dated_high_or_medium"] = int(hm.Project_ID.nunique())
    out["scaler_projects_dated_high"] = int(m[m.match_confidence == "high"].Project_ID.nunique())
    out["examples_high_medium"] = hm[["Project_ID", "Project_Name", "scaler_jurisdiction", "scaler_cost",
                                      "hma_id", "hma_activity", "hma_amount_field", "hma_amount",
                                      "hma_date_submitted_to_fema", "match_confidence"]].to_dict(orient="records")
    return out


# ----------------------------------------------------------------------------
# 3. First look against the tract table
# ----------------------------------------------------------------------------
def first_look(t, ty):
    tot = ty.groupby("GEOID").agg(claims=("claims", "sum"), paid=("paid_building_contents", "sum"))
    d = t[["GEOID", "jurisdiction", "population", "low_pop_flag", "nri_eal_per_person", "slr_3ft_pop_share",
           "surge_cat3_any_pop_share", "sited_dollars"]].merge(tot, on="GEOID", how="left")
    d[["claims", "paid"]] = d[["claims", "paid"]].fillna(0)
    d["claims_per_1000"] = d.claims / d.population * 1000
    d["paid_per_resident"] = d.paid / d.population
    d["sited_per_resident"] = d.sited_dollars / d.population
    tr = d[d.low_pop_flag == 0]
    out = {"n_tracts": len(tr), "tracts_zero_claims": int((tr.claims == 0).sum())}
    cols = {"nri_eal_per_person": "FEMA expected annual loss per resident",
            "slr_3ft_pop_share": "share of residents in 3 ft sea level rise area",
            "surge_cat3_any_pop_share": "share of residents in Category 3 surge area",
            "sited_per_resident": "sited investment per resident"}
    rows = []
    for y in ("claims", "claims_per_1000", "paid", "paid_per_resident"):
        for x, lab in cols.items():
            ok = tr[[x, y]].dropna()
            rho, pv = spearmanr(ok[x], ok[y])
            rows.append({"claims_measure": y, "variable": x, "label": lab, "n": len(ok),
                         "spearman_rho": round(float(rho), 3), "p_value": float(f"{pv:.3g}")})
    sp = pd.DataFrame(rows)
    sp.to_csv(paths.OUT_IMPACT / "nfip_spearman.csv", index=False)
    out["spearman"] = rows
    # same correlations for the recent period only (2010 onward), as a check
    rec = ty[ty.year >= 2010].groupby("GEOID").claims.sum()
    tr2 = tr.assign(claims_2010=tr.GEOID.map(rec).fillna(0))
    tr2["claims_2010_per_1000"] = tr2.claims_2010 / tr2.population * 1000
    out["spearman_2010_on"] = [{"variable": x, "rho_total": round(float(spearmanr(tr2[x], tr2.claims_2010, nan_policy="omit")[0]), 3),
                                "rho_per_1000": round(float(spearmanr(tr2[x], tr2.claims_2010_per_1000, nan_policy="omit")[0]), 3)}
                               for x in cols]
    top_c = d.sort_values("claims", ascending=False).head(20)
    top_p = d.sort_values("paid", ascending=False).head(20)
    keep = ["GEOID", "jurisdiction", "population", "claims", "claims_per_1000", "paid", "paid_per_resident",
            "low_pop_flag"]
    top_c[keep].to_csv(paths.OUT_IMPACT / "top20_tracts_by_claims.csv", index=False)
    top_p[keep].to_csv(paths.OUT_IMPACT / "top20_tracts_by_paid.csv", index=False)
    out["top_claims"] = top_c[keep].round(2).to_dict(orient="records")
    out["top_paid"] = top_p[keep].round(0).to_dict(orient="records")
    out["overlap_top20"] = len(set(top_c.GEOID) & set(top_p.GEOID))
    out["top20_claims_share"] = round(float(top_c.claims.sum() / d.claims.sum()), 3)
    out["top20_paid_share"] = round(float(top_p.paid.sum() / d.paid.sum()), 3)
    out["top20_jurisdictions_claims"] = top_c.jurisdiction.value_counts().to_dict()
    out["top20_jurisdictions_paid"] = top_p.jurisdiction.value_counts().to_dict()
    return out


def main():
    t = load_table()
    LOG["nfip"], ty = nfip(t)
    LOG["hma"] = hma(t)
    LOG["first_look"] = first_look(t, ty)
    (paths.OUT_IMPACT / "fema_first_look_log.json").write_text(json.dumps(LOG, indent=1, default=str))
    print(json.dumps(LOG, indent=1, default=str))


if __name__ == "__main__":
    main()
