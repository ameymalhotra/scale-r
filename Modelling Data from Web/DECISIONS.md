# Decision log

**Rule: every new decision gets an entry here at the time it is made.** Add it
under its topic with the next free number. Never renumber or delete an entry.
If a decision is reversed, add a new entry that says which one it replaces,
and change the old entry's status to "Replaced by D-xxx".

This log exists so the methods section of a paper can be written from it.
Each entry has the same ten fields. Dates are when the decision was made. Where
only the report date is known, the date reads "before <date>".

Who decided:
- **Professor Paharaj**: the files say the professor set, approved or chose
  it.
- **Amey, confirmed by professor**: proposed by Amey and approved.
- **Amey**: made in the analysis.

Where a file records a decision without naming who made it, the entry says
"(not recorded)" and gives the most likely owner.

Backfilled on 5 November 2026 from:
- `DATA_PROCESSING.md`;
- every report in this folder;
- the prompts in `prompts/`;
- the scripts.

## Contents

| Topic | Entries |
|---|---|
| Project data | D-001 to D-006 |
| Geography | D-007 to D-014 |
| Social indicators | D-015 to D-026 |
| Physical indicators | D-027 to D-033 |
| Population exposure | D-034 to D-044, D-069 |
| Investment measures | D-045 to D-050 |
| Analysis methods | D-051 to D-060, D-067 |
| Project organization | D-061 to D-066, D-068, D-070 |
| Machine learning | D-071 onward |
| Impact data (FEMA claims and grants) | D-113 to D-118 |
| Benefit simulator (prompt 27) | D-119 onward |

---

## Project data

### D-001. One project file

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: The project inventory looked for every file that could hold
  project records.
- What is wrong: Nothing, once confirmed. Without the check, an old export
  could have been mixed in.
- How we are fixing it: Use `SCALE-R_Database.csv` as the only source of
  projects. It is the only non-census file in the folder.
- Decision: `SCALE-R_Database.csv` (1,664 projects) is the single project
  source.
- Reason: One file means one set of costs, statuses and scale tags.
- Evidence: `project_data_profile.md`, Step 1.
- Affects: Every investment table.

### D-002. Status filter

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey (not recorded;
  the same filter is restated in prompt 22 as the rule for the project).
- What happened: Projects carry a status: Completed, Funded, Ongoing or
  Planned.
- What is wrong: Planned projects have no committed money. Counting them
  would treat intentions as investment.
- How we are fixing it: Keep only Completed, Funded and Ongoing projects.
- Decision: 1,405 of 1,664 projects ($8,553,271,609.50) are in scope. The 259
  Planned projects are excluded from every investment measure.
- Reason: Only committed or spent money is investment. Planned projects are
  kept apart as the "future" set for the machine learning work (prompt 22).
- Evidence: `INVESTMENT_TABLES.md` (Scope); `scripts/01_projects/build_investment_tables.py`;
  `prompts/claude_code_prompt_22_ml_scenario_module.md` (Rules).
- Affects: `tract_investment.csv`, `blockgroup_investment.csv`,
  `tract_analysis.csv`, `blockgroup_analysis.csv`, the ML training set.

### D-003. Allocation rules

- Date: before 12 Sep 2026. Status: Final. Decided by: Professor Paharaj.
- What happened: Each project has a scale tag (parcel, neighborhood,
  corridor, municipality, county) and a point location.
- What is wrong: A point misstates where county-wide or city-wide money goes.
  Putting a county project's full cost on the tract under its pin would be
  wrong.
- How we are fixing it:
  - Parcel, neighborhood and corridor projects go whole to the unit
    containing the point.
  - Municipality projects are spread by population across that
    municipality's units.
  - County projects are spread by population across all 707 tracts or 1,843
    block groups.
- Decision: The professor's scale classification is used exactly as given;
  no scale tag is reclassified.
- Reason: The scale tag is the professor's call. Population weighting is the
  simplest neutral rule for money with no single location.
- Evidence: `INVESTMENT_TABLES.md` (Allocation rules); audit ledgers
  `data/processed/investment/allocation_audit_tract.csv` and `_bg.csv`, which reconcile to the
  dollar.
- Affects: Every investment outcome. It is also why jurisdiction effects are
  partly built in (D-048).

### D-004. County-tagged projects with a municipal jurisdiction

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Some county-tagged projects name a municipality as their
  jurisdiction: Cutler Bay, Miami Beach, Sunny Isles Beach, and 2 SFWMD
  projects.
- What is wrong: The two fields disagree.
- How we are fixing it: The scale tag drives allocation, so these are spread
  county-wide.
- Decision: Used as given, not corrected.
- Reason: Correcting them would mean reclassifying the professor's scale
  tags (D-003).
- Evidence: `INVESTMENT_TABLES.md`; `project_data_profile.md` (SFWMD is not a
  municipality).
- Affects: County-path dollars.

### D-005. Jurisdiction name normalization

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: The project file runs some names together (`MiamiBeach`) and
  spells two differently from TIGER (`Opa-Locka`, `Indian Creek Village`).
- What is wrong: The names would not match the TIGER places, and those
  projects would fail to allocate.
- How we are fixing it: Normalize names to TIGER spelling. Nothing is
  reclassified.
- Decision: All 34 municipality names resolve after spelling normalization.
- Reason: It is a spelling fix, not a judgement.
- Evidence: `INVESTMENT_TABLES.md`; `scripts/common/allocation.py`
  (`normalize_municipality`).
- Affects: The municipality path.

### D-006. Large footprint projects flagged, not removed

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: 5 SMART Program transit corridors and 19 SFWMD basin
  projects cover far more ground than their points suggest. One corridor is
  $4.2 billion.
- What is wrong: Their footprint is misrepresented by a point.
- How we are fixing it: Model them normally and flag every receiving unit
  (`flag_large_project`) so results can be rerun without them.
- Decision: Kept and flagged.
- Reason: Dropping them would remove real money. Flagging allows a
  robustness check.
- Evidence: `INVESTMENT_TABLES.md` (columns); `project_data_profile.md`.
- Affects: All outcomes; robustness checks in `RESULTS_FOR_REVIEW.md` section 6.

---

## Geography

### D-007. 698-tract analysis frame

- Date: before 16 Sep 2026. Status: Final. Decided by: Amey (not recorded;
  the files say "the decision already made").
- What happened: Miami-Dade has 707 tracts. 9 have no residents (PortMiami,
  the airports, the Everglades and similar), and one has 28 residents
  (12086981100, Thompson Park / Pennsuco).
- What is wrong: Zero-population tracts have undefined per-person outcomes
  and no SVI or ACS values. The 28-person tract has $862,995 per person.
- How we are fixing it: Exclude only true zeros. Floors of 50, 100, 250 and
  500 were tested; at tract level they all remove the same one extra tract.
- Decision: The tract frame is 698 tracts. The 9 zero-population tracts are
  excluded and the 28-person Pennsuco tract is kept. No block group is
  excluded.
- Reason: Exclusion on population = 0 is a rule, not a judgement about an
  outlier. It removes $301,575,705 (3.53%). The Pennsuco tract is a real
  place with real residents. Since prompt 21 it is kept out of every top-10
  and top-20 list (D-043).
- Evidence: `zero_population_investigation.md` (Decision needed, Option 1);
  `correlation_analysis.md` Part 1; `scripts/common/analysis_variables.py`
  (`load_tract` asserts 698).
- Affects: All tract analyses, the ML frame, Stage B.

### D-008. Block groups as the second grain, composition only

- Date: before 16 Sep 2026; put to the professor 19 Sep 2026. Status: Pending
  professor. Decided by: Amey.
- What happened: Block groups (1,843) give finer detail. Their per-person
  investment is unstable: the maximum is $1.7M per person, and a 6-resident
  block group holds $6.6M.
- What is wrong: No population floor fixes the instability, and no hazard
  layer existed at block group then.
- How we are fixing it: Report block groups for binaries and type shares
  only, with no per-person or total outcomes.
- Decision: Tract is primary. Block group is reported in full as a
  composition and exposure analysis.
- Reason: Tract is the only grain where the investment-volume question can
  be asked soundly.
- Evidence: `correlation_analysis.md` Part 4d; `REVIEW_MEMO.md` section 4b
  and question 4.
- Affects: All block group analyses, including Stage B (D-042).

### D-009. Unincorporated Miami-Dade as its own jurisdiction

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: About 45% of tracts (315 of 707) are in no municipality.
  Census designated places such as Kendall and Westchester have no
  government.
- What is wrong: Treating "no municipality" as a leftover bucket would
  misdescribe it. It is governed directly by the county.
- How we are fixing it: Units not inside an incorporated place (TIGER
  `CLASSFP` C*) belong to "Unincorporated Miami-Dade". Census designated
  places fold into it.
- Decision: Unincorporated Miami-Dade is one jurisdiction.
- Reason: It acts as a single decision-making body.
- Evidence: `DATA_PROCESSING.md` section 5; `INVESTMENT_TABLES.md`.
- Affects: The municipality path, jurisdiction columns, and any multilevel
  model.

### D-010. Centroid assignment with intersect fallback

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Each unit is assigned to the municipality containing its
  centroid, computed in EPSG:6346. El Portal and Bay Harbor Islands are
  smaller than a tract, so no tract centroid falls in either.
- What is wrong: Without a fallback, their projects (12 projects,
  $18,679,837) have nowhere to land and the totals do not reconcile.
- How we are fixing it: For a municipality with no centroid-assigned unit,
  spread its money over units whose geometry intersects it, still by
  population.
- Decision: Centroid assignment everywhere, with the intersect fallback only
  for those two municipalities at tract grain (7 tracts, 0.22% of dollars).
- Reason: It keeps every dollar while changing only 0.22% of the
  allocation.
- Evidence: `DATA_PROCESSING.md` section 5; `INVESTMENT_TABLES.md`.
- Affects: Tract jurisdiction counts: 33 jurisdictions at tract, 35 at block
  group.

### D-011. County cannot be a model level

- Date: 20 Sep 2026. Status: Final. Decided by: Amey (in response to the
  professor's multilevel request).
- What happened: The professor asked for a multilevel model of tract,
  municipality and county effects.
- What is wrong: There is one county, so it has no variance to estimate.
  Groups are also very unbalanced: unincorporated holds 315 of 707 tracts.
- How we are fixing it: Two estimable levels, tracts within jurisdictions.
  The county is the intercept. Run on single-unit investment (D-048), and
  recount units per jurisdiction on the 698 frame before fitting.
- Decision: County is the intercept, not a level.
- Reason: A random effect needs several units to estimate variance across.
- Evidence: `DATA_PROCESSING.md` section 5 (constraints 1 to 3).
- Affects: Any multilevel model.

### D-012. EPSG:6346 for all area work

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: TIGER, NOAA and NHC data come in geographic coordinates
  (EPSG:4269). Landsat comes in UTM 17N (EPSG:32617).
- What is wrong: Areas in degrees are meaningless.
- How we are fixing it: Reproject to NAD83(2011) / UTM 17N (EPSG:6346) before
  any area or centroid calculation. Categorical rasters are never
  reprojected; units are projected onto the raster grid instead.
- Decision: EPSG:6346 for every area, centroid and overlay.
- Reason: It is a metric, conformal projection for south Florida, and is
  used everywhere in the project.
- Evidence: `scripts/common/allocation.py` (`PROJ_CRS`); `slr_processing.md`;
  `population_exposure.md` 2.3.
- Affects: Centroids, land shares, exposure.

### D-013. TIGER 2024 boundaries to match ACS 2020 to 2024

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Boundaries must match the population table they carry.
- What is wrong: A boundary vintage different from the ACS geography would
  break the GEOID joins.
- How we are fixing it: Use TIGER/Line 2024 tracts, block groups, area
  water and places, which match the ACS 2024 five-year geography. 2020 census
  blocks, used only to place people, nest exactly in them: the block load
  checks that every block group matches.
- Decision: TIGER 2024 for all units.
- Reason: Same geography as the population data: 707 tracts and 1,843 block
  groups, confirmed.
- Evidence: `DATA_PROCESSING.md` (header); `scripts/common/population_surface.py`
  (block group match check).
- Affects: All tables.

### D-014. GEOID as a string; Miami-Dade filter

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Tools read GEOIDs as numbers by default.
- What is wrong: That drops leading digits, and joins fail silently.
- How we are fixing it: Read every GEOID as text and filter on prefix
  `12086`. Check row counts after every filter.
- Decision: GEOID is always a string: 11 digits for tracts, 12 for block
  groups.
- Reason: It prevents silent join failures.
- Evidence: `DATA_PROCESSING.md` section 0.
- Affects: Every table.

---

## Social indicators

### D-015. No composite indices; individual components only

- Date: before 11 Sep 2026. Status: Final. Decided by: Professor Paharaj.
- What happened: SVI, ADI, CRE and EJScreen all publish composite scores.
- What is wrong: A composite hides which component drives a result, and some
  composites mix exposure with demographics.
- How we are fixing it: Use each index's individual indicators:
  - SVI `EP_*` percentages;
  - ADI components rebuilt from ACS;
  - EJScreen raw indicators, ignoring its EJ indexes.
- Decision: No composite index enters any analysis.
- Reason: The professor's rule. It keeps each indicator interpretable.
- Evidence: `DATA_PROCESSING.md` sections 2 and 3; `nri_audit.md` (the same
  logic applied to FEMA, D-027).
- Affects: All vulnerability variables, the PCA, and the CDC Heat & Health
  Index exclusion (D-033).

### D-016. ACS 2020 to 2024 five-year

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: ACS tables are pulled at tract and block group.
- What is wrong: Mixing vintages within a source makes rates incomparable.
- How we are fixing it: All ACS pulls are 2024 five-year Detailed Tables.
  Numerator cells are chosen by label, not code. MOE columns are kept.
  Annotation flags become NA.
- Decision: ACS 2020 to 2024 for every ACS variable and for population.
- Reason: The most recent five-year data, in one vintage.
- Evidence: `DATA_PROCESSING.md` sections 0 and 1.
- Affects: Population, CRE components, ADI components.

### D-017. SVI 2022, Florida ranking

- Date: before 11 Sep 2026. Status: Provisional (ranking may change). Decided
  by: Professor Paharaj.
- What happened: SVI is published for several years and ranking areas.
- What is wrong: Older vintages lack some indicators. Uncomputable values
  are coded −999, which poisons means if not caught.
- How we are fixing it: Use 2022, Florida, census tract. Replace −999 with
  NA on load. Use the `EP_*` columns only.
- Decision: SVI 2022 with Florida ranking. The professor may re-rank to
  Miami-Dade.
- Reason: 2022 has the current indicator list. Florida ranking was the
  professor's choice.
- Evidence: `DATA_PROCESSING.md` section 2, and "Open decisions pending from
  professor".
- Affects: The 24 SVI tract variables. The vintage gap (SVI describes 2018 to
  2022, ACS 2020 to 2024) is stated in methods.

### D-018. Poverty and crowding thresholds

- Date: before 11 Sep 2026. Status: Final. Decided by: Professor Paharaj.
- What happened: CRE uses poverty below 1.30 times the line and crowding
  above 0.75 people per room. ACS bands do not split there.
- What is wrong: The exact CRE thresholds cannot be built.
- How we are fixing it: Use poverty below 1.25 and crowding above 1.00, and
  record both as threshold departures.
- Decision: `poverty_under125` and `crowding_over100`.
- Reason: The nearest ACS bands. The professor approved both.
- Evidence: `DATA_PROCESSING.md` section 1 (Threshold caveats).
- Affects: Two tract CRE variables.

### D-019. Proxy variables flagged; one variable dropped

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Three CRE components have no exact ACS table.
- What is wrong: Treating a proxy as exact would overstate precision.
- How we are fixing it: Carry proxy flags through to the write-up.
  - `no_broadband`: total minus broadband of any type.
  - `no_fulltime_worker_hh`: households with no workers, the loosest proxy.
  - `no_diploma_pop25`: person-level, not household-level.
  - The single or zero caregiver component has no public table and is
    dropped.
- Decision: Three proxies kept and flagged; one component dropped.
- Reason: Keep what can be measured and say how.
- Evidence: `DATA_PROCESSING.md` section 1.
- Affects: Tract CRE variables.

### D-020. EJScreen v2.3 reconstruction

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: EPA withdrew EJScreen in February 2025.
- What is wrong: The only available copy is a volunteer reconstruction.
- How we are fixing it:
  - Use the PEDP / Harvard Dataverse v2.3 reconstruction
    (`EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv`).
  - Verify the v2.3 columns: NO2, underground storage tanks, drinking water.
  - Cite source, version and access date.
  - Ignore the EJ index columns.
- Decision: EJScreen v2.3 reconstruction at block group.
- Reason: It is the only source of these block group environmental measures.
- Evidence: `DATA_PROCESSING.md` section 3. Only 2 of the 5 expected health
  indicators exist in this file (`RESULTS_FOR_REVIEW.md` 7a).
- Affects: 13 environmental, 7 socioeconomic and 2 health block group
  variables.

### D-021. ADI built from individual ACS components

- Date: before 11 Sep 2026. Status: Final. Decided by: Professor Paharaj (no
  composite); Amey (component list).
- What happened: The Neighborhood Atlas ADI is a composite.
- What is wrong: Four of its components duplicate EJScreen measures.
- How we are fixing it: Pull 13 unique ADI components at block group, ACS
  2024 five-year.
  - The four EJScreen duplicates are dropped: no vehicle, no internet,
    unemployment, and at-least-high-school.
  - Income disparity is log(households under $10,000 / households $50,000 or
    more), with the original cutoffs, not inflation-adjusted.
- Decision: 13 ADI components, no ADI score.
- Reason: No composite (D-015), and one source per concept.
- Evidence: `DATA_PROCESSING.md` section 3; `correlation_analysis.md` Part 1
  (the missing B25014 table was found and pulled).
- Affects: The block group ADI variables.

### D-022. Block group suppression handling

- Date: before 11 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Block group medians are often suppressed ("-" and "**").
  Small counts carry large MOEs.
- What is wrong: Read as zeros, the suppressed medians would bias every
  statistic.
- How we are fixing it: Convert the flags to NA. Count missing values per
  variable. Keep the MOEs.
- Decision: Suppressed means missing. Variables missing in more than 20% of
  block groups are flagged and also run without them in the PCA.
- Reason: Missing is not zero.
- Evidence: `DATA_PROCESSING.md` section 3; `pca_analysis.md` (21-variable
  run).
- Affects: Block group medians, the PCA.

### D-023. Race adjunct columns out of scope

- Date: 27 Sep 2026. Status: Final. Decided by: Amey (not recorded; confirm).
- What happened: SVI carries seven race and ethnicity adjunct columns
  (EP_HISP, EP_AFAM, EP_ASIAN, EP_AIAN, EP_NHPI, EP_TWOMORE, EP_OTHERRACE).
- What is wrong: They are not on the professor's indicator list, and they
  overlap EP_MINRTY.
- How we are fixing it: Leave them out of both PCA lists. They stay in
  `tract_analysis.csv`.
- Decision: Out of scope for the vulnerability PCA.
- Reason: Not on the indicator list.
- Evidence: `DATA_PROCESSING.md` section 7 (Final PCA input lists);
  `scripts/common/analysis_variables.py` (`_RACE_ADJUNCTS`).
- Affects: The PCA inputs.

### D-024. Environmental measures excluded from the vulnerability PCA

- Date: 27 Sep 2026. Status: Pending professor (provisional). Decided by:
  Amey.
- What happened: The 13 EJScreen environmental measures are highly
  intercorrelated. Cluster B1 has 9 measures and 8 links at 0.75 or above.
- What is wrong: They measure exposure, not social vulnerability. Including
  them would also need four drops under the 0.75 rule.
- How we are fixing it: Exclude them from the vulnerability PCA. The two
  minimal drop sets are listed in case they are included.
- Decision: The block group PCA uses 24 social indicators only.
- Reason: Exposure and vulnerability should not be mixed in one index.
- Evidence: `DATA_PROCESSING.md` section 7; `correlation_screen.md`.
- Affects: The block group PCA.

### D-025. 2020 decennial counts at block group

- Date: before 27 Sep 2026. Status: Pending professor. Decided by:
  Professor Paharaj (suggestion).
- What happened: The professor suggested 2020 decennial data at block group.
- What is wrong: ACS block group estimates are small samples with large MOEs.
- How we are fixing it: If approved, replace population, aged 65 and over,
  aged under 5, owner-occupied share and single-parent households with full
  counts, then rerun the block group PCA.
- Decision: Not yet made.
- Reason: Full counts are more precise than small-sample estimates.
- Evidence: `DATA_PROCESSING.md` section 7 (Pending items, 2).
- Affects: The block group PCA and five block group variables.

### D-026. SVI kept over its ACS twin in eight pairs

- Date: 27 Sep 2026. Status: Final. Decided by: Amey (applying the
  professor's 0.75 rule, D-053).
- What happened: Eight SVI and ACS pairs measure the same concept, with
  Spearman between +0.764 and +0.898.
- What is wrong: Keeping both would double-count each concept.
- How we are fixing it: Keep the SVI version and drop the ACS twin:
  no_diploma_pop25, age65plus, no_broadband, uninsured, no_vehicle,
  poverty_under125, limited_english_hh and disability.
- Decision: Keep SVI in all eight pairs. Crowding (+0.721) is below the line,
  so both versions are kept.
- Reason:
  - every SVI version is graded clean;
  - three of the ACS twins are proxies or threshold approximations;
  - SVI matches the professor's list;
  - it keeps one data year per concept.
  The choice was not made on results against investment.
- Evidence: `DATA_PROCESSING.md` section 7;
  `outputs/correlation/correlation_screen/correlation_decisions_tract.csv`.
- Affects: The 19-variable tract PCA list.

---

## Physical indicators

### D-027. FEMA NRI expected annual loss only

- Date: 19 Sep 2026. Status: Final. Decided by: Amey (applying D-015).
- What happened: The NRI file has composite risk scores alongside expected
  annual loss.
- What is wrong: The risk score is loss times social vulnerability divided by
  community resilience. Those are SVI and CRE, already our predictors. Using
  it would put the predictors on both sides of the model.
- How we are fixing it: Use expected annual loss columns only. Exclude
  RISK_*, SOVI_*, RESL_*, CRF_VALUE and every per-hazard RISKS / RISKR column.
- Decision: NRI enters only as expected annual loss.
- Reason: It avoids building our predictors into the outcome.
- Evidence: `nri_audit.md` (The exclusion to carry forward; Task 3).
  Note: no NRI column has been joined to the analysis tables yet (D-044).
- Affects: Any NRI variable, the hazard screen, the ML features.

### D-028. Sea level rise: connected and low-lying kept apart, land only

- Date: 22 Sep 2026. Status: Final. Decided by: Amey (the land-only
  footprint was confirmed during processing).
- What happened: NOAA ships ocean-connected (`_slr_`) and unconnected
  low-lying (`_low_`) layers. Its polygons include existing open water.
- What is wrong: Intersecting raw unit polygons would count bay water as
  flooded land and could push shares above 1. The two layers are disjoint
  (0.000 km² overlap at 3 ft), so they cannot be treated as nested.
- How we are fixing it:
  - The footprint is each unit minus TIGER area water (AWATER > 0 only).
  - `gridcode` is ignored.
  - `_slr_` is primary at 1, 2, 3 and 6 ft; `_low_` is a 3 ft sensitivity.
- Decision: Land-only shares, with the two layers never combined.
- Reason: The numerator and denominator are both land. The two layers
  measure different places (Spearman −0.106 at 3 ft).
- Evidence: `slr_processing.md` (Land footprint; `_slr_` versus `_low_`);
  `slr_inspection.md`.
- Affects: `slr_tract.csv`, `slr_blockgroup.csv`, population exposure.

### D-029. Storm surge read as raw values

- Date: 22 Sep 2026. Status: Final. Decided by: Amey.
- What happened: In the NHC rasters, 255 is the nodata tag, but on county
  land it also means "not inundated". 99 is levee. Classes 1 to 21 are 1 ft
  depth bins.
- What is wrong: A masked or nodata-aware read drops dry land from the
  denominator and inflates every share.
- How we are fixing it:
  - Read raw values only.
  - On land, 255 means dry and stays in the denominator.
  - 99 is counted separately and never enters a depth (0 pixels in
    Miami-Dade).
  - Use only the June 2026 reprocessing, which fixed a South Florida bug.
- Decision: Raw-value handling for every surge calculation.
- Reason: It is the only correct reading of this file's coding.
- Evidence: `surge_inspection.md` (1c, 1e); `scripts/03_physical/process_surge.py`.
- Affects: `surge_tract.csv`, `surge_blockgroup.csv`, population exposure.

### D-030. Category 5 hole corrected by pixel maximum

- Date: 5 Nov 2026 (the hole was found 22 Sep 2026). Status: Final. Decided
  by: Amey (specified in prompt 21).
- What happened: In central Miami, some land is wet at Category 4 or lower
  but 255 (dry) at Category 5.
- What is wrong:
  - 31 tracts have a smaller Category 5 land share than Category 4, by up to
    0.94.
  - In residents, 18,928 people sit in the hole.
  - 26 tracts lose 16,599 residents between Category 4 and 5.
- How we are fixing it: Build `cat5max`, the deepest class over Categories 1
  to 5 at each pixel, and flag units where the hole holds at least 1% of
  residents.
- Decision: Only the corrected Category 5 (`cat5max`) is used. The raw
  version stays in the files for reference.
- Reason: The hole is a product artefact, not a hazard.
- Evidence: `outputs/physical/surge_processing_log.txt` (monotonicity);
  `population_exposure.md` section 3; `exposure_vs_investment.md` section 2.
- Affects: Every Category 5 measure, Stage B, the ML scenarios.

### D-031. Primary hazard scenarios

- Date: 3 Nov 2026 (prompt 21); amended 5 Nov 2026 (D-036). Status:
  Provisional (confirm with professor). Decided by: Amey.
- What happened: Sea level rise has 21 scenarios and surge has 5 categories.
- What is wrong: Picking the scenario that gives the strongest result would
  be fishing.
- How we are fixing it: Fix the primary scenarios in advance and show the
  rest as sensitivity.
- Decision:
  - Primary: sea level rise 3 ft (ocean-connected), and storm surge
    Categories 3 and 4 (any inundation).
  - Heat: the population-weighted mean and the 95th percentile share
    (D-036).
- Reason: 3 ft is a mid-range planning level. Categories 3 and 4 separate
  coastal and inland exposure, while Category 5 floods 62% of residents.
- Evidence: `prompts/claude_code_prompt_21_population_exposure.md`
  (A3, Stage B); `population_exposure.md`.
- Affects: Stage B, the ML scenarios.

### D-032. FEMA flood zone file unusable

- Date: 5 Nov 2026. Status: Pending (re-download). Decided by: Amey.
- What happened: The file in `data/raw/physical/flood_zones/` is
  a CSV with zone codes and areas but no geometry.
- What is wrong: Without geometry it cannot be overlaid on tracts or blocks.
- How we are fixing it: Skip it. A National Flood Hazard Layer download with
  geometry is needed.
- Decision: Flood zones are not used until a file with geometry is
  available.
- Reason: No way to place the zones.
- Evidence: `population_exposure.md` 2.3 and section 5; `nri_audit.md` Task 4.
- Affects: Physical indicators (pending).

### D-033. Heat from Landsat surface temperature

- Date: 3 Nov 2026 (prompt 21). Status: Final. Decided by: Amey.
- What happened: Three heat sources were available: Landsat surface
  temperature, the CDC Heat & Health Index, and FEMA heat wave loss.
- What is wrong:
  - The CDC index is a composite that includes vulnerability (D-015).
  - FEMA heat wave loss is a tract-level dollar estimate, not a map. Its
    building loss is effectively zero in this county.
- How we are fixing it: Use the Landsat 8/9 Collection 2 Level-2 summer
  median composite, June to September 2021 to 2024, at 30 m. Call it
  "surface heat", not air heat.
- Decision: Landsat surface temperature is the heat hazard.
- Reason: It is the only heat source that is a map and not a composite.
- Evidence: prompt 21 (A3); `nri_audit.md` Task 4; `population_exposure.md`
  2.3.
- Affects: Heat exposure, Stage B, ML heat features.

---

## Population exposure

### D-034. Built from the original hazard data

- Date: 3 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The website already had resident counts read off its
  animation images (`slr.png`, `surge.png`, `heat.png`).
- What is wrong: Those are Web Mercator renderings at reduced resolution,
  with values encoded for display:
  - 30 m pixel centres for flooding;
  - 60 m averaged pixels for heat.
  Heat at 113°F comes out 8% lower than from the original raster.
- How we are fixing it: Compute from the NOAA polygons, the NHC GeoTIFFs and
  the Landsat composite. Use the website numbers only for comparison.
- Decision: Website images are never model inputs.
- Reason: Analysis needs the source data at full resolution.
- Evidence: prompt 21 (A1); `population_exposure.md` section 3 (website
  comparisons).
- Affects: `exposure_tract.csv`, `exposure_blockgroup.csv`.

### D-035. Residents spread evenly over block land

- Date: 3 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Population is known per block group (ACS) and per block
  (2020 census), not per building.
- What is wrong: Within a block, the location of people is unknown.
- How we are fixing it:
  - Split each block group's ACS count over its 2020 blocks by their 2020
    counts.
  - Spread each block's residents evenly over its land.
  - Exposed residents = block residents × exposed share of the block's land.
  - Sum to block groups and tracts. Report nothing below block group.
- Decision: Even spread within the block is the stated assumption.
- Reason: It is the finest defensible placement without building
  footprints. No raw footprint file exists, so the footprint sensitivity
  could not be run.
- Evidence: `population_exposure.md` 2.1 and 2.2, and section 5 item 6.
- Affects: Every population exposure variable.

### D-036. Heat threshold for population exposure

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 21 defined heat exposure as residents on land at or
  above the county 75th percentile of surface temperature.
- What is wrong: The percentile is taken over all county land, including the
  cooler Everglades. So 96% of residents live above it, and the median tract
  share is 0.999. The measure cannot tell tracts apart.
- How we are fixing it: Use the population-weighted mean surface
  temperature, and the share of residents at or above the county 95th
  percentile (113.27°F).
- Decision: The 75th percentile is not used. The primary heat measures are
  the population-weighted mean and the 95th percentile share.
- Reason: A measure with almost no variation adds nothing to correlations or
  models. The mean is continuous, and the 95th percentile still varies
  (27.7% of residents county-wide).
- Evidence: `population_exposure.md` (2.3 update, 4.1); `exposure_tract.csv`.
- Affects: Stage B heat measures, ML heat features and heat scenarios.

### D-037. Fractional pixel coverage by supersampling

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Small blocks cover only a few surge or heat pixels.
- What is wrong: A pixel-centre rule can miss or overcount partial pixels.
  exactextract is not installed, and nothing may be downloaded.
- How we are fixing it: Split each pixel into 4 × 4 sub-cells. Compute the
  pixel-centre version too, and compare.
- Decision: Fractional coverage (4 × 4) for every raster layer.
- Reason: The prompt requires fractional coverage. The two methods differ by
  at most 0.05% in county totals.
- Evidence: `population_exposure.md` 2.3 and section 3;
  `outputs/exposure/stage_a/exposure_county_totals.csv`.
- Affects: Surge and heat exposure.

### D-038. Data cautions adopted, with their flags

- Date: 3 Nov 2026 (cautions); 5 Nov 2026 (flag cutoffs). Status: Final.
  Decided by: Amey.
- What happened: Prompt 21 listed 16 standard cautions for this kind of
  data.
- What is wrong: Each one could mislead if ignored. Examples: worst-case
  surge read as a forecast, surface heat read as air heat, block noise, small
  units.
- How we are fixing it: Each caution is handled in the method or written
  into Limitations. The flags in the files:
  - `low_pop_flag`: under 100 residents; 10 tracts, 16 block groups.
  - `bg_low_reliability`: CV above 40%; 79 block groups.
  - `surge_cat5_hole_flag`: hole holds at least 1% of residents; 30 tracts,
    63 block groups.
  - `heat_nodata_share`.
- Decision: All 16 cautions apply to every use of the exposure layers.
- Reason: These are the known failure modes of these datasets.
- Evidence: prompt 21 (Data cautions); `population_exposure.md` section 5.
- Affects: Every exposure result.

### D-039. Website script reverted; shared logic in a new module

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Early in Stage A, an optional `crs` argument was added to
  `load_blocks()` in `scripts/website/build_population_exposure.py`. Prompt 21 had
  said not to change that script.
- What is wrong: It changed a website script, even though not its outputs.
- How we are fixing it: Revert the file with `git checkout`, and copy the
  logic into `scripts/common/population_surface.py`. Confirm that the copy
  reproduces the block checkpoint exactly: 25,805 blocks, a difference of 0.0
  residents and 0.0 m².
- Decision: The website script is unchanged. The analysis imports
  `population_surface.py`.
- Reason: It keeps the website untouched while reusing the same logic. The
  two copies must be kept in step.
- Evidence: `population_exposure.md` 2.1; git shows the website script
  unmodified.
- Affects: `scripts/04_exposure/build_exposure_layers.py`.

### D-040. Stage B: one measure per hazard family

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The hazard correlation screen found 157 tract pairs at
  |rho| ≥ 0.75, all within a single hazard family. Examples: neighbouring
  scenarios, and population share against land share.
- What is wrong: Reporting every member of a family would repeat the same
  signal many times.
- How we are fixing it: Report one measure per family at the primary
  scenarios. The others are sensitivity only.
- Decision:
  - Primary measures: `slr_3ft_pop_share`, `surge_cat3_any_pop_share`,
    `surge_cat4_any_pop_share`, `heat_lst_popwt_mean_f`,
    `heat_p95_pop_share`.
  - Land shares are for comparison only.
- Reason: The 0.75 rule (D-053) applied to the hazard families. No pair
  crossed families, so one measure per family is enough.
- Evidence: `population_exposure.md` 4.6; `exposure_vs_investment.md`
  section 2.
- Affects: Stage B, ML features.

### D-041. Stage B: corrected Category 5 only

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Stage A built both raw Category 5 and `cat5max`.
- What is wrong: Raw Category 5 contains the hole (D-030).
- How we are fixing it: Use `cat5max` only, as sensitivity.
- Decision: Raw Category 5 is not analysed.
- Reason: The hole is an artefact.
- Evidence: `exposure_vs_investment.md` section 2.
- Affects: Stage B sensitivity.

### D-042. Stage B: pairing rule, single-unit repeat, block group scope

- Date: 3 Nov 2026 (prompt 21). Status: Final. Decided by: Amey.
- What happened: Exposed-resident counts and investment totals both grow
  with population.
- What is wrong: Correlating a count with a count mostly measures size.
  Municipal and county money is spread by population, so it builds in
  jurisdiction patterns.
- How we are fixing it:
  - Shares go with per-person, per-area, binary and type share outcomes.
  - Counts go only with total investment, as a partial Spearman controlling
    for population, and raw with a note.
  - The main correlations are repeated on single-unit sited investment.
  - At block group, binaries and type shares only (D-008).
- Decision: As above.
- Reason: Caution 12, and the allocation constraint in `DATA_PROCESSING.md`
  section 5.
- Evidence: `exposure_vs_investment.md` section 2.
- Affects: Stage B.

### D-043. Small and unreliable units in Stage B

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: 10 tracts have under 100 residents (9 empty plus Pennsuco),
  and 79 block groups have CV above 40%.
- What is wrong: Their shares are unstable.
- How we are fixing it:
  - Keep the small tracts in the correlations, but leave them out of every
    top-10 and top-20 list.
  - Run block group results with and without the low-reliability units.
- Decision: As above. Removing the low-reliability block groups changed no
  correlation by more than 0.015.
- Reason: Flag, do not drop (cautions 7 and 8).
- Evidence: `exposure_vs_investment.md` 3.3 and 3.6.
- Affects: Stage B lists and block group results.

### D-044. NRI columns used in the hazard screen

- Date: 5 Nov 2026. Status: Provisional. Decided by: Amey.
- What happened: Prompt 21 asked to screen the FEMA NRI loss variables "in
  use".
- What is wrong: None is in use. No NRI column is joined to the analysis
  tables.
- How we are fixing it: Use the loss columns that `nri_audit.md`
  recommended: HWAV_EALT, CFLD_EALT, CFLD_EALB, IFLD_EALT, IFLD_EALB,
  HRCN_EALT and HRCN_EALB.
- Decision: These seven columns stand in until the NRI variables for the
  analysis are chosen.
- Reason: They are the audit's candidates. Heat wave building loss is
  effectively zero, so total loss is used for heat.
- Evidence: `population_exposure.md` 4.6 and section 5; `nri_audit.md`
  Tasks 4 and 5.
- Affects: The hazard screen; any later NRI join.

### D-069. Heat tercile investment analysis, by hazard focus

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Stage B found that the hottest third of tracts (by
  population-weighted mean surface temperature) received $1,669 per resident,
  against $4,968 for the coolest third.
- What is wrong: The figure mixes every kind of project. A few very large
  projects could drive it.
- How we are fixing it: Save the follow-up as a script and a report:
  - the same terciles as Stage B (equal-count, 698 tracts, the 28-person
    tract kept);
  - dollars from the allocation ledger, so the allocation rules are
    unchanged, for all projects and sited only;
  - pooled (total dollars ÷ total residents), tract mean and tract median;
  - a breakdown by each `Hazard_Focus` value plus flood-related (Flooding,
    Coastal Hazards, Storms & Hurricanes);
  - Extreme Heat project counts;
  - sensitivity: drop The Underline Phases 2 and 3 and SCALER-0595 (S1), and
    the five largest heat projects (S2). Also a count measure, sited heat
    projects per 100,000 residents.
- Decision: The pooled figure is the headline, with mean and median shown.
  Extreme Heat money is reported as following the overall pattern:
  - $240 per resident in the coolest third against $36 in the hottest;
  - 4.5 to 7.4 times after dropping the dominant projects;
  - 2.6 to 3.0 against 0.8 to 0.9 sited heat projects per 100,000 residents.
- Reason:
  - Pooled matches Stage B.
  - The mean is distorted by the 28-person tract.
  - The count measure cannot be driven by one project.
- Evidence: `reports/exposure/heat_tercile_investment.md`;
  `scripts/04_exposure/heat_tercile_investment.py`;
  `outputs/exposure/heat_terciles/`.
- Affects: Interpretation of the heat findings; ML heat scenarios.

---

## Investment measures

### D-045. Investment per person as the primary outcome

- Date: before 17 Sep 2026. Status: Final. Decided by: Amey (not recorded;
  stated as "our primary outcome" in the findings sent to the professor).
- What happened: Total, per person and per km² were all built.
- What is wrong:
  - Totals grow with size.
  - Per km² is close to mechanical with housing density (+0.57 against
    multi-unit housing).
- How we are fixing it: Per person is primary. The others are reported
  alongside.
- Decision: `investment_per_capita` is the primary outcome at tract. It is
  empty, not zero, where population is 0.
- Reason: It measures money relative to the people it serves.
- Evidence: `FINDINGS_FOR_PROFESSOR.md` (4.1, "per person remains our
  primary outcome"); `INVESTMENT_TABLES.md` (columns).
- Affects: All tract volume analyses, Stage B.

### D-046. `investment_any` replaced

- Date: before 16 Sep 2026. Status: Final. Decided by: Amey.
- What happened: County projects reach every populated unit.
- What is wrong: So `investment_any` is 1 everywhere; it has zero variance
  at both grains.
- How we are fixing it: Replace it with two binaries:
  - `investment_any_excl_county`: received any non-county money;
  - `investment_any_single_unit`: has a project sited in the unit.
- Decision: `investment_any` is not used.
- Reason: A constant cannot be analysed.
- Evidence: `correlation_analysis.md` Part 2 (Outcome variables);
  `scripts/common/analysis_variables.py` (`BINARY_OUTCOMES`).
- Affects: All binary outcome analyses.

### D-047. Per-area units and undefined values

- Date: before 12 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Some units have no land or no residents.
- What is wrong: Dividing by zero gives meaningless values, and writing them
  as zero would make it look like no money went there.
- How we are fixing it: Per person and per area are empty where the
  denominator is 0. `investment_per_area` is dollars per m² of TIGER land;
  multiply by 1e6 for $/km².
- Decision: Undefined, not zero.
- Reason: Missing is not zero.
- Evidence: `INVESTMENT_TABLES.md` (columns).
- Affects: Volume outcomes.

### D-048. Single-unit sited investment as the clean outcome

- Date: 20 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Municipal and county money is spread by population. So
  every tract in a city gets the same amount per person from those projects.
- What is wrong: Jurisdiction effects on total investment would partly be
  our own allocation rule.
- How we are fixing it: Repeat key analyses, and run any multilevel model, on
  single-unit investment only: parcel, neighborhood and corridor.
- Decision: Single-unit investment ($6,041,448,104, 70.6% of dollars) is the
  outcome free of the allocation rule.
- Reason: No rule distributed those dollars. The cost is losing 29.4% of
  dollars.
- Evidence: `DATA_PROCESSING.md` section 5 (constraint 3);
  `exposure_vs_investment.md` 3.1.
- Affects: The multilevel model, Stage B, ML location targets.

### D-049. Type shares, and blue flagged as sparse

- Date: before 16 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Investment is split by infrastructure type: gray, green,
  blue and hybrid.
- What is wrong: Blue has 28 projects reaching 19 units with sited blue
  investment, below the 20-unit sparsity line.
- How we are fixing it: Each type share is that type's dollars divided by the
  unit's total investment. Flag any category with fewer than 20 single-unit
  receiving units as sparse, and never read sparse cells as findings.
- Decision: Type shares as defined, with blue flagged as sparse everywhere.
- Reason: Too few blue projects to support a pattern.
- Evidence: `outputs/correlation/part2_univariate/sparsity_baseline.csv`;
  `scripts/common/analysis_variables.py` (`add_type_scale_measures`).
- Affects: Composition analyses, Stage B.

### D-050. Gray split into sub-categories

- Date: 17 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Gray is the largest type and mixes transit, roads,
  drainage, water and sewer, and more.
- What is wrong: A single gray share hides which kind of gray drives a
  result.
- How we are fixing it:
  - Classify gray projects into seven sub-categories by keyword pattern:
    transit, coastal and seawall, drainage and stormwater, road, water and
    sewer, power and communication facilities, other.
  - Projects matching both drainage and road are filed under drainage by
    priority order, and the overlap is disclosed.
  - Each share is a fraction of total investment.
- Decision: The drainage and stormwater share is the gray sub-measure carried
  forward.
- Reason: Drainage alone reproduces the gray pattern.
- Evidence: `gray_decomposition.md`; `scripts/common/gray_classification.py`;
  `scripts/05_analysis/part7_gray_decomposition.py`.
- Affects: Composition analyses, Stage B.

---

## Analysis methods

### D-051. Spearman, not Pearson

- Date: before 16 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Dollar outcomes are heavily right-skewed: |skew| 6 to 37.
- What is wrong: Pearson is driven by a few extreme values. For example,
  no-vehicle against investment per person is Pearson 0.117 but Spearman
  0.333.
- How we are fixing it: Use Spearman rank correlation as the primary
  statistic. Pearson was reported alongside in the early analysis.
- Decision: Spearman throughout.
- Reason: It is robust to skew and to outliers.
- Evidence: `correlation_analysis.md` Part 4; `correlation_screen.md`.
- Affects: Every correlation, the screens, Stage B.

### D-052. Keep every variable through the correlation stage

- Date: before 11 Sep 2026. Status: Final. Decided by: Professor Paharaj.
- What happened: Many indicators overlap: SVI against CRE, and EJScreen
  socioeconomic against ADI.
- What is wrong: Dropping early would hide how correlated everything is.
- How we are fixing it: Keep all variables until the correlation screen, then
  resolve true duplicates.
- Decision: No pre-dropping.
- Reason: The professor wants to see the full correlation structure first.
- Evidence: `DATA_PROCESSING.md` section 3 (EJScreen).
- Affects: The correlation screen, the PCA inputs.

### D-053. Drop one of each pair at |rho| ≥ 0.75

- Date: 27 Sep 2026. Status: Final. Decided by: Professor Paharaj (rule);
  Amey (which variable to drop).
- What happened: The correlation screen compared every pair of indicators.
- What is wrong: Near-duplicate variables would double-weight a concept.
- How we are fixing it: For any pair with |Spearman rho| ≥ 0.75
  (pairwise-complete, compared unrounded), drop one. Amey chooses which, on
  data quality and source consistency, never on results. Anything below 0.75
  is accepted, and both variables are kept.
- Decision: The 0.75 rule, applied to vulnerability indicators (D-026) and
  to the hazard families (D-040).
- Reason: A clear, pre-set line.
- Evidence: `DATA_PROCESSING.md` section 7; `correlation_screen.md`;
  `population_exposure.md` 4.6.
- Affects: The PCA lists, Stage B measures.

### D-054. FDR adjustment within families

- Date: before 16 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Hundreds of correlations are tested.
- What is wrong: Some will pass p < 0.05 by chance.
- How we are fixing it: Benjamini-Hochberg FDR within each defined family of
  tests. Report n, raw p and adjusted p.
- Decision: BH-FDR within families, everywhere.
- Reason: It controls false discoveries without the loss of power of
  Bonferroni.
- Evidence: `correlation_analysis.md` Part 4;
  `scripts/05_analysis/part4_investment_vs_indicators.py`; `exposure_vs_investment.md`
  section 2.
- Affects: Every significance statement.

### D-055. Spatial weights and Moran's I

- Date: before 17 Sep 2026. Status: Final. Decided by: Amey.
- What happened: Nearby tracts are alike.
- What is wrong:
  - Ordinary p-values assume independent units and overstate significance.
  - Moran's I on raw skewed dollars is misleading: investment per person
    gives raw I = 0.006, against 0.495 on ranks.
- How we are fixing it: k = 6 nearest-neighbour weights on centroids in
  EPSG:6346, row-standardised, 999 permutations, on rank-transformed values.
- Decision: Moran's I with k = 6 KNN on ranks. Every report says that
  p-values are not adjusted for space.
- Reason: k = 6 is a standard default, and ranks remove the effect of skew.
- Evidence: `correlation_analysis.md` Part 5;
  `scripts/05_analysis/part5_diagnostics.py`; `scripts/05_analysis/part6b_moran_transforms.py`;
  `followup_analysis.md`.
- Affects: Diagnostics, Stage B section 3.5.

### D-056. Spatial diagnostic gate and core specification

- Date: before 11 Sep 2026. Status: Provisional. Decided by: Amey (not
  recorded).
- What happened: A model of investment against risk and vulnerability is
  planned.
- What is wrong: A spatial model fitted without evidence of clustering adds
  complexity for nothing. Ignoring clustering overstates confidence.
- How we are fixing it:
  - Core specification: `investment ~ risk + vulnerability +
    risk*vulnerability + controls`, reporting simple slopes.
  - Fit OLS first and run Moran's I on its residuals.
  - Move to a spatial model only if the residuals cluster, and then report
    direct and indirect impacts.
  - Check zero-inflation, and consider a hurdle model if needed.
- Decision: As above, not yet fitted.
- Reason: Standard practice.
- Evidence: `DATA_PROCESSING.md` section 6; `REVIEW_MEMO.md` section 5.
- Affects: The modelling stage.

### D-057. Density as a control for composition findings

- Date: 17 Sep 2026. Status: Final. Decided by: Amey.
- What happened: The access and minority composition findings could be urban
  density effects.
- What is wrong: Density is linked to both vulnerability and project type.
- How we are fixing it: Partial Spearman controlling for population density,
  and stratified by density tercile.
  - At block group, housing density from EJScreen ACSTOTHU is also used.
  - At tract, housing density was "not available": no total housing unit
    table was pulled.
  - In prompt 21 it was derived for the heat comparison only, by summing
    block group ACSTOTHU.
- Decision: Population density is the control at both grains, and housing
  density at block group.
- Reason: It tests whether findings survive urban form.
- Evidence: `followup_analysis.md` Task 3; `gray_decomposition.md`;
  `scripts/05_analysis/part6c_density_control.py`; `population_exposure.md` 4.7.
- Affects: Composition findings.

### D-058. PCA method

- Date: 27 Sep 2026. Status: Final (method). Decided by: Amey.
- What happened: The vulnerability indicators were reduced by PCA.
- What is wrong: The results depend on scaling, rotation and the retention
  rule.
- How we are fixing it:
  - Primary run on standardized variables; sensitivity run on ranks.
  - Complete cases only; KMO and Bartlett checks.
  - Eigenvalue above 1, scree and parallel analysis compared side by side.
  - Varimax rotation; the two runs compared by Tucker congruence.
- Decision: As above.
- Reason: The SoVI convention, plus a rank check consistent with the
  Spearman screen.
- Evidence: `pca_analysis.md` (Method).
- Affects: The PCA outputs.

### D-059. Number of PCA components

- Date: 27 Sep 2026. Status: Pending professor. Decided by: Amey (proposal).
- What happened: The retention criteria disagree.
- What is wrong: The choice changes which constructs appear.
- How we are fixing it: Proposed values:

  | Run | Proposed components | Variance explained | What the criteria say |
  |---|---|---|---|
  | Tract, 19 variables | 5 | 67.5% | eigenvalue and parallel analysis agree |
  | Block group, 24 variables | 6 | 58.0% | |
  | Block group, 21 variables | 4 | 50.4% | PC5 sits on the parallel line |

- Decision: Not yet made. The brief framed the question as 4 versus 5
  components; the proposals above are what `pca_analysis.md` reports.
- Reason: The criteria disagree, so the professor decides.
- Evidence: `pca_analysis.md` (Proposals for you to confirm).
- Affects: Any use of component scores.

### D-060. Component scores or representative variables

- Date: 27 Sep 2026. Status: Pending professor. Decided by: not yet.
- What happened: The PCA can feed later analysis as component scores or as
  one representative variable per component.
- What is wrong: Scores are harder to interpret. Single variables lose
  information.
- How we are fixing it: Scores are saved (`outputs/pca/pca_scores_*.csv`) but
  not used anywhere.
- Decision: Not yet made.
- Reason: A professor decision.
- Evidence: `pca_analysis.md` (header).
- Affects: The modelling stage and ML features.

### D-067. Fixed seed for every Moran's I permutation test

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Moran's I p-values and z-scores come from 999 random
  permutations. Rerunning Stage B gave different z-scores each time.
- What is wrong: Results that change on every run cannot be reproduced
  exactly.
- How we are fixing it: Seed numpy's random generator with 12086 before
  every Moran call.
  - `part5_diagnostics.py` and `part6b_moran_transforms.py` already did this.
  - `exposure_vs_investment.py` now does too (`MORAN_SEED`).
  - Seeding per call makes each result independent of call order.
  - esda's `Moran` has no seed argument, so the global seed is set.
- Decision: Every Moran's I in the project uses seed 12086.
- Reason: Reproducibility. Moran's I itself never depended on the seed; only
  the permutation p and z did.
- Evidence:
  - Stage B was run twice after the change, and all ten output files were
    byte-identical.
  - `part5_diagnostics.py` was run twice: identical, and identical to its
    earlier output.
  - Moran's I and p are unchanged from the unseeded run; only z moved, to
    its seeded value.
- Affects: `outputs/exposure/stage_b/morans_i.csv`; any later spatial test.

---

## Project organization

### D-061. Folder reorganized into data, scripts, outputs and reports

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Everything sat at the top of `Modelling Data from Web/`:
  - 11 tables;
  - 17 reports;
  - 49 scripts in one folder;
  - raw data under `tract-level/`, `block-group-level/` and `boundaries/`;
  - every result under `output/`.
- What is wrong: Files were hard to find. Raw downloads, built tables and
  results were mixed. Every script hard-coded its own paths.
- How we are fixing it:
  - The new layout:
    - `data/raw/` (untouched downloads) and `data/processed/` (tables we
      built);
    - `scripts/01_projects` to `05_analysis`, plus `common/`, `website/` and
      `ml/`;
    - `outputs/`, `reports/`, `prompts/` and `archive/`.
  - Every path is defined once in `scripts/common/paths.py`.
  - Tracked files used `git mv`; untracked and ignored files used plain `mv`.
  - Nothing was deleted. Leftover folders that held only Finder `.DS_Store`
    files went to `archive/old_empty_folders/`.
- Decision: As above. `README.md` maps the folder and explains how to rerun
  each step.
- Reason: One place per kind of file, and one place per path.
- Evidence: `REORGANIZATION_PLAN.md`; `README.md`; the checks in D-064.
- Affects: Every script path, every report link, `.gitignore`, and five
  website scripts in `../scripts/python/`.

### D-062. Website scripts moved and proven unchanged (option A)

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (answers to the plan's five questions,
  5 Nov 2026).
- What happened: `build_population_exposure.py` and `build_surge_animation.py`
  write the website's `src/exposure/data/`. They could not move without
  editing their path lines.
- What is wrong: Prompt 21 said not to change `build_population_exposure.py`.
- How we are fixing it:
  - Move both to `scripts/website/` and edit only their path lines: the
    `sys.path` insert, `BASE` one level up, and the surge folder.
  - Prove `build_population_exposure.py` is unchanged: run its real code with
    the output folder redirected to a temporary copy of `src/exposure/data`.
    All seven files (`exposure_blocks.json`, `heat.json`, `heat.png`,
    `slr.json`, `slr.png`, `surge.json`, `surge.png`) came out byte-identical
    to the committed versions, and the committed folder was not touched.
  - `build_surge_animation.py` downloads the project list from Supabase
    whenever it runs, so it was not rerun, because no downloads were allowed.
    Its paths were checked instead: its top level executes and its surge
    rasters resolve.
- Decision: Option A.
- Reason: It keeps one copy of the shared modules, and the byte check shows
  the website is unaffected.
- Evidence: this entry; `README.md` (Website section).
- Affects: `scripts/website/`.

### D-063. What was archived

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Some files are outdated.
- What is wrong: Archiving too much would hide files still in use.
- How we are fixing it: Only `correlation_analysis.md` (superseded) and the
  empty `.Rhistory` went to `archive/`. Other candidates are listed in
  `README.md` and left in place:
  - `reports/analysis/RESULTS_FOR_REVIEW.md` (16 Sep; predates the
    correlation screen and the PCA);
  - `followup_analysis.md` and `gray_decomposition.md`, whose findings are
    folded into `FINDINGS_FOR_PROFESSOR.md`;
  - `REORGANIZATION_PLAN.md`, now carried out.
- Decision: Archive only the two files for now.
- Reason: Amey's answer to the plan (5 Nov 2026): archive only these for now.
- Evidence: `archive/`; `README.md`.
- Affects: Nothing that runs.

### D-064. Git status kept as it was; checks after the move

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Raw data (9.6 GB) and `output/` were git-ignored. A move
  could have exposed them.
- What is wrong: Untracked raw data could be committed by accident.
- How we are fixing it:
  1. `.gitignore` was updated first. New lines ignore `data/raw/boundaries`,
     `social`, `physical`, `outputs/`, and the files that left `output/` (the
     allocation audits, the join keys, the variable dictionary). The old
     lines are kept too.
  2. Tracked files stay tracked; the exposure tables stay untracked and not
     ignored.
  3. `git status` was taken before and after.
- Decision: Every file keeps the git status it had. No raw data file became
  tracked.
- Reason: Amey's answer to the plan (5 Nov 2026).
- Evidence of the checks after the move:
  - All 424 files have the same SHA-256 before and after (the folder total
    is unchanged).
  - Every path in `paths.py` exists.
  - Every script imports and runs its top level with a clean `sys.path`.
  - The loaders give 698 tracts, 1,843 block groups and 25,805 blocks with
    2,738,356 residents.
  - Two reruns match the earlier outputs: `part6b_moran_transforms.py`
    identically, and Stage B identically except the random Moran permutation
    z-scores.
  - `npm run build` passes.
- Affects: `.gitignore`.

### D-065. Published strings left unchanged

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: `public/layers/storm-surge-category-3.json`,
  `public/layers/surface-metadata.json` and the `src/admin/viz/gapMap.js`
  label name old paths.
- What is wrong: The text is now out of date.
- How we are fixing it: Leave them as they are. They record where the source
  was when each layer was built; no code reads them as paths.
- Decision: Unchanged.
- Reason: No changes to the website's published outputs.
- Evidence: `REORGANIZATION_PLAN.md` 3.4.
- Affects: Nothing.

### D-066. Two website helper scripts are git-ignored

- Date: 5 Nov 2026. Status: Replaced by D-068. Decided by: Amey.
- What happened: `../scripts/python/build_lst_layer.py` and
  `build_hhi_layer.py` are covered by the repo's `scripts/python/*` ignore
  rule.
- What is wrong: Their boundary-path fix (`build_lst_layer.py`, line 53) is
  local only and will not appear in a commit.
- How we are fixing it: Record it here. If those scripts should be shared,
  un-ignore them in a separate change.
- Decision: Edited locally, and flagged.
- Reason: Changing what the repo ignores is outside this task.
- Evidence: `git check-ignore -v scripts/python/build_lst_layer.py`.
- Affects: Anyone rebuilding the heat layer from another clone.

### D-068. Track the heat layer scripts in git

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: `../scripts/python/build_lst_layer.py` builds the Landsat
  surface temperature composite that all heat exposure depends on.
  `build_hhi_layer.py` builds the CDC Heat & Health Index layer and imports
  from it. Both were git-ignored by the repo's `scripts/python/*` rule
  (D-066).
- What is wrong: The heat data could not be rebuilt from a fresh clone, and
  the boundary-path fix from the reorganization was local only.
- How we are fixing it: Add `.gitignore` exceptions
  (`!scripts/python/build_lst_layer.py`, `!scripts/python/build_hhi_layer.py`)
  and stage both files. They are not committed yet.
- Decision: Both scripts are tracked.
- Reason: Analysis inputs should be reproducible from the repository.
- Evidence: `.gitignore` (lines 33 to 35); `git status` shows both as added.
  `build_lst_layer.py`'s install line names `scripts/python/requirements.txt`;
  D-070 tracks it as well.
- Affects: `.gitignore`; replaces D-066.

### D-070. Track the heat layer requirements file

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: `build_lst_layer.py` says to install its dependencies from
  `scripts/python/requirements.txt`. That file was still git-ignored after
  D-068.
- What is wrong: A fresh clone would have the heat layer script but not its
  dependency list, so the heat layer could not be rebuilt as documented.
- How we are fixing it: Add `!scripts/python/requirements.txt` to
  `.gitignore`, next to the two script exceptions.
- Decision: The requirements file is tracked.
- Reason: The heat data the exposure analysis depends on should be
  rebuildable from the repository.
- Evidence: `.gitignore`; the file lists numpy, rasterio, pystac-client,
  planetary-computer and pyshp for `build_lst_layer.py`. It has minimum
  versions, not pinned ones. It holds no secrets.
- Affects: `.gitignore`.

---

## Machine learning

Entries will be added here as prompt 22
(`prompts/claude_code_prompt_22_ml_scenario_module.md`) runs, numbered
from D-071. Choices already fixed by earlier entries that the ML work must
respect:
- the training statuses (D-002);
- the 698-tract frame (D-007);
- single-unit location targets (D-048);
- the hazard scenarios (D-031, D-036, D-041).

### D-071. Gradient boosting packages are not installed

- Date: 5 Nov 2026. Status: Replaced by D-079. Decided by: Amey.
- What happened: Prompt 22 asks for LightGBM, XGBoost and SHAP. None is
  installed in the repo's `.venv` or in any other Python environment on this
  machine.
- What is wrong: Installing them means downloading, which the prompt rules
  out without approval. Stage 2 cannot start as written.
- How we are fixing it: Stage 1 uses scikit-learn only (installed, 1.9.1).
  Two options for Stage 2:
  - install the three packages, which needs your approval;
  - use scikit-learn's `HistGradientBoostingClassifier`, which supports
    monotone constraints, with permutation importance and partial dependence
    in place of SHAP.
- Decision: Not yet made.
- Reason: No downloads without approval.
- Evidence: `scripts/ml/requirements.txt` (pinned versions, the three
  packages listed as not installed); `reports/ml/stage1_report.md` section 5.
- Affects: Stage 2 models, explanations and the scenario engine.

### D-072. ML training frame: 697 tracts

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 says to exclude the 10 tracts under 100 residents
  from training.
- What is wrong: Nine of those ten have no residents and are already outside
  the 698-tract frame (D-007). Only one tract in the frame is under 100:
  Pennsuco, 12086981100, with 28 residents.
- How we are fixing it: Train and evaluate on the other 697 tracts. Keep
  Pennsuco in the modelling table and the outputs, flagged by
  `low_pop_flag`.
- Decision: 697 training tracts.
- Reason: The prompt's rule, applied to the frame.
- Evidence: `outputs/ml/stage1/model_table_tract.csv`; target counts in
  `reports/ml/stage1_report.md`.
- Affects: All ML targets.

### D-073. Context features under the 0.75 rule; hazard pairs kept

- Date: 5 Nov 2026. Status: Provisional (confirm). Decided by: Amey.
- What happened: Six pairs among the main features reach |Spearman rho| ≥
  0.75 on the 697 training tracts:
  - population density vs housing density, +0.94;
  - housing density vs land area, −0.87;
  - population density vs land area, −0.86;
  - heat population-weighted mean vs heat 95th percentile share, +0.95;
  - surge Category 3 any vs Category 3 more than 3 ft, +0.92;
  - surge Category 3 vs Category 4, +0.82.
- What is wrong: Near-duplicate features double-weight a concept and split
  explanation credit.
- How we are fixing it:
  - Keep population density, the established control (D-057), and leave
    housing density and land area out of the main set. They stay in the table
    and the dictionary.
  - Keep the three hazard pairs, because prompt 22 names that hazard set
    explicitly.
- Decision: The main set has 30 features. The three hazard pairs are kept
  and flagged.
- Reason: The 0.75 rule (D-053) for the context features; the prompt's
  explicit list for the hazard features.
- Evidence: `outputs/ml/stage1/feature_screen_pairs.csv`;
  `reports/ml/stage1_report.md` section 2.
- Affects: ML features, Stage 2 explanations.

### D-074. Fixed log transform for skewed features

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The first T5 ridge baseline gave R² −19 under spatial CV.
- What is wrong: Raw, very skewed features (land area, densities, FEMA loss
  per person, distance) produced extreme predictions in folds that held
  unusual tracts, such as the large Everglades tracts.
- How we are fixing it: Apply log1p to population density, housing density,
  land area, distance to the coast and the two FEMA loss features. It is a
  fixed elementwise transform with nothing fitted, so it cannot leak across
  folds.
- Decision: log1p for those six features in every model.
- Reason: It is standard for skewed positive quantities. After it, ridge
  under spatial CV gives R² 0.22.
- Evidence: `scripts/ml/stage1_build.py` (`LOG1P`); `outputs/ml/stage1/baselines_T5.csv`.
- Affects: All ML models.

### D-075. Validation design for the ML module

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Neighbouring tracts are alike (Moran's I 0.62 to 0.88 for
  exposure), so random folds overstate accuracy.
- What is wrong: A single random cross-validation would report optimistic
  scores.
- How we are fixing it:
  - **Primary:** 10 spatial folds from k-means of tract representative
    points, seed 12086.
  - **Also reported:** 10 stratified random folds, to show the gap, and
    leave one jurisdiction out (33 groups).
  - **Tuning:** hyperparameters chosen by an inner grouped CV on the training
    folds only (nested). Imputation, scaling and PCA are fitted inside each
    training fold.
  - **Scores:** ROC-AUC, PR-AUC, log loss and Brier, pooled. ROC-AUC and
    PR-AUC are also averaged over folds, because pooling folds with different
    base rates distorts a constant predictor's ranking scores.
- Decision: As above, for every ML target.
- Reason: Prompt 22's rules, plus the pooling problem found in Stage 1.
- Evidence: `outputs/ml/stage1/spatial_folds.csv` and
  `spatial_fold_assignment.csv`; `reports/ml/stage1_report.md` section 4.
- Affects: All ML scores.

### D-076. Definitions of the new ML features

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 asks for FEMA loss per person and per building
  value, distance to the coast, and a heat land measure for the comparison
  model.
- What is wrong: None of these existed. There is no coastline file, and FEMA
  population is zero in 6 tracts (none of them in the frame).
- How we are fixing it:
  - `nri_eal_per_person` = `EAL_VALT` ÷ NRI `POPULATION` (NA where 0).
  - `nri_ealb_per_building_value` = `EAL_VALB` ÷ `BUILDVALUE`.
  - `dist_coast_km` = distance from each tract's representative point to the
    union of TIGER marine water polygons: MTFCC H2051 (bay, estuary, sound)
    and H2053 (ocean), that is Biscayne Bay, the Atlantic, and Card, Barnes
    and Little Card Sound.
  - `heat_land_mean_f` = land-area-weighted mean of the Landsat block group
    means, comparison model only.
  - `in_municipality` = 1 if the tract centroid is in an incorporated place.
  - A named empty slot for FEMA flood zones.
- Decision: As above.
- Reason: The closest available measure to each requested feature, built
  only from data already on disk.
- Evidence: `scripts/ml/stage1_build.py`; `outputs/ml/stage1/feature_dictionary.csv`.
- Affects: ML features.

### D-077. ML target definitions

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 defines five targets.
- What is wrong: Three need interpretation against the data.
- How we are fixing it:
  - **T1:** any sited (parcel, neighborhood, corridor) completed, funded or
    ongoing project in the tract. It matches `investment_any_single_unit`
    exactly.
  - **T2:** any Planned sited project in the tract. 217 projects in total,
    201 in 108 frame tracts. Scored with spatial out-of-fold T1 predictions,
    never trained on.
  - **T3:** trained on "first sited project's `Reported_Year` ≤ 2023". Tested
    on tracts with none by 2023, where the positives are tracts whose first
    project falls in 2024 to 2026. `Reported_Year` is a document year, and
    399 sited projects carry 2020.
  - **T4:** gray (919) against green, blue and hybrid together (180) at
    project level. Blue has 18 projects in scope; the prompt's 36 counts
    every status. Features are the tract's features plus scale and hazard
    focus. Hazard focus is a project attribute decided alongside type, so it
    describes projects but would not be known for an unproposed one.
  - **T5:** log(sited dollars ÷ residents) for the 395 tracts with a sited
    project.
- Decision: As above.
- Reason: Faithful to the prompt, and to the data as it is.
- Evidence: `outputs/ml/stage1/target_counts.csv`; `reports/ml/stage1_report.md`
  section 3.
- Affects: All ML results.

### D-078. Where ML reports live

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 asks for reports in `output/ml/`.
- What is wrong: Since the reorganization (D-061), results live in
  `outputs/`, which is git-ignored, and reports live in `reports/`.
- How we are fixing it: Machine-readable results go to `outputs/ml/`
  (`paths.OUT_ML`). Written reports go to `reports/ml/`, so they are tracked.
- Decision: As above.
- Reason: It follows the folder layout and keeps reports under version
  control.
- Evidence: `reports/ml/stage1_report.md`.
- Affects: All ML reports, including the model card.

### D-079. Dedicated ML environment

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Amey approved installing LightGBM, XGBoost, SHAP and TabPFN
  for Stage 2 (replaces D-071).
- What is wrong: The LightGBM and XGBoost wheels need the OpenMP runtime
  (`libomp`), which is not installed on this machine.
- How we are fixing it:
  - Create `scripts/ml/.venv-ml` with uv. It is ignored by git through its
    own `.gitignore`.
  - Install the pinned packages: lightgbm 4.7.0, xgboost 3.4.1, shap 0.54.1,
    tabpfn 9.2.0, torch 2.15.0, plus the Stage 1 set.
  - Run every ML script through `scripts/ml/run_ml.sh`. It points the loader
    at the `libomp` bundled with PyTorch, so all three libraries share one
    OpenMP runtime and nothing is installed system-wide.
- Decision: As above.
- Reason: It keeps the ML stack apart from the analysis `.venv` and needs no
  system change.
- Evidence: `scripts/ml/requirements.txt`, `requirements-lock.txt` (the full
  freeze), `run_ml.sh`.
- Affects: All Stage 2 and later ML scripts.

### D-080. One hazard feature per family in the main model

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Stage 1 kept three hazard pairs above the 0.75 line
  (D-073).
- What is wrong: Near-duplicate hazard features split explanation credit and
  make scenario changes ambiguous.
- How we are fixing it: Apply the 0.75 rule to the hazard features.
  - **Main model:** `slr_3ft_pop_share`, `surge_cat3_any_pop_share`,
    `heat_lst_popwt_mean_f`.
  - **Sensitivity model:** adds the three dropped versions,
    `heat_p95_pop_share`, `surge_cat3_over3ft_pop_share` and
    `surge_cat4_any_pop_share`.
  - **Scenario engine:** a scenario replaces the value of the one feature in
    its family. For example, surge Category 4 shares go into the surge
    feature.
- Decision: The main model has 27 features: 19 social, 3 hazard, 2 FEMA loss
  and 3 context.
- Reason: Amey's instruction, and the project's 0.75 rule (D-053).
- Evidence: this entry; `reports/ml/stage2_report.md`.
- Affects: Stage 2 models, the scenario engine, SHAP.

### D-081. T3 is a diagnostic only

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: T3 (the temporal check) scored ROC-AUC 0.57 in Stage 1.
- What is wrong: `Reported_Year` is the year of the source document, not the
  build year, and 399 sited projects carry 2020. So T3 does not measure "new
  investment" reliably.
- How we are fixing it: Report T3, flagged as limited, and never use it for
  claims. T2 (planned projects) is the main future check.
- Decision: As above.
- Reason: The label cannot support a claim.
- Evidence: `reports/ml/stage1_report.md` section 3.
- Affects: Stage 2 reporting and the model card.

### D-082. TabPFN as a challenger model

- Date: 5 Nov 2026. Status: Provisional (blocked on a license key). Decided
  by: Amey.
- What happened: Amey asked to add TabPFN (Hollmann et al., Nature 2025) as a
  challenger for T1 and T4, with the same nested spatial CV. LightGBM or
  XGBoost stays the scenario model, because of the monotone constraints and
  SHAP. If TabPFN clearly wins on spatial CV, it drives the prediction map.
- What is wrong: tabpfn 9.2.0 installs, but its model weights need a one-time
  license acceptance on Prior Labs' site (account, then an API key in
  `TABPFN_TOKEN`). Creating accounts, accepting licenses and handling API
  keys are for Amey to do.
- How we are fixing it: The Stage 2 script runs TabPFN only when
  `TABPFN_TOKEN` is set in the environment, and otherwise records "not run
  (no license key)" in the results table. The model card notes the license:
  the Prior Labs License, Apache 2.0 with an attribution requirement.
- Decision: Built in; runs once Amey sets the key.
- Reason: No account or credential handling by the assistant.
- Evidence: `scripts/ml/stage2_models.py`; `scripts/ml/requirements.txt`.
- Affects: The T1 and T4 comparison tables, and the choice of prediction map.

### D-083. Conformal uncertainty intervals

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Amey asked for conformal prediction (split or
  cross-conformal, inside the spatial folds) for per-tract intervals, with
  achieved coverage reported.
- What is wrong: A binary target gives a probability, not a value with an
  error. A plain conformal interval does not apply directly.
- How we are fixing it: Every method below is fitted inside each outer
  spatial fold. One training fold is held out as the calibration set; the
  model is fitted on the rest and applied to the test fold.
  - **T1 likelihood:** an inductive Venn-ABERS interval [p0, p1] for each
    tract. This is a conformal-family method that gives a calibrated
    probability interval. It comes with conformal prediction sets at 90%,
    whose achieved coverage is reported.
  - **T5 amount:** split conformal intervals (absolute-residual
    nonconformity) at 90%, with achieved coverage.
- Decision: As above.
- Reason: Conformal methods give distribution-free coverage. Venn-ABERS is
  the conformal answer for probabilities.
- Evidence: `scripts/ml/stage2_models.py`; `reports/ml/stage2_report.md`.
- Affects: Dashboard intervals, the model card.

### D-084. Heat scenarios are illustrative shifts

- Date: 5 Nov 2026. Status: Final (confirmed and extended by D-093). Decided by: Amey.
- What happened: Prompt 22 lists heat scenarios at the 75th and 95th
  percentile. After D-080, the model's one heat feature is the
  population-weighted mean surface temperature.
- What is wrong: A threshold scenario has no meaning for a mean, and no
  projected heat layer exists. The 75th percentile is also not used (D-036).
- How we are fixing it: The scenario engine offers "current" plus
  ILLUSTRATIVE uniform warming of +1, +2 and +3°F on the mean. These are
  labelled hypothetical everywhere and are not projections. Tracts pushed
  above the training range are flagged as extrapolation.
- Decision: As above.
- Reason: It keeps one feature per family (D-080), and is honest that no heat
  projection exists.
- Evidence: `scripts/ml/scenarios.py`.
- Affects: The scenario engine and the dashboard heat control.

### D-085. Need and gap

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 asks for a transparent need score, kept separate
  from the model, and a gap between need and predicted investment.
- What is wrong: The hazard measures are on different scales: two shares and
  a temperature.
- How we are fixing it:
  - **exposure index** = mean of the percentile ranks of the three primary
    hazard features: SLR 3 ft share, surge Category 3 share, heat mean.
  - **vulnerability** = PCA component RC1, "general socioeconomic
    disadvantage", oriented so that higher means more poverty.
  - **need** = exposure percentile × vulnerability percentile, then ranked.
  - **gap** = need percentile minus predicted-likelihood percentile. Positive
    means more need than the model expects investment.
  - Under a scenario, values are ranked against the current distribution, so
    more hazard raises need.
- Decision: As above. The one tract without SVI values has no need score.
- Reason: Simple, explainable, and independent of the model.
- Evidence: `scripts/ml/stage2_models.py` (section 8); `scenarios.py`.
- Affects: The dashboard need and gap layers, `interventions.py`.

### D-086. Model choice rule, and the monotone scenario model

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Several models compete for T1.
- What is wrong: Picking whichever looks best after the fact invites
  fishing.
- How we are fixing it: The rule was fixed before seeing the scores:
  - The **map model** is the tree model (LightGBM or XGBoost) with the
    higher spatial PR-AUC; ties go to lower log loss. (The map model was
    later changed to logistic regression by D-091.)
  - TabPFN replaces it on the map only if it beats it by at least 0.02 in
    both spatial ROC-AUC and PR-AUC.
  - The **scenario model** is the same tree family with monotone increasing
    constraints on the three hazard features. Its accuracy cost is reported.
  - Hyperparameters for the final fits are the values chosen most often
    across the outer spatial folds.
- Decision: As above.
- Reason: A choice set in advance. Monotone constraints keep scenarios
  plausible: more hazard never lowers predicted need.
- Evidence: `outputs/ml/stage2/model_choice.json`; `reports/ml/stage2_report.md`.
- Affects: The dashboard map and the scenarios.

### D-087. What the dashboard shows as a tract's prediction

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: A model fitted on all tracts and then used to predict those
  same tracts looks better than it is.
- What is wrong: In-sample predictions overstate how well the model knows a
  tract.
- How we are fixing it: Each training tract's prediction is its spatial
  out-of-fold prediction, calibrated with Venn-ABERS, and the interval is
  [p0, p1] (D-083). The one tract under 100 residents, not in training, gets
  the final-fit prediction and is flagged.
  - Scenario values come from the final monotone model, shown as the change
    from that model's own current prediction.
- Decision: As above.
- Reason: Honest, out-of-sample numbers on the map.
- Evidence: `outputs/ml/stage2/tract_predictions.csv`; `outputs/ml/dashboard/`.
- Affects: The dashboard.

### D-088. T5 is reported but unreliable, and has no dashboard numbers

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: T5 (log sited dollars per resident) is weak: best spatial
  R² 0.23 (ridge). Its split conformal 90% intervals hit 91.7% coverage, but
  average 6.5 log units wide, a factor of about 650 between the bottom and
  top of a typical interval.
- What is wrong: Intervals that wide make dollar predictions meaningless for
  any single tract.
- How we are fixing it: T5 stays in the reports, flagged as unreliable. No
  dollar prediction appears on the dashboard; `tracts.json` and
  `scores.json` carry no T5 field.
- Decision: As above.
- Reason: Do not show numbers that cannot be trusted.
- Evidence: `outputs/ml/stage2/results_T5.csv`, `results_conformal.csv`;
  `reports/ml/stage2_report.md`.
- Affects: The dashboard and the model card.

### D-089. Tree models do not beat logistic regression on T1

- Date: 5 Nov 2026. Status: Replaced by D-091. Decided by: Amey.
- What happened: Under spatial CV, T1 logistic regression scored ROC-AUC
  0.675 and PR-AUC 0.719. XGBoost scored 0.660 and 0.714, and LightGBM 0.644
  and 0.712. Under random CV they are about equal.
- What is wrong: Prompt 22 says a complex model is only worth using if it
  clearly beats the baselines. It does not. The map currently uses XGBoost
  (D-086).
- How we are fixing it: Results are reported as they are. Two options:
  - put the logistic out-of-fold predictions on the map, keeping monotone
    XGBoost for scenarios (its monotone constraint costs nothing: 0.660
    either way);
  - keep XGBoost on the map for its SHAP drivers. Logistic coefficients
    could give drivers instead.
- Decision: Not yet made. The map stays on XGBoost until Amey decides.
- Reason: The prompt's own rule.
- Evidence: `outputs/ml/stage2/results_binary.csv`; `reports/ml/stage2_report.md`.
- Affects: Dashboard predictions and drivers.

### D-090. Hazard exposure barely drives where projects were sited

- Date: 5 Nov 2026. Status: Final (finding). Decided by: Amey.
- What happened: SHAP ranks the three hazard features 13th (surge), 18th
  (heat) and 20th (sea level rise) of 27. Distance to the coast and
  population density dominate. In partial dependence, the full range of each
  hazard moves the average prediction by 0.02 or less.
- What is wrong: The scenario engine changes only hazard features, so the
  scenarios barely move predicted likelihood: at most +0.01 on average (Cat 5
  surge). Heat moves nothing, because past investment fell with heat and the
  monotone constraint flattens that to zero.
- How we are fixing it: Report this plainly. The scenarios say "under current
  patterns, more hazard would hardly change where projects go". The need and
  gap layers, which respond directly to exposure, carry the scenario story.
  For example, tracts with a gap of 0.5 or more rise from 87 now to 97 at Cat
  5 surge and 94 at 6 ft.
- Decision: As above.
- Reason: It is what the data show, and it is itself a finding about past
  investment.
- Evidence: `outputs/ml/stage2/shap_global.csv`, `partial_dependence.csv`,
  `scenario_summary.csv`.
- Affects: How the scenarios are presented, on the dashboard and in the model
  card.

### D-091. Map model: logistic regression

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (rule); the result
  applied it.
- What happened: Logistic regression scored slightly above XGBoost on T1
  under spatial CV (D-089). Amey asked for a significance test, plus an
  average of the two and TabPFN as candidates.
- What is wrong: A difference of 0.015 ROC-AUC on 697 tracts may be noise.
- How we are fixing it:
  - A paired bootstrap of the spatial out-of-fold predictions: 2,000
    resamples of tracts, seed 12086, 95% intervals.

    | Comparison | ROC-AUC difference [95%] | PR-AUC difference [95%] | Log loss difference [95%] |
    |---|---|---|---|
    | Logistic minus XGBoost | +0.016 [−0.010, +0.042] | +0.005 [−0.028, +0.039] | +0.002 [−0.021, +0.027] |
    | Average minus logistic | −0.002 [−0.016, +0.011] | +0.010 [−0.010, +0.027] | −0.012 [−0.028, +0.001] |

  - The average scores best on spatial PR-AUC (0.729), but it is not
    reliably better than logistic regression.
  - TabPFN was not run: no `TABPFN_TOKEN` (D-082).
- Decision: Logistic regression drives the map. Each tract's prediction is
  its spatial out-of-fold probability with a Venn-ABERS interval: coverage of
  the 90% sets is 89.2%, and the average interval width 0.21. Drivers are the
  per-tract log-odds contributions (coefficient × standardized value).
  Monotone XGBoost stays the scenario model.
- Reason: Amey's rule: with no real difference, use the simpler and more
  transparent model.
- Evidence: `outputs/ml/stage2/map_model_scores.csv`, `map_model_test.csv`;
  `scripts/ml/stage2b_map_model.py`.
- Affects: The dashboard map, intervals and drivers.

### D-092. Primary gap is need versus actual investment

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The Stage 2 gap compared need with the model's expected
  likelihood. Two of the three highest-gap tracts already had a sited
  project.
- What is wrong: A gap against expected investment is hard to read as
  "underserved".
- How we are fixing it:
  - **Primary gap** = need percentile minus the percentile of actual sited
    dollars per resident. Tracts with no sited project share the bottom rank.
  - **Flag:** high need (top quarter, need percentile ≥ 0.75) with no sited
    project.
  - **Secondary layer**, labelled "need versus expected investment" = need
    percentile minus predicted-likelihood percentile.
  - `interventions.py` and the dashboard export use both. A funded tract
    gets an assumed sited amount per resident, by default the county median
    among tracts with a sited project ($580 per resident). The high-need flag
    is cleared for funded tracts.
- Decision: As above.
- Reason: Amey's instruction. The actual gap reads directly as underserved.
- Evidence:
  - Need and actual sited dollars per resident are unrelated (Spearman
    +0.02).
  - 85 tracts have a primary gap of 0.5 or more.
  - **72 tracts (275,141 residents) have high need and no sited project:**
    Hialeah 21, Miami 19, Unincorporated 18, Miami Beach 8.
  - `tracts.json` carries observed sited dollars per resident (not a
    prediction) so the dashboard can recompute the gap.
- Affects: The dashboard layers, the scenarios and interventions.

### D-093. Heat scenarios change need and the gap only

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Under the monotone constraint, the scenario model gives heat
  no effect (D-090). Past investment fell, if anything, with heat.
- What is wrong: Feeding heat scenarios to the model would show "no change"
  and could be misread.
- How we are fixing it:
  - Heat scenarios (+1, +2, +3°F illustrative uniform warming, D-084) are not
    passed to the model. Predicted likelihood stays at its current value, and
    only need and the gaps change.
  - The dashboard states: "Heat scenarios change need and the gap only. They
    do not change predicted investment, because past investment did not
    follow heat."
  - High-need tracts with no sited project rise from 72 now to 93 (+1°F), 104
    (+2°F) and 112 (+3°F).
- Decision: As above.
- Reason: Amey's instruction. It keeps the dashboard honest about what the
  model can say.
- Evidence: `scripts/ml/scenarios.py`; `outputs/ml/stage2/scenario_summary.csv`.
- Affects: The dashboard heat control.

### D-094. The Scenario dashboard lives in the admin panel only

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 22 Stage 3 asked for a public Scenario page. Partway
  through, Amey changed the plan: the Scenario dashboard must be in the admin
  panel only.
- What is wrong: A public page would show preliminary, unreviewed model
  results to everyone.
- How we are fixing it:
  - **Public changes undone:**
    - `src/App.jsx` (lazy import, `/scenario` route, route metadata,
      full-window class) and `src/components/Navbar.jsx` (the "Scenarios"
      link) were restored to their committed versions with `git checkout`;
    - `src/pages/Scenario.jsx` was removed;
    - `src/scenario/` was moved into the admin panel.

    Nothing else on the public site was touched.
  - **The view now lives at** `src/admin/viz/scenario/` (markup, script,
    styles, data). It is served at `/admin/viz/scenario` through the
    existing `VizPage`, behind `RequireAdmin`, with a "Scenarios
    (preliminary)" link in the admin navigation.
  - **Data:** `scripts/website/build_scenario_data.py` writes to
    `src/admin/viz/scenario/data/`.
- Decision: As above.
- Reason: Amey's instruction. It matches how the existing draft
  visualizations (the resilience gap map) are kept off the public site.
- Evidence:
  - The public source files are identical to HEAD.
  - A production build compared with the pre-Stage-3 build, with the same
    env files, gives public chunks (`index`, `Team`, `TechnicalDocs`,
    `dataParser.core`, `index.html`) of the same size and content. Only
    content hashes and minified names differ, because the admin chunk
    changed.
  - Scenario code and data URLs appear only in the admin `VizPage` and
    `AdminApp` chunks.
  - A logged-out visit to `/admin/viz/scenario` redirects to the login and
    requests no Scenario data.
  - New tests (`src/admin/viz/scenarioAccess.test.jsx`) cover signed-out,
    non-admin and admin access.
- Affects: The website, the admin panel, the build script.

### D-095. The admin view's data files are still public static files

- Date: 5 Nov 2026. Status: Approved, deferred (see D-096). Decided by: Amey.
- What happened: The build emits the Scenario data as hashed static assets
  (`dist/assets/scenarios-*.json`, `tracts-*.geojson`). Only the admin chunks
  reference them.
- What is wrong: A logged-out visitor cannot reach the view, and nothing
  public links to the data. But anyone who reads the admin JavaScript chunk
  (itself a public static file) can find the hashed URLs and fetch the files
  directly. The existing gap map's data has the same exposure. Login does
  not protect static assets on Vercel.
- How we are fixing it: Not yet. The robust fix serves the files from a
  private Supabase Storage bucket readable only by admins, checked with the
  existing `is_admin()`, and has the view fetch them with the admin's
  session. That needs a new bucket, access policies and an upload step, so
  it waits for Amey's approval.
- Decision: Not yet made.
- Reason: Being clear about what the login protects and what it does not.
- Evidence: `dist/assets/` after `npm run build`; `reports/ml/stage3_report.md`.
- Affects: The admin Scenario view, and the existing gap map's data.

### D-096. Private admin data fix approved but deferred; no push or deploy until done

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Amey approved the D-095 fix, as planned in
  `docs/PRIVATE_ADMIN_DATA_PLAN.md`: a private Supabase bucket
  `admin-data`, read by admins only via `public.is_admin()`. Amey then put it
  on hold.
- What is wrong: Until the fix is done, the admin data would be exposed:
  - any push would put the Scenario data (local commit `a32dbdf`) on the
    public GitHub repository;
  - any deploy would publish the Scenario data as static files.
- How we are fixing it: The plan stays as written. Nothing is done yet:
  - no bucket is created;
  - nothing is uploaded;
  - no policy is changed;
  - commit `a32dbdf` is not rewritten.
- Decision: **Nothing may be pushed or deployed until the D-095 fix is done.**
  That covers every branch, including `data-prep-exposure` and
  `ml-scenario-module`.
- Reason: Amey's instruction. It keeps the unpushed Scenario data private
  while the fix waits.
- Evidence: `docs/PRIVATE_ADMIN_DATA_PLAN.md`; `git log` (`a32dbdf` is local
  only).
- Affects: All pushes and deploys from this repository.

### D-097. Software for the Bayesian multiscale model: NumPyro

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 24 asked for R with R-INLA first, then PyMC or
  NumPyro.
  - R 4.5.2 is installed, but without INLA or the R spatial packages.
  - The ML environment had no PyMC or NumPyro.
- What is wrong: Every option needed an install.
- How we are fixing it: Amey chose NumPyro and ArviZ in `scripts/ml/.venv-ml`
  (numpyro 0.22.0, jax 0.12.0.1, arviz 1.3.0), pinned in
  `scripts/ml/requirements.txt`. No existing package changed version. Models
  are fitted by NUTS MCMC, with the ICAR and BYM2 terms written explicitly.
- Decision: NumPyro. No R or system install.
- Reason:
  - It gives the required MCMC checks (R-hat, ESS, divergences) and LOO
    directly.
  - It uses one environment.
  - INLA would still have needed an MCMC cross-check in another tool.
- Evidence: `scripts/ml/requirements-lock.txt`.
- Affects: Stage 4.

### D-098. Tract adjacency graph for the spatial effects

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: BYM2 needs a connected graph of the 697 training tracts.
- What is wrong: Queen contiguity on the TIGER 2024 tract polygons
  (EPSG:6346) gives 2,221 links in 2 components. The main component has 693
  tracts. Key Biscayne's 4 tracts touch no other tract. No tract is left
  without any neighbour.
- How we are fixing it: Join each smaller component to the nearest tract
  outside it, by the shortest distance between polygons. One link was added:
  12086004602 (Key Biscayne) to 12086006802 (Miami), 4,113 m. Miami Beach and
  Fisher Island are already connected, because TIGER tract outlines include
  water.
- Decision: The graph has 2,222 links and 1 component. Every tract has at
  least 2 neighbours, and the mean is 6.4. The BYM2 scaling factor is 0.412.
- Reason: The prompt's rule. Nearest-distance joins add the fewest
  artificial links.
- Evidence: `outputs/ml/stage4/graph_summary.json`, `graph_added_links.csv`;
  `scripts/ml/stage4_graph.py`.
- Affects: All Stage 4 spatial effects.

### D-099. Missing SVI values in one tract for the Bayesian models

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (proposal; confirm).
- What happened: Tract 12086008904 has no value for 8 SVI percentage
  variables, and so no PCA vulnerability score (RC1).
- What is wrong: NUTS needs a complete design matrix. The Stage 2 models
  handled the gap inside their own pipelines.
- How we are fixing it: Fill the 8 values and RC1 with the training-frame
  median, for the Stage 4 models only. The source tables are not changed.
- Decision: Median imputation for this one tract, listed in
  `outputs/ml/stage4/run_meta.json`.
- Reason: One tract of 697. Its effect on any coefficient is negligible, and
  the tract keeps its place in the spatial graph.
- Evidence: `scripts/ml/stage4_models.py` (`load_data`).
- Affects: Stage 4 only.

### D-100. Priors for the Bayesian multiscale models

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (rule from prompt 24);
  the values are proposals.
- What happened: Prompt 24 set the prior families. The values had to be
  chosen.
- What is wrong: Nothing. This records the values.
- How we are fixing it: Not applicable.
- Decision:
  - Part 1 (logit scale):
    - standardized coefficients Normal(0, 1);
    - intercept Normal(0, 2.5);
    - jurisdiction SD and BYM2 SD with PC (exponential) priors,
      P(SD > 1) = 0.05;
    - BYM2 mixing parameter with a PC prior, P(rho < 0.5) = 2/3 (the INLA
      default), computed from this graph's eigenvalues;
    - Model 2 slope SDs as for the other SDs.
  - Part 2 (log dollars):
    - same coefficient prior;
    - intercept centred on the mean log dollars per resident, SD 2.5;
    - SDs with P(SD > 2) = 0.05;
    - Gamma shape Exponential(1);
    - lognormal SD HalfNormal(2.5).
  - Sensitivity: narrow (coefficients Normal(0, 0.5), P(SD > 0.5) = 0.05) and
    wide (Normal(0, 2.5), P(SD > 2) = 0.05).
- Reason: Weakly informative on the scales the predictors are on. The PC
  priors shrink towards the simpler model without the random effect.
- Evidence: `scripts/ml/stage4_models.py` (`PRIORS`),
  `outputs/ml/stage4/prior_predictive.csv`.
- Affects: Stage 4.

### D-101. Part 2 spatial effect is structured only (ICAR), and longer chains

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (proposal; confirm).
- What happened: With BYM2 in Part 2 (dollars per resident, 395 tracts with
  a sited project), the lognormal fit failed: 69 divergences, R-hat 1.57,
  ESS 7. The Gamma fit had ESS 153.
- What is wrong: Each tract has one dollar figure. BYM2's unstructured
  tract effect and the model's own observation noise both describe
  tract-to-tract scatter, so the data cannot separate them.
- How we are fixing it:
  - Part 2 keeps the jurisdiction intercept and a structured spatial effect
    (ICAR, scaled by the same BYM2 scaling factor). It drops the
    unstructured tract term, whose role the observation noise already
    plays.
  - Part 1 keeps full BYM2: a yes or no outcome has no separate noise
    term.
  - Chains:
    - spatial Part 1 models run 4 × 5,000 draws after 2,000 warmup;
    - Model 2, the narrow-prior run and Part 2 run 4 × 10,000, keeping every
      2nd draw, after 2,000 to 3,000 warmup.
- Decision: As above. In Part 2 the "tract" scale is part of the residual.
- Reason: An effect that cannot be identified gives no information and
  breaks the sampler.
- Evidence: `outputs/ml/stage4/diagnostics.csv`;
  `scripts/ml/stage4_models.py` (`use_bym2="icar"`).
- Affects: Stage 4 Part 2 variance split.

### D-102. Part 2 family: lognormal; how Part 1 models are compared

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (rule from prompt 24:
  choose by posterior predictive checks); the tie-break is a proposal.
- What happened:
  - Both Part 2 families pass every posterior predictive check: the 10th,
    25th, 50th, 75th and 90th percentiles of sited dollars per resident all
    fall inside the 95% predictive ranges.
  - PSIS-LOO favours Gamma by 16 elpd. But the Gamma's LOO is unreliable:
    101 of 395 Pareto k exceed 0.7, and p_loo is 158. The Gamma fit also had
    1 divergence.
  - The lognormal's LOO has no k above 0.7 (p_loo 44), and its fit passes
    every MCMC check.
  - For Part 1, PSIS-LOO fails for every model with a BYM2 term: about 625
    of 697 k exceed 0.7, and p_loo is about 285. With one yes or no per
    tract, the tract-level effect lets each tract be fitted nearly on its
    own, so leaving one tract out changes the posterior too much for
    importance sampling.
- What is wrong: An unreliable LOO cannot pick a model.
- How we are fixing it:
  - Part 2 family rule: among fits that pass all MCMC checks and have
    reliable LOO (no more than 1% of k above 0.7), take the higher elpd. The
    PPCs must pass. This picks the lognormal.
  - Part 1 models are compared by the spatial cross-validation on the
    Stage 2 folds: log loss, ROC-AUC, PR-AUC, Brier and the summed
    out-of-fold log predictive density. PSIS-LOO and WAIC are reported but
    flagged.
- Decision: Lognormal for Part 2. Spatial CV for Part 1 model comparison.
- Reason: The PPCs cannot separate the two families. Only the lognormal's
  fit can be checked. K-fold CV does not depend on importance sampling.
- Evidence: `outputs/ml/stage4/loo.csv`, `posterior_predictive.csv`,
  `diagnostics.csv`, `spatial_cv_scores.csv`.
- Affects: Stage 4 Part 2 results; Stage 4 model comparison.

### D-103. Stage 4 recommendation: the Bayesian Model 1 as the module's one model

- Date: 5 Nov 2026. Status: Final (approved in D-104). Decided by: Amey (rule from
  prompt 24, A7); the result applied it.
- What happened: On the Stage 2 spatial folds, Model 1 (Part 1: BYM2 plus
  jurisdiction intercept) scored as follows.

  | Model | ROC-AUC | PR-AUC | Log loss |
  |---|---|---|---|
  | Model 1 | 0.685 | 0.730 | 0.643 |
  | Logistic regression | 0.675 | 0.719 | 0.653 |
  | XGBoost | 0.660 | 0.714 | 0.651 |

  Every paired-bootstrap 95% interval includes zero. Model 2 (spatially
  varying hazard slopes) converged but did not improve the out-of-fold elpd
  (+0.4, SE 0.8).
- What is wrong: Nothing. The rule says a model that predicts at least as
  well becomes the module's one model.
- How we are fixing it: Not applicable.
- Decision (proposed):
  - Model 1 becomes the module's one model, with lognormal Part 2.
  - Model 2 is not used.
  - Model 0c (no city intercept) is equivalent for prediction (−0.9 elpd for
    Model 1, SE 0.6). Model 1 is kept for the city level.
  - The dashboard is not changed until Part B.
  - Before Part B, Amey to decide whether Part 2's dollar predictions may be
    shown (D-088 says no).
- Reason: Prompt 24's A7 rule.
- Evidence: `outputs/ml/stage4/spatial_cv_scores.csv`,
  `spatial_cv_comparison.csv`, `spatial_cv_elpd_differences.csv`;
  `reports/ml/stage4_bayesian_report.md` section 6.
- Affects: Part B (unified admin Scenario screen).

### D-104. Bayesian Model 1 approved as the module's main model

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Amey approved D-103.
- What is wrong: Nothing.
- How we are fixing it: Not applicable.
- Decision:
  - Bayesian Model 1 (BYM2 plus city intercepts; lognormal Part 2) is the
    module's main model.
  - Model 0c (BYM2, no city intercept) stays reported as a comparison.
  - The Stage 2 machine learning setup stays available for comparison in
    the admin dashboard (Part B):
    - logistic regression for likelihood;
    - monotone XGBoost for scenario changes.
- Reason: D-103.
- Evidence: `reports/ml/stage4_bayesian_report.md` sections 4.3 and 6.
- Affects: Part B; the model card.

### D-105. Dollar figures stay off the dashboard; report the interval width

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Model 1's Part 2 predicts sited dollars per resident and
  passes its posterior predictive checks.
- What is wrong: Whether its intervals are narrow enough to show is not yet
  known.
- How we are fixing it: Report the median width, in dollars, of Model 1's
  90% intervals for dollars per resident, so Amey can decide later.
- Decision: D-088 stands. No dollar predictions on the dashboard.
- Reason: Amey's call. The decision waits for the interval widths.
- Evidence: `outputs/ml/stage4/dollar_interval_widths.csv` (written by
  `scripts/ml/stage4_dashboard.py`).
- Affects: Part B (no dollar figures shown).

### D-106. Wording of the heat result

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Stage 4 found that the raw heat gap disappears after
  controls. Distance from the coast explains the most.
- What is wrong: Nothing. This fixes the wording.
- How we are fixing it: The report and the dashboard About panel say it
  plainly. Hotter tracts receive less investment. After controls, this is
  explained mainly by distance from the coast (inland location), not by
  heat itself.
- Decision: Use that wording.
- Reason: Amey's call. It matches section 5.7 of the Stage 4 report.
- Evidence: `outputs/ml/stage4/heat_gap_after_controls.csv`.
- Affects: Stage 4 report; dashboard About panel.

### D-107. Four project types in the intervention tool; cost per resident by type

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The intervention tool offered two types, gray and
  nature-based or hybrid.
- What is wrong: The database has four types. In the sited, completed,
  funded or ongoing projects in training tracts there are:
  - Gray: 919;
  - Hybrid: 122;
  - Green: 40;
  - Blue: 18.
- How we are fixing it:
  - The tool offers gray, green, blue and hybrid.
  - Coverage (residents, exposed and vulnerable residents) does not depend
    on type, and the tool says so.
  - Typical sited cost per resident is computed per type: the median over
    that type's projects of project cost ÷ the receiving tract's residents.
  - Green and blue are flagged with their project counts, because so few
    projects make their medians unstable.
  - A four-class version of T4 is run (D-108).
- Decision: As above.
- Reason: Amey's call.
- Evidence: `outputs/ml/stage4/cost_per_resident_by_type.csv`.
- Affects: Part B intervention tool.

### D-108. Four-class project type (T4): not reliable for blue or hybrid; the binary model stays

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (rule); the result
  applied it.
- What happened: Following D-107, a four-class T4 (gray, green, blue,
  hybrid) was fitted:
  - same frame as the binary model: 1,092 projects, 27 tract features,
    project scale and hazard focus;
  - same spatial folds;
  - class weights: multinomial logistic with balanced weights, and
    XGBoost with balanced sample weights;
  - tuning inside each training fold.

  Spatial cross-validation:

  | Class | Projects | Logistic precision / recall | XGBoost precision / recall |
  |---|---|---|---|
  | Gray | 913 | 0.93 / 0.67 | 0.91 / 0.78 |
  | Green | 40 | 0.35 / 0.68 | 0.36 / 0.58 |
  | Blue | 17 | 0.04 / 0.35 | 0.00 / 0.00 |
  | Hybrid | 122 | 0.23 / 0.39 | 0.17 / 0.30 |

  Collapsing the four classes back to two gives ROC-AUC 0.79, the same as
  the binary model (0.79 to 0.80).
- What is wrong: Blue is not predictable from 17 projects. Hybrid is weak.
- How we are fixing it: Keep the binary model (gray against green, blue or
  hybrid) wherever a type model is used. Show no four-class predictions.
- Decision: The binary T4 stays. The intervention tool offers four types
  for coverage and cost only (D-107). Type does not come from a model.
- Reason: Amey's rule. Keep the binary model if blue or green are
  unreliable, and blue is.
- Evidence: `outputs/ml/stage4/t4_multiclass_per_class.csv`,
  `t4_multiclass_confusion.csv`; `scripts/ml/stage4_t4_multiclass.py`.
- Affects: Part B; model card.

### D-109. Part B design: two models in one admin Scenario screen

- Date: 5 Nov 2026. Status: Final. Decided by: Amey (the model switch, the
  compare view, the Bayesian default); the details are proposals.
- What happened: Amey asked for one admin screen with a switch between the
  machine learning setup (Stage 2/3) and Bayesian Model 1, plus a Compare
  models view.
- What is wrong: Several details had to be fixed so that the two models are
  shown on equal terms.
- How we are fixing it:
  - **Map likelihood.**
    - Machine learning: as in Stage 3, the logistic model's spatial
      out-of-fold, Venn-ABERS calibrated probability.
    - Bayesian: the spatial out-of-fold posterior mean from the Stage 4
      cross-validation fits, not the in-sample fit. The in-sample fit
      nearly reproduces each tract's own outcome (D-102).
  - **Bayesian interval.**
    - The 90% credible interval averages over the tract's own unexplained
      effect, and keeps parameter and neighbourhood uncertainty.
    - Median width is 0.73, against 0.13 for Venn-ABERS, which measures
      calibration uncertainty only.
    - Averaging out the neighbourhood effect too gives 0.34. That figure is
      reported but not shown.
  - **Scenario changes.**
    - Machine learning: the monotone XGBoost change is added to the map
      probability, as in Stage 3.
    - Bayesian: the sea level rise and surge inputs and their vulnerability
      interactions change draw by draw, using each fold fit's own
      standardization. City and neighbourhood effects are held fixed.
    - The Bayesian model is not monotone. Its sea level rise effect is
      negative, so higher sea level lowers its predictions. Under 6 ft and
      Category 5 the mean change is −0.085, against +0.016 for the machine
      learning model. The screen says so, and hatches extrapolated tracts.
  - **Heat** changes need and the gap only, for both models (D-093).
  - **Combined presets.**
    - Current baseline: 3 ft, Category 3, heat now.
    - Professor's median: 3 ft, Category 4, +2°F.
    - Lower: 1 ft, Category 1, now.
    - Higher: 6 ft, Category 5, +3°F.
    - Custom levels can be chosen per family.
    - Need is recomputed on the page from per-family percentiles, the same
      way as `scenarios.py`. For the professor's median this gives 118
      high-need tracts with no sited project (454,281 residents).
  - **The tract under 100 residents** is not in the Bayesian model's graph.
    Its Bayesian values are shown as not modelled.
  - **Compare models view:**
    - spatial CV scores for the Bayesian model, Model 0c, the logistic model
      both as shown (calibrated) and uncalibrated, and XGBoost;
    - paired bootstrap intervals and Moran's I;
    - a difference map and the 12 largest disagreements;
    - drivers side by side;
    - city effects, the neighbourhood effect map and the heat result;
    - a note on when to trust each model.
  - **The calibrated machine learning probabilities score lower** than the
    uncalibrated logistic model: ROC-AUC 0.644 against 0.675. Venn-ABERS
    calibration creates large ties, and many tracts sit at exactly 0.385.
    Both rows are shown.
  - The Bayesian model is the default. The PRELIMINARY label stays. No
    dollar predictions are shown (D-105).
- Decision: As above.
- Reason: Like-for-like comparison. Honest intervals.
- Evidence: `scripts/ml/stage4_dashboard.py`;
  `outputs/ml/dashboard/models.json`, `compare.json`.
- Affects: the admin Scenario screen (`src/admin/viz/scenario/`).

### D-110. Machine learning map shows the uncalibrated logistic probability

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Part B found that the Venn-ABERS calibrated probabilities
  on the machine learning map rank tracts worse than the uncalibrated
  logistic model (ROC-AUC 0.644 against 0.675). Calibration puts many
  tracts on the same value. Stage 2 found the logistic probabilities
  already well calibrated.
- What is wrong: The map showed the weaker version.
- How we are fixing it:
  - The machine learning map shows the uncalibrated logistic probability:
    spatial out-of-fold, from the same nested fits as Stage 2. The tract
    under 100 residents keeps its final-fit value.
  - Venn-ABERS is used only for the interval, labelled "calibration range,
    not full uncertainty".
  - The comparison table scores both models on what the map shows. The
    Venn-ABERS version stays as a labelled reference row.
- Decision:
  - As above.
  - Both as shown, Bayesian minus machine learning: ROC-AUC +0.010 (−0.012
    to +0.030), log loss −0.010 (−0.030 to +0.011). No clear difference.
- Reason: Amey's call. Better ranking at no cost in calibration.
- Evidence: `outputs/ml/dashboard/compare.json`;
  `scripts/ml/stage4_dashboard.py`.
- Affects: the admin Scenario screen.
- **Open question for Amey:** the uncalibrated probability lies outside its
  Venn-ABERS range in 423 of 697 tracts, because the range was built around
  the calibrated value. The screen says so tract by tract ("the map value
  lies outside it"). Dropping the range, or recomputing an interval around
  the uncalibrated value, needs a decision.

### D-111. Bayesian scenario changes with credible intervals; "no reliable change"

- Date: 5 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The screen showed Bayesian scenario changes as point
  values only.
- What is wrong: Many of those changes are smaller than their
  uncertainty.
- How we are fixing it:
  - **Per tract:** the change is computed draw by draw against the current
    baseline, from the same out-of-fold posterior as the likelihood
    interval (D-109). The 90% credible interval is the 5th to 95th
    percentile.
  - **Where the interval includes zero,** the screen shows "no reliable
    change", greyed out, instead of a number. A new "Change from current"
    map layer shows these tracts in pale grey.
  - **County average change** carries an interval too. Draws are paired by
    index across the ten independent fold fits.
  - The reliability flag is computed in Python at full precision and
    shipped with the data.
  - One added line on the screen: "Under current patterns, more future
    flood exposure does not attract more projects, so need and the gap are
    the main scenario outputs."
  - Machine learning changes have no interval and are shown as numbers.
- Decision: As above. Results:

  | Scenario | County average change (90% CrI) | Tracts reliably up | Tracts reliably down |
  |---|---|---|---|
  | Professor's median (3 ft, Cat 4) | +1.7 points (−0.5 to +3.8): no reliable change | 144 | 0 |
  | 6 ft, Cat 3 | −11.8 (−18.6 to −4.3) | 0 | 253 |
  | 6 ft, Cat 5 | −8.5 (−16.0 to −0.8) | 45 | 153 |

  The surge effect is positive, so a stronger surge reliably raises the
  likelihood in some tracts. Sea level rise lowers it.
- Reason: Amey's call.
- Evidence: `outputs/ml/stage4/stage4_dashboard_log.txt`;
  `src/admin/viz/scenario/scenarioModel.test.js`.
- Affects: the admin Scenario screen.

## Impact data (FEMA claims and grants)

D-112 is used on the `ml-scenario-module` branch, so this topic starts at
D-113.

### D-113. FEMA datasets: current OpenFEMA names, where the files live

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asked for OpenFEMA `FimaNfipClaims` and
  `HazardMitigationAssistanceProjects`, latest version.
- What is wrong: Neither name is served any more. Every version returns
  404, and neither appears in the OpenFEMA dataset list.
- How we are fixing it:
  - **Claims:** `NfipClaims` v3, title "NFIP Redacted Claims". This is the
    same dataset under its new name. Last data refresh 9 Sep 2026; records
    as of 8 Sep 2026.
  - **Grants:** `HmaSubapplications` v2, title "HMA Subapplications". This
    is the successor to the HMA projects dataset. Last data refresh
    8 Nov 2026.
  - Downloaded 8 Nov 2026 by paging the API (10,000 rows a page, ordered
    by `id`). The script stops if the rows saved differ from the API count
    or any `id` repeats.
  - Paths added to `scripts/common/paths.py`.
  - The raw claims CSV (27 MB) is git-ignored, like the other large raw
    downloads. The grants CSV and `download_log.json` (queries, counts,
    refresh dates) are kept in git.
  - The Census 2010-to-2020 tract relationship file was downloaded, as
    allowed, because conversion was needed (D-115). It sits under
    `data/raw/boundaries/rel2020/`, which is git-ignored.
  - Sources were recorded in two places:
    - a sources table at the top of `reports/impact/fema_first_look.md`,
      the project's convention;
    - new rows appended to the "Data and sources" table in
      `reports/ml/model_card.md`, the closest project-wide table. No
      existing row was changed.
- Decision: As above. Rows: 62,029 claims (equal to the API count); 288
  grant rows (D-114).
- Reason: These are the same datasets under their current names, and the
  latest versions, as the brief asked.
- Evidence: `data/raw/fema/download_log.json`;
  `scripts/impact/download_fema.py`.
- Affects: everything in `reports/impact/`.

### D-114. Which HMA rows count as Miami-Dade

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: HMA subapplications have no county code. The county is
  in `benefitingCounties`, a text field that can list several counties.
- What is wrong:
  - 69 Florida rows have no county at all.
  - "Statewide" rows benefit every county, Miami-Dade included, but are
    not Miami-Dade projects.
- How we are fixing it:
  - Kept: Florida rows whose `benefitingCounties` contains "Miami-Dade"
    (283).
  - Also kept: 5 rows with no county from bodies that are plainly in
    Miami-Dade, checked by hand against the Florida list:
    - City of Opa-locka;
    - Miami-Dade County;
    - Miami-Dade County DERM (2);
    - University of Miami.
  - Statewide rows that do not name Miami-Dade were left out.
- Decision: 288 rows.
- Reason: Keep what is clearly a Miami-Dade project, and nothing that
  only might be.
- Evidence: `scripts/impact/download_fema.py` (`HMA_NULL_COUNTY_KEEP`).
- Affects: D-117 and section 6 of the report.

### D-115. NFIP claims mix 2010 and 2020 tracts; how they were put on 2020 tracts

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened:
  - The only small-area location in the claims is `censusGeoid`, a
    12-digit block group code. Latitude and longitude are rounded to one
    decimal (29 points for the whole county). The data dictionary does not
    say which census the codes use.
  - Checked against the Census relationship file, the codes mix both
    censuses, record by record. 2010-only codes still appear in 2023
    claims. 2020-only codes appear in 1990s claims.
- What is wrong: Tract totals on 2020 GEOIDs need every claim on a 2020
  tract.
- How we are fixing it:
  - **Same tract in both censuses** (same code, at least 99% of land
    shared both ways): kept. 33,382 claims, 327 codes.
  - **2020-only code:** kept. 2,380 claims, 253 codes.
  - **Code valid in both but the shape changed:** kept as 2020. 2,588
    claims, 25 codes. These keep a median 98% of their land (lowest 81%).
    Treating them as 2010 would move 88 claims.
  - **2010-only code:** converted. 23,512 claims, 160 codes. Each claim is
    shared out to the 2020 tracts its 2010 tract overlaps, weighted by
    land area (`AREALAND_PART` over the 2010 tract's land). Total area is
    used only where a tract has no land. Claims and dollars become
    fractional. Only 794 of these claims have 90% or more of the land in
    one 2020 tract.
  - **Missing (160) or invalid or out of county (7):** not placed in a
    tract, kept in county totals.
  - The table carries `share_converted_from_2010`.
- Decision: As above. 341 of the 701 tracts get more than half their
  claims from conversion.
- Reason: The relationship file was the one conversion source allowed.
  Land area is the only weight it carries.
- Evidence: `scripts/impact/fema_first_look.py` (`classify_vintage`,
  `to_2020`); `outputs/impact/fema_first_look_log.json`.
- Affects: `data/processed/impact/nfip_claims_tract_year.csv`; sections 2,
  4 and 5 of the report.
- **Open question for Amey:** weighting the split by 2020 housing units
  per block would be better than land area. It needs the Census
  block-level relationship file, which was not downloaded.

### D-116. What counts as a claim and as dollars paid

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: 25,307 of the 62,029 claims paid nothing. Payments come in
  three parts: building, contents and increased cost of compliance.
- What is wrong: "Claims" and "dollars" need one meaning across the tables.
- How we are fixing it:
  - `claims` counts every claim record.
  - `claims_paid` counts only those with building plus contents above
    zero.
  - Dollars are building plus contents, as the brief asked. Increased
    cost of compliance is left out.
  - Dollars are nominal, not inflation-adjusted.
  - Year is `yearOfLoss`.
  - No row has a negative payment, so none needed handling.
- Decision: As above.
- Reason: As asked, and simple to explain.
- Evidence: `scripts/impact/fema_first_look.py` (`load_claims`).
- Affects: all claim tables and the report.

### D-117. Matching HMA grants to SCALE-R projects: cost and jurisdiction only

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened:
  - `subapplicationTitle` is empty in all 288 Miami-Dade rows, so names
    cannot be matched.
  - The only date fields with content are `dateSubmittedToFema` and
    `fiscalYear`. There is no approval or close date.
- What is wrong: The brief asked for matching by name, jurisdiction and
  cost.
- How we are fixing it:
  - **Cost:** SCALE-R `Estimated_Cost` against the FEMA total amount,
    federal share or benefit-cost total cost, within 2%.
  - **Jurisdiction:** the FEMA applicant mapped by hand to a SCALE-R
    jurisdiction. City names, county departments and the Public Health
    Trust map to Miami-Dade County; the water district maps to SFWMD.
    Hospitals, universities, nonprofits and state agencies are left
    unmapped. A county applicant counts as a plausible jurisdiction for a
    city project.
  - **Two checks on the name:**
    - the SCALE-R name or description cites the same disaster number;
    - a keyword test of whether FEMA's activity type contradicts the
      SCALE-R name.
  - **High:** cost equal to the dollar and not a multiple of $1,000;
    one-to-one among plausible exact candidates, with re-filings of one
    application counted once; activity not contradicted; and same
    jurisdiction or the same disaster cited.
  - **Medium:** one-to-one, activity not contradicted, plus one of:
    - same jurisdiction with an equal cost that is a multiple of $1,000
      but not $10,000;
    - same jurisdiction with costs within 1% and neither a multiple of
      $1,000;
    - a county applicant with cost equal to the dollar.
  - **Low:** everything else plausible. Not to be used as a date.
  - The date offered is `dateSubmittedToFema` (the earliest, for
    re-filings). Matches are written only to
    `data/processed/impact/hma_scaler_matches.csv`.
    `SCALE-R_Database.csv` is unchanged.
- Decision: 15 SCALE-R projects dated: 12 high, 3 medium. The medium
  S-25A pair (SFWMD, 2002 grant) is doubtful and should be checked by hand.
- Reason: Without titles, an exact non-round cost in the right
  jurisdiction is the strongest evidence available. Round costs match too
  many projects by chance; a $200,000 grant matched 22.
- Evidence: `scripts/impact/fema_first_look.py` (`hma`);
  `data/processed/impact/hma_scaler_matches.csv`.
- Affects: any later use of project dates.

### D-118. First-look correlations: frame and measures

- Date: 8 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asked for Spearman correlations of tract claims,
  total and per 1,000 residents, with four measures:
  - FEMA expected annual loss;
  - 3 ft sea level rise exposure;
  - Category 3 surge exposure;
  - sited investment per resident.
- What is wrong: The frame and the exact columns needed fixing.
- How we are fixing it:
  - **Frame:** the 697 training tracts from `ml_common.load_table()`. The
    tract under 100 residents is left out, as in the ML work.
  - **Columns:** `nri_eal_per_person`, `slr_3ft_pop_share`,
    `surge_cat3_any_pop_share`, and `sited_dollars / population`.
  - **Claims:** 1978 to 2026 totals. Tracts with no claims count as zero.
  - **Per 1,000 residents** uses the table's ACS 2020 to 2024 population.
  - Dollars paid (total and per resident) were added alongside.
  - A 2010-onward version was added as a check, because 1999 and 2000
    dominate the counts.
- Decision: As above. Descriptive only, no model.
- Reason: Same frame and variables as the rest of the project.
- Evidence: `outputs/impact/nfip_spearman.csv`;
  `outputs/impact/fema_first_look_log.json`.
- Affects: section 5 of the report.

---

## Benefit simulator (prompt 27)

### D-119. Where the benefit simulator work lives, and how it reaches the raw data

- Date: 10 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Prompt 27 asked for a new branch `benefit-simulator` from
  `impact-data`. The main checkout holds uncommitted work on
  `ml-scenario-module`, and `data/raw/` is git-ignored, so a fresh branch
  has none of the large inputs.
- What is wrong: Switching branches in the main checkout would disturb that
  work, and copying 9 GB of rasters and polygons is wasteful.
- How we are fixing it:
  - The branch lives in its own git worktree
    (`.claude/worktrees/benefit-simulator`), started from `impact-data`
    (commit 9914caa).
  - The existing raw inputs (boundaries, social, physical) and earlier
    outputs (ML, PCA, exposure) are reached through local links to the main
    checkout. They are read, never written.
  - Every new download goes into new folders under `data/raw/` that are
    git-ignored (`.gitignore` lists them).
  - All new paths are in `scripts/common/paths.py`.
- Decision: As above.
- Reason: Keeps both lines of work apart and the repository small.
- Evidence: `git worktree list`; `.gitignore`; `scripts/common/paths.py`.
- Affects: every prompt 27 script.

### D-120. NFIP policies: pulled community by community, needed fields only

- Date: 10 Nov 2026. Status: Replaced by D-135 (filter and paging); the
  kept fields still apply. Decided by: Amey (proposal; confirm).
- What happened:
  - OpenFEMA's current policy dataset is `NfipPolicies` v3 (title "NFIP
    Redacted Policies", 74.7 million rows nationally, last data refresh
    9 Sep 2026). `FimaNfipPolicies` returns 404.
  - The v3 file has no county field. Filters on the start of
    `censusGeoid` time out.
- What is wrong: The brief asked for Miami-Dade policies, and the full file
  is far too large to download.
- How we are fixing it:
  - Policies are requested one NFIP community at a time
    (`nfipRatedCommunityNumber`, an indexed field), for the 37 Miami-Dade
    community numbers named in the claims file (the county, the old
    Metropolitan Dade County number and every municipality). The few
    mis-coded numbers on Miami-Dade claims (Dade City, Monroe, Broward,
    out-of-state) are left out. The list covers 61,660 of the 61,867 claims
    with a Miami-Dade block group code.
  - Rows are then kept only where `censusGeoid` starts with 12086.
  - Only 26 of the 80 fields are kept: location, policy dates and count,
    flood zones, occupancy, building type and foundation, elevations,
    coverage, premium and CRS class.
  - Each community's saved rows must equal the API count; ids must be
    unique.
- Decision: As above.
- Reason: The only filter the API can run fast enough. The kept fields are
  what is needed to turn claims into rates per insured building.
- Evidence: `scripts/benefit/download_policies.py`;
  `data/raw/fema/nfip_policies_download_log.json`.
- Affects: Stage 2 calibration (claims per insured home).

### D-121. Tax roll: 2026 final NAL, qualified sales codes 01 and 02 only, no owner data

- Date: 10 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened:
  - The DOR data portal holds the 2026 final NAL for Miami-Dade (county
    number 23 in the 2026 User's Guide, page 2), posted 28 Oct 2026.
  - The file has 939,447 parcels. Its two sale slots hold only sales from
    2025 and 2026: 106,595 parcels have a first sale, 14,698 a second.
  - The file includes owner names and mailing addresses.
- What is wrong: Sale codes need a rule, and personal data should not
  travel into our tables.
- How we are fixing it:
  - Use the 2026 final roll, not the preliminary one.
  - A sale counts as qualified only with code 01 or 02 (User's Guide,
    pages 17 to 18: "qualified and included in sales ratio analysis",
    by deed examination or by documented evidence). Codes 03 to 06 are
    arm's length but the property changed after the sale, or the sale
    covered several parcels or crossed a county line, so the price does not
    match the parcel as described; they are left out. Codes 11 to 43 are
    disqualified (for example quit claim deeds, bank sales, sales between
    relatives). 98 and 99 are undecided.
  - Owner name, owner address and fiduciary fields are never read.
- Decision: As above.
- Reason: Codes 01 and 02 are the sales the state itself treats as market
  sales.
- Evidence: `data/raw/reference_docs/dor/2026_NAL_SDF_NAP_Users_Guide.pdf`;
  `scripts/benefit/build_buildings.py` (`NAL_COLS`).
- Affects: Stage 3. With sales only from 2025 and 2026, the before and
  after comparison around project dates cannot use this file.

### D-122. Linking buildings, parcels and the tax roll

- Date: 10 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened:
  - The DOR 2026 parcel file has 596,837 polygons. Condo units have no
    polygon of their own; the DOR ships a separate Miami-Dade condo unit
    point file whose `PARENT_FOL` names the building's master parcel.
  - NSI structures are points.
- What is wrong: The links need fixed rules, and a parcel can hold several
  buildings or hundreds of condo units.
- How we are fixing it:
  - A tax roll record is placed on its own polygon when the parcel IDs
    match; a condo unit is placed on its parent folio's polygon; failing
    that, on the polygon under its unit point.
  - A building takes the parcel polygon it sits in. If it sits on no
    parcel (on a road edge, for example), it takes the nearest parcel
    within 50 ft, flagged; otherwise none.
  - Tax roll values are summed over each parcel and its condo units.
  - Where a parcel holds several buildings, its just value is shared out by
    NSI floor area (`jv_alloc`). The parcel total is kept beside it.
- Decision: As above.
- Reason: Uses the state's own unit-to-building link; the floor-area share
  is the simplest split that keeps totals intact.
- Evidence: `scripts/benefit/build_buildings.py`;
  `outputs/benefit/stage1/build_stats.json`.
- Affects: `buildings.parquet`; Stages 2 to 4.

### D-123. FEMA flood zones: county NFHL file, base flood elevations kept in NGVD29

- Date: 10 Nov 2026. Status: Partly replaced by D-131 (the BFEs are now
  converted to NAVD88). Decided by: Amey (proposal; confirm).
- What happened:
  - The FEMA Map Service Center's Miami-Dade NFHL file is
    `12086C_20260125.zip` (database revised 26 Jan 2026).
  - The effective FIRM dates from 11 Sep 2009 (all 251 panels), with 60
    letters of map revision from 26 Feb 2010 to 26 Jan 2026.
  - A new FIRM is pending, effective 19 Feb 2027.
  - Base flood elevations are in feet NGVD29. The DEM is in NAVD88.
- What is wrong: The two datums differ by about a foot and a half in South
  Florida, and the exact local shift is not in any file we hold.
- How we are fixing it:
  - The table keeps the zone, subtype, SFHA flag and the BFE exactly as
    published, with its datum in a column.
  - The NGVD29 to NAVD88 conversion is left to Stage 2, where it will be
    taken from a cited source and logged.
  - Where flood polygons overlap, the higher hazard zone is kept.
- Decision: As above.
- Reason: Do not change published values silently.
- Evidence: `data/raw/fema/nfhl/extract/STUDY_INFO.dbf`, `S_FIRM_PAN.dbf`,
  `S_LOMR.dbf`.
- Affects: Stage 2 depths for the 1% and 0.2% floods. Results will need a
  refresh when the 2027 maps take effect.

### D-124. FEMA standard values: latest official documents, page-checked, nothing invented

- Date: 10 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asked for FEMA's standard values for
  displacement, mental stress, lost productivity, loss of function and
  green infrastructure and ecosystem services, with pages and dollar years.
- What is wrong:
  - FEMA's own BCA pages now point to 2024 and 2025 versions of the
    methodology reports. The older URLs return 404.
  - The dollar values for mental stress and lost productivity are not
    printed in any of the FEMA documents. The Help Content describes the
    method only. State agency slides quote $2,443 and $8,736.
- How we are fixing it:
  - Six FEMA documents are saved in `data/raw/reference_docs/fema/`: the
    Standard Economic Value report v13 (Sep 2024, updated Jul 2025), the
    flood module report v6, the project configuration report v6, the BCA
    Toolkit Help Content (28 Aug 2025), the green infrastructure values
    (Jul 2022, updated Jul 2025) and the ecosystem service value update
    (Jun 2022).
  - `build_reference_tables.py` holds each value with a text snippet. It
    finds the snippet in the PDF and writes the PDF page and printed page
    itself. A value whose snippet is not on the page stops the script.
  - Values not printed by FEMA go to `fema_standard_values_missing.csv`.
    Secondary sources are not used.
  - Rows that would double count with property values or avoided flood
    losses are marked (green infrastructure "property value improvement";
    the aesthetic, recreation and flood reduction parts of the ecosystem
    values).
  - Discount rate: FEMA's default for new analyses is 7% (Help Content).
    3.1% (used in 2023 and 2024) is kept as a sensitivity value.
- Decision: As above. 175 values, 6 missing items.
- Reason: Every dollar figure must trace to a page.
- Evidence: `data/reference/fema_standard_values.csv`,
  `fema_standard_values_missing.csv`.
- Affects: Stages 2 and 4. Mental stress and lost productivity cannot be
  valued until the user supplies an official FEMA source or approves an
  alternative.

### D-125. Depth-damage curves: the USACE occupancy library that matches NSI codes

- Date: 10 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asked for standard FEMA Hazus or USACE curves
  for the main occupancy and foundation types.
- What is wrong: The full Hazus and BCA Toolkit curve libraries sit inside
  the software, not in a downloadable document.
- How we are fixing it:
  - Use the occupancy type library USACE ships with its consequence model,
    go-consequences (`structures/occtypes.json`, pinned at commit
    dff647c, 27 Dec 2021). It is keyed to the same occupancy codes as the
    NSI (for example RES1-1SNB, COM1).
  - Keep the freshwater depth curves (USACE EGM 01-03 for houses,
    HEC-FIA Galveston curves for other uses) and the saltwater "depth,
    salinity" curves where USACE supplies them (FEMA coastal and NACCS).
  - Store mean, standard deviation and a low to high band per depth.
  - Check: the RES1-1SNB structure and contents curves equal FEMA's printed
    example DDF (flood module report v6, Table 1, page 12: 13.4% and 8.1%
    at 0 ft, 23.3% and 13.3% at 1 ft).
- Decision: As above.
- Reason: A public, versioned USACE source that lines up with the
  building inventory.
- Evidence: `data/reference/depth_damage_curves.csv`;
  `data/raw/reference_docs/usace/occtypes_commit.txt`.
- Affects: Stage 2 damage estimates.

### D-126. Building hazard values: DEM ground elevation, surge class, sea level rise flags

- Date: 10 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The table needs ground elevation and our hazard values at
  each building.
- What is wrong: The NOAA DEM is not stored locally, the surge rasters hold
  1 ft depth bins, and the sea level rise data are polygons with no depth.
- How we are fixing it:
  - **Ground:** the NOAA OCM FL_SE 3 m DEM (NAVD88, metres) is read tile
    by tile over HTTP, as the website's map script does. Values below
    -50 m (NOAA's -99 water code) are treated as no ground. Feet are
    metres divided by 0.3048. NSI's own ground elevation is kept beside it
    as a check.
  - **Surge:** the class at the building's pixel, for Categories 1 to 5.
    Depth is the bin midpoint (class minus 0.5 ft); class 21 ("more than
    20 ft") is set to 20.5 ft. Off-depth codes (255 on land) count as dry.
  - **Sea level rise:** 1 if the building point lies in the inundated
    polygon at 1, 2, 3 or 6 ft, else 0. The "low-lying, not connected"
    3 ft layer is kept as a separate flag, as in D-036.
  - **Block group and tract:** a point-in-polygon join to TIGER/Line 2024
    block groups (2020 geography); nearest block group for points just
    outside.
- Decision: As above.
- Reason: Same sources as the rest of the project; nothing is resampled.
- Evidence: `scripts/benefit/build_buildings.py`.
- Affects: Stage 2 depths. Surge depths are screening level (NHC: "not for
  a parcel level ... assessment").

### D-127. Parquet output needs a package that is not installed

- Date: 10 Nov 2026. Status: Final (approved by the user on 10 Nov 2026;
  pyarrow 21.0.0 installed in `.venv` only). Decided by: Amey, confirmed by
  the user.
- What happened: The brief asks for `buildings.parquet`. Neither `.venv`
  nor `.venv-ml` has a Parquet engine (pyarrow or fastparquet).
- What is wrong: Installing a package needs the user's approval.
- How we are fixing it: Until approved, the script writes the same table
  as `data/processed/benefit/buildings.csv.gz`. Once pyarrow is installed
  (pinned version, into the project environment only), a rerun writes the
  Parquet file from the checkpoints in seconds.
- Decision: Ask the user. The user approved; pyarrow 21.0.0 (pinned, from
  a binary wheel) was installed into the project environment `.venv`, and
  the table is written as Parquet.
- Reason: Standing rule on installs.
- Evidence: `outputs/benefit/stage1/build_stats.json` (`parquet_pending`).
- Affects: the file format only.

### D-128. NSI version: 2022 as the brief says, not the 2026 version the API now serves

- Date: 10 Nov 2026. Status: Replaced by D-130. Decided by: Amey (proposal; confirm).
- What happened:
  - USACE released NSI 2026, and its API now serves 2026 data. The 2022
    version is still offered as state GeoPackages by the download tool
    (`nsi_2022_12.gpkg.zip`, file dated 30 Sep 2022).
  - The 2026 API extract for Miami-Dade was downloaded first, before the
    version was checked.
- What is wrong: The brief names NSI 2022.
- How we are fixing it:
  - The building table uses NSI 2022 (579,117 Miami-Dade structures).
  - The 2026 extract stays in `data/raw/nsi/` unused. It can be deleted, or
    used later as a check or an update if the user prefers the newer
    version.
  - NSI values are depreciated replacement costs, not market prices.
- Decision: As above.
- Reason: Follow the brief; flag the newer version.
- Evidence: `data/raw/nsi/nsi_2022_12_headers.txt`;
  USACE NSI technical references, release notes (2026).
- Affects: all building values and resident counts.

### D-129. FHFA tract index: new file name, 2020 tracts confirmed

- Date: 10 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The brief's file name `hpi_at_bdl_tract.csv` now returns
  FHFA's 404 page. FHFA's dataset page lists the census tract index as
  `hpi_at_tract.csv` (annual, developmental, not seasonally adjusted).
- What is wrong: The file name changed, and the tract vintage needed
  checking.
- How we are fixing it:
  - Download `hpi_at_tract.csv`, keep the Miami-Dade rows (codes starting
    12086), and delete the national file after recording its checksum.
  - Vintage check: all 425 Miami-Dade tract codes are valid 2020 tracts;
    220 of them exist only in 2020. So the file uses 2020 tracts.
- Decision: As above.
- Reason: Same product under its current name.
- Evidence: `data/raw/fhfa/sha256.txt`.
- Affects: Stage 3 step 6. Only 425 of 707 tracts have an index, and only
  222 have a 2025 value.

### D-130. NSI 2026 replaces NSI 2022

- Date: 10 Nov 2026. Status: Final. Decided by: the user (rule: use the
  latest available data). Replaces D-128.
- What happened: The user chose NSI 2026, the version the NSI API now
  serves, over the 2022 version named in the brief.
- What is wrong: Nothing. The two versions differ, so the change is
  measured.
- How we are fixing it:
  - The building table uses the NSI 2026 API extract for Miami-Dade
    (627,252 structures).
  - Comparison with NSI 2022 (579,117 structures), before any recoding:
    - Structure value $414.1 billion against $243.0 billion; contents
      $305.4 billion against $176.0 billion.
    - Night residents 2.88 million against 2.66 million.
    - Foundations, slab / crawl / basement / pile / pier: 419,223 /
      121,459 / 56,201 / 15,699 / 13,942 in 2026, against 289,031 /
      170,575 / 109,704 / 7,589 / 1,833 in 2022.
    - By 2020 tract (our own point-in-polygon join, because NSI 2022 uses
      2010 block codes and NSI 2026 uses 2020 codes): Spearman 0.96 for
      structure counts and 0.77 for structure value.
    - No structure ID is shared between the versions.
  - The 2022 run is kept in `outputs/benefit/stage1_nsi2022/` for
    reference.
- Decision: As above.
- Reason: Latest data, newer inputs and better population and value
  methods (NSI 2026 release notes).
- Evidence: `scripts/benefit/compare_nsi_versions.py`;
  `outputs/benefit/stage1/nsi_2022_vs_2026.json`.
- Affects: every building value and resident count.

### D-131. FEMA base flood elevations converted from NGVD29 to NAVD88 with NOAA NCAT

- Date: 10 Nov 2026. Status: Final. Decided by: the user (method);
  Amey (grid). Replaces the "convert later" part of D-123.
- What happened: All 260,450 buildings with a base flood elevation have
  it in NGVD29 (FIRM effective 11 Sep 2009). The DEM is in NAVD88.
- What is wrong: The two cannot be compared without a datum shift.
- How we are fixing it:
  - NOAA's NGS Coordinate Conversion and Transformation Tool (NCAT, web
    API, VERTCON 3.0) was asked for the NAVD88 height of an NGVD29 height
    of 0, on a 0.05 degree grid over the county (323 points).
  - The shift is interpolated bilinearly to each building and added to
    the published BFE: `fema_bfe_ft_navd88`.
  - Shift across the grid: -1.42 to -2.05 ft. At buildings with a BFE:
    -1.47 to -1.91 ft, median -1.55 ft. NCAT's stated uncertainty is
    under 1 cm at the test point.
  - BFEs already in NAVD88 pass through unchanged. So when the new FIRM
    (effective 19 Feb 2027) is published, the county file is downloaded,
    `paths.NFHL_COUNTY_ZIP` is changed, and the script reruns.
- Decision: As above.
- Reason: NOAA's official conversion, as the user asked.
- Evidence: `scripts/benefit/fetch_vertcon_grid.py`;
  `data/reference/ngvd29_to_navd88_grid.csv`;
  `outputs/benefit/stage1/build_stats.json`.
- Affects: Stage 2 flood depths for the 1% and 0.2% events.

### D-132. NSI basements recoded to slab

- Date: 10 Nov 2026. Status: Final. Decided by: the user (recode); Amey
  (first-floor height).
- What happened: NSI 2026 gives 56,201 Miami-Dade structures a basement
  foundation and 46,994 a "with basement" occupancy code (RES1-1SWB and
  similar). Basements are almost absent in Miami-Dade because of the high
  water table.
- What is wrong: Basement damage curves and foundation heights would
  overstate damage.
- How we are fixing it:
  - Foundation B becomes S (slab); occupancy codes with "WB" become "NB"
    (no basement). 56,205 structures change (46,990 have both).
  - NSI gives all of them a first floor 2.0 ft above ground (one at
    5.25 ft). A slab house sits lower, so each takes the median height of
    existing slab buildings of its occupancy type: 0.75 ft (46,994),
    0.5 ft (7,456) or 0.25 ft (1,755).
  - The tax roll has no foundation field, so it cannot refine this.
  - The original NSI values are kept in `nsi_found_type_orig`,
    `nsi_occtype_orig` and `nsi_found_ht_orig`, with a `basement_recoded`
    flag.
- Decision: As above.
- Reason: Local building practice; keeps damage curves realistic.
- Evidence: `scripts/benefit/build_buildings.py` (`load_nsi`).
- Affects: Stage 2 damage curves and first-floor depths.

### D-133. Mental stress and lost productivity: still no FEMA-printed value

- Date: 10 Nov 2026. Status: Final. Decided by: the user (rule); Amey
  (search).
- What happened: The user asked to check FEMA's sustainability benefits
  methodology and current BCA Toolkit documentation, and to add the values
  only if a FEMA document prints them.
- What is wrong: None of the FEMA documents still available prints them.
- How we are fixing it: Checked:
  - BCA Toolkit Help Content (28 Aug 2025), PDF pages 176 to 177: method
    only (a standard value times residents not displaced, and times working
    residents).
  - Standard Economic Value report v13 (2024, updated 2025) and flood
    module report v6: not mentioned.
  - BCA Toolkit 6.0 release notes (Jul 2020) and User Guide (May 2019): not
    printed.
  - The 2012 "Final Sustainability Benefits Methodology Report" is not on
    fema.gov. The FEMA web page that printed "Table 5: BCA Social Benefits
    Values" returns 404. Two FEMA policy aids return "This file is
    unpublished".
  - State agency slides quote $2,443 per person and $8,736 per worker.
    These are not FEMA documents and are not used.
- Decision: Both stay in `fema_standard_values_missing.csv`.
- Reason: The user's rule: only values printed by FEMA, with page and
  dollar year.
- Evidence: `data/reference/fema_standard_values_missing.csv`.
- Affects: Stage 2 people-related losses (displacement can be valued;
  mental stress and productivity cannot).

### D-134. Value basis of NSI dollars, and why NSI 2026 values are higher

- Date: 11 Nov 2026. Status: Final. Decided by: Amey (from the NSI
  documentation; the user asked for the check).
- What happened: NSI 2026 structure value is 70% higher than NSI 2022.
- What is wrong: Stage 2 damage dollars need a clear value basis and
  price year.
- How we are fixing it:
  - **Basis (NSI technical documentation).**
    - NSI 2026: `val_struct` is depreciated replacement value; `fullrep`
      is full replacement cost new ($564.4 billion in Miami-Dade). "All
      values are reported in August 2025 price levels." Costs are scaled
      by county construction wages. Depreciation follows tract-based
      curves (lower, typical or higher maintenance).
    - NSI 2022: depreciated replacement value at 2021 price levels,
      depreciated 1% a year for 20 years, then held at 80%.
    - Contents (2026): depreciated structure value times an occupancy
      ratio; 0.5 for RES1. The documentation notes that USACE EGM 04-01
      assumes 1.0 and that users of EGM curves calibrated to structure
      value should use the EGM ratio. Stage 2 must handle this.
  - **Where the increase comes from** (total = structures x floor area per
    structure x value per square foot, shares of the log increase):
    - All structures (x1.70): more structures 15%, larger floor area per
      structure 70% (3,405 to 4,934 sq ft), higher value per square foot
      15% ($123 to $134).
    - Single-family (RES1, x1.62): more structures 17%, floor area 2%,
      value per square foot 81% ($106 to $157). For houses the rise is
      mostly price level (2021 to August 2025) and the new depreciation
      method.
  - **Label for Stage 2:** damage dollars are "estimated from our data:
    NSI 2026 depreciated replacement value, August 2025 dollars".
- Decision: As above.
- Reason: Keeps estimated and published dollars apart, and states the
  price year.
- Evidence: NSI technical references, technical documentation (2026 and
  2022 versions);
  `outputs/benefit/stage1/nsi_2022_vs_2026.json`.
- Affects: Stage 2 damage and every later dollar figure based on NSI.

### D-135. NFIP policies: county filter on the census code, large pages, no per-page count

- Date: 11 Nov 2026. Status: Final. Decided by: the user (filter and
  paging rules); Amey (page sizes). Replaces the filter and paging of D-120.
- What happened:
  - The community-by-community download (D-120) stopped after 4 of 37
    communities because FEMA's API returned 503 errors for hours.
  - On 11 Nov 2026 the API was answering again, and the user set new rules.
- What is wrong: The old method was slow (10,000-row pages, a count on every
  page) and fragile.
- How we are fixing it:
  - Filter: `propertyState eq 'FL' and startswith(censusGeoid,'12086')`
    (v3 policies have no county field). This replaces the list of 37
    community numbers, so policies are kept by location only, whatever
    community number they carry.
  - Page size: the largest that answers reliably. Tests on 11 Nov 2026:
    250,000 rows (ID only) answered in 77 s; 1,000,000 rows timed out with
    a 503. With the 26 kept fields, 100,000 rows took 42 s and 200,000 took
    138 s. Pages are 200,000 rows; a failed page is retried at 100,000 and
    then 50,000 rows.
  - No `$count` on the pages. The saved rows are counted, and the API total
    is asked once at the end; the two must match, and every ID must be
    unique.
  - Each page is saved as it arrives, so a rerun resumes.
  - If 503 errors continue after the retries, the script stops and reports;
    the user will then download the full Parquet file by hand.
  - The 26 kept fields are unchanged from D-120.
- Decision: As above.
- Reason: The user's settings; fewer, larger requests and no slow count.
- Evidence: `scripts/benefit/download_policies.py`;
  `data/raw/fema/nfip_policies_download_log.json` (written when complete).
- Affects: Stage 2 calibration.

### D-136. Hurricane frequencies for the surge events

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: Stage 2 needs a yearly chance for each surge category. The
  brief asks for published return periods for Miami-Dade, cited and logged
  as an assumption.
- What is wrong: NHC's current return period maps (50 nautical miles of a
  point, HURISK, data to 2010) give only "any hurricane" and "major
  hurricane", not each category. Along the Southeast Florida coast the maps
  show about 6 to 7 years for hurricanes and 14 to 19 years for major
  hurricanes.
- How we are fixing it:
  - Use NOAA Technical Memorandum NWS NHC-6 (Blake, Landsea and Gibney,
    2011), Table 10, Florida (Southeast) row, strikes 1851 to 2010 by
    category: 16, 14, 11, 3 and 1 (PDF page 23, printed page 21).
  - Yearly chance of at least Category k = strikes of Category k or more
    divided by 160 years: 0.281, 0.181, 0.094, 0.025 and 0.006 (return
    periods 3.6, 5.5, 10.7, 40 and 160 years).
  - The script checks the row against the PDF text before writing
    `data/reference/hurricane_strike_rates.csv`. The NHC maps are kept in
    `data/raw/reference_docs/nhc/` as a check.
- Decision: As above, labelled "assumption (published historical
  frequency)".
- Reason: The only NOAA table that splits strikes by category for a region
  that contains Miami-Dade.
- Evidence: `scripts/benefit/build_hurricane_rates.py`.
- Affects: surge part of the expected annual damage; see D-142.

### D-137. Turning events into expected annual damage

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: There are two hazard families: surge (five categories)
  and FEMA flood zones (1% and 0.2%). Coastal FEMA base flood elevations
  already include storm surge.
- What is wrong: Adding the two families would count the same flood twice.
- How we are fixing it:
  - Put all seven events on one probability scale. At each probability,
    keep the larger damage of the two families (never the sum), and make
    damage never fall as events get rarer.
  - Middle estimate: trapezoid rule over the probabilities, plus the
    rarest event's damage times its probability for the tail.
  - Low estimate: low curve band and the damage of the more frequent end
    of each interval. High estimate: high curve band and the rarer end.
  - FEMA maps print no 0.2% flood elevation, so the 0.2% event uses the 1%
    depth (a lower bound). Zone A (1,452 buildings, no elevation) and the
    shaded 0.2% zone X (34,893) get no FEMA depth.
- Decision: As above.
- Reason: Avoids double counting and gives an honest range.
- Evidence: `scripts/benefit/baseline_risk.py` (`ead`).
- Affects: every EAD figure.

### D-138. Damage curves, water type and the value base

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The USACE library (D-125) has freshwater curves for all
  types and saltwater curves for houses (RES1) and commercial types only.
- What is wrong: Each event needs one curve per building and a clear value
  base (D-134).
- How we are fixing it:
  - Surge and FEMA zone VE use saltwater curves where they exist (pier
    versions for pier foundations); all other cases use freshwater curves.
  - Contents: the EGM freshwater house curves are scaled to structure
    value, as the NSI documentation advises, so contents damage uses
    structure value there; other curves use NSI contents value.
  - Main value base: NSI depreciated replacement value, August 2025
    prices. A full replacement cost version is also given.
  - No damage is counted where the water does not reach the building.
- Decision: As above.
- Reason: Follows the curve sources and the NSI documentation.
- Evidence: `scripts/benefit/baseline_risk.py` (`damage_fractions`).
- Affects: all damage dollars (labelled "estimated from our data, with
  standard curves").

### D-139. Displacement, mental stress and lost productivity

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asks for displacement, mental stress and lost
  productivity, using FEMA standard values.
- What is wrong: FEMA prints displacement days only for one example (one
  story, no basement: 45 days per foot, 0 to 5 ft). Mental stress and lost
  productivity have no FEMA-printed value (D-133).
- How we are fixing it:
  - Displacement = FEMA rent per square foot per month x flooded floor area
    x days, plus FEMA's one-time disruption cost per square foot (2021
    dollars, by occupancy).
  - Days: FEMA's example, 45 days per foot of water above the first floor,
    capped at 225 days at 5 ft, used for all building types (an extension,
    labelled as such). Low and high cases added in D-145.
  - Flooded floor area: floor area divided by stories (only the ground
    floor). Story counts are capped at 60 (NSI has a few impossible
    values).
  - Mental stress and lost productivity: not put in dollars. The report
    gives the people counts they would multiply.
- Decision: As above, all labelled "assumption (FEMA standard values)".
- Reason: Uses only values FEMA prints.
- Evidence: `scripts/benefit/baseline_risk.py` (`displacement_cost`).
- Affects: Stage 2 people and other losses; Stage 4 avoided losses.

### D-140. Provisional check against NFIP claims per occupied housing unit

- Date: 11 Nov 2026. Status: Provisional. Decided by: the user (use claims
  per housing unit until the policies arrive); Amey (details).
- What happened: The policies file is incomplete (D-135). The user asked
  for a provisional check against claims per housing unit (ACS).
- What is wrong: No consumer price index is on disk, and it is not in the
  list of downloads, so claims cannot be inflation-adjusted yet. (Update:
  the user approved CPI-U on 11 Nov 2026; claims are now in 2025 dollars,
  D-144.)
- How we are fixing it:
  - Observed: NFIP building plus contents payments by 2020 tract, 1978 to
    2025, averaged per year with weights that halve every 15 years back
    from 2025. Nominal dollars at first; 2025 dollars since D-144.
  - Denominator: occupied housing units, ACS 2020-2024 table B25003,
    summed from block groups. Tracts with fewer than 50 units are left out.
  - Measures: Spearman correlation of modelled EAD per unit and claims per
    unit (with a bootstrap 95% interval), and the ratio of county totals.
  - Labelled provisional. It will be redone with the policies file
    (claims per insured home) and, with the user's approval, a CPI series.
- Decision: As above. No adjustment is applied.
- Reason: The user's instruction; the brief says adjust only if clearly
  justified.
- Evidence: `outputs/benefit/stage2/summary.json` (`calibration`),
  `calibration_deciles.csv`.
- Affects: Stage 2 calibration; see D-142.

### D-141. Sea level rise in Stage 2

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The NOAA sea level rise layers show where land would be
  under water at high tide, with no depth.
- What is wrong: They cannot be used as one more flood event with a
  probability.
- How we are fixing it:
  - Future storm risk: 1, 2 and 3 ft are added to the water level of each
    event (to surge only where the event already floods; to the FEMA flood
    elevation everywhere), and EAD is recomputed.
  - Permanent high-tide flooding (1, 2, 3 and 6 ft layers) is reported
    separately as buildings, value and residents, not as yearly damage.
- Decision: As above.
- Reason: Keeps permanent flooding apart from storm risk, so nothing is
  counted twice.
- Evidence: `scripts/benefit/baseline_risk.py` (`event_depths`).
- Affects: Stage 2 scenarios; Stage 4 scenario option.

### D-142. Surge maps give damage far above the claims record: FEMA zones carry the yearly risk

- Date: 11 Nov 2026. Status: Final. Decided by: the user (option A, 11 Nov
  2026). Replaces the combining rule of D-137 for the main figure.
- What happened:
  - Modelled EAD (middle) is $7.9 billion a year; $7.9 billion of it comes
    from surge. NFIP claims average $20 million a year (weighted, nominal).
    The ratio is about 390 (low to high 200 to 660). FEMA zones alone give
    $354 million a year, about 17 times the claims.
  - One Category 5 surge map event damages $132 billion of buildings. In
    1992 Hurricane Andrew (Category 5, Miami-Dade) produced $138 million of
    NFIP payments.
  - Tract ranking agrees only moderately: Spearman 0.44 (95% interval 0.38
    to 0.50) for all events, 0.49 for FEMA zones alone, 0.41 for surge
    alone.
- What is wrong: The NHC surge rasters are "maximum of maximums": for each
  category, the worst depth any storm of that category could bring at high
  tide. Any single storm floods only part of that area. Pairing them with
  the chance that a storm of that category hits anywhere in Southeast
  Florida overstates yearly damage many times over. Insurance take-up,
  coverage limits and deductibles explain a factor of a few, not 390.
- How we are fixing it: Not fixed. Stopped and reported, as the standing
  rules require. Options for the user:
  - A (recommended): main EAD from the FEMA 1% and 0.2% floods only (they
    already include surge on the coast); surge maps kept as worst-case
    "what if" scenarios with damage per event, not yearly figures.
  - B: keep both families and scale the surge part to the claims record
    (a calibration factor of the size above).
  - C: keep the combined figure as an upper bound, labelled as such.
- Decision: Option A (the user's choice). The main expected annual damage,
  displacement and people figures come from the FEMA 1% and 0.2% floods
  only. The surge maps are reported as worst-case scenarios per event
  (buildings, residents and damage if that map's flooding happened), with
  no yearly figure. The combined figure stays in the building file as a
  reference column only (`ead_combined_ref_*`). No calibration factor is
  applied.
- Reason: The difference is too large to adjust quietly; FEMA's coastal
  flood elevations already include surge.
- Evidence: `outputs/benefit/stage2/summary.json`;
  `outputs/benefit/stage2/calibration_deciles.csv`.
- Affects: all Stage 2 results, Stage 4 avoided losses.

### D-143. Multi-story buildings: damage only on the floors the water reaches

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: After D-142, half of the yearly damage sat in a few large
  buildings. The largest, a 12-story commercial building worth $1.1 billion,
  lost $901 million in the 1% flood from 2.8 ft of water.
- What is wrong: The commercial, public and apartment curves (HEC-FIA
  Galveston, NACCS) give a share of the whole building's value. Water 3 ft
  deep cannot damage the floors above it. Only the house curves (RES1)
  already depend on the number of stories.
- How we are fixing it:
  - For every type except RES1, the curve is applied only to the share of
    the building on floors the water reaches: 1 + whole multiples of 10 ft
    of water above the first floor, divided by the number of stories
    (capped at 60).
  - Houses (RES1) are unchanged.
  - The whole-building figure is kept as a reference column
    (`ead_whole_building_ref_slr0`).
- Decision: As above.
- Reason: A physical limit, not a fit to the claims. Ground floors often
  hold more value (lobbies, plant rooms), so this may understate damage in
  tall buildings; the report says so.
- Evidence: `scripts/benefit/baseline_risk.py` (`flooded_share`). Effect:
  county expected annual damage (middle) falls from $354 million to $174
  million; the ratio to claims from 17 to 8.4; the tract Spearman moves
  from 0.49 to 0.50.
- Affects: all Stage 2 damage dollars; Stage 4 avoided losses.

### D-144. Claims inflation-adjusted to 2025 dollars with CPI-U

- Date: 11 Nov 2026. Status: Final. Decided by: the user (approved the
  download and the 2025 base); Amey (details).
- What happened: The brief asks for inflation-adjusted claims. No price
  index was on disk (D-140).
- What is wrong: Old claims in old dollars make the gap look larger than
  it is.
- How we are fixing it:
  - Downloaded BLS series CUUR0000SA0 (CPI-U, US city average, all items,
    not seasonally adjusted) for 1978 to 2025 from the BLS Public Data API
    v1 (five requests of ten years) into `data/raw/bls/`.
  - Annual value = mean of the months. October 2025 was not published (the
    2025 lapse in appropriations), so 2025 uses 11 months.
  - Each year's payments are multiplied by CPI 2025 / CPI of the loss year
    (for example 2.29 for 1992 and 1.31 for 2017).
  - The results match BLS published annual averages (1992: 140.3; 2000:
    172.2; 2017: 245.1).
- Decision: As above. Claims are reported in 2025 dollars; NSI values are
  August 2025 prices, so the two are close in time.
- Reason: The user's approval; CPI-U is the standard general price index.
- Evidence: `scripts/benefit/build_cpi.py`; `data/reference/cpi_u_annual.csv`.
- Affects: Stage 2 calibration (weighted claims rise from $20.2 million to
  $30.3 million a year).

### D-145. Displacement duration: one assumption, with low and high cases

- Date: 11 Nov 2026. Status: Final. Decided by: the user (asked for the
  label and a range); Amey (the range).
- What happened: FEMA prints displacement days for one building type only
  (D-139), and we apply it to all types.
- What is wrong: A single duration for every building type is an
  assumption, and it needs a range.
- How we are fixing it:
  - Middle: FEMA's 45 days per foot, capped at 225 days.
  - Low: half of that (22.5 days per foot). High: one and a half times (67.5
    days per foot). The one-time cost is the same in all cases.
  - The 0.5 and 1.5 multipliers are our sensitivity choice, not FEMA
    values, and the report says so.
- Decision: As above.
- Reason: Shows how much the result depends on the assumption, without
  inventing a FEMA number.
- Evidence: `scripts/benefit/baseline_risk.py` (`DISP_DAYS_CASES`).
- Affects: displacement figures in Stage 2 and Stage 4.

### D-146. No scaling to the claims; what the remaining gap is made of

- Date: 11 Nov 2026. Status: Provisional (final check waits for the
  policies file). Decided by: the user (no scaling; break the gap down);
  Amey (method).
- What happened: After D-142, D-143 and D-144, modelled yearly damage is 5.7
  times NFIP payments (4.0 times for homes only).
- What is wrong: The gap needs explaining before anything is adjusted.
- How we are fixing it:
  - The model is not scaled.
  - The gap is broken into known factors, each a multiplier on the gap,
    using county totals in 2025 dollars:
    1. Homes only (NFIP is mostly homes): factor 0.69.
    2. Residential claims inside the FEMA 100-year zones only (the model
       covers only those floods; 10% of residential payments are outside):
       factor 1.11.
    3. Replacement cost instead of depreciated value (NFIP pays
       replacement cost for many homes): factor 1.24.
    4. Payout caps and deductibles: paid divided by adjusted damage in the
       18,247 residential claims that record both (54% of paid residential
       claims): 0.91, factor 0.91.
    5. Left over: a gap of 4.9, which would mean about 20% of residential
       flood losses are insured. This is to be measured with the policies
       file.
  - Caveat: adjusters record damage to insured items, so step 4 shows the
    effect of deductibles and limits within coverage, not losses above
    coverage.
- Decision: As above.
- Reason: The user's instruction; a transparent breakdown rather than a
  fitted factor.
- Evidence: `scripts/benefit/baseline_risk.py` (`gap_decomposition`);
  `outputs/benefit/stage2/summary.json` (`gap_decomposition`).
- Affects: Stage 2 calibration; Stage 4 uses the uncalibrated figures with
  this note.

### D-147. Limitation: only two flood frequencies

- Date: 11 Nov 2026. Status: Final. Decided by: the user (state it as a
  limitation).
- What happened: The yearly figure rests on the FEMA 1% and 0.2% floods only
  (D-142).
- What is wrong: Frequent small floods (heavy rain outside the mapped
  zones, king tides, minor street flooding) are not in the model. They
  cause many small claims, and the 176 tracts with no modelled damage still
  have claims (median $2.5 per unit a year versus $13.3 where the model
  has damage).
- How we are fixing it: Stated as a limitation in the Stage 2 report. Not
  modelled in Phase 1.
- Decision: As above.
- Reason: The user's instruction.
- Evidence: `outputs/benefit/stage2/summary.json`
  (`claims_per_unit_zero_vs_positive_ead`).
- Affects: Stage 2 and Stage 4 interpretation.

### D-148. Stage 2 approved; whole-building damage as the high end; claims-trained model as the planned fix

- Date: 11 Nov 2026. Status: Final. Decided by: the user.
- What happened: The user approved Stage 2. They asked to keep the
  floors-reached rule (D-143) and also show the whole-building version.
- What is wrong: Readers should see both versions for tall buildings, and
  the missing rain and tidal flooding should be stated clearly.
- How we are fixing it:
  - The high end of every Stage 2 damage range now uses the curves' high
    band and, for apartments, commercial and public buildings, damage to
    the whole building. The middle and low figures keep the floors-reached
    rule. Houses (RES1) are unaffected.
  - County EAD today: low $94 million, middle $174 million, high $523
    million (it was $263 million). The ratio of the model to claims is now
    3.0 to 16.8 (middle 5.6).
  - Added to the limitations: 176 tracts with claims but no modelled
    damage show that rain and tidal flooding are missing. The planned fix
    is a flood damage model trained on the claims.
- Decision: As above.
- Reason: The user's instructions.
- Evidence: `scripts/benefit/baseline_risk.py` (`whole_building=(stat ==
  "high")`); `reports/benefit/stage2_baseline_risk.md`.
- Affects: Stage 2 ranges; Stage 4 avoided-loss ranges.


### D-149. Stage 3 sales: which sales, where they sit, and gaps filled

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The 2026 NAL holds two recent sales per parcel, all from
  2025 and 2026.
- What is wrong: The model needs one clean row per sale with a location and
  features.
- How we are fixing it:
  - Keep sale 1 and sale 2 when qualified (codes 01 and 02, D-121) and
    improved (VI_CD = I), for single-family homes (DOR_UC 001) and condo
    units (004). This gives 18,128 single-family and 23,770 condo sales.
  - Drop the lowest and highest 0.5% of prices in each group (single-family
    $225,000 to $17.97 million kept; condo $104,761 to $10.95 million), and
    rows with no living area or year built.
  - Location: a point inside the parcel the record sits on (condo units
    take their building's parcel, Stage 1). 580 sales could not be placed.
  - Final table: 40,901 sales (17,935 single-family, 22,966 condo).
  - 3,702 sales sit on parcels with no NSI building. They take flood zone,
    ground elevation, sea level rise and surge values from the nearest
    building (median 50 m away).
  - 8,357 sales are in block groups with no published family income. They
    take the tract average of its block groups (then the county median),
    and a flag marks them.
  - Block group median home value is not used: it is close to the outcome
    itself (leakage).
- Decision: As above.
- Reason: Uses only qualified market sales and keeps every gap visible.
- Evidence: `scripts/benefit/build_sales_features.py`;
  `outputs/benefit/stage3/build_log.json`.
- Affects: all Stage 3 models; Stage 4 property value change.

### D-150. Access layers: Miami-Dade open data for rail, schools and parks

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asks for distance to the coast, downtown,
  Metrorail stations, major parks and schools, using "public layers we have
  or can get". The TIGER landmark files on disk have no Metrorail stations,
  5 schools and 16 parks.
- What is wrong: The layers on disk are too thin.
- How we are fixing it:
  - Downloaded four layers from Miami-Dade County's open data portal
    (ArcGIS Online, publisher MDPublisher) on 11 Nov 2026, saved in
    `data/raw/mdc_layers/`:
    - Metrorail Station (23 stations);
    - Public School (451 sites);
    - County Park Boundary (309);
    - Municipal Park Boundary (563).
  - Major park: a park polygon of at least 10 acres (210 parks).
  - Downtown: the Government Center Metrorail station.
  - Coast: Census TIGER 2024 area water for bays, sounds and the ocean
    (MTFCC H2051 and H2053), already on disk.
- Decision: As above.
- Reason: Official county layers; the brief allows getting public layers.
- Evidence: `scripts/benefit/build_sales_features.py` (`access`).
- Affects: Stage 3 access features.

### D-151. Projects used for proximity: completed and ongoing, at a real place

- Date: 11 Nov 2026. Status: Provisional. Decided by: the user (completed
  and ongoing only); Amey (location rule).
- What happened: The SCALE-R database has 1,664 projects. Each has one
  point, but for municipality-wide and county-wide projects that point is
  only a stand-in for the whole area.
- What is wrong: Distance to a stand-in point says nothing about
  proximity.
- How we are fixing it:
  - Keep projects with status Completed or Ongoing.
  - Keep spatial resolution Parcel, Corridor or Neighborhood only.
  - Result: 969 projects (gray 800, hybrid 118, green 36, blue 15).
  - For each sale and each type: distance to the nearest project, and the
    number and dollars of projects within 500 m and 1 km.
- Decision: As above.
- Reason: Proximity only means something for projects tied to a place.
- Evidence: `outputs/benefit/stage3/projects_used.csv`.
- Affects: Stage 3 project features; Stage 4 uses the same rule.

### D-152. Stage 3 models and tests

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asks for OLS, MGWR and XGBoost, with spatial
  cross-validation as the main test and residual Moran's I.
- What is wrong: The setup needs fixing before the results are read.
- How we are fixing it:
  - Separate models for single-family homes and condos. Outcome: log sale
    price (main) and log just value (check).
  - Features:
    - structure: log living area, log lot size (single-family only), age
      and age squared;
    - month of sale;
    - eight block group ACS and vulnerability measures;
    - access: log distances to the coast, downtown, Metrorail, major parks
      and schools;
    - hazard: FEMA 100-year zone, ground elevation, sea level rise 3 and
      6 ft, Category 3 surge depth, Landsat surface temperature, and tract
      NFIP claims per unit;
    - projects (main): for each type, a flag for a project within 500 m
      and a flag for 500 m to 1 km.
  - OLS standard errors are clustered by tract.
  - Spatial cross-validation: the 10 tract folds from the ML work. Nested
    baselines: month mean only; plus structure; plus neighbourhood, access
    and hazard; plus projects.
  - XGBoost: same features (plus distance, count and dollar versions of
    the project features), same folds, fixed seed 20261111, xgboost 3.4.1
    in `.venv-ml`.
  - Residual Moran's I: 8 nearest neighbours, one value per location
    (condo units in one building share a point), 199 permutations.
- Decision: As above.
- Reason: Follows the brief and the project's ML practice.
- Evidence: `scripts/benefit/stage3_common.py`, `stage3_models.py`,
  `stage3_xgb.py`.
- Affects: Stage 3 results.

### D-153. MGWR: how the sample is drawn and what goes in

- Date: 11 Nov 2026. Status: Provisional. Decided by: the user (explain
  the sample; check two samples); Amey (details).
- What happened: MGWR cannot run on 18,000 sales in reasonable time.
- What is wrong: The sample and covariates must be stated and stable.
- How we are fixing it:
  - Single-family sales only. 2,000 sales drawn stratified by tract: each
    tract gives in proportion to its share of sales (at least one where it
    has any). Two samples, seeds 101 and 202.
  - The outcome is log price with month effects removed. All variables
    are standardised.
  - Covariates (final): log living area, log lot, age, log distance to the
    coast, ground elevation, and log distance (50 m to 5 km) to the nearest
    gray, hybrid and green project. The local intercept takes up
    neighbourhood price levels.
  - Left out: yes/no flags, which made local fits singular in a first
    attempt (stopped); the flood-zone flag, for the same reason; and blue
    projects, which are too few in a 2,000-sale sample.
  - Stability: bandwidths, coefficient spreads and the share of locally
    significant estimates are compared across the two samples, and local
    estimates are compared tract by tract where both samples have sales.
  - Two earlier full runs failed on inference. Their outputs are kept in
    `outputs/benefit/stage3/mgwr_first_run/` and `mgwr_second_run/`.
    - Run 1 also had distance to downtown and income, with no minimum
      bandwidth. Downtown shrank to 44 neighbours.
    - Run 2 set a minimum of 200 neighbours.
    - In both, the local standard errors were missing in one sample and
      enormous in the other, so no significance could be read.
    - A test on synthetic data showed the package works. The cause is local
      collinearity: with all covariates at 200 neighbours, the median local
      condition number was 48, and 61% of locations were above 30.
  - Final setup: distance to downtown and income dropped, and a minimum
    bandwidth of 500 neighbours (a quarter of the sample). Median local
    condition number 6.4; 2% of locations above 30.
  - In the final run the standard errors were finite but still enormous
    (median in the hundreds of thousands on standardised variables), so
    MGWR's own local significance tests cannot be used. Tests on synthetic
    data with UTM-sized coordinates gave correct standard errors, and the
    cause in our data was not found in reasonable time.
  - Therefore:
    - MGWR is used only to show how effects vary across the county;
    - that variation is tested by agreement between the two independent
      samples (tract Spearman 0.77 to 0.99);
    - all confidence intervals come from the OLS models;
    - the `sig_*` and `se_*` columns in the MGWR output files are not to
      be used.
  - Package: mgwr 2.2.1 (with spglm 1.1.0 and spreg 1.9.2), installed in
    `.venv` with the user's approval (D-158).
- Decision: As above.
- Reason: The user's instructions; a stable, documented sample.
- Evidence: `scripts/benefit/stage3_mgwr.py`.
- Affects: Stage 3 local results.

### D-154. When a project effect is "indicative" and when it is too uncertain

- Date: 11 Nov 2026. Status: Provisional. Decided by: the user (say where
  estimates are too uncertain); Amey (the rule).
- What happened: The brief asks for the value of being near each project
  type with intervals, and the user asked to say where estimates are too
  uncertain to use.
- What is wrong: A first rule (interval excludes zero in the main model)
  passed estimates that collapse once properties are compared within the
  same area.
- How we are fixing it: An effect is "indicative" only if all of these
  hold; otherwise it is "too uncertain to use":
  - at least 300 sales fall in the distance band;
  - the main model, the within-tract model and the within-block-group
    model give the same sign;
  - at least two of those three 95% intervals exclude zero.
- Decision: As above.
- Reason: Projects are not placed at random. An effect that only shows up
  without area controls is likely to be about the place, not the project.
- Evidence: `outputs/benefit/stage3/ols_project_effects.csv` (`verdict`).
- Affects: Stage 3 report; Stage 4 property value change (only indicative
  effects, with ranges).

### D-155. Bias checks, and why the before-and-after test cannot be done

- Date: 11 Nov 2026. Status: Final. Decided by: the user.
- What happened: All qualified sales in the 2026 NAL are from 2025 and
  2026.
- What is wrong: There are no sales from before most projects' document
  year, so the before-and-after comparison in the brief cannot be made.
- How we are fixing it:
  - Before-and-after: not done, stated plainly in the report.
  - Run instead:
    - (B) tract fixed effects: properties compared only with others in the
      same tract;
    - (C) block group fixed effects: the same within the block group;
    - (D) distance, count and dollar versions of the project features;
    - (E) just value as the outcome.
  - The report shows how much each estimate moves.
- Decision: As above.
- Reason: The user's instruction; the data allow nothing else.
- Evidence: `outputs/benefit/stage3/ols_project_effects.csv`.
- Affects: Stage 3 report.

### D-156. FHFA tract index check

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: The brief asks whether tracts with more projects saw
  faster value growth than similar tracts.
- What is wrong: The FHFA index has only 236 tracts with a 2024 value, and
  most projects were reported from 2020 on.
- How we are fixing it:
  - Outcome: index growth 2019 to 2024.
  - Projects: log(1 + number) of completed and ongoing projects in the
    tract (same rule as D-151), all types together and by type.
  - Controls ("similar tracts"): 2014 to 2019 growth, median family income,
    distance to the coast, and the share of buildings in the FEMA 100-year
    zone.
  - Robust standard errors. 223 tracts have all values.
- Decision: As above.
- Reason: The simplest fair comparison the data allow.
- Evidence: `scripts/benefit/stage3_models.py` (`fhfa_check`).
- Affects: Stage 3 report.

### D-157. Stage 3 MGWR uses log distance; Stage 4 recomputes value with distance

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (proposal; confirm).
- What happened: Stage 4 recomputes each parcel's value with a new
  project's distance.
- What is wrong: The yes/no band features cannot express a small change in
  distance, and MGWR needs continuous inputs.
- How we are fixing it: The OLS distance version (check D) and the MGWR
  log-distance coefficients are kept for Stage 4. Only effects rated
  indicative under D-154 will be used there, with their ranges.
- Decision: As above.
- Reason: Matches what Stage 4 must compute.
- Evidence: `outputs/benefit/stage3/ols_project_effects.csv` (spec D);
  `mgwr_seed*.csv`.
- Affects: Stage 4.

### D-158. mgwr package installed in the project environment

- Date: 11 Nov 2026. Status: Final. Decided by: the user (approved the
  install in `.venv` only).
- What happened: MGWR needs the `mgwr` package, which was not installed in
  either environment.
- What is wrong: Nothing may be installed without approval.
- How we are fixing it: `pip install mgwr==2.2.1` into the repository's
  `.venv` (not system-wide). It brought spglm 1.1.0 and spreg 1.9.2.
- Decision: As above.
- Reason: The user's approval.
- Evidence: this entry; `.venv` package list.
- Affects: `scripts/benefit/stage3_mgwr.py`.

### D-159. Stage 3 paused and kept as a draft after the professor's new specification

- Date: 11 Nov 2026. Status: Provisional. Decided by: the user (on the
  professor's specification).
- What happened: The professor sent a specification that changes the
  property value model. Its key variable must be flood risk (the Stage 2
  expected yearly damage), not distance to project types. Single-family
  homes and condos get separate MGWR models. Value change is computed as
  value x (exp(beta_flood x change in expected yearly damage) - 1).
- What is wrong: The Stage 3 model (D-149 to D-158) is built around
  distance to project types, so it does not match the new design.
- How we are fixing it: Stage 3 stops here. The existing scripts, outputs
  and report stay in the repository, marked as a draft, and are not used
  in Stage 4. Work resumes when the updated plan arrives.
- Decision: As above.
- Reason: The user's instruction.
- Evidence: this entry; the draft note at the top of
  `reports/benefit/stage3_property_model.md`.
- Affects: Stage 3 (to be redone); Stage 4 property value change.

### D-160. Ground elevation: USGS 3DEP 1 m recommended over the NOAA 3 m DEM (not switched yet)

- Date: 11 Nov 2026. Status: Provisional (waiting for the user). Decided by:
  Amey (recommendation); the user confirms.
- What happened: The professor's specification computes depth above the
  first floor from ground elevation, so the elevation source matters. The
  USGS 3D Elevation Program has a 1 m bare-earth DEM for Miami-Dade
  (project FL_MiamiDade_D23, lidar flown 27 Dec 2023 to 29 May 2024,
  published 15 Dec 2025, 57 tiles, 13.6 GB, NAVD88 metres). Our NOAA DEM is
  3 m, compiled in 2023 from 2015 and 2018 county lidar (NAVD88 metres,
  Geoid 12B).
- What is wrong: Nothing is wrong with the NOAA DEM on average, but it is
  6 to 9 years older and coarser.
- How we are fixing it: Compared both at 5,000 buildings (stratified by
  tract, seed 20261111). 3DEP minus NOAA: median -0.08 ft, middle half
  -0.25 to +0.12 ft, 3.1% of buildings differ by more than 1 ft and 1.6% by
  more than 2 ft. The 1 m point value and the 3 x 3 m mean give the same
  result, so resolution is not the cause; the date of the lidar is.
  The biggest gaps are new building pads on fill (3DEP up to 6 ft higher in
  Homestead and Hialeah) and spots where the NOAA DEM is far too high
  (14 to 19 ft on Key Biscayne, Miami Beach and Miami).
- Decision: Recommend switching to 3DEP 1 m for Module A. Not switched until
  the user confirms. The full 13.6 GB set is not downloaded (42 GB free on
  disk); it is read tile by tile over the web, as the NOAA DEM already is.
  To check before switching: the geoid model of the 3DEP heights (expected
  to differ from Geoid 12B by centimetres).
- Reason: Newer survey that shows current ground, finer cells, one
  consistent project, same vertical datum. County totals will barely move,
  but individual buildings, which the what-if tool works on, will.
- Evidence: `scripts/benefit/compare_dem.py`;
  `outputs/benefit/spec_alignment/dem_compare.json`, `dem_compare_by_place.csv`.
- Affects: Module A depth, Module B damage, first-floor elevation.

### D-161. FEMA flood risk products: no depth grids exist; the 2027 FIRM database used instead

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey.
- What happened: Searched FEMA's Map Service Center for Miami-Dade
  (county 12086C and community 120635) for the current maps (effective
  11 Sep 2009) and the new maps (effective 19 Feb 2027, confirmed by the
  pending FIRM database and the 8-volume Flood Insurance Study).
- What is wrong: Neither map set has a Flood Risk Database, depth grids or
  a Flood Risk Report on the Map Service Center.
- How we are fixing it: Downloaded the public 2027 FIRM database (199 MB)
  and Flood Insurance Study volume 1. Unlike the 2009 data we had, they hold
  water levels for five storm frequencies (10%, 4%, 2%, 1%, 0.2%):
  - coastal: still-water elevations at 218 transects (ADCIRC and SWAN
    surge model, 2018);
  - rainfall and canal flooding: water levels at 1,077 XP-SWMM model nodes
    (county basin models, 2007).
- Decision: Treat these as the frequency source for Module A in Part 2,
  pending the user's confirmation. They are points and transects, not
  grids, so a method for carrying them to each building is needed (to be
  proposed in Part 2).
- Reason: Best public multi-frequency data available now; it replaces the
  "0.2% equals 1% depth" lower bound (D-137).
- Evidence: `data/raw/fema/firm_2027/` (gitignored, logged in
  `benefit_download_log.json`).
- Affects: Module A, Module B.

### D-162. First-floor elevation estimated for every building

- Date: 11 Nov 2026. Status: Provisional (checked against the user's
  summary of the specification; the specification file itself is not yet in
  `docs/`). Decided by: the specification (ground plus typical floor height
  by building type and year built); Amey (the table).
- What happened: Module A needs first-floor elevation. No elevation
  certificates are available yet.
- What is wrong: Stage 2 used ground plus foundation height only, which
  ignores flood-zone building rules.
- How we are fixing it: Columns added to the buildings table:
  `ffe_ft_navd88`, `ffe_estimated` (1 for all 627,252), `ffe_rule`,
  `ffe_simple_ft_navd88`, `year_built_used` and its source. Rule:
  - typical floor height by foundation type, from NSI: slab 0.25 to 0.75 ft,
    crawlspace and solid wall 2 ft, pier or pile 5.25 to 6.25 ft (6.5 to
    9 ft in VE);
  - built after the first flood map (29 Sep 1972) inside zones A, AE, AH,
    VE: at least the base flood elevation (44 CFR 60.3);
  - built from 2012 (Florida Building Code 2010 edition): at least the base
    flood elevation plus 1 ft;
  - zone AO: ground plus zone depth.
  Year built is the tax roll value (97%) or the NSI block median. No
  building dropped; 33 with no ground value get the tract median.
- Decision: As above. 21,199 buildings are raised to the code level
  (median 1 ft). Buildings with a floor below the 1% flood level fall from
  49,766 to 31,019.
- Reason: Follows the specification and the national floodplain rules.
  Assumes full compliance with the current base flood elevation, which
  older maps may not have used.
- Evidence: `scripts/benefit/build_ffe.py`;
  `outputs/benefit/spec_alignment/ffe_summary.json`.
- Affects: Module A, Module B, building elevation projects in Module C.

### D-163. Tax roll fields for Module D tax revenue

- Date: 11 Nov 2026. Status: Final. Decided by: Amey.
- What happened: Module D needs homestead status, exemptions, assessed and
  taxable value.
- What is wrong: Nothing; the 2026 NAL has them.
- How we are fixing it: Fields:
  - homestead: `JV_HMSTD`, `AV_HMSTD` and exemption `EXMPT_01`
    (451,765 parcels, 48%);
  - assessed value: `AV_SD` (school) and `AV_NSD` (non-school; the 10%
    non-homestead cap applies here); the Save Our Homes cap shows as
    just value minus assessed value (median 49% of just value on homestead
    parcels);
  - taxable value: `TV_SD`, `TV_NSD`;
  - other exemptions: `EXMPT_02` to `EXMPT_82`; taxing district:
    `TAX_AUTH_CD`.
- Decision: Use these fields in Module D. Only aggregate counts were read;
  no owner fields.
- Reason: Official roll, same year as the sales.
- Evidence: `scripts/benefit/tax_fields_summary.py`.
- Affects: Module D tax revenue.

### D-164. Millage rates: 2026 adopted, by taxing district code

- Date: 11 Nov 2026. Status: Final. Decided by: Amey.
- What happened: The tax roll has no millage rates.
- What is wrong: Nothing.
- How we are fixing it: Downloaded the Property Appraiser's 2026 adopted
  millage chart and the DOR 2025 adopted file. Parsed all 38 codes into
  `data/reference/millage_2026_by_code.csv`. Every row's parts add up to
  its total; the DOR 2025 totals match the chart's 2025 column exactly; all
  38 tax roll codes have a rate.
- Decision: Use the 2026 adopted rates (14.90 to 24.19 mills). The school
  part (6.623 mills) applies to school taxable value, the rest to
  non-school taxable value.
- Reason: Same year as the tax roll; official.
- Evidence: `scripts/benefit/build_millage.py`; `millage_check.json`.
- Affects: Module D tax revenue.

### D-165. House features: what is free, what costs money

- Date: 11 Nov 2026. Status: Provisional. Decided by: Amey (nothing bought
  or downloaded).
- What happened: The specification's property model needs bedrooms,
  bathrooms, pool and waterfront.
- What is wrong: The tax roll has none of them.
- How we are fixing it:
  - Free: the county's official "Property Point View" layer
    (Property Appraiser data on the county open data site, 944,398
    folios). It has bedrooms, bathrooms, half bathrooms, floors, units,
    areas, year built and the latest sale date and price (any year). 99.9%
    of single-family homes and 93% of condos have bedrooms. It also holds
    owner names and addresses, so only the house fields would be requested.
  - Pool: no free field. Proxy: the tax roll's special features value
    (pools, docks, fences together). The Property Appraiser's bulk files
    cost $50 per file; custom files need a request.
  - Waterfront: no field; can be derived free from parcel and water
    polygons we already have.
- Decision: Recommend the free layer (house fields only) and a
  derived waterfront flag; ask the user before buying anything.
- Reason: Free official data covers most needs.
- Evidence: ArcGIS service `PaGISView_gdb` field list and counts (queried
  11 Nov 2026).
- Affects: Module D.

### D-166. Ground elevation switched to USGS 3DEP 1 m

- Date: 11 Nov 2026. Status: Final. Decided by: the user (switch after
  confirming the datum); Amey (method).
- What happened: The user approved D-160's recommendation, on condition
  that the vertical datum and geoid were confirmed first.
- What is wrong: Nothing. The datum is confirmed from the USGS final DEM
  report and the vendor metadata: NAVD88 (GEOID18), NAD83(2011), 10 cm
  RMSEz accuracy class. The NOAA DEM is NAVD88 (Geoid 12B); the median
  difference of -0.07 ft fits a geoid and survey-date difference.
- How we are fixing it: Sampled the 1 m cell under each of the 627,252
  buildings (5,578 blocks read over the web, 22 minutes). 626,519 from the
  1 m cell, 1 from the 3 x 3 m mean, 732 (water or gaps) keep the NOAA
  value, 3 with neither get the tract median. `ground_elev_ft_navd88` is
  now 3DEP; `ground_elev_ft_noaa` keeps the old value; `ground_source`
  says which.
- Decision: As above. First-floor elevations were rebuilt on the new
  ground. 3,345 post-2012 homes now need the code raise, down from 8,073,
  because 3DEP shows their lots already raised on fill.
- Reason: User approval; newer and finer survey.
- Evidence: `scripts/benefit/sample_3dep.py`, `ground_3dep_summary.json`;
  `data/raw/usgs_3dep/metadata/`.
- Affects: Modules A and B; first-floor elevation.

### D-167. FEMA 2027 map database is the main water-level source; 2009 maps for comparison

- Date: 11 Nov 2026. Status: Final. Decided by: the user.
- What happened: The user chose the 2027 FEMA database (5 frequencies,
  coastal and rainfall/canal) as the main source for Module A, with the
  2009 effective maps kept as a comparison.
- What is wrong: The rainfall and canal levels cover only the C-8 and C-9
  basins in the north of the county (75,117 buildings after the extent cap).
  Part 1 did not say so clearly; the Part 1 report is corrected. Elsewhere,
  inland 1% zones (mostly AH zones carried over from the 2009 study) have
  only a 1% level.
- How we are fixing it:
  - coastal levels countywide (5 frequencies);
  - rainfall and canal levels in C-8 and C-9 (5 frequencies);
  - elsewhere, the 2027 map's 1% flood elevation (68,031 buildings), with
    the 0.2% storm using the 1% level (lower bound, as D-137) and no damage
    assumed for the more frequent storms, which have no data there.
  - 2009 maps run through the same Modules A and B as a comparison.
- Decision: As above. Only the source data changed; it does not undo the
  user's decision.
- Reason: The user's decision; best public data available.
- Evidence: `module_config.json` (`sources`, `comparison_sources`);
  `water_level_methods.json`.
- Affects: Modules A and B.

### D-168. First-floor rule uses each community's initial FIRM date

- Date: 11 Nov 2026. Status: Final. Decided by: the user.
- What happened: The user asked to replace the county-wide 1972 date with
  each community's initial FIRM date from FEMA's NFIP Community Status
  Book (OpenFEMA).
- What is wrong: Nothing. All 35 Miami-Dade communities have an initial
  FIRM date of 29 Sep 1972; newer cities kept the county's date.
- How we are fixing it: Each building is placed in its NFIP community
  (2027 FIRM database polygons, 35 communities) and given that community's
  date (`nfip_cid`, `initial_firm_date`).
- Decision: As above. No floor changes in Miami-Dade, but the rule now
  follows the data.
- Reason: The user's instruction.
- Evidence: `data/raw/fema/community_status/csb_miami_dade.json`;
  `scripts/benefit/build_ffe.py`.
- Affects: First-floor elevation.

### D-169. House features downloaded without personal fields; pool data optional

- Date: 11 Nov 2026. Status: Final. Decided by: the user.
- What happened: The user approved downloading the county Property Point
  View layer, keeping only parcel ID, bedrooms, bathrooms, living area,
  sale price, sale date and qualification code.
- What is wrong: The layer has no qualification code.
- How we are fixing it:
  - only the kept fields are requested from the server, so owner names,
    addresses and coordinates are never sent, held or written; the script
    stops if any other field arrives;
  - 944,398 parcels in 29 seconds; 796,786 with bedrooms;
  - qualification code taken from the 2026 tax roll where the same sale is
    there (100,669 sales from 2021 on, all 2025 and 2026);
  - the layer gives each parcel's latest sale only. From 2021 to 2024 that
    adds 92,084 single-family and 115,821 condo latest sales, without a
    qualification code. The free DOR sales data files for earlier roll
    years have the codes; not downloaded (not named).
  - paid pool data skipped; logged as optional.
- Decision: As above.
- Reason: The user's instruction and privacy.
- Evidence: `scripts/benefit/download_pa_features.py`;
  `pa_features_summary.json`; `data/processed/benefit/pa_features.parquet`
  (gitignored).
- Affects: Module D.

### D-170. How FEMA 2027 water levels are carried to buildings

- Date: 11 Nov 2026. Status: Provisional (recommended; the user asked for a
  recommendation before use). Decided by: Amey.
- What happened: The 2027 levels are at 218 coastal transects and 1,077
  canal model nodes, not grids.
- What is wrong: A method is needed to give each building a level.
- How we are fixing it: Compared methods against the 2027 base flood
  elevation of the zone each building sits in, and against FEMA's mapped
  flood extent:
  - coastal, nearest transect: 82% of buildings within 1 ft of the zone's
    1% elevation; 7.6% of minimal-hazard buildings wrongly below the 1%
    level;
  - coastal, interpolation along the shoreline: 77% within 1 ft; 10.2%
    wrongly wet;
  - rainfall, the node of the building's own subbasin: 100% within 0.5 ft;
  - rainfall, nearest node: 96.5%; 3-node average: 97%.
  Filling the land to the water level also wet buildings FEMA maps as
  outside the floodplain (45,000 in the 0.2% zone at 1%; 30,000 outside
  both zones at 0.2%). So each storm's levels are limited to FEMA's mapped
  extent: the 1% zone for the 1% storm and more frequent ones, and the 1%
  plus 0.2% zones for the 0.2% storm. With sea level rise, NOAA's
  inundation area for that rise is added to the extent; this adds only 75
  to 6,720 buildings, so most future spread beyond today's floodplain is
  not captured.
- Decision: Coastal: nearest transect. Rainfall: own subbasin node. Extent
  cap on. The coastal levels are still water and leave out wave height,
  which the coastal base flood elevations include.
- Reason: Best agreement with FEMA's own mapped elevations and extent.
- Evidence: `scripts/benefit/compare_water_levels.py`,
  `water_level_methods.json`; `module_a_summary.json`.
- Affects: Modules A, B and C.

### D-171. Module B expected yearly damage: rule and range

- Date: 11 Nov 2026. Status: Provisional. Decided by: the specification
  (formula); Amey (range, tail).
- What happened: The specification gives
  EYD = sum 0.5 x (L_i + L_i+1) x (p_i - p_i+1), with loss 0 at the most
  frequent storm that causes no damage.
- What is wrong: The formula stops at the rarest storm; the specification
  also asks for a wider range where the floor is estimated.
- How we are fixing it:
  - EYD as written, over 10%, 4%, 2%, 1% and 0.2%; rarer storms never do
    less damage at a building; the part beyond 0.2% (loss x 0.002) is
    reported separately;
  - low: low curve band, estimated floors 1 ft higher;
  - high: high curve band, whole-building damage for non-house buildings
    (D-148), estimated floors 1 ft lower;
  - mid: mean curve; floors-reached rule kept (D-143);
  - displacement reported separately.
- Decision: As above. County EYD: $318M low, $701M mid, $1,925M high a
  year, plus $153M beyond the 0.2% storm. That is four times the Stage 2
  figure ($174M). The rise comes from:
  - the 2027 maps' higher and wider 1% levels;
  - real 0.2% levels, where Stage 2 copied the 1% depth;
  - three more frequent storms.
  The provisional claims ratio for all buildings rises to 27.9 (Stage 2:
  5.6), and for residential buildings to 16.9 (Stage 2: 3.1). Tract rank
  agreement falls to 0.35 (Stage 2: 0.49). Not tuned; final calibration
  waits for the policies file.
- Reason: Follows the specification.
- Evidence: `scripts/benefit/module_b_eyd.py`; `module_b_summary.json`,
  `module_b_breakdown.json`.
- Affects: Module C, benefit per dollar.

### D-172. Module C: seawall and building elevation; building ID is fd_id

- Date: 11 Nov 2026. Status: Provisional. Decided by: the specification;
  Amey (the "behind the alignment" rule).
- What happened: The specification asks for seawall and building
  elevation first, each returning results in seconds.
- What is wrong: "Behind the alignment" needs a working rule. Also the
  `bid` column is not unique (47,994 blank, 105,275 repeated).
- How we are fixing it:
  - seawall: a building is behind the wall if the straight line from it to
    its nearest point on the coastal shoreline (the FEMA transect baseline)
    crosses the wall (5 m tolerance), it is within 2 km of the shoreline,
    and its ground is below the crest. For those buildings, coastal water is
    removed for every storm whose coastal level (with sea level rise) is
    below the crest. Overtopping storms keep their full depth. Rainfall is
    unchanged. Water going round the ends is not stopped;
  - building elevation: the first floor of the selected buildings is
    raised by X ft;
  - only affected buildings are recomputed: 0.02 to 0.07 seconds per
    scenario, after a 0.2 second model load;
  - pumps and drainage, buyout and green stormwater are placeholders;
  - every module table is keyed by `fd_id`, which is unique.
- Decision: As above.
- Reason: The specification; a rule that is simple to explain.
- Evidence: `scripts/benefit/module_c_projects.py`; `module_c_examples.json`.
- Affects: Module C; Module D will read the change in EYD.

### D-173. Coastal water levels anchored to FEMA's mapped 1% elevation at each building

- Date: 12 Nov 2026. Status: Provisional (recommended in D-174). Decided by:
  the user (anchor to the mapped 1% elevation, transect curve for the
  differences only); Amey (VE and AE handling).
- What happened: The user asked to anchor coastal levels to the 2027 mapped
  1% elevation at each building. The transect frequency curve is used only
  for the step from the 1% level to the 10%, 4%, 2% and 0.2% levels. The
  0.2% mapped extent applies to the 0.2% storm. Wave-inclusive and
  still-water levels must not be mixed.
- What is wrong: Mapped 1% elevations include waves where waves matter;
  transect levels are still water. In Miami-Dade:
  - coastal AE zones sit a median 0.3 ft above the nearest transect still
    water (middle half 0 to 0.6 ft), so they are almost still water;
  - VE zones sit a median 10 ft against still water of about 6.7 ft, so
    they carry about 3 ft of wave crest.
- How we are fixing it:
  - AE and AH zones from the coastal studies (STUDY5, STUDY6): the mapped
    elevation is the still-water 1% anchor; the small wave part (about
    0.3 ft) is kept and stated;
  - VE (129 buildings): the wave crest is removed with FEMA's depth-limited
    breaking wave rule (crest = still water + 0.55 x still-water depth), so
    still water = (BFE + 0.55 x ground) / 1.55. Each storm is shifted in
    still water, then the waves are added back with the same rule;
  - AO: ground plus zone depth;
  - 0.2% zone (shaded X): the mapped elevation of the nearest coastal AE
    zone, plus the transect step to 0.2%. The extent cap keeps these
    buildings dry for the 1% and more frequent storms;
  - combined coastal and canal zones in C-8 and C-9 (STUDY7), zone A and
    the minimal zone: no anchor; nearest-transect still water as D-170. The
    canal model already matches the mapped elevation there;
  - each storm = anchor + (transect level for that storm - transect 1%
    level), from the nearest transect.
  Anchor types: 176,680 mapped elevation, 142,965 nearest AE, 129 VE,
  48 AO, 182,283 no anchor (most outside the mapped extent).
- Decision: As above; the D-170 transect method is kept as a comparison
  source.
- Reason: The user's instruction; consistent with FEMA's map at each
  building and no mixing of wave and still-water levels.
- Evidence: `scripts/benefit/water_levels.py` (`coastal_anchored`);
  `module_config.json`; `module_a_summary.json`.
- Affects: Modules A, B and C.

### D-174. Three versions compared with NFIP claims; anchored version recommended

- Date: 12 Nov 2026. Status: Provisional (waiting for the user). Decided
  by: Amey (recommendation); nothing tuned to claims.
- What happened: The user asked to compare Stage 2, the transect method
  (D-170) and the anchored method (D-173) with claims, on totals and tract
  ranking, without tuning.
- What is wrong: All three overstate claims (insured, paid losses), as
  expected. The two new versions overstate much more, and they rank tracts
  less well than Stage 2.
- How we are fixing it: Same footing for all three: structure and
  contents, including the part beyond the rarest storm, no displacement;
  694 tracts with 50+ occupied homes. Results:

  | | Stage 2 | Transect | Anchored |
  |---|---|---|---|
  | County, $M per year | 164 | 854 | 889 |
  | Model to claims, all | 5.3 | 27.9 | 29.0 |
  | Model to claims, residential | 2.9 | 16.9 | 16.5 |
  | Tract ranking (Spearman) | 0.49 | 0.35 | 0.35 |
  | Tracts with claims but no damage | 170 | 61 | 60 |

  The anchored version's frequent storms alone (10% to 2%) give $187M,
  6.1 times claims, close to Stage 2's ratio. The rare storms (2% to 0.2%),
  which the 1978 to 2025 claims barely sample, make the rest. The ranking
  stays near 0.30 even for frequent storms, because damage concentrates on
  the coast while 94% of claims come from tracts without rainfall levels
  (D-175).
- Decision: Recommend the anchored version for the tool:
  - it follows the specification (five storms) and matches FEMA's map at
    every building, with waves handled;
  - its frequent-storm level is in line with Stage 2 against claims;
  - its lower ranking comes from the missing inland rainfall, which no
    version fixes.
  Stage 2 stays as a benchmark. Final calibration waits for the policies
  file.
- Reason: Specification; FEMA consistency; no tuning.
- Evidence: `scripts/benefit/compare_versions.py`;
  `version_comparison.json`, `version_comparison.csv`.
- Affects: Modules B and C; Module D flood variable.

### D-175. Inland rainfall gap recorded as a known undercount

- Date: 12 Nov 2026. Status: Final (as a limitation). Decided by: the user.
- What happened: Rainfall levels for the 10%, 4% and 2% storms exist only
  in the C-8 and C-9 basins.
- What is wrong: Outside them, frequent rainfall floods count as zero.
- How we are fixing it: Measured and reported:
  - outside C-8 and C-9: 535,228 buildings and 2.49 million residents
    (240,537 buildings and 1.20 million residents in the 1% zone);
  - map only (1% zone, only the 1% level): 68,031 buildings, 257,725
    residents;
  - coastal storms counted, rainfall missing: 312,340 buildings, 1.54
    million residents;
  - no flood source at all: 154,857 buildings, 689,730 residents;
  - 93.9% of claims come from tracts mostly outside C-8 and C-9.
- Decision: Reported as a known undercount until countywide rainfall depth
  outputs arrive (requested); a claims-trained flood model remains the
  planned fix (Stage 2 limitation).
- Reason: The user's instruction.
- Evidence: `scripts/benefit/inland_gap.py`; `inland_gap.json`.
- Affects: Modules B and C; claims check.

### D-176. DOR sales files: only 2025 and 2026 are online

- Date: 12 Nov 2026. Status: Provisional (waiting for the user). Decided
  by: the user (download 2021 to 2024, non-personal fields only).
- What happened: The user approved downloading the free DOR sales data
  files (SDF, with qualification codes) for 2021 to 2024.
- What is wrong: The DOR data portal holds only the current roll year: the
  SDF folder has 2026F and 2026P only (checked through the portal's file
  listing). The 2026 final file covers sales in 2025 and 2026, so it adds
  nothing before 2025. Earlier years must be requested from DOR
  (PTOTechnology@floridarevenue.com), which is an email the user must send
  or approve.
- How we are fixing it: Downloaded the 2026 final SDF (125,117 sales). It
  holds no owner names or addresses. Kept parcel ID, use code,
  qualification code, vacant/improved code, sale year, month and price,
  multi-parcel flag and sale ID code. All parcels match the tax roll; it
  confirms the qualification code for 103,099 latest sales in the county
  house layer (2025 and 2026).
- Decision: Stop here and report. The 2021 to 2024 sales still lack
  qualification codes.
- Reason: Only data the user named; no emails sent without approval.
- Evidence: `scripts/benefit/build_sdf_sales.py`; `sdf_sales_summary.json`.
- Affects: Module D sales sample.

### D-177. Benchmark against FEMA's National Risk Index (flood only)

- Date: 12 Nov 2026. Status: Final (benchmark; nothing tuned). Decided by:
  the user.
- What happened: The user asked for a comparison with the NRI's expected
  annual loss to buildings from coastal and inland flooding (December 2025,
  `fema_miami_dade_dec_2025.csv`), excluding hurricane wind.
- What is wrong: The two disagree on where flood losses are. NRI puts
  $269M a year on inland flooding and $18M on coastal flooding. Our model
  puts almost all of its damage on the coast.
- How we are fixing it: Compared 706 tracts, totals and ranking (loss per
  dollar of building value):

  | | Total, $M a year | Ranking against NRI flood | Ranking against NFIP claims |
  |---|---|---|---|
  | NRI coastal + inland | 287 | n/a | 0.25 |
  | Anchored (structure + contents) | 889 | 0.02 | 0.35 |
  | Anchored, structure only (NRI counts buildings) | 463 | 0.06 | n/a |
  | Frequent storms only (10% to 2%) | 187 | -0.08 | 0.30 |
  | Stage 2 | 164 | -0.02 | 0.49 |

  Against NRI coastal flooding alone: anchored 0.14, frequent 0.28, Stage 2
  0.65.
- Decision: Report it. NRI ranks NFIP claims less well (0.25) than our
  anchored model (0.35), so it is a check on totals, not a target. The
  totals bracket NRI ($187M to $463M against $287M). NRI's large inland
  flood figure supports the missing inland rainfall (D-175).
- Reason: The user's instruction; no tuning.
- Evidence: `scripts/benefit/nri_benchmark.py`; `nri_benchmark.json`,
  `nri_benchmark_tracts.csv`.
- Affects: Interpretation of Module B.

### D-178. Module D sales samples

- Date: 12 Nov 2026. Status: Provisional. Decided by: the user (main and
  test samples); Amey (variables).
- What happened: Until DOR's 2021 to 2024 files arrive, the 2025 and 2026
  qualified sales are the main sample, and the house layer's 2021 to 2024
  latest sales are a test.
- What is wrong: No pool field is free (D-165), and older sales lack
  qualification codes.
- How we are fixing it: Specification variables:
  - log price;
  - flood risk = anchored EYD in $1,000s per property, including the part
    beyond the 0.2% storm (condos: the parcel's damage split by unit just
    value);
  - living area; lot (single-family); age; bedrooms; bathrooms
    (full + half x 0.5);
  - pool proxy (single-family: special features value above 0, which also
    counts docks and fences);
  - waterfront (parcel within 10 m of FEMA water or open water);
  - log distance to water; ground elevation (3DEP); time (sale year +
    month).
  Main: 17,935 single-family and 22,966 condo sales.
- Decision: As above.
- Reason: Specification D1 and D2.
- Evidence: `scripts/benefit/module_d_prepare.py`; `prepare_log.json`.
- Affects: Module D.

### D-179. Non-market rule for 2021 to 2024 latest sales

- Date: 12 Nov 2026. Status: Provisional. Decided by: Amey (stated before
  fitting; not tuned on the model).
- What happened: The house layer's latest sales have no qualification code.
- What is wrong: Many are not arm's-length (family transfers, nominal
  prices).
- How we are fixing it: A sale is kept only if all hold:
  - price at least $50,000;
  - price divided by the 2026 just value (moved back to the sale year with
    FHFA's county index) inside the 2.5th to 97.5th percentile of the same
    ratio in the qualified 2025 to 2026 sales (single-family 0.92 to 1.73;
    condo 0.97 to 1.64);
  - price per square foot (in 2025 dollars) inside the 0.5th to 99.5th
    percentile of the qualified sales (single-family $171 to $2,251;
    condo $133 to $2,645);
  - living area and year built present, not sold before built.
  Single-family: 92,084 to 41,729 (44,553 below $50,000). Condo: 115,821
  to 57,824 (37,804 below $50,000).
- Decision: As above; results reported with and without them.
- Reason: A simple, stated rule that removes nominal and outlying prices.
- Evidence: `prepare_log.json` (`older_rule`).
- Affects: Module D test sample.

### D-181. NFIP policies: full file downloaded and checked; claims check per insured home

- Date: 12 Nov 2026. Status: Final (download); Provisional (check).
  Decided by: the user.
- What happened: The user asked for a resumable download of the full
  `NfipPoliciesV3.parquet`, checked against FEMA, filtered to Miami-Dade,
  and a claims check per insured building.
- What is wrong: Nothing with the file. The user's own browser copy in
  Downloads is complete too (same size), not partial, so it was not
  deleted.
- How we are fixing it:
  - downloaded with `curl -C -` and retries: 3,713,009,365 bytes,
    matching FEMA's Content-Range; MD5 275e07e99258e4ff7684cf4505f91406,
    matching FEMA's ETag; SHA-256 recorded;
  - filtered to censusGeoid starting 12086: 3,317,242 policy records
    (2009 to 2026); 20 non-identifying fields kept;
  - residential policy-years about 340,000 to 355,000 a year; take-up
    (policy-years / occupied homes, 2015 to 2025) 35.5% county-wide,
    against 20.3% implied in Stage 2's gap breakdown;
  - modelled insured loss = residential damage x tract take-up x paid-to-
    damage ratio (0.906): anchored $153M against claims $30.3M (5.0 times),
    tract ranking 0.46 (0.39 to 0.51); Stage 2 $44M (1.45 times), ranking
    0.52;
  - floor height from policy elevation fields (lowest floor minus lowest
    adjacent grade, block-group medians only): median 1.1 ft (0.9 to
    1.5 ft), higher than our slab heights (0.25 to 0.75 ft).
- Decision: Use measured take-up in the calibration. The floor-height
  finding suggests our damage is too high; report it, and propose using the
  block-group medians for estimated floors in a later step (not done here,
  to avoid changing Module B now).
- Reason: The user's instruction.
- Evidence: `scripts/benefit/nfip_policies.py`; `nfip_policies_check.json`,
  `nfip_floor_height_by_bg.csv`; `data/raw/fema/nfip_policies_full/md5.txt`.
- Affects: Module B calibration.

### D-180. Module D model set-up: OLS benchmark and MGWR on 5,000 sales per model

- Date: 12 Nov 2026. Status: Provisional. Decided by: the specification
  (D1 to D4); Amey (sample size, bandwidth floor, details).
- What happened: The specification asks for separate single-family and
  condo models, OLS first, MGWR on 10,000 to 30,000 sales per model,
  coefficients stored on every building, and held-out error.
- What is wrong:
  - MGWR's time and memory grow with the square of the sample; 2,000 sales
    took 3 to 17 minutes in Stage 3, and this machine has 17 GB of memory.
  - In Stage 3, small local windows made local fits unstable (D-153).
  - Yes/no controls (waterfront, pool proxy) are all zero in many local
    windows, which made the first runs singular.
- How we are fixing it:
  - 20% of main-sample sales held out (random within tracts, seed
    20261112); OLS on all other main sales (tract-clustered errors);
  - MGWR on a tract-stratified sample of 5,000 of them (below the
    specification's 10,000 to 30,000; a larger run is possible overnight);
  - bandwidth floor 500 neighbours; waterfront and pool proxy held
    countywide; backfitting starts from a countywide regression;
  - local coefficients converted to original units around the sample
    means, so each can be carried to new points on its own bandwidth
    (bisquare kernel, specification route 2) for held-out sales and for
    every building;
  - variants (frequent-storm flood variable; with 2021 to 2024 sales) refit
    with the main bandwidths held fixed.
- Decision: As above.
- Reason: Feasible on this machine; follows the specification otherwise.
- Evidence: `scripts/benefit/module_d_fit.py`; `outputs/benefit/module_d/*.json`.
- Affects: Module D.

### D-183. The flood coefficient has the wrong sign for single-family homes

- Date: 12 Nov 2026. Status: Open (needs the user and the professor).
  Decided by: nobody yet; stopped and reported.
- What happened: The single-family models give a positive flood
  coefficient: higher expected yearly damage goes with higher prices.
  - OLS: +1.6% per $1,000 (0.4% to 2.8%);
  - MGWR: median +1.3%, with only 12% of locations negative;
  - within tracts +0.4%; within block groups +0.5%; more than 1 km from
    water +3.0%.
  Condos: OLS -1.2% (-2.0% to -0.3%), but about 0 within tracts.
- What is wrong: With a positive coefficient, the value-change formula says
  flood protection lowers home values. The cause is mostly mechanical:
  damage in dollars grows with the home's own value (bigger homes have more
  to lose). With damage per $100,000 of structure value instead, the
  single-family effect is -0.06% per $100 a year (-0.39% to +0.26%),
  that is, no clear effect. Condos show -4.8% (-6.0% to -3.6%) across the
  county, but +0.9% within tracts.
- How we are fixing it: Not fixed. The results are reported, and the
  value change is shown for the test scenarios only to show what the
  formula gives.
- Decision: Waiting for the user. Options in the report:
  1. flood variable as a damage rate (per $100,000 of value), not dollars;
  2. use only local coefficients that are negative and significant, else 0;
  3. a published flood discount as an assumption until the before-and-after
     check (D6) can be run with 2021 to 2024 qualified sales.
- Reason: The rule to stop and report when results contradict expectations.
- Evidence: `scripts/benefit/module_d_sign_check.py`; `sign_check.json`;
  `single_family_main.json`.
- Affects: Module D value change and tax change.

### D-182. Module D value and tax change: method, and what the current coefficients give

- Date: 12 Nov 2026. Status: Provisional (method); results not usable until
  D-183 is settled. Decided by: the specification (D4, D5, D7); Amey
  (details).
- What happened: The specification asks for coefficients on every building,
  value change = value x (exp(beta x delta EYD) - 1) with a beta +/- 2 SE
  range, and tax change in year 1 and year 10 under Florida's caps.
- What is wrong: With the current (mostly positive) coefficients, the
  formula gives value losses from flood protection:
  - seawall (8 ft, North Miami): -$15.2M (-$35.9M to +$6.9M) with the main
    model; -$4.7M with the frequent-storm model (0.31 times);
  - elevation (3 ft, Princeton): -$20.3M (-$72.2M to +$34.6M) main;
    -$20.9M frequent (1.03 times).
  When carried to buildings, the coefficients also stretch beyond the
  calibration range in places (condo median +8% per $1,000).
- How we are fixing it: Method in place and tested:
  - coefficients and standard errors stored on 383,978 single-family and
    103,882 condo buildings;
  - value = 2026 just value allocated to the building; condo damage change
    split equally across units;
  - tax: Save Our Homes (2.9%, the lower of 3% and CPI) for homesteads;
    10% cap on non-school levies for others; school levies on just value;
    2026 exemptions and millage; 3% market growth; no sales in 10 years.
- Decision: Keep the method. Do not use the value or tax results until the
  flood variable is settled (D-183).
- Reason: Specification; the stop-and-report rule.
- Evidence: `scripts/benefit/module_d_value_tax.py`; `value_tax_examples.json`.
- Affects: Module D; benefit per dollar (tax part).

### D-184. Module D flood variable: damage rate instead of dollars (change from the specification)

- Date: 12 Nov 2026. Status: Final (choice); results in D-187. Decided by:
  the user (option 1 of D-183; option 2 rejected).
- What happened: The specification's flood variable is expected yearly
  damage in dollars. With it, the single-family coefficient was positive,
  because dollar damage grows with the home's own value (D-183).
- What is wrong: The dollar variable partly measures house size and quality,
  so its coefficient is not a clean flood effect.
- How we are fixing it:
  - flood variable = expected yearly damage per $100,000 of building value
    (NSI structure value of the buildings on the parcel), in units of $100
    a year per $100,000 (0.1% of the building's value a year);
  - condos: the rate is the same for every unit on the parcel (damage and
    value both split by unit), so no unit split is needed;
  - main: anchored damage (D-174) including the tail; sensitivity: storms
    10% to 2% only; the dollar variable is refitted for comparison;
  - value change keeps the specification's form in the new unit:
    value_change = value x (exp(beta_rate x delta_rate) - 1), where
    delta_rate = change in the building's yearly damage / its structure
    value x 1,000 (same unit as the model);
  - option 2 (keep only negative significant local coefficients) is not
    used.
- Decision: Damage rate is the main Module D flood variable. Logged as a
  change from the specification (D2, D5).
- Reason: The user's decision; removes the mechanical link between dollar
  damage and home value.
- Evidence: `scripts/benefit/module_d_prepare.py`, `module_d_fit.py`,
  `module_d_value_tax.py`.
- Affects: Module D coefficients, value change and tax change.

### D-185. First-floor heights from NFIP policy elevation fields by block group and building type

- Date: 12 Nov 2026. Status: Provisional. Decided by: the user (method);
  Amey (details).
- What happened: The policies' elevation fields gave a median floor height
  of 1.1 ft above the ground, above our NSI slab heights (0.25 to 0.75 ft)
  (D-181). The user asked to use them, as block-group summaries by building
  type, and to rerun Modules A and B.
- What is wrong: The fields are almost all from policies in zones AE and
  AH, so X-zone buildings have little direct evidence. Each building
  appears once per policy year.
- How we are fixing it:
  - floor height = lowest floor elevation minus lowest adjacent grade,
    kept between -5 and 20 ft; records collapsed to one per building with a
    proxy key held in memory only;
  - four building types from NFIP occupancy and from NSI occupancy:
    single-family, multi-family and condo, mobile home, non-residential;
  - median by block group and type where at least 10 buildings; tract and
    type below that; county by type otherwise; only these summaries are
    written;
  - slab buildings take the median; crawlspace, wall, pier and pile
    buildings keep the NSI height where higher; the code rule (BFE from
    1973, BFE + 1 ft from 2012) applies on top as before; the old result
    is kept as ffe_nsi_ft_navd88; every floor stays estimated
    (ffe_estimated = 1) and keeps the +/-1 ft low and high cases.
- Results:
  - 435,667 building records after collapsing policy years; medians:
    single-family 1.1 ft, multi-family 1.0 ft, non-residential 0.8 ft,
    mobile home 2.9 ft; summaries for 1,484 block groups (single-family);
  - source per building: block group 328,491, tract 66,725, county
    94,785, NSI kept (higher) 137,251; slab median 0.75 to 1.1 ft;
    first floors raised a median 0.35 ft (76% raised, 0.6% lowered);
  - county expected yearly damage (mid): $745M to $550M; with the tail
    $889M to $672M; low $320M to $222M; high $2,217M to $1,800M;
  - claims check: all buildings 29.0 to 22.1 times claims, tract ranking
    0.345 to 0.338; insured part (measured take-up) 5.0 to 3.9 times,
    ranking 0.46 to 0.44; NRI totals ratio 3.1 to 2.3 times.
- Decision: Use the policy-based floor heights in Modules A and B.
- Reason: Measured floor heights in Miami-Dade are better evidence than
  national foundation defaults.
- Evidence: `scripts/benefit/nfip_floor_heights.py`, `build_ffe.py`;
  `nfip_floor_height_summary.csv`, `ffe_summary.json`.
- Affects: Modules A to D, every damage total and the claims comparison.

### D-186. MGWR on every training sale (specification size)

- Date: 12 Nov 2026. Status: Provisional. Decided by: the user (size);
  Amey (details).
- What happened: The user asked for MGWR with the specification's 10,000 to
  30,000 sales per model, run overnight.
- What is wrong: Nothing. The training sales (2025 and 2026 qualified, 80%
  not held out) are about 14,000 single-family and 18,000 condo, inside the
  specification's range, so no sampling is needed.
- How we are fixing it:
  - all training sales used (cap 30,000); same hold-out as before;
  - bandwidth floor kept at 500 neighbours (instability in Stage 3 came
    from the number of neighbours, not the share of the sample); yes/no
    controls held countywide as before;
  - the final fit runs in chunks to limit memory; 8 parallel workers;
  - variants (frequent storms, dollar variable, with 2021 to 2024 sales)
    reuse the main bandwidths; the 2021 to 2024 variant keeps the main
    model's sample size so only the sales mix changes;
  - the 5,000-sale results stay in `outputs/benefit/module_d/`; the large
    runs go to `outputs/benefit/module_d/large/`.
- Decision: Run both segments on every training sale.
- Reason: The specification and the user's instruction.
- Evidence: `scripts/benefit/module_d_fit.py`.
- Affects: Module D coefficients.

### D-187. Main flood result from the data, with a labelled published-discount scenario

- Date: 13 Nov 2026. Status: Final. Decided by: the user.
- What happened: The single-family MGWR and block-group fixed-effects
  models both put the price effect of the flood damage rate at about zero
  (fixed effects: -0.03% per unit, 95% range -0.16% to +0.11%). The user
  asked how to report this, given that published studies find flood
  discounts.
- What is wrong: Nothing in the data. An effect near zero is consistent
  with the research finding that flood risk is often underpriced in
  housing markets, especially where buyers are not told about it.
- How we are fixing it:
  - the data-based estimate (about zero, with its 95% range) is the main
    result for single-family and condo;
  - a separate scenario, labelled as an assumption and not an estimate,
    applies published discounts: Fu and Nijman (2021), 3% for the FEMA
    100-year floodplain in coastal Miami-Dade (central case); Beltran,
    Maddison and Elliott (2018), 4.6% (meta-analysis); Bernstein,
    Gustafson and Lewis (2019), 7% (exposure to sea level rise). Each
    discount is turned into a coefficient on our damage rate by dividing
    ln(1 - discount) by the gap in mean damage rate between buildings
    inside and outside the 2027 1% zone, per segment;
  - value and tax change for the two test projects are shown for the
    main estimate, the fixed-effects estimate and each published scenario;
  - the underpricing literature is cited in the report.
- Decision: As above.
- Reason: The user's instruction. The main result must come from the
  data; the published values show what the benefit would be if buyers
  priced flood risk as other studies found.
- Evidence: `outputs/benefit/module_d/fe_block_group.json`,
  `scripts/benefit/module_d_value_tax.py` (PUBLISHED, published_coefficients).
- Affects: Module D report, value and tax results.

### D-188. Which MGWR runs are full size

- Date: 12 Nov 2026. Status: Final. Decided by: the user.
- What happened: The full-size plan (D-186) fitted all eight models (two
  segments, main plus three variants) on every training sale. MGWR's work
  grows with the square of the sample, so the estimate was about 15 hours.
- What is wrong: The dollar-variable and 2021 to 2024 comparisons are
  checks, not inputs to the value change, and took about 6 of those hours.
- How we are fixing it:
  - full size (every training sale): the single-family and condo main
    models (damage rate) and the frequent-storm variant;
  - 5,000 sales (as in D-180): the dollar-variable and 2021 to 2024
    comparisons, with their own 5,000-sale main model for the bandwidths,
    in `outputs/benefit/module_d/n5000/`;
  - the single-family main run that was already going was not restarted;
    only the queue of later runs was replaced;
  - the value and tax step uses full-size coefficients where they exist
    and the 5,000-sale ones for the dollar comparison, and records which.
- Decision: As above.
- Reason: The user's choice, to finish overnight; a GPU would not help
  because the `mgwr` package runs on ordinary processors only.
- Evidence: `scripts/benefit/module_d_fit.py`,
  `scripts/benefit/module_d_value_tax.py`.
- Affects: Module D run time; how comparable the comparison runs are with
  the main runs (smaller sample).

### D-189. MGWR runs on all 10 processor cores

- Date: 13 Nov 2026. Status: Final. Decided by: the user (use all cores if
  the results are identical); Amey (test and settings).
- What happened: The full single-family main model (D-186) had run for
  about 13 hours against an estimate of about 2, using roughly one of the
  machine's 10 cores.
- What is wrong: The run time made the full-size plan impractical.
- How we are fixing it:
  - the installed `mgwr` (2.2.1) spreads the local fits over worker
    processes through its `n_jobs` option (the older `pool` option no
    longer does anything); the fit script now sets `n_jobs` for both the
    bandwidth search and the final fit (`MGWR_JOBS`, -1 = all cores) and no
    longer opens the unused pool;
  - test on 1,500 single-family sales, all cores against one core: the
    same bandwidths and the same AICc; local coefficients and standard
    errors differ by less than 0.000000000000002 (rounding only);
  - speed: at 1,500 sales all cores was slower (238 against 180 seconds,
    the cost of handing out many small jobs); at 10,000 sales one local
    fit took 0.4 seconds on all cores against 0.8 on one, so about twice
    as fast at the size used;
  - the search now prints each backfitting round, so progress can be seen;
  - the full single-family main model already running was left alone.
- Decision: Run every remaining model on all 10 cores.
- Reason: Identical results, about half the time at 10,000 sales.
- Evidence: `scripts/benefit/module_d_fit.py`; test scripts and outputs in
  the session scratchpad (`par_test.py`, `par_unit.py`).
- Affects: Module D run time only, not results.

### D-190. Remaining MGWR models at 10,000 sales

- Date: 13 Nov 2026. Status: Provisional. Decided by: the user (size);
  Amey (details).
- What happened: Replaces the run plan in D-188. The full single-family
  main model (all 14,350 training sales; the 30,000 in D-186 is only a
  cap) had not finished after about 13 hours.
- What is wrong: At that pace the remaining full-size models would take
  one to two more days.
- How we are fixing it:
  - every remaining model uses 10,000 sales (the low end of the
    specification's 10,000 to 30,000), drawn with the same stratified
    sample and seed as before: single-family and condo main (damage rate),
    the frequent-storm variant, the dollar variable and the 2021 to 2024
    comparison; results in `outputs/benefit/module_d/n10000/`;
  - each segment gets its own 10,000-sale main model, and the variants
    reuse its bandwidths. Bandwidths are counts of neighbouring sales, so
    bandwidths from a model on a different number of sales would cover a
    different area; keeping all of a segment's models on the same 10,000
    sales avoids that;
  - the value and tax step reads the 10,000-sale models
    (`MODULE_D_RUN=n10000`) so every variant comes from the same sample;
  - the full single-family main model (all 14,350 training sales) was
    stopped by the user on 13 Nov at about 11:40 after 13 hours 25 minutes,
    unfinished; nothing from it was saved or used. It can be rerun later on
    a bigger machine if a full-sample check is wanted;
  - the earlier 5,000-sale queue (D-188) was stopped before any of it ran.
- Decision: As above.
- Reason: The user's choice, so the models finish in hours, not days,
  while staying inside the specification's range.
- Evidence: `scripts/benefit/module_d_fit.py`,
  `scripts/benefit/module_d_value_tax.py`.
- Affects: Module D coefficients (sample size), value and tax results.

### D-191. Block-group fixed-effects model next to MGWR

- Date: 13 Nov 2026. Status: Final. Decided by: the user (side by side);
  Amey (details).
- What happened: The single-family MGWR flood effect was near zero and
  the same everywhere (flood bandwidth 9,993 of 10,000). A standard
  hedonic model with one dummy per census block group compares only homes
  in the same block group, so neighbourhood quality cannot drive the
  flood coefficient.
- What is wrong: Nothing; a check on MGWR.
- How we are fixing it:
  - log price on the specification's house variables plus one dummy per
    2024 block group, all qualified 2025 to 2026 sales (training and
    held-out together), single-family and condo separately;
  - standard errors clustered by block group, and by tract as a stricter
    check; the frequent-storm rate as a variant;
  - share of the flood rate's variation within block groups (about 40%
    in both segments, so the model has variation to use);
  - held-out error: fit on training sales, predict held-out sales;
  - its single coefficient per segment is one of the value and tax cases.
- Decision: Report MGWR and block-group fixed effects side by side.
- Reason: The user's instruction (D-187 step 5); the fixed-effects model
  is the usual hedonic benchmark and is robust to neighbourhood quality.
- Evidence: `scripts/benefit/module_d_fe.py`,
  `outputs/benefit/module_d/fe_block_group.json`.
- Affects: Module D report, value and tax results.

### D-192. Progress reporting for every long-running script

- Date: 14 Nov 2026. Status: Final (standard from now on). Decided by:
  the user.
- What happened: The condo main model's final fit ran for about 7 hours
  (against about 65 minutes for single-family) with no way to tell how far
  it had got, and the bandwidth search had no progress display.
- What is wrong: Without progress, a slow run cannot be told apart from a
  stuck one, and finish times can only be guessed.
- How we are fixing it:
  - tqdm 4.67.1 installed (pinned) in the project's `.venv` only, so mgwr
    shows its own progress bars in the log (backfitting rounds; its
    standard-error bar only fills at the end, so it is not relied on);
  - new `scripts/common/progress.py`, used by every script that can run
    longer than a few minutes: each step logs its start and end time and
    duration; countable work logs percent done and the time left from the
    rate seen so far; a heartbeat line every 5 minutes; one short status
    file with the current step, percent done and estimated finish;
  - the MGWR standard-error step runs in chunks (10 workers x 4 = 40
    parts) and each finished part is logged, so its percent and time left
    are visible;
  - queue runners pass the queue position and the expected length of the
    later jobs (from the jobs already done), so the status file also shows
    the whole queue's estimated finish.
- Decision: As above, for all long-running scripts from now on.
- Reason: The user's instruction; it makes slow, stuck and finished runs
  easy to tell apart.
- Evidence: `scripts/common/progress.py`, `scripts/benefit/module_d_fit.py`,
  `scripts/benefit/module_d_queue.py`; tested on a 600-sale condo fit
  (40 parts reported, heartbeat and status file written).
- Affects: How runs are monitored only; no result changes.

### D-193. Condo main rerun with its search bandwidths held fixed, queue detached

- Date: 14 Nov 2026. Status: Final. Decided by: the user.
- What happened: The 10,000-sale queue (D-190) ran as a child of the
  Claude app. When the app restarted at about 00:14 on 14 Nov, the queue
  was stopped during the condo main model's final fit (standard errors),
  after about 7 hours of that step. Nothing from the condo main fit was
  saved. The four single-family models were already saved and are kept.
- What is wrong: The condo main model, the three condo variants and the
  value and tax step had to be run again.
- How we are fixing it:
  - the condo bandwidth search had finished (13 Nov, 17:13) and its final
    bandwidths are in the run log: intercept 501, flood rate 503, living
    area 501, age 501, bedrooms 504, bathrooms 882, waterfront 10,000
    (countywide by design), distance to water 501, ground elevation 501,
    time 525. The condo main model is refitted with these held fixed
    (new `fixed` mode of `module_d_fit.py`), the same way the variants
    reuse the main bandwidths; the 46-minute search is not repeated;
  - the condo search stopped at the 200-round limit, not at the
    convergence tolerance: its last convergence measure was 0.0000103
    against the 0.00001 cutoff, and the bandwidths had not changed for
    many rounds before the limit. They are treated as final; the report
    says so;
  - the queue (condo main, frequent, dollar, with_older, then value and
    tax) runs from `scripts/benefit/module_d_queue.py --detach`, in its
    own session under caffeinate, so an app or terminal restart cannot
    stop it; each job is its own process and saves its model as soon as
    it finishes; progress as in D-192, in
    `outputs/benefit/module_d/n10000/queue/` (queue.log, status.txt,
    queue.pid). Started 14 Nov 00:29.
- Decision: As above.
- Reason: Same bandwidths as the finished search, so the coefficients and
  standard errors are those the original run would have produced, about
  45 minutes sooner.
- Evidence: search log of 13 Nov (rounds 1 to 200, bandwidths stable),
  `scripts/benefit/module_d_fit.py`, `scripts/benefit/module_d_queue.py`.
- Affects: Condo Module D models (timing only), value and tax results.

### D-194. Status-file crash and why the condo final fit is slow

- Date: 14 Nov 2026. Status: Final. Decided by: Amey (bug fix); the user
  (tolerance, validation, checkpoint).
- What happened: The detached condo queue (D-193) ran the condo main
  model's standard-error step for 8 hours 54 minutes (00:47 to 09:41 on
  14 Nov), reached 40 of 40 parts, then stopped with an error before
  saving. Two threads of the new progress code (D-192) wrote the status
  file's temporary copy at the same moment; one renamed it, the other
  then failed. Nothing from the fit was saved, and the queue stopped
  because the variants need the condo main model.
- What is wrong: (1) a bug in `scripts/common/progress.py`; (2) the condo
  final fit takes about six times longer than single-family. mgwr's
  standard-error step repeats one pass for every backfitting round of the
  model. The single-family search converged at round 33; the condo search
  never met the 0.00001 tolerance and used all 200 rounds (convergence
  measure 0.000049 at round 30, 0.000020 at 60, 0.000016 at 100, 0.0000103
  at 200; bandwidths unchanged from at least round 30). So every condo
  model at the current tolerance needs about 9 hours for standard errors.
- How we are fixing it: (1) status writes now take a lock, use a separate
  temporary file per thread, and a failed status write is logged instead
  of stopping the job; tested with 8 threads writing 4,000 times;
  (2) condo models use a backfitting tolerance of 0.00002 (bandwidths
  unchanged), reached at about round 60 of the condo search instead of
  never, so each condo model needs roughly a third of the time;
  (3) validation first: the single-family main model is refitted at
  0.00002 with its saved bandwidths and compared with the saved 0.00001
  model (largest and median change in every coefficient and standard
  error; flood result and significance); the queue stops if the flood
  result changes. Result (14 Nov, 14:52; `outputs/benefit/module_d/tol_check.json`):
  same bandwidths; 28 rounds instead of 33; across all variables and all
  10,000 local estimates the largest coefficient change is 0.33 of its
  standard error (median changes 0.004 to 0.07 standard errors) and the
  largest standard-error change is 4.6% (medians under 0.5%); flood rate
  median -0.019% per unit before, -0.015% after, share negative 55% and
  54%, significant local estimates 0 and 0 (raw and corrected); hold-out
  error 10.69% both. The flood result does not change, so the condo
  models went ahead. These differences also include the different
  backfitting path (the saved model's path includes the search rounds),
  so they are an upper bound on the effect of the tolerance;
  (4) checkpoint: right after backfitting, each model's fitted selector,
  local coefficients and fit summary are saved
  (`<segment>_<variant>_checkpoint.pkl`, `_backfit.parquet`, `_backfit.json`);
  a rerun with the same sales, bandwidths and tolerance resumes at the
  standard-error step;
  (5) queue (validation, comparison, condo main, three condo variants,
  value and tax) restarted detached on 14 Nov at 13:09.
- Decision: As above.
- Reason: A convenience file must never be able to stop a model run.
- Evidence: `outputs/benefit/module_d/n10000/queue/queue.log` (traceback
  at 09:41:33), condo search log of 13 Nov, mgwr 2.2.1
  `MGWR._chunk_compute_R` (loops over `bws_history`, one row per round).
- Affects: Condo Module D run time; no results changed.

### D-195. Six quick checks of the flood effect with fixed effects; value and tax memory fix

- Date: 14 Nov 2026. Status: Final. Decided by: the user (tests; tract
  dummies for tests 2 and 3); Amey (details, memory fix).
- What happened: (1) After the queue, the user asked for six quick checks
  with the fixed-effects model (single-family and condo, all qualified
  2025 to 2026 sales), each replacing or adding to the flood rate: FEMA
  zone (1% zone; VE against AE, 2027 maps); average NFIP premium per
  insured home by block group; NFIP claims since 2010 per 1,000 homes by
  block group; the flood rate in five groups; the main model away from
  water; the main model where floor heights come from the block group's
  own elevation certificates. (2) The queue's last job (value and tax)
  was killed by the system after 5 minutes (exit -9, out of memory).
- What is wrong: (1) Premium and claims are block group values, the same
  for every sale in a block group, so block group dummies absorb them;
  FEMA's public records go no finer than block group. VE cannot be
  tested: 0 single-family and 13 condo sales are in VE. (2) Carrying the
  local flood coefficients to every building found, for each of 383,978
  single-family buildings, its 9,993 nearest calibration sales at once
  (single-family flood bandwidth 9,993 of 10,000): about 24 GB.
- How we are fixing it:
  - tests 2 and 3 use one dummy per census tract instead (the user's
    choice), so they compare block groups in the same tract, standard
    errors clustered by tract; the main model with tract dummies is shown
    for comparison; the other tests keep block group dummies and block
    group clustering;
  - premium: residential policies (occupancy 1, 2, 3, 11 to 16) that
    started in 2025, total premium divided by insured units; block groups
    with at least 10 policies (1,396); only block group totals are made;
  - claims: residential claims with loss year 2010 or later (8,163; 6,698
    in a 2024 block group), per 1,000 occupied homes (ACS 2020 to 2024,
    B25003), in units of 10 claims per 1,000 homes;
  - groups: none (rate 0) and the quartiles of the positive rates within
    each segment; away from water: not waterfront and over 500 m from
    FEMA water areas; floor heights: block groups with their own summary
    (at least 10 insured buildings of the type, D-185);
  - each of tests 1 to 3 also run with the flood rate added back;
  - `smooth_to` now takes the target buildings in blocks (about 160 MB
    per array) and shares one neighbour search between variables with the
    same bandwidth; checked identical to the old version on test data;
    value and tax now reports progress (D-192).
- Decision: As above.
- Reason: The user's instruction; the memory fix changes no result.
- Evidence: `scripts/benefit/module_d_fe_tests.py`,
  `outputs/benefit/module_d/fe_tests.json` and `fe_tests.csv`;
  `scripts/benefit/module_d_fit.py` (`smooth_to`),
  `outputs/benefit/module_d/n10000/queue/value_tax_rerun.log`.
  Results: single-family: no flood measure is significant except claims
  (+0.70% per 10 claims per 1,000 homes, 95% range +0.29% to +1.10%,
  positive); 1% zone +1.19% (-0.06% to +2.45%, p 0.06); flood rate away
  from water +0.04%, with better floor heights -0.06%, both not
  significant. Condo: the flood rate stays positive and significant
  (+0.57% main; +0.95% away from water; +1.14% with better floor heights;
  the high and very high groups +7.1% and +12.5% against none); 1% zone
  -3.0% (-7.2% to +1.4%) and premium -0.06%, not significant; claims
  +1.98% per 10 per 1,000 homes, positive.
  Value and tax rerun on 14 Nov: 13 minutes, peak memory 3.2 GB,
  results in `outputs/benefit/module_d/value_tax_examples.json`.
- Affects: Module D report; value and tax run (memory only).

### D-196. Typical funded flood projects from the SCALE-R database (prompt 29, Part 1)

- Date: 15 Nov 2026. Status: Provisional (Part 1 only; Part 2 waits for
  the user). Decided by: the user (task); Amey (rules).
- What happened: The user asked to test Module C on projects like those
  actually funded in Miami-Dade, starting with what a typical seawall and
  a typical home elevation project look like in the investment database.
- What is wrong: The database has 54 seawall projects but only 2 home
  elevation projects (one clear: 2 homes in Miami Beach), so there is no
  typical elevation project in our data. Seawall length is stated for 5
  projects and crest height for 2.
- How we are fixing it:
  - flood projects: hazard Flooding or Coastal Hazards, or flood words in
    the name or description (1,154 of 1,664);
  - one type per project by keyword rules, first match (seawall; building
    elevation; pumps; road raising; drainage; canals, levees and
    structures; beach; green; shoreline repair; floodproofing; buyouts;
    plans; sewer; roads and parks; other), with 17 rows set by hand after
    reading them; all rules in `scripts/benefit/typical_projects_part1.py`;
  - location usable for Parcel, Corridor or Neighborhood points;
  - costs to 2025 dollars with CPI-U, Reported_Year taken as the cost year
    (assumption; 2026 as 2025);
  - cost flags from reading every seawall and elevation row: 11 programme
    totals, 20 where the seawall is one part of a bigger project, 3 likely
    duplicates; flagged rows stay in counts but not in cost statistics
    (32 of 54 seawalls left out);
  - PortMiami bulkheads (5) and canal or lake edges (4) kept as subtypes,
    not used for the typical project;
  - unit costs compared with North Bay Village and Miami Beach seawall
    figures, Elevate Florida and the USACE Back Bay Chief's Report.
- Decision: Typical seawall (suggested): 550 ft, crest +6.0 ft NAVD,
  $1.76M (middle half $0.56M to $2.74M), about $3,500 per ft. Typical
  elevation project: not set; the user chooses the source.
- Reason: The user's instruction; the rules are stated so the user can
  check the classification.
- Evidence: `outputs/benefit/typical_projects/part1_projects.csv`,
  `part1_summary.json`, `reports/benefit/typical_projects_part1.md`.
- Affects: Prompt 29 Part 2 (projects and typical sizes).

### D-197. Typical elevation from FEMA HMA data, and Part 2 settings (prompt 29, Part 2)

- Date: 16 Nov 2026. Status: Accepted. Decided by: the user (data source,
  rules, Part 2A scope, lengths); Amey (settings marked assumption).
- What happened: The user chose FEMA's mitigation grant list for the
  typical elevation project and approved downloading OpenFEMA "Hazard
  Mitigation Assistance Projects". That dataset no longer exists on
  OpenFEMA (404 at v1 to v4, not in the DataSets catalogue on 16 Nov
  2026). We stopped and asked; the user approved its current replacement,
  HMA Subapplications v2 (already used for Miami-Dade, D-113), for Florida.
- What is wrong: Our database has one real elevation project, so Part 2
  needs an outside source for a typical one.
- How we are fixing it:
  - downloaded the 5,291 Florida rows of HmaSubapplications v2
    (`scripts/benefit/download_hma_florida.py`; filter
    subapplicantStateAbbreviation eq 'FL'; all rows saved, count checked);
  - elevation = primaryActivity "Elevation" (955 records; 45 in South
    Florida, 4 in Miami-Dade);
  - kept funded records only (Closed, Approved, Obligated, Subaward
    Accepted). Dropped: 40 withdrawn or void, 216 denied, not selected or
    ineligible, 206 pending or in review, then 2 with no building count
    and 35 with zero cost. Usable: 456 Florida, 13 South Florida, 1
    Miami-Dade;
  - cost = federal + non-federal share (without FEMA management costs),
    CPI-U to 2025 with the fiscal year as cost year; homes =
    numberBuildingLocations;
  - typical = South Florida (13 usable, at least 10): median 1 home,
    median $253,859 per home (middle half $221,422 to $381,735). All of
    Florida: median 1 home, $326,706 per home; 79% of projects are one
    home;
  - second case, labelled assumption: Elevate Florida, 10 homes at about
    $267,000 each;
  - Part 2A: 12 shoreline seawalls, with the 5 PortMiami bulkheads and 4
    canal or lake edges shown separately; alignment on the FEMA 2027
    coastal shoreline (transect baseline) centred on the project point;
    length as stated, otherwise cost / $3,500 per ft, limited to the
    shoreline line there; crest +6.0 ft NAVD unless stated. Elevation
    SCALER-0684: the 2 single-family homes with the highest expected
    yearly damage in Miami Beach (homes not named);
  - Part 2B: 10 placements each, picked from high, middle and low
    expected damage bands, one per place, alternating coastal and inland
    for elevation; in each, the homes with the highest expected yearly
    damage are raised 3 ft (Module C default, assumption);
  - benefit per dollar: 7% discount rate (FEMA BCA Toolkit help content,
    Aug 2025, PDF page 59); project life 50 years for floodwalls and
    concrete infrastructure, 30 years for residential elevation (FEMA BCA
    Project Configuration and Cost Estimation Methodology Report, July
    2025, Table 1, page 16); maintenance 1% of cost a year for seawalls
    and none for elevation (assumptions; FEMA gives no standard rate).
    Tax change shown separately with the published Miami price discount
    scenario (D-187, assumption); value change kept out of the ratio.
- Decision: As above.
- Reason: The user's instructions; FEMA's current dataset holds the same
  elevation subapplications as the retired project list.
- Evidence: `data/raw/fema/hma_subapplications_fl/` (data and download
  log), `outputs/benefit/typical_projects/hma_elevation_summary.json`,
  `scripts/benefit/typical_elevation_hma.py`,
  `scripts/benefit/typical_projects_part2.py`. Results: typical FEMA
  elevation returns $1.26 to $2.45 per dollar in 4 high-damage places,
  $0.10 to $0.58 in middle ones; Elevate Florida case $0.67 to $0.99 in
  the high places; typical +6 ft seawall clears $1 in 1 of 10 placements
  and 6 of 443 shoreline stretches (all Miami Beach), $2.58 to $8.68 at
  +8 ft (sensitivity) in the high places; 7 of 12 real shoreline seawalls
  are more than 500 m from FEMA's coastal shoreline and were not run.
  Also added: projects more than 500 m from the coastal shoreline are not
  run (Module C would otherwise move them to the open shore), and the tax
  roll is read once per run in `module_d_value_tax.tax_change`.
- Affects: `reports/benefit/typical_projects_part2.md`.

### D-198. Part 2 follow-up: 3% sensitivity, frequent flooding note, best-case elevation, short walls (prompt 29, Part 2 follow-up)

- Date: 16 Nov 2026. Status: Accepted. Decided by: the user (all four
  additions); Amey (wording, the 200 ft cut applied to length used).
- What happened: The user asked for small additions to Part 2 without
  changing the method. While rerunning we also found that the first
  Part 2 summary, D-197 and the report back swapped a count: 5 of the 12
  real shoreline seawalls were not run (more than 500 m from FEMA's
  coastal shoreline) and 7 ran, not the other way round. Table A itself
  was right.
- What is wrong: Results were shown at 7% only; frequent tidal flooding
  was not flagged as missing; elevation results raise the single most
  damaged home, a best case; short walls (no end-around flooding) were
  mentioned in summary statements.
- How we are fixing it:
  - every benefit per dollar in Tables A and B, the +8 ft seawall
    sensitivity and the coastline scan is also computed at a 3% discount
    rate (same project lives and maintenance), shown next to 7% and
    labelled sensitivity (assumption); 7% stays the main figure;
  - summary and limits now say the most frequent storm in the model is
    the 10% (10-year) storm, so high-tide, king-tide and other frequent
    flooding are missing and seawall benefits are probably understated;
    a report-only section names NOAA CO-OPS high tide flooding thresholds
    and flood-day counts (Virginia Key) and the NOAA Sea Level Rise Viewer
    depth and extent layers as possible sources, with what each gives and
    the effort; nothing was downloaded;
  - for the typical FEMA elevation, the same project is also run on the
    5th and 10th most damaged single-family home in each tract; high-damage
    results are described as "up to";
  - real walls with a length used under 200 ft are flagged "end-around
    flooding not modelled, likely overstated" and left out of totals and
    best-result statements (Bay Harbor Islands 75 ft, Vizcaya 160 ft
    among those run; Yacht Club Drive and North Grapeland Heights were not
    run anyway). All typical walls are 550 ft.
- Decision: As above.
- Reason: The user's instructions; the count correction keeps the report
  consistent with its own table.
- Evidence: `scripts/benefit/typical_projects_part2.py` (RATE_LOW,
  SHORT_FT, `top_homes(start=)`), `outputs/benefit/typical_projects/`
  (`part2_*.csv`, `part2_summary.json`). Results at 7% are unchanged. At
  3%: elevation ratios rise about 1.6 times and seawall ratios about 1.7
  times; typical seawall still clears $1 in 1 of 10 placements and in 8
  of 443 stretches (6 at 7%); Elevate Florida case clears $1 in all four
  high-damage places ($1.06 to $1.56). 5th most damaged home: $0.58 to
  $1.22 at 7%; 10th: $0.40 to $0.85 (high-damage places). Real shoreline
  walls that ran and are at least 200 ft: 5, $15.6M, about $16,600 a
  year, $0.01 per dollar ($0.02 at 3%).
- Affects: `reports/benefit/typical_projects_part2.md` (map unchanged,
  since 7% figures did not change; regenerated with the run).

### D-199. Admin Flood What-If, Part 1: browser engine and private per-building export

- Date: 17 Nov 2026. Status: Proposed (Part 1 plan; waits for the user's
  confirmation before Part 2). Decided by: the user (goal, branch, rules);
  Amey (design, marked as recommendations).
- What happened: The user asked for a Flood What-If view in the admin panel
  so the professor can place a seawall or home elevation and see damage
  avoided, buildings protected and benefit per dollar. Part 1 is the plan
  and the data export, on the new branch `admin-what-if` from
  `benefit-simulator`.
- What is wrong: Module C runs in Python with a 96 MB table; the admin
  panel is a static site. The admin data must stay private (D-095), and the
  D-095 private bucket still does not exist (D-096).
- How we are fixing it:
  - recommend a browser engine: a plain JavaScript copy of Module B's
    `levels`, `event_loss`, `eyd` and Module C's `seawall` and `elevate`,
    with our own UTM projection formula; no server and no new packages;
  - export only the 386,929 buildings wet in at least one storm today
    (of 627,252) to `outputs/admin_data/what_if/` (git-ignored), in 438
    gzip binary column files on a 2 km UTM grid (21.9 MB in all), plus a
    manifest, curves, the FEMA coastal shoreline, the C-8 and C-9 outline
    and an optional overview file; no owner, address or parcel ID fields;
    parcel fields limited to allocated just value and segment;
  - round-trip check: Module B's `compute` on the exported files matches
    the stored expected yearly damage (largest building difference $3.68 a
    year, high case);
  - privacy: in production the files go to the private `admin-data`
    bucket under `what_if/`, read by admins only; the D-095 SQL needs
    `application/octet-stream` added to the allowed types; for local
    preview a development-only Vite setting serves the folder;
  - parity test plan: every Part 2 run reproduced in the browser within
    1% of Python's damage avoided; baseline within 0.1%.
- Decision: As above, pending the user's confirmation of the plan and the
  two choices (JavaScript instead of TypeScript; no new packages).
- Reason: The engine is small arithmetic on precomputed inputs, so a
  browser copy is fast and needs no service to host or secure; the parity
  test keeps it equal to Python.
- Evidence: `scripts/benefit/export_what_if.py`,
  `outputs/admin_data/what_if/export_summary.json`,
  `reports/benefit/admin_what_if_part1.md`.
- Affects: The admin panel (Part 2), `scripts/common/paths.py`
  (`ADMIN_DATA_DIR`, `ADMIN_WHAT_IF_DIR`).

### D-200. Admin Flood What-If, Part 2: the view, its checks and three open questions

- Date: 17 Nov 2026. Status: Accepted for the view; three questions open
  (below). Decided by: the user (plain JavaScript, no new packages, browser
  engine; show buildings water never reaches); Amey (design details).
- What happened: Built the Flood What-If view at `/admin/viz/what-if`
  (`src/admin/viz/whatif/`): seawall and raise-homes tools, dragging,
  Examples, results with 7% and 3% benefit per dollar, property value kept
  separate, building details, "Read this with" and About. The browser engine
  copies Modules B and C; `what_if_parity_fixture.py` writes Python's answers
  for 87 Part 2 projects to the private folder and `whatIfParity.test.js`
  checks them. A development-only Vite route serves
  `outputs/admin_data/` locally; production reads the private bucket
  (`whatIfData.js`), so no build contains the data. The export now also has
  house size and the 240,323 buildings the model expects water never to
  reach (positions only, shown as faint dots).
- What is wrong: While testing, three problems with the existing model
  showed up in the view:
  - the seawall "behind the wall" rule credits buildings far from the wall
    when FEMA's coastal shoreline skips creeks and canals (Miami Beach
    example: 119 protected buildings a median 688 m from a 168 m wall);
  - the published-discount property value scenario stretches a 3%
    flood-zone discount to heavily flooded homes (6 North Miami homes:
    +33% of value);
  - seawalls can only be valued within 2 km of FEMA's coastal shoreline
    (14% of county damage); walls on tidal rivers and canals cannot be.
- How we are fixing it: For now only warnings in the view, no change to
  the method: a warning when half the protected buildings are more than
  300 m from the wall; the property value change is shown as a share of
  value with a warning above 5%. Options for each are in
  `reports/benefit/admin_what_if_part2.md`, section 6 and 7.
- Decision: View accepted as built. The three method questions wait for
  the user.
- Reason: Changing the seawall rule or the Module D scenario would change
  Part 2 results, so the user decides.
- Evidence: parity 0.0002% largest difference (rule 1%); baseline totals
  within 0.1%; drag timing median 3.6 ms seawall, under 1 ms elevation
  (this MacBook); 192 tests pass; build has no data files; screenshots in
  the private `outputs/admin_data/what_if_screens/`.
- Affects: The admin panel (`AdminApp.jsx`, `AdminLayout.jsx`,
  `VizPage.jsx`, `src/admin/viz/whatif/`), `vite.config.js` (development
  route only), `scripts/benefit/export_what_if.py`.

### D-201. Drawn seawalls are placed on FEMA's coastal shoreline

- Date: 17 Nov 2026. Status: Accepted. Decided by: Amey, after the user
  found a drawn wall showing $0.
- What happened: A 1,588 ft wall drawn just off the Miami Beach bayfront at
  +9 ft protected nothing.
- What is wrong: Module C counts a building as behind a wall when its
  straight line to its nearest point on FEMA's coastal shoreline (transect
  baseline) crosses the wall. Those lines end at the shoreline, so a wall
  drawn even 10 m out in the water is crossed by none (tested: the Part 2
  Miami Beach wall at +8 ft avoids $1.26M a year on the line, $0 when moved
  10 m into the bay).
- How we are fixing it: The view places a drawn wall on the shoreline the
  way Part 2 placed real walls (`wall_line`): centred on the shoreline point
  nearest the middle of the drawn line, with the drawn length
  (`snapToShore` in `whatIfEngine.js`, with a test). It says how far the wall
  moved and shows the drawn line dashed. Lines more than 500 m from the
  shoreline are left where drawn, with the "not covered by FEMA's coastal
  study" warning. The shoreline is drawn more clearly and is in the legend.
- Decision: As above. Module C itself is unchanged, so parity still holds.
- Reason: Matches how Part 2 placed walls; users cannot be expected to draw
  exactly on a line they cannot easily see.
- Evidence: `src/admin/viz/whatif/whatIfEngine.test.js`.
- Affects: The admin Flood What-If view.

### D-202. Seawall waterway rule and 1 km cap (Module C and the What-If view)

- Date: 17 Nov 2026. Status: Accepted. Decided by: the user (rule, cap,
  no new downloads); Amey (which FEMA layer, what counts as inner water).
- What happened: Module C credited a seawall with every building whose
  nearest point on FEMA's coastal shoreline lies behind it. FEMA's shoreline
  skips canals and creeks, so buildings next to Indian Creek, the Miami River
  or the Biscayne Canal were counted as protected by a wall on the bay.
- What is wrong: The Part 2 seawall results were overstated (Miami Beach
  example: 119 protected buildings a median 688 m from a 168 m wall).
- How we are fixing it:
  - a building is protected only if its nearest open water is the coastal
    shoreline, not inner water, and it is within 1 km of the wall
    (`module_config.json` projects.seawall: inner_water_rule,
    max_distance_from_wall_m);
  - inner water: FEMA 2027 FIRM water lines (S_Wtr_Ln, on disk). The water
    areas layer (S_Wtr_Ar) the user suggested is almost all ponds and misses
    the canals, so it is not used. Left out: the open coast the study faces,
    water lines within 30 m of the coastal shoreline, isolated ponds
    (`build_water_distance.py`, `inner_water_distance.parquet`);
  - the same rule in the browser engine (export column `inner_water`);
    parity rerun: 87 runs, largest difference 0.0002%;
  - the view's overcrediting warning is replaced by a note of how many
    buildings the rule removed, and a softer warning only when half the
    protected buildings are more than 600 m away (small canals FEMA's lines
    may miss).
- Decision: As above.
- Reason: The user's rule; it removes the overcrediting found in D-200.
- Evidence: `reports/benefit/seawall_waterway_rule.md` (before and after);
  the waterway rule removes 22,640 of 41,808 behind-the-wall checks over 443
  stretches at +6 and +8 ft, the 1 km cap alone 1,250 (3%). After the rule
  no typical +6 ft placement or stretch returns $1 per dollar (best 0.87);
  at +8 ft the high-damage placements return $0.00 to $0.08 (were $2.58 to
  $8.68). Home elevation unchanged.
- Affects: `module_c_projects.py`, `typical_projects_part2.py` results,
  `reports/benefit/typical_projects_part2.md` (to update), the admin
  Flood What-If view, `scripts/common/paths.py` (INNER_WATER_PARQUET).

### D-203. Part 2 report updated for the waterway rule; closed-system sensitivity for Miami Beach

- Date: 23 Nov 2026. Status: Accepted. Decided by: the user (update,
  sanity check, sensitivity, wording); Amey (the closed-system extent).
- What happened: The Part 2 report still had the seawall results from
  before the waterway rule (D-202).
- What is wrong: Its seawall statements were overstated.
- How we are fixing it:
  - sanity check, nothing wrong: Miami Beach S2 has 3 buildings directly
    fronting the wall (two schools and a church, 280 to 300 m back); they
    flood above the floor only in the 2%, 1% and 0.2% storms, whose bay
    levels (6.2, 7.0, 8.4 ft) go over a 6 ft crest, so $0 at +6 ft and
    $12,231 a year at +8 ft. Miami S4 has 18 fronting building records at
    two points (the building inventory stacks records on one point): 12 on
    ground at 9.4 ft, above either crest, flooded only in the 0.2% storm;
    6 with floors at 10.5 to 11.6 ft, reached only by the 0.2% storm
    (11.6 ft), which goes over both crests; so $0 at +6 and +8 ft;
  - sensitivity, labelled as not a typical project: a continuous wall on the
    whole 13.1 km bay-side shoreline of Miami Beach's main island, closing
    the Biscayne Waterway, Indian Creek and an unnamed north waterway mouth
    (`closed_system_miami_beach.py`; waterway rule and cap off for this run
    only); $150M at $3,500 per foot, gates not costed (upper bound):
    +8 ft avoids $11.2M a year, 0.91 per dollar at 7%, 1.53 at 3%; +6 ft
    $2.0M a year, 0.16 and 0.28; with the mouths left open about half;
  - the report summary now explains in plain language why one wall segment
    protects little (water reaches homes through canals and creeks), and
    that tidal flooding and existing canal seawalls are still not modelled;
    Table A, the Table B seawall rows, the coastline scan and the map are
    from the rerun with the rule.
- Decision: As above.
- Reason: The user's instructions.
- Evidence: `reports/benefit/typical_projects_part2.md`,
  `reports/benefit/typical_projects_part2_map.png`,
  `outputs/benefit/typical_projects/closed_system_miami_beach.json`.
- Affects: The Part 2 report and map.

### D-204. Explanation layer in the Flood What-If view

- Date: 23 Nov 2026. Status: Accepted. Decided by: the user (what to show);
  Amey (colours, wording, the two precision changes below).
- What happened: The user wanted to see why each building is or is not
  protected by a seawall, and why homes are or are not picked for raising.
- What is wrong: The view showed totals only, so results such as $0 for
  the Miami Beach wall could not be checked building by building.
- How we are fixing it:
  - one reason per flooding building within 1 km of the selected wall, in
    this order: floods only from rainfall or canals; nearest water is a
    canal, creek or inner waterway (named where FEMA's water line has a
    name); nearest water is the bay beyond the ends of the wall; beyond the
    1 km limit; protected (yearly damage goes down); behind the wall but
    every flooding storm goes over it. Defined once in Python
    (`Model.seawall_reasons`) and copied in the browser (`seawallReasons`);
  - cards: click a building for the reason, nearest water and distances,
    heights (estimated or from records), year built, type, value, a
    five-storm table (level, above the floor, blocked or not, damage before
    and after) and yearly damage; shift-click a second building to compare
    side by side with differences highlighted; for raising homes, the rank
    by expected damage and the storms before and after raising;
  - a toggle draws each building's line to the water it is matched to;
  - export: nearest inner-water point and name, and year built, added
    (`build_water_distance.py`, `export_what_if.py`); inverse map projection
    in the browser (`fromUtm17`, tested against pyproj);
  - precision, no change to the rule: Module C's "line passes within 5 m of
    the wall" now uses the exact distance instead of an approximated buffer
    shape, and the canal-versus-shore comparison uses single precision, as
    the browser does. Rerunning Part 2 changed no result.
- Decision: As above.
- Reason: The user's request; the same rule in both places keeps the cards
  honest.
- Evidence: `whatIfParity.test.js`: the reason of all 23,946 buildings near
  the 42 Part 2 wall runs matches Python (0 mismatches); damage avoided
  parity unchanged (0.0002%); 195 tests pass; build has no data files.
- Affects: `module_c_projects.py`, `build_water_distance.py`,
  `export_what_if.py`, `what_if_parity_fixture.py`, `src/admin/viz/whatif/`.

### D-205. No cost for raising 2 to 4 unit buildings: left as a limitation

- Date: 23 Nov 2026. Status: Accepted. Decided by: the user (add the switch
  only if FEMA's grant records give a cost).
- What happened: The area tool raises single-family homes only. The user
  asked whether duplexes and small apartment buildings could be included.
- What is wrong: A cost per building is needed, and the typical cost
  ($254,000) is from single-family FEMA grants.
- How we are fixing it: Checked the Florida rows of OpenFEMA HMA
  Subapplications v2 (already on disk, D-197): there is no building-type
  field; only 115 of 955 elevation records have a title, and no title in
  the Florida file mentions a duplex, triplex, multi-family building,
  apartment or condo. So no switch was added. The view and the Part 2
  report now say so; Click homes still lets a user raise any building and
  type a cost.
- Decision: Leave it; listed as a limitation.
- Reason: The user's rule; no cost source.
- Evidence: `data/raw/fema/hma_subapplications_fl/hma_subapplications_florida.csv`.
- Affects: The admin Flood What-If view (note and card wording),
  `reports/benefit/typical_projects_part2.md`.

### D-206. Scenario data removed from the admin-what-if history; the view loads it privately

- Date: 24 Nov 2026. Status: Done (not pushed). Decided by: the user (D-095
  step 6, "Remove the Scenario data from commit a32dbdf").
- What happened: The admin Scenario data files
  (`src/admin/viz/scenario/data/`: scenarios.json, scores.json,
  tracts.geojson, models.json, compare.json) were in local commit `a32dbdf`
  and in 28 later commits on `admin-what-if`. None was ever pushed.
- What is wrong: Any push of the branch would have put them on the public
  GitHub repository, and any build bundled them as public static files.
- How we are fixing it: Rewrote only this branch's unpushed commits
  (`origin/main..admin-what-if`, 38 commits) with `git filter-branch
  --index-filter`, removing that folder from every commit and keeping every
  other change. Old tip: `366c916`. The files now live in the git-ignored
  `outputs/admin_data/scenario/` (`paths.ADMIN_SCENARIO_DIR`);
  `build_scenario_data.py` writes there; the view loads them through the
  new shared loader `src/admin/viz/adminData.js` (dev middleware locally,
  private bucket `admin-data` in production, the same as the What-If view);
  the folder is git-ignored; the Scenario test reads the private copy and
  is skipped where it is missing.
- Decision: Done on `admin-what-if` only. `ml-scenario-module` and
  `benefit-simulator` still hold the old commits and must not be pushed.
- Reason: D-095, D-096: admin data must never reach the public repository
  or a public build.
- Evidence: before and after file lists (29 commits carried the folder, 0
  after); `npx vite build` has no Scenario data in `dist/assets/`.
- Affects: Branch history of `admin-what-if`; the admin Scenario view needs
  the bucket upload (D-095 steps 1 to 3) before it works in production.

### D-207. D-095 fix: private bucket created; all admin views load from it

- Date: 24 Nov 2026. Status: Done (not deployed). Decided by: the user
  (D-095 plan, approved in D-096).
- What happened: The user ran the bucket SQL. Checks: bucket `admin-data`
  exists, not public, 10 MB per file, types JSON, GeoJSON and binary
  (`application/octet-stream`, for the What-If tiles); one read policy,
  SELECT for authenticated users where `is_admin()`; the public URL answers
  400 and a logged-out listing is empty.
- What is wrong: The gap map still bundled its tract file from `src/`.
- How we are fixing it: The gap map now loads `gap/tracts.geojson` through
  `src/admin/viz/adminData.js`, like the Scenario and What-If views;
  `build_viz_tracts.py` writes to the git-ignored staging folder; the file
  is removed from `src/` and the folder is git-ignored. New
  `scripts/js/upload-admin-data.mjs` (`npm run upload-admin-data`) uploads
  `gap/`, `scenario/` and `what_if/` (918 files, 34.7 MB; test-only files
  skipped) and refuses a public bucket. The SQL is recorded in
  `supabase/sql/admin_dashboard.sql`.
- Decision: The build now contains no admin data.
- Reason: D-095.
- Evidence: `npx vite build` (no admin files in `dist/`); 195 tests pass.
  After the upload (918 files): the public URL answers 400; logged out,
  every download is refused and listings are empty; signed in as the
  non-admin test user `scaler-nonadmin-test@example.com` (created by the
  user, not on the admin list, `is_admin()` false), every download is
  refused and listings are empty.
- Affects: All three admin data views. The gap map file stays in the public
  history of `main` (open decision, D-095 step 6).

### D-208. Flood What-If view simplified for a first-time reader

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user (redesign brief: understandable within 30 seconds by someone with no
  flood modelling background).
- What happened: The view showed every control, note and layer at once:
  long paragraphs, jargon (NAVD88, EYD, crest), six reason colours, damage
  shading, dry dots and the C-8/C-9 outline.
- What is wrong: A new reader could not tell what to do or what the result
  meant without reading several paragraphs.
- How we are fixing it: Layout, wording and defaults only; the engine,
  rules and numbers are unchanged (parity and engine tests pass as before).
  - Toolbar: Seawall, Raise homes, Examples, About; tool controls show only
    for the active tool (wall height; area or click, homes, raise by).
  - First visit: a three-step hint, dismissed once (localStorage, in
    try/catch).
  - One result card: "Prevents about $X a year in flood damage"; buildings
    protected, residents protected, benefit per dollar with Pays back or
    Does not pay back; cost with an edit pencil; the five-storm basis.
    Range, 7% and 3%, project life, cost source and property value are
    under Details. Warnings and notes are one-line chips with the full text
    on hover or tap. Money is rounded ($1.3M, $12k).
  - Map: buildings grey (still floods) and green (protected) by default;
    the coast line only while drawing a wall. Reason colours, lines to
    water, damage shading, dry buildings and the C-8/C-9 outline are under
    a Show why switch; the legend lists only what is shown.
  - Building card: a one-line answer (for example "Not protected: water
    reaches it through Indian Creek."), damage before, after and avoided;
    the storm table and building facts under Details. Compare still works.
  - About: five bullets (what it does, data, how projects work, benefit
    per dollar, main limits), with the longer method under More detail.
  - The D-205 limitation (no cost for 2 to 4 unit buildings) moved to a
    tooltip on "Homes to raise" and the "not a candidate" card.
- Decision: Adopted for the admin view.
- Reason: The user's brief.
- Evidence: Before and after screenshots (desktop and phone: empty map,
  seawall placed, building card, Examples, Show why) in
  `outputs/admin_data/what_if_screens/redesign/` (private); 198 tests pass;
  new `whatIfExplain.test.js` checks the rounding and one-line answers.
- Affects: `src/admin/viz/whatif/whatIfMap.{html,css,js}`,
  `whatIfExplain.js`.

### D-209. Building compare mode removed from the Flood What-If view

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: Shift-clicking a second building opened two cards side by
  side with differences highlighted (D-204, kept in D-208).
- What is wrong: The user asked for it to be removed, to keep the view
  simple.
- How we are fixing it: A click now always shows one building card; the
  shift-click handling, the "Shift-click another building to compare" note
  and the two-card layout are gone. `cardHtml` still accepts a second card,
  unused.
- Decision: Removed.
- Reason: The user's request.
- Evidence: `after_desktop_card.jpg` and `after_phone_card.jpg` in
  `outputs/admin_data/what_if_screens/redesign/`; What-If tests pass.
- Affects: `src/admin/viz/whatif/whatIfMap.js`, `whatIfMap.css`. D-208's
  "Compare still works" no longer holds.

### D-210. The view's comparison discount rate is FEMA's 3.1%, not 3%

- Date: 24 Nov 2026. Status: Done in the admin view (not pushed); Part 2
  report and scripts still at 3%. Decided by: the user.
- What happened: The view showed benefit per dollar at 7% (main) and 3%
  (sensitivity, an assumption, D-198).
- What is wrong: A round 3% is not a rate anyone uses. FEMA used 3.1% in
  2023 and 2024 and went back to 7% in 2025 (FEMA BCA Toolkit help content,
  28 August 2025, page 59; `data/reference/fema_standard_values.csv`,
  `discount_rate_2023_2024`).
- How we are fixing it: `SETTINGS.rates.sensitivity` is 0.031; Details reads
  "Back per $1 at 7% (FEMA rate since 2025)" and "at 3.1% (FEMA rate in 2023
  and 2024, shown for comparison)", no longer tagged assumed; About says the
  same. Damage figures do not change.
- Decision: 7% stays the main figure; 3.1% is the comparison.
- Reason: Both rates are published FEMA values, so the comparison is
  defensible.
- Evidence: `whatIfEngine.test.js` checks the setting and one ratio (S2:
  $2.62 per dollar at 3.1%, $2.66 at 3%).
- Affects: The admin Flood What-If view. `typical_projects_part2.py`
  (`RATE_LOW`), `closed_system_miami_beach.py` and
  `reports/benefit/typical_projects_part2.md` still use 3% until rerun.

### D-211. Building card opens next to the building

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: Clicking a building opened its card in a fixed panel at
  the top right (bottom on a phone), away from the building.
- What is wrong: The reader had to look back and forth to see which
  building the card was about.
- How we are fixing it: The card is now a map popup anchored to the
  building, with a pointer to it. If the building is under the side column
  or near an edge, the map slides so both are in view. Clicking empty map,
  or starting to draw, closes it. The fixed card panel is removed.
- Decision: Adopted.
- Reason: The user's request.
- Evidence: `after_desktop_card.jpg`, `after_phone_card.jpg` in
  `outputs/admin_data/what_if_screens/redesign/`; What-If tests pass.
- Affects: `src/admin/viz/whatif/whatIfMap.{js,css,html}`.

### D-212. Example 1 is a wall that pays back; long project names wrap

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: Example 1 was the typical Miami Beach wall at +6 ft, which
  prevents $0 a year in the middle case, so no example wall paid back. Long
  project names, such as "Typical elevation, Brownsville (low damage)", were
  cut off with no way to read them.
- What is wrong: The examples showed only a wall that does nothing, and the
  project name was unreadable.
- How we are fixing it: Example 1 is now the strongest 550 ft stretch of the
  coastline scan (Miami Beach ocean front) with an +8 ft wall: about $299k
  a year prevented, $1.9M cost, $1.88 back per $1 at 7% ($3.13 at 3.1%).
  The same stretch at +6 ft returns $0.80, and at +7 ft $1.64. The scan
  names the place "Unincorporated Miami-Dade" because the FEMA shoreline runs
  just outside the city outline; the label says Miami Beach. Examples 2 and 3
  are unchanged ($1.26 and $0.00 per $1). Project names now wrap.
- Decision: Adopted.
- Reason: The user's request. Limitation: the wall cost is $3,500 per foot
  of length whatever the height, so a higher wall looks better than it would
  with a height-based cost.
- Evidence: `after2_desktop_examples.jpg`, `after2_phone_examples.jpg` in
  `outputs/admin_data/what_if_screens/redesign/`; values from the view.
- Affects: `scripts/benefit/what_if_parity_fixture.py`,
  `outputs/admin_data/what_if/examples.json` (private, needs re-upload to
  the bucket), `src/admin/viz/whatif/whatIfMap.css`.

### D-213. Examples is a tab of its own

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: Examples was a one-off button. After loading the examples,
  switching to Seawall or Raise homes left the examples on the map and in
  the results, and loading them had also deleted the user's own projects.
- What is wrong: The top row looks like tabs, so the examples should go
  away when the user changes tab.
- How we are fixing it: Examples is now a tab like Seawall and Raise homes.
  Opening it sets the user's own projects aside and shows the three
  examples. Switching to another tab, or clicking Examples again, removes
  the examples and brings back the user's own projects. If the user switches
  away while the examples are still loading, they do not appear.
- Decision: Adopted.
- Reason: The user's request.
- Evidence: Checked in the dev view: draw a wall, open Examples (3 examples
  shown, tab pressed), switch to Raise homes (only the user's wall on the map
  and in the results), reopen and close Examples, and a fast switch while
  loading. What-If tests pass.
- Affects: `src/admin/viz/whatif/whatIfMap.{js,html}`.

### D-214. Project number markers drawn by the view, not by a map text layer

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user (bug report), cause found by testing.
- What happened: After D-213, switching from Examples to Raise homes still
  left example markers (the numbered dots) on the map. The project list was
  empty and the map's marker data was empty, yet the map kept drawing them.
- What is wrong: Root cause, found step by step: (1) reproduced with real
  clicks; (2) the walls and highlighted buildings cleared, only the numbered
  markers stayed; (3) the marker data source was empty, so our code was right
  and the drawing was stale; (4) this was the only map source that fed both
  a circle layer and a text layer, which Mapbox (v3.15) keeps in two separate
  caches; giving the numbers their own source fixed the circles, but the text
  layer still kept old numbers. So Mapbox's text layer does not reliably
  redraw after its data changes. Our D-213 check missed this because it
  tested the data, not what is drawn on screen.
- How we are fixing it: The numbered markers are now small page elements
  that the view creates from the project list on every redraw and removes
  itself, so what is shown always matches the list. The tab rules moved to a
  small module (`whatIfTabs.js`) with tests for every tab change, for never
  bringing an example back with the user's projects, and for exactly one
  marker per project.
- Decision: Adopted.
- Reason: The map must always match the project list; a check of the data
  alone is not enough, so the browser check now counts what is drawn.
- Evidence: Six runs in the dev view (leave to Raise homes, Seawall, or
  Examples again, including a switch 0.15 s after opening): 3 markers, the
  wall and 146 buildings while open; 0 of each after leaving. Clicking a
  marker still selects its project. What-If tests: 18 pass.
- Affects: `src/admin/viz/whatif/whatIfMap.{js,css}`,
  `src/admin/viz/whatif/whatIfTabs.js`, `whatIfTabs.test.js`.

### D-215. Guided tour of the Flood What-If view

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: A first-time reader, such as the professor, had only a
  three-line hint and would not know what the card, the numbers, the
  buildings or Show why mean.
- What is wrong: The view needs a walk-through that works without anyone
  explaining it in person.
- How we are fixing it: A Tour button in the title row (and "Take the tour"
  in the first-visit hint) starts a nine-step tour. Each step highlights one
  part and explains it in one or two sentences: welcome, the tabs, the result
  card, cost and Details, switching projects, a building card, Show why,
  drawing your own project, and About. The tour opens the Examples tab and
  one building card itself, so there is always something real to look at.
  Back, Next, Skip, the arrow keys and Esc work; on a phone the text sits at
  the bottom or top of the screen. Plain JavaScript, no new packages.
- Decision: Adopted.
- Reason: The user's request.
- Evidence: Screenshots of every step on desktop and phone in
  `outputs/admin_data/what_if_screens/tour/`; tests for where the text box is
  placed (it always stays inside the window). What-If tests: 22 pass.
- Affects: `src/admin/viz/whatif/whatIfTour.js`, `whatIfTour.test.js`,
  `whatIfMap.{js,css,html}`.

### D-216. The tour shows how to add a seawall and raise homes

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: The tour (D-215) said in one step how to draw a project but
  never showed it.
- What is wrong: A first-time reader learns faster by seeing a project being
  added and its card appear.
- How we are fixing it: The one "Try your own project" step became four:
  "Add a seawall" (opens the Seawall tab and explains Draw a wall),
  "Your seawall" (the tour places a sample wall on the Miami Beach coast and
  points to Wall height), "Raise homes" (opens the tab and explains Draw an
  area, Click homes, Homes to raise and Raise by), and "Your raised homes"
  (the tour draws a sample area in Miami Shores and raises its 5 most damaged
  homes). The tour now has 12 steps. The samples are named "Sample seawall"
  and "Sample raised homes" and are removed when the tour ends; the user's
  own projects stay. On a phone the highlight now covers only the part of a
  panel that shows, and the panel scrolls to it.
- Decision: Adopted.
- Reason: The user's request.
- Evidence: Screenshots of steps 8 to 12 on desktop and phone in
  `outputs/admin_data/what_if_screens/tour/`; in the dev view a user's own
  wall stayed and both samples were gone after Finish. What-If tests: 22 pass.
- Affects: `src/admin/viz/whatif/whatIfMap.js`, `whatIfTour.js`.

### D-217. Water paths only behind the wall, easier to find; zoom to the selected project

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: With Show why on, "Lines to nearest water" drew a line for
  every flooding building within 1 km of the wall (1,204 for Example 1),
  including buildings far from the wall whose water never reaches it. The
  option was a small checkbox inside the legend. Selecting an example did
  not move the map to it.
- What is wrong: The far lines buried the story of the wall, and a regular
  user would not notice the checkbox.
- How we are fixing it: The 1 km rule stays for the colored dots (it is the
  same rule Module C uses, and the counts show how many buildings a short
  wall misses); the legend heading now says "Within 1 km of" the project.
  Lines are drawn only for the buildings behind the wall (protected and
  water goes over the wall: 214 for Example 1), whose path to the coast
  crosses the wall. A distance cut was tried first and rejected: even the
  nearest flooding building is about 260 m inland, so 300 m kept only 20
  lines. The option is now a "Water paths" switch under Show why, on by
  default, with a ? that explains the lines; the tour's Show why step
  mentions it. Clicking a project chip or its numbered marker zooms to that
  project (a wall together with the buildings it protects), and opening
  Examples zooms to project 1.
- Decision: Adopted.
- Reason: The user's request.
- Evidence: `after3_desktop_exwhy.jpg`, `after3_*_exchip3.jpg` in
  `outputs/admin_data/what_if_screens/redesign/`; in the dev view, Examples
  opens at zoom 15.5 on project 1 and chip 2 and marker 1 move the map to
  their project. What-If tests: 22 pass.
- Affects: `src/admin/viz/whatif/whatIfMap.{js,css}`.

### D-218. Count physical buildings, not structure records

- Date: 24 Nov 2026. Status: Done (not pushed or deployed). Decided by: the
  user.
- What happened: The What-If card for Example 1 said 144 buildings
  protected, but the map showed about 86 green dots. The National Structure
  Inventory (NSI) splits a building with several uses into one record per
  use (occupancy type), all at the same point with the same footprint id,
  and the floor area is shared among them. Every count labelled "buildings"
  in the tool, Module C, the parity tests and the reports counted records.
  Countywide 627,252 records are 570,111 buildings; 386,929 flooding records
  are 348,094 buildings. 34,667 buildings hold 2 to 12 records.
- What is wrong: Counts labelled buildings were too high wherever there are
  mixed-use buildings (Example 1: 144 records, 86 buildings).
- How we are fixing it:
  - Grouping key: records at exactly the same NSI point are one building
    (UTM x and y in Python, the same exported tile position in the browser;
    no re-export). The NSI building id (bid) was checked and rejected: of
    the 48,303 records that share a bid but not a point, 47,994 have a blank
    bid (parcel-based points, each at its own spot, so separate buildings)
    and 309 in 152 bids are separate footprints 0.3 to 2.7 m apart with
    their own footprint ids and floor areas.
  - A building is protected if any of its records has damage avoided > 0;
    otherwise it takes the group its records share (no building in any
    parity run has records that disagree otherwise).
  - Python Module C: buildings_affected, buildings_with_damage_before,
    buildings_protected and storms_held_by_wall_buildings count buildings;
    records_* fields keep the record counts. Part 2, the closed-system run
    and the Module C examples report buildings with records beside them. The
    Module C example stretch is still chosen by records, so the example and
    its dollars do not move.
  - Browser: the card, legend groups and map count and draw one dot (and
    one water path) per building; Details shows "N use records". A building
    card for a building with several uses lists each use with its own damage
    before and after, and shows the building totals.
  - Parity: the browser must match Python exactly on buildings affected,
    records affected, buildings protected, buildings per reason group for
    every Part 2 wall, and the countywide 348,094 flooding buildings.
- Decision: Adopted.
- Reason: The user's decision. Dollars are summed over records, so they are
  unchanged: rerunning the last committed Module C and this version gives
  identical non-count results; Part 2 and the closed-system outputs differ
  only in count columns.
- Evidence: Example 1 in the dev view: 86 buildings protected, 86 green
  dots, legend 86 / 24 / 116 / 428 (records 144 / 70 / 203 / 787). Raise
  homes ranking unchanged: it ranks single-family records and every home in
  the top 10 of each typical tract is its own building; 3,668 RES1 records
  (2,698 flooding) sit in split buildings, mostly RES1 with one commercial
  use. What-If tests: 23 pass, including the new building parity checks.
- Found on the way: `spec_alignment_part2.md` quotes the North Miami wall
  (1,881 buildings, $2.2M) and Princeton (2,726 homes, $8.4M) from a Module
  C run made before D-202; the current model gives 104 records / 91
  buildings and $56,684, and 2,712 homes and $8.0M. That report needs
  updating for D-202, separately from this change.
- Affects: `scripts/benefit/module_c_projects.py`,
  `typical_projects_part2.py`, `closed_system_miami_beach.py`,
  `what_if_parity_fixture.py`, `src/admin/viz/whatif/whatIfEngine.js`,
  `whatIfMap.{js,css}`, `whatIfExplain.js`, `whatIfParity.test.js`; reports
  to update by the user: `typical_projects_part2.md`, `admin_what_if_part1.md`,
  `admin_what_if_part2.md`, `stage1_data.md`, `spec_alignment_part2.md`.
