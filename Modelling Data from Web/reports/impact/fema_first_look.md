# FEMA flood claims and mitigation grants: a first look

Written 8 November 2026. Descriptive only: no model was fitted. Decisions
D-113 to D-118 in `DECISIONS.md`.

## In short

- **62,029 flood insurance claims** were filed in Miami-Dade from 1978 to
  2026. 36,722 of them (59%) were paid. Together they paid **$855.8 million**
  for buildings and contents (not adjusted for inflation).
- **Five years hold 75% of all claims:** 1999 (Hurricane Irene), 2000 (an
  October flood that FEMA labels only "Flooding"), 2005 (Katrina), 1992
  (Andrew) and 2017 (Irma).
- **Claims carry a mix of 2010 and 2020 census tract codes.** The mix is
  record by record, not year by year. 23,512 claims (38%) sit on 2010 tracts
  that were later split. They were shared out to 2020 tracts by land area.
  Their tract-level numbers are approximate.
- **Tracts with more claims tend to have higher FEMA expected loss**
  (Spearman 0.38; 0.41 per 1,000 residents). The links with sea level rise
  exposure, storm surge exposure and sited investment are weaker (0.11 to
  0.20).
- **The mitigation grant data could date only 15 SCALE-R projects** (12 high
  and 3 medium confidence). FEMA's Miami-Dade grant records have no project
  titles, so names could not be matched. The only usable date is the day the
  application reached FEMA. There are no approval or close dates.

## 1. Sources

| Input | Publisher | Dataset and version | Data years | Released | Where it came from | Rows |
|---|---|---|---|---|---|---|
| Flood insurance claims | FEMA (OpenFEMA) | NFIP Redacted Claims, API entity `NfipClaims` v3. The brief's name `FimaNfipClaims` no longer exists (it returns 404). Record `asOfDate` 8 Sep 2026 | loss years 1978 to 2026 | last data refresh 9 Sep 2026 | https://www.fema.gov/api/open/v3/NfipClaims, filter `countyCode eq '12086'`, downloaded 8 Nov 2026 | 62,029 (equal to the API count) |
| Mitigation grants | FEMA (OpenFEMA) | HMA Subapplications, API entity `HmaSubapplications` v2. The brief's `HazardMitigationAssistanceProjects` is no longer served (404 for v1 to v4); this is its successor | fiscal years 1999 to 2025 | last data refresh 8 Nov 2026 | https://www.fema.gov/api/open/v2/HmaSubapplications, Florida rows whose benefiting counties include Miami-Dade, plus 5 rows with no county from Miami-Dade bodies (D-114), downloaded 8 Nov 2026 | 288 (283 + 5) |
| 2010 to 2020 tract conversion | US Census Bureau | 2020 Census Tract to 2010 Census Tract Relationship File (national) | 2010 and 2020 tracts | 2021 | https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt, downloaded 8 Nov 2026 | 126,450 (all states) |
| 2020 tract and block group lists | US Census Bureau | TIGER/Line 2024 | 1 Jan 2024 | 2024 | `data/raw/boundaries/tl_2024_12_tract.zip`, `tl_2024_12_bg.zip` (already in the project) | 707 county tracts |
| Tract table | this project | the table the ML scripts load (`ml_common.load_table()`): population, jurisdiction, FEMA expected annual loss, exposure shares, sited dollars | as in `reports/ml/model_card.md` | 5 Nov 2026 | `outputs/ml/stage1/model_table_tract.csv` and `data/processed/exposure/exposure_tract.csv` | 698 tracts; 697 used |
| Projects | SCALE-R project team | SCALE-R project database | document years 1998 to 2026 | 2026 | `data/raw/projects/SCALE-R_Database.csv` (read only, not edited) | 1,664 projects |

Raw files: `data/raw/fema/` (paths in `scripts/common/paths.py`); the API
queries, counts and refresh dates are in `data/raw/fema/download_log.json`.
Scripts: `scripts/impact/download_fema.py`, then
`scripts/impact/fema_first_look.py`.

## 2. Flood insurance claims

### What is in the file

- **62,029 claims, loss years 1978 to 2026.** 2026 is partial: the records
  run to early September.
- **Money:** $673.4 million paid on buildings and $182.4 million on
  contents. Increased cost of compliance payments are left out, as asked. No
  row has a negative payment.
- **About 4 in 10 claims paid nothing** (25,307). They count as claims in
  the tables. A separate "claims paid" column counts only those with
  money paid.

### Location fields

| Field | What it is | Filled |
|---|---|---|
| `censusGeoid` | 12-digit census block group code. The tract is its first 11 digits. There is no separate tract field | 61,869 (99.7%) |
| `latitude`, `longitude` | rounded by FEMA to 1 decimal place (about 11 km) for privacy. Only 29 distinct points cover the whole county | 100%, but too coarse to place a claim in a tract |
| `reportedZipCode` | ZIP code | 61,966 (99.9%) |
| `nfipCommunityName` | the city or county flood insurance community | 61,996 (99.95%) |
| `reportedCity` | always "Currently Unavailable" | 0% |
| `countyCode` | 12086 for every row | 100% |

So the block group code is the only usable small-area location.

### Census tract vintage

The data dictionary does not say which census the codes come from. Checking
every code against both censuses showed a mix:

| Tract code is... | Claims | Distinct codes | How it was handled |
|---|---|---|---|
| the same tract in 2010 and 2020 (same code, at least 99% of land shared) | 33,382 | 327 | kept as is |
| a 2020 tract only | 2,380 | 253 | kept as is |
| valid in both censuses but the shape changed | 2,588 | 25 | kept as a 2020 tract (D-115). These tracts keep a median 98% of their land (lowest 81%). Treating them as 2010 instead would move only 88 claims |
| a 2010 tract only | 23,512 | 160 | **converted**: shared out to the 365 2020 tracts it overlaps, by land area |
| missing | 160 | | not placed in a tract; kept in county totals |
| not a valid Miami-Dade code (5 invalid, 2 Broward) | 7 | 6 | not placed; kept in county totals |

- **The mix is per record, not per year.** 2010-only codes still appear in
  2023 claims. 2020-only codes appear in 1990s claims.
- **Most converted claims are split across several tracts.** Only 794 of
  the 23,512 had 90% or more of their 2010 tract's land in a single 2020
  tract. The rest were shared out by land area, which assumes insured
  buildings are spread evenly over the land. That is rough. A better split
  would weight by 2020 housing or population per block. That needs the
  block-level relationship file, which was not downloaded (not asked for).
- **Result:** 341 of the 701 tracts in the tract-by-year table get more than
  half their claims from conversion. The table has a
  `share_converted_from_2010` column so these can be flagged.

### The tract-by-year table

`data/processed/impact/nfip_claims_tract_year.csv`: 10,912 rows, 701 2020
tracts, years 1978 to 2026. Columns:

- **claims**, **claims_paid**: can be fractional because of the land-area
  split.
- **paid_building**, **paid_contents**, **paid_building_contents**: in
  nominal dollars.
- **share_converted_from_2010**.

It totals 61,862 claims and $852.0 million: everything except the 167
claims with no usable tract. Five special land-use tracts (codes 9802 to
9812, outside the 698-tract frame) hold 32 claims.

## 3. Claims per year

County totals, all claims (paid and unpaid). Full series:
`outputs/impact/nfip_claims_by_year.csv`.

| Year | Claims | Paid (million $) | Largest named event in FEMA's data |
|---|---|---|---|
| 1992 | 8,390 | 140.5 | Hurricane Andrew (8,025) |
| 1999 | 13,393 | 91.5 | Hurricane Irene (12,658) |
| 2000 | 11,091 | 146.8 | "Flooding" (10,744; October 2000 floods) |
| 2005 | 9,717 | 124.4 | Hurricane Katrina (6,622); Wilma 2,073 |
| 2009 | 830 | 26.5 | no event name |
| 2017 | 4,100 | 108.7 | Hurricane Irma (3,765) |
| 2020 | 1,526 | 58.2 | no event name for 930; Hurricane Eta 586 |
| 2024 | 864 | 52.9 | June South Florida Flooding (760) |

- **Five years hold 75% of all claims:** 1999, 2000, 2005, 1992 and 2017.
  In most other years there are a few hundred claims.
- **Recent claims are fewer but cost more.** The 2024 June rain flood had
  760 claims and $52 million paid, about $69,000 per claim. Irene in 1999
  averaged under $7,000.
- **13,333 claims have no event name**, so the event column is a guide only.

## 4. Top 20 tracts

Totals over 1978 to 2026, nominal dollars. Full tables:
`outputs/impact/top20_tracts_by_claims.csv`, `top20_tracts_by_paid.csv`.

**By number of claims**

| Rank | Tract | Jurisdiction | Residents | Claims | Per 1,000 residents | Paid (million $) |
|---|---|---|---|---|---|---|
| 1 | 12086004602 | Key Biscayne | 4,513 | 1,367 | 303 | 45.5 |
| 2 | 12086008000 | Coral Gables | 4,695 | 1,154 | 246 | 35.7 |
| 3 | 12086020002 | Unincorporated | 4,666 | 809 | 173 | 9.4 |
| 4 | 12086006802 | Miami | 3,726 | 641 | 172 | 21.9 |
| 5 | 12086010610 | Cutler Bay | 4,327 | 600 | 139 | 17.5 |
| 6 | 12086014500 | Unincorporated | 4,142 | 598 | 144 | 6.9 |
| 7 | 12086015400 | Unincorporated | 5,358 | 575 | 107 | 5.7 |
| 8 | 12086010209 | Unincorporated | 6,718 | 569 | 85 | 13.5 |
| 9 | 12086009704 | Unincorporated | 5,729 | 538 | 94 | 10.9 |
| 10 | 12086009066 | Unincorporated | 7,210 | 528 | 73 | 27.1 |
| 11 | 12086018601 | Unincorporated | 4,309 | 443 | 103 | 3.1 |
| 12 | 12086009102 | Unincorporated | 3,213 | 439 | 137 | 22.6 |
| 13 | 12086009703 | Unincorporated | 3,455 | 429 | 124 | 6.1 |
| 14 | 12086020100 | Unincorporated | 4,264 | 416 | 98 | 4.3 |
| 15 | 12086004000 | Miami Beach | 5,449 | 389 | 71 | 5.3 |
| 16 | 12086020001 | Unincorporated | 2,101 | 388 | 185 | 4.9 |
| 17 | 12086018602 | Unincorporated | 3,877 | 388 | 100 | 2.7 |
| 18 | 12086011500 | Unincorporated | 5,483 | 386 | 70 | 3.1 |
| 19 | 12086007300 | Miami | 4,324 | 382 | 88 | 23.4 |
| 20 | 12086003906 | Miami Beach | 2,760 | 372 | 135 | 6.2 |

**By dollars paid**

| Rank | Tract | Jurisdiction | Claims | Paid (million $) | Paid per resident ($) |
|---|---|---|---|---|---|
| 1 | 12086004602 | Key Biscayne | 1,367 | 45.5 | 10,087 |
| 2 | 12086008000 | Coral Gables | 1,154 | 35.7 | 7,609 |
| 3 | 12086009066 | Unincorporated | 528 | 27.1 | 3,760 |
| 4 | 12086007300 | Miami | 382 | 23.4 | 5,402 |
| 5 | 12086009102 | Unincorporated | 439 | 22.6 | 7,041 |
| 6 | 12086006802 | Miami | 641 | 21.9 | 5,890 |
| 7 | 12086010610 | Cutler Bay | 600 | 17.5 | 4,038 |
| 8 | 12086009010 | Doral | 372 | 17.3 | 2,354 |
| 9 | 12086000134 | Aventura | 263 | 14.7 | 4,388 |
| 10 | 12086010209 | Unincorporated | 569 | 13.5 | 2,009 |
| 11 | 12086004607 | Key Biscayne | 309 | 11.6 | 2,617 |
| 12 | 12086009704 | Unincorporated | 538 | 10.9 | 1,899 |
| 13 | 12086008205 | Palmetto Bay | 271 | 10.5 | 2,643 |
| 14 | 12086013700 | Hialeah Gardens | 191 | 10.4 | 1,655 |
| 15 | 12086020002 | Unincorporated | 809 | 9.4 | 2,007 |
| 16 | 12086000228 | Unincorporated | 371 | 8.3 | 2,724 |
| 17 | 12086000310 | Unincorporated | 363 | 7.8 | 1,866 |
| 18 | 12086010212 | Unincorporated | 306 | 7.0 | 2,063 |
| 19 | 12086009031 | Unincorporated | 88 | 6.9 | 1,533 |
| 20 | 12086014500 | Unincorporated | 598 | 6.9 | 1,656 |

- **Losses are concentrated.** The top 20 tracts by claims hold 18.5% of all
  claims. The top 20 by dollars hold 39% of all money paid.
- **11 tracts are on both lists.** Key Biscayne tract 4602 and Coral Gables
  tract 8000 lead both by a wide margin.
- **Unincorporated Miami-Dade has 13 of the top 20 by claims** and 10 of the
  top 20 by dollars.

## 5. How claims line up with risk and investment

Spearman rank correlations over the 697 training tracts (the one tract under
100 residents is left out, as in the ML work). Claims are totals for 1978 to
2026 on 2020 tracts. "Per 1,000 residents" uses today's population (ACS
2020 to 2024). Full table: `outputs/impact/nfip_spearman.csv`.

| Compared with | Claims | Claims per 1,000 residents | Dollars paid | Dollars paid per resident |
|---|---|---|---|---|
| FEMA expected annual loss per resident (`nri_eal_per_person`) | 0.38 | 0.41 | 0.32 | 0.34 |
| Share of residents in the 3 ft sea level rise area (`slr_3ft_pop_share`) | 0.11 | 0.16 | 0.30 | 0.33 |
| Share of residents in the Category 3 surge area (`surge_cat3_any_pop_share`) | 0.20 | 0.20 | 0.34 | 0.34 |
| Sited investment per resident (`sited_dollars / population`) | 0.15 | 0.16 | 0.24 | 0.25 |

All p-values are below 0.005. Only 2 of the 697 tracts have no claims at all.

- **FEMA's expected loss lines up best with how many claims a tract has.**
- **Sea level rise and surge exposure line up better with dollars than
  with claim counts.** Coastal claims cost more per claim.
- **The counts are dominated by 1999 and 2000.** Those floods were inland
  rain floods. Counting only claims from 2010 on, the sea level rise link
  rises to 0.39 (0.43 per 1,000 residents). Surge is then 0.32 and expected
  loss 0.32.
- **Places with more past claims get somewhat more sited investment per
  resident** (0.15 to 0.25). The link is weak.

**Cautions.**
- **Claims count insured homes, not all damage.** Tracts where few people
  carry flood insurance will look safer than they are.
- **Dividing 48 years of claims by today's population** is a rough rate.
- **38% of claims reach their tract through the land-area split** (section 2).
- **Correlation here says nothing about cause.**

## 6. Mitigation grants (HMA subapplications)

### What is in the file

288 subapplications (D-114).

- **Program:**
  - Hazard Mitigation Grant Program: 281;
  - Pre-Disaster Mitigation: 4;
  - HMGP Post Fire: 2;
  - Flood Mitigation Assistance: 1.
- **Status:**
  - Closed: 183;
  - Pending: 59;
  - Approved: 42;
  - Not Approved or Denied: 3;
  - Withdrawn: 1.
- **Activity:**
  - Retrofit: 187 (mostly wind retrofits such as shutters and windows);
  - Flood control: 36;
  - Generator: 21;
  - Studies and design: 20;
  - Utility and infrastructure protection: 13;
  - Other: 5;
  - Elevation: 3;
  - Floodproofing, acquisition, stabilization: 1 each.
- **Main hazard:**
  - hurricane: 169;
  - wind: 71;
  - flood: 30;
  - severe storm: 10;
  - none given: 8.
- **Largest disasters:**
  - DR-1609 (Wilma, 2005): 56;
  - DR-4337 (Irma, 2017): 41;
  - DR-1345 (declared in fiscal 2001, the October 2000 floods): 33.
- **Money:** total subapplication amounts sum to $1.66 billion and the
  federal share to $348 million.
- **Who applied:** 197 of the 288 rows come from a city, the county or a
  county agency, or the water district. The rest are hospitals,
  universities, nonprofits and state agencies.

### Date fields

| Field | Filled |
|---|---|
| `dateSubmittedToFema` | 100% |
| `fiscalYear` (for disaster grants, the year the disaster was declared) | 100% |
| `estimatedTotalDuration` (months) | 1.7% |
| `dateInitiatedInSystem`, `dateSubmittedToApplicant`, `proposedProjectStartDate`, `proposedProjectEndDate`, `eo12372ReviewDate`, `dateMitigationPlanApproved` | 0% |

The dataset has **no approval date and no close date**. Status says whether
a grant is closed, but not when. So the only real date is when the
application reached FEMA, which is an application date, not a build date.

### Matching to SCALE-R projects

**No names to match on.** `subapplicationTitle` is empty in all 288
Miami-Dade rows. Matching therefore uses:

- **cost:** the SCALE-R `Estimated_Cost` against the FEMA total amount,
  federal share or benefit-cost total cost;
- **jurisdiction:** FEMA's applicant mapped to a SCALE-R jurisdiction by
  hand (D-117);
- **two checks on the name:**
  - whether the SCALE-R name or description cites the same disaster
    number (for example "HMGP DR-4337");
  - whether FEMA's activity type contradicts the SCALE-R name (for example
    a generator grant against a drainage project).

| Confidence | Rule | SCALE-R projects | Candidate pairs |
|---|---|---|---|
| High | Cost equal to the dollar and not a multiple of $1,000. One-to-one. Activity does not contradict the name. Same jurisdiction, or the SCALE-R name cites the same disaster number | 12 | 14 |
| Medium | One-to-one, and activity does not contradict the name, plus one of: same jurisdiction with an equal cost that is a multiple of $1,000 but not of $10,000; same jurisdiction with costs within 1% and neither a multiple of $1,000; or a county agency applicant with cost equal to the dollar | 3 | 3 |
| Low | Any other pair within 2% where the jurisdiction is plausible, or an exact non-round cost with a different jurisdiction. Not to be used as a date | 1,035 | 2,207 |

"One-to-one" means:
- **for exact matches:** no other plausible candidate has the same exact
  cost;
- **for re-filings:** one application re-filed under several disasters
  (same applicant, same amount) counts once.

**15 SCALE-R projects get a FEMA date at high or medium confidence.** That
is 0.9% of the 1,664 projects.

| Project | SCALE-R status | FEMA ID | FEMA status | Submitted to FEMA | Confidence |
|---|---|---|---|---|---|
| SCALER-0675 Edison Plaza Wind Retrofit and Generator (HMGP DR-4337), Miami | Completed | DR-4337-0095-R | Closed | 2019-02-27 | high |
| SCALER-1086 Holtz Children's Hospital Wind Retrofit, county | Completed | DR-4337-0207-R | Closed | 2019-06-27 | high |
| SCALER-1370 North Bay Village Utility Undergrounding (HMGP DR-4337) | Completed | DR-4337-0279-R | Closed | 2019-08-19 | high |
| SCALER-0897 North Campus, Building 900 Hurricane Protection, county | Completed | DR-1609-0072-R | Closed | 2007-04-18 | high |
| SCALER-0472 Miami Fire Rescue Fire Station 6 Hardening | Funded | DR-4486-0075-R | Approved | 2022-08-11 | high |
| SCALER-0484 Miami Fire Rescue Fire Station 3 Hardening | Planned | FM-5426-0001 | Closed | 2023-06-20 | high |
| SCALER-0944 Structural and Roof Rehabilitation, Fire Rescue stations, county | Ongoing | DR-4486-0119-R | Approved | 2023-01-24 | high |
| SCALER-0936 MDFR Retrofit at Stations 14, 43, 50, county | Planned | DR-4734-0128 | Pending | 2025-08-15 | high |
| SCALER-0941 MDFR Retrofit at Stations 48 to 66, county | Planned | DR-4734-0155 | Pending | 2025-09-08 | high |
| SCALER-0943 Homeless Assistance Center South Hardening, county | Funded | DR-4794-0004 | Pending | 2025-12-11 | high |
| SCALER-1068 HMGP Naranja Library Wind retrofit, generator, flood protection, county | Planned | DR-4794-0008-R | Pending | 2025-12-12 | high |
| SCALER-1048 Jackson West Medical Center generator quick connect, county | Planned | DR-4806-0090 (also re-filed as DR-4828-0227, DR-4834-0235) | Closed / Pending | 2026-02-06 (earliest) | high |
| SCALER-0667 Wind Retrofit Project at RTC, Miami (Public Health Trust applicant) | Completed | DR-1539-0173-R | Closed | 2010-06-01 | medium |
| SCALER-0870 Miami Springs Wind Retrofit Project (county applicant) | Funded | DR-4486-0068-R | Approved | 2022-07-27 | medium |
| SCALER-1503 S-25A Coastal Structure Resiliency, SFWMD | Ongoing | DR-1345-0012-R | Closed | 2002-04-16 | medium; doubtful |

- **The S-25A pair should be checked by hand.** It meets the medium rule
  (costs within $536 and same agency). But a 2002 grant is an odd match for
  a project in a 2025 water district plan.
- **Most high matches are wind retrofits and hardening jobs** by the county,
  Jackson Health (Public Health Trust) or the City of Miami. Those are the
  projects that appear in both the county mitigation strategy and FEMA's
  grant list with the same cost.
- **This route will not date most of the SCALE-R database.** Most SCALE-R
  projects are capital improvement items, not FEMA grants.

Matches file: `data/processed/impact/hma_scaler_matches.csv`. It has every
candidate pair at any confidence, with the rule text, the jurisdiction fit,
the activity check and the FEMA submission date. `SCALE-R_Database.csv` was
not changed.

## 7. What this does not do

- **No model.**
- **No inflation adjustment.**
- **No flood insurance policy counts.** Without them, claims per insured
  home cannot be computed; `NfipPolicies` would give them.
- **No housing-weighted 2010 to 2020 split.**

Each would be a separate decision.
