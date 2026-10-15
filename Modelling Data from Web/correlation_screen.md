# Correlation screen before PCA: vulnerability indicators

Screen only. Nothing has been dropped, imputed or modelled, and no PCA has been run.
The rule being applied is the professor's: if two indicators correlate above
0.75, one is dropped. Which one is dropped is **not** recommended here.

**Method.** Spearman rank correlation, pairwise-complete observations, with n
reported for every listed pair. The absolute value is compared against 0.75
unrounded (the listed values are rounded to three decimals for display only);
the sign is reported. A pair is listed if |rho| >= 0.75. Near misses are
0.70 <= |rho| < 0.75. A **cluster** is any set of indicators connected through
one or more above-line links. The **minimum drop sets** are every smallest set
of indicators whose removal leaves no above-line pair inside the cluster
(minimum vertex covers, enumerated exhaustively). Tract and block group are
screened separately and never mixed.

**Status column.** DATA_PROCESSING.md grades only the ten tract ACS variables
(clean / threshold approximation / proxy). For every other variable the status
is taken from the variable table in FINDINGS_FOR_PROFESSOR.md Sec 2, which
extends it; `*_decision_support.csv` records which source each status came from.

**Headline-finding column.** "yes" marks the access indicators behind the gray
and green composition result: households with no vehicle (both versions),
multi-unit housing, no internet access, no broadband subscription and minority
population share. At block group, no multi-unit housing, no internet access or
second no-vehicle measure exists; the block-group composition result used
EJScreen's people of colour share (`PEOPCOLORPCT`), which has the same
definition as minority share, so it is marked as the block-group counterpart.

Script: `scripts/correlation_screen.py`. Outputs: `output/correlation_screen/`.
Decision sheets to fill in: `output/correlation_screen/correlation_decisions_tract.csv`
and `output/correlation_screen/correlation_decisions_blockgroup.csv`.

![Tract heatmap](output/correlation_screen/tract_spearman_heatmap.png)

![Block group heatmap](output/correlation_screen/blockgroup_spearman_heatmap.png)

## Tract (698 tracts)

### Scope checks

- **Race / ethnicity adjuncts: 7 of 7 are still present in `tract_analysis.csv`**: Hispanic population share (`EP_HISP`), Black population share (`EP_AFAM`), Asian population share (`EP_ASIAN`), Two or more races share (`EP_TWOMORE`), Other race share (`EP_OTHERRACE`), American Indian / Alaska Native share (`EP_AIAN`), Native Hawaiian / Pacific Islander share (`EP_NHPI`). The table itself has not been updated. They are **excluded from this screen**. (`scripts/analysis_variables.py` `TRACT_VULN_VARS` also still lists all 34.)
- Minority population share (`EP_MINRTY`) is retained. No internet access (`EP_NOINT`) is retained.
- Indicators screened: 27 (expected 27). Rows: 698 (expected 698).
- Not read: investment outcomes, FEMA hazard losses, sea level rise, storm surge, flood.

### Counts

- Indicators screened: **27** (351 distinct pairs)
- Pairs with |rho| >= 0.75: **8**
- Clusters: **8**, covering **16** variables
- Near misses (0.70 <= |rho| < 0.75): **4**

Files: `output/correlation_screen/tract_spearman_matrix.csv`, `tract_pairwise_n_matrix.csv`, `tract_spearman_heatmap.png`, `tract_pairs_at_or_above_075.csv`, `tract_near_misses_070_075.csv`, `tract_clusters.csv`, `tract_cluster_links.csv`, `tract_decision_support.csv`, `correlation_decisions_tract.csv`.

### Every pair at or above 0.75, ranked by |rho|

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | No high school diploma (`EP_NOHSDP`) | No high school diploma (adults 25+) (`no_diploma_pop25`) | +0.898 | 698 |
| 2 | Aged 65 and over (`EP_AGE65`) | Aged 65 and over (ACS) (`age65plus`) | +0.877 | 698 |
| 3 | No internet access (`EP_NOINT`) | No broadband subscription (`no_broadband`) | +0.862 | 697 |
| 4 | Without health insurance (`EP_UNINSUR`) | Without health insurance (ACS) (`uninsured`) | +0.849 | 698 |
| 5 | Households with no vehicle (`EP_NOVEH`) | Households with no vehicle (ACS) (`no_vehicle`) | +0.841 | 697 |
| 6 | Below 150% of poverty line (`EP_POV150`) | Below 125% of poverty line (`poverty_under125`) | +0.825 | 697 |
| 7 | Limited English speaking households (`EP_LIMENG`) | Limited English speaking households (ACS) (`limited_english_hh`) | +0.821 | 698 |
| 8 | With a disability (`EP_DISABL`) | With a disability (ACS) (`disability`) | +0.764 | 698 |

### Clusters

#### Cluster T1 (2 variables, 1 links)

Members: No high school diploma (`EP_NOHSDP`); No high school diploma (adults 25+) (`no_diploma_pop25`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | No high school diploma (`EP_NOHSDP`) | No high school diploma (adults 25+) (`no_diploma_pop25`) | +0.898 | 698 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- No high school diploma (`EP_NOHSDP`)
- No high school diploma (adults 25+) (`no_diploma_pop25`)

#### Cluster T2 (2 variables, 1 links)

Members: Aged 65 and over (`EP_AGE65`); Aged 65 and over (ACS) (`age65plus`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Aged 65 and over (`EP_AGE65`) | Aged 65 and over (ACS) (`age65plus`) | +0.877 | 698 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- Aged 65 and over (`EP_AGE65`)
- Aged 65 and over (ACS) (`age65plus`)

#### Cluster T3 (2 variables, 1 links)

Members: No internet access (`EP_NOINT`); No broadband subscription (`no_broadband`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | No internet access (`EP_NOINT`) | No broadband subscription (`no_broadband`) | +0.862 | 697 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- No internet access (`EP_NOINT`)
- No broadband subscription (`no_broadband`)

#### Cluster T4 (2 variables, 1 links)

Members: Without health insurance (`EP_UNINSUR`); Without health insurance (ACS) (`uninsured`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Without health insurance (`EP_UNINSUR`) | Without health insurance (ACS) (`uninsured`) | +0.849 | 698 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- Without health insurance (`EP_UNINSUR`)
- Without health insurance (ACS) (`uninsured`)

#### Cluster T5 (2 variables, 1 links)

Members: Households with no vehicle (`EP_NOVEH`); Households with no vehicle (ACS) (`no_vehicle`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Households with no vehicle (`EP_NOVEH`) | Households with no vehicle (ACS) (`no_vehicle`) | +0.841 | 697 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- Households with no vehicle (`EP_NOVEH`)
- Households with no vehicle (ACS) (`no_vehicle`)

#### Cluster T6 (2 variables, 1 links)

Members: Below 150% of poverty line (`EP_POV150`); Below 125% of poverty line (`poverty_under125`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Below 150% of poverty line (`EP_POV150`) | Below 125% of poverty line (`poverty_under125`) | +0.825 | 697 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- Below 150% of poverty line (`EP_POV150`)
- Below 125% of poverty line (`poverty_under125`)

#### Cluster T7 (2 variables, 1 links)

Members: Limited English speaking households (`EP_LIMENG`); Limited English speaking households (ACS) (`limited_english_hh`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Limited English speaking households (`EP_LIMENG`) | Limited English speaking households (ACS) (`limited_english_hh`) | +0.821 | 698 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- Limited English speaking households (`EP_LIMENG`)
- Limited English speaking households (ACS) (`limited_english_hh`)

#### Cluster T8 (2 variables, 1 links)

Members: With a disability (`EP_DISABL`); With a disability (ACS) (`disability`)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | With a disability (`EP_DISABL`) | With a disability (ACS) (`disability`) | +0.764 | 698 |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **1**. There are 2 such sets (information only, not a recommendation):

- With a disability (`EP_DISABL`)
- With a disability (ACS) (`disability`)


### Near misses, 0.70 to 0.75 (not covered by the rule)

| # | variable A | variable B | rho | n |
|---|---|---|---|---|
| 1 | Below 150% of poverty line (`EP_POV150`) | Housing cost burdened (`EP_HBURD`) | +0.746 | 697 |
| 2 | Crowded housing (`EP_CROWD`) | Crowded housing (over 1 per room) (`crowding_over100`) | +0.721 | 697 |
| 3 | No high school diploma (`EP_NOHSDP`) | Limited English speaking households (`EP_LIMENG`) | +0.705 | 698 |
| 4 | No high school diploma (`EP_NOHSDP`) | Minority population share (`EP_MINRTY`) | +0.700 | 698 |

### Decision support, every variable in an above-line pair

| cluster | variable | code | source | status | % missing | partners >= 0.75 | mean abs rho (all others) | in headline finding |
|---|---|---|---|---|---|---|---|---|
| T1 | No high school diploma | `EP_NOHSDP` | SVI | clean | 0.0 | 1 | 0.414 | no |
| T1 | No high school diploma (adults 25+) | `no_diploma_pop25` | ACS | proxy | 0.0 | 1 | 0.404 | no |
| T2 | Aged 65 and over | `EP_AGE65` | SVI | clean | 0.0 | 1 | 0.202 | no |
| T2 | Aged 65 and over (ACS) | `age65plus` | ACS | clean | 0.0 | 1 | 0.199 | no |
| T3 | No internet access | `EP_NOINT` | SVI | clean | 0.1 | 1 | 0.422 | yes |
| T3 | No broadband subscription | `no_broadband` | ACS | proxy | 0.0 | 1 | 0.404 | yes |
| T4 | Without health insurance | `EP_UNINSUR` | SVI | clean | 0.0 | 1 | 0.360 | no |
| T4 | Without health insurance (ACS) | `uninsured` | ACS | clean | 0.0 | 1 | 0.359 | no |
| T5 | Households with no vehicle | `EP_NOVEH` | SVI | clean | 0.1 | 1 | 0.339 | yes |
| T5 | Households with no vehicle (ACS) | `no_vehicle` | ACS | clean | 0.0 | 1 | 0.330 | yes |
| T6 | Below 150% of poverty line | `EP_POV150` | SVI | clean | 0.1 | 1 | 0.423 | no |
| T6 | Below 125% of poverty line | `poverty_under125` | ACS | threshold approximation | 0.0 | 1 | 0.400 | no |
| T7 | Limited English speaking households | `EP_LIMENG` | SVI | clean | 0.0 | 1 | 0.360 | no |
| T7 | Limited English speaking households (ACS) | `limited_english_hh` | ACS | clean | 0.0 | 1 | 0.387 | no |
| T8 | With a disability | `EP_DISABL` | SVI | clean | 0.0 | 1 | 0.331 | no |
| T8 | With a disability (ACS) | `disability` | ACS | clean | 0.0 | 1 | 0.319 | no |

Status notes:

- `no_diploma_pop25`: person-level for a household concept
- `no_broadband`: Total minus broadband of any type
- `poverty_under125`: 1.25 vs CRE 1.30

## Block group (1,843 block groups)

### Scope checks

- Indicators screened: 37 (expected 37). Rows: 1843 (expected 1,843).
- **Environmental exposure group (13 EJScreen measures), reported separately below:** Fine particulate matter (`PM25`), Ozone (`OZONE`), Nitrogen dioxide (`NO2`), Diesel particulate matter (`DSLPM`), Air toxics released (`RSEI_AIR`), Traffic proximity (`PTRAF`), Superfund site proximity (`PNPL`), Chemical accident risk site proximity (`PRMP`), Hazardous waste site proximity (`PTSDF`), Underground storage tanks (`UST`), Wastewater discharge (`PWDIS`), Drinking water non-compliance (`DWATER`), Pre-1960 housing (lead paint indicator) (`PRE1960PCT`).
- The other 24 are the block-group vulnerability indicators. Every pair table carries a `group` column (vulnerability x vulnerability, vulnerability x environmental, environmental x environmental), and the decision-support table gives mean |rho| both against all 36 others and against the 24 non-environmental indicators only, so the effect of the inclusion decision is visible.
- Not read: investment outcomes, FEMA hazard losses, sea level rise, storm surge, flood.

### Counts

- Indicators screened: **37** (666 distinct pairs)
- Pairs with |rho| >= 0.75: **8**
- Clusters: **1**, covering **9** variables
- Near misses (0.70 <= |rho| < 0.75): **12**
- Listed pairs (>= 0.75) resting on 1,200 block groups or fewer: **0**
- Pairs >= 0.75 by group: environmental x environmental: 8

Files: `output/correlation_screen/blockgroup_spearman_matrix.csv`, `blockgroup_pairwise_n_matrix.csv`, `blockgroup_spearman_heatmap.png`, `blockgroup_pairs_at_or_above_075.csv`, `blockgroup_near_misses_070_075.csv`, `blockgroup_clusters.csv`, `blockgroup_cluster_links.csv`, `blockgroup_decision_support.csv`, `correlation_decisions_blockgroup.csv`.

### Every pair at or above 0.75, ranked by |rho|

| # | variable A | variable B | rho | n | group | n <= 1,200? |
|---|---|---|---|---|---|---|
| 1 | Fine particulate matter (`PM25`) | Ozone (`OZONE`) | +0.950 | 1,843 | environmental x environmental |  |
| 2 | Diesel particulate matter (`DSLPM`) | Traffic proximity (`PTRAF`) | +0.804 | 1,837 | environmental x environmental |  |
| 3 | Fine particulate matter (`PM25`) | Diesel particulate matter (`DSLPM`) | +0.800 | 1,837 | environmental x environmental |  |
| 4 | Diesel particulate matter (`DSLPM`) | Air toxics released (`RSEI_AIR`) | +0.790 | 1,837 | environmental x environmental |  |
| 5 | Nitrogen dioxide (`NO2`) | Traffic proximity (`PTRAF`) | +0.785 | 1,827 | environmental x environmental |  |
| 6 | Nitrogen dioxide (`NO2`) | Hazardous waste site proximity (`PTSDF`) | +0.769 | 1,827 | environmental x environmental |  |
| 7 | Air toxics released (`RSEI_AIR`) | Chemical accident risk site proximity (`PRMP`) | +0.759 | 1,837 | environmental x environmental |  |
| 8 | Superfund site proximity (`PNPL`) | Chemical accident risk site proximity (`PRMP`) | +0.757 | 1,837 | environmental x environmental |  |

### Clusters

#### Cluster B1 (9 variables, 8 links)

Members: Fine particulate matter (`PM25`); Ozone (`OZONE`); Nitrogen dioxide (`NO2`); Diesel particulate matter (`DSLPM`); Air toxics released (`RSEI_AIR`); Traffic proximity (`PTRAF`); Superfund site proximity (`PNPL`); Chemical accident risk site proximity (`PRMP`); Hazardous waste site proximity (`PTSDF`)

| # | variable A | variable B | rho | n | n <= 1,200? |
|---|---|---|---|---|---|
| 1 | Fine particulate matter (`PM25`) | Ozone (`OZONE`) | +0.950 | 1,843 |  |
| 2 | Diesel particulate matter (`DSLPM`) | Traffic proximity (`PTRAF`) | +0.804 | 1,837 |  |
| 3 | Fine particulate matter (`PM25`) | Diesel particulate matter (`DSLPM`) | +0.800 | 1,837 |  |
| 4 | Diesel particulate matter (`DSLPM`) | Air toxics released (`RSEI_AIR`) | +0.790 | 1,837 |  |
| 5 | Nitrogen dioxide (`NO2`) | Traffic proximity (`PTRAF`) | +0.785 | 1,827 |  |
| 6 | Nitrogen dioxide (`NO2`) | Hazardous waste site proximity (`PTSDF`) | +0.769 | 1,827 |  |
| 7 | Air toxics released (`RSEI_AIR`) | Chemical accident risk site proximity (`PRMP`) | +0.759 | 1,837 |  |
| 8 | Superfund site proximity (`PNPL`) | Chemical accident risk site proximity (`PRMP`) | +0.757 | 1,837 |  |

Smallest number of drops that leaves no pair in this cluster at or above 0.75: **4**. There are 2 such sets (information only, not a recommendation):

- Ozone (`OZONE`), Nitrogen dioxide (`NO2`), Diesel particulate matter (`DSLPM`), Chemical accident risk site proximity (`PRMP`)
- Fine particulate matter (`PM25`), Nitrogen dioxide (`NO2`), Diesel particulate matter (`DSLPM`), Chemical accident risk site proximity (`PRMP`)


### Near misses, 0.70 to 0.75 (not covered by the rule)

| # | variable A | variable B | rho | n | group | n <= 1,200? |
|---|---|---|---|---|---|---|
| 1 | Fine particulate matter (`PM25`) | Air toxics released (`RSEI_AIR`) | +0.741 | 1,842 | environmental x environmental |  |
| 2 | Ozone (`OZONE`) | Diesel particulate matter (`DSLPM`) | +0.739 | 1,837 | environmental x environmental |  |
| 3 | Air toxics released (`RSEI_AIR`) | Traffic proximity (`PTRAF`) | +0.735 | 1,837 | environmental x environmental |  |
| 4 | Ozone (`OZONE`) | Air toxics released (`RSEI_AIR`) | +0.733 | 1,842 | environmental x environmental |  |
| 5 | Traffic proximity (`PTRAF`) | Hazardous waste site proximity (`PTSDF`) | +0.719 | 1,837 | environmental x environmental |  |
| 6 | Low income (`LOWINCPCT`) | Below 150% of poverty line (`poverty_under150`) | +0.718 | 1,832 | vulnerability x vulnerability |  |
| 7 | Median home value (`median_home_value`) | Median monthly mortgage cost (`median_monthly_mortgage`) | +0.716 | 1,200 | vulnerability x vulnerability | **yes** |
| 8 | Diesel particulate matter (`DSLPM`) | Chemical accident risk site proximity (`PRMP`) | +0.711 | 1,837 | environmental x environmental |  |
| 9 | Low income (`LOWINCPCT`) | Median family income (`median_family_income`) | -0.710 | 1,496 | vulnerability x vulnerability |  |
| 10 | Below 150% of poverty line (`poverty_under150`) | Median family income (`median_family_income`) | -0.706 | 1,496 | vulnerability x vulnerability |  |
| 11 | Air toxics released (`RSEI_AIR`) | Superfund site proximity (`PNPL`) | +0.702 | 1,837 | environmental x environmental |  |
| 12 | Air toxics released (`RSEI_AIR`) | Hazardous waste site proximity (`PTSDF`) | +0.700 | 1,837 | environmental x environmental |  |

### Decision support, every variable in an above-line pair

| cluster | variable | code | source | status | % missing | partners >= 0.75 | mean abs rho (all others) | mean abs rho (24 non-environmental) | in headline finding |
|---|---|---|---|---|---|---|---|---|---|
| B1 | Fine particulate matter | `PM25` | EJScreen | clean | 0.0 | 2 | 0.230 | 0.129 | no |
| B1 | Ozone | `OZONE` | EJScreen | clean | 0.0 | 1 | 0.210 | 0.107 | no |
| B1 | Nitrogen dioxide | `NO2` | EJScreen | clean | 0.6 | 2 | 0.297 | 0.212 | no |
| B1 | Diesel particulate matter | `DSLPM` | EJScreen | clean | 0.3 | 3 | 0.320 | 0.205 | no |
| B1 | Air toxics released | `RSEI_AIR` | EJScreen | clean | 0.1 | 2 | 0.302 | 0.172 | no |
| B1 | Traffic proximity | `PTRAF` | EJScreen | clean | 0.3 | 2 | 0.310 | 0.195 | no |
| B1 | Superfund site proximity | `PNPL` | EJScreen | clean | 0.3 | 1 | 0.322 | 0.255 | no |
| B1 | Chemical accident risk site proximity | `PRMP` | EJScreen | clean | 0.3 | 2 | 0.306 | 0.219 | no |
| B1 | Hazardous waste site proximity | `PTSDF` | EJScreen | clean | 0.3 | 1 | 0.273 | 0.167 | no |
