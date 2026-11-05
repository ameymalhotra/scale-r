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

- Date: 5 Nov 2026. Status: Pending Amey. Decided by: Amey (rule from
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
