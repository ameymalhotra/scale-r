# Stage 3: Property value model (RAISE-style hedonic model)

> **Draft, paused (D-159).** The professor's specification changes this model: the key
> variable becomes flood risk (expected yearly damage from Stage 2) instead of distance to
> project types, with separate single-family and condo MGWR models. The results below are
> kept for reference only and will not be used in Stage 4.

Benefit simulator, Phase 1. 11 Nov 2026. Branch `benefit-simulator`.
Decisions D-149 to D-158 in `DECISIONS.md`.

## In short

- **What we asked.** Do homes near completed and ongoing resilience projects
  sell for more, holding everything else equal? We used 40,901 qualified
  sales from 2025 and 2026: 17,935 single-family homes (median price
  $670,000) and 22,966 condo units (median price $430,000).
- **Main answer: mostly no clear effect.** For 14 of the 16 combinations of
  project type, distance band and home type, the estimate is too uncertain
  to use. Usually it shrinks or changes sign once homes are compared only
  with others in the same neighbourhood.
- **Two effects are "indicative"** (they hold within the same tract and the
  same block group):
  - single-family homes 500 m to 1 km from a **hybrid** project sell for
    about **+2% to +5%** more (main estimate +4.6%, about $31,000 at the
    median price; 95% interval +0.3% to +9.1%);
  - condos within 500 m of a **green** project sell for about **10% to 15%
    less** (main estimate -14.6%, about -$63,000; interval -23% to -5%).
    This is more likely about where green projects are placed than about
    what they do to prices (section 5).
- **Blue projects** (living shorelines and similar) show large positive
  differences, up to +90% for condos within 500 m. But there are only 15
  such projects. Most of the difference disappears within the same area,
  so it reflects waterfront locations, not the projects.
- **Model quality.** On held-out areas, XGBoost explains 83% of the
  variation in single-family log prices and 77% for condos; OLS explains
  73% and 49%. Adding the project features does not improve the
  single-family predictions at all.
- **The before-and-after test cannot be done** with this file: every sale
  is from 2025 or 2026. We ran the other bias checks instead.
- **FHFA check.** Tracts with more projects did not see clearly faster
  house price growth from 2019 to 2024 than similar tracts.

- **MGWR** (local model, two samples of 2,000 single-family sales):
  - It gives the same local pattern in both samples.
  - Hybrid projects go with higher prices in central and northern areas
    (Miami, Coral Gables, North Miami: about +4% to +7% per halving of
    distance) and slightly lower prices in the far south (Cutler Bay,
    Palmetto Bay: about -1% to -2%).
  - Gray projects show almost no effect anywhere.
  - Green projects go both ways.
  - MGWR's own standard errors could not be used on these data, so these
    local patterns have no intervals; the intervals in this report come
    from OLS.

## 1. Sources

| Publisher | Dataset and version | Data years vs release year | Where downloaded | File |
|---|---|---|---|---|
| Florida Department of Revenue | 2026 final tax roll (NAL), Miami-Dade (county 23) | sales 2025 to 2026; released 2026 | DOR data portal (Stage 1) | `data/raw/dor/Dade_23_Final_NAL_2026.zip` |
| Florida Department of Revenue | 2026 parcel and condo GIS, Miami-Dade | 2026 | DOR data portal (Stage 1) | `data/raw/dor/miamidade_2026Ppar.zip`, `miamidade_condos_2026.zip` |
| Stage 1 and 2 (this project) | Building table (flood zone, elevation, sea level rise, surge) and tract NFIP claims per unit | see Stage 1 and 2 reports | built here | `buildings.parquet`, `ead_tract.csv` |
| SCALE-R | Project database (location, type, status, cost) | reported 2012 to 2026 | project file | `data/raw/projects/SCALE-R_Database.csv` |
| Miami-Dade County (MDPublisher) | Metrorail Station; Public School; County Park Boundary; Municipal Park Boundary | layers last edited Jun 2025, Nov 2025, Oct 2026 and Sep 2024; downloaded 11 Nov 2026 | ArcGIS Online, Miami-Dade open data | `data/raw/mdc_layers/` |
| US Census Bureau | TIGER 2024 area water (coast), block groups, tracts, places | 2024 | already on disk | `data/raw/boundaries/` |
| US Census Bureau and EPA | Block group ACS 2020-2024 and EJScreen 2024 indicators (project table) | 2020 to 2024 | already on disk | `data/processed/analysis/blockgroup_analysis.csv` |
| SCALE-R (Landsat) | Surface temperature composite | current composite | already on disk | `output/lst/lst_composite_f.tif` |
| FHFA | Census tract house price index, 2020 tracts | to 2025 (222 tracts with 2025) | Stage 1 | `data/raw/fhfa/hpi_at_tract_miami_dade.csv` |

## 2. The data

**Sales** (D-149).
- Kept: qualified sales (codes 01 and 02) of improved single-family homes
  and condo units, sale 1 and sale 2 of the 2026 roll.
- Dropped: the lowest and highest 0.5% of prices in each group, and rows
  with no living area or year built.
- The repeat sales of 765 parcels are both kept.
- Each sale is placed inside its parcel; condo units take their
  building's parcel.

**Features** (D-152).

| Group | Features |
|---|---|
| Structure | living area, lot size (single-family only), age |
| Time | month of sale |
| Neighbourhood (block group) | median family income, low income %, people of colour %, over 64 %, less than high school %, owner-occupied %, unemployment %, no vehicle % |
| Access | distance to the coast, downtown (Government Center), nearest Metrorail station, nearest major park (10 acres or more), nearest public school |
| Hazard | FEMA 100-year zone, ground elevation, sea level rise 3 ft and 6 ft, Category 3 worst-case surge depth, surface temperature, tract NFIP claims per housing unit |
| Projects (main) | for gray, green, blue and hybrid: a project within 500 m; a project 500 m to 1 km away |
| Projects (check) | distance to nearest, number within 500 m, dollars within 1 km |

**Projects** (D-151).
- Kept: completed and ongoing projects whose point marks a real place
  (parcel, corridor or neighbourhood scale): 969 projects (gray 800,
  hybrid 118, green 36, blue 15).
- Left out: municipality-wide and county-wide projects, whose point is
  only a stand-in for the whole area.

How many sales are near each type:

| Type | Single-family within 500 m | Single-family 500 m to 1 km | Condo within 500 m | Condo 500 m to 1 km |
|---|---|---|---|---|
| Gray | 6,151 | 6,383 | 12,152 | 6,825 |
| Hybrid | 1,077 | 2,280 | 4,591 | 5,188 |
| Green | 301 | 692 | 1,709 | 3,539 |
| Blue | 164 | 439 | 246 | 791 |

## 3. How well the models predict (spatial cross-validation)

Each test holds out whole groups of tracts (10 spatial folds), so the
model is always judged on areas it has not seen.

| Model | Single-family R2 | Single-family typical error | Condo R2 | Condo typical error |
|---|---|---|---|---|
| Baseline: average by month | -0.08 | 34% | -0.06 | 40% |
| OLS: structure only | 0.55 | 24% | 0.18 | 43% |
| OLS: + neighbourhood, access, hazard | 0.74 | 21% | 0.40 | 37% |
| OLS: + projects (full) | 0.73 | 21% | 0.49 | 35% |
| XGBoost (full) | **0.83** | **15%** | **0.77** | **21%** |

- "Typical error" is the median absolute percentage error of the
  predicted price.
- For single-family homes, adding the project features does not improve
  predictions.
- For condos, it adds 0.09, but that gain comes mainly from blue projects
  near the beach, which mark waterfront location.
- Condo prices depend on floor, view and building, which the tax roll
  does not describe, so the condo models are weaker.

**Residual Moran's I** (how much nearby errors look alike; 0 means no
pattern):

| Model | Single-family | Condo |
|---|---|---|
| OLS (block group controls) | 0.48 | 0.61 |
| OLS with tract fixed effects | 0.10 | 0.22 |
| XGBoost (held-out errors) | 0.55 | 0.66 |
| MGWR (2,000-sale samples) | 0.15 and 0.12 | not run |

All are significant (p = 0.005). Prices still share a strong local
pattern that the features do not capture; this is what MGWR is meant to
address. Tract fixed effects remove most of it.

Other results from the main OLS (single-family, holding all else equal):
- each doubling of distance to the coast lowers price by about 12%;
- a home in the FEMA 100-year zone sells for about 3% less;
- each foot of worst-case Category 3 surge depth lowers price by about
  4%.

## 4. Value of being near each project type

These are the main results. "Main" is OLS with block group controls,
with 95% intervals clustered by tract. Dollars are at the median price of
each home type ($670,000 single-family, $430,000 condo).

The bias checks show how much each estimate moves when homes are compared
only with homes **in the same tract** or **in the same block group**.
"Just value" repeats the main model with the appraiser's value instead of
the sale price.

| Home type | Project and distance | Sales in band | Main estimate (95% interval) | Dollars at median (95% interval) | Same tract | Same block group | Just value | Verdict |
|---|---|---|---|---|---|---|---|---|
| Single-family | Gray, within 500 m | 6,151 | -0.4% (-3.9 to +3.3) | -$2k (-26k to +22k) | +2.0% (-0.3 to +4.4) | +1.3% (-0.9 to +3.5) | -0.3% (-3.6 to +3.2) | too uncertain |
| Single-family | Gray, 500 m to 1 km | 6,383 | +2.3% (-0.8 to +5.5) | +$15k (-5k to +37k) | +2.1% (+0.5 to +3.7) | +1.3% (-0.3 to +2.9) | +2.0% (-0.9 to +5.1) | too uncertain |
| Single-family | Hybrid, within 500 m | 1,077 | -0.1% (-7.0 to +7.2) | -$1k (-47k to +49k) | +1.9% (-2.3 to +6.3) | +3.1% (-0.7 to +7.1) | -2.1% (-8.5 to +4.8) | too uncertain |
| Single-family | **Hybrid, 500 m to 1 km** | 2,280 | **+4.6% (+0.3 to +9.1)** | **+$31k (+2k to +61k)** | +2.0% (-1.0 to +5.0) | +3.4% (+0.4 to +6.4) | +2.6% (-1.5 to +6.9) | **indicative** |
| Single-family | Green, within 500 m | 301 | +1.1% (-7.6 to +10.7) | +$7k (-51k to +71k) | +2.8% (-10.4 to +18.0) | -5.7% (-17.0 to +7.2) | +2.5% (-6.5 to +12.5) | too uncertain |
| Single-family | Green, 500 m to 1 km | 692 | -3.7% (-10.5 to +3.6) | -$25k (-71k to +24k) | -1.5% (-8.4 to +5.9) | -4.5% (-11.4 to +3.0) | -3.3% (-9.5 to +3.3) | too uncertain |
| Single-family | Blue, within 500 m | 164 | +8.4% (-1.7 to +19.5) | +$56k (-11k to +130k) | -0.6% (-6.7 to +5.8) | -4.0% (-9.9 to +2.2) | +7.3% (-1.9 to +17.4) | too uncertain (too few sales) |
| Single-family | Blue, 500 m to 1 km | 439 | +14.6% (+8.3 to +21.3) | +$98k (+56k to +143k) | +2.6% (-2.1 to +7.6) | +0.7% (-3.5 to +5.2) | +12.5% (+6.4 to +18.9) | too uncertain |
| Condo | Gray, within 500 m | 12,152 | -3.7% (-11.3 to +4.6) | -$16k (-49k to +20k) | -5.9% (-14.5 to +3.5) | -2.5% (-8.4 to +3.7) | -4.0% (-11.5 to +4.2) | too uncertain |
| Condo | Gray, 500 m to 1 km | 6,825 | -5.0% (-11.4 to +1.8) | -$22k (-49k to +8k) | -9.3% (-17.4 to -0.5) | -3.3% (-8.0 to +1.5) | -5.4% (-11.7 to +1.3) | too uncertain |
| Condo | Hybrid, within 500 m | 4,591 | -4.2% (-12.8 to +5.3) | -$18k (-55k to +23k) | -10.2% (-18.7 to -0.7) | -3.0% (-16.2 to +12.2) | -3.9% (-12.3 to +5.4) | too uncertain |
| Condo | Hybrid, 500 m to 1 km | 5,188 | -4.7% (-12.2 to +3.4) | -$20k (-52k to +15k) | -8.7% (-15.0 to -1.9) | -5.2% (-11.2 to +1.2) | -5.3% (-12.6 to +2.6) | too uncertain |
| Condo | **Green, within 500 m** | 1,709 | **-14.6% (-23.2 to -5.2)** | **-$63k (-100k to -22k)** | -10.3% (-18.5 to -1.3) | -11.5% (-21.7 to +0.1) | -13.8% (-22.1 to -4.5) | **indicative (see caution)** |
| Condo | Green, 500 m to 1 km | 3,539 | -7.6% (-15.5 to +1.0) | -$33k (-66k to +4k) | -4.2% (-11.7 to +3.9) | -5.9% (-15.1 to +4.2) | -7.6% (-15.3 to +0.8) | too uncertain |
| Condo | Blue, within 500 m | 246 | +90.2% (+47.7 to +145.0) | +$388k (+205k to +623k) | +27.5% (+3.6 to +56.8) | +17.4% (+2.1 to +34.9) | +87.9% (+47.0 to +140.1) | too uncertain (too few sales) |
| Condo | Blue, 500 m to 1 km | 791 | +59.7% (+35.5 to +88.2) | +$257k (+153k to +379k) | +3.5% (-7.8 to +16.2) | +7.3% (-0.5 to +15.8) | +57.5% (+33.9 to +85.3) | too uncertain |

**Rule for "indicative"** (D-154). All three must hold:
- at least 300 sales in the band;
- the same sign in the main, same-tract and same-block-group models;
- at least two of those three intervals exclude zero.

Otherwise the estimate is too uncertain to use.

**XGBoost comparison.** XGBoost estimates the average change in predicted
price when every held-out sale is moved into each band (mean of the 10
fold models):

| Home type | Gray | Hybrid | Green | Blue |
|---|---|---|---|---|
| Single-family, within 500 m | +0.3% | -0.7% | -0.4% | -0.6% |
| Single-family, 500 m to 1 km | +0.2% | +0.4% | 0.0% | +3.7% |
| Condo, within 500 m | +0.7% | +0.4% | -0.9% | +2.4% |
| Condo, 500 m to 1 km | -0.2% | +0.5% | -0.4% | +8.8% |

The fold-to-fold ranges are in `xgb_summary.json`; for blue projects they
are very wide (for example -12% to +30% for condos within 500 m). XGBoost
agrees that the effects of gray, hybrid and green projects are small,
within about 1%.

### MGWR: how the effects vary across the county

**How the sample was drawn** (D-153).
- 2,000 single-family sales, stratified by tract: each tract contributes
  in proportion to its share of sales, at least one where it has any.
- Two independent samples were drawn with different seeds (101 and 202).
  They cover 566 and 563 tracts, 560 of them in both.
- Price is first adjusted for the month of sale.

**What goes in.**
- Covariates: living area, lot size, age, distance to the coast, ground
  elevation, and distance to the nearest gray, hybrid and green project.
- Blue projects are too few for a 2,000-sale sample.
- Distance to downtown and neighbourhood income were taken out. Locally
  they move together with the coast distance and the local intercept,
  which made the local fits unstable (median local condition number 48).
  The local intercept now carries neighbourhood price levels.
- Each covariate can work at its own scale, with at least 500 neighbours.

**What went wrong first, and what that means.**
- Two earlier runs, with more covariates and smaller minimum
  bandwidths, produced broken standard errors.
- In the final run the standard errors are finite but still implausibly
  large. Tests on synthetic data showed the package itself works, and the
  cause in our data was not found.
- So **MGWR is used only to describe how effects vary**, and we test that
  by checking the two samples agree. All confidence intervals in this
  report come from OLS.

**Stability across the two samples.**

| Item | Sample 101 | Sample 202 | Tract-by-tract agreement (Spearman, 560 tracts) |
|---|---|---|---|
| R2 (in sample) | 0.89 | 0.88 | |
| Residual Moran's I | 0.15 | 0.12 | |
| Bandwidth, gray (neighbours) | 1,017 | 1,998 (whole sample) | 0.77 |
| Bandwidth, hybrid | 530 | 501 | 0.86 |
| Bandwidth, green | 501 | 501 | 0.93 |
| Coast distance, living area, lot, age, elevation | 501 each | 501 each | 0.89 to 0.99 |

The two samples agree closely, so the local patterns below are not a fluke
of one sample. MGWR also removes most of the leftover spatial pattern:
residual Moran's I is 0.12 to 0.15, against 0.48 for OLS.

**Change in price per halving of distance to the nearest project.**
Middle 80% of locations, both samples:

| Project type | Sample 101 (10th / median / 90th percentile) | Sample 202 |
|---|---|---|
| Gray | -1.3% / +0.2% / +2.2% | -0.1% / +0.1% / +0.4% |
| Hybrid | -0.4% / +2.7% / +8.2% | -1.2% / +1.6% / +6.2% |
| Green | -5.2% / -1.1% / +9.3% | -6.5% / -1.3% / +12.3% |

**By area** (median over sales in both samples; places with at least 40
sampled sales; full list in `outputs/benefit/stage3/mgwr_by_place.csv`):

| Project type | Lowest | Highest |
|---|---|---|
| Hybrid | Cutler Bay -1.7%, Palmetto Bay -1.2%, Princeton -1.1% | Coral Terrace +7.3%, Coral Gables +7.1%, West Little River +6.6%, Miami +6.5% |
| Green | Coral Gables -6.1%, Miami -5.4%, Coral Terrace -4.9% | Miami Gardens +13.3%, Biscayne Gardens +13.1%, North Miami Beach +12.3%, North Miami +10.8% |
| Gray | West Little River -0.9% | Leisure City +2.2%, Cutler Bay +1.8% |

How to read this:
- **Hybrid:** the positive association found by OLS for single-family
  homes is concentrated in central and northern Miami-Dade.
- **Green:** the sign changes from place to place, matching the
  uncertain OLS results. It should not be used as a project effect.
- **Gray:** essentially no association anywhere.
- These local values have no intervals. They show where an effect is
  larger or smaller; they are not proof of an effect.


## 5. Bias checks: how much the estimates move

Projects are not placed at random. Gray drainage works go where streets
flood. Blue projects go on the waterfront. Green projects often go into
dense, lower-income neighbourhoods with grant support. Each of these can
make "near a project" look good or bad for reasons that have nothing to
do with the project.

- **Before and after: not possible.** The 2026 tax roll holds only each
  parcel's two most recent sales, and all qualified sales are from 2025 and
  2026. No sale took place before most projects' document year (mostly
  2020 to 2025), so prices before and after a nearby project cannot be
  compared with this file. An older sales history (earlier NAL years or
  the county's sales file) would be needed.
- **Same tract and same block group** (fixed effects). Comparing a home
  only with homes in the same small area removes most neighbourhood
  differences.
  - Blue: +60% to +90% for condos falls to +3% to +27%; +15% for
    single-family 500 m to 1 km falls to +1% to +3%. The raw blue
    differences are mostly about waterfront location.
  - Gray and hybrid near condos turn more negative within the same tract
    (down to -10%). This is consistent with projects being placed where
    flooding is worst, and their effect is still unclear.
  - Hybrid, 500 m to 1 km from single-family homes, stays positive (+2% to
    +5%).
  - Green within 500 m of condos stays negative (-10% to -15%). Green
    projects in this database are often in older, denser neighbourhoods
    with grant funding. The negative sign is more likely about those
    places than about the projects, so we would not use it as a project
    effect.
- **Distance, counts and dollars** (check D).
  - Single-family: being closer to a hybrid project goes with a higher
    price (each halving of distance +3.3%, p = 0.004). Gray and green show
    nothing clear.
  - Condo: being closer to green and hybrid projects goes with lower
    prices, and closer to blue with higher prices, consistent with the
    location effects above.
- **Just value** gives almost the same estimates as sale prices.

## 6. FHFA check: did tracts with more projects see faster growth?

House price growth from 2019 to 2024 (FHFA tract index, median +82%) was
compared across 223 tracts. Controls: earlier growth (2014 to 2019),
income, distance to the coast and flood zone share (D-156).

| Projects in the tract (log of 1 + number) | Change in 2019-2024 growth per unit | 95% interval |
|---|---|---|
| All types together | +0.012 | -0.027 to +0.052 |
| Gray | +0.013 | -0.027 to +0.052 |
| Hybrid | +0.036 | -0.064 to +0.135 |
| Green | -0.117 | -0.341 to +0.107 |
| Blue | -0.062 | -0.236 to +0.112 |

No clear difference. The FHFA index covers only about a third of tracts
in recent years, and most projects were reported in 2020 or later, so
this check has little power.

## 7. What this means for Stage 4

- The property value change in the calculator will use only the
  indicative effect for **hybrid projects near single-family homes**
  (+2% to +5% within 500 m to 1 km), with that range. MGWR suggests it is
  larger in central and northern areas and near zero in the far south;
  Stage 4 can show that as a note, not as a separate number. All other types
  will show a property value change of "not estimated (too uncertain)",
  not zero.
- The blue and green results will not be used as project effects.
- Property value change stays separate from avoided losses (no double
  counting).

## 8. Limitations

- Only two years of sales, so prices cannot be followed over time.
- Condo prices depend on floor, view and building quality, which the tax
  roll does not record.
- Project points are approximate for corridor and neighbourhood projects.
- Only 15 blue and 36 green projects qualify.
- MGWR was run on samples of 2,000 single-family sales, and its own
  standard errors could not be used (D-153). It shows patterns, not
  tested effects.
- Project costs and types come from the SCALE-R database as entered.
- All results are associations, not proven effects. The within-area
  checks reduce, but do not remove, the influence of where projects are
  placed.

## 9. Files and rerun

From `Modelling Data from Web/`:

| Step | Command | Time |
|---|---|---|
| Sales table | `../.venv/bin/python -I scripts/benefit/build_sales_features.py` | 15 seconds |
| OLS, bias checks, FHFA | `../.venv/bin/python -I scripts/benefit/stage3_models.py` | 15 seconds |
| XGBoost | `bash scripts/ml/run_ml.sh scripts/benefit/stage3_xgb.py` (the ML environment is in the main checkout) | 40 seconds |
| MGWR (two samples) | `../.venv/bin/python -I scripts/benefit/stage3_mgwr.py 101` and `... 202` | about 4 minutes each, plus `stage3_mgwr_compare.py` |

Outputs:
- `data/processed/benefit/sales_features.parquet` (not committed);
- `outputs/benefit/stage3/`: `ols_project_effects.csv`,
  `ols_spatial_cv.csv`, `ols_summary.json`, `xgb_summary.json`,
  `mgwr_seed101.*`, `mgwr_seed202.*`, `mgwr_compare.json`,
  `mgwr_by_place.csv`, `projects_used.csv`, `build_log.json`. Do not use
  the `se_*` and `sig_*` columns of the MGWR files (D-153).
- Earlier MGWR attempts are kept in `mgwr_first_run/` and
  `mgwr_second_run/` for the record.
