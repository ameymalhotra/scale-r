# Principal component analysis of the vulnerability indicators

Tract and block group are analysed separately and never mixed. Inputs are the
variable lists recorded in DATA_PROCESSING.md Sec 7 ("Variable reduction before
PCA"): 19 tract variables and 24 block-group social variables. The 13 EJScreen
environmental measures are excluded (provisional, pending the professor). No
hazard or investment variable enters any PCA, nothing is modelled, and nothing
is imputed.

**Nothing here is final.** The number of components and every component name
are proposals for you to confirm. Component scores are saved in
`output/pca/pca_scores_tract.csv` and `output/pca/pca_scores_blockgroup.csv`
(GEOID as string) and are not used anywhere.

**Method.**
- Primary run: each variable standardized (mean 0, SD 1), PCA on the
  correlation matrix. Sensitivity run: each variable replaced by its average
  rank, then standardized (consistent with the Spearman screen).
- Complete cases only, n reported per run.
- Suitability: Kaiser-Meyer-Olkin, overall and per variable (flag below 0.5),
  and Bartlett's test of sphericity.
- Retention criteria side by side: eigenvalue above 1, scree plot, and Horn's
  parallel analysis (1000 random normal data sets of the same n and p;
  a component is retained while its eigenvalue exceeds the 95th
  percentile of the random eigenvalues).
- Loadings are correlations between variable and component. Rotation is
  varimax with Kaiser normalisation (the SoVI convention). Communality is the
  share of a variable's variance reproduced by the retained components;
  flagged below 0.5.
- Primary and rank runs are compared by Tucker's congruence coefficient on
  matched rotated components: 0.95 or above is treated as the same
  component, 0.85 to 0.95 as fair similarity, below 0.85 as different
  (Lorenzo-Seva and ten Berge 2006).

Script: `scripts/pca_analysis.py`. Figures and tables: `output/pca/`.

## Proposals for you to confirm

| run | n | eigenvalue > 1 | scree | parallel analysis | proposed k | variance explained |
|---|---|---|---|---|---|---|
| Tract, 19 variables | 697 | 5 | 3 (sharp break after 1; curve flattens after 3) | 5 | **5** | 67.5% |
| Block group, all 24 variables | 518 | 7 | 3 (sharp break after 1; curve flattens after 3) | 6 | **6** | 58.0% |
| Block group, 21 variables (3 over 20% missing excluded) | 1,247 | 6 | 3 (sharp break after 1; curve flattens after 3) | 4 | **4** | 50.4% |

- Tract, 19 variables: RC1 *General socioeconomic disadvantage*; RC2 *Older, non-working and disabled households*; RC3 *Families with children and unemployment*; RC4 *Multi-unit housing versus minority share*; RC5 *Group quarters*
- Block group, all 24 variables: RC1 *Low income, low education and people of colour*; RC2 *Renters without a vehicle or broadband*; RC3 *Housing costs and family income*; RC4 *Older residents versus young families*; RC5 *Low life expectancy and unemployment*; RC6 *Incomplete plumbing and kitchens*
- Block group, 21 variables (3 over 20% missing excluded): RC1 *Low income, low education and people of colour*; RC2 *Poverty, renting and lack of vehicle or broadband*; RC3 *Older residents versus single-parent families*; RC4 *Incomplete kitchens*

---

## Tract

### Sample

- Variables: **19**. Complete cases: **n = 697** of 698 units (1 excluded for a missing value in at least one variable; nothing imputed).
- Units missing each variable (before listwise exclusion): Below 150% of poverty line 1, Housing cost burdened 1, Multi-unit housing structures 1, Mobile homes 1, Crowded housing 1, Households with no vehicle 1, No internet access 1, Single-parent households 1.

### Suitability

| run | overall KMO | Bartlett chi-square | df | p |
|---|---|---|---|---|
| standardized (primary) | 0.800 | 6,566.2 | 171 | 0 |
| rank (sensitivity) | 0.850 | 6,602.5 | 171 | 0 |

| variable | code | KMO standardized | KMO rank | flag (< 0.5) |
|---|---|---|---|---|
| Below 150% of poverty line | `EP_POV150` | 0.908 | 0.918 |  |
| Unemployed | `EP_UNEMP` | 0.773 | 0.809 |  |
| Households with no workers | `no_fulltime_worker_hh` | 0.731 | 0.732 |  |
| Housing cost burdened | `EP_HBURD` | 0.888 | 0.893 |  |
| No high school diploma | `EP_NOHSDP` | 0.866 | 0.902 |  |
| Multi-unit housing structures | `EP_MUNIT` | 0.486 | 0.570 | **yes** |
| Mobile homes | `EP_MOBILE` | 0.717 | 0.809 |  |
| Crowded housing | `EP_CROWD` | 0.786 | 0.827 |  |
| Crowded housing (over 1 per room) | `crowding_over100` | 0.801 | 0.845 |  |
| Living in group quarters | `EP_GROUPQ` | 0.284 | 0.789 | **yes** |
| Households with no vehicle | `EP_NOVEH` | 0.851 | 0.876 |  |
| No internet access | `EP_NOINT` | 0.922 | 0.930 |  |
| Minority population share | `EP_MINRTY` | 0.758 | 0.889 |  |
| Limited English speaking households | `EP_LIMENG` | 0.836 | 0.867 |  |
| Aged 65 and over | `EP_AGE65` | 0.592 | 0.632 |  |
| Aged 17 and under | `EP_AGE17` | 0.498 | 0.603 | **yes** |
| Single-parent households | `EP_SNGPNT` | 0.731 | 0.773 |  |
| Without health insurance | `EP_UNINSUR` | 0.905 | 0.928 |  |
| With a disability | `EP_DISABL` | 0.891 | 0.922 |  |

Per-variable KMO below 0.5: Multi-unit housing structures, Living in group quarters, Aged 17 and under.

### Eigenvalues and retention criteria

| component | eigenvalue | % variance | cumulative % | PA 95th pct | > 1 | > PA | rank-run eigenvalue |
|---|---|---|---|---|---|---|---|
| PC1 | 5.699 | 30.0 | 30.0 | 1.351 | yes | yes | 6.092 |
| PC2 | 2.568 | 13.5 | 43.5 | 1.286 | yes | yes | 2.478 |
| PC3 | 1.760 | 9.3 | 52.8 | 1.240 | yes | yes | 1.835 |
| PC4 | 1.567 | 8.2 | 61.0 | 1.196 | yes | yes | 1.381 |
| PC5 | 1.225 | 6.4 | 67.5 | 1.161 | yes | yes | 1.048 |
| PC6 | 0.962 | 5.1 | 72.5 | 1.128 |  |  | 0.968 |
| PC7 | 0.867 | 4.6 | 77.1 | 1.099 |  |  | 0.798 |
| PC8 | 0.714 | 3.8 | 80.8 | 1.069 |  |  | 0.731 |
| PC9 | 0.584 | 3.1 | 83.9 | 1.041 |  |  | 0.548 |
| PC10 | 0.455 | 2.4 | 86.3 | 1.014 |  |  | 0.484 |
| PC11 | 0.441 | 2.3 | 88.6 | 0.986 |  |  | 0.447 |
| PC12 | 0.383 | 2.0 | 90.7 | 0.962 |  |  | 0.396 |
| PC13 | 0.362 | 1.9 | 92.6 | 0.936 |  |  | 0.331 |
| PC14 | 0.305 | 1.6 | 94.2 | 0.910 |  |  | 0.295 |
| PC15 | 0.287 | 1.5 | 95.7 | 0.885 |  |  | 0.280 |
| PC16 | 0.237 | 1.2 | 96.9 | 0.858 |  |  | 0.268 |
| PC17 | 0.220 | 1.2 | 98.1 | 0.833 |  |  | 0.220 |
| PC18 | 0.186 | 1.0 | 99.1 | 0.804 |  |  | 0.205 |
| PC19 | 0.178 | 0.9 | 100.0 | 0.770 |  |  | 0.196 |

| criterion | standardized | rank |
|---|---|---|
| Eigenvalue > 1 (Kaiser) | 5 | 5 |
| Scree plot (elbow, read visually) | 3 (sharp break after 1; curve flattens after 3) | same plot |
| Parallel analysis (Horn, 95th pct, 1000 draws) | 5 | 4 |

Scree plot: `output/pca/scree_tract.png`.

**Proposed number of components: 5** (pending your confirmation). Eigenvalue above 1 and parallel analysis agree on 5 in the standardized run, and PC5 (1.225) clears the parallel-analysis line (1.161) by a clear margin. The scree reads 3, but 3 components leave seven variables with communality below 0.5, and none of the three replicates cleanly under ranks (congruence 0.80 to 0.85). **Caveats:** RC5 is essentially a single variable (group quarters), and RC4 and RC5 do not replicate in the rank run, where PC5 falls below the parallel-analysis line (rank run: parallel analysis 4). **Alternative: k = 4.** RC1 to RC3 then replicate at 0.95 or above; RC4 (multi-unit versus minority) still does not (0.56); group quarters is left almost unexplained (communality 0.06).

### Loadings, retained components (k = 5)

PC = unrotated, RC = varimax-rotated (Kaiser-normalised). Bold: |loading| >= 0.5. Each component is oriented so its largest loading is positive; the sign of a whole component is arbitrary.

| variable | PC1 | PC2 | PC3 | PC4 | PC5 | RC1 | RC2 | RC3 | RC4 | RC5 | communality |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Below 150% of poverty line | +0.84 | -0.08 | +0.15 | +0.15 | +0.01 | **+0.68** | +0.34 | +0.39 | -0.08 | +0.17 | 0.77 |
| Unemployed | +0.32 | -0.23 | +0.41 | +0.51 | +0.03 | +0.11 | +0.17 | **+0.71** | +0.06 | +0.18 | 0.58 |
| Households with no workers | +0.39 | +0.57 | +0.21 | +0.35 | -0.39 | +0.09 | **+0.86** | +0.14 | +0.17 | -0.12 | 0.80 |
| Housing cost burdened | +0.76 | -0.04 | +0.24 | -0.12 | +0.05 | **+0.73** | +0.21 | +0.20 | +0.12 | +0.16 | 0.66 |
| No high school diploma | +0.82 | -0.04 | -0.32 | +0.10 | +0.13 | **+0.66** | +0.29 | +0.10 | -0.47 | +0.21 | 0.80 |
| Multi-unit housing structures | +0.10 | +0.30 | +0.67 | -0.48 | +0.03 | +0.27 | +0.05 | -0.16 | **+0.82** | +0.11 | 0.78 |
| Mobile homes | +0.20 | -0.06 | -0.25 | +0.11 | +0.19 | +0.12 | +0.02 | +0.01 | -0.32 | +0.18 | 0.15 **low** |
| Crowded housing | +0.56 | -0.32 | -0.01 | -0.40 | -0.23 | **+0.74** | -0.13 | +0.05 | -0.02 | -0.26 | 0.63 |
| Crowded housing (over 1 per room) | +0.60 | -0.33 | -0.05 | -0.40 | -0.17 | **+0.77** | -0.14 | +0.04 | -0.06 | -0.21 | 0.67 |
| Living in group quarters | +0.11 | +0.05 | +0.08 | +0.21 | +0.83 | -0.02 | -0.06 | +0.07 | -0.09 | **+0.86** | 0.76 |
| Households with no vehicle | +0.62 | +0.28 | +0.46 | -0.06 | +0.05 | **+0.53** | +0.42 | +0.14 | +0.39 | +0.24 | 0.69 |
| No internet access | +0.77 | +0.22 | +0.09 | +0.01 | +0.01 | **+0.62** | +0.47 | +0.09 | +0.00 | +0.18 | 0.65 |
| Minority population share | +0.59 | -0.23 | -0.52 | +0.04 | +0.02 | **+0.52** | +0.06 | +0.04 | **-0.63** | -0.01 | 0.67 |
| Limited English speaking households | +0.66 | +0.22 | -0.47 | -0.24 | -0.01 | **+0.63** | +0.32 | -0.35 | -0.38 | +0.01 | 0.76 |
| Aged 65 and over | +0.08 | +0.79 | -0.22 | +0.20 | -0.25 | -0.18 | **+0.79** | -0.35 | -0.06 | -0.08 | 0.78 |
| Aged 17 and under | -0.03 | -0.70 | +0.08 | +0.36 | -0.40 | -0.05 | -0.26 | **+0.70** | -0.19 | -0.44 | 0.78 |
| Single-parent households | +0.39 | -0.54 | +0.21 | +0.39 | -0.01 | +0.28 | -0.08 | **+0.73** | -0.15 | +0.04 | 0.64 |
| Without health insurance | +0.70 | -0.20 | +0.04 | -0.18 | +0.11 | **+0.72** | +0.01 | +0.14 | -0.07 | +0.15 | 0.57 |
| With a disability | +0.57 | +0.44 | -0.18 | +0.33 | -0.02 | +0.26 | **+0.71** | +0.02 | -0.26 | +0.17 | 0.66 |

Variance carried after rotation: RC1 24.9%, RC2 14.4%, RC3 10.9%, RC4 9.9%, RC5 7.3% (total 67.5%, same as the first 5 unrotated components).

### Components: salient variables and suggested names

Names are **suggestions only**, based on the variables loading at |0.5| or more.

- **RC1**, suggested name: *General socioeconomic disadvantage*. Loading at |0.5| or more: Crowded housing (over 1 per room) (+0.77); Crowded housing (+0.74); Housing cost burdened (+0.73); Without health insurance (+0.72); Below 150% of poverty line (+0.68); No high school diploma (+0.66); Limited English speaking households (+0.63); No internet access (+0.62); Households with no vehicle (+0.53); Minority population share (+0.52).
- **RC2**, suggested name: *Older, non-working and disabled households*. Loading at |0.5| or more: Households with no workers (+0.86); Aged 65 and over (+0.79); With a disability (+0.71).
- **RC3**, suggested name: *Families with children and unemployment*. Loading at |0.5| or more: Single-parent households (+0.73); Unemployed (+0.71); Aged 17 and under (+0.70).
- **RC4**, suggested name: *Multi-unit housing versus minority share*. Loading at |0.5| or more: Multi-unit housing structures (+0.82); Minority population share (-0.63).
- **RC5**, suggested name: *Group quarters*. Loading at |0.5| or more: Living in group quarters (+0.86).

Variables with no loading at |0.5| or more on any retained component: Mobile homes.

**Communality below 0.5** (less than half the variable's variance explained by the 5 retained components): Mobile homes (0.15).

### Sensitivity: rank-transformed PCA

Same complete cases, each variable replaced by its average rank then standardized; same k = 5, same rotation. Components matched by maximum |Tucker congruence|.

| primary component | matched rank component | congruence (phi) | correlation of scores | reading |
|---|---|---|---|---|
| RC1 | RC1 | +0.946 | +0.842 | fair similarity (0.85 to 0.95) |
| RC2 | RC2 | +0.946 | +0.920 | fair similarity (0.85 to 0.95) |
| RC3 | RC4 | +0.978 | +0.897 | equal (>= 0.95) |
| RC4 | RC3 | +0.615 | +0.810 | **different (< 0.85)** |
| RC5 | RC5 | +0.051 | -0.116 | **different (< 0.85)** |

**Verdict: materially different for at least one component.** Unrotated congruence, PC1 to PC5: +0.995, +0.982, +0.831, +0.881, -0.031. Criteria on the rank run: eigenvalue > 1 gives 5, parallel analysis gives 4 (standardized run: 5 and 5).

Changes in the salient (|0.5|) variable set under ranks: RC1: loses Households with no vehicle; RC4: gains Housing cost burdened, Households with no vehicle; loses Minority population share; RC5: gains Mobile homes; loses Living in group quarters.

### Relevance to earlier findings

Headline access variables (households with no vehicle, multi-unit housing, no internet access) and minority population share, on the varimax components of the standardized run. The ACS versions of no vehicle and no broadband were dropped at the screen, so only the SVI versions appear.

| variable | code | RC1 | RC2 | RC3 | RC4 | RC5 | highest loading on | communality |
|---|---|---|---|---|---|---|---|---|
| Households with no vehicle | `EP_NOVEH` | **+0.53** | +0.42 | +0.14 | +0.39 | +0.24 | RC1 | 0.69 |
| Multi-unit housing structures | `EP_MUNIT` | +0.27 | +0.05 | -0.16 | **+0.82** | +0.11 | RC4 | 0.78 |
| No internet access | `EP_NOINT` | **+0.62** | +0.47 | +0.09 | +0.00 | +0.18 | RC1 | 0.65 |
| Minority population share | `EP_MINRTY` | **+0.52** | +0.06 | +0.04 | **-0.63** | -0.01 | RC4 | 0.67 |

Spearman rho among these variables on the PCA sample: Households with no vehicle vs Multi-unit housing structures +0.469; Households with no vehicle vs No internet access +0.629; Households with no vehicle vs Minority population share +0.180; Multi-unit housing structures vs No internet access +0.219; Multi-unit housing structures vs Minority population share -0.164; No internet access vs Minority population share +0.448.

Minority population share loads highest on RC4 (Multi-unit housing versus minority share). Households with no vehicle loads highest on RC1 (General socioeconomic disadvantage); Multi-unit housing structures loads highest on RC4 (Multi-unit housing versus minority share); No internet access loads highest on RC1 (General socioeconomic disadvantage). **Partly merged:** minority composition shares its main component with Multi-unit housing structures, and is separated from Households with no vehicle, No internet access. On RC1, Minority population share loads +0.52 and Households with no vehicle +0.53, No internet access +0.62 (same sign). On RC4, Minority population share loads -0.63 and Multi-unit housing structures +0.82 (opposite signs). On the 0.38 to 0.45 figures from the earlier analysis: minority share correlates +0.379 with no broadband subscription (dropped at the screen) and, as above, with no internet access. Its correlation with the vehicle and multi-unit measures is much weaker, so the 0.38 to 0.45 overlap is specific to connectivity.

---

## Block group

With all 24 variables, complete cases are **518** of 1,843, below the roughly 1,200 threshold. So two versions are reported and **you choose between them**:

- **24 variables, n = 518.** Every social indicator, on the block groups that report all of them.
- **21 variables, n = 1,247.** Excludes the three variables above 20% missing: Income disparity (low to high earner ratio) (`income_disparity`), Median gross rent (`median_gross_rent`), Median monthly mortgage cost (`median_monthly_mortgage`). Median family income (18.8%) and median home value (16.7%) are under the 20% line and stay in.

The complete-case block groups are not a random subset: a block group drops out when a median is suppressed (small sample) or income disparity is undefined (zero households in a bracket), so the smaller sample leans toward larger, more populous block groups.

### Block group, version A: all 24 variables

### Sample

- Variables: **24**. Complete cases: **n = 518** of 1,843 units (1,325 excluded for a missing value in at least one variable; nothing imputed).
- Units missing each variable (before listwise exclusion): Income disparity (low to high earner ratio) 636, Median monthly mortgage cost 605, Median gross rent 546, Median family income 347, Median home value 308, Low life expectancy 93, Families below poverty line 16, Single-parent households with children 16, Below 150% of poverty line 11, Owner-occupied homes 11, Crowded housing (over 1 per room) 11, Lacking complete plumbing 11, Lacking complete kitchen 11, Households with no vehicle 11, No broadband subscription 11, Under 9 years of schooling 10.

#### Suitability

| run | overall KMO | Bartlett chi-square | df | p |
|---|---|---|---|---|
| standardized (primary) | 0.833 | 4,133.1 | 276 | 0 |
| rank (sensitivity) | 0.848 | 4,092.0 | 276 | 0 |

| variable | code | KMO standardized | KMO rank | flag (< 0.5) |
|---|---|---|---|---|
| Low income | `LOWINCPCT` | 0.909 | 0.925 |  |
| Below 150% of poverty line | `poverty_under150` | 0.872 | 0.892 |  |
| Families below poverty line | `poverty_pct_families` | 0.822 | 0.856 |  |
| Median family income | `median_family_income` | 0.904 | 0.921 |  |
| Income disparity (low to high earner ratio) | `income_disparity` | 0.923 | 0.909 |  |
| Unemployed | `UNEMPPCT` | 0.781 | 0.707 |  |
| Less than high school education | `LESSHSPCT` | 0.866 | 0.881 |  |
| Under 9 years of schooling | `no_diploma_under9yrs` | 0.878 | 0.877 |  |
| Median home value | `median_home_value` | 0.704 | 0.699 |  |
| Median gross rent | `median_gross_rent` | 0.910 | 0.905 |  |
| Median monthly mortgage cost | `median_monthly_mortgage` | 0.733 | 0.707 |  |
| Owner-occupied homes | `pct_owner_occupied` | 0.793 | 0.788 |  |
| Crowded housing (over 1 per room) | `pct_crowding_over100` | 0.849 | 0.869 |  |
| Lacking complete plumbing | `pct_no_plumbing` | 0.543 | 0.559 |  |
| Lacking complete kitchen | `pct_no_kitchen` | 0.502 | 0.539 |  |
| Households with no vehicle | `no_vehicle` | 0.826 | 0.857 |  |
| No broadband subscription | `no_broadband` | 0.895 | 0.887 |  |
| People of colour share | `PEOPCOLORPCT` | 0.794 | 0.893 |  |
| Limited English speaking households | `LINGISOPCT` | 0.799 | 0.799 |  |
| Single-parent households with children | `pct_single_parent_children` | 0.835 | 0.840 |  |
| Aged 65 and over | `OVER64PCT` | 0.628 | 0.652 |  |
| Aged under 5 | `UNDER5PCT` | 0.683 | 0.732 |  |
| With a disability | `DISABILITYPCT` | 0.838 | 0.881 |  |
| Low life expectancy | `LIFEEXPPCT` | 0.784 | 0.797 |  |

Per-variable KMO below 0.5: none.

#### Eigenvalues and retention criteria

| component | eigenvalue | % variance | cumulative % | PA 95th pct | > 1 | > PA | rank-run eigenvalue |
|---|---|---|---|---|---|---|---|
| PC1 | 5.877 | 24.5 | 24.5 | 1.469 | yes | yes | 5.981 |
| PC2 | 2.271 | 9.5 | 34.0 | 1.390 | yes | yes | 2.266 |
| PC3 | 1.732 | 7.2 | 41.2 | 1.337 | yes | yes | 1.650 |
| PC4 | 1.420 | 5.9 | 47.1 | 1.289 | yes | yes | 1.478 |
| PC5 | 1.381 | 5.8 | 52.8 | 1.248 | yes | yes | 1.369 |
| PC6 | 1.242 | 5.2 | 58.0 | 1.208 | yes | yes | 1.263 |
| PC7 | 1.060 | 4.4 | 62.4 | 1.176 | yes |  | 0.981 |
| PC8 | 0.976 | 4.1 | 66.5 | 1.143 |  |  | 0.946 |
| PC9 | 0.857 | 3.6 | 70.1 | 1.110 |  |  | 0.823 |
| PC10 | 0.779 | 3.2 | 73.3 | 1.079 |  |  | 0.746 |
| PC11 | 0.716 | 3.0 | 76.3 | 1.052 |  |  | 0.703 |
| PC12 | 0.672 | 2.8 | 79.1 | 1.025 |  |  | 0.668 |
| PC13 | 0.601 | 2.5 | 81.6 | 0.996 |  |  | 0.615 |
| PC14 | 0.587 | 2.4 | 84.0 | 0.971 |  |  | 0.600 |
| PC15 | 0.563 | 2.3 | 86.4 | 0.944 |  |  | 0.584 |
| PC16 | 0.552 | 2.3 | 88.7 | 0.917 |  |  | 0.518 |
| PC17 | 0.470 | 2.0 | 90.6 | 0.891 |  |  | 0.489 |
| PC18 | 0.416 | 1.7 | 92.4 | 0.865 |  |  | 0.451 |
| PC19 | 0.372 | 1.6 | 93.9 | 0.838 |  |  | 0.393 |
| PC20 | 0.349 | 1.5 | 95.4 | 0.811 |  |  | 0.353 |
| PC21 | 0.337 | 1.4 | 96.8 | 0.783 |  |  | 0.320 |
| PC22 | 0.282 | 1.2 | 98.0 | 0.754 |  |  | 0.283 |
| PC23 | 0.258 | 1.1 | 99.0 | 0.724 |  |  | 0.277 |
| PC24 | 0.231 | 1.0 | 100.0 | 0.689 |  |  | 0.244 |

| criterion | standardized | rank |
|---|---|---|
| Eigenvalue > 1 (Kaiser) | 7 | 6 |
| Scree plot (elbow, read visually) | 3 (sharp break after 1; curve flattens after 3) | same plot |
| Parallel analysis (Horn, 95th pct, 1000 draws) | 6 | 6 |

Scree plot: `output/pca/scree_bg24.png`.

**Proposed number of components: 6** (pending your confirmation). Parallel analysis gives 6 in both the standardized and rank runs; eigenvalue above 1 gives 7 in the standardized run (PC7 = 1.06, below the parallel-analysis line of 1.18) and is known to over-extract. All six components replicate under ranks (congruence 0.95 or above for five, 0.949 for the sixth). The scree reads 3, but 3 components leave 16 of 24 variables with communality below 0.5. **Caveat:** n = 518 complete cases.

#### Loadings, retained components (k = 6)

PC = unrotated, RC = varimax-rotated (Kaiser-normalised). Bold: |loading| >= 0.5. Each component is oriented so its largest loading is positive; the sign of a whole component is arbitrary.

| variable | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 | RC1 | RC2 | RC3 | RC4 | RC5 | RC6 | communality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Low income | +0.79 | -0.13 | +0.04 | -0.03 | +0.05 | -0.00 | **+0.58** | +0.43 | -0.24 | -0.19 | +0.16 | -0.07 | 0.65 |
| Below 150% of poverty line | +0.77 | -0.15 | +0.05 | -0.15 | +0.22 | -0.17 | **+0.69** | +0.32 | -0.16 | -0.25 | +0.02 | -0.22 | 0.72 |
| Families below poverty line | +0.52 | -0.36 | +0.07 | -0.15 | +0.26 | -0.28 | **+0.54** | +0.15 | -0.01 | -0.45 | -0.02 | -0.24 | 0.57 |
| Median family income | -0.74 | +0.11 | +0.32 | +0.15 | +0.03 | +0.08 | **-0.53** | -0.24 | **+0.55** | +0.23 | +0.00 | +0.06 | 0.69 |
| Income disparity (low to high earner ratio) | +0.52 | -0.09 | +0.33 | -0.25 | -0.02 | +0.01 | +0.29 | **+0.53** | +0.00 | -0.12 | +0.02 | -0.26 | 0.45 **low** |
| Unemployed | +0.24 | -0.26 | +0.04 | +0.13 | +0.11 | +0.44 | +0.08 | +0.12 | -0.07 | -0.09 | **+0.56** | -0.08 | 0.35 **low** |
| Less than high school education | +0.72 | +0.25 | -0.09 | +0.21 | +0.28 | -0.07 | **+0.78** | +0.16 | -0.18 | +0.16 | +0.11 | +0.13 | 0.72 |
| Under 9 years of schooling | +0.64 | +0.19 | +0.07 | +0.24 | +0.33 | -0.10 | **+0.75** | +0.17 | +0.01 | +0.11 | +0.13 | +0.10 | 0.62 |
| Median home value | -0.44 | -0.06 | +0.61 | +0.24 | +0.30 | -0.20 | -0.08 | -0.12 | **+0.86** | -0.01 | -0.01 | +0.00 | 0.76 |
| Median gross rent | -0.61 | -0.04 | -0.25 | -0.03 | +0.19 | -0.16 | -0.28 | **-0.60** | +0.12 | -0.01 | -0.18 | -0.06 | 0.49 **low** |
| Median monthly mortgage cost | -0.45 | -0.08 | +0.64 | +0.20 | +0.22 | -0.27 | -0.12 | -0.07 | **+0.87** | -0.06 | -0.09 | +0.01 | 0.78 |
| Owner-occupied homes | -0.50 | +0.14 | -0.22 | +0.18 | +0.52 | +0.17 | -0.07 | **-0.69** | +0.19 | +0.30 | +0.20 | -0.07 | 0.65 |
| Crowded housing (over 1 per room) | +0.36 | -0.08 | +0.00 | +0.10 | -0.04 | -0.35 | +0.36 | +0.15 | -0.03 | -0.25 | -0.17 | +0.17 | 0.27 **low** |
| Lacking complete plumbing | +0.07 | +0.10 | -0.12 | +0.65 | -0.25 | -0.07 | +0.07 | -0.01 | -0.02 | +0.02 | +0.11 | **+0.71** | 0.52 |
| Lacking complete kitchen | +0.03 | +0.13 | -0.05 | +0.56 | -0.41 | -0.31 | +0.01 | +0.08 | +0.04 | -0.05 | -0.16 | **+0.75** | 0.60 |
| Households with no vehicle | +0.51 | +0.10 | +0.48 | -0.05 | -0.38 | +0.17 | +0.08 | **+0.81** | +0.01 | +0.06 | +0.09 | +0.04 | 0.68 |
| No broadband subscription | +0.53 | +0.16 | +0.28 | +0.18 | -0.17 | +0.36 | +0.21 | **+0.58** | -0.07 | +0.21 | +0.35 | +0.14 | 0.57 |
| People of colour share | +0.47 | +0.05 | -0.45 | +0.24 | +0.21 | -0.07 | **+0.56** | -0.17 | -0.37 | -0.02 | +0.12 | +0.20 | 0.53 |
| Limited English speaking households | +0.50 | +0.53 | -0.00 | -0.13 | -0.16 | -0.35 | +0.44 | +0.37 | -0.21 | +0.29 | -0.48 | +0.12 | 0.70 |
| Single-parent households with children | +0.28 | -0.57 | -0.04 | +0.05 | -0.08 | -0.06 | +0.12 | +0.12 | -0.11 | **-0.58** | +0.18 | +0.00 | 0.41 **low** |
| Aged 65 and over | +0.14 | +0.73 | +0.16 | -0.16 | +0.15 | +0.16 | +0.20 | +0.19 | +0.01 | **+0.73** | -0.12 | -0.14 | 0.65 |
| Aged under 5 | +0.11 | -0.60 | +0.13 | +0.01 | -0.00 | -0.14 | +0.04 | +0.08 | +0.12 | **-0.61** | +0.11 | -0.07 | 0.41 **low** |
| With a disability | +0.42 | +0.36 | +0.16 | +0.11 | +0.30 | +0.12 | +0.49 | +0.19 | +0.06 | +0.37 | +0.16 | -0.03 | 0.44 **low** |
| Low life expectancy | +0.38 | -0.45 | +0.02 | +0.38 | +0.11 | +0.42 | +0.20 | +0.12 | -0.06 | -0.28 | **+0.72** | +0.10 | 0.67 |

Variance carried after rotation: RC1 15.7%, RC2 11.9%, RC3 9.1%, RC4 9.0%, RC5 6.2%, RC6 6.0% (total 58.0%, same as the first 6 unrotated components).

#### Components: salient variables and suggested names

Names are **suggestions only**, based on the variables loading at |0.5| or more.

- **RC1**, suggested name: *Low income, low education and people of colour*. Loading at |0.5| or more: Less than high school education (+0.78); Under 9 years of schooling (+0.75); Below 150% of poverty line (+0.69); Low income (+0.58); People of colour share (+0.56); Families below poverty line (+0.54); Median family income (-0.53).
- **RC2**, suggested name: *Renters without a vehicle or broadband*. Loading at |0.5| or more: Households with no vehicle (+0.81); Owner-occupied homes (-0.69); Median gross rent (-0.60); No broadband subscription (+0.58); Income disparity (low to high earner ratio) (+0.53).
- **RC3**, suggested name: *Housing costs and family income*. Loading at |0.5| or more: Median monthly mortgage cost (+0.87); Median home value (+0.86); Median family income (+0.55).
- **RC4**, suggested name: *Older residents versus young families*. Loading at |0.5| or more: Aged 65 and over (+0.73); Aged under 5 (-0.61); Single-parent households with children (-0.58).
- **RC5**, suggested name: *Low life expectancy and unemployment*. Loading at |0.5| or more: Low life expectancy (+0.72); Unemployed (+0.56).
- **RC6**, suggested name: *Incomplete plumbing and kitchens*. Loading at |0.5| or more: Lacking complete kitchen (+0.75); Lacking complete plumbing (+0.71).

Variables with no loading at |0.5| or more on any retained component: Crowded housing (over 1 per room), Limited English speaking households, With a disability.

**Communality below 0.5** (less than half the variable's variance explained by the 6 retained components): Income disparity (low to high earner ratio) (0.45), Unemployed (0.35), Median gross rent (0.49), Crowded housing (over 1 per room) (0.27), Single-parent households with children (0.41), Aged under 5 (0.41), With a disability (0.44).

#### Sensitivity: rank-transformed PCA

Same complete cases, each variable replaced by its average rank then standardized; same k = 6, same rotation. Components matched by maximum |Tucker congruence|.

| primary component | matched rank component | congruence (phi) | correlation of scores | reading |
|---|---|---|---|---|
| RC1 | RC1 | +0.996 | +0.958 | equal (>= 0.95) |
| RC2 | RC2 | +0.988 | +0.949 | equal (>= 0.95) |
| RC3 | RC4 | +0.984 | +0.933 | equal (>= 0.95) |
| RC4 | RC3 | +0.996 | +0.963 | equal (>= 0.95) |
| RC5 | RC6 | +0.949 | +0.913 | fair similarity (0.85 to 0.95) |
| RC6 | RC5 | +0.975 | +0.823 | equal (>= 0.95) |

**Verdict: broadly similar but not identical.** Unrotated congruence, PC1 to PC6: +0.998, +0.995, +0.836, +0.500, -0.529, +0.938. Criteria on the rank run: eigenvalue > 1 gives 6, parallel analysis gives 6 (standardized run: 7 and 6).

Changes in the salient (|0.5|) variable set under ranks: RC2: loses Income disparity (low to high earner ratio); RC3: loses Median family income.

### Block group, version B: 21 variables

### Sample

- Variables: **21**. Complete cases: **n = 1,247** of 1,843 units (596 excluded for a missing value in at least one variable; nothing imputed).
- Units missing each variable (before listwise exclusion): Median family income 347, Median home value 308, Low life expectancy 93, Families below poverty line 16, Single-parent households with children 16, Below 150% of poverty line 11, Owner-occupied homes 11, Crowded housing (over 1 per room) 11, Lacking complete plumbing 11, Lacking complete kitchen 11, Households with no vehicle 11, No broadband subscription 11, Under 9 years of schooling 10.

#### Suitability

| run | overall KMO | Bartlett chi-square | df | p |
|---|---|---|---|---|
| standardized (primary) | 0.871 | 8,832.6 | 210 | 0 |
| rank (sensitivity) | 0.890 | 9,022.8 | 210 | 0 |

| variable | code | KMO standardized | KMO rank | flag (< 0.5) |
|---|---|---|---|---|
| Low income | `LOWINCPCT` | 0.936 | 0.947 |  |
| Below 150% of poverty line | `poverty_under150` | 0.883 | 0.901 |  |
| Families below poverty line | `poverty_pct_families` | 0.858 | 0.888 |  |
| Median family income | `median_family_income` | 0.915 | 0.927 |  |
| Unemployed | `UNEMPPCT` | 0.815 | 0.798 |  |
| Less than high school education | `LESSHSPCT` | 0.888 | 0.890 |  |
| Under 9 years of schooling | `no_diploma_under9yrs` | 0.875 | 0.887 |  |
| Median home value | `median_home_value` | 0.885 | 0.935 |  |
| Owner-occupied homes | `pct_owner_occupied` | 0.825 | 0.851 |  |
| Crowded housing (over 1 per room) | `pct_crowding_over100` | 0.924 | 0.932 |  |
| Lacking complete plumbing | `pct_no_plumbing` | 0.514 | 0.531 |  |
| Lacking complete kitchen | `pct_no_kitchen` | 0.662 | 0.677 |  |
| Households with no vehicle | `no_vehicle` | 0.842 | 0.864 |  |
| No broadband subscription | `no_broadband` | 0.920 | 0.912 |  |
| People of colour share | `PEOPCOLORPCT` | 0.867 | 0.920 |  |
| Limited English speaking households | `LINGISOPCT` | 0.856 | 0.892 |  |
| Single-parent households with children | `pct_single_parent_children` | 0.903 | 0.902 |  |
| Aged 65 and over | `OVER64PCT` | 0.562 | 0.576 |  |
| Aged under 5 | `UNDER5PCT` | 0.576 | 0.666 |  |
| With a disability | `DISABILITYPCT` | 0.896 | 0.900 |  |
| Low life expectancy | `LIFEEXPPCT` | 0.837 | 0.848 |  |

Per-variable KMO below 0.5: none.

#### Eigenvalues and retention criteria

| component | eigenvalue | % variance | cumulative % | PA 95th pct | > 1 | > PA | rank-run eigenvalue |
|---|---|---|---|---|---|---|---|
| PC1 | 5.961 | 28.4 | 28.4 | 1.273 | yes | yes | 6.228 |
| PC2 | 1.968 | 9.4 | 37.8 | 1.224 | yes | yes | 1.902 |
| PC3 | 1.412 | 6.7 | 44.5 | 1.192 | yes | yes | 1.346 |
| PC4 | 1.239 | 5.9 | 50.4 | 1.160 | yes | yes | 1.311 |
| PC5 | 1.136 | 5.4 | 55.8 | 1.137 | yes |  | 1.090 |
| PC6 | 1.014 | 4.8 | 60.6 | 1.112 | yes |  | 0.985 |
| PC7 | 0.970 | 4.6 | 65.2 | 1.091 |  |  | 0.900 |
| PC8 | 0.869 | 4.1 | 69.4 | 1.070 |  |  | 0.873 |
| PC9 | 0.808 | 3.8 | 73.2 | 1.051 |  |  | 0.784 |
| PC10 | 0.761 | 3.6 | 76.8 | 1.030 |  |  | 0.718 |
| PC11 | 0.738 | 3.5 | 80.4 | 1.010 |  |  | 0.673 |
| PC12 | 0.624 | 3.0 | 83.3 | 0.992 |  |  | 0.638 |
| PC13 | 0.570 | 2.7 | 86.0 | 0.974 |  |  | 0.572 |
| PC14 | 0.508 | 2.4 | 88.5 | 0.956 |  |  | 0.513 |
| PC15 | 0.482 | 2.3 | 90.8 | 0.937 |  |  | 0.477 |
| PC16 | 0.435 | 2.1 | 92.8 | 0.919 |  |  | 0.452 |
| PC17 | 0.375 | 1.8 | 94.6 | 0.899 |  |  | 0.401 |
| PC18 | 0.319 | 1.5 | 96.1 | 0.880 |  |  | 0.338 |
| PC19 | 0.295 | 1.4 | 97.5 | 0.860 |  |  | 0.286 |
| PC20 | 0.281 | 1.3 | 98.9 | 0.838 |  |  | 0.262 |
| PC21 | 0.235 | 1.1 | 100.0 | 0.812 |  |  | 0.249 |

| criterion | standardized | rank |
|---|---|---|
| Eigenvalue > 1 (Kaiser) | 6 | 5 |
| Scree plot (elbow, read visually) | 3 (sharp break after 1; curve flattens after 3) | same plot |
| Parallel analysis (Horn, 95th pct, 1000 draws) | 4 | 4 |

Scree plot: `output/pca/scree_bg21.png`.

**Proposed number of components: 4** (pending your confirmation). Parallel analysis gives 4 in both the standardized and rank runs. PC5 (1.136) sits on the parallel-analysis line (1.137); re-running the simulation with five other seeds put the line between 1.135 and 1.137, so PC5 is indistinguishable from random-data noise at the 95th percentile. Eigenvalue above 1 gives 6 and is known to over-extract; the scree reads 3, but 3 components replicate poorly under ranks (congruence as low as 0.24). **Alternative: k = 5**, which adds a plumbing and kitchen component (the counterpart of RC6 in the 24-variable version) but replicates less well under ranks (lowest congruence 0.84 against 0.88 at k = 4).

#### Loadings, retained components (k = 4)

PC = unrotated, RC = varimax-rotated (Kaiser-normalised). Bold: |loading| >= 0.5. Each component is oriented so its largest loading is positive; the sign of a whole component is arbitrary.

| variable | PC1 | PC2 | PC3 | PC4 | RC1 | RC2 | RC3 | RC4 | communality |
|---|---|---|---|---|---|---|---|---|---|
| Low income | +0.82 | -0.06 | -0.08 | -0.07 | **+0.58** | **+0.56** | -0.18 | -0.10 | 0.69 |
| Below 150% of poverty line | +0.79 | -0.12 | -0.17 | -0.07 | +0.49 | **+0.60** | -0.24 | -0.13 | 0.67 |
| Families below poverty line | +0.60 | -0.27 | -0.20 | -0.06 | +0.32 | +0.48 | -0.35 | -0.17 | 0.48 **low** |
| Median family income | -0.78 | +0.11 | -0.23 | -0.01 | **-0.72** | -0.31 | +0.23 | -0.04 | 0.67 |
| Unemployed | +0.21 | -0.22 | -0.32 | -0.33 | -0.00 | +0.28 | -0.18 | -0.43 | 0.30 **low** |
| Less than high school education | +0.74 | +0.25 | +0.19 | -0.14 | **+0.72** | +0.36 | +0.16 | -0.03 | 0.67 |
| Under 9 years of schooling | +0.62 | +0.23 | +0.08 | -0.12 | **+0.56** | +0.36 | +0.15 | -0.04 | 0.46 **low** |
| Median home value | -0.60 | +0.06 | -0.44 | -0.01 | **-0.72** | -0.05 | +0.14 | -0.09 | 0.55 |
| Owner-occupied homes | -0.61 | +0.16 | +0.26 | -0.39 | -0.22 | **-0.60** | +0.36 | -0.27 | 0.61 |
| Crowded housing (over 1 per room) | +0.41 | -0.20 | +0.07 | +0.23 | +0.30 | +0.20 | -0.31 | +0.18 | 0.26 **low** |
| Lacking complete plumbing | +0.07 | +0.08 | +0.06 | +0.35 | +0.04 | +0.06 | -0.02 | +0.37 | 0.14 **low** |
| Lacking complete kitchen | +0.10 | +0.16 | +0.06 | +0.65 | +0.01 | +0.13 | -0.02 | **+0.67** | 0.46 **low** |
| Households with no vehicle | +0.49 | +0.17 | -0.54 | +0.22 | +0.00 | **+0.77** | +0.00 | +0.13 | 0.62 |
| No broadband subscription | +0.55 | +0.25 | -0.34 | +0.01 | +0.21 | **+0.65** | +0.13 | -0.00 | 0.48 **low** |
| People of colour share | +0.57 | -0.01 | +0.59 | -0.08 | **+0.81** | -0.09 | -0.06 | +0.05 | 0.68 |
| Limited English speaking households | +0.62 | +0.40 | +0.06 | +0.23 | +0.49 | +0.45 | +0.22 | +0.33 | 0.60 |
| Single-parent households with children | +0.40 | -0.50 | +0.03 | +0.07 | +0.28 | +0.15 | **-0.55** | -0.05 | 0.41 **low** |
| Aged 65 and over | +0.02 | +0.76 | -0.19 | -0.20 | -0.02 | +0.26 | **+0.76** | -0.05 | 0.65 |
| Aged under 5 | +0.03 | -0.48 | -0.25 | -0.03 | -0.16 | +0.12 | -0.46 | -0.20 | 0.30 **low** |
| With a disability | +0.46 | +0.43 | -0.07 | -0.31 | +0.38 | +0.38 | +0.41 | -0.20 | 0.49 **low** |
| Low life expectancy | +0.43 | -0.34 | -0.04 | -0.29 | +0.33 | +0.20 | -0.32 | -0.37 | 0.39 **low** |

Variance carried after rotation: RC1 19.0%, RC2 15.6%, RC3 9.7%, RC4 6.1% (total 50.4%, same as the first 4 unrotated components).

#### Components: salient variables and suggested names

Names are **suggestions only**, based on the variables loading at |0.5| or more.

- **RC1**, suggested name: *Low income, low education and people of colour*. Loading at |0.5| or more: People of colour share (+0.81); Median family income (-0.72); Median home value (-0.72); Less than high school education (+0.72); Low income (+0.58); Under 9 years of schooling (+0.56).
- **RC2**, suggested name: *Poverty, renting and lack of vehicle or broadband*. Loading at |0.5| or more: Households with no vehicle (+0.77); No broadband subscription (+0.65); Owner-occupied homes (-0.60); Below 150% of poverty line (+0.60); Low income (+0.56).
- **RC3**, suggested name: *Older residents versus single-parent families*. Loading at |0.5| or more: Aged 65 and over (+0.76); Single-parent households with children (-0.55).
- **RC4**, suggested name: *Incomplete kitchens*. Loading at |0.5| or more: Lacking complete kitchen (+0.67).

Variables with no loading at |0.5| or more on any retained component: Families below poverty line, Unemployed, Crowded housing (over 1 per room), Lacking complete plumbing, Limited English speaking households, Aged under 5, With a disability, Low life expectancy.

**Communality below 0.5** (less than half the variable's variance explained by the 4 retained components): Families below poverty line (0.48), Unemployed (0.30), Under 9 years of schooling (0.46), Crowded housing (over 1 per room) (0.26), Lacking complete plumbing (0.14), Lacking complete kitchen (0.46), No broadband subscription (0.48), Single-parent households with children (0.41), Aged under 5 (0.30), With a disability (0.49), Low life expectancy (0.39).

#### Sensitivity: rank-transformed PCA

Same complete cases, each variable replaced by its average rank then standardized; same k = 4, same rotation. Components matched by maximum |Tucker congruence|.

| primary component | matched rank component | congruence (phi) | correlation of scores | reading |
|---|---|---|---|---|
| RC1 | RC1 | +0.970 | +0.889 | equal (>= 0.95) |
| RC2 | RC2 | -0.934 | +0.817 | fair similarity (0.85 to 0.95) |
| RC3 | RC3 | +0.985 | +0.932 | equal (>= 0.95) |
| RC4 | RC4 | +0.880 | +0.741 | fair similarity (0.85 to 0.95) |

**Verdict: broadly similar but not identical.** Unrotated congruence, PC1 to PC4: -0.998, +0.987, -0.039, +0.014. Criteria on the rank run: eigenvalue > 1 gives 5, parallel analysis gives 4 (standardized run: 6 and 4).

Changes in the salient (|0.5|) variable set under ranks: RC1: gains With a disability, Below 150% of poverty line; loses Median home value; RC2: gains Limited English speaking households, Median family income; RC3: gains Aged under 5; RC4: gains Lacking complete plumbing.

### Version A against version B

Rotated components matched by |congruence| on the 21 shared variables:

| 24-variable component | 21-variable component | congruence |
|---|---|---|
| RC1 | RC1 | +0.891 |
| RC2 | RC2 | +0.944 |
| RC4 | RC3 | +0.978 |
| RC6 | RC4 | +0.720 |

The versions retain different numbers of components (6 and 4), so some components are unmatched.

### Relevance to earlier findings (block group)

Block group has no multi-unit housing, no internet-access or second no-vehicle measure. The access variables are households with no vehicle and no broadband subscription, and the minority-composition measure is people of colour share (same definition as minority share).

**Block group, all 24 variables**

| variable | code | RC1 | RC2 | RC3 | RC4 | RC5 | RC6 | highest loading on | communality |
|---|---|---|---|---|---|---|---|---|---|
| Households with no vehicle | `no_vehicle` | +0.08 | **+0.81** | +0.01 | +0.06 | +0.09 | +0.04 | RC2 | 0.68 |
| No broadband subscription | `no_broadband` | +0.21 | **+0.58** | -0.07 | +0.21 | +0.35 | +0.14 | RC2 | 0.57 |
| People of colour share | `PEOPCOLORPCT` | **+0.56** | -0.17 | -0.37 | -0.02 | +0.12 | +0.20 | RC1 | 0.53 |

Spearman rho among these variables on the PCA sample: Households with no vehicle vs No broadband subscription +0.459; Households with no vehicle vs People of colour share +0.103; No broadband subscription vs People of colour share +0.224.

People of colour share loads highest on RC1 (Low income, low education and people of colour). Households with no vehicle loads highest on RC2 (Renters without a vehicle or broadband); No broadband subscription loads highest on RC2 (Renters without a vehicle or broadband). **The PCA separates minority composition from every access variable.** 

**Block group, 21 variables (3 over 20% missing excluded)**

| variable | code | RC1 | RC2 | RC3 | RC4 | highest loading on | communality |
|---|---|---|---|---|---|---|---|
| Households with no vehicle | `no_vehicle` | +0.00 | **+0.77** | +0.00 | +0.13 | RC2 | 0.62 |
| No broadband subscription | `no_broadband` | +0.21 | **+0.65** | +0.13 | -0.00 | RC2 | 0.48 |
| People of colour share | `PEOPCOLORPCT` | **+0.81** | -0.09 | -0.06 | +0.05 | RC1 | 0.68 |

Spearman rho among these variables on the PCA sample: Households with no vehicle vs No broadband subscription +0.439; Households with no vehicle vs People of colour share +0.137; No broadband subscription vs People of colour share +0.241.

People of colour share loads highest on RC1 (Low income, low education and people of colour). Households with no vehicle loads highest on RC2 (Poverty, renting and lack of vehicle or broadband); No broadband subscription loads highest on RC2 (Poverty, renting and lack of vehicle or broadband). **The PCA separates minority composition from every access variable.** 

---

## Files

- `output/pca/scree_<run>.png`, `loadings_varimax_<run>.png`, `loadings_unrotated_<run>.png` (plain-language labels)
- `output/pca/eigenvalues_<run>_<prim|rank>.csv`, `loadings_unrotated_<run>_<prim|rank>.csv`, `loadings_varimax_<run>_<prim|rank>.csv` (with communality), `kmo_<run>.csv`
- `output/pca/pca_scores_tract.csv`: GEOID, `in_sample`, unrotated `PC*`, varimax `RC*`, rank-run varimax `rankRC*` (unit variance; blank outside the sample)
- `output/pca/pca_scores_blockgroup.csv`: same, prefixed `bg24_` and `bg21_` for the two versions
- Run ids: `tract`, `bg24`, `bg21`
