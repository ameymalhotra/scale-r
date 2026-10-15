# Gray Infrastructure Decomposition + Density Premise Check

Two loose ends before write-up. **Descriptive and correlational only** — no
model was fit anywhere in this document. Same scope as before: 698-tract
sample, 1,843 block groups, no variable dropped, nothing imputed, FDR-adjusted
p-values alongside raw, all prior decisions hold.

Scripts (reusable):

| script | task | what it does |
|---|---|---|
| `scripts/part7a_density_premise.py` | 1 | density → outcome zero-order correlations + the housing_density supplementary control |
| `scripts/gray_classification.py` | 2a | the text-classification rules, disclosed in full |
| `scripts/part7_gray_decomposition.py` | 2a/2b/2c/3 | profile, per-sub-category shares, partial correlations |

```
python scripts/part7a_density_premise.py
python scripts/part7_gray_decomposition.py
```

Outputs: `output/part7_gray/`.

---

## Task 1 — The density premise check

**You were right to ask. At tract grain, density barely predicts the outcome
at all, so the Part 6 partial-correlation result is a much weaker exoneration
than it appeared.**

### Zero-order correlations: `pop_density` → outcomes, tract (n=698)

| outcome | Pearson r | Pearson p | Spearman ρ | Spearman p |
|---|---|---|---|---|
| `type_gray_share` | 0.073 | 0.0527 | **0.031** | **0.4075 (ns)** |
| `type_green_share` | −0.019 | 0.6087 | 0.009 | 0.8198 (ns) |
| `type_blue_share` | −0.075 | 0.0492 | −0.027 | 0.4729 (ns) |
| `type_hybrid_share` | 0.008 | 0.8264 | −0.083 | 0.0288 |
| `investment_per_capita` (raw) | −0.050 | 0.1908 | 0.017 | 0.6592 (ns) |
| `investment_per_capita` (rank) | 0.081 | 0.0335 | 0.017 | 0.6592 (ns) |

**The largest |Spearman ρ| between density and any outcome at tract is
0.083**, and the two shares that carry the headline finding — gray and green —
are at **ρ = 0.031 and 0.009, neither significant**.

Binary outcomes, tract (Mann-Whitney on density between receiving/not):

| outcome | n receiving | n not | mean density receiving | mean density not | p |
|---|---|---|---|---|---|
| `investment_any_excl_county` | 540 | 158 | 4,987.9 | 4,005.3 | 0.2320 (ns) |
| `investment_any_single_unit` | 396 | 302 | 4,143.6 | 5,580.9 | <0.0001 |

The one real density signal at tract is on `investment_any_single_unit`:
tracts with a physically-sited project are **less** dense on average
(4,144 vs 5,581 persons/km²).

### Block group (n=1,838–1,842), including `housing_density`

| density measure | outcome | Pearson r | Spearman ρ | Spearman p |
|---|---|---|---|---|
| pop_density | `type_gray_share` | 0.062 | 0.061 | 0.0089 |
| pop_density | `type_green_share` | −0.041 | −0.014 | 0.5617 (ns) |
| pop_density | `type_blue_share` | −0.041 | −0.022 | 0.3430 (ns) |
| pop_density | `type_hybrid_share` | −0.029 | −0.061 | 0.0091 |
| pop_density | `investment_per_capita` (raw) | −0.044 | 0.046 | 0.0474 |
| pop_density | `investment_per_capita` (rank) | 0.086 | 0.046 | 0.0474 |
| **housing_density** | `type_gray_share` | 0.140 | **0.144** | <0.0001 |
| **housing_density** | `type_green_share` | −0.075 | −0.098 | <0.0001 |
| **housing_density** | `type_blue_share` | −0.132 | −0.119 | <0.0001 |
| **housing_density** | `type_hybrid_share` | 0.012 | −0.083 | 0.0004 |
| **housing_density** | `investment_per_capita` (raw) | −0.004 | 0.149 | <0.0001 |
| **housing_density** | `investment_per_capita` (rank) | 0.176 | 0.149 | <0.0001 |

| density measure | outcome | n recv | n not | mean recv | mean not | p |
|---|---|---|---|---|---|---|
| pop_density | `investment_any_excl_county` | 1,260 | 582 | 5,612.5 | 4,243.4 | <0.0001 |
| pop_density | `investment_any_single_unit` | 581 | 1,261 | 4,016.3 | 5,716.1 | <0.0001 |
| housing_density | `investment_any_excl_county` | 1,260 | 582 | 3,066.0 | 1,682.8 | <0.0001 |
| housing_density | `investment_any_single_unit` | 581 | 1,261 | 2,020.2 | 2,909.5 | <0.0001 |

At block group density *does* relate to composition — but weakly (max
|ρ| = 0.149, all under 0.15) — and **`housing_density` is consistently the
stronger of the two measures**, roughly double `pop_density` on every share.
Part 6 controlled for `pop_density`, i.e. the weaker one.

### Supplementary: re-running the Part 6 control on `housing_density` instead

| type | variable | n | zero-order ρ | partial ρ (pop_density) | partial ρ (**housing_density**) | p_fdr (housing) |
|---|---|---|---|---|---|---|
| gray | no_vehicle | 1,832 | 0.2028 | 0.1923 (−5%) | **0.1643 (−19%)** | <0.0001 |
| gray | no_broadband | 1,832 | 0.1778 | 0.1703 (−4%) | 0.1514 (−15%) | <0.0001 |
| gray | PEOPCOLORPCT | 1,838 | −0.1742 | −0.1816 | **−0.1759 (1% *stronger*)** | <0.0001 |
| green | no_vehicle | 1,832 | −0.1809 | −0.1814 | −0.1553 (−14%) | <0.0001 |
| green | no_broadband | 1,832 | −0.1312 | −0.1294 | −0.1119 (−15%) | <0.0001 |
| green | PEOPCOLORPCT | 1,838 | 0.2212 | 0.2237 | **0.2222 (+0.5%)** | <0.0001 |

Under the stronger control the access variables attenuate more (14–19%
rather than 4–5%) but **everything remains FDR-significant**, and
`PEOPCOLORPCT` barely moves at all (≤1%).

### Plain statement

**Density does not predict investment composition at tract grain** (max
|ρ| = 0.083, gray/green shares both non-significant), and predicts it only
weakly at block group (max |ρ| = 0.149, via `housing_density`). **So the Part
6 partial-correlation result should be reported as "density was never a
serious competing explanation," not as "the finding survived a strong
challenge."** The test was close to uninformative at tract because there was
almost nothing there for the control to absorb. At block group the control is
genuinely informative — density does relate to composition there — and the
finding does survive it, including under the stronger `housing_density`
version, with 14–19% attenuation on the access variables and ~1% on
`PEOPCOLORPCT`. That block-group result carries real weight; the tract one
carries much less than it appeared to.

---

## Task 2 — Decompose gray infrastructure

### 2a. What is inside gray

**No column distinguishes project sub-types.** The database has
`Project_ID, Project_Name, Latitude, Longitude, Jurisdiction, Data_Source,
Infrastructure_Type, Hazard_Focus, Project_Description, Project_Status,
Estimated_Cost, Reported_Year, Spatial_Resolution` — nothing else.
`Hazard_Focus` was checked and rejected for this purpose: it is a hazard
category, not an infrastructure sub-type, and mixes drainage, roads and
coastal projects together under "Flooding" and "Coastal Hazards". So
sub-categories had to be derived from `Project_Name` + `Project_Description`
text. Full rules in `scripts/gray_classification.py`.

**Transit detection — and a first attempt that had to be tightened.** A loose
pattern using bare `transit|shuttle|station|brightline` produced 6 matches, 4
of them false positives. These are shown so the tightening is checkable:

| Project_ID | name | loose match | why it is NOT transit |
|---|---|---|---|
| SCALER-0002 | NE 29PL & Aventura Boulevard Phase 1 Drainage Work | `brightline` | drainage project "in the vicinity of … aventura brightline station" |
| SCALER-0623 | Dinner Key Marina and Mooring Facility Reconstruction | `shuttle` | a marina "shuttle boat" — a boat, not transit |
| SCALER-1167 | NW 39 St & NW 25 Ave Trash Racks and Wet Wells Upgrade | `transit` | stormwater pump station described as protecting "regional commercial transit grids" |
| SCALER-1183 | Storm Bollards - Miami SeaPort | `transit` | marina mooring/bollard project self-described as "coastal transit infrastructure" (boat transit) |

The tightened rule requires a transit-**specific compound** term:
`SMART Program | Metrorail | Metromover | TransitWay | Trolley | Light Rail |
Bus Rapid Transit | BRT | Commuter Rail | Transit Corridor | Transit Station |
Bus Terminal | Bus Shelter | Park and Ride`. It matches **exactly 2 of 1,157**
filtered Gray projects: `SCALER-1335` (SMART Program – Northeast Corridor) and
`SCALER-1338` (SMART Program – South Dade TransitWay) — both already flagged
in `flag_large_project`.

**The 7-way partition** (transit checked first, then the five patterns in
priority order `coastal_seawall → drainage_stormwater → road → water_sewer →
power_comm_facility`, else `other_unclassified`). Tract-grain receiving units
shown; block-group counts are in
`output/part7_gray/2a_gray_subcategory_profile.csv`:

| sub-category | n projects | dollars | % of gray $ | receiving units (any path) | receiving units (**single-unit-sited**) | sparse? |
|---|---|---|---|---|---|---|
| `drainage_stormwater` | 682 | $1,694,373,624 | **33.7%** | 700 | **298** | no |
| `transit` | **2** | $1,295,553,493 | **25.8%** | 2 | **2** | **SPARSE** |
| `other_unclassified` | 283 | $1,185,517,671 | 23.6% | 701 | 109 | no |
| `water_sewer` | 70 | $352,878,844 | 7.0% | 698 | 21 | no |
| `road` | 50 | $212,696,386 | 4.2% | 698 | 38 | no |
| `coastal_seawall` | 26 | $164,554,379 | 3.3% | 699 | **17** | **SPARSE** |
| `power_comm_facility` | 44 | $120,129,616 | 2.4% | 698 | 26 | no |

Example matches (first 3 each, so the classification can be spot-checked):

| sub-category | examples |
|---|---|
| transit | SMART Program – Northeast Corridor; SMART Program – South Dade TransitWay |
| coastal_seawall | Yacht Club Drive Seawall Repairs; NE 213th & NE 183rd Street Seawall; Seawall Improvements (5-yr program) |
| drainage_stormwater | NE 29PL & Aventura Boulevard Phase 1 Drainage Work; Yacht Club Drive Drainage Improvements; Aventura Parking Lot Injection Well |
| road | Country Club Drive F-Curb Installation; Collins Avenue and 96th Street Water-Main Improvements; 95th Street Gazebo and Shade Project |
| water_sewer | Bal Harbour Village Wastewater Lift Station Rehabilitation; Sewer SCADA Implementation—BHI-206; Sewer T-Liner Installation Program |
| power_comm_facility | Emergency Power Generator for Police & EOC; Hardened 911 Communication and EOC; Police Department Hardening & Reconstruction (ARPA) |
| other_unclassified | Crosswalk Solar-Lighting Program; Bus-Shelter Solar-Lighting Retrofit; Waterways Playground Relocation—ARPA |

**Reliability caveat, stated plainly.** The **transit vs non-transit** split is
high-confidence: 2 unambiguous projects, no bundling problem. The **finer
6-way split is lower-confidence**, because project names bundle functions:
**420 of 688 projects matching the drainage pattern (61%) also match the road
pattern** (e.g. "Roadway and Drainage Improvement Project"), and are filed
under drainage by priority order. The `road` category (50 projects) is
therefore "road work with no drainage language in its name," not all
road-related spending — and `road`'s example list shows the imperfection
directly ("Collins Avenue and 96th Street **Water-Main** Improvements" landed
in road because "Avenue" was matched before the water pattern was reached).
`other_unclassified` at 283 projects / 23.6% of gray dollars is left
deliberately large rather than forced into categories — it holds building
hardening, HVAC, IT, vulnerability assessments, solar retrofits and similar.

### 2b. Composition correlations per sub-category

Zero-order and partial (controlling `pop_density`) Spearman, FDR-adjusted
within each table. Full tables in `output/part7_gray/2b_*.csv`.

**Tract — access/connectivity variables:**

| sub-category | EP_NOVEH ρ → partial | no_vehicle ρ → partial | EP_MUNIT ρ → partial | EP_NOINT ρ → partial | no_broadband ρ → partial | all sig after control? |
|---|---|---|---|---|---|---|
| `drainage_stormwater` | 0.151 → **0.154** | 0.134 → **0.137** | 0.102 → **0.110** | 0.141 → **0.140** | 0.142 → **0.141** | **yes, all 5** |
| `water_sewer` | 0.261 → **0.170** | 0.276 → **0.182** | 0.175 → 0.001 (ns) | 0.204 → **0.140** | 0.226 → **0.168** | 4 of 5 |
| `power_comm_facility` | 0.113 → 0.029 (ns) | 0.146 → 0.063 (ns) | 0.100 → −0.047 (ns) | 0.085 → 0.028 (ns) | 0.052 → −0.003 (ns) | none |
| `other_unclassified` | 0.080 → 0.069 (ns) | 0.065 → 0.054 (ns) | 0.081 → 0.067 (ns) | −0.006 → −0.017 (ns) | −0.005 → −0.014 (ns) | none |
| `road` | 0.014 → −0.074 (ns) | 0.091 → 0.006 (ns) | 0.000 → **−0.158** | 0.069 → 0.015 (ns) | 0.028 → −0.025 (ns) | 1 of 5 |
| `coastal_seawall` **SPARSE** | −0.162 → −0.196 | −0.118 → −0.153 | −0.060 → −0.113 | −0.115 → −0.134 | −0.161 → −0.180 | flagged, not read |
| `transit` **SPARSE** | 0.001 → 0.032 (ns) | −0.066 → −0.039 (ns) | −0.022 → 0.028 (ns) | −0.022 → −0.003 (ns) | 0.010 → 0.029 (ns) | flagged, not read |

**Tract — minority-composition variables:**

| sub-category | EP_MINRTY ρ → partial | EP_HISP ρ → partial | EP_AFAM ρ → partial |
|---|---|---|---|
| `drainage_stormwater` | −0.111 → **−0.113** | −0.170 → **−0.176** | 0.092 → **0.095** |
| `other_unclassified` | −0.138 → **−0.143** | −0.178 → **−0.189** | 0.062 → 0.069 (ns) |
| `water_sewer` | 0.144 → **0.117** | 0.128 → 0.075 (ns) | −0.042 → 0.003 (ns) |
| `road` | 0.098 → 0.075 (ns) | 0.130 → **0.091** | −0.010 → 0.025 (ns) |
| `power_comm_facility` | 0.029 → 0.003 (ns) | 0.010 → −0.037 (ns) | 0.006 → 0.043 (ns) |
| `coastal_seawall` **SPARSE** | 0.025 → 0.018 (ns) | 0.044 → 0.033 (ns) | −0.017 → −0.008 (ns) |
| `transit` **SPARSE** | −0.064 → −0.056 (ns) | −0.046 → −0.031 (ns) | 0.029 → 0.017 (ns) |

**The direct answer — the non-transit and non-road aggregates (tract):**

| aggregate | variable | n | zero-order ρ | partial ρ | p_fdr |
|---|---|---|---|---|---|
| **`gray_non_transit_share`** | EP_NOVEH | 697 | **0.299** | **0.301** | <0.0001 |
| `gray_non_transit_share` | no_vehicle | 698 | 0.261 | 0.263 | <0.0001 |
| `gray_non_transit_share` | EP_MUNIT | 697 | 0.211 | 0.220 | <0.0001 |
| `gray_non_transit_share` | EP_NOINT | 697 | 0.205 | 0.199 | <0.0001 |
| `gray_non_transit_share` | no_broadband | 698 | 0.256 | 0.252 | <0.0001 |
| `gray_non_transit_share` | EP_MINRTY | 698 | −0.122 | −0.128 | 0.0011 |
| `gray_non_transit_share` | EP_HISP | 698 | −0.128 | −0.138 | 0.0004 |
| `gray_non_transit_share` | EP_AFAM | 698 | 0.015 | 0.021 | 0.608 (ns) |
| **`gray_non_road_share`** | EP_NOVEH | 697 | **0.291** | **0.301** | <0.0001 |
| `gray_non_road_share` | no_vehicle | 698 | 0.241 | 0.251 | <0.0001 |
| `gray_non_road_share` | EP_MUNIT | 697 | 0.188 | 0.209 | <0.0001 |
| `gray_non_road_share` | EP_NOINT | 697 | 0.203 | 0.203 | <0.0001 |
| `gray_non_road_share` | no_broadband | 698 | 0.258 | 0.259 | <0.0001 |
| `gray_non_road_share` | EP_MINRTY | 698 | −0.118 | −0.121 | 0.0017 |
| `gray_non_road_share` | EP_HISP | 698 | −0.126 | −0.132 | 0.0006 |
| `gray_non_road_share` | EP_AFAM | 698 | 0.016 | 0.019 | 0.608 (ns) |

**For reference, the original all-gray figures were EP_NOVEH ρ = 0.305,
no_vehicle 0.254, EP_MUNIT 0.209, no_broadband 0.258.** Removing transit
changes EP_NOVEH from 0.305 to 0.299. **The relationship is not transit's.**

**Block group — same test:**

| sub-category | no_vehicle ρ → partial | no_broadband ρ → partial | PEOPCOLORPCT ρ → partial |
|---|---|---|---|
| `drainage_stormwater` | 0.118 → **0.112** | 0.108 → **0.104** | −0.099 → **−0.104** |
| `water_sewer` | 0.234 → **0.180** | 0.209 → **0.180** | 0.166 → **0.145** |
| `other_unclassified` | 0.115 → **0.089** | 0.062 → 0.047 (0.064, ns) | −0.184 → **−0.197** |
| `power_comm_facility` | 0.104 → **0.064** | 0.070 → 0.047 (0.064, ns) | 0.107 → **0.092** |
| `road` | 0.054 → 0.019 (ns) | 0.038 → 0.019 (ns) | 0.188 → **0.176** |
| `coastal_seawall` **SPARSE** | −0.056 → −0.078 | −0.073 → −0.085 | 0.020 → 0.012 (ns) |
| `transit` **SPARSE** | −0.043 → −0.032 (ns) | −0.023 → −0.017 (ns) | −0.046 → −0.042 (ns) |

### The explicit answer to 2b

**Yes — the gray/access relationship holds for non-transit gray on its own,
and it is specifically a drainage and water/sewer story, not a roads story.**

- `drainage_stormwater` — the largest sub-category (33.7% of gray dollars,
  682 projects, 298 single-unit-sited tract units, **not sparse**) —
  reproduces the full pattern independently: all five access variables
  positive and FDR-significant, essentially unmoved by the density control
  (0.3–7.7% change), and the minority-composition signs match the overall
  finding (`EP_HISP` −0.176, `EP_MINRTY` −0.113).
- `water_sewer` (7.0%, 70 projects, 21 units — just above the sparsity floor)
  shows the pattern *more strongly* still (no_vehicle 0.276 → 0.182 partial).
- `road` (4.2%, 50 projects) shows **no** access relationship (4 of 5
  variables non-significant after control) — so roads are not carrying it
  either.
- `transit` cannot carry it: 2 projects, 2 receiving units, every correlation
  non-significant and flagged sparse.
- The tautology concern does not materialise. Transit is 25.8% of gray
  *dollars* but touches only 2 of ~700 units, so it cannot drive a
  correlation computed across units.

### 2c. Sparsity guard

| sub-category | grain | single-unit-sited receiving units | status |
|---|---|---|---|
| `transit` | tract & bg | 2 | **SPARSE — correlations not interpretable** |
| `coastal_seawall` | tract | 17 | **SPARSE — below the 20-unit floor** |
| `coastal_seawall` | bg | 17 | **SPARSE** |
| `water_sewer` | tract | 21 | just above floor — treat with caution |
| `power_comm_facility` | tract | 26 | above floor |
| `road` | tract | 38 | above floor |
| `other_unclassified` | tract | 109 | fine |
| `drainage_stormwater` | tract | 298 | fine |

Every sparse row carries `flag_sparse=True` in the CSVs and is marked
**SPARSE** in the tables above. Note this means the coastal-hardening half of
your question **cannot be answered**: `coastal_seawall` shows a *consistently
negative* relationship with the access variables (−0.118 to −0.196, opposite
in sign to drainage), but on 17 units that is not a finding. Blue
infrastructure was flagged at 19 units; this is 17, so the same standard
applies.

---

## Task 3 — Block-group environmental proximity vs gray sub-categories

Zero-order and `pop_density`-controlled partial Spearman, FDR within table.

| sub-category | PTRAF ρ → partial | NO2 ρ → partial | UST ρ → partial | RSEI_AIR ρ → partial |
|---|---|---|---|---|
| `water_sewer` | 0.201 → **0.171** | 0.298 → **0.234** | 0.316 → **0.284** | 0.186 → **0.157** |
| `power_comm_facility` | 0.282 → **0.264** | 0.260 → **0.219** | 0.128 → **0.101** | 0.055 → 0.032 (ns) |
| `road` | 0.191 → **0.173** | 0.210 → **0.174** | 0.068 → 0.043 (ns) | −0.046 → **−0.068** |
| `drainage_stormwater` | 0.146 → **0.142** | 0.119 → **0.113** | 0.225 → **0.222** | 0.027 → 0.022 (ns) |
| `other_unclassified` | −0.055 → **−0.072** | −0.037 → **−0.077** | 0.064 → 0.046 (ns) | −0.066 → **−0.082** |
| `coastal_seawall` **SPARSE** | −0.212 → −0.227 | −0.179 → −0.219 | −0.163 → −0.181 | −0.164 → −0.177 |
| `transit` **SPARSE** | −0.024 → −0.018 (ns) | −0.036 → −0.023 (ns) | −0.003 → 0.005 (ns) | −0.012 → −0.006 (ns) |

**The non-road aggregate:**

| aggregate | variable | n | zero-order ρ | partial ρ | p_fdr |
|---|---|---|---|---|---|
| `gray_non_road_share` | PTRAF | 1,837 | 0.135 | **0.127** | <0.0001 |
| `gray_non_road_share` | NO2 | 1,828 | 0.162 | **0.149** | <0.0001 |
| `gray_non_road_share` | UST | 1,838 | 0.282 | **0.275** | <0.0001 |
| `gray_non_road_share` | RSEI_AIR | 1,838 | 0.127 | **0.119** | <0.0001 |

**Yes — the environmental-proximity relationship holds for non-road gray
infrastructure.** All four environmental variables correlate significantly
with non-road gray share, barely moved by the density control (4–8%). The
traffic-tautology concern is real but limited: `road` *is* the strongest
correlate of `PTRAF` and `NO2` among the categories where it matters
(0.191/0.210), consistent with roads being built where traffic is. But
`UST` — the single strongest environmental relationship in the whole table
(non-road aggregate ρ=0.282) — is driven by `water_sewer` (0.316) and
`drainage_stormwater` (0.225), with **`road` not significant at all
(0.068 → 0.043, ns)**. So the environmental co-location result does not
depend on roads.

---

## What this changes

**1. Does density predict composition at all — and how much weight does the
Part 6 result deserve?** **At tract, essentially not at all.** The maximum
|Spearman ρ| between `pop_density` and any outcome is 0.083, and the gray and
green shares that carry the headline finding sit at ρ = 0.031 and 0.009,
*neither significant*. The Part 6 partial correlation therefore could not
have moved much regardless of the truth, and **should be written up as
"density was never a serious competing explanation at tract grain," not as a
finding that survived a strong test.** At block group the picture is better:
density does relate to composition (|ρ| up to 0.149 via `housing_density`,
the stronger measure, which Part 6 did *not* use), and re-running the control
on `housing_density` attenuates the access variables by 14–19% while leaving
everything FDR-significant and `PEOPCOLORPCT` essentially unmoved (≤1%). **The
block-group density control carries real evidential weight; the tract one
carries much less than it appeared to.**

**2. Does the gray/access finding survive removing transit? Yes, almost
unchanged.** `gray_non_transit_share` vs `EP_NOVEH` is ρ = 0.299 (partial
0.301) against 0.305 for all-gray — a change of 0.006. Transit is 25.8% of
gray dollars but only **2 projects landing in 2 units**, so it is
arithmetically incapable of driving a cross-unit correlation. More
importantly, the pattern reproduces **independently inside
`drainage_stormwater`** (33.7% of gray dollars, 298 receiving tract units, all
five access variables significant, ~0–8% movement under the density control)
and inside `water_sewer`. **The finding is a drainage-and-utilities story. It
is not transit, and it is not roads** — `road` shows no access relationship at
either grain. This makes the finding substantially stronger than it was, and
also more specific than "gray infrastructure": it is about where drainage and
water/sewer work goes.

**3. Does the block-group environmental finding survive removing roads? Yes.**
`gray_non_road_share` correlates significantly with all four environmental
proximity measures (PTRAF 0.127, NO2 0.149, UST 0.275, RSEI_AIR 0.119 after
the density control). The traffic-tautology risk is genuine for `PTRAF`/`NO2`
specifically — `road` is their strongest non-sparse correlate — but the
strongest environmental relationship overall, `UST`, runs through
`water_sewer` (0.316) and `drainage_stormwater` (0.225) with **`road`
non-significant**.

**4. Which sub-categories are too sparse to interpret?** `transit` (**2**
single-unit-sited receiving units, both grains) and `coastal_seawall` (**17**,
both grains) — both below the 20-unit floor applied to Blue infrastructure
(19 units). `water_sewer` at 21 tract units clears the floor by a single unit
and should be treated with caution despite showing some of the strongest
coefficients. **The practical consequence: your question about whether
coastal hardening shows the pattern independently cannot be answered from this
data.** `coastal_seawall` runs *negative* against the access variables
(−0.118 to −0.196, opposite in sign to drainage), which would be interesting
if it were interpretable — on 17 units it is not.
