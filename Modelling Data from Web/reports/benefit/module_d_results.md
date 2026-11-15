# Module D results: does flood risk lower home prices in Miami-Dade?

Benefit simulator. 14 Nov 2026. Branch `benefit-simulator`.
Decisions D-184 to D-195 in `DECISIONS.md`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| Miami-Dade Property Appraiser sales and house layer; Florida DOR 2026 tax roll | Qualified sales 2025 to 2026 (main), 2021 to 2024 sales (test), house features, just value, millage | Roll year 2026; sales to 2026 | Already on disk (D-178, D-179) |
| Our Modules A to C | Expected yearly flood damage per building (the flood rate), project examples | This work | Built here |
| FEMA 2027 FIRM database (effective 19 Feb 2027) | Flood zones, water areas (waterfront, distance to water) | 2027 maps | Already on disk (D-161) |
| OpenFEMA NFIP Redacted Policies v3 | Floor heights from elevation certificates (D-185); average premium by block group (test 2) | Refreshed 9 Sep 2026 | Already on disk (D-181) |
| OpenFEMA NFIP Redacted Claims | Claims since 2010 by block group (test 3) | 1978 to 2026 | Already on disk (D-113) |
| ACS 2020 to 2024, table B25003, block groups | Occupied homes (claims per 1,000 homes) | 2024 release | Already on disk |
| Census 2024 TIGER block groups | Block group and tract of each sale | 2024 | Already on disk |
| Published studies (listed at the end) | Published flood discounts for the scenario; the underpricing research | 2018 to 2023 | Cited only |

**Estimated** numbers come from our data and models. **Assumed** numbers
are inputs we chose or took from published studies (marked "assumption").

## In short

- **Single-family homes: no flood discount in the data.** The best estimate
  is about zero, and the 95% range is small and includes zero:
  - fixed-effects model: -0.03% of price per unit of flood rate (95% range
    -0.16% to +0.11%);
  - MGWR: median -0.02% per unit, no local estimate significant;
  - the effect is the same everywhere in the county: MGWR's flood
    bandwidth is 9,993 of 10,000 sales (countywide).
  One unit of flood rate is $100 of expected yearly damage per $100,000 of
  building value.
- **Condos: a small positive link, which is not a flood premium.** Condos
  with a higher flood rate sell for slightly more (fixed effects +0.57% per
  unit, significant). It stays positive in every check. The likely reason
  is that the most exposed condo buildings are on the water, with views
  and amenities the data cannot see. We do not read it as buyers paying
  more for flood risk.
- **The six extra checks agree.** No other flood measure shows a discount
  either (FEMA zone, insurance premium, past claims, groups instead of a
  straight line, homes away from water, block groups with good floor
  height data). The only significant results are positive and point to
  the same hidden-amenity problem.
- **This matches published research on underpricing.** Several studies
  find that housing markets, Florida's in particular, price flood risk
  weakly or not at all, especially without disclosure. A zero estimate
  does not mean flood protection has no value; it means buyers do not
  currently pay for it in the price.
- **Published-discount scenario (assumption).** To show what the benefit
  would be if buyers priced flood risk as other studies found, we also
  apply published discounts (3% Miami-Dade central case; 4.6% and 7%).
  These are labelled assumptions, not estimates. In the scenario the two test projects raise home values by $24M to $60M (seawall, North Miami) and $86M to $217M (elevation, Princeton); with the data-based estimates the single-family change is about zero.
- **Fixed effects predict as well as MGWR.** Held-out error (median, sales
  the models never saw): single-family 10.7% both; condo 10.9% fixed
  effects against 12.8% MGWR. Both are far better than one countywide
  regression (20% and 31%).

## 1. What was run

- **Sales:** qualified 2025 to 2026 sales of improved homes: 17,935
  single-family and 22,966 condo. 20% of the sales in each tract are held
  out to test predictions.
- **Flood variable:** the flood rate, expected yearly flood damage per
  $100,000 of building value (D-184), from Modules A to C. Variants:
  storms from 10% to 2% a year only ("frequent"); dollar damage (the
  specification's variable); main sample plus 2021 to 2024 sales.
- **Other variables:** living area, lot size (single-family), age,
  bedrooms, bathrooms, pool proxy (single-family), waterfront, distance to
  water, ground elevation, time of sale.
- **Models:**
  1. MGWR (the specification): every coefficient can vary by place, each
     with its own bandwidth (how many nearby sales each local estimate
     uses). Fitted on 10,000 training sales per model (D-190), inside the
     specification's 10,000 to 30,000 range.
  2. Block-group fixed effects (D-191): one flood coefficient for the
     county, but each sale is compared only with sales in the same census
     block group, so neighbourhood quality cannot drive the result.
  3. One countywide regression (OLS), for reference.

## 2. MGWR results

### Bandwidths (estimated)

A bandwidth near 500 means the effect changes from place to place; near
10,000 means it is the same across the county.

| Variable | Single-family | Condo |
|---|---|---|
| Intercept (price level) | 501 | 501 |
| **Flood rate** | **9,993 (countywide)** | **503 (local)** |
| Living area | 501 | 501 |
| Lot size | 501 | not used |
| Age | 501 | 501 |
| Bedrooms | 3,181 | 504 |
| Bathrooms | 503 | 882 |
| Pool proxy | 9,999 (held countywide) | not used |
| Waterfront | 9,999 (held countywide) | 10,000 (held countywide) |
| Distance to water | 501 | 501 |
| Ground elevation | 501 | 501 |
| Time of sale | 501 | 525 |

- **Single-family:** the flood effect does not vary by place.
- **Condo:** the flood effect varies a lot by place. It is positive at 73%
  of the local estimates; 34% are significant after correcting for
  multiple tests.

### Flood effect (estimated, % price change per unit)

| Model | Single-family median (10th to 90th percentile of local estimates) | Significant (corrected) | Condo median (10th to 90th) | Significant (corrected) |
|---|---|---|---|---|
| Main | -0.02% (-0.05% to +0.05%) | 0% | +1.22% (-5.25% to +4.94%) | 34% |
| Frequent storms only | -0.03% (-0.04% to +0.02%) | 0% | +1.96% (-17.6% to +25.8%) | 29% |
| Dollar damage (per $1,000 a year) | +0.48% (+0.25% to +0.55%) | 54% | +2.97% (-18.5% to +23.3%) | 45% |
| With 2021 to 2024 sales | -0.18% (-0.18% to -0.17%) | 100% | +1.26% (-3.57% to +5.42%) | 38% |

- The dollar variable is positive because dollar damage grows with the
  home's value (D-183); this is why the rate is the main variable.
- With the 2021 to 2024 sales added, single-family shows a small
  significant discount (-0.18% per unit). Those sales have no
  qualification code and pass only a stated non-market rule (D-179), so
  the main result stays on qualified 2025 to 2026 sales; this result is a
  hint that the discount may have been somewhat larger in earlier years.

### How the models were fitted

- **Single-family:** bandwidths from the search, tolerance 0.00001, 33
  backfitting rounds; the three variants reuse the main bandwidths.
- **Condo, bandwidths:** from the condo search of 13 Nov. That search
  stopped at mgwr's 200-round limit without meeting the 0.00001 tolerance
  (last change 0.0000103), but the bandwidths had not changed for at least
  170 rounds, so they were held fixed and the condo main model was refitted
  with them (D-193).
- **Condo, tolerance 0.00002** (D-194). mgwr's standard-error step repeats
  one pass for every backfitting round, so 200 rounds made each condo
  model take about 9 hours. At 0.00002 the condo models stop after 37 to
  61 rounds and took 1 to 3 hours each. We checked first that this does
  not change results: the single-family main model refitted at 0.00002
  with the same bandwidths moved no coefficient by more than 0.33 of its
  standard error (median changes under 0.1), no standard error by more
  than 4.6%, the flood median from -0.019% to -0.015%, significant flood
  estimates 0 and 0, held-out error 10.69% both.
- **Full-size single-family run** (all 14,350 training sales) was stopped
  after 13 hours 25 minutes without finishing (D-190); nothing from it is
  used.

## 3. Fixed effects and MGWR side by side (estimated)

| | Single-family | Condo |
|---|---|---|
| Fixed effects, flood rate (95% range) | -0.03% (-0.16% to +0.11%), not significant | +0.57% (+0.19% to +0.95%), significant |
| Fixed effects, frequent storms | -0.04% (-0.23% to +0.15%), not significant | +0.49% (+0.03% to +0.95%), significant |
| MGWR, flood rate median | -0.02% | +1.22% |
| Countywide OLS, flood rate | -0.25% (SE 0.20) | -4.66% (SE 0.87) |
| Held-out error, fixed effects | 10.7% | 10.9% |
| Held-out error, MGWR | 10.7% | 12.8% |
| Held-out error, OLS | 20.2% | 31.1% |
| Share of flood rate variation within block groups | 40% | 40% |

- The countywide OLS shows a discount, but it compares homes in different
  neighbourhoods; once location is accounted for (fixed effects or MGWR)
  the discount goes away. Flood-exposed areas differ in many other ways
  from the rest of the county.
- About 40% of the flood rate's variation is within block groups, so the
  fixed-effects model has real variation to work with.

## 4. Six extra checks with fixed effects (estimated)

Each check replaces the flood rate with another flood measure, or keeps the
main model on a subset of sales (D-195). Tests 2 and 3 are block group
averages, the same for every sale in a block group, so they use one dummy
per census tract instead of per block group (comparing block groups in the
same tract). Significant means p below 0.05.

| Test | Measure (unit) | Single-family: effect (95% range) | Sig. | Condo: effect (95% range) | Sig. |
|---|---|---|---|---|---|
| Main | Flood rate (per unit) | -0.03% (-0.16% to +0.11%) | no | +0.57% (+0.19% to +0.95%) | yes |
| Main, tract dummies | Flood rate (per unit) | +0.01% (-0.12% to +0.14%) | no | +0.58% (+0.17% to +0.98%) | yes |
| 1. FEMA zone | In the 1% zone, 2027 maps (yes/no) | +1.19% (-0.06% to +2.45%) | no (p 0.06) | -3.00% (-7.21% to +1.39%) | no |
| 1. VE against AE | VE zone | not possible: 0 sales in VE | | not possible: 13 sales in VE | |
| 2. Insurance cost | Average NFIP premium (per $100 a year) | +0.46% (-0.19% to +1.12%) | no | -0.06% (-1.10% to +1.00%) | no |
| 3. Flood experience | NFIP claims since 2010 (per 10 per 1,000 homes) | +0.70% (+0.29% to +1.10%) | yes, positive | +1.98% (+0.74% to +3.24%) | yes, positive |
| 4. Step effect | Low against none | +0.93% (-0.49% to +2.37%) | no | -2.04% (-8.09% to +4.41%) | no |
| | Medium against none | +1.26% (-0.37% to +2.91%) | no | +3.04% (-2.50% to +8.90%) | no |
| | High against none | +0.86% (-1.12% to +2.88%) | no | +7.07% (+1.51% to +12.9%) | yes, positive |
| | Very high against none | -0.21% (-2.80% to +2.44%) | no | +12.5% (+5.79% to +19.6%) | yes, positive |
| 5. Away from water | Flood rate, not waterfront and over 500 m from water (per unit) | +0.04% (-0.12% to +0.20%) | no | +0.95% (+0.21% to +1.70%) | yes |
| 6. Better floor heights | Flood rate, block groups with their own elevation certificates (per unit) | -0.06% (-0.21% to +0.08%) | no | +1.14% (+0.55% to +1.73%) | yes |

Details:
- **Sales in each test:** all sales except: premium 15,758 single-family
  and 18,251 condo (block groups with at least 10 policies); away from
  water 10,029 and 5,461; better floor heights 13,599 and 13,624.
- **Group cut points (flood rate):** single-family 1.5, 2.9, 6.6;
  condo 0.2, 0.9, 2.5. About 40% of sales have a rate of zero ("none").
- **With the flood rate added back** (tests 1 to 3), the results above
  hardly change, and the flood rate stays near zero for single-family and
  about +0.5% to +0.6% for condo.

What the checks say:
- **Single-family:** nothing shows a discount. The FEMA zone comes closest
  to significance, and it is positive. More past claims go with slightly
  higher prices within a tract; past claims also track insurance take-up,
  which is higher in wealthier coastal areas, so this is not a sign that
  flood experience raises prices.
- **Condo:** the positive link grows with the flood rate (+7% and +13% in
  the two highest groups) and survives away from water and with good
  floor height data. The most exposed condo buildings are mostly
  waterfront and bay-front towers. The model controls for waterfront and
  distance to water, but not for views, the unit's floor or building
  amenities, which are not in the data. We therefore read the condo result
  as unmeasured amenities, not as a flood premium, and do not use it as
  evidence that flood risk raises condo prices.

## 5. Value and tax for the two test projects

Two example projects from Module C (the same as before): an 8 ft seawall
in North Miami and raising 3 ft of homes in Princeton. Value change is the
2026 just value of each single-family and condo building times the price
effect of its lower flood rate. Other buildings (472 for the seawall, 37
for the elevation) get no value change. Tax is the change in county
property tax after Florida's assessment caps, year 1 and year 10, assuming
no sale (D-182). Low and high use the coefficient minus and plus two
standard errors; published scenarios have one fixed coefficient, so no
range.

Coefficients carried to every building (median % per unit of flood rate):

| Case | Single-family | Condo | Type |
|---|---|---|---|
| MGWR main | -0.01% | +2.14% | estimated |
| Fixed effects | -0.03% | +0.57% | estimated |
| Published, Miami-Dade 3% (central) | -0.66% | -1.03% | assumption |
| Published, meta-analysis 4.6% | -1.01% | -1.59% | assumption |
| Published, sea level rise 7% | -1.56% | -2.44% | assumption |

A published discount for being inside the FEMA 1% zone becomes a
coefficient by dividing it over the gap in mean flood rate between
buildings inside and outside the 2027 1% zone (single-family 5.39 against
0.77; condo 3.76 against 0.82).

Seawall, North Miami (losses avoided $1.51M a year, Module C):

| Case | Value change, mid (low to high) | Single-family part | Condo part | Tax year 1 | Tax year 10 |
|---|---|---|---|---|---|
| MGWR main (estimated) | -$9.6M (-$18.7M to +$0.1M) | +$0.7M | -$10.3M | -$111k | -$161k |
| Fixed effects (estimated) | -$1.3M (-$6.7M to +$4.3M) | +$0.8M | -$2.1M | -$17k | -$25k |
| Published 3%, Miami-Dade (assumption) | +$24.2M | +$20.2M | +$4.0M | +$137k | +$246k |
| Published 4.6% (assumption) | +$38.0M | +$31.7M | +$6.3M | +$197k | +$375k |
| Published 7% (assumption) | +$60.0M | +$50.1M | +$9.9M | +$285k | +$574k |

Elevation 3 ft, Princeton (losses avoided $8.01M a year, Module C):

| Case | Value change, mid (low to high) | Single-family part | Condo part | Tax year 1 | Tax year 10 |
|---|---|---|---|---|---|
| MGWR main (estimated) | -$22.5M (-$50.3M to +$6.3M) | -$1.1M | -$21.4M | -$210k | -$279k |
| Fixed effects (estimated) | -$19.4M (-$42.0M to +$3.8M) | +$1.8M | -$21.2M | -$194k | -$257k |
| Published 3%, Miami-Dade (assumption) | +$86.0M | +$44.4M | +$41.6M | +$425k | +$598k |
| Published 4.6% (assumption) | +$135.9M | +$69.9M | +$66.0M | +$552k | +$873k |
| Published 7% (assumption) | +$216.7M | +$110.9M | +$105.9M | +$701k | +$1.32M |

How to read this:
- **Single-family (estimated):** about zero in both projects and both
  models (-$1.1M to +$1.8M), as expected from a flood coefficient of about
  zero.
- **Condo (estimated):** negative, because the condo coefficient is
  positive: lower flood risk times a positive coefficient gives a lower
  value. Section 4 explains why we do not read the positive condo
  coefficient as a flood premium, so these condo losses should not be
  taken as a real cost of the projects. Our suggestion is to show the
  condo value change as "not estimated reliably" and use the published
  scenario for condos; this is for the user and professor to decide.
- **Published scenarios (assumption):** these show the benefit if buyers
  priced flood risk as the cited studies found: $24M to $60M for the
  seawall and $86M to $217M for the elevation project, with county tax
  gains of $137k to $285k (seawall) and $425k to $701k (elevation) in
  year 1.
- The frequent-storm and dollar variants are in
  `value_tax_examples.json` for comparison (no tax computed).

## 6. Why a zero estimate is plausible: underpricing research

- Bakkensen and Barrage (2022, Review of Financial Studies 35(8)) find
  wide differences in flood-risk beliefs among coastal home buyers, with
  many buyers underestimating risk, so prices reflect less than the full
  risk.
- Gourevitch and others (2023, Nature Climate Change 13) estimate that US
  homes in flood zones are overvalued by $121 to $237 billion compared with
  prices that reflect flood risk, with Florida among the most overvalued
  states.
- Hino and Burke (2021, PNAS 118(17)) find that homes in the floodplain
  sell at a discount mainly where sellers must disclose flood risk; Florida
  had no seller disclosure law for flood risk until 2024.
- Keenan, Hill and Gumber (2018, Environmental Research Letters 13(5)) find
  that higher-elevation homes in Miami-Dade have appreciated faster, a sign
  that buyers are beginning to price elevation and flood exposure slowly
  over time.

Our result (no discount for single-family on 2025 to 2026 qualified sales)
is consistent with these findings. The published discounts in the scenario
show the size of the benefit if buyers came to price flood risk as some
other markets and periods do.

## 7. Limits

- **Sample size:** 10,000 training sales per MGWR model, not every sale
  (D-190); the fixed-effects model uses every sale.
- **Condo flood rate** is the same for all units in a building (D-184), so
  unit floor and views are not separated from flood exposure.
- **Flood rate** comes from our own damage model (Modules A to C), with
  floor heights from NFIP elevation certificates where available (D-185);
  errors in it would weaken any estimated effect toward zero.
- **Tests 2 and 3** compare block groups within tracts; their variation is
  coarser than the flood rate's.
- **Tax** assumes no sale for 10 years (a sale resets the assessment cap),
  which understates the tax change.

## Published sources

- Fu, X. and Nijman, J. (2021). Sea level rise, homeownership, and
  residential real estate markets in South Florida. The Professional
  Geographer 73(1). 3% floodplain discount, Miami-Dade (scenario, central).
- Beltran, A., Maddison, D. and Elliott, R. (2018). Is flood risk
  capitalised into property values? Ecological Economics 146: 668-685.
  4.6% meta-analysis discount (scenario).
- Bernstein, A., Gustafson, M. and Lewis, R. (2019). Disaster on the
  horizon: the price effect of sea level rise. Journal of Financial
  Economics 134(2): 253-272. 7% discount for exposure to sea level rise
  (scenario).
- Bakkensen, L. and Barrage, L. (2022). Going underwater? Flood risk belief
  heterogeneity and coastal home price dynamics. Review of Financial
  Studies 35(8): 3666-3709.
- Gourevitch, J. and others (2023). Unpriced climate risk and the potential
  consequences of overvaluation in US housing markets. Nature Climate
  Change 13: 250-257.
- Hino, M. and Burke, M. (2021). The effect of information about climate
  risk on property values. PNAS 118(17): e2003374118.
- Keenan, J., Hill, T. and Gumber, A. (2018). Climate gentrification: from
  theory to empiricism in Miami-Dade County, Florida. Environmental
  Research Letters 13(5): 054001.

## Files

- Scripts: `scripts/benefit/module_d_fit.py`, `module_d_fe.py`,
  `module_d_fe_tests.py`, `module_d_value_tax.py`, `module_d_queue.py`,
  `module_d_tol_check.py`, `nfip_floor_heights.py`;
  `scripts/common/progress.py`.
- Results: `outputs/benefit/module_d/n10000/` (MGWR models),
  `fe_block_group.json`, `fe_tests.json` and `.csv`, `tol_check.json`,
  `value_tax_examples.json`.
