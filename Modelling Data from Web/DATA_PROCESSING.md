# Data Processing Notes — SCALE-R investment / risk / vulnerability modeling

Running record of every cleaning and transformation step the downloaded data
needs before modeling. Built to hand to Claude Code in the data directory.
Goal: pull the CRE-component and SVI variables as tract-level marginals and
test them against project risk and investment. This does NOT reconstruct any
published index.

Study area: Miami-Dade County, FL. State FIPS 12, county FIPS 086.
Sizes, confirmed against TIGER 2024 and the 2024 five-year ACS: 707 census
tracts and 1,843 block groups. The analysis frame is 698 tracts, after
excluding nine with zero population. The earlier estimates in this file of
"~698 tracts" and "~1,500-1,800 block groups" were expectations, not counts;
the confirmed figures above supersede them.

---

## 0. GLOBAL RULES (apply to every file)

- **GEOID as string, never numeric.** Read the tract/block-group ID column as
  text on load. If a tool parses it as a number it drops leading digits and
  joins fail silently. Tract GEOID = 11 digits starting `12086`. Block group
  GEOID = 12 digits, also starting `12086`.
- **Filter to Miami-Dade** by `GEOID.str.startswith("12086")`.
- **Row-count sanity check** after every filter: ~698 tracts. Far fewer means a
  geography setting slipped or the ID went numeric. Block-group files: ~1,500-1,800.
- **Keep vintages consistent within a source.** All ten ACS tables are 2024
  ACS 5-Year, Detailed Tables. Note the cross-source vintage gap: ACS marginals
  are 2020-2024 (5-year), SVI is 2022. Acceptable, but state it in methods.
- **Track the denominator universe per variable** (see ACS section). Person-level
  and household-level rates do NOT share a denominator. Do not compare or pool
  them as if they do.
- **Validate before trusting:** hand-check 2-3 specific tracts for each variable
  against data.census.gov (same table, same 2024 5-year vintage). If three
  tracts tie out, the logic holds across all 698 because it runs identically per
  tract.

---

## 1. ACS CRE-COMPONENT TABLES (ten files)

All: 2024 ACS 5-Year, Detailed Tables, census tract, Miami-Dade.
Each download has a DATA file (cryptic codes like `B01001_020E`) and a METADATA
file mapping codes to labels. Keep both; the metadata file is how you identify
the right columns.

For each: numerator = sum of the listed cells, denominator = the table Total
(`..._001E`), rate = numerator / denominator.

| var name | table | numerator cells (by label) | denominator universe | status |
|---|---|---|---|---|
| age65plus | B01001 | male + female bands: 65-66, 67-69, 70-74, 75-79, 80-84, 85+ (12 cells) | total population | clean |
| poverty_under125 | C17002 | Under .50 + .50 to .99 + 1.00 to 1.24 | pop w/ poverty status determined | THRESHOLD (CRE uses 1.30) |
| uninsured | B27001 | all "No health insurance coverage" rows | civilian noninstitutional pop | clean |
| disability | B18101 | all "With a disability" rows | civilian noninstitutional pop | clean |
| no_vehicle | B25044 | owner "No vehicle available" + renter "No vehicle available" | occupied housing units (HH) | clean |
| crowding_over100 | B25014 | 1.01 to 1.50 + 1.51 to 2.00 + 2.01 or more (owner + renter) | occupied housing units (HH) | THRESHOLD (CRE uses 0.75) |
| limited_english_hh | C16002 | all "Limited English speaking household" rows | households | clean |
| no_broadband | B28002 | Total − "Broadband of any type" | households | PROXY |
| no_fulltime_worker_hh | B08202 | "No workers" | households | PROXY (loose) |
| no_diploma_pop25 | B15003 | "No schooling completed" through "12th grade, no diploma" | population 25+ | PROXY (person-level) |
| single_zero_caregiver_hh | — | no clean public table | — | DROPPED |

### ACS cleaning steps
- **Coerce estimate columns to numeric**, turning ACS annotation / negative
  sentinel values into NaN. Then count NaNs per variable so suppression is
  visible, not silent.
- **Keep the margin-of-error (`..._M`) columns** alongside estimates. Needed if
  we weight by reliability later, and for the poverty/crowding threshold notes.
- **Threshold caveats to record in methods:**
  - poverty is `<1.25`, not CRE's `<1.30` (professor approved).
  - crowding is `>1.00` per room, not CRE's `>0.75` (professor approved).
- **Proxy flags to carry through to the writeup** (do not silently treat as
  exact): no_broadband, no_fulltime_worker_hh, no_diploma_pop25. no_fulltime is
  the loosest (counts households with zero workers, misses part-time/seasonal).
- **no_broadband method choice:** using Total − Broadband-of-any-type. If we
  switch to the stricter "No Internet access" row, note the change.
- If scripting the pull instead of manual: select numerator cells by matching
  the label TEXT, not hardcoded codes (codes shuffle between vintages). See
  pull_cre_components.py / validate_cre_components.py.

---

## 2. CDC/ATSDR SVI (one file) — DOWNLOADED

Source: CDC/ATSDR SVI Data & Documentation Download (svi.cdc.gov).
Selection: **2022, Florida, census tract.** Florida geography = percentiles
ranked within Florida (professor's choice, not national).

### SVI cleaning steps
- **FIRST STEP ON LOAD: replace -999 with missing (NA).** SVI marks
  uncomputable values as -999, not blank. If not fixed first, every -999 poisons
  any mean, model, or map. This is the single most common way an SVI analysis
  goes quietly wrong.
- **GEOID / FIPS column as string** (global rule).
- **Column families** (all pre-computed, do not build):
  - `E_*` = raw counts
  - `EP_*` = percentages (KEEP as reserve)
  - `EPL_*` = per-variable percentiles
  - `RPL_THEME1..4` = the four theme rankings
  - `RPL_THEMES` = overall ranking
- **Model inputs: INDIVIDUAL COMPONENTS, NOT composites.** Per the no-composite
  decision (same rule as ADI), use the `EP_*` per-indicator percentage columns
  as the SVI variables. Do NOT use the `RPL_THEME1..4` or `RPL_THEMES` rankings
  as model inputs — those are composites. Keep all `EP_*` indicators through the
  correlation stage; resolve overlaps (SVI vs CRE components) only at modeling.
- 2022 vintage matches the pasted indicator list (Housing cost burden, No health
  insurance, 150% poverty were added/current in 2022). Older vintages would be
  missing columns — stay on 2022.

---

## 3. BLOCK-GROUP SOURCES (downloaded)

### EJScreen (block group) — DOWNLOADED
- File on disk: `EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv` (national-percentile
  version; raw environmental values are identical to the state file, so this is
  the right one).
- Source: reconstruction of **v2.3** (PEDP / Harvard Dataverse), NOT epa.gov
  (withdrawn Feb 2025).
- Also want (if not already grabbed): `ejscreen-tech-doc-version-2-3.pdf` and
  `EJScreen_2024_BG_Percentiles_Columns.xlsx` (column dictionary).
- **13 raw environmental indicators** = EXPOSURE / risk inputs.
- **7 socioeconomic + 5 health indicators = KEEP through the correlation stage.**
  Do NOT pre-drop them. Professor wants to see how correlated everything is
  first. Only resolve TRUE duplicates at the modeling stage, and in the
  block-group analysis the overlap to watch is EJScreen socioeconomic vs ADI
  (NOT vs SVI/CRE — those are the separate tract analysis).
- IGNORE the pre-combined EJ Index / supplemental index columns for modeling
  (they already mix environment × demographics, which is what we're estimating).
- ID as string, filter `12086`, ~1,843 block groups. Check EJScreen's own
  missing-data conventions before computing.
- VERSION CHECK: confirm this is genuinely v2.3 — NO2, Underground Storage Tanks,
  and Drinking Water Non-Compliance columns must be present and populated (an
  older 2.2 reconstruction would silently leave 10 environmental indicators).
- Document provenance: withdrawn federal product, frozen at 2024, volunteer
  reconstruction. Cite source + version + access date. Spot-check a few block
  groups against an independent source.

### Area Deprivation Index / ADI (block group)

DECISION: no composite ADI score. Pull the individual components from ACS at
BLOCK-GROUP level (2024 ACS 5-Year, Detailed Tables), same manual process as the
tract CRE pulls but geography = Block Group, Florida, Miami-Dade, all block
groups. Expect ~1,843 block groups per file.

Pull ONLY the components that are NOT duplicates of EJScreen (unique-only rule).
Confirm the 4 dropped duplicates against EJScreen's data dictionary when that
file lands; if EJScreen defines one differently, it becomes "similar" not
"identical" and may be worth keeping after all.

**Pulling (13 unique components):**

| ADI component | ACS table | handling |
|---|---|---|
| Median family income | B19113 | median value, take directly (CONFIRMED available at block group) |
| Income disparity | B19001 | DERIVED, see formula below |
| % families below poverty | B17010 | rate — see B17010 note below |
| % below 150% poverty | C17002 | rate, sum bands under 1.50 |
| % age 25+ less than 9 years education | B15003 | rate, sum "No schooling completed" through "8th grade" ONLY — see B15003 note |
| Median home value | B25077 | median value |
| Median gross rent | B25064 | median value |
| Median monthly mortgage | B25088 | median value — use "with a mortgage" version (see note) |
| % owner-occupied | B25003 | rate — Owner occupied / Total |
| % without complete plumbing | B25049 | rate — TENURE version; see plumbing/kitchen note |
| % crowding, over 1 per room | B25014 | rate |
| % single-parent households w/ children | B11003 | rate — see single-parent note (verify BG) |
| % without complete kitchen facilities | B25053 | rate — TENURE version; see plumbing/kitchen note |

**Dropped as EJScreen duplicates (do NOT pull):** no motor vehicle,
no household internet, unemployment, at-least-HS-diploma (mirror image of
EJScreen "Less Than High School"). Also dropped: composite ADI index.

Education note: keeping ADI "less than 9 years" (more extreme threshold, distinct
from EJScreen's <HS). Dropping "at least HS diploma" (redundant complement).

**INCOME DISPARITY DERIVATION (from B19001, computed in analysis — not a pull):**
ADI income disparity is NOT a rate. It is the log ratio of low-income to
high-income households:
  - low  = count of households earning under $10,000  (bottom B19001 bracket)
  - high = count of households earning $50,000 or more (sum all B19001 brackets
           from $50,000 up)
  - income_disparity = log(low / high)  (per Singh 2003 ADI methodology)
CAVEAT: the $10,000 and $50,000 cutoffs are the original early-2000s ADI
thresholds and are NOT inflation-adjusted in standard ADI. In 2024 dollars they
are low. This is correct per the ADI definition; using inflation-adjusted cutoffs
instead would be a deliberate deviation to flag, not a default.

**B25049 plumbing & B25053 kitchen — SUM ACROSS TENURE:**
Both are Tenure by (Plumbing/Kitchen) Facilities. Structure: Total, then Owner
occupied (complete / lacking) and Renter occupied (complete / lacking).
  - numerator = owner "Lacking complete [plumbing/kitchen] facilities" + renter
    "Lacking complete [plumbing/kitchen] facilities" (SUM the two lacking rows
    across tenure). Do not take just one tenure.
  - denominator = Total (occupied housing units).

**B11003 single-parent households w/ children — WITH-CHILDREN ROWS ONLY:**
B11003 = Family Type by Presence and Age of Own Children. Structure: Total
families; Married-couple (with / without own children); Other family: Male
householder no spouse (with / without children); Female householder no spouse
(with / without children).
  - numerator = Male householder no spouse WITH own children under 18
    + Female householder no spouse WITH own children under 18 (2 rows).
  - Do NOT include the "no own children" rows, and do NOT include married-couple.
  - denominator = Total families.
  - CONFIRMED available at block group (has data for every block group; the
    file is wide because the family-type table has many cells, but every block
    group has a data row).

**B25088 (median monthly mortgage) — PICK THE RIGHT COLUMN:**
B25088 has two versions: median selected monthly owner costs for units WITH a
mortgage, and for units WITHOUT a mortgage. Use the WITH-a-mortgage version for
the ADI component. Median-dollar handling + block-group suppression apply.

**B15003 (education) — SAME TABLE, TWO DIFFERENT NUMERATORS. Do not mix them up:**
B15003 is pulled at BOTH grains for different analyses, with different cuts:
  - TRACT / CRE proxy (no_diploma_pop25): sum "No schooling completed" through
    "12th grade, no diploma" (everything below a HS diploma, i.e. <12 years).
  - BLOCK GROUP / ADI (less than 9 years): sum "No schooling completed" through
    "8th grade" ONLY. STOP at 8th grade — do NOT include 9th, 10th, 11th, or
    12th-no-diploma.
  Both are sum-the-bands. Denominator = Total (population 25+) in both. Easy to
  slip and apply the wrong cut — confirm which analysis the file feeds.

**B17010 (% families below poverty) — DO NOT SUM NESTED ROWS:**
B17010 breaks families into below-poverty vs at-or-above, then each into family
type (married / male / female householder) and presence+age of children.
  - numerator = the single subtotal row "Income in the past 12 months below
    poverty level" ONLY. It already contains all the family-type / children
    detail beneath it.
  - denominator = the top "Total:" row (total families).
  - Do NOT add the nested family-type or children rows — that double-counts.
  Contrast with C17002, where you DO sum bands. Table structure decides whether
  you sum or take a subtotal; check each before computing.

**BLOCK-GROUP COUNT NOISE (family / household tables like B17010, B11003):**
At block group these counts are tiny and carry very large margins of error
(e.g. estimate 33, MOE +/-37; zero rows show the +/-15 ACS floor). Values are
present, not suppressed, but imprecise. Keep the MOE columns. Do not treat point
estimates as exact — consider the noise when these become model features.

**BLOCK-GROUP MEDIAN SUPPRESSION (applies to all median variables above):**
Block-group medians are suppressed far more often than tract data because block
groups are small samples. Suppressed cells show as "-" (estimate) and "**"
(margin of error), NOT as zero or blank. These are ACS annotation flags.
  - On load, convert "-" and "**" to proper missing (NA). Same discipline as
    SVI's -999 but different symbols.
  - Count missing per median variable. If a median is missing for a large share
    of block groups, it may be too sparse to use — flag and consider a fallback.

Standardization caveat (if the composite is ever revisited): the Neighborhood
Atlas ADI is unstandardized and can collapse toward income + home value. NaNDA
Standardized ADI (openICPSR) is a robustness alternative. Not relevant while
pulling components only.

---

## 4. GEOGRAPHIC HARMONIZATION (downstream, once all sources are in)

- **Two grains.** SVI + ACS marginals are tract. EJScreen + ADI are block group.
  Block group → tract: the first 11 digits of a block-group GEOID ARE its tract.
  Aggregate block-group data up to tract (population- or household-weighted as
  appropriate) OR model those two at block-group level per the source doc.
- **Project / investment data** carries a scale tag (parcel / corridor /
  municipality / county) + point coordinates. Snap each record to the standard
  geography matching its true footprint (change-of-support):
  - parcel → census tract
  - corridor → census tract (crosses multiple tracts; NEEDS A RULE: assign to
    majority-length tract, or split investment across tracts it passes through)
  - municipality → city
  - county → county
  Read risk/vulnerability off the polygon at that record's real scale, not off
  the raw pin (a county pin misstates a county-wide footprint).
- **Recover municipality/county from pins** via point-in-polygon spatial join
  (Census TIGER boundaries), since only a scale tag + coordinates are in the data.
- **Nesting caveats:** tracts nest cleanly in counties (FIPS), but NOT cleanly
  in cities. Treat Unincorporated Miami-Dade as its own jurisdiction; let city
  enter as a cross-classified factor / covariate, not a strict nesting level.
- **Spatial weights (W):** define neighbors within ONE analysis scale. With
  points, build W from k-nearest-neighbors or a distance band.

### Open decisions pending from professor
- SVI national-vs-local ranking (Florida chosen for now; may re-rank to Miami-Dade).
- One model on a common tract grid (disaggregate city/county dollars down with an
  allocation rule, sensitivity-tested) VS three levels kept separate (stratified).

---

## 5. JURISDICTION STRUCTURE AND MULTILEVEL-MODEL CONSTRAINTS

Recorded because the professor has asked for a multilevel analysis of tract,
municipality and county effects. The constraints below are structural, not
fixable by cleaning, and need to be settled before the model is specified.

All figures verified against INVESTMENT_TABLES.md and output/ on 20 Sep 2026.

### How units are assigned to a jurisdiction

- Each unit is assigned to the **incorporated place containing its centroid**
  (TIGER 2024, `CLASSFP` = `C*`), computed in EPSG:6346.
- **Unincorporated Miami-Dade is its own jurisdiction, not a residual
  category.** It is governed directly by the county and functions as a single
  decision-making body, so treating it as one jurisdiction is substantively
  correct rather than a leftovers bucket.
- **Census designated places are not municipalities.** Kendall, Westchester,
  Tamiami and the rest are statistical labels with no government. They fold
  into Unincorporated Miami-Dade.

### Jurisdiction counts differ by grain, and the difference is structural

Counts are over the full investment-table frame: 707 tracts and 1,843 block
groups.

| grain | units in a municipality | unincorporated | distinct jurisdictions |
|---|---|---|---|
| tract | 392 | 315 | 33 |
| block group | 1,054 | 789 | 35 |

Miami-Dade has **34 incorporated municipalities**. With Unincorporated
Miami-Dade that is **35 possible jurisdictions**.

Block group reaches all 35. **Tract reaches only 33.** El Portal and Bay
Harbor Islands are physically smaller than a census tract, so no tract
centroid falls inside either, and neither is represented as a jurisdiction at
tract grain. Block groups are small enough to sit inside them, which is why
the finer grain recovers both.

**The general principle, worth stating once:** a model can only represent
structures larger than its own unit of analysis. This is the same constraint
that makes a county-scale project unmappable to a single tract.

### Centroid fallback, tract grain only

For a municipality with zero centroid-assigned tracts, recipients fall back to
tracts whose geometry **intersects** it, still population-weighted. This
applies to El Portal and Bay Harbor Islands only: **12 projects, $18,679,837,
7 tracts, 0.22 percent of the filtered total.** Without it those dollars have
nowhere to land and the reconciliation check fails. All other 32
municipalities use centroid assignment. Block groups need no fallback.

**The dollars are not lost.** They were distributed to intersecting tracts and
are present in the totals. What is missing at tract grain is only the
*jurisdiction label* for those two municipalities.

### Constraints for the multilevel model

These are modelling constraints, not data problems. None is fixed by more
cleaning.

**1. County cannot be a level.** A random effect needs multiple units to
estimate variance across, and there is one county. Anything county-wide is a
constant and is absorbed into the intercept. So "tract, municipality and
county simultaneously" is **two estimable levels: tracts nested in
jurisdictions.** The county layer is the intercept, not a level.

**2. The groups are severely unbalanced.** Unincorporated Miami-Dade holds
**315 of 707 tracts**, about 45 percent of the sample, as a single
jurisdiction, while some municipalities hold two or three tracts. Multilevel
models need a reasonable number of units per group to estimate group effects
stably, so the small jurisdictions will produce unstable estimates. **Check
the per-jurisdiction counts before interpreting any group effect**, rather
than assuming the imbalance away.

**3. Part of any jurisdiction effect is our own allocation rule.** Municipality
and county dollars were distributed population-weighted across each
jurisdiction's units, so **every tract in a given city received an identical
municipal amount per person by construction.** A multilevel model run on total
investment would find jurisdiction effects that are artifacts of that rule
rather than evidence of real allocation behaviour.

*Mitigation:* run the multilevel model on **single-unit investment only**,
meaning projects physically sited in a unit, which no rule distributed. That
outcome is clean by construction. The cost is **29.4 percent of the filtered
dollars**: single-unit projects account for $6,041,448,104 of the
$8,553,271,610 filtered total, so roughly three dollars in ten fall outside
this specification.

### One frame check to do before fitting

The jurisdiction counts above are computed over all **707** tracts, which is
the investment-table frame. The analysis frame is **698** after excluding the
nine zero-population tracts (see the exclusion rule in the analysis notes), so
the per-jurisdiction counts in a model fitted on 698 will be slightly smaller
than the table above. The nine excluded tracts are special-use areas such as
PortMiami, the airports and the Everglades, which sit disproportionately in
Unincorporated Miami-Dade. **Recount units per jurisdiction on the 698 frame
before fitting**, and do not carry the 707-based counts into the model
description.

### Methods-section disclosure, draft for later use

> Tracts were assigned to the jurisdiction containing their centroid, with
> Unincorporated Miami-Dade treated as a single jurisdiction. Two
> municipalities contained no tract centroid and are not represented as
> jurisdictions at tract level; their attributed investment, 0.22 percent of
> the filtered total, was distributed to intersecting tracts.

---

## 6. ANALYSIS-STAGE REMINDERS (not data cleaning, but don't lose them)

- **Vulnerability multicollinearity:** SVI, CRE, and the ACS marginals largely
  measure the same construct and are highly correlated. Do NOT stack them as
  co-predictors. Pick a primary vulnerability axis; use the others as robustness
  / cross-check.
- **Interaction is the point:** the core spec is
  `investment ~ risk + vulnerability + risk*vulnerability + controls`. Report
  simple slopes (effect of risk at low/med/high vulnerability), not the raw
  interaction coefficient.
- **Spatial diagnostic gate:** fit OLS, run Moran's I on the residuals. Only
  escalate to a spatial model (SDM etc.) if residuals are spatially clustered.
  For any spatial model, report direct/indirect impacts, not raw coefficients.
- **Zero-inflation check:** if many tracts have zero investment, consider a
  two-part / hurdle model.
- **Cost-record robustness:** rerun key results on corrected vs uncorrected cost
  data (the verification work is a built-in robustness check).

---

## 7. VARIABLE REDUCTION BEFORE PCA

Recorded 27 Sep 2026. Evidence: `correlation_screen.md` and
`output/correlation_screen/` (script `scripts/correlation_screen.py`).
Variable lists: `PCA_TRACT_VARS` and `PCA_BG_VARS` in
`scripts/analysis_variables.py`. No column was deleted from
`tract_analysis.csv` or `blockgroup_analysis.csv`; the full tables are kept for
traceability and the PCA selects variables through the lists.

### The rule

Professor's rule: for any pair of vulnerability indicators with |Spearman rho|
at or above 0.75 (pairwise-complete, compared unrounded), drop one of the two.
Anything below 0.75 is accepted and both variables are kept.

### The principle (tract)

Where an SVI indicator and its ACS twin both exist, keep the SVI version:

- every SVI version is graded clean, while three ACS twins are a proxy
  (`no_diploma_pop25`, `no_broadband`) or a threshold approximation
  (`poverty_under125`);
- SVI matches the professor's indicator list exactly;
- one source per concept avoids mixing data years (SVI 2022 describes 2018 to
  2022; the ACS pulls describe 2020 to 2024).

Tie-breakers were checked and did not separate the pairs: mean |rho| with the
other indicators and missingness were near identical within each pair. The
choice was **not** made on which version gave stronger results against
investment.

### Decisions (tract)

| cluster | keep | drop | Spearman rho | n |
|---|---|---|---|---|
| T1 | EP_NOHSDP | no_diploma_pop25 | +0.898 | 698 |
| T2 | EP_AGE65 | age65plus | +0.877 | 698 |
| T3 | EP_NOINT | no_broadband | +0.862 | 697 |
| T4 | EP_UNINSUR | uninsured | +0.849 | 698 |
| T5 | EP_NOVEH | no_vehicle | +0.841 | 697 |
| T6 | EP_POV150 | poverty_under125 | +0.825 | 697 |
| T7 | EP_LIMENG | limited_english_hh | +0.821 | 698 |
| T8 | EP_DISABL | disability | +0.764 | 698 |

All eight rho values verified against `correlation_screen.md`; no mismatch.
Filled-in sheet: `output/correlation_screen/correlation_decisions_tract.csv`.

### Accepted below the line (tract), recorded explicitly

- `EP_CROWD` and `crowding_over100`, +0.721: **both kept**. Same concept from two
  sources, but below 0.75, so the rule keeps both. Crowding is the one concept
  entering the tract PCA twice.
- `EP_POV150` and `EP_HBURD`, +0.746: both kept.
- `EP_NOHSDP` and `EP_LIMENG` (+0.705), `EP_NOHSDP` and `EP_MINRTY` (+0.700):
  both kept.

### Decisions (block group)

- No pair among the 24 social indicators reaches 0.75, so all 24 are kept.
  Near misses among them (low income vs below 150% poverty +0.718; median home
  value vs median mortgage +0.716 on n = 1,200; median family income vs low
  income -0.710 and vs below 150% poverty -0.706) are all accepted.
- **The 13 EJScreen environmental measures are excluded from the vulnerability
  PCA as exposure rather than vulnerability. PROVISIONAL, pending professor
  confirmation.** If they were ever included, cluster B1 (9 environmental
  measures, 8 links) would need four drops; `correlation_screen.md` lists the
  two minimal sets.

### Final PCA input lists

Tract, 19 variables (17 SVI + 2 ACS with no twin): EP_POV150, EP_UNEMP,
EP_HBURD, EP_NOHSDP, EP_UNINSUR, EP_AGE65, EP_AGE17, EP_DISABL, EP_SNGPNT,
EP_LIMENG, EP_MINRTY, EP_MUNIT, EP_MOBILE, EP_CROWD, EP_NOVEH, EP_GROUPQ,
EP_NOINT, no_fulltime_worker_hh, crowding_over100.

The seven SVI race adjuncts (EP_HISP, EP_AFAM, EP_ASIAN, EP_TWOMORE,
EP_OTHERRACE, EP_AIAN, EP_NHPI) are out of scope and in neither list. They are
still present as columns in `tract_analysis.csv`, which was not updated.

Block group, 24 variables:
- EJScreen socioeconomic (7): PEOPCOLORPCT, LOWINCPCT, UNEMPPCT, LINGISOPCT,
  LESSHSPCT, UNDER5PCT, OVER64PCT
- EJScreen health (2): DISABILITYPCT, LIFEEXPPCT
- ADI components (13): median_family_income, income_disparity,
  poverty_pct_families, poverty_under150, no_diploma_under9yrs,
  median_home_value, median_gross_rent, median_monthly_mortgage,
  pct_owner_occupied, pct_no_plumbing, pct_crowding_over100,
  pct_single_parent_children, pct_no_kitchen
- ACS added late (2): no_vehicle, no_broadband

### Pending items

1. **Environmental exclusion at block group** (above): provisional until the
   professor confirms.
2. **2020 decennial census at block group.** The professor suggested 2020
   decennial data at block group. It could replace population, aged 65 and
   over, aged under 5, owner-occupied share and single-parent households
   (full-count values instead of small-sample ACS estimates). If approved, the
   block-group PCA must be rerun.
