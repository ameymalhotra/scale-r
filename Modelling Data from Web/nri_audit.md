# FEMA National Risk Index extract: audit

**Audit only.** The file was read, counted and described. It was not joined to
anything, no variables were built from it, nothing was correlated or modelled,
and the file itself was not modified. Script: `scripts/audit_nri.py`, raw
output in `output/nri_audit_raw.txt`.

File audited: `../fema_miami_dade_dec_2025.csv`

---

## The exclusion to carry forward

**Do not use NRI's composite risk columns as the risk variable.** The
composite risk score is expected annual loss multiplied by a social
vulnerability factor and divided by a community resilience factor. Those two
factors derive from the CDC Social Vulnerability Index and the Census
Community Resilience Estimates, which are already our independent variables.
Using the composite would put our predictors on both sides of the model.

**We use expected annual loss columns only.** The full exclusion list is in
Task 3, and every excluded column is present in this file, so the mistake is
available to make.

---

## Task 1. File inventory

| | |
|---|---|
| Rows | **706** data rows, one per tract |
| Columns | **467** |
| Identifier column | **`TRACTFIPS`**, an 11-digit string, no duplicates |
| Example value | `12086000107` |
| Rows beginning 12086 | **706 of 706** |
| State / county fields | State FIPS `12`, county FIPS `86`, county name Miami-Dade, single value each |
| Grain | **Census tract.** All identifiers are 11 digits, which is the tract length. Not block group (12) and not county (5) |

Three other identifier-like columns exist and should not be mistaken for the
join key: `NRI_ID` (12 characters, the tract code prefixed with `T`),
`STCOFIPS` (5 digits, county only, one distinct value), and `TRACT` (3 to 6
characters, the tract suffix without the state and county prefix).

**Row count against our own frame.** This file has 706 tracts. Our tract
analysis frame has 707 before exclusions, from the 2024 TIGER boundary file
and the 2024 five-year survey. That is a one-tract difference. I have not
determined which tract differs, because that requires matching the two files
and this is an audit. It needs reconciling whenever a join is actually built.

**Data dictionary: none.** There is no NRI data dictionary, codebook or
metadata file in this directory or the repo root. The only other NRI-named
file is `NRI_Table_CensusTracts.csv`, which is the national data table, not
documentation. Every column meaning in this audit is read from the NRI naming
convention rather than from a dictionary shipped with the data. Where a name
does not settle the meaning, I have said so rather than guessed.

---

## Task 2. Hazards present

**All 18 NRI hazards are present.** Nine of the ten prefixes on the list
appear. The tenth, `RFLD`, is absent, and its absence is informative rather
than a gap: see Task 6.

| Prefix | Hazard | Present | Columns |
|---|---|---|---|
| HWAV | heat wave | yes | 26 |
| CFLD | coastal flooding | yes | 22 |
| **RFLD** | **riverine flooding** | **no** | **0, superseded by IFLD** |
| HRCN | hurricane | yes | 26 |
| SWND | strong wind | yes | 26 |
| TRND | tornado | yes | 26 |
| WFIR | wildfire | yes | 26 |
| LTNG | lightning | yes | 22 |
| DRGT | drought | yes | 16 |
| HAIL | hail | yes | 26 |

Also present, not on the list: `IFLD` inland flooding (26), `CWAV` cold wave
(26), `WNTW` winter weather (26), `AVLN` avalanche (22), `ERQK` earthquake
(22), `ISTM` ice storm (22), `LNDS` landslide (22), `TSUN` tsunami (22),
`VLCN` volcanic activity (22).

### Component types by hazard

A dash means NRI does not publish that component for that hazard.

| Hazard | EALT | EALB | EALP | EALPE | EALA | AFREQ | EXPB | EXPP | EXPA | RISKS | RISKR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HWAV | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| CFLD | yes | yes | yes | yes | **-** | yes | yes | yes | **-** | yes | yes |
| HRCN | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| IFLD | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| SWND | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| TRND | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| WFIR | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| HAIL | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| LTNG | yes | yes | yes | yes | **-** | yes | yes | yes | **-** | yes | yes |
| DRGT | yes | **-** | **-** | **-** | yes | yes | **-** | **-** | yes | yes | yes |
| CWAV, WNTW | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| AVLN, ERQK, ISTM, LNDS, TSUN, VLCN | yes | yes | yes | yes | **-** | yes | yes | yes | **-** | yes | yes |

Component key: `_EALT` total expected annual loss, `_EALB` building loss (the
property damage measure), `_EALP` population loss, `_EALPE` population
equivalence, `_EALA` agriculture loss, `_AFREQ` annualized frequency, `_EXPB`
/ `_EXPP` / `_EXPA` exposure values, `_RISKS` and `_RISKR` hazard-specific
risk score and rating.

**Two component notes.** Coastal flooding has no agriculture component, so
`CFLD_EALA` does not exist. Drought is loss-to-agriculture only: it has no
building, population or population-equivalence loss column at all. Of the 18
hazards, 17 carry a building-loss column; drought is the one that does not.

Four further suffixes appear on most hazards and are not on the list above:
`_EVNTS` event count, `_EXP_AREA` exposed area, `_HLRB` / `_HLRP` / `_HLRR`
historic loss ratios, `_EALS` and `_EALR` loss score and rating, `_ALRB` /
`_ALRP` / `_ALR_NPCTL` annualized loss ratios, and `_RISKV` risk value. The
`_HLRR` suffix in particular is not self-explanatory from its name and I have
not guessed at it.

---

## Task 3. Composite columns, excluded

Every one of these is present in the file. All are excluded, for the reason
stated at the top of this document.

| Column | In file | Status |
|---|---|---|
| `RISK_SCORE` | yes | **EXCLUDED** |
| `RISK_RATNG` | yes | **EXCLUDED** |
| `RISK_SPCTL` | yes | **EXCLUDED** |
| `RISK_VALUE` | yes | **EXCLUDED** |
| `SOVI_SCORE` | yes | **EXCLUDED**, this is CDC social vulnerability, already a predictor |
| `SOVI_RATNG` | yes | **EXCLUDED** |
| `SOVI_SPCTL` | yes | **EXCLUDED** |
| `RESL_SCORE` | yes | **EXCLUDED**, this is community resilience, already a predictor |
| `RESL_RATNG` | yes | **EXCLUDED** |
| `RESL_SPCTL` | yes | **EXCLUDED** |
| `RESL_VALUE` | yes | **EXCLUDED** |
| `CRF_VALUE` | yes | **EXCLUDED**, the community resilience factor itself |

The per-hazard `_RISKS` and `_RISKR` columns carry the same problem, since
each hazard's risk score is built the same way from that hazard's loss and the
same two factors. They are listed in Task 2 for completeness but should be
treated as excluded on the same grounds.

---

## Task 4. The five requests against this file

| Request | In this file | Columns that cover it | If not present, what would be needed |
|---|---|---|---|
| **Extreme heat exposure** | **Yes** | `HWAV_EALT`, `HWAV_EALB`, `HWAV_EALP`, `HWAV_EALPE`, `HWAV_EALA`, plus frequency and exposure columns | n/a, but see the caveat below |
| **Property damage costs** | **Yes** | `_EALB` for each of 17 hazards, plus the all-hazard total `EAL_VALB` | n/a |
| **Flood hazard zones** | **Partly** | Flood *loss* is here: coastal `CFLD_*` and inland `IFLD_*`. Flood *zone* designations are not | Zone designations (AE, VE, X) come from the National Flood Hazard Layer, a separate FEMA product. A search for zone-like column names returned nothing |
| **Sea level rise exposure** | **No, not separable** | None | NRI folds four subtypes into one coastal flooding number and publishes only the combined total. A search for sea level rise and tide terms returned no columns. Separating it would need a dedicated inundation surface, for example a NOAA sea level rise layer |
| **Storm surge inundation** | **No, not separable** | None | Same structure: surge is one of the four subtypes inside coastal flooding. A search for surge terms returned no columns. Separating it would need a surge product such as SLOSH |

**Caveat on heat and property damage, which interact.** Both requests are
nominally satisfied, but they do not combine. Heat wave building loss is
effectively zero across this county: `HWAV_EALB` has a mean of $0.58 and a
maximum of $9.96 per tract, against a hurricane building-loss mean of
$410,027. Heat wave total loss is almost entirely population equivalence:
`HWAV_EALT` averages $44,105 and `HWAV_EALPE` averages $44,102 of it. So if
the analysis uses building loss as the property damage measure, heat will
contribute essentially nothing to it. Heat has to be carried by its
population or total loss columns instead.

---

## Task 5. Data quality on the loss columns we would use

All figures below are expected annual loss in dollars, except `_EALP` which is
a fractional population measure. Coverage is complete: **no missing values, no
unparseable values, and no sentinel codes** in any of these columns. NRI marks
a hazard that does not apply to a tract with a genuine zero here rather than a
missing code, which matters for interpretation: a zero is a real estimate, not
an absence.

| Column | n | Missing | Zeros | Min | Median | Mean | Max | Skew |
|---|---|---|---|---|---|---|---|---|
| `HWAV_EALT` | 706 | 0 | 3 (0.4%) | 0.00 | 43,525.58 | 44,104.98 | 122,357.85 | **0.29** |
| `HWAV_EALB` | 706 | 0 | 3 (0.4%) | 0.00 | 0.46 | 0.58 | 9.96 | 8.15 |
| `HWAV_EALP` | 706 | 0 | 8 (1.1%) | 0.00 | 0.00 | 0.00 | 0.01 | 0.29 |
| `HWAV_EALPE` | 706 | 0 | 8 (1.1%) | 0.00 | 43,525.23 | 44,101.81 | 122,354.85 | 0.29 |
| `HWAV_EALA` | 706 | 0 | 520 (73.7%) | 0.00 | 0.00 | 2.58 | 777.30 | 22.63 |
| `CFLD_EALT` | 706 | 0 | 130 (18.4%) | 0.00 | 5,923.80 | 32,274.33 | 1,847,207.63 | 8.97 |
| `CFLD_EALB` | 706 | 0 | 130 (18.4%) | 0.00 | 4,433.55 | 25,836.83 | 1,492,685.08 | 9.15 |
| `CFLD_EALP` | 706 | 0 | 141 (20.0%) | 0.00 | 0.00 | 0.00 | 0.03 | 8.60 |
| `CFLD_EALPE` | 706 | 0 | 141 (20.0%) | 0.00 | 1,334.99 | 6,437.50 | 354,523.61 | 8.60 |
| `IFLD_EALT` | 706 | 0 | **0** | 3,062.66 | 336,701.50 | 503,953.72 | 33,070,554.32 | 21.23 |
| `IFLD_EALB` | 706 | 0 | **0** | 79.28 | 299,074.98 | 380,620.14 | 2,818,697.61 | **2.33** |
| `IFLD_EALP` | 706 | 0 | 59 (8.4%) | 0.00 | 0.00 | 0.00 | 0.02 | 0.97 |
| `IFLD_EALPE` | 706 | 0 | 59 (8.4%) | 0.00 | 32,519.79 | 38,530.89 | 220,747.41 | 0.97 |
| `IFLD_EALA` | 706 | 0 | 563 (79.7%) | 0.00 | 0.00 | 84,802.69 | 30,787,441.71 | 23.64 |
| `HRCN_EALT` | 706 | 0 | **0** | 709.00 | 358,459.99 | 468,269.98 | 8,540,018.19 | 9.22 |
| `HRCN_EALB` | 706 | 0 | **0** | 204.97 | 318,370.76 | 410,027.23 | 6,640,514.93 | 7.77 |
| `HRCN_EALP` | 706 | 0 | 6 (0.8%) | 0.00 | 0.00 | 0.00 | 0.01 | 0.39 |
| `HRCN_EALPE` | 706 | 0 | 6 (0.8%) | 0.00 | 37,019.52 | 37,416.83 | 106,960.72 | 0.39 |
| `HRCN_EALA` | 706 | 0 | 520 (73.7%) | 0.00 | 0.00 | 20,825.92 | 6,661,757.49 | 23.28 |

`RFLD` columns do not exist, so there is nothing to report for them.

**Skew, which was the reason for asking.** The expectation was right for most
of these, and a transformation will be needed. Twelve of the nineteen columns
have skew above 2, and the dollar columns that matter most sit between 7.8 and
21.2: coastal building loss at 9.15, hurricane building loss at 7.77, inland
total loss at 21.23. This is the same shape as the investment outcome, which
needed a rank or log transform before its spatial statistic behaved, so plan
on the same here.

**Three exceptions worth knowing.** Heat wave loss is close to symmetric
(skew 0.29), so it will not need the same treatment as the flood and hurricane
columns. Inland building loss is only moderately skewed at 2.33, much less
than its own total at 21.23. And the agriculture columns are the most skewed
of all, between 22.6 and 23.6, because roughly three quarters of tracts in an
urban county have zero agricultural loss.

**Zero structure differs by hazard, and it is substantive.** Inland flooding
and hurricane have no zero tracts at all: every tract in the county carries
some modelled loss. Coastal flooding is zero in 130 tracts, about 18 percent,
which is the inland part of the county. Agriculture is zero in about three
quarters. If any of these enter a model, the coastal and agriculture columns
have a zero mass that a plain log transform cannot handle.

---

## Task 6. Version

**No explicit version field exists in the file.** There is no column carrying
a version, release, vintage or update value. The version has to be inferred
from the column set.

**The inference is clear: this file postdates the inland flooding rebuild.**
It carries `IFLD` columns and no `RFLD` columns. NRI renamed that hazard from
Riverine Flooding to Inland Flooding when it rebuilt the hazard to include
pluvial flooding alongside fluvial, which is precisely the change flagged as
the version concern. A file using the new name carries the new method.

Two qualifications on that inference. First, it is an inference from a naming
convention, not a version stamp, and I could not confirm it against a data
dictionary because none is present. Second, the file name says December 2025,
which is consistent with a recent release, but a file name is not evidence of
what is inside it. If the exact version number matters for the methods
write-up, it should be confirmed against the NRI release notes for the
download date rather than taken from this audit.

---

## What we have and what we still need

**Satisfied by this file, no download needed:**

1. **Extreme heat exposure.** Present as heat wave columns, complete, no
   missing values. Use the total or population loss columns, not building
   loss, for the reason in Task 4.
2. **Property damage costs.** Present as building expected annual loss for 17
   of the 18 hazards, plus an all-hazard total. Complete, no missing values.
3. **Flood hazard, as loss.** Present for both coastal and inland flooding,
   complete, with the zero structure noted in Task 5.

**Not satisfied, and what each would need:**

4. **Flood hazard zones.** This file has flood loss, not zone designations.
   The AE, VE and X zones come from the National Flood Hazard Layer, a
   separate FEMA product that would have to be downloaded and spatially joined
   to tracts. Worth deciding whether loss or zone is what the question
   actually needs, since they answer different things: loss is a modelled
   dollar expectation, zone is a regulatory designation.
5. **Sea level rise exposure.** Not separable from this file, confirmed by
   column search. NRI publishes only the combined coastal flooding total,
   which folds sea level rise and high tide flooding together with the
   100-year and 500-year flood areas and hurricane surge. A separate
   inundation product, such as the NOAA sea level rise layer, would be needed.
6. **Storm surge inundation.** Not separable, same structure and same
   confirmation. A dedicated surge product such as SLOSH would be needed.

So three of the five requests are met here, and the two coastal ones are not,
because FEMA does not publish them separately at this grain. If sea level rise
and surge need to be distinct variables rather than folded into one coastal
flooding measure, that requires new data, not a different column from this
file.

**Is a re-download warranted on version grounds? No.** The file already
carries the rebuilt inland flooding hazard, which was the specific concern. A
re-download would not change the inland flooding method. The one open item is
confirming the exact version number against the release notes, which is a
documentation step for the methods section rather than a reason to pull the
data again.

**One item to settle before any join, not resolved here.** This file has 706
tracts and our analysis frame has 707. That difference needs reconciling when
a join is built. I did not investigate which tract differs, because
identifying it means matching the two files, and this was an audit.
