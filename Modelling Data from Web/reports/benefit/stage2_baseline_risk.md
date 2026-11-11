# Stage 2: Baseline flood risk in dollars (before any new project)

Benefit simulator, Phase 1. 11 Nov 2026. Branch `benefit-simulator`.
Decisions D-136 to D-147 in `DECISIONS.md`.

## In short

- **Yearly flood damage to buildings in Miami-Dade, today: about $174
  million a year** (range $94 million to $263 million). This is the
  expected annual damage (EAD) from the FEMA 1% and 0.2% annual chance
  floods, for 627,252 buildings. *Estimated from our data, with standard
  damage curves.*
- **Homes account for $92 million** of it, commercial buildings for $64
  million, and industrial and public buildings for the rest.
- **Sea level rise raises it quickly:** $351 million a year with 1 ft, $634
  million with 2 ft, and $1.0 billion with 3 ft.
- **Displacement** (rent and moving while a building is repaired) adds
  about **$10 million a year** (range $7 to $13 million). *Assumption:
  FEMA standard values, 2021 dollars.*
- **People.** 564,355 residents live in buildings that get water in the
  FEMA 1% flood. On average, about 9,900 residents a year live in a building
  that floods, and about 2,500 a year are displaced.
- **Storm surge worst cases** are shown separately, not as yearly figures.
  If the NHC worst-case Category 3 surge happened, 125,810 buildings with
  598,000 residents would get water, with $17 billion of damage.
- **Check against real claims (provisional).**
  - Flood insurance (NFIP) payments average $30 million a year in 2025
    dollars.
  - The model ranks tracts in a similar order to the claims (Spearman
    0.49).
  - The model's total is 5.7 times higher (4.0 for homes). Known factors
    explain part of the gap. What is left would mean that about 20% of
    home flood losses are insured; this will be checked with the
    policies file.
  - The model is not scaled to the claims.
- **Investment.** Risk per resident and sited investment per resident are
  only weakly related (Spearman 0.34). Of the 175 tracts with the highest
  risk per resident, 46 are below the median investment per resident.

**What the dollar labels mean.** "Estimated from our data" means
computed from our building inventory, maps and standard curves.
"Assumption" means based on published standard values. The two are kept
apart in every table.

## 1. Sources

| Publisher | Dataset and version | Data years vs release year | Where downloaded | File |
|---|---|---|---|---|
| Stage 1 (this project) | Building table: NSI 2026, tax roll, FEMA flood zones (effective 11 Sep 2009), surge, sea level rise, ground elevation | see Stage 1 report | built in Stage 1 | `data/processed/benefit/buildings.parquet` |
| USACE | go-consequences occupancy damage curves, commit dff647c | curves as published; library Dec 2021 | GitHub (Stage 1) | `data/reference/depth_damage_curves.csv` |
| FEMA | BCA standard values: displacement rent and one-time cost (Sustainment report), displacement days example (flood module report v6, Table 1) | 2021 dollars; documents 2025 | fema.gov (Stage 1) | `data/reference/fema_standard_values.csv` |
| NOAA National Hurricane Center | Technical Memorandum NWS NHC-6 (Blake, Landsea and Gibney), Table 10 | 1851 to 2010; published Aug 2011 | nhc.noaa.gov/pdf/nws-nhc-6.pdf | `data/raw/reference_docs/nhc/nws-nhc-6.pdf` |
| NOAA National Hurricane Center | Return period maps, hurricanes and major hurricanes (HURISK) | data to 2010; web page current 2026 | nhc.noaa.gov/climo | `data/raw/reference_docs/nhc/return_hurr.jpg`, `return_mjrhurr.jpg` |
| FEMA | NFIP redacted claims, Miami-Dade (from the impact-data work) | losses 1978 to 2026; downloaded Nov 2026 | OpenFEMA | `data/raw/fema/nfip_claims_miami_dade.csv`, `data/processed/impact/nfip_claims_tract_year.csv` |
| US Bureau of Labor Statistics | CPI-U, US city average, all items (CUUR0000SA0), not seasonally adjusted | 1978 to 2025 (Oct 2025 not published); downloaded 11 Nov 2026 | BLS Public Data API v1 | `data/raw/bls/cpiu_*.json`, `data/reference/cpi_u_annual.csv` |
| US Census Bureau | ACS 5-year, table B25003 (occupied housing units), block groups | 2020 to 2024; released 2025 | already on disk | `data/raw/social/acs_blockgroup/B25003-Tenure/` |
| US Census Bureau | TIGER places 2024 (tract labels in tables only) | 2024 | already on disk | `data/raw/boundaries/tl_2024_12_place.zip` |
| SCALE-R | Sited investment by tract | project database | already on disk | `data/processed/investment/tract_investment.csv` |

## 2. How the yearly risk is calculated

1. **Water depth at each building.**
   - FEMA 1% flood: base flood elevation (converted to NAVD88 in Stage 1)
     minus ground elevation from the NOAA elevation model.
   - FEMA 0.2% flood: FEMA maps print no 0.2% flood elevation, so the 1%
     depth is used. This is a lower bound.
   - Buildings in zone A (no elevation printed, 1,452 buildings) and in the
     shaded 0.2% zone X (34,893 buildings) get no FEMA depth.
   - The first-floor height (NSI foundation height) is subtracted to get
     the depth inside the building.
2. **Damage.**
   - A standard USACE depth-damage curve for each building type gives the
     share of the building and of its contents that is lost.
   - Dollars use NSI depreciated replacement value at August 2025 prices.
     A full replacement cost version is also kept: $203 million a year.
   - Saltwater curves are used in the coastal V zone; freshwater curves
     elsewhere.
3. **Tall buildings.** For apartments, commercial and public buildings,
   damage counts only on the floors the water reaches (D-143). Without
   this, a 12-story building with 3 ft of water would lose most of its
   whole value. With it, the county figure falls from $354 million to $174
   million. Ground floors often hold more value (lobbies, plant rooms), so
   this may understate damage in tall buildings.
4. **Yearly figure.** EAD = 1% x damage in the 1% flood + the extra
   damage between the 1% and 0.2% floods + the tail beyond 0.2%. The low
   and high values use the curves' uncertainty bands (D-137).
5. **Displacement** (D-139, D-145).
   - FEMA rent per square foot and FEMA's one-time moving cost, for the
     flooded floor only.
   - Time away: FEMA prints one example (a one-story house without
     basement), 45 days per foot of water, up to 225 days. We apply this
     single duration to **all** building types, which is an assumption.
   - Low case: half (22.5 days per foot). High case: one and a half times
     (67.5 days per foot). These multipliers are our sensitivity choice,
     not FEMA values.
6. **Mental stress and lost productivity.** FEMA describes the method but
   prints no dollar value in any document still available (D-133), so they
   are not in dollars. The people counts they would apply to are in
   section 4.
7. **Sea level rise** (D-141). 1, 2 and 3 ft are added to the FEMA flood
   elevation and the EAD is recomputed. Permanent high-tide flooding is
   counted separately.

**Why not the storm surge maps for the yearly figure?** The NHC surge maps
are "maximum of maximums": for each category, the worst depth any storm of
that category could bring, at high tide, along the whole coast. Any real
storm floods only part of that area. Paired with how often hurricanes of
each category strike Southeast Florida (NOAA, 1851 to 2010), they gave
$7.9 billion a year, about 390 times the claims record. On your decision
(D-142), the yearly figure uses the FEMA zones, whose coastal elevations
already include surge. The surge maps are kept as worst-case scenarios
(section 5).

## 3. Expected annual damage

### County totals

| Item (per year) | Low | Middle | High | Label |
|---|---|---|---|---|
| Buildings and contents, today | $94 million | $174 million | $263 million | estimated from our data |
| of which homes (residential) | | $92 million | | estimated from our data |
| of which commercial | | $64 million | | estimated from our data |
| of which industrial and public | | $18 million | | estimated from our data |
| Full replacement cost version | | $203 million | | estimated from our data |
| Displacement | $7 million | $10 million | $13 million | assumption (FEMA standard values, 2021 dollars; single duration for all types) |

Where the damage is:
- By flood zone: AE zones $124 million, AH (shallow ponding) $47 million,
  VE (coastal waves) $3 million.
- 89,627 buildings have some expected damage.
- The 1% of buildings with the most damage hold 54% of it, and the 10% of
  tracts with the most damage hold 63%.

### With sea level rise (middle values)

| Rise | Buildings and contents | Displacement | Residents flooded per year | Residents displaced per year |
|---|---|---|---|---|
| Today | $174 million | $10 million | 9,876 | 2,534 |
| +1 ft | $351 million | $19 million | 15,657 | 5,292 |
| +2 ft | $634 million | $38 million | 19,776 | 8,731 |
| +3 ft | $1.0 billion | $60 million | 21,449 | 11,375 |

Permanent high-tide flooding (NOAA layers), not part of the yearly figure:

| Rise | Buildings | Structure value | Residents |
|---|---|---|---|
| 1 ft | 75 | $38 million | 87 |
| 2 ft | 506 | $446 million | 2,341 |
| 3 ft | 6,720 | $5.8 billion | 41,030 |
| 6 ft | 116,810 | $91.3 billion | 656,340 |

### Top 10 tracts by dollars at risk (today)

| Tract | Place (largest share of buildings) | EAD, middle ($ million) | EAD range ($ million) | EAD per resident ($) | Residents wet in 1% flood | NFIP claims per year, 2025 $ (thousand) | Sited investment per resident ($) |
|---|---|---|---|---|---|---|---|
| 12086004602 | Key Biscayne | 5.6 | 2.9 to 8.7 | 1,283 | 4,318 | 1,366 | 6,010 |
| 12086008000 | Coral Gables | 4.2 | 2.1 to 6.8 | 809 | 3,761 | 1,081 | 7,119 |
| 12086006802 | Miami | 4.2 | 2.2 to 6.3 | 983 | 2,622 | 782 | 16,137 |
| 12086011500 | unincorporated | 4.1 | 2.3 to 6.0 | 533 | 2,516 | 102 | 2,100 |
| 12086004000 | Miami Beach | 3.5 | 1.8 to 5.4 | 371 | 4,942 | 201 | 22,792 |
| 12086004106 | Miami Beach | 3.1 | 1.6 to 4.8 | 951 | 3,213 | 108 | 40,440 |
| 12086004102 | Miami Beach | 2.5 | 1.3 to 4.0 | 869 | 2,856 | 99 | 56,144 |
| 12086009010 | Doral | 2.4 | 1.4 to 3.4 | 189 | 629 | 653 | 12,450 |
| 12086980500 | unincorporated | 2.4 | 1.3 to 3.4 | 685 | 520 | 34 | 2,840 |
| 12086003804 | Surfside | 2.2 | 1.2 to 3.4 | 360 | 2,143 | 89 | 17,418 |

## 4. People at risk

- 101,786 buildings with **564,355 residents** (98,550 aged over 65) get
  water at the building in the FEMA 1% flood.
- Expected each year: 9,876 residents in a building that floods; 2,534
  displaced from a flooded ground floor.
- Mental stress and lost productivity (not in dollars, D-133): FEMA's
  method applies its values to residents who are flooded but not
  displaced, about 7,300 a year on these figures. The number of working
  residents needed for lost productivity is not in our data.

### Top 10 tracts by people at risk (today)

| Tract | Place | Residents flooded per year | Residents wet in 1% flood | Residents wet in worst-case Cat 3 surge | EAD ($ million) | Sited investment per resident ($) |
|---|---|---|---|---|---|---|
| 12086002709 | Miami | 157 | 8,960 | 8,960 | 0.4 | 879 |
| 12086000120 | North Miami | 122 | 6,993 | 6,515 | 1.4 | 1,062 |
| 12086003006 | Miami | 113 | 6,431 | 5,862 | 1.0 | 879 |
| 12086003801 | Bay Harbor Islands | 103 | 5,884 | 5,840 | 2.0 | 16,116 |
| 12086005705 | Miami | 91 | 5,221 | 1,980 | 0.1 | 1,044 |
| 12086003004 | Miami | 89 | 5,113 | 3,964 | 1.3 | 2,963 |
| 12086005202 | Miami | 87 | 4,944 | 2,920 | 0.9 | 879 |
| 12086004000 | Miami Beach | 86 | 4,942 | 4,769 | 3.5 | 22,792 |
| 12086003917 | North Bay Village | 86 | 4,915 | 4,939 | 0.7 | 12,902 |
| 12086000132 | Aventura | 83 | 4,755 | 0 | 0.3 | 792 |

Many of these are tracts with large apartment towers. Many people live
where water reaches the building, but the dollar damage is modest because
only the ground floor is affected.

## 5. Storm surge: worst-case scenarios (not yearly figures)

**Worst case.** Each row shows what would happen if the NHC "maximum of
maximums" flooding for that category occurred everywhere at once. No real
storm does this, so these are upper limits for planning, not forecasts.

| Category | Buildings with water | Residents in them | Damage if it happened (worst case) |
|---|---|---|---|
| 1 | 15,244 | 87,055 | $0.8 billion |
| 2 | 57,075 | 279,434 | $4.6 billion |
| 3 | 125,810 | 597,921 | $17.2 billion |
| 4 | 253,275 | 1,163,774 | $53.0 billion |
| 5 | 377,479 | 1,721,504 | $94.0 billion |

For context, NOAA counts 45 hurricane strikes on Southeast Florida from
1851 to 2010: 16 Category 1, 14 Category 2, 11 Category 3, 3 Category 4 and
1 Category 5 (assumption, published frequency, D-136). Hurricane Andrew
(Category 5, 1992) led to $319 million of NFIP payments in 2025 dollars.

## 6. Check against real claims (provisional)

As agreed, until the full NFIP policies file is on disk the check uses
NFIP payments per occupied housing unit (ACS). Payments are in 2025 dollars
(CPI-U) and weighted toward recent years: the weight halves every 15 years
back from 2025 (D-140, D-144).

| Measure | Result |
|---|---|
| NFIP payments per year, weighted, 2025 dollars | $30.3 million (nominal: $20.2 million) |
| Spearman, tract EAD per unit vs claims per unit (694 tracts) | 0.49 (95% interval 0.43 to 0.54) |
| Same, homes only | 0.47 (0.41 to 0.52) |
| Ratio of totals, model / claims | 5.6 (low to high 3.0 to 8.5) |
| Same, homes only | 3.1 |
| Ratio using only 2000 to 2025, unweighted | 4.9 |

By decile of modelled risk, the median claims per unit rise from $0.61 to
$31.94 a year (`outputs/benefit/stage2/calibration_deciles.csv`). The
model sorts tracts in the right direction.

### What the remaining gap is made of (county totals, 2025 dollars)

No scaling is applied (D-146). Each step changes the gap by the factor
shown.

| Step | Gap after step | Factor | What it is |
|---|---|---|---|
| Start: all buildings vs all claims | 5.7 | | |
| 1. Homes only | 4.0 | 0.69 | NFIP payments are mostly for homes; many commercial and public buildings are not in the NFIP |
| 2. Claims inside the FEMA 100-year zones only | 4.4 | 1.11 | 10% of home payments come from floods outside these zones, which the model does not cover |
| 3. Replacement cost instead of depreciated value | 5.4 | 1.24 | NFIP pays replacement cost for many homes; the model uses depreciated value, so this widens the gap |
| 4. Payout caps and deductibles | 4.9 | 0.91 | Payments are 91% of adjusted damage in 18,247 home claims that record both |
| 5. Left over | 4.9 | | If all of this were uninsured losses, about 20% of home flood losses would be insured |

How to read this:
- The biggest unknown is insurance take-up: the share of homes that carry
  flood insurance, and how much of their value is covered. It needs the
  policies file.
- Step 4 is a lower bound on the effect of limits. Adjusters record damage
  to insured items, so losses above the coverage limit do not appear.
- Final calibration waits for the policies file.

## 7. Risk compared with sited investment

Across 698 tracts with at least 100 residents:
- risk per resident vs investment per resident: Spearman 0.34;
- total risk vs total investment: Spearman 0.33;
- of the 175 tracts in the top quarter of risk per resident, 46 are
  below the median investment per resident ($879).

The largest of those "high risk, low investment" tracts:

| Tract | Place | EAD ($ million) | EAD per resident ($) | Investment per resident ($) |
|---|---|---|---|---|
| 12086001705 | unincorporated | 1.5 | 701 | 638 |
| 12086001701 | Brownsville | 0.9 | 204 | 815 |
| 12086000505 | Hialeah | 0.9 | 157 | 583 |
| 12086012900 | Hialeah | 0.8 | 130 | 720 |
| 12086008415 | Kendall | 0.7 | 147 | 565 |
| 12086010303 | unincorporated | 0.7 | 200 | 565 |
| 12086015002 | unincorporated | 0.7 | 157 | 565 |
| 12086002403 | Miami | 0.7 | 165 | 879 |

The full list is in `outputs/benefit/stage2/high_risk_low_investment_tracts.csv`.
Investment per resident spreads project cost over the tracts a project
touches, so it is a rough measure (see the investment reports).

## 8. Limitations

- **Only two flood frequencies.** The yearly figure rests on the FEMA 1% and
  0.2% floods alone (D-147). Frequent small floods, such as heavy rain
  outside the mapped zones, king tides and street flooding, are missing.
  They cause many small claims: the 176 tracts with no modelled damage still
  have claims (median $2.54 per unit a year, against $13.32 where the model
  has damage).
- **The 0.2% flood uses the 1% depth**, a lower bound, because FEMA maps
  print no 0.2% elevation.
- **The FEMA maps date from 2009.** New maps are pending for 19 Feb 2027,
  and the code can swap them in (Stage 1 report).
- **Ground elevation is bare earth.** Buildings on fill or raised pads may
  be higher than the elevation model shows.
- **The curves are standard national curves**, not fitted to Miami-Dade.
- **Tall buildings:** damage is limited to flooded floors (D-143), which
  may understate damage to ground-floor plant and lobbies.
- **Displacement** uses one FEMA duration for all building types
  (assumption, with a low and high case). Its dollars are in 2021 prices.
- **Mental stress and lost productivity** are not in dollars (no
  FEMA-printed value).
- **The claims check is provisional.** It uses per housing unit, not per
  insured home, until the policies file is on disk.
- **Surge maps are worst cases.** They are not combined into the yearly
  figure.

## 9. Files and rerun

From `Modelling Data from Web/`, with the repository's `.venv`:

| Step | Command | Time |
|---|---|---|
| Hurricane frequencies | `../.venv/bin/python -I scripts/benefit/build_hurricane_rates.py` | seconds |
| CPI table | `../.venv/bin/python -I scripts/benefit/build_cpi.py` | seconds |
| Stage 2 | `../.venv/bin/python -I scripts/benefit/baseline_risk.py` | about 30 seconds |
| Download log | `../.venv/bin/python -I scripts/benefit/write_download_log.py` | seconds |

Outputs:
- `data/processed/benefit/ead_buildings.parquet`: per building, all events,
  EAD low, middle and high, sea level rise, displacement and people (not
  committed; 103 MB).
- `data/processed/benefit/ead_tract.csv`: per tract, with ranks, claims,
  housing units and investment.
- `outputs/benefit/stage2/`: `summary.json`, `calibration_deciles.csv`,
  `top20_tracts_dollars.csv`, `top20_tracts_people.csv`,
  `high_risk_low_investment_tracts.csv`, `tract_places.csv`.

When the policies file arrives: point `NFIP_POLICIES_PARQUET_MANUAL` in
`scripts/common/paths.py` at it. The check will then be redone per insured
home, and step 5 above replaced by the measured take-up.
