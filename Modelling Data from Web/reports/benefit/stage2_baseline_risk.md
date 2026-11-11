# Stage 2: Baseline flood risk in dollars (DRAFT, stopped at the calibration check)

Status, 11 Nov 2026: the model runs for all 627,252 buildings, but the check
against real flood insurance claims shows the storm surge part is far too
high. Following the project rules, work stopped here for a decision (D-142).
The numbers below are not final and should not be quoted yet.

## In short

- **What was built.** For every building: water depth in each flood event,
  damage in dollars, expected annual damage (EAD), displacement costs and
  people exposed, today and with 1, 2 and 3 ft of sea level rise.
- **The problem.** Modelled EAD is about **$7.9 billion a year**. Flood
  insurance (NFIP) payments in Miami-Dade average about **$20 million a
  year**. Almost all of the modelled figure ($7.9 billion) comes from the
  storm surge maps.
- **Why.** The NHC surge maps show the *worst* flooding any storm of a given
  category could cause, anywhere along the coast, at high tide. A real storm
  floods only part of that area. Treating the worst case as what happens
  every time a hurricane of that category hits Southeast Florida inflates the
  yearly figure many times over. For example, the Category 5 map damages $132
  billion of buildings; Hurricane Andrew (Category 5, 1992) led to $138
  million of NFIP payments.
- **FEMA flood zones alone** give about **$354 million a year** (estimated
  from our data), about 17 times the claims. Most of that gap is expected:
  many homes are not insured, payments are capped and have deductibles, and
  old claims are in old dollars.
- **Decision needed** (options in section 6). Recommended: use the FEMA 1%
  and 0.2% floods for the yearly figure, and show the surge maps as
  worst-case scenarios.

## 1. Sources

| Publisher | Dataset and version | Data years vs release | Where downloaded | File |
|---|---|---|---|---|
| Stage 1 (this project) | Building table, NSI 2026 with tax roll, flood zones, surge, sea level rise | see Stage 1 report | built in Stage 1 | `data/processed/benefit/buildings.parquet` |
| USACE | go-consequences occupancy damage curves, commit dff647c | curves as published; library 2021 | GitHub (Stage 1) | `data/reference/depth_damage_curves.csv` |
| FEMA | BCA standard values (displacement), page-checked | FY2025 and 2021 dollars; documents 2024 to 2025 | fema.gov (Stage 1) | `data/reference/fema_standard_values.csv` |
| NOAA NHC | Technical Memorandum NWS NHC-6, Table 10 (hurricane strikes by category) | 1851 to 2010; published Aug 2011 | nhc.noaa.gov/pdf/nws-nhc-6.pdf | `data/raw/reference_docs/nhc/nws-nhc-6.pdf` |
| NOAA NHC | Hurricane and major hurricane return period maps (HURISK) | data to 2010; page current 2026 | nhc.noaa.gov/climo | `data/raw/reference_docs/nhc/return_hurr.jpg`, `return_mjrhurr.jpg` |
| FEMA | NFIP redacted claims, Miami-Dade (from the impact-data work) | 1978 to 2026; downloaded Nov 2026 | OpenFEMA | `data/processed/impact/nfip_claims_tract_year.csv` |
| US Census Bureau | ACS 5-year table B25003 (occupied housing units), block groups | 2020 to 2024; released 2025 | already on disk | `data/raw/social/acs_blockgroup/B25003-Tenure/` |
| SCALE-R | Sited investment by tract | project database | already on disk | `data/processed/investment/tract_investment.csv` |

## 2. Method in plain words

1. **Water depth at each building** for seven events:
   - storm surge Categories 1 to 5 (NHC maps);
   - the FEMA 1% flood: base flood elevation minus ground elevation. FEMA
     maps print no 0.2% elevation, so the 0.2% event uses the 1% depth (a
     lower bound).
   The first-floor height (NSI) is then subtracted to get the depth inside
   the building.
2. **Damage** = standard USACE depth-damage curve x structure value, plus
   the contents curve x contents value. Saltwater curves are used for surge.
   Dollars are NSI depreciated replacement value at August 2025 prices.
3. **Yearly chance of each event.**
   - FEMA events: 1% and 0.2% a year.
   - Hurricanes: NOAA counts of strikes on Southeast Florida, 1851 to 2010.
     A Category 1 or stronger storm comes about every 3.6 years; Category 3
     or stronger about every 11 years; Category 5 about every 160 years
     (assumption, D-136).
4. **Expected annual damage.** At each probability, the larger damage of
   the two hazard types is kept, never the sum, because FEMA's coastal
   flood elevations already include surge (D-137). Low and high values use
   the curves' uncertainty bands.
5. **Displacement.** FEMA's rent per square foot and one-time moving cost,
   with FEMA's example of 45 days away per foot of water, up to 225 days
   (assumption, D-139). FEMA prints no dollar value for mental stress or
   lost productivity, so those are not in dollars (D-133).
6. **Sea level rise.** Added to the water level of each event. Permanent
   high-tide flooding is counted separately, not as yearly damage (D-141).

## 3. Results so far (not final)

| Item (per year) | Low | Middle | High | Label |
|---|---|---|---|---|
| EAD, surge maps and FEMA zones together | $4.1 billion | $7.9 billion | $13.5 billion | estimated from our data (standard curves) |
| EAD, FEMA zones only | | $354 million | | estimated from our data |
| Displacement, middle | | $272 million | | assumption (FEMA standard values, 2021 dollars) |
| NFIP payments, weighted average | | $20 million | | observed (nominal dollars) |

FEMA-zone EAD with sea level rise: $354 million today, $635 million with
1 ft, $1.04 billion with 2 ft and $1.54 billion with 3 ft (middle values).

Permanent high-tide flooding (NOAA layers):

| Rise | Buildings | Structure value | Residents |
|---|---|---|---|
| 1 ft | 75 | $38 million | 87 |
| 2 ft | 506 | $446 million | 2,341 |
| 3 ft | 6,720 | $5.8 billion | 41,030 |
| 6 ft | 116,810 | $91.3 billion | 656,340 |

People: 101,786 buildings with 564,355 residents get water at the building
in the FEMA 1% flood.

## 4. Check against real claims (provisional)

As agreed, the check uses NFIP payments per occupied housing unit (ACS)
until the full policies file is on disk (D-140). Payments are weighted
toward recent years (weight halves every 15 years). They are **not**
inflation-adjusted: no price index is on disk, and one is not in the list
of downloads.

| Measure | All events | FEMA zones only | Surge only |
|---|---|---|---|
| Spearman, tract EAD per unit vs claims per unit (694 tracts) | 0.44 (95% interval 0.38 to 0.50) | 0.49 | 0.41 |
| Ratio of county totals, model / claims | about 390 (200 to 660) | about 17 | |

The ranking of tracts agrees moderately. The size does not.

## 5. Comparison with sited investment (preliminary)

Across 698 tracts with at least 100 residents, modelled risk per resident
and investment per resident have a Spearman correlation of 0.30. Of the 175
tracts in the top quarter of risk per resident, 48 are below the median of
investment per resident. These comparisons will be repeated once the risk
measure is settled.

## 6. Decision needed

- **A (recommended).** Yearly risk from the FEMA 1% and 0.2% floods, which
  already include surge along the coast. Surge maps are shown as
  worst-case "what if a Category 3 hits" scenarios, with damage per event
  but no yearly figure.
- **B.** Keep both and scale the surge part down to match the claims record
  (a large calibration factor, which needs justification).
- **C.** Keep the combined figure, labelled as an upper bound.

Also needed:
- the full NFIP policies file, to compare per insured home (the user is
  downloading it);
- permission to download one consumer price index series (BLS CPI-U), so
  claims can be inflation-adjusted as the brief asks.

## 7. Files and rerun

| Step | Command (from `Modelling Data from Web/`) |
|---|---|
| Hurricane frequencies | `../.venv/bin/python -I scripts/benefit/build_hurricane_rates.py` |
| Stage 2 run (about 20 seconds) | `../.venv/bin/python -I scripts/benefit/baseline_risk.py` |

Outputs:
- `data/processed/benefit/ead_buildings.parquet` (per building);
- `data/processed/benefit/ead_tract.csv` (per tract, with ranks);
- `outputs/benefit/stage2/` (summary, calibration deciles, top tracts,
  high-risk low-investment tracts).
