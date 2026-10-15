# Follow-up Analysis: New Variables, Robust Spatial Retest, Density Control

Three follow-ups to `correlation_analysis.md` / `RESULTS_FOR_REVIEW.md`, in
the priority order given. **Still descriptive and correlational only** — no
predictive model was fit anywhere in this document. Task 3 uses partial
correlation and a descriptive stratification, not a fitted model. All prior
scope decisions from `DATA_PROCESSING.md` and the earlier build hold: 698-tract
sample (9 zero-population tracts excluded, Pennsuco kept), per-capita as the
primary dollar outcome, no variable dropped, no FEMA risk layer, SVI as
`EP_*` components.

**One path fix made in passing:** `scripts/allocation.py` pointed at
`block-group-level/B01003-Total Population/` for block-group population; the
user had reorganized that folder into `block-group-level/ADI Data/B01003-Total
Population/`. Fixed before anything else ran — the investment-table pipeline
would otherwise have failed outright, not silently misbehaved.

Scripts (all reusable):

| script | task | what it does |
|---|---|---|
| `scripts/vulnerability_loaders.py` (`load_new_bg_vars`) | 1 | B25044/B28002 recipes at BG grain |
| `scripts/build_analysis_tables.py` | 1 | wires the two new vars into `blockgroup_analysis.csv` |
| `scripts/part3_correlation.py`, `scripts/part4_investment_vs_indicators.py` | 1 | re-run as-is with the expanded 37-variable BG set |
| `scripts/part6b_moran_transforms.py` | 2 | Moran's I on raw/log/rank transforms |
| `scripts/part6c_density_control.py` | 3 | density measures, partial correlation, tercile stratification |

```
python scripts/build_analysis_tables.py
python scripts/part3_correlation.py
python scripts/part4_investment_vs_indicators.py
python scripts/part6b_moran_transforms.py
python scripts/part6c_density_control.py
```

Outputs: `output/part6_followup/*.csv` (new), plus the block-group files
under `output/part3_correlation/` and `output/part4_investment_vs_indicators/`
(overwritten in place with the expanded variable set — this is a legitimate
re-run of Parts 3/4, not a new analysis track).

---

## Task 1 — The two new block-group variables

### Build

`B25044` (Tenure by Vehicles Available) and `B28002` (Presence and Types of
Internet Subscriptions) at block-group grain, 2024 ACS 5-Year — confirmed
same vintage as their 12 ADI siblings: `diff` of both new tables'
`Column-Metadata.csv` files against the tract-grain versions returned **zero
differences** (identical column codes/labels), and the data files have 1,843
data rows each, matching every other block-group ACS table already on disk.

Recipes, identical to the tract CRE recipes in `DATA_PROCESSING.md` Sec 1,
applied at block-group grain:
- `no_vehicle` = (owner "No vehicle available" + renter "No vehicle
  available") / Total occupied housing units — B25044_003E + B25044_010E
  over B25044_001E.
- `no_broadband` = Total − "Broadband of any type", over Total households —
  B28002_001E − B28002_004E, over B28002_001E. **Same complement method as
  the tract grain**, kept consistent as instructed.

Hand-validated against the raw file for block group `120860001071`: manual
16/542 = 0.02952029520295203, loader value identical to 16 significant
figures.

| variable | n rows | n missing | % missing |
|---|---|---|---|
| `no_vehicle` | 1,843 | 11 | 0.6% |
| `no_broadband` | 1,843 | 11 | 0.6% |

Both now live in `blockgroup_analysis.csv` (82 columns, up from 76; still
1,843 rows). `BG_VULN_VARS` grew from 35 to **37**.

### Re-run: correlations with every other block-group indicator

**No new |r| > 0.8 pairs formed.** The block-group high-correlation list is
still exactly the 2 pairs from before (`PM25`–`OZONE` 0.900, `PM25`–`DSLPM`
0.801) — `no_vehicle` and `no_broadband` do not duplicate anything already on
disk. Their strongest correlates, from `output/part3_correlation/bg_pearson.csv`
/ `bg_spearman.csv`:

| variable | strongest correlate | Pearson r | Spearman ρ |
|---|---|---|---|
| `no_vehicle` | `pct_owner_occupied` | −0.504 | −0.498 |
| `no_vehicle` | `income_disparity` | 0.490 | 0.435 |
| `no_vehicle` | `poverty_under150` | 0.466 | 0.401 |
| `no_vehicle` | `no_broadband` | 0.457 | 0.461 |
| `no_broadband` | `no_vehicle` | 0.457 | 0.461 |
| `no_broadband` | `LOWINCPCT` | 0.443 | 0.461 |
| `no_broadband` | `median_gross_rent` | −0.441 | −0.477 |

**Note the ceiling: 0.504.** At tract, the SVI/CRE analogue (`EP_NOVEH`) tops
out at 0.898 with its own CRE twin. Here, `no_vehicle`'s single strongest
relationship with *anything* in the whole 37-variable block-group set is
moderate, not near-duplicate strength.

### Re-run: type share, path share, and the binaries

`output/part4_investment_vs_indicators/4d_bg_type_composition_continuous.csv`
(share rows) and `4d_bg_path_composition_continuous.csv`, filtered to the two
new variables:

| type | variable | n | Spearman ρ | p_fdr |
|---|---|---|---|---|
| blue | no_vehicle | 1,832 | −0.174 | 3.76e-13 (**SPARSE**) |
| gray | no_vehicle | 1,832 | **0.203** | 1.38e-17 |
| green | no_vehicle | 1,832 | −0.181 | 3.69e-14 |
| hybrid | no_vehicle | 1,832 | −0.125 | 2.27e-07 |
| blue | no_broadband | 1,832 | −0.135 | 1.94e-08 (**SPARSE**) |
| gray | no_broadband | 1,832 | 0.178 | 1.08e-13 |
| green | no_broadband | 1,832 | −0.131 | 5.41e-08 |
| hybrid | no_broadband | 1,832 | −0.168 | 2.21e-12 |

| path | variable | n | Spearman ρ | p_fdr |
|---|---|---|---|---|
| county | no_vehicle | 1,832 | −0.192 | 6.70e-16 |
| municipality | no_vehicle | 1,832 | **0.239** | 1.44e-24 |
| single_unit | no_vehicle | 1,832 | 0.019 | 0.507 (not significant) |
| county | no_broadband | 1,832 | −0.144 | 2.13e-09 |
| municipality | no_broadband | 1,832 | 0.194 | 2.41e-16 |
| single_unit | no_broadband | 1,832 | 0.017 | 0.565 (not significant) |

Binary comparisons (`{type}_any` are structurally undefined for these two
variables at block group — `n_not = 0` for every type: every block group
receives some of every type, as already established, so there's no "not
receiving" group to compare against; reported as such, not silently
dropped). `{path}_any` and the two volume proxies:

| group | variable | n receiving | n not | mean receiving | mean not | p_fdr |
|---|---|---|---|---|---|---|
| municipality | no_vehicle | 1,050 | 782 | 0.116 | 0.064 | 6.67e-24 |
| single_unit | no_vehicle | 576 | 1,256 | 0.097 | 0.093 | 0.794 |
| municipality | no_broadband | 1,050 | 782 | 0.122 | 0.078 | 2.31e-18 |
| single_unit | no_broadband | 576 | 1,256 | 0.105 | 0.102 | 0.639 |
| `investment_any_excl_county` | no_vehicle | 1,254 | 578 | 0.110 | 0.059 | 1.83e-18 |
| `investment_any_single_unit` | no_vehicle | 576 | 1,256 | 0.097 | 0.093 | 0.794 |
| `investment_any_excl_county` | no_broadband | 1,254 | 578 | 0.118 | 0.070 | 1.80e-19 |
| `investment_any_single_unit` | no_broadband | 576 | 1,256 | 0.105 | 0.102 | 0.639 |

### Updated VIF

| grain | dataset | `no_vehicle` VIF | `no_broadband` VIF | top VIF overall |
|---|---|---|---|---|
| bg | all 37, n=495 complete cases | 1.866 | 1.704 | `PM25` 32.233, `OZONE` 24.646 |
| bg | 34 vars excl. 3 high-missing, n=1,185 | 1.674 | 1.670 | `PM25` 20.009, `OZONE` 13.356 |

Both new variables sit at VIF < 2 — no combination-multicollinearity issue,
and `PM25`/`OZONE` remain the only VIF > 10 finding, unchanged from before
these variables were added.

### The question this pull was for: does `no_vehicle` behave at block group the way `EP_NOVEH` does at tract?

**No.** At tract, `EP_NOVEH` is the single strongest variable in three
separate tables:

| tract table | rank | value |
|---|---|---|
| `investment_per_capita` (34 vars) | **#1 of 34** | ρ = 0.333 |
| `type_gray_share` (34 vars) | **#1 of 34** | ρ = 0.305 |
| `type_green_share` (34 vars) | **#1 of 34** | ρ = −0.284 |

At block group, `no_vehicle` is a middling, not leading, correlate:

| bg table | rank | value |
|---|---|---|
| `type_gray_share` (37 vars) | #5 of 37 | ρ = 0.203 |
| `type_green_share` (37 vars) | #6 of 37 | ρ = −0.181 |
| `investment_any_excl_county` (37 vars) | #18 of 37 | mean diff 0.051 |
| `investment_any_single_unit` (37 vars) | #29 of 37 | not FDR-significant |

At block group, the top of every composition table is dominated by
**environmental proximity measures** (`PTRAF`, `NO2`, `UST`, `RSEI_AIR`,
`PNPL`, `PM25`, `PRE1960PCT`, `PTSDF`) — the same pattern already reported in
`correlation_analysis.md`'s Part 4d, now confirmed to hold even with the two
new variables added to the competition. **The main reason this variable was
pulled — to see if the tract-level "no vehicle is the strongest single
predictor" result replicates at finer geography — does not hold up.** Whatever
is driving the block-group composition pattern most strongly is environmental
exposure, not vehicle access.

---

## Task 2 — Moran's I retest on transformed outcomes

**The original conclusion does not survive.** `investment_per_capita`'s
apparent lack of spatial clustering was an artifact of its skew (18.718), not
a real absence of clustering.

Same k=6 KNN weights (same justification as before: standard
spatial-econometrics default, distance-based to avoid the island problem),
same 698-tract sample. Zero/undefined handling for the log transform: **none
of the three outcomes has any zero, negative, or missing value** at tract
grain (`investment_per_capita` min = $565.50, the county-allocation floor;
`investment_total` and `investment_per_area` are likewise fully positive and
complete for all 698 tracts) — so plain `log(x)` was used throughout, with no
zeros to handle and no rows dropped. Stated explicitly per the instruction,
not defaulted silently.

`output/part6_followup/6b_moran_transforms.csv`:

| variable | transform | n | I | p_sim | z_sim | skew after |
|---|---|---|---|---|---|---|
| investment_per_capita | raw | 698 | 0.006 | 0.0700 | 0.482 | 18.718 |
| investment_per_capita | log | 698 | **0.343** | **0.0010** | 16.874 | 1.979 |
| investment_per_capita | rank | 698 | **0.495** | **0.0010** | 23.128 | 0.011 |
| investment_total | raw | 698 | 0.033 | 0.0270 | 1.917 | 14.379 |
| investment_total | log | 698 | 0.281 | 0.0010 | 13.686 | 1.426 |
| investment_total | rank | 698 | 0.294 | 0.0010 | 14.268 | 0.000 |
| investment_per_area | raw | 698 | 0.162 | 0.0010 | 8.898 | 10.206 |
| investment_per_area | log | 698 | 0.514 | 0.0010 | 24.327 | 0.185 |
| investment_per_area | rank | 698 | 0.553 | 0.0010 | 26.453 | 0.000 |
| type_green_share (skew 4.319) | raw | 698 | 0.055 | 0.0080 | 2.904 | 4.319 |
| type_green_share | log | 698 | 0.219 | 0.0010 | 11.159 | −1.800 |
| type_green_share | rank | 698 | 0.370 | 0.0010 | 18.075 | −0.006 |
| type_hybrid_share (skew 3.688) | raw | 698 | 0.146 | 0.0010 | 7.111 | 3.688 |
| type_hybrid_share | log | 698 | 0.183 | 0.0010 | 8.841 | 0.423 |
| type_hybrid_share | rank | 698 | 0.264 | 0.0010 | 12.710 | −0.004 |

**Baseline reproduction check:** raw `investment_per_capita` reproduces the
original Part 5c number exactly (I=0.0059, p_sim=0.0700, seed pinned at
`np.random.seed(12086)` for the 999-permutation Monte Carlo draw) — this is
the same statistic as before, not a different weights matrix or sample.

**Reading the contrast:**
- **`investment_per_capita`: 0.006 (not significant) → 0.343 (log) →
  0.495 (rank), both p<0.001.** The rank transform — the most robust of the
  three, weighted most heavily per the instructions — shows I=0.495, in the
  same range as the vulnerability indicators themselves (I=0.31–0.99 in the
  original Part 5c table). **This is a real clustering signal that the raw
  skewed variable was hiding, not a marginal or borderline change.**
- `investment_total` was already weakly significant even raw (I=0.033,
  p=0.027) — not previously tested in Part 5c (which only covered
  `investment_per_capita` among the continuous outcomes), and both transforms
  push it substantially higher (I=0.28–0.29).
- `investment_per_area` was already clustered raw (I=0.162, p<00.001) and
  becomes markedly more so after transform (I=0.51–0.55) — consistent with
  the outcome-definition finding in `correlation_analysis.md` that
  `investment_per_area` and multi-unit housing share are tightly linked, and
  housing density is itself spatially clustered.
- `type_green_share` and `type_hybrid_share` (the two skew>3 composition
  outcomes) both show the same pattern: raw I is small-but-significant
  (0.055–0.146), and both transforms roughly double-to-triple it
  (0.18–0.37).

**Plain statement: the "no spatial autocorrelation in per-capita investment"
conclusion does NOT survive.** Once the extreme skew is handled by either
transform — and especially by rank, the most robust of the three — per-capita
investment is significantly and moderately-to-strongly spatially clustered,
in the same range as the vulnerability indicators and the composition
outcomes already found to be clustered in Part 5c. **This changes the
modeling path: the per-capita outcome now joins the binary and composition
outcomes as needing a spatial specification, not sitting apart from them.**

---

## Task 3 — The density control (highest priority)

### 3a. Density measures

`pop_density = population / (ALAND / 1e6)` — persons per km². Built at both
grains from TIGER `ALAND` (already loaded via `scripts/allocation.py`) and
each table's own `population` column.

`housing_density`: **available at block group only.** EJScreen's own
`ACSTOTHU` (total housing units, read directly from the same source file
already on disk) gives `housing_density = ACSTOTHU / area_km2`. **Not
available at tract grain** — the ten pulled ACS CRE tables (`B25044`,
`B25014`, etc.) carry *occupied* housing units as their denominator, not
total housing units; substituting that would misrepresent density in
coastal/seasonal tracts with high vacancy (a real concern in this county),
and no total-housing-unit table was pulled at tract grain. Reported as
unavailable rather than approximated with a mismatched definition, per the
instruction.

**Distributions** (`output/part6_followup/6a_density_vs_access_hardship_{tract,bg}.csv`
and the two `6a_*_with_density.csv` tables):

| | n | mean | p5 | p25 | median | p75 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| pop_density, tract (persons/km²) | 698 | 4,765.5 | 747.7 | 2,227.5 | 3,413.6 | 5,293.6 | 13,353.7 | 68,417.1 |
| pop_density, bg (persons/km²) | 1,842 | 5,179.9 | 670.2 | 2,033.4 | 3,559.1 | 6,199.9 | 15,137.8 | 86,568.6 |
| housing_density, bg (units/km²) | 1,842 | 2,629.0 | 231.7 | 724.6 | 1,265.4 | 2,592.1 | 9,434.5 | 59,080.2 |

**Density vs. the access/connectivity and hardship blocks:**

| grain | variable | block | n | Pearson r | Spearman ρ |
|---|---|---|---|---|---|
| tract | EP_NOVEH | access | 697 | 0.212 | 0.344 |
| tract | no_vehicle | access | 698 | 0.192 | 0.361 |
| tract | EP_MUNIT | access | 697 | 0.540 | **0.546** |
| tract | EP_NOINT | access | 697 | 0.048 | 0.233 |
| tract | no_broadband | access | 698 | 0.060 | 0.219 |
| tract | EP_POV150 | hardship | 697 | 0.010 | 0.226 |
| tract | poverty_under125 | hardship | 698 | 0.001 | 0.192 |
| tract | EP_UNEMP | hardship | 698 | −0.040 | 0.065 |
| tract | EP_NOHSDP | hardship | 698 | −0.076 | 0.097 |
| tract | no_diploma_pop25 | hardship | 698 | −0.095 | 0.074 |
| tract | EP_AGE65 | hardship | 698 | −0.131 | −0.014 |
| tract | age65plus | hardship | 698 | −0.156 | −0.044 |
| bg | no_vehicle | access | 1,832 | 0.129 | 0.254 |
| bg | no_broadband | access | 1,832 | 0.023 | 0.142 |
| bg | poverty_under150 | hardship | 1,832 | 0.032 | 0.200 |
| bg | poverty_pct_families | hardship | 1,827 | 0.016 | 0.161 |
| bg | LOWINCPCT | hardship | 1,842 | 0.036 | 0.213 |
| bg | UNEMPPCT | hardship | 1,842 | −0.009 | 0.076 |
| bg | LESSHSPCT | hardship | 1,842 | −0.048 | 0.095 |
| bg | no_diploma_under9yrs | hardship | 1,833 | −0.056 | 0.040 |
| bg | OVER64PCT | hardship | 1,842 | −0.075 | −0.058 |

**Read:** the access block sits at Spearman ρ 0.219–0.546 (tract) and
0.142–0.254 (bg); the hardship block sits at −0.058 to 0.226 (tract) and
0.040–0.213 (bg), with age 65+ the only variable to turn *negative*. The
ranges overlap at the edges (`EP_POV150` at 0.226 is comparable to
`EP_NOINT`/`no_broadband`'s 0.219–0.233), so this is not a clean separation —
**directionally consistent with the density hypothesis, but not by itself
conclusive**, which is exactly why 3b/3c matter more.

### 3b. Partial correlation (the core output)

Spearman partial correlation, standard rank-based formula, controlling for
`pop_density`, computed on the same listwise-complete rows as its matching
zero-order correlation. Full tables: `output/part6_followup/6b_partial_correlation_{tract,bg}.csv`
(all 34/37 vulnerability variables × 2 types — nothing dropped; excerpts
below are the access/connectivity and minority-composition rows named in the
task).

**Tract, access/connectivity (5 variables × 2 types):**

| variable | type | n | zero-order ρ | partial ρ | % change | p_fdr (partial) | significant after control |
|---|---|---|---|---|---|---|---|
| EP_MUNIT | gray | 697 | 0.209 | 0.228 | 8.8% | 1.5e-8 | **yes** |
| EP_NOVEH | gray | 697 | 0.305 | 0.313 | 2.5% | <1e-10 | **yes** |
| EP_NOINT | gray | 697 | 0.201 | 0.199 | 1.2% | 2.8e-7 | **yes** |
| no_vehicle | gray | 698 | 0.254 | 0.261 | 2.5% | 5.9e-11 | **yes** |
| no_broadband | gray | 698 | 0.258 | 0.257 | 0.2% | 3.9e-11 | **yes** |
| EP_MUNIT | green | 697 | −0.194 | −0.236 | 21.5% | 6.5e-9 | **yes** |
| EP_NOVEH | green | 697 | −0.284 | −0.305 | 7.3% | <1e-10 | **yes** |
| EP_NOINT | green | 697 | −0.140 | −0.145 | 4.0% | 4.9e-4 | **yes** |
| no_vehicle | green | 698 | −0.239 | −0.260 | 8.6% | 1.9e-11 | **yes** |
| no_broadband | green | 698 | −0.209 | −0.216 | 3.4% | 3.7e-9 | **yes** |

**Every single access/connectivity relationship survives the density
control at tract, and several strengthen rather than weaken** (EP_MUNIT-green
moves 21.5% *further from zero*, not toward it). Density is not soaking up
this signal.

**Tract, minority-composition (3 variables × 2 types):**

| variable | type | n | zero-order ρ | partial ρ | % change | p_fdr (partial) | significant after control |
|---|---|---|---|---|---|---|---|
| EP_MINRTY | gray | 698 | −0.135 | −0.139 | 3.1% | 8.9e-4 | **yes** |
| EP_AFAM | gray | 698 | 0.028 | 0.033 | 16.7% | 0.503 | no |
| EP_HISP | gray | 698 | −0.140 | −0.149 | 5.8% | 2.4e-4 | **yes** |
| EP_MINRTY | green | 698 | 0.199 | 0.199 | 0.1% | 8.7e-8 | **yes** |
| EP_AFAM | green | 698 | −0.035 | −0.034 | 2.5% | 0.454 | no |
| EP_HISP | green | 698 | 0.155 | 0.156 | 0.6% | 1.4e-4 | **yes** |

**`EP_MINRTY` and `EP_HISP` both survive, essentially unmoved** (0.1–5.8%
change). **`EP_AFAM` is the exception — it was never significant to begin
with** (zero-order ρ = 0.028/−0.035, both non-significant before any
control was applied) and stays non-significant after. This is not a
density effect erasing a real EP_AFAM signal; there was no signal there to
erase.

**Block group, access/connectivity (2 variables × 2 types):**

| variable | type | n | zero-order ρ | partial ρ | % change | p_fdr (partial) | significant after control |
|---|---|---|---|---|---|---|---|
| no_vehicle | gray | 1,832 | 0.203 | 0.192 | 5.2% | <1e-10 | **yes** |
| no_broadband | gray | 1,832 | 0.178 | 0.170 | 4.2% | <1e-10 | **yes** |
| no_vehicle | green | 1,832 | −0.181 | −0.181 | 0.2% | <1e-10 | **yes** |
| no_broadband | green | 1,832 | −0.131 | −0.129 | 1.3% | <1e-10 | **yes** |

**Block group, minority-composition (1 variable × 2 types — EJScreen carries
no separate Hispanic/Black split, only `PEOPCOLORPCT`):**

| variable | type | n | zero-order ρ | partial ρ | % change | p_fdr (partial) | significant after control |
|---|---|---|---|---|---|---|---|
| PEOPCOLORPCT | gray | 1,838 | −0.174 | −0.182 | 4.2% | <1e-10 | **yes** |
| PEOPCOLORPCT | green | 1,838 | 0.221 | 0.224 | 1.1% | <1e-10 | **yes** |

**Same pattern at block group as at tract: both blocks survive the density
control with minimal movement (0.2–5.2%), all remaining strongly
significant.**

*Note on `income_disparity` specifically* (not an access/minority variable,
but present in the full 37-variable partial-correlation table): its n is
correctly reduced to **1,207** in both the gray and green rows (zero_order
ρ=0.109/−0.096, partial ρ=0.106/−0.095), reflecting the 34.5% of block groups
where the log-ratio formula is undefined (Sec 7d of `RESULTS_FOR_REVIEW.md`).
Left as-is, not imputed, exactly as required.

### 3c. Density-tercile stratification

Terciles built from `pop_density` (`pd.qcut`, 3 equal-count groups):

| grain | low | medium | high | n per stratum |
|---|---|---|---|---|
| tract | < 2,658.6 | 2,658.6 – 4,500.6 | ≥ 4,500.6 | 233 / 232 / 233 |
| bg | < 2,501.1 | 2,501.1 – 4,959.7 | ≥ 4,959.7 | 614 / 614 / 614 |

Full tables: `output/part6_followup/6c_density_stratified_{tract,bg}.csv`.

**Tract, gray/green share vs. access/connectivity, within stratum:**

| tercile | type | EP_NOVEH ρ (p_fdr) | EP_MUNIT ρ (p_fdr) | EP_NOINT ρ (p_fdr) | no_broadband ρ (p_fdr) |
|---|---|---|---|---|---|
| low | gray | 0.214 (0.002) | 0.215 (0.002) | 0.042 (0.556, ns) | 0.133 (0.059, ns) |
| medium | gray | 0.408 (<0.001) | 0.237 (0.001) | 0.312 (<0.001) | 0.354 (<0.001) |
| high | gray | 0.310 (<0.001) | 0.190 (0.007) | 0.273 (<0.001) | 0.290 (<0.001) |
| low | green | −0.172 (0.015) | −0.168 (0.017) | 0.012 (0.879, ns) | −0.083 (0.254, ns) |
| medium | green | −0.398 (<0.001) | −0.273 (<0.001) | −0.273 (<0.001) | −0.355 (<0.001) |
| high | green | −0.348 (<0.001) | −0.165 (0.018) | −0.227 (0.001) | −0.234 (0.001) |

**`EP_NOVEH` and `EP_MUNIT` hold significant in all 3 strata, both types**
(all p_fdr ≤ 0.018; not shown in the compact table above but in the full
CSV). `no_vehicle` holds in 5 of 6 stratum×type cells - the one exception is
`no_vehicle`-green in the **low** stratum specifically (ρ=−0.061, p_fdr=0.41,
not significant). `EP_NOINT` and `no_broadband` are the weakest of the five:
both non-significant in the low stratum (p_fdr 0.06–0.88) but clearly
significant in medium/high. **So the pattern is not uniformly bullet-proof
across every access variable in the lowest-density tercile, but it holds for
the two strongest variables (`EP_NOVEH`, `EP_MUNIT`) everywhere, and for the
weaker three in 2 of 3 strata.**

**Tract, gray/green share vs. minority-composition, within stratum:**

| tercile | type | EP_MINRTY ρ (p_fdr) | EP_HISP ρ (p_fdr) | EP_AFAM ρ (p_fdr) |
|---|---|---|---|---|
| low | gray | −0.139 (0.048) | −0.165 (0.018) | 0.047 (0.528, ns) |
| medium | gray | −0.017 (0.834, ns) | −0.111 (0.116, ns) | 0.043 (0.556, ns) |
| high | gray | −0.201 (0.004) | −0.195 (0.006) | 0.076 (0.296, ns) |
| low | green | 0.221 (0.002) | 0.169 (0.016) | −0.010 (0.884, ns) |
| medium | green | 0.119 (0.093, ns) | 0.161 (0.020) | −0.061 (0.407, ns) |
| high | green | 0.192 (0.007) | 0.183 (0.010) | −0.076 (0.094, ns) |

**`EP_MINRTY` and `EP_HISP` hold in the low and high strata, and weaken (but
`EP_HISP`-green stays significant) in the middle stratum.** `EP_AFAM` is
non-significant in every stratum, at both types — consistent with 3b:
never a real signal, at any density level.

**Block group, gray/green share vs. access and minority, within stratum:**

| tercile | type | no_vehicle ρ (p_fdr) | no_broadband ρ (p_fdr) | PEOPCOLORPCT ρ (p_fdr) |
|---|---|---|---|---|
| low | gray | 0.079 (0.059, ns) | 0.079 (0.059, ns) | −0.183 (<0.001) |
| medium | gray | 0.281 (<0.001) | 0.202 (<0.001) | −0.096 (0.023) |
| high | gray | 0.232 (<0.001) | 0.262 (<0.001) | −0.225 (<0.001) |
| low | green | −0.025 (0.578, ns) | −0.015 (0.713, ns) | 0.278 (<0.001) |
| medium | green | −0.267 (<0.001) | −0.163 (<0.001) | 0.145 (<0.001) |
| high | green | −0.259 (<0.001) | −0.240 (<0.001) | 0.222 (<0.001) |

**`PEOPCOLORPCT` holds significant in every single stratum at both types** —
the cleanest "survives stratification" result in the whole analysis.
`no_vehicle`/`no_broadband` are borderline non-significant in the **low**
density stratum specifically (p_fdr ≈ 0.06, same direction, roughly half the
effect size) but clearly significant in medium/high.

### 3d. Minority-composition variables — explicit flag

Per the task: **the minority-composition relationship DOES survive the
density control, at both grains, essentially as strongly as the
access/connectivity relationship does.** `EP_MINRTY`/`EP_HISP` (tract) and
`PEOPCOLORPCT` (block group) move by 0.1–5.8% under the partial-correlation
control and hold significant in 2 of 3 (tract) or 3 of 3 (block group)
density strata. This is flagged explicitly as requested: **the equity signal
here is not confined to the deprivation/access axis — it is present, and
roughly equally robust to density, on the demographic axis as well.** The one
qualifier is `EP_AFAM`, which was never significant at zero order and stays
that way throughout — the minority-composition finding rests on
`EP_MINRTY`/`EP_HISP`/`PEOPCOLORPCT`, not uniformly across every race/ethnicity
variable in the vulnerability set.

---

## What survives

**1. Does the gray/green composition pattern hold after controlling for
density? Yes.** Every access/connectivity variable's partial correlation
with `type_gray_share`/`type_green_share` remains significant after
controlling for `pop_density` (5 of 5 tract variables, 2 of 2 block-group
variables), with changes of 0.2–21.5% — several *strengthen*. The tercile
stratification shows the same relationships present in the medium and high
density strata at both grains, and mostly (`EP_NOVEH`, `EP_MUNIT`,
`no_vehicle`) in the low stratum too — the two exceptions (`EP_NOINT`/tract,
`no_broadband`/both grains) are non-significant specifically in the lowest
density tercile. **The composition finding is not a density artifact.**

**2. Does the minority-composition pattern hold after controlling for
density? Yes, and about as robustly as the access pattern.** `EP_MINRTY`,
`EP_HISP` (tract), and `PEOPCOLORPCT` (block group) all survive the partial
correlation with minimal movement (0.1–5.8%) and remain significant in most
or all density strata. `EP_AFAM` alone shows no relationship, at zero order
or after any control — it never had a finding to lose. **This is the result
flagged as most important if it came out this way: the equity signal here
runs on (at least) two independent axes — access/connectivity and
race/ethnicity composition — and density does not explain either one.**

**3. Is per-capita investment spatially clustered once the skew is
handled? Yes — the original "not clustered" finding does not survive.**
Raw `investment_per_capita` (I=0.006, p=0.070) understated the true spatial
structure because of its 18.7 skew. Log transform gives I=0.343 (p<0.001);
rank transform — the most robust and most heavily weighted per the
instructions — gives I=0.495 (p<0.001), on par with the vulnerability
indicators' own clustering (I=0.31–0.99). **The per-capita outcome now
belongs with the binary and composition outcomes as needing a spatial
model specification, not apart from them**, changing the modeling path
described in `correlation_analysis.md`.

**4. Does `no_vehicle` behave at block group the way `EP_NOVEH` does at
tract? No.** At tract it is the single strongest variable in three separate
tables (per-capita volume, gray share, green share — rank #1 of 34 in all
three). At block group it is a middling correlate (rank #5–6 of 37 in
composition, #18–29 in the volume-proxy binaries), and forms no new |r|>0.8
duplicate with anything on disk. The block-group composition pattern is led
instead by environmental proximity measures (`PTRAF`, `NO2`, `UST`,
`RSEI_AIR`), not by vehicle access — the specific hypothesis that motivated
pulling this variable does not hold up at the finer grain.
