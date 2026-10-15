# Investment × Vulnerability: Correlation Analysis

**Descriptive and correlational only.** Nothing in this analysis was fit,
tuned, or validated as a predictive model — no regression, no ML, no
train/test split. Every number below is a description of the data as it
exists, produced to support feature decisions, not to make them.

**Scope note, stated plainly so it isn't misread:** this is
**investment × vulnerability**, not investment × risk × vulnerability. No
FEMA NRI or other physical-risk layer is used anywhere in this document —
that was explicitly out of scope for this build, even though a tract-level
risk source (`../fema_miami_dade_dec_2025.csv`) exists one directory up and
was flagged as available in `project_data_profile.md`. Everything here
answers "how does investment relate to who lives somewhere and what they're
exposed to," not "how does investment relate to physical hazard."

Scripts (all reusable, re-run in order to reproduce every number and file in
`output/`):

| script | part | what it does |
|---|---|---|
| `scripts/vulnerability_loaders.py` | 1 | SVI / ACS-CRE / EJScreen / ADI loaders, built to `DATA_PROCESSING.md` recipes |
| `scripts/build_analysis_tables.py` | 1 | joins investment tables to indicators → `tract_analysis.csv`, `blockgroup_analysis.csv` |
| `scripts/analysis_variables.py` | — | shared variable lists / composition-measure builder used by Parts 2–5 |
| `scripts/part2_univariate.py` | 2 | univariate profile + sparsity baseline |
| `scripts/part3_correlation.py` | 3 | Pearson/Spearman matrices, VIF, overlap questions |
| `scripts/part4_investment_vs_indicators.py` | 4 | the core: volume and composition vs. vulnerability |
| `scripts/part5_diagnostics.py` | 5 | Pennsuco/flag robustness, Moran's I, zero/skew |

```
python scripts/build_analysis_tables.py
python scripts/part2_univariate.py
python scripts/part3_correlation.py
python scripts/part4_investment_vs_indicators.py
python scripts/part5_diagnostics.py
```

---

## Part 1 — Analysis tables

`tract_analysis.csv` — **698 rows** (`tract_investment.csv`'s 707, minus the 9
zero-population tracts per the decision already made — all 9 have every SVI
`EP_*` indicator at −999/missing and a 0/0 undefined denominator on all ten
ACS CRE tables, confirmed again on this join: 0 rows with all-SVI-missing or
all-CRE-missing survive). Joined to SVI `EP_*` (24 columns) and the ten ACS
CRE-component rates (10 columns, `+_num`/`_den` companions kept for audit).

`blockgroup_analysis.csv` — **1,843 rows**, none excluded (the exclusion
decision was tract-only). Joined to EJScreen (22 columns: 13 environmental +
7 socioeconomic + 2 health) and 13 ADI components.

**Build-time note on a real data gap, resolved mid-build:** `DATA_PROCESSING.md`
lists 13 ADI components including block-group B25014 (crowding, >1
occupant/room), but only 12 of the 13 tables had actually been downloaded to
`block-group-level/ADI Data/`. Flagged and resolved by downloading the missing
table (same 2024 ACS 5-Year vintage as its 12 siblings) before building — all
13 ADI components are present in `blockgroup_analysis.csv`.

**Build-time note on a documentation mismatch, reported not papered over:**
`DATA_PROCESSING.md` describes EJScreen as carrying "7 socioeconomic + 5
health indicators." The file's own column dictionary
(`EJScreen_2024_BG_Percentiles_Columns.xlsx`) confirms exactly 7 socioeconomic
indicators (`PEOPCOLORPCT, LOWINCPCT, UNEMPPCT, LINGISOPCT, LESSHSPCT,
UNDER5PCT, OVER64PCT`) but only **2** health-type indicators
(`DISABILITYPCT, LIFEEXPPCT`) actually exist as raw columns in this v2.3
extract. No search of the file turned up 3 more health columns under any
name. Used what's actually there (2, not 5) — see
`output/variable_dictionary.csv` for the full accounting.

**A second undefined-value case, handled the same way as the zero-population
per-capita problem in the prior build:** ADI's `income_disparity =
log(low-income HH / high-income HH)` is mathematically undefined (±∞) whenever
either count is exactly zero — and at block-group grain that's common, not
rare: **619 of 1,843 block groups** have zero households in the bottom income
bracket (log(0) = −∞), and **17** have zero households in the $50k+ brackets
(÷0 = +∞). Both are left as `NaN`, not computed as literal infinities that
would corrupt every downstream statistic, and not imputed. `income_disparity`
is therefore only defined for **1,207 of 1,843** block groups (65.5%) — this
is *why* it shows up as a >20%-missing variable in Part 2, and the missingness
is a property of the formula at this grain, not a data quality problem.

Reconciliation: both joins were checked for silent row loss — 0 tract rows
and 0 block-group rows lost coverage on all-indicator-missing grounds beyond
the deliberate 9-tract exclusion (asserted in the build script; it errors out
otherwise).

---

## Part 2 — Univariate description

Full tables: `output/part2_univariate/univariate_{tract,bg}_{vulnerability,outcomes}.csv`.

### Tract (698 rows, 34 vulnerability indicators: 24 SVI `EP_*` + 10 ACS CRE)

- **Missingness: none over 20%.** No SVI or CRE variable is missing in more
  than a handful of rows post-exclusion (a couple of ACS rates are undefined
  in 1 tract where a table's own denominator is 0 — e.g. `EP_NOVEH`/`no_vehicle`
  each miss 1, `EP_NOINT`/`no_broadband` each miss 1 — these are 0/0 cases in
  otherwise-populated tracts, reported not imputed).
- **No near-constant variables.**
- **No rate outside [0,1]** (SVI `EP_*` checked against its native 0–100 scale).
- **10 heavily skewed (|skew| > 2):** `EP_UNEMP, EP_SNGPNT, EP_MOBILE,
  EP_GROUPQ, EP_ASIAN, EP_AIAN, EP_NHPI, EP_TWOMORE, EP_OTHERRACE, no_vehicle`
  — mostly small-share race/ethnicity and rare-housing-type variables, as
  expected for county-wide rates concentrated in a few tracts.

### Block group (1,843 rows, 35 vulnerability indicators: 13 env + 7 socio + 2 health + 13 ADI)

- **3 variables exceed 20% missing:** `income_disparity` (34.5% missing, per
  the log-of-zero issue above), `median_gross_rent` (29.6%), `median_monthly_mortgage`
  (32.8%) — all three are block-group ACS medians, which the source
  documentation (`DATA_PROCESSING.md` §3) already warns are suppressed far
  more often than tract medians because of small block-group samples.
- **No near-constant variables.**
- **6 environmental indicators read as "outside [0,1]" by a literal 0–1
  check** — `PNPL, PRMP, PTSDF, UST, PWDIS, DWATER`. **This is not a bug**:
  these are EJScreen *proximity/count* scores in their native units (e.g.
  facility counts within distance bands), not rates, despite the flag logic
  applying a rate-style bound. Documented in
  `output/variable_dictionary.csv` as "raw exposure units."
- **9 heavily skewed:** `RSEI_AIR, PNPL, PWDIS, UNEMPPCT, no_diploma_under9yrs,
  median_home_value, pct_no_plumbing, pct_crowding_over100, pct_no_kitchen` —
  environmental proximity scores and several ADI rates, both expected to be
  right-skewed at fine geography.

### Outcome variables

`investment_any` (as built) has **exactly one distinct value (1) at both
grains** — zero variance, confirmed unusable, exactly as diagnosed before
this build. Its two replacements, `investment_any_excl_county` and
`investment_any_single_unit`, both show real variation (see Part 4).

Every dollar-valued outcome and every type/scale dollar column is heavily
right-skewed (|skew| 6–37 at tract; up to 37 at block group) — expected,
consistent with the post-filter project-level skew of 18.4 already reported
in the investment-table build.

### Project-type / scale-tag sparsity baseline (Part 4e input)

`output/part2_univariate/sparsity_baseline.csv`. Two counts matter here:
`n_receiving_units` (any allocation path, inflated by the county path which
reaches nearly every unit regardless of type) and
`n_receiving_units_single_unit_only` (a project *physically sited* there —
the number that actually reflects footprint, and the one used to flag
sparsity for Part 4):

| grain | dimension | category | n projects | single-unit-sited units | flagged sparse? |
|---|---|---|---|---|---|
| tract | type | **Blue** | 28 | **19** | **yes** |
| tract | type | Gray | 1,157 | 370 | no |
| tract | type | Green | 67 | 35 | no |
| tract | type | Hybrid | 153 | 90 | no |
| tract | scale | Parcel/Neighborhood/Corridor | 405/239/477 | 187/148/257 | no |
| bg | type | **Blue** | 28 | **19** | **yes** |
| bg | type | Gray/Green/Hybrid | — | 524/37/103 | no |

**Blue infrastructure is the one genuinely sparse composition category at
both grains** (19 single-unit-sited receiving units against 698 tracts / 1,843
block groups). Every Blue-share/Blue-any result in Part 4 carries
`flag_sparse=True` and is reported as a flag, not a finding, per the
constraint on sparse cells. Municipality and County are structurally always 0
on this metric (they *are* the distributed paths, not a footprint to compare)
— sparsity for those two is judged on project count instead (253 and 31
respectively — not sparse).

---

## Part 3 — Correlation among the indicators

Full matrices, heatmaps, and pair lists: `output/part3_correlation/`.
**Never correlated across grains**, as instructed.

### Tract (34 indicators)

**7 pairs exceed |Pearson r| > 0.8** — all SVI-vs-CRE construct pairs, i.e.
exactly the redundancy the prompt asked to quantify:

| SVI | CRE | Pearson r | Spearman ρ |
|---|---|---|---|
| `EP_NOVEH` | `no_vehicle` | 0.898 | 0.841 |
| `EP_NOHSDP` | `no_diploma_pop25` | 0.895 | 0.898 |
| `EP_AGE65` | `age65plus` | 0.888 | 0.877 |
| `EP_NOINT` | `no_broadband` | 0.854 | 0.862 |
| `EP_UNINSUR` | `uninsured` | 0.848 | 0.849 |
| `EP_LIMENG` | `limited_english_hh` | 0.840 | 0.821 |
| `EP_POV150` | `poverty_under125` | 0.832 | 0.825 |

**VIF: 7 variables > 10**, all race/ethnicity shares —
`EP_HISP` (152,742!), `EP_AFAM` (131,350), `EP_MINRTY` (58,857), `EP_ASIAN`
(1,411), `EP_TWOMORE` (1,320), `EP_OTHERRACE` (224), `EP_AIAN` (30). These
five-to-six race-share columns are near-perfectly collinear **in combination**
because they (plus the omitted white share) are compositional — they sum
close to 100% of the tract population, so any subset predicts the rest almost
exactly. No pairwise correlation flagged this (none of these appear in the
|r|>0.8 list above), which is exactly the "hides in combination" case VIF is
for. Every other variable (including all 7 SVI-CRE near-duplicates above) sits
at VIF 1.1–7.3 — elevated by the pairwise duplication but nowhere near the
race-share problem.

**The named SVI-vs-CRE overlap, all 9 pairs from the prompt's construct list**
(`output/part3_correlation/tract_svi_vs_cre_overlap.csv`):

| construct | SVI var | CRE var | n | Pearson r | Spearman ρ |
|---|---|---|---|---|---|
| poverty (150% vs 125% threshold) | `EP_POV150` | `poverty_under125` | 697 | 0.832 | 0.825 |
| uninsured | `EP_UNINSUR` | `uninsured` | 698 | 0.848 | 0.849 |
| disability | `EP_DISABL` | `disability` | 698 | 0.764 | 0.764 |
| no vehicle | `EP_NOVEH` | `no_vehicle` | 697 | 0.898 | 0.841 |
| age 65+ | `EP_AGE65` | `age65plus` | 698 | 0.888 | 0.877 |
| limited English HH | `EP_LIMENG` | `limited_english_hh` | 698 | 0.840 | 0.821 |
| no HS diploma | `EP_NOHSDP` | `no_diploma_pop25` | 698 | 0.895 | 0.898 |
| no internet/broadband | `EP_NOINT` | `no_broadband` | 697 | 0.854 | 0.862 |
| crowding | `EP_CROWD` | `crowding_over100` | 697 | 0.739 | 0.721 |

**All 9 are true near-duplicates** (r = 0.74–0.90) even though 5 of them use
different thresholds or slightly different denominators (150% vs 125%
poverty; different age/disability universes). The high-but-not-1.0 pattern is
exactly what "measuring the same thing with a different cutoff" should
produce — none of these looks like a coincidental correlation.

### Block group (35 indicators)

Only **2 pairs exceed |Pearson r| > 0.8**, both inside the EJScreen
environmental block: `PM25`–`OZONE` (r=0.900) and `PM25`–`DSLPM` (r=0.801) —
regional air-quality co-pollutants that move together for physical reasons,
not measurement duplication.

**VIF, all 35 variables: only `PM25` (32.1) and `OZONE` (24.4) exceed 10**,
computed on the 495 complete-case rows that survive listwise deletion across
all 35 columns (27% of the sample — most of that loss is the 3 high-missing
dollar variables). Re-run excluding those 3 (`income_disparity,
median_gross_rent, median_monthly_mortgage`) on **1,185 rows (64%)**: same
result — `PM25` (20.0) and `OZONE` (13.3) remain the only VIF>10 variables,
confirming the finding isn't an artifact of the smaller complete-case sample.
Nothing else in the ADI/EJScreen socioeconomic/health set shows combination
multicollinearity at this grain.

**EJScreen socioeconomic (7) vs ADI (13) — the 4 flagged TRUE-duplicate
candidates, checked individually:**

| candidate pair | result |
|---|---|
| no vehicle | **Cannot check** — EJScreen has no raw "no vehicle" column in this extract (there is no vehicle-access indicator at all, only `PTRAF` traffic-proximity, a hazard measure, not a household-access measure) |
| no internet | **Cannot check** — EJScreen has no raw "no household internet" column in this extract |
| unemployment | **Cannot check** — EJScreen's `UNEMPPCT` exists, but ADI dropped unemployment as a duplicate at the pull stage (never collected), so there is no ADI-side column to correlate against. The redundancy claim in `DATA_PROCESSING.md` §3 can't be numerically verified from what's on disk — it can be neither confirmed nor refuted here |
| less-than-HS vs <9-years education | **r = 0.679, ρ = 0.695 (n=1,833)** — high but well short of ~1.0. Expected: these use genuinely different thresholds (HS-diploma cut vs 8th-grade cut) by construction, so "related, not identical" is the correct read, not "duplicate" |

Three of the four "flagged as likely duplicates" pairs turn out to be
**un-verifiable from the data actually assembled**, not confirmed or refuted
— worth flagging to whoever compiled that duplicate list, since two of the
three gaps are EJScreen simply not carrying that indicator in this vintage.

**Full cross of all 7 socioeconomic × 13 ADI pairs (91 pairs,
`output/part3_correlation/bg_ejscreen_socio_vs_adi_full_cross.csv`)** — the
top pairs beyond the 4 flagged ones:

| EJScreen | ADI | n | Pearson r | Spearman ρ |
|---|---|---|---|---|
| `LOWINCPCT` | `poverty_under150` | 1,832 | 0.708 | 0.718 |
| `LOWINCPCT` | `median_family_income` | 1,496 | −0.649 | −0.710 |
| `LOWINCPCT` | `poverty_pct_families` | 1,827 | 0.523 | 0.524 |
| `PEOPCOLORPCT` | `median_family_income` | 1,496 | −0.510 | −0.515 |
| `LOWINCPCT` | `pct_owner_occupied` | 1,832 | −0.495 | −0.487 |

None of these exceed the 0.8 duplicate bar — `LOWINCPCT` and ADI's poverty/
income measures are correlated (as expected — both are income-based) but
constructed differently enough (percent-below-a-line vs. median dollars vs.
percent-below-a-different-line) that they aren't redundant in the way the SVI/CRE
tract pairs are.

**EJScreen environmental (13) × ADI (13) — the environmental-justice
co-location question, reported as a finding, not a redundancy screen**
(169 pairs, `output/part3_correlation/bg_environmental_vs_adi_ej_question.csv`):

| environmental | ADI deprivation | n | Pearson r | Spearman ρ |
|---|---|---|---|---|
| `UST` (underground storage tanks) | `pct_owner_occupied` | 1,832 | −0.423 | −0.432 |
| `PTSDF` (hazardous waste proximity) | `pct_owner_occupied` | 1,832 | −0.380 | −0.374 |
| `NO2` | `pct_owner_occupied` | 1,822 | −0.373 | −0.385 |
| `PRMP` (RMP facility proximity) | `no_diploma_under9yrs` | 1,833 | 0.313 | 0.340 |
| `PTRAF` (traffic proximity) | `pct_owner_occupied` | 1,832 | −0.303 | −0.317 |

**Median |r| across all 169 pairs is only 0.099**, and just 5 pairs exceed
|r|=0.3. **The co-location signal is real but modest, and it runs almost
entirely through one channel: renter-occupied housing.** `pct_owner_occupied`
(inverted: % renter-occupied) is the ADI variable that shows up repeatedly
against hazard-proximity measures (underground storage tanks, hazardous
waste, NO2, traffic) — renter-heavy block groups sit closer to these
exposures. Income and education measures show weaker, more scattered
relationships with the environmental block. This is a real but partial EJ
finding: tenure, not poverty or education, is the strongest deprivation
correlate of physical-hazard proximity in this county.

---

## Part 4 — Investment distribution vs. the indicators (the core)

Full test tables: `output/part4_investment_vs_indicators/`. Every continuous
pair reports **both Pearson and Spearman**; every binary-outcome comparison
reports **group means/medians and a Mann-Whitney U p-value**. All p-values
carry a **Benjamini-Hochberg FDR adjustment computed within each family**
(grouped by outcome for 4a/4d-volume, by group×measure for 4b/4c/4d-share) —
see the "many comparisons" note at the end of this Part.

### 4a — Tract volume

**Pearson is systematically weaker than Spearman here** — direct confirmation
that the skewed outcome (post-filter skew 18.4) is compressing linear
correlation. For `investment_per_capita`, the strongest relationship is
`EP_NOVEH` (no-vehicle rate): **Pearson r = 0.117, Spearman ρ = 0.333** — a
threefold difference in apparent strength depending only on which statistic
is used.

**Top relationships with `investment_per_capita`** (all Spearman, FDR-significant):

| variable | n | Spearman ρ |
|---|---|---|
| `EP_NOVEH` (no vehicle) | 697 | **0.333** |
| `EP_MUNIT` (multi-unit structures) | 697 | 0.279 |
| `no_vehicle` (ACS CRE) | 698 | 0.271 |
| `EP_MINRTY` (minority) | 698 | −0.256 |
| `no_broadband` (ACS CRE) | 698 | 0.227 |
| `EP_HISP` | 698 | −0.203 |
| `EP_NOINT`, `EP_TWOMORE` | 697/698 | 0.163 |

These are **weak-to-moderate at best** (ρ ≈ 0.25–0.33). The dominant
relationship is with housing-density/vehicle-access variables, not the
"classic" vulnerability axis (poverty, disability, age) — `EP_POV150` (ρ=0.026),
`poverty_under125` (ρ=0.021), `EP_AGE65` (ρ=−0.032) are all essentially flat.
Full LOESS scatterplots for the 8 strongest relationships:
`output/part4_investment_vs_indicators/4a_loess_*.png` — visually, the LOESS
curves for `EP_NOVEH`, `EP_MUNIT`, `no_vehicle` show a fairly monotone rise
with no sharp threshold; `EP_MINRTY` and `EP_HISP` decline gently.

**Outcome-variant sensitivity** (`output/part4_investment_vs_indicators/4a_outcome_definition_consistency.csv`):
one variable changes materially across `{per_capita, total, per_area}` — **not
a sign flip, a magnitude swing**: `EP_MUNIT` (multi-unit housing share) has
ρ=0.279 with per-capita, 0.212 with total, but **0.570 with per-area** — more
than double. Multi-unit-housing tracts are dense, so investment-per-land-area
correlates much more strongly with them than investment-per-person does; this
is a real, mechanically-expected difference between outcome definitions, not
noise. Nine other variables show trivial sign disagreement (all |ρ| < 0.15 on
whichever side is negative) — not worth reading as instability, just
noise-level near-zero correlations landing on either side of 0.

**Binary outcomes (Mann-Whitney, group means, `output/part4_investment_vs_indicators/4a_tract_volume_binary.csv`):**

`investment_any_excl_county` (n=539 receiving / 158 not): receiving tracts
have higher `EP_MUNIT` (35.6 vs 23.5), `EP_NOINT` (16.8 vs 9.6), `EP_NOVEH`
(10.8 vs 4.7) — consistent with the continuous result. `EP_MINRTY` shows
**no significant difference** (84.9 vs 88.9, FDR p=0.87) despite the
continuous per-capita relationship — the presence/absence question and the
"how much once you have any" question give different answers for this
variable specifically.

`investment_any_single_unit` (n=396/302 — a project physically sited there):
here `EP_HISP` (63.1 vs 75.6) and `EP_MINRTY` (83.6 vs 88.8) run in the
**opposite direction from the continuous per-capita result's sign for
EP_HISP/EP_MINRTY** — i.e. tracts with a physically-sited project skew
*less* Hispanic/minority than tracts without one, same direction as the
per-capita result, but `EP_AFAM` runs the other way (16.9 vs 10.0, *higher*
in receiving tracts) — race/ethnicity indicators do not move together here.

### 4b — Tract composition by project type

**This is the "what kind" finding a volume-only analysis misses.** Share
correlations by type (`output/part4_investment_vs_indicators/4b_tract_type_composition_continuous.csv`,
Spearman ρ):

| vulnerability variable | Blue share⚠ | Gray share | Green share | Hybrid share |
|---|---|---|---|---|
| `EP_NOVEH` | −0.315 | **+0.305** | −0.284 | −0.168 |
| `no_vehicle` | −0.267 | +0.254 | −0.239 | −0.133 |
| `EP_MUNIT` | −0.274 | +0.209 | −0.194 | −0.045 |
| `no_broadband` | −0.219 | +0.258 | −0.209 | −0.241 |
| `EP_NOINT` | −0.154 | +0.201 | −0.140 | −0.231 |
| `EP_MINRTY` | **+0.239** | −0.135 | +0.199 | −0.166 |
| `EP_HISP` | +0.187 | −0.140 | +0.155 | −0.078 |

⚠ = Blue is the **flagged-sparse** category (19 single-unit-sited tracts) —
reported for completeness but not to be read as a stable finding.

**A real, internally consistent pattern in the non-sparse categories: Gray
infrastructure's share of a tract's investment rises with vehicle-access and
connectivity deprivation, while Green and Hybrid shares fall with the same
variables.** This is the volume-vs-composition distinction working exactly
as the prompt anticipated: Part 4a showed only weak overall volume
relationships with these variables, but the *composition* of what a
vulnerable tract receives leans harder toward conventional gray
infrastructure and away from green/hybrid, even where total dollars aren't
very different. For the race/ethnicity axis the pattern is different again —
Blue and Green shares rise (not fall) with `EP_MINRTY`/`EP_HISP` while Gray
falls — the two vulnerability axes (access/connectivity vs. race/ethnicity)
pull composition in different directions, worth keeping distinct rather than
treating "vulnerability" as one dimension.

### 4c — Tract composition by allocation path

Share correlations by path (`output/part4_investment_vs_indicators/4c_tract_path_composition_continuous.csv`):

| vulnerability variable | single-unit share | municipality share | county share |
|---|---|---|---|
| `EP_NOVEH` | — | — | **−0.330** |
| `EP_MUNIT` | — | — | −0.277 |
| `no_vehicle` | — | — | −0.268 |
| `EP_MINRTY` | −0.178 | — | +0.259 |
| `no_broadband` | — | +0.255 | −0.227 |
| `EP_HISP` | — | — | +0.208 |
| `EP_NOINT` | — | +0.190 | −0.162 |

**The "was this tract targeted or just automatically covered" question has a
real answer, and it's reassuring on one axis and not on another.** County
share — the untargeted, population-weighted automatic distribution — is
**lower** in tracts with more vehicle/broadband/housing-density deprivation
(`EP_NOVEH` ρ=−0.330, `EP_MUNIT` ρ=−0.277, `no_broadband` ρ=−0.227): these
tracts get *more* of their money from the targeted single-unit/municipality
paths, not just the automatic county spread. But county share is **higher**
in tracts with more `EP_MINRTY` (ρ=+0.259) and `EP_HISP` (ρ=+0.208) — the
opposite direction: more-minority tracts get *more* of their investment from
the passive, untargeted mechanism, not less. Same split as Part 4b: the
access/connectivity axis looks targeted, the race/ethnicity axis looks more
passively covered.

### 4d — Block group, composition only

**Restricted scope, stated up front:** no `{type}_per_capita` or
`{path}_per_capita` was computed at block group (per-capita instability there
— max $1.7M/person, a 6-resident block group holding $6.6M — was diagnosed in
`zero_population_investigation.md` and no population floor fixes it, so it
isn't a sound basis for a correlation here). `investment_total` and
`investment_per_area` were not used as block-group correlation targets
either (not requested for the composition question). `investment_per_capita`
is reported **descriptively only**: n=1,833, min=$565.50 (the county-floor
value), median=$729, p95=$9,352, p99=$56,922, **max=$1,702,228** — no
correlation was built on it, only these figures.

**Volume proxies** (`investment_any_excl_county`, `investment_any_single_unit`)
against EJScreen/ADI, Mann-Whitney (`output/part4_investment_vs_indicators/4d_bg_volume_proxy_binary.csv`):
receiving-any-non-county-dollar block groups have **higher** hazard-proximity
means than non-receiving ones — `RSEI_AIR` (3,307 vs 2,833), `UST` (16.7 vs
7.3), `PWDIS` (3.32 vs 0.67), `PTSDF` (2.88 vs 1.18), `NO2` (10.2 vs 9.0), all
FDR-significant. **Investment (beyond the automatic county share) tends to
land in more environmentally exposed block groups**, not less — plausibly
because gray/drainage infrastructure projects concentrate in industrial and
high-traffic corridors, which are also where these exposure measures are
highest; this dataset can't distinguish "targeted because exposed" from "both
driven by industrial land use," only that they co-occur.

For `investment_any_single_unit` specifically, the **income-side variables
run the other way**: receiving block groups have *higher* mean
`median_home_value` ($575,040 vs $494,653) and `median_family_income`
($101,517 vs $89,486), both FDR-significant. **Physically-sited (targeted)
single-unit projects skew toward higher-value block groups, not toward the
most economically deprived ones** — worth flagging plainly since it cuts
against a simple "investment reaches the neediest" reading.

**Type/path share** (`output/part4_investment_vs_indicators/4d_bg_type_composition_continuous.csv`,
`4d_bg_path_composition_continuous.csv`): the strongest share relationships
are almost entirely environmental — `municipality`-path share rises with
`PTSDF` (ρ=0.349) and `UST` (ρ=0.298); `county`-path share rises with `PM25`
(ρ=0.263) and `PEOPCOLORPCT` (ρ=0.262) but *falls* with `UST` (ρ=−0.262) and
`PTSDF` (ρ=−0.247) — the same "environmental exposure and race/ethnicity pull
in different directions from the vehicle/plumbing/tenure axis" pattern seen
at tract grain, now showing up in the allocation-path composition too.

### 4e — Sparsity and multiple comparisons

**Sparsity:** only **Blue** infrastructure (type dimension, both grains, 19
single-unit-sited receiving units) falls under the 20-unit floor. Every Blue
row across 4b/4c/4d carries `flag_sparse=True` in its CSV and is called out
above as flagged, not treated as a finding, even where its correlation looks
large (e.g. Blue share vs `EP_NOVEH`, ρ=−0.315 — larger in magnitude than
several non-sparse results, but resting on only 19 tracts/block groups).

**Multiple comparisons:** Part 4 runs on the order of **1,000+ individual
tests** across 4a–4d (5 outcomes × 34 vars at tract alone is 170; composition
adds several hundred more per grain). BH-FDR correction was applied within
each family (grouped by outcome, or by group×measure for composition) rather
than globally, because pooling wildly different sample sizes and effect-size
distributions into one correction would over- or under-penalize different
families. **With this many pairs, some reach nominal significance by chance
even after FDR correction within a family** — every number reported above as
a "top relationship" is the *strongest available* result in its family, not
independently pre-registered, so read magnitudes and consistency-across-related-variables
(e.g. the whole vehicle/broadband/housing-density cluster moving together)
as the trustworthy signal, not any single p-value in isolation.

---

## Part 5 — Diagnostics that decide the modeling approach

Full tables: `output/part5_diagnostics/`.

### 5a — Pennsuco (12086981100) influence

Pennsuco holds the tract-level per-capita maximum (pop=28, $24.2M,
$862,995/person). Re-running the 10 headline tract pairs with and without it
(`output/part5_diagnostics/5a_pennsuco_influence.csv`): **only 2 of 10 pairs
move Spearman ρ by more than 10%**, and both are pairs whose correlation is
already essentially zero (`investment_per_capita` vs `EP_POV150`: 0.026→0.030,
a 17% *relative* move on a near-null result; vs `poverty_under125`:
0.021→0.025, 20% relative). **None of the substantive relationships
(`EP_NOVEH`, `EP_MUNIT`, `EP_MINRTY`, the SVI-CRE overlap pairs) move by more
than 2%.** Pennsuco is not driving any headline result — its extreme
per-capita value is a curiosity, not an influential point for these
correlations.

### 5b — `flag_large_project` split (3 tracts, 2 surviving SMART corridors)

Same check, dropping the 3 flagged tracts (`12086001205, 12086005705,
12086010400`) instead: **again only 2 of 10 pairs move >10%, both the same
near-null poverty pairs** (0.026→0.029, 10.1%; 0.021→0.023, 12.5%). The
flagged units — despite carrying $927M and $368M single transit corridors —
**do not measurably distort any of the headline vulnerability correlations**.
This is a useful robustness result: whatever decision gets made about
excluding or reweighting the SMART-corridor tracts for modeling, it will not
change the correlational picture in this report.

### 5c — Moran's I (k=6 nearest-neighbor weights)

**k chosen as 6**: a standard default in spatial-econometrics practice
(matches the typical number of contiguous neighbors for an urban tract/
block-group grid) and, being distance-based rather than contiguity-based,
avoids the "island" problem a fixed-distance band would create given the
size-heterogeneous mix of dense urban tracts and large southern/rural
parcels in this county. *(Build note: constructing the k-NN graph reported
"2 disconnected components" for both grains — expected for a geography with an
isolated peninsula/barrier-island cluster whose 6 nearest neighbors by
centroid distance don't reciprocate into the mainland's graph; this affects
only the network's connectivity structure, not the permutation-based
significance test used here.)*

**The central finding: the dollar outcome and the vulnerability indicators
have very different spatial structure.**

| variable | grain | Moran's I | p (999 perms) |
|---|---|---|---|
| `investment_per_capita` | tract | **0.006** | 0.070 (not significant) |
| `investment_any_excl_county` | tract | 0.465 | <0.001 |
| `investment_any_single_unit` | tract | 0.194 | <0.001 |
| `type_gray_share` | tract | 0.338 | <0.001 |
| `type_blue_share`⚠ | tract | 0.454 | <0.001 |
| `EP_NOVEH` | tract | 0.485 | <0.001 |
| `EP_MUNIT` | tract | 0.580 | <0.001 |
| `EP_MINRTY` | tract | 0.669 | <0.001 |
| `EP_NOHSDP` | tract | 0.574 | <0.001 |
| `investment_any_excl_county` | bg | 0.604 | <0.001 |
| `PM25` | bg | 0.970 | <0.001 |
| `OZONE` | bg | 0.986 | <0.001 |
| `UST` | bg | 0.709 | <0.001 |
| `LOWINCPCT` | bg | 0.422 | <0.001 |

**`investment_per_capita` shows essentially zero spatial autocorrelation**
(I=0.006, not significant) even though **every vulnerability variable tested
is strongly and significantly spatially clustered** (I=0.31–0.67 at tract,
0.33–0.99 at block group — air-quality variables are the most extreme, as
physically expected for pollutants that diffuse regionally). The **binary
outcomes and type/path shares sit in between** — moderately-to-strongly
clustered (I=0.14–0.60), much closer to the vulnerability indicators' spatial
structure than to the near-zero per-capita result.

**This is a genuine modeling-relevant finding, not a nuisance result: a
plain OLS on `investment_per_capita` may not need a spatial specification (no
detectable clustering to leave unmodeled in the residuals), but any
model on the binary outcomes or the type/path composition shares almost
certainly will** — their outcome variable is already spatially clustered
before any covariate is added, exactly the condition the spatial diagnostic
gate in `DATA_PROCESSING.md` §5 says should trigger escalation to a spatial
model. Full tables (16 tract variables, 14 block-group variables):
`output/part5_diagnostics/5c_moran_{tract,bg}.csv`.

### 5d — Zero/skew profile per outcome, including per type

`output/part5_diagnostics/5d_zero_skew_{tract,bg}.csv`. No dollar-total or
type-share variable has more than a handful of exact zeros at tract grain
(all type shares and type totals: 0% zero, since every tract received
*something*). The allocation-path amounts are different:
`path_single_unit_amt` is **43.3% zero at tract, 68.5% zero at block
group** — and at block group, this is the **only variable in the whole
profile exceeding the 50%-zero hurdle-model threshold**. `path_municipality_amt`
is close behind (43.8% tract, 43.0% bg) without crossing it.

**This directly supports treating the allocation-path breakdown, if it enters
any downstream model, as a hurdle/two-part specification at block-group
grain** (a large mass of true zeros for "did a project get physically sited
here" plus a heavily-skewed positive part) — while the aggregate
`investment_total`/type-share outcomes do **not** show the same zero-mass
problem and can likely be modeled as a continuous (skewed) outcome without a
hurdle component, consistent with the low zero-investment shares already
established in the investment-table build (`INVESTMENT_TABLES.md`).

---

## What the investment distribution looks like

**Volume: weak relationships with vulnerability, essentially flat with the
"classic" vulnerability axis.** At tract grain, the strongest volume
relationship with `investment_per_capita` — vehicle-access/housing-density
deprivation (`EP_NOVEH`, `EP_MUNIT`, `no_vehicle`) — is only weak-to-moderate
(Spearman ρ ≈ 0.27–0.33) and would be read as much weaker still on Pearson
(r ≈ 0.04–0.12), because the outcome is heavily skewed. Poverty, disability,
and age — the variables most people mean by "vulnerability" — show **no
meaningful relationship with investment volume at all** (ρ ≈ 0.02–0.08 in
either direction). At block group, the binary volume proxies show investment
(beyond the automatic county share) landing in *more* environmentally exposed
places, and single-unit-sited investment skewing toward *higher*-income block
groups — neither supports a simple "more vulnerable → more investment"
story, and if anything the income-side result points mildly the other way for
targeted projects specifically.

**Composition: a real, coherent pattern that the volume numbers completely
hide.** Gray infrastructure's *share* of a tract's investment rises
consistently with vehicle-access, connectivity, and housing-density
deprivation, while Green and Hybrid shares fall with the same variables —
several independent measures (type share, allocation-path share, the tract
and block-group binary comparisons) all point the same direction. Separately,
and pulling the *opposite* way, the race/ethnicity axis (`EP_MINRTY`,
`EP_HISP`) associates with *more* Blue/Green share and *more* passive
county-only allocation, not more Gray or more targeted single-unit
investment — meaning "vulnerability" is not one axis here; the
access/connectivity cluster and the race/ethnicity cluster pull composition
in different directions, and collapsing them into a single vulnerability
score for modeling would erase a real distinction visible in this data. The
one composition category that looked most dramatic — Blue infrastructure — is
also the one resting on only 19 receiving units and should not be treated as
settled.

**Spatially**, the vulnerability indicators are clustered everywhere
(Moran's I 0.3–0.99), but the primary dollar outcome (`investment_per_capita`)
is not (I≈0.006, not significant) — investment dollars-per-person don't
cluster geographically the way need does, while *whether* a tract got
anything at all, and *what kind* it got, both do cluster. That's a genuine
disconnect between the volume and composition/presence pictures, on top of
being disconnected from vulnerability itself.

---

## Feature decisions this evidence supports

**No variable was dropped anywhere in this analysis — everything below is
evidence for a decision you and your professor will make, not a decision
already made.**

**Redundant (r > 0.8), one candidate for dropping at modeling stage:**
- All 7 tract SVI↔CRE construct pairs (`EP_NOVEH`/`no_vehicle`,
  `EP_NOHSDP`/`no_diploma_pop25`, `EP_AGE65`/`age65plus`,
  `EP_NOINT`/`no_broadband`, `EP_UNINSUR`/`uninsured`,
  `EP_LIMENG`/`limited_english_hh`, `EP_POV150`/`poverty_under125`) — r =
  0.83–0.90. These are the cleanest true-duplicate case in the whole
  analysis.
- Block-group `PM25`↔`OZONE` (r=0.900) and `PM25`↔`DSLPM` (r=0.801) —
  regional air-quality co-pollutants.

**Multicollinear in combination even without a high pairwise r (VIF):**
- Tract: the 5–6 SVI race/ethnicity share columns (`EP_HISP, EP_AFAM,
  EP_MINRTY, EP_ASIAN, EP_TWOMORE, EP_OTHERRACE`, VIF 224–152,742) — a
  compositional-data problem (they sum close to 100%), not a data error.
- Block group: `PM25` and `OZONE` again (VIF 20–32), consistent with the
  pairwise finding.

**Degraded / usability caveats (not redundancy, but affects what a model can
lean on):**
- Block-group `income_disparity` is undefined (not merely missing) for
  34.5% of block groups by construction of the log-ratio formula at fine
  geography — usable, but with a documented, formula-driven missingness
  pattern rather than a random one.
- `median_gross_rent` (29.6% missing) and `median_monthly_mortgage` (32.8%
  missing) at block group — small-sample ACS median suppression, as
  `DATA_PROCESSING.md` already anticipated.
- Blue-infrastructure composition measures (type share/any) rest on only 19
  receiving units at either grain — any relationship involving Blue share
  should be treated as suggestive at best, not as a stable estimate.

**Relate most strongly to investment (numbers attached, weak-to-moderate at
best for volume, stronger and more coherent for composition):**
- Volume (tract, `investment_per_capita`): `EP_NOVEH` ρ=0.333, `EP_MUNIT`
  ρ=0.279, `no_vehicle` ρ=0.271, `EP_MINRTY` ρ=−0.256 — the ceiling of what
  volume alone shows.
- Composition (tract, type share): the Gray-up/Green-and-Hybrid-down pattern
  against the same vehicle/connectivity/density cluster, ρ up to ±0.32
  (non-sparse categories only).
- Composition (tract, path share): county-only share down with
  vehicle/connectivity deprivation (ρ down to −0.33) but up with
  race/ethnicity share (ρ up to +0.26) — the clearest single piece of
  evidence that "vulnerability" splits into (at least) two axes here.
- Environmental co-location (block group): renter-occupancy (`pct_owner_occupied`,
  inverted) is the ADI variable most associated with hazard-proximity
  exposure (r up to −0.42 with underground storage tanks) — a modest but
  real EJ signal running through tenure specifically, not through income or
  education.

**Structural / modeling-approach evidence (Part 5), each independently
supported:**
- `investment_per_capita` is robust to both the Pennsuco outlier and the
  3 flagged SMART-corridor tracts (all headline correlations move <2%
  under either exclusion) and shows no significant spatial autocorrelation
  (Moran's I ≈ 0.006) — the least structurally complicated of the outcome
  variants.
- The binary presence outcomes and the type/path composition shares are all
  significantly spatially clustered (Moran's I 0.14–0.60) — any model on
  these should expect to need a spatial specification, per the diagnostic
  gate already set out in `DATA_PROCESSING.md` §5.
- `path_single_unit_amt` crosses the 50%-zero threshold at block group
  (68.5% zero) — the one outcome variant in this whole profile that looks
  like a genuine hurdle/two-part candidate; the aggregate dollar and
  type-share outcomes do not.
