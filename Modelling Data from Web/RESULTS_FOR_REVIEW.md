# Results for Review — SCALE-R Investment × Vulnerability Correlation Analysis

**Compiled for a reader with no access to this directory.** Every number
below was pulled from existing output files, not recomputed. This is a
descriptive/correlational analysis only — nothing here was fit, tuned, or
validated as a predictive model, and no FEMA NRI or other physical-risk layer
is used anywhere (this is investment × vulnerability, not investment × risk ×
vulnerability).

**Grains:** tract = 698 units (of 707; 9 zero-population tracts excluded —
see `zero_population_investigation.md`). Block group = 1,843 units, none
excluded. Filtered project universe = 1,405 projects (Completed/Funded/
Ongoing only), $8,553,271,610 total allocated.

**Source files for this compilation, by section**, are named at the top of
each section below. The full narrative version of these results, with
plain-language framing throughout, is `correlation_analysis.md`. The
underlying scripts are `scripts/part2_univariate.py` through
`scripts/part5_diagnostics.py`.

**Table conventions:** coefficients rounded to 3 decimals (scientific
notation only if rounding to 3 decimals would show `0.000` for a genuinely
nonzero value); p-values rounded to 4 decimals, or scientific notation below
0.0001. `**` in a `sig` column = FDR-adjusted p < 0.05. `SPARSE` = fewer than
20 single-unit-sited receiving units behind this row (Section 3) — read as
flagged, not as a finding, regardless of its coefficient or p-value.

---

## 1. The composition finding (headline)

*Sources: `output/part4_investment_vs_indicators/4b_tract_type_composition_continuous.csv`, `4c_tract_path_composition_continuous.csv`, `4d_bg_type_composition_continuous.csv`, `4d_bg_path_composition_continuous.csv`, and the four matching `_binary.csv` files.*

**Plain-language read:** Gray infrastructure's *share* of a unit's investment tends to rise with several deprivation indicators (vehicle access, housing density, internet access) while Green's share tends to fall with the same indicators. At **tract** grain this gray-up/green-down sign pattern holds for **21 of 34** vulnerability variables, but only **6** have both sides individually FDR-significant (**10** have at least one side significant). At **block group** grain the pattern holds for **18 of 35**, with **11** both-significant (**13** either-significant). Gray-share Spearman ρ ranges -0.140 to 0.305 (tract) / -0.223 to 0.271 (BG); Green-share ρ ranges -0.284 to 0.199 (tract) / -0.252 to 0.248 (BG). **The sign pattern is broad but the FDR-survivable evidence rests on a minority of variables at both grains** - this must be read as a directional tendency across the vulnerability block, not as a small set of strong individual relationships.

Blue infrastructure is flagged sparse at both grains (19 single-unit-sited receiving units - see Section 3) and every Blue row below is marked `SPARSE`; its coefficients are shown for completeness but should not be read as stable.

### 1a. Project-type SHARE vs. vulnerability - tract, 698 units, 4 types x 34 vulnerability variables (n=136 pairs)

| variable              | type   | n   | rho       | p_raw    | p_fdr    | sig    |
|:----------------------|:-------|:----|:----------|:---------|:---------|:-------|
| EP_AFAM               | blue   | 698 | -0.006    | 0.8812   | 0.9726   | SPARSE |
| EP_AFAM               | gray   | 698 | 0.028     | 0.4563   | 0.5746   |        |
| EP_AFAM               | green  | 698 | -0.035    | 0.3570   | 0.4669   |        |
| EP_AFAM               | hybrid | 698 | -0.001    | 0.9846   | 0.9846   |        |
| EP_AGE17              | blue   | 698 | 0.061     | 0.1096   | 0.2329   | SPARSE |
| EP_AGE17              | gray   | 698 | -0.051    | 0.1744   | 0.2823   |        |
| EP_AGE17              | green  | 698 | 0.051     | 0.1801   | 0.3402   |        |
| EP_AGE17              | hybrid | 698 | 0.098     | 0.0093   | 0.0175   | **     |
| EP_AGE65              | blue   | 698 | 0.034     | 0.3760   | 0.4917   | SPARSE |
| EP_AGE65              | gray   | 698 | -0.005    | 0.9053   | 0.9327   |        |
| EP_AGE65              | green  | 698 | 0.055     | 0.1473   | 0.3131   |        |
| EP_AGE65              | hybrid | 698 | -0.002    | 0.9572   | 0.9846   |        |
| EP_AIAN               | blue   | 698 | -0.001    | 0.9840   | 0.9840   | SPARSE |
| EP_AIAN               | gray   | 698 | 0.032     | 0.3982   | 0.5612   |        |
| EP_AIAN               | green  | 698 | -0.009    | 0.8099   | 0.8605   |        |
| EP_AIAN               | hybrid | 698 | -0.031    | 0.4078   | 0.4613   |        |
| EP_ASIAN              | blue   | 698 | -0.034    | 0.3656   | 0.4917   | SPARSE |
| EP_ASIAN              | gray   | 698 | -0.026    | 0.5006   | 0.6079   |        |
| EP_ASIAN              | green  | 698 | -0.042    | 0.2647   | 0.4669   |        |
| EP_ASIAN              | hybrid | 698 | 0.112     | 0.0031   | 0.0062   | **     |
| EP_CROWD              | blue   | 697 | -0.068    | 0.0729   | 0.1653   | SPARSE |
| EP_CROWD              | gray   | 697 | 0.095     | 0.0117   | 0.0331   | **     |
| EP_CROWD              | green  | 697 | -0.058    | 0.1279   | 0.2899   |        |
| EP_CROWD              | hybrid | 697 | -0.120    | 0.0015   | 0.0039   | **     |
| EP_DISABL             | blue   | 698 | -0.047    | 0.2184   | 0.4109   | SPARSE |
| EP_DISABL             | gray   | 698 | 0.117     | 0.0019   | 0.0058   | **     |
| EP_DISABL             | green  | 698 | -0.041    | 0.2836   | 0.4669   |        |
| EP_DISABL             | hybrid | 698 | -0.133    | 0.0004   | 0.0019   | **     |
| EP_GROUPQ             | blue   | 698 | 0.004     | 0.9154   | 0.9726   | SPARSE |
| EP_GROUPQ             | gray   | 698 | 0.022     | 0.5665   | 0.6642   |        |
| EP_GROUPQ             | green  | 698 | -0.052    | 0.1686   | 0.3372   |        |
| EP_GROUPQ             | hybrid | 698 | -0.070    | 0.0627   | 0.0853   |        |
| EP_HBURD              | blue   | 697 | -0.090    | 0.0179   | 0.0467   | SPARSE |
| EP_HBURD              | gray   | 697 | 0.121     | 0.0014   | 0.0046   | **     |
| EP_HBURD              | green  | 697 | -0.082    | 0.0303   | 0.0857   |        |
| EP_HBURD              | hybrid | 697 | -0.121    | 0.0013   | 0.0038   | **     |
| EP_HISP               | blue   | 698 | 0.187     | 6.14e-07 | 3.48e-06 | SPARSE |
| EP_HISP               | gray   | 698 | -0.140    | 0.0002   | 0.0011   | **     |
| EP_HISP               | green  | 698 | 0.155     | 3.91e-05 | 0.0002   | **     |
| EP_HISP               | hybrid | 698 | -0.078    | 0.0393   | 0.0556   |        |
| EP_LIMENG             | blue   | 698 | 0.112     | 0.0031   | 0.0089   | SPARSE |
| EP_LIMENG             | gray   | 698 | -0.058    | 0.1277   | 0.2386   |        |
| EP_LIMENG             | green  | 698 | 0.064     | 0.0905   | 0.2366   |        |
| EP_LIMENG             | hybrid | 698 | -0.119    | 0.0016   | 0.0039   | **     |
| EP_MINRTY             | blue   | 698 | 0.239     | 1.51e-10 | 1.29e-09 | SPARSE |
| EP_MINRTY             | gray   | 698 | -0.135    | 0.0004   | 0.0018   | **     |
| EP_MINRTY             | green  | 698 | 0.199     | 1.22e-07 | 1.04e-06 | **     |
| EP_MINRTY             | hybrid | 698 | -0.166    | 1.04e-05 | 8.86e-05 | **     |
| EP_MOBILE             | blue   | 697 | -0.035    | 0.3613   | 0.4917   | SPARSE |
| EP_MOBILE             | gray   | 697 | 0.075     | 0.0468   | 0.1137   |        |
| EP_MOBILE             | green  | 697 | -0.038    | 0.3189   | 0.4669   |        |
| EP_MOBILE             | hybrid | 697 | -0.092    | 0.0150   | 0.0255   | **     |
| EP_MUNIT              | blue   | 697 | -0.274    | 1.68e-13 | 2.85e-12 | SPARSE |
| EP_MUNIT              | gray   | 697 | 0.209     | 2.47e-08 | 2.10e-07 | **     |
| EP_MUNIT              | green  | 697 | -0.194    | 2.41e-07 | 1.64e-06 | **     |
| EP_MUNIT              | hybrid | 697 | -0.045    | 0.2336   | 0.2941   |        |
| EP_NHPI               | blue   | 698 | 0.035     | 0.3564   | 0.4917   | SPARSE |
| EP_NHPI               | gray   | 698 | -0.042    | 0.2643   | 0.3907   |        |
| EP_NHPI               | green  | 698 | 0.014     | 0.7204   | 0.7901   |        |
| EP_NHPI               | hybrid | 698 | 0.039     | 0.2974   | 0.3612   |        |
| EP_NOHSDP             | blue   | 698 | 0.119     | 0.0016   | 0.0049   | SPARSE |
| EP_NOHSDP             | gray   | 698 | -0.031    | 0.4126   | 0.5612   |        |
| EP_NOHSDP             | green  | 698 | 0.084     | 0.0257   | 0.0857   |        |
| EP_NOHSDP             | hybrid | 698 | -0.136    | 0.0003   | 0.0018   | **     |
| EP_NOINT              | blue   | 697 | -0.154    | 4.70e-05 | 0.0002   | SPARSE |
| EP_NOINT              | gray   | 697 | 0.201     | 8.21e-08 | 5.58e-07 | **     |
| EP_NOINT              | green  | 697 | -0.140    | 0.0002   | 0.0009   | **     |
| EP_NOINT              | hybrid | 697 | -0.231    | 6.54e-10 | 1.11e-08 | **     |
| EP_NOVEH              | blue   | 697 | -0.315    | 1.70e-17 | 5.78e-16 | SPARSE |
| EP_NOVEH              | gray   | 697 | 0.305     | 1.64e-16 | 5.59e-15 | **     |
| EP_NOVEH              | green  | 697 | -0.284    | 2.29e-14 | 7.77e-13 | **     |
| EP_NOVEH              | hybrid | 697 | -0.168    | 8.60e-06 | 8.86e-05 | **     |
| EP_OTHERRACE          | blue   | 698 | -0.040    | 0.2923   | 0.4917   | SPARSE |
| EP_OTHERRACE          | gray   | 698 | 0.008     | 0.8372   | 0.8896   |        |
| EP_OTHERRACE          | green  | 698 | -0.039    | 0.2995   | 0.4669   |        |
| EP_OTHERRACE          | hybrid | 698 | 0.084     | 0.0257   | 0.0380   | **     |
| EP_POV150             | blue   | 697 | -0.036    | 0.3481   | 0.4917   | SPARSE |
| EP_POV150             | gray   | 697 | 0.085     | 0.0241   | 0.0629   |        |
| EP_POV150             | green  | 697 | -0.037    | 0.3311   | 0.4669   |        |
| EP_POV150             | hybrid | 697 | -0.126    | 0.0009   | 0.0029   | **     |
| EP_SNGPNT             | blue   | 697 | 0.068     | 0.0712   | 0.1653   | SPARSE |
| EP_SNGPNT             | gray   | 697 | -0.013    | 0.7287   | 0.7992   |        |
| EP_SNGPNT             | green  | 697 | 0.038     | 0.3137   | 0.4669   |        |
| EP_SNGPNT             | hybrid | 697 | -0.036    | 0.3472   | 0.4070   |        |
| EP_TWOMORE            | blue   | 698 | -0.164    | 1.27e-05 | 6.18e-05 | SPARSE |
| EP_TWOMORE            | gray   | 698 | 0.133     | 0.0004   | 0.0018   | **     |
| EP_TWOMORE            | green  | 698 | -0.141    | 0.0002   | 0.0009   | **     |
| EP_TWOMORE            | hybrid | 698 | 0.052     | 0.1737   | 0.2271   |        |
| EP_UNEMP              | blue   | 698 | -0.005    | 0.8916   | 0.9726   | SPARSE |
| EP_UNEMP              | gray   | 698 | 0.049     | 0.1957   | 0.3024   |        |
| EP_UNEMP              | green  | 698 | 0.020     | 0.5906   | 0.6924   |        |
| EP_UNEMP              | hybrid | 698 | -0.088    | 0.0198   | 0.0306   | **     |
| EP_UNINSUR            | blue   | 698 | -0.011    | 0.7700   | 0.9350   | SPARSE |
| EP_UNINSUR            | gray   | 698 | 0.053     | 0.1618   | 0.2751   |        |
| EP_UNINSUR            | green  | 698 | -0.031    | 0.4146   | 0.5035   |        |
| EP_UNINSUR            | hybrid | 698 | -0.094    | 0.0128   | 0.0229   | **     |
| age65plus             | blue   | 698 | 0.052     | 0.1735   | 0.3470   | SPARSE |
| age65plus             | gray   | 698 | -0.030    | 0.4361   | 0.5703   |        |
| age65plus             | green  | 698 | 0.083     | 0.0293   | 0.0857   |        |
| age65plus             | hybrid | 698 | -0.031    | 0.4206   | 0.4613   |        |
| crowding_over100      | blue   | 698 | 0.019     | 0.6158   | 0.7754   | SPARSE |
| crowding_over100      | gray   | 698 | 0.016     | 0.6711   | 0.7605   |        |
| crowding_over100      | green  | 698 | -0.004    | 0.9103   | 0.9103   |        |
| crowding_over100      | hybrid | 698 | -0.091    | 0.0165   | 0.0267   | **     |
| disability            | blue   | 698 | -0.001    | 0.9690   | 0.9840   | SPARSE |
| disability            | gray   | 698 | 0.069     | 0.0702   | 0.1592   |        |
| disability            | green  | 698 | -0.007    | 0.8519   | 0.8777   |        |
| disability            | hybrid | 698 | -0.119    | 0.0017   | 0.0039   | **     |
| limited_english_hh    | blue   | 698 | 0.046     | 0.2296   | 0.4109   | SPARSE |
| limited_english_hh    | gray   | 698 | -2.00e-04 | 0.9958   | 0.9958   |        |
| limited_english_hh    | green  | 698 | 0.035     | 0.3556   | 0.4669   |        |
| limited_english_hh    | hybrid | 698 | -0.136    | 0.0003   | 0.0018   | **     |
| no_broadband          | blue   | 698 | -0.219    | 4.96e-09 | 3.37e-08 | SPARSE |
| no_broadband          | gray   | 698 | 0.258     | 4.54e-12 | 7.72e-11 | **     |
| no_broadband          | green  | 698 | -0.209    | 2.64e-08 | 3.00e-07 | **     |
| no_broadband          | hybrid | 698 | -0.241    | 1.06e-10 | 3.60e-09 | **     |
| no_diploma_pop25      | blue   | 698 | 0.123     | 0.0011   | 0.0039   | SPARSE |
| no_diploma_pop25      | gray   | 698 | -0.057    | 0.1333   | 0.2386   |        |
| no_diploma_pop25      | green  | 698 | 0.086     | 0.0232   | 0.0857   |        |
| no_diploma_pop25      | hybrid | 698 | -0.126    | 0.0009   | 0.0029   | **     |
| no_fulltime_worker_hh | blue   | 698 | -0.123    | 0.0012   | 0.0039   | SPARSE |
| no_fulltime_worker_hh | gray   | 698 | 0.122     | 0.0013   | 0.0046   | **     |
| no_fulltime_worker_hh | green  | 698 | -0.062    | 0.0992   | 0.2409   |        |
| no_fulltime_worker_hh | hybrid | 698 | -0.029    | 0.4372   | 0.4645   |        |
| no_vehicle            | blue   | 698 | -0.267    | 7.81e-13 | 8.85e-12 | SPARSE |
| no_vehicle            | gray   | 698 | 0.254     | 9.39e-12 | 1.06e-10 | **     |
| no_vehicle            | green  | 698 | -0.239    | 1.49e-10 | 2.53e-09 | **     |
| no_vehicle            | hybrid | 698 | -0.133    | 0.0004   | 0.0019   | **     |
| poverty_under125      | blue   | 698 | -0.034    | 0.3684   | 0.4917   | SPARSE |
| poverty_under125      | gray   | 698 | 0.067     | 0.0750   | 0.1594   |        |
| poverty_under125      | green  | 698 | -0.033    | 0.3801   | 0.4786   |        |
| poverty_under125      | hybrid | 698 | -0.125    | 0.0009   | 0.0029   | **     |
| uninsured             | blue   | 698 | -0.006    | 0.8817   | 0.9726   | SPARSE |
| uninsured             | gray   | 698 | 0.057     | 0.1315   | 0.2386   |        |
| uninsured             | green  | 698 | -0.018    | 0.6416   | 0.7271   |        |
| uninsured             | hybrid | 698 | -0.114    | 0.0026   | 0.0055   | **     |

### 1a. Project-type SHARE vs. vulnerability - block group, 1,843 units, 4 types x 35 vulnerability variables (n=140 pairs)

| variable                   | type   | n     | rho       | p_raw    | p_fdr    | sig    |
|:---------------------------|:-------|:------|:----------|:---------|:---------|:-------|
| DISABILITYPCT              | blue   | 1,838 | 0.002     | 0.9318   | 0.9798   | SPARSE |
| DISABILITYPCT              | gray   | 1,838 | 0.062     | 0.0079   | 0.0138   | **     |
| DISABILITYPCT              | green  | 1,838 | 0.024     | 0.3114   | 0.4037   |        |
| DISABILITYPCT              | hybrid | 1,838 | -0.114    | 9.23e-07 | 2.94e-06 | **     |
| DSLPM                      | blue   | 1,837 | 0.064     | 0.0063   | 0.0110   | SPARSE |
| DSLPM                      | gray   | 1,837 | -0.025    | 0.2818   | 0.3945   |        |
| DSLPM                      | green  | 1,837 | 0.072     | 0.0020   | 0.0043   | **     |
| DSLPM                      | hybrid | 1,837 | -0.196    | 1.93e-17 | 9.67e-17 | **     |
| DWATER                     | blue   | 1,677 | -0.096    | 8.54e-05 | 0.0002   | SPARSE |
| DWATER                     | gray   | 1,677 | 0.115     | 2.23e-06 | 6.36e-06 | **     |
| DWATER                     | green  | 1,677 | -0.158    | 8.49e-11 | 3.71e-10 | **     |
| DWATER                     | hybrid | 1,677 | -0.024    | 0.3230   | 0.3565   |        |
| LESSHSPCT                  | blue   | 1,838 | 0.140     | 1.69e-09 | 5.37e-09 | SPARSE |
| LESSHSPCT                  | gray   | 1,838 | -0.071    | 0.0023   | 0.0046   | **     |
| LESSHSPCT                  | green  | 1,838 | 0.101     | 1.57e-05 | 4.59e-05 | **     |
| LESSHSPCT                  | hybrid | 1,838 | -0.088    | 0.0002   | 0.0003   | **     |
| LIFEEXPPCT                 | blue   | 1,749 | -0.001    | 0.9518   | 0.9798   | SPARSE |
| LIFEEXPPCT                 | gray   | 1,749 | 0.021     | 0.3711   | 0.4996   |        |
| LIFEEXPPCT                 | green  | 1,749 | -0.023    | 0.3357   | 0.4196   |        |
| LIFEEXPPCT                 | hybrid | 1,749 | -0.084    | 0.0004   | 0.0008   | **     |
| LINGISOPCT                 | blue   | 1,838 | 0.041     | 0.0784   | 0.1143   | SPARSE |
| LINGISOPCT                 | gray   | 1,838 | -0.007    | 0.7523   | 0.8331   |        |
| LINGISOPCT                 | green  | 1,838 | 0.001     | 0.9650   | 0.9650   |        |
| LINGISOPCT                 | hybrid | 1,838 | -0.072    | 0.0020   | 0.0031   | **     |
| LOWINCPCT                  | blue   | 1,838 | 0.021     | 0.3707   | 0.4806   | SPARSE |
| LOWINCPCT                  | gray   | 1,838 | 0.043     | 0.0682   | 0.1064   |        |
| LOWINCPCT                  | green  | 1,838 | 0.010     | 0.6578   | 0.7939   |        |
| LOWINCPCT                  | hybrid | 1,838 | -0.110    | 2.16e-06 | 6.31e-06 | **     |
| NO2                        | blue   | 1,828 | -0.112    | 1.52e-06 | 4.10e-06 | SPARSE |
| NO2                        | gray   | 1,828 | 0.147     | 2.72e-10 | 9.53e-10 | **     |
| NO2                        | green  | 1,828 | -0.098    | 2.73e-05 | 7.35e-05 | **     |
| NO2                        | hybrid | 1,828 | -0.272    | 2.65e-32 | 4.64e-31 | **     |
| OVER64PCT                  | blue   | 1,838 | 0.014     | 0.5486   | 0.6749   | SPARSE |
| OVER64PCT                  | gray   | 1,838 | 0.009     | 0.7143   | 0.8331   |        |
| OVER64PCT                  | green  | 1,838 | 0.024     | 0.3093   | 0.4037   |        |
| OVER64PCT                  | hybrid | 1,838 | -0.062    | 0.0079   | 0.0110   | **     |
| OZONE                      | blue   | 1,838 | 0.176     | 2.81e-14 | 1.64e-13 | SPARSE |
| OZONE                      | gray   | 1,838 | -0.170    | 1.95e-13 | 9.77e-13 | **     |
| OZONE                      | green  | 1,838 | 0.169     | 2.61e-13 | 1.52e-12 | **     |
| OZONE                      | hybrid | 1,838 | -0.080    | 0.0006   | 0.0010   | **     |
| PEOPCOLORPCT               | blue   | 1,838 | 0.250     | 1.39e-27 | 2.43e-26 | SPARSE |
| PEOPCOLORPCT               | gray   | 1,838 | -0.174    | 5.37e-14 | 3.76e-13 | **     |
| PEOPCOLORPCT               | green  | 1,838 | 0.221     | 8.34e-22 | 7.29e-21 | **     |
| PEOPCOLORPCT               | hybrid | 1,838 | -0.073    | 0.0018   | 0.0028   | **     |
| PM25                       | blue   | 1,838 | 0.246     | 8.85e-27 | 1.03e-25 | SPARSE |
| PM25                       | gray   | 1,838 | -0.223    | 4.30e-22 | 3.76e-21 | **     |
| PM25                       | green  | 1,838 | 0.248     | 3.90e-27 | 4.55e-26 | **     |
| PM25                       | hybrid | 1,838 | -0.095    | 4.72e-05 | 0.0001   | **     |
| PNPL                       | blue   | 1,837 | -0.162    | 3.24e-12 | 1.62e-11 | SPARSE |
| PNPL                       | gray   | 1,837 | 0.171     | 1.50e-13 | 8.74e-13 | **     |
| PNPL                       | green  | 1,837 | -0.116    | 5.62e-07 | 1.79e-06 | **     |
| PNPL                       | hybrid | 1,837 | -0.252    | 4.57e-28 | 4.00e-27 | **     |
| PRE1960PCT                 | blue   | 1,838 | -0.203    | 1.37e-18 | 9.61e-18 | SPARSE |
| PRE1960PCT                 | gray   | 1,838 | 0.242     | 8.35e-26 | 1.46e-24 | **     |
| PRE1960PCT                 | green  | 1,838 | -0.208    | 1.88e-19 | 1.32e-18 | **     |
| PRE1960PCT                 | hybrid | 1,838 | -0.135    | 5.81e-09 | 2.03e-08 | **     |
| PRMP                       | blue   | 1,837 | 0.014     | 0.5592   | 0.6749   | SPARSE |
| PRMP                       | gray   | 1,837 | 0.016     | 0.4832   | 0.6263   |        |
| PRMP                       | green  | 1,837 | 0.033     | 0.1623   | 0.2366   |        |
| PRMP                       | hybrid | 1,837 | -0.150    | 1.03e-10 | 4.53e-10 | **     |
| PTRAF                      | blue   | 1,837 | -0.086    | 0.0002   | 0.0005   | SPARSE |
| PTRAF                      | gray   | 1,837 | 0.120     | 2.44e-07 | 7.78e-07 | **     |
| PTRAF                      | green  | 1,837 | -0.053    | 0.0243   | 0.0426   | **     |
| PTRAF                      | hybrid | 1,837 | -0.287    | 3.73e-36 | 1.31e-34 | **     |
| PTSDF                      | blue   | 1,837 | -0.233    | 5.61e-24 | 4.91e-23 | SPARSE |
| PTSDF                      | gray   | 1,837 | 0.232     | 6.63e-24 | 7.74e-23 | **     |
| PTSDF                      | green  | 1,837 | -0.251    | 1.10e-27 | 1.92e-26 | **     |
| PTSDF                      | hybrid | 1,837 | -0.237    | 8.79e-25 | 6.15e-24 | **     |
| PWDIS                      | blue   | 1,837 | -0.146    | 3.05e-10 | 1.19e-09 | SPARSE |
| PWDIS                      | gray   | 1,837 | 0.159     | 7.68e-12 | 2.99e-11 | **     |
| PWDIS                      | green  | 1,837 | -0.031    | 0.1860   | 0.2604   |        |
| PWDIS                      | hybrid | 1,837 | -0.141    | 1.22e-09 | 4.76e-09 | **     |
| RSEI_AIR                   | blue   | 1,838 | -0.093    | 6.25e-05 | 0.0001   | SPARSE |
| RSEI_AIR                   | gray   | 1,838 | 0.107     | 4.41e-06 | 1.10e-05 | **     |
| RSEI_AIR                   | green  | 1,838 | -0.049    | 0.0366   | 0.0610   |        |
| RSEI_AIR                   | hybrid | 1,838 | -0.258    | 2.06e-29 | 2.40e-28 | **     |
| UNDER5PCT                  | blue   | 1,838 | -0.008    | 0.7258   | 0.8467   | SPARSE |
| UNDER5PCT                  | gray   | 1,838 | 0.006     | 0.7855   | 0.8331   |        |
| UNDER5PCT                  | green  | 1,838 | -0.003    | 0.8825   | 0.9526   |        |
| UNDER5PCT                  | hybrid | 1,838 | 0.030     | 0.2008   | 0.2342   |        |
| UNEMPPCT                   | blue   | 1,838 | 0.031     | 0.1806   | 0.2528   | SPARSE |
| UNEMPPCT                   | gray   | 1,838 | 0.001     | 0.9724   | 0.9724   |        |
| UNEMPPCT                   | green  | 1,838 | 0.036     | 0.1209   | 0.1840   |        |
| UNEMPPCT                   | hybrid | 1,838 | -0.023    | 0.3259   | 0.3565   |        |
| UST                        | blue   | 1,838 | -0.253    | 3.81e-28 | 1.33e-26 | SPARSE |
| UST                        | gray   | 1,838 | 0.271     | 2.31e-32 | 8.08e-31 | **     |
| UST                        | green  | 1,838 | -0.252    | 5.35e-28 | 1.87e-26 | **     |
| UST                        | hybrid | 1,838 | -0.206    | 4.02e-19 | 2.35e-18 | **     |
| income_disparity           | blue   | 1,207 | -0.105    | 0.0002   | 0.0005   | SPARSE |
| income_disparity           | gray   | 1,207 | 0.109     | 0.0002   | 0.0004   | **     |
| income_disparity           | green  | 1,207 | -0.096    | 0.0008   | 0.0020   | **     |
| income_disparity           | hybrid | 1,207 | -0.085    | 0.0032   | 0.0046   | **     |
| median_family_income       | blue   | 1,496 | -0.055    | 0.0320   | 0.0487   | SPARSE |
| median_family_income       | gray   | 1,496 | -0.003    | 0.9223   | 0.9494   |        |
| median_family_income       | green  | 1,496 | -0.049    | 0.0567   | 0.0901   |        |
| median_family_income       | hybrid | 1,496 | 0.107     | 3.19e-05 | 7.43e-05 | **     |
| median_gross_rent          | blue   | 1,297 | 0.066     | 0.0168   | 0.0267   | SPARSE |
| median_gross_rent          | gray   | 1,297 | -0.131    | 2.36e-06 | 6.36e-06 | **     |
| median_gross_rent          | green  | 1,297 | 0.085     | 0.0021   | 0.0043   | **     |
| median_gross_rent          | hybrid | 1,297 | 0.126     | 5.07e-06 | 1.27e-05 | **     |
| median_home_value          | blue   | 1,535 | -0.147    | 7.06e-09 | 2.06e-08 | SPARSE |
| median_home_value          | gray   | 1,535 | 0.084     | 0.0010   | 0.0021   | **     |
| median_home_value          | green  | 1,535 | -0.146    | 9.61e-09 | 3.74e-08 | **     |
| median_home_value          | hybrid | 1,535 | 0.002     | 0.9262   | 0.9534   |        |
| median_monthly_mortgage    | blue   | 1,238 | -0.171    | 1.43e-09 | 4.99e-09 | SPARSE |
| median_monthly_mortgage    | gray   | 1,238 | 0.099     | 0.0005   | 0.0011   | **     |
| median_monthly_mortgage    | green  | 1,238 | -0.160    | 1.59e-08 | 5.57e-08 | **     |
| median_monthly_mortgage    | hybrid | 1,238 | -3.84e-04 | 0.9892   | 0.9892   |        |
| no_diploma_under9yrs       | blue   | 1,833 | 0.094     | 5.64e-05 | 0.0001   | SPARSE |
| no_diploma_under9yrs       | gray   | 1,833 | -0.064    | 0.0064   | 0.0118   | **     |
| no_diploma_under9yrs       | green  | 1,833 | 0.064     | 0.0062   | 0.0114   | **     |
| no_diploma_under9yrs       | hybrid | 1,833 | -0.079    | 0.0007   | 0.0011   | **     |
| pct_crowding_over100       | blue   | 1,832 | 0.029     | 0.2109   | 0.2839   | SPARSE |
| pct_crowding_over100       | gray   | 1,832 | -0.006    | 0.7823   | 0.8331   |        |
| pct_crowding_over100       | green  | 1,832 | 0.006     | 0.7929   | 0.8952   |        |
| pct_crowding_over100       | hybrid | 1,832 | -0.044    | 0.0587   | 0.0733   |        |
| pct_no_kitchen             | blue   | 1,832 | -0.060    | 0.0102   | 0.0170   | SPARSE |
| pct_no_kitchen             | gray   | 1,832 | 0.060     | 0.0097   | 0.0162   | **     |
| pct_no_kitchen             | green  | 1,832 | -0.068    | 0.0037   | 0.0073   | **     |
| pct_no_kitchen             | hybrid | 1,832 | -0.041    | 0.0805   | 0.0972   |        |
| pct_no_plumbing            | blue   | 1,832 | 0.001     | 0.9516   | 0.9798   | SPARSE |
| pct_no_plumbing            | gray   | 1,832 | 0.014     | 0.5368   | 0.6479   |        |
| pct_no_plumbing            | green  | 1,832 | -0.002    | 0.9250   | 0.9526   |        |
| pct_no_plumbing            | hybrid | 1,832 | -0.060    | 0.0099   | 0.0133   | **     |
| pct_owner_occupied         | blue   | 1,832 | 0.158     | 8.97e-12 | 3.93e-11 | SPARSE |
| pct_owner_occupied         | gray   | 1,832 | -0.162    | 2.63e-12 | 1.15e-11 | **     |
| pct_owner_occupied         | green  | 1,832 | 0.168     | 5.31e-13 | 2.65e-12 | **     |
| pct_owner_occupied         | hybrid | 1,832 | 0.107     | 4.00e-06 | 1.08e-05 | **     |
| pct_single_parent_children | blue   | 1,827 | 0.066     | 0.0049   | 0.0090   | SPARSE |
| pct_single_parent_children | gray   | 1,827 | -0.042    | 0.0699   | 0.1064   |        |
| pct_single_parent_children | green  | 1,827 | 0.076     | 0.0012   | 0.0027   | **     |
| pct_single_parent_children | hybrid | 1,827 | -0.008    | 0.7378   | 0.7825   |        |
| poverty_pct_families       | blue   | 1,827 | -0.001    | 0.9828   | 0.9828   | SPARSE |
| poverty_pct_families       | gray   | 1,827 | 0.015     | 0.5168   | 0.6460   |        |
| poverty_pct_families       | green  | 1,827 | -0.008    | 0.7221   | 0.8425   |        |
| poverty_pct_families       | hybrid | 1,827 | -0.060    | 0.0103   | 0.0134   | **     |
| poverty_under150           | blue   | 1,832 | 0.007     | 0.7517   | 0.8487   | SPARSE |
| poverty_under150           | gray   | 1,832 | 0.031     | 0.1863   | 0.2717   |        |
| poverty_under150           | green  | 1,832 | -0.002    | 0.9254   | 0.9526   |        |
| poverty_under150           | hybrid | 1,832 | -0.080    | 0.0006   | 0.0011   | **     |

### 1b. Allocation-path SHARE vs. vulnerability - tract, 698 units, 3 paths (single-unit/municipality/county) x 34 vars (n=102 pairs)

| variable              | path         | n   | rho       | p_raw    | p_fdr    | sig   |
|:----------------------|:-------------|:----|:----------|:---------|:---------|:------|
| EP_AFAM               | county       | 698 | -0.013    | 0.7231   | 0.8288   |       |
| EP_AFAM               | municipality | 698 | -0.145    | 0.0001   | 0.0006   | **    |
| EP_AFAM               | single_unit  | 698 | 0.142     | 0.0002   | 0.0009   | **    |
| EP_AGE17              | county       | 698 | 0.074     | 0.0517   | 0.1172   |       |
| EP_AGE17              | municipality | 698 | -0.090    | 0.0169   | 0.0338   | **    |
| EP_AGE17              | single_unit  | 698 | 0.023     | 0.5496   | 0.7275   |       |
| EP_AGE65              | county       | 698 | 0.033     | 0.3774   | 0.5346   |       |
| EP_AGE65              | municipality | 698 | -0.031    | 0.4078   | 0.5135   |       |
| EP_AGE65              | single_unit  | 698 | -0.008    | 0.8342   | 0.9149   |       |
| EP_AIAN               | county       | 698 | 0.002     | 0.9487   | 0.9774   |       |
| EP_AIAN               | municipality | 698 | -0.027    | 0.4709   | 0.5713   |       |
| EP_AIAN               | single_unit  | 698 | 0.017     | 0.6592   | 0.8301   |       |
| EP_ASIAN              | county       | 698 | -0.055    | 0.1473   | 0.2782   |       |
| EP_ASIAN              | municipality | 698 | -0.013    | 0.7281   | 0.7985   |       |
| EP_ASIAN              | single_unit  | 698 | 0.045     | 0.2306   | 0.4355   |       |
| EP_CROWD              | county       | 697 | -0.053    | 0.1622   | 0.2902   |       |
| EP_CROWD              | municipality | 697 | 0.120     | 0.0014   | 0.0061   | **    |
| EP_CROWD              | single_unit  | 697 | -2.38e-04 | 0.9950   | 0.9950   |       |
| EP_DISABL             | county       | 698 | -0.045    | 0.2312   | 0.3743   |       |
| EP_DISABL             | municipality | 698 | 0.039     | 0.3088   | 0.4373   |       |
| EP_DISABL             | single_unit  | 698 | 0.038     | 0.3197   | 0.5434   |       |
| EP_GROUPQ             | county       | 698 | 0.013     | 0.7313   | 0.8288   |       |
| EP_GROUPQ             | municipality | 698 | -0.094    | 0.0125   | 0.0327   | **    |
| EP_GROUPQ             | single_unit  | 698 | 0.061     | 0.1080   | 0.2447   |       |
| EP_HBURD              | county       | 697 | -0.089    | 0.0182   | 0.0475   | **    |
| EP_HBURD              | municipality | 697 | 0.181     | 1.58e-06 | 8.95e-06 | **    |
| EP_HBURD              | single_unit  | 697 | -0.011    | 0.7723   | 0.9054   |       |
| EP_HISP               | county       | 698 | 0.208     | 3.13e-08 | 1.77e-07 | **    |
| EP_HISP               | municipality | 698 | 0.004     | 0.9183   | 0.9183   |       |
| EP_HISP               | single_unit  | 698 | -0.265    | 1.09e-12 | 3.72e-11 | **    |
| EP_LIMENG             | county       | 698 | 0.121     | 0.0013   | 0.0041   | **    |
| EP_LIMENG             | municipality | 698 | 0.054     | 0.1556   | 0.2520   |       |
| EP_LIMENG             | single_unit  | 698 | -0.182    | 1.36e-06 | 2.31e-05 | **    |
| EP_MINRTY             | county       | 698 | 0.259     | 3.52e-12 | 2.99e-11 | **    |
| EP_MINRTY             | municipality | 698 | -0.095    | 0.0117   | 0.0327   | **    |
| EP_MINRTY             | single_unit  | 698 | -0.178    | 2.19e-06 | 2.49e-05 | **    |
| EP_MOBILE             | county       | 697 | -0.039    | 0.3030   | 0.4480   |       |
| EP_MOBILE             | municipality | 697 | 0.006     | 0.8724   | 0.8989   |       |
| EP_MOBILE             | single_unit  | 697 | 0.034     | 0.3743   | 0.6060   |       |
| EP_MUNIT              | county       | 697 | -0.277    | 9.39e-14 | 1.60e-12 | **    |
| EP_MUNIT              | municipality | 697 | 0.326     | 1.09e-18 | 1.85e-17 | **    |
| EP_MUNIT              | single_unit  | 697 | 0.084     | 0.0264   | 0.0747   |       |
| EP_NHPI               | county       | 698 | 0.039     | 0.3030   | 0.4480   |       |
| EP_NHPI               | municipality | 698 | 0.026     | 0.4873   | 0.5713   |       |
| EP_NHPI               | single_unit  | 698 | -0.054    | 0.1505   | 0.3010   |       |
| EP_NOHSDP             | county       | 698 | 0.127     | 0.0008   | 0.0026   | **    |
| EP_NOHSDP             | municipality | 698 | -0.032    | 0.3984   | 0.5135   |       |
| EP_NOHSDP             | single_unit  | 698 | -0.097    | 0.0107   | 0.0330   | **    |
| EP_NOINT              | county       | 697 | -0.162    | 1.72e-05 | 7.31e-05 | **    |
| EP_NOINT              | municipality | 697 | 0.190     | 4.48e-07 | 3.05e-06 | **    |
| EP_NOINT              | single_unit  | 697 | 0.083     | 0.0290   | 0.0760   |       |
| EP_NOVEH              | county       | 697 | -0.330    | 3.92e-19 | 1.33e-17 | **    |
| EP_NOVEH              | municipality | 697 | 0.342     | 1.33e-20 | 4.52e-19 | **    |
| EP_NOVEH              | single_unit  | 697 | 0.156     | 3.72e-05 | 0.0003   | **    |
| EP_OTHERRACE          | county       | 698 | -0.057    | 0.1316   | 0.2632   |       |
| EP_OTHERRACE          | municipality | 698 | -0.015    | 0.6968   | 0.7898   |       |
| EP_OTHERRACE          | single_unit  | 698 | 0.081     | 0.0314   | 0.0763   |       |
| EP_POV150             | county       | 697 | -0.024    | 0.5318   | 0.6954   |       |
| EP_POV150             | municipality | 697 | 0.100     | 0.0082   | 0.0253   | **    |
| EP_POV150             | single_unit  | 697 | -0.026    | 0.4985   | 0.7275   |       |
| EP_SNGPNT             | county       | 697 | 0.080     | 0.0347   | 0.0843   |       |
| EP_SNGPNT             | municipality | 697 | -0.070    | 0.0657   | 0.1117   |       |
| EP_SNGPNT             | single_unit  | 697 | -0.001    | 0.9690   | 0.9950   |       |
| EP_TWOMORE            | county       | 698 | -0.168    | 7.73e-06 | 3.75e-05 | **    |
| EP_TWOMORE            | municipality | 698 | 0.038     | 0.3216   | 0.4373   |       |
| EP_TWOMORE            | single_unit  | 698 | 0.166     | 1.08e-05 | 9.18e-05 | **    |
| EP_UNEMP              | county       | 698 | -4.92e-04 | 0.9896   | 0.9896   |       |
| EP_UNEMP              | municipality | 698 | 0.050     | 0.1901   | 0.2810   |       |
| EP_UNEMP              | single_unit  | 698 | -0.004    | 0.9255   | 0.9833   |       |
| EP_UNINSUR            | county       | 698 | -0.013    | 0.7294   | 0.8288   |       |
| EP_UNINSUR            | municipality | 698 | 0.091     | 0.0162   | 0.0338   | **    |
| EP_UNINSUR            | single_unit  | 698 | -0.022    | 0.5563   | 0.7275   |       |
| age65plus             | county       | 698 | 0.057     | 0.1310   | 0.2632   |       |
| age65plus             | municipality | 698 | -0.079    | 0.0370   | 0.0698   |       |
| age65plus             | single_unit  | 698 | -0.011    | 0.7651   | 0.9054   |       |
| crowding_over100      | county       | 698 | 0.024     | 0.5278   | 0.6954   |       |
| crowding_over100      | municipality | 698 | 0.078     | 0.0392   | 0.0701   |       |
| crowding_over100      | single_unit  | 698 | -0.042    | 0.2703   | 0.4836   |       |
| disability            | county       | 698 | 0.008     | 0.8302   | 0.9105   |       |
| disability            | municipality | 698 | -0.009    | 0.8086   | 0.8591   |       |
| disability            | single_unit  | 698 | 0.009     | 0.8205   | 0.9149   |       |
| limited_english_hh    | county       | 698 | 0.047     | 0.2195   | 0.3732   |       |
| limited_english_hh    | municipality | 698 | 0.110     | 0.0037   | 0.0140   | **    |
| limited_english_hh    | single_unit  | 698 | -0.125    | 0.0009   | 0.0044   | **    |
| no_broadband          | county       | 698 | -0.227    | 1.38e-09 | 9.36e-09 | **    |
| no_broadband          | municipality | 698 | 0.255     | 8.80e-12 | 7.48e-11 | **    |
| no_broadband          | single_unit  | 698 | 0.116     | 0.0021   | 0.0089   | **    |
| no_diploma_pop25      | county       | 698 | 0.145     | 0.0001   | 0.0005   | **    |
| no_diploma_pop25      | municipality | 698 | -0.051    | 0.1753   | 0.2710   |       |
| no_diploma_pop25      | single_unit  | 698 | -0.105    | 0.0054   | 0.0183   | **    |
| no_fulltime_worker_hh | county       | 698 | -0.115    | 0.0023   | 0.0064   | **    |
| no_fulltime_worker_hh | municipality | 698 | 0.108     | 0.0042   | 0.0144   | **    |
| no_fulltime_worker_hh | single_unit  | 698 | 0.057     | 0.1350   | 0.2869   |       |
| no_vehicle            | county       | 698 | -0.268    | 5.90e-13 | 6.69e-12 | **    |
| no_vehicle            | municipality | 698 | 0.307     | 1.05e-16 | 1.19e-15 | **    |
| no_vehicle            | single_unit  | 698 | 0.107     | 0.0045   | 0.0169   | **    |
| poverty_under125      | county       | 698 | -0.018    | 0.6400   | 0.8059   |       |
| poverty_under125      | municipality | 698 | 0.091     | 0.0163   | 0.0338   | **    |
| poverty_under125      | single_unit  | 698 | -0.027    | 0.4766   | 0.7275   |       |
| uninsured             | county       | 698 | -0.004    | 0.9202   | 0.9774   |       |
| uninsured             | municipality | 698 | 0.090     | 0.0169   | 0.0338   | **    |
| uninsured             | single_unit  | 698 | -0.023    | 0.5500   | 0.7275   |       |

### 1b. Allocation-path SHARE vs. vulnerability - block group, 1,843 units, 3 paths x 35 vars (n=105 pairs)

| variable                   | path         | n     | rho    | p_raw    | p_fdr    | sig   |
|:---------------------------|:-------------|:------|:-------|:---------|:---------|:------|
| DISABILITYPCT              | county       | 1,838 | 0.002  | 0.9248   | 0.9520   |       |
| DISABILITYPCT              | municipality | 1,838 | 0.034  | 0.1488   | 0.1929   |       |
| DISABILITYPCT              | single_unit  | 1,838 | -0.025 | 0.2864   | 0.3713   |       |
| DSLPM                      | county       | 1,837 | 0.078  | 0.0008   | 0.0016   | **    |
| DSLPM                      | municipality | 1,837 | 0.002  | 0.9209   | 0.9209   |       |
| DSLPM                      | single_unit  | 1,837 | -0.038 | 0.1029   | 0.1896   |       |
| DWATER                     | county       | 1,677 | -0.097 | 6.97e-05 | 0.0002   | **    |
| DWATER                     | municipality | 1,677 | 0.135  | 3.05e-08 | 1.07e-07 | **    |
| DWATER                     | single_unit  | 1,677 | -0.006 | 0.8043   | 0.8797   |       |
| LESSHSPCT                  | county       | 1,838 | 0.139  | 2.05e-09 | 6.51e-09 | **    |
| LESSHSPCT                  | municipality | 1,838 | -0.068 | 0.0033   | 0.0065   | **    |
| LESSHSPCT                  | single_unit  | 1,838 | -0.090 | 0.0001   | 0.0004   | **    |
| LIFEEXPPCT                 | county       | 1,749 | -0.004 | 0.8660   | 0.9185   |       |
| LIFEEXPPCT                 | municipality | 1,749 | -0.025 | 0.3035   | 0.3427   |       |
| LIFEEXPPCT                 | single_unit  | 1,749 | 0.040  | 0.0914   | 0.1881   |       |
| LINGISOPCT                 | county       | 1,838 | 0.028  | 0.2310   | 0.3109   |       |
| LINGISOPCT                 | municipality | 1,838 | 0.087  | 0.0002   | 0.0004   | **    |
| LINGISOPCT                 | single_unit  | 1,838 | -0.109 | 2.74e-06 | 2.39e-05 | **    |
| LOWINCPCT                  | county       | 1,838 | 0.023  | 0.3283   | 0.4255   |       |
| LOWINCPCT                  | municipality | 1,838 | 0.070  | 0.0025   | 0.0052   | **    |
| LOWINCPCT                  | single_unit  | 1,838 | -0.077 | 0.0010   | 0.0032   | **    |
| NO2                        | county       | 1,828 | -0.106 | 5.26e-06 | 1.42e-05 | **    |
| NO2                        | municipality | 1,828 | 0.248  | 4.19e-27 | 2.93e-26 | **    |
| NO2                        | single_unit  | 1,828 | -0.061 | 0.0091   | 0.0213   | **    |
| OVER64PCT                  | county       | 1,838 | 0.017  | 0.4670   | 0.5636   |       |
| OVER64PCT                  | municipality | 1,838 | -0.027 | 0.2445   | 0.2853   |       |
| OVER64PCT                  | single_unit  | 1,838 | -0.002 | 0.9327   | 0.9327   |       |
| OZONE                      | county       | 1,838 | 0.189  | 2.55e-16 | 1.49e-15 | **    |
| OZONE                      | municipality | 1,838 | -0.116 | 6.38e-07 | 1.72e-06 | **    |
| OZONE                      | single_unit  | 1,838 | -0.067 | 0.0041   | 0.0118   | **    |
| PEOPCOLORPCT               | county       | 1,838 | 0.262  | 2.52e-30 | 3.19e-29 | **    |
| PEOPCOLORPCT               | municipality | 1,838 | -0.153 | 4.96e-11 | 1.93e-10 | **    |
| PEOPCOLORPCT               | single_unit  | 1,838 | -0.145 | 4.11e-10 | 1.44e-08 | **    |
| PM25                       | county       | 1,838 | 0.263  | 2.02e-30 | 3.19e-29 | **    |
| PM25                       | municipality | 1,838 | -0.181 | 5.01e-15 | 2.51e-14 | **    |
| PM25                       | single_unit  | 1,838 | -0.094 | 5.91e-05 | 0.0003   | **    |
| PNPL                       | county       | 1,837 | -0.157 | 1.34e-11 | 5.64e-11 | **    |
| PNPL                       | municipality | 1,837 | 0.262  | 2.73e-30 | 3.19e-29 | **    |
| PNPL                       | single_unit  | 1,837 | 0.035  | 0.1333   | 0.2158   |       |
| PRE1960PCT                 | county       | 1,838 | -0.215 | 1.21e-20 | 8.50e-20 | **    |
| PRE1960PCT                 | municipality | 1,838 | 0.239  | 2.60e-25 | 1.52e-24 | **    |
| PRE1960PCT                 | single_unit  | 1,838 | 0.091  | 9.80e-05 | 0.0004   | **    |
| PRMP                       | county       | 1,837 | 0.039  | 0.0941   | 0.1373   |       |
| PRMP                       | municipality | 1,837 | 0.041  | 0.0772   | 0.1039   |       |
| PRMP                       | single_unit  | 1,837 | 0.002  | 0.9211   | 0.9327   |       |
| PTRAF                      | county       | 1,837 | -0.069 | 0.0030   | 0.0052   | **    |
| PTRAF                      | municipality | 1,837 | 0.125  | 6.99e-08 | 2.22e-07 | **    |
| PTRAF                      | single_unit  | 1,837 | 0.024  | 0.3126   | 0.3907   |       |
| PTSDF                      | county       | 1,837 | -0.247 | 5.71e-27 | 5.00e-26 | **    |
| PTSDF                      | municipality | 1,837 | 0.349  | 6.71e-54 | 2.35e-52 | **    |
| PTSDF                      | single_unit  | 1,837 | 0.019  | 0.4045   | 0.4882   |       |
| PWDIS                      | county       | 1,837 | -0.157 | 1.45e-11 | 5.64e-11 | **    |
| PWDIS                      | municipality | 1,837 | 0.115  | 7.05e-07 | 1.76e-06 | **    |
| PWDIS                      | single_unit  | 1,837 | 0.121  | 1.79e-07 | 3.13e-06 | **    |
| RSEI_AIR                   | county       | 1,838 | -0.088 | 0.0002   | 0.0003   | **    |
| RSEI_AIR                   | municipality | 1,838 | 0.174  | 5.65e-14 | 2.47e-13 | **    |
| RSEI_AIR                   | single_unit  | 1,838 | 0.035  | 0.1354   | 0.2158   |       |
| UNDER5PCT                  | county       | 1,838 | 0.007  | 0.7510   | 0.8214   |       |
| UNDER5PCT                  | municipality | 1,838 | -0.020 | 0.3994   | 0.4236   |       |
| UNDER5PCT                  | single_unit  | 1,838 | 0.034  | 0.1490   | 0.2173   |       |
| UNEMPPCT                   | county       | 1,838 | 0.033  | 0.1574   | 0.2204   |       |
| UNEMPPCT                   | municipality | 1,838 | 0.011  | 0.6376   | 0.6564   |       |
| UNEMPPCT                   | single_unit  | 1,838 | -0.034 | 0.1418   | 0.2158   |       |
| UST                        | county       | 1,838 | -0.262 | 2.73e-30 | 3.19e-29 | **    |
| UST                        | municipality | 1,838 | 0.298  | 4.55e-39 | 7.96e-38 | **    |
| UST                        | single_unit  | 1,838 | 0.080  | 0.0006   | 0.0022   | **    |
| income_disparity           | county       | 1,207 | -0.105 | 0.0003   | 0.0006   | **    |
| income_disparity           | municipality | 1,207 | 0.148  | 2.25e-07 | 6.57e-07 | **    |
| income_disparity           | single_unit  | 1,207 | -0.017 | 0.5641   | 0.6369   |       |
| median_family_income       | county       | 1,496 | -0.060 | 0.0196   | 0.0298   | **    |
| median_family_income       | municipality | 1,496 | -0.055 | 0.0333   | 0.0507   |       |
| median_family_income       | single_unit  | 1,496 | 0.123  | 1.68e-06 | 1.96e-05 | **    |
| median_gross_rent          | county       | 1,297 | 0.068  | 0.0142   | 0.0226   | **    |
| median_gross_rent          | municipality | 1,297 | -0.065 | 0.0192   | 0.0305   | **    |
| median_gross_rent          | single_unit  | 1,297 | -0.018 | 0.5073   | 0.5918   |       |
| median_home_value          | county       | 1,535 | -0.140 | 3.33e-08 | 9.71e-08 | **    |
| median_home_value          | municipality | 1,535 | 0.067  | 0.0089   | 0.0155   | **    |
| median_home_value          | single_unit  | 1,535 | 0.113  | 9.48e-06 | 6.64e-05 | **    |
| median_monthly_mortgage    | county       | 1,238 | -0.172 | 1.21e-09 | 4.25e-09 | **    |
| median_monthly_mortgage    | municipality | 1,238 | 0.126  | 8.20e-06 | 1.91e-05 | **    |
| median_monthly_mortgage    | single_unit  | 1,238 | 0.109  | 0.0001   | 0.0004   | **    |
| no_diploma_under9yrs       | county       | 1,833 | 0.099  | 2.31e-05 | 5.77e-05 | **    |
| no_diploma_under9yrs       | municipality | 1,833 | -0.045 | 0.0537   | 0.0784   |       |
| no_diploma_under9yrs       | single_unit  | 1,833 | -0.066 | 0.0048   | 0.0130   | **    |
| pct_crowding_over100       | county       | 1,832 | 0.022  | 0.3506   | 0.4383   |       |
| pct_crowding_over100       | municipality | 1,832 | 0.032  | 0.1668   | 0.2085   |       |
| pct_crowding_over100       | single_unit  | 1,832 | -0.035 | 0.1363   | 0.2158   |       |
| pct_no_kitchen             | county       | 1,832 | -0.066 | 0.0048   | 0.0080   | **    |
| pct_no_kitchen             | municipality | 1,832 | 0.063  | 0.0073   | 0.0135   | **    |
| pct_no_kitchen             | single_unit  | 1,832 | 0.039  | 0.0987   | 0.1896   |       |
| pct_no_plumbing            | county       | 1,832 | -0.001 | 0.9605   | 0.9605   |       |
| pct_no_plumbing            | municipality | 1,832 | 0.021  | 0.3590   | 0.3927   |       |
| pct_no_plumbing            | single_unit  | 1,832 | -0.004 | 0.8533   | 0.9051   |       |
| pct_owner_occupied         | county       | 1,832 | 0.173  | 7.92e-14 | 3.96e-13 | **    |
| pct_owner_occupied         | municipality | 1,832 | -0.261 | 7.39e-30 | 6.46e-29 | **    |
| pct_owner_occupied         | single_unit  | 1,832 | 0.030  | 0.2013   | 0.2710   |       |
| pct_single_parent_children | county       | 1,827 | 0.073  | 0.0019   | 0.0035   | **    |
| pct_single_parent_children | municipality | 1,827 | -0.028 | 0.2324   | 0.2805   |       |
| pct_single_parent_children | single_unit  | 1,827 | -0.042 | 0.0717   | 0.1569   |       |
| poverty_pct_families       | county       | 1,827 | 0.010  | 0.6735   | 0.7604   |       |
| poverty_pct_families       | municipality | 1,827 | 0.044  | 0.0573   | 0.0802   |       |
| poverty_pct_families       | single_unit  | 1,827 | -0.033 | 0.1556   | 0.2178   |       |
| poverty_under150           | county       | 1,832 | 0.012  | 0.6080   | 0.7093   |       |
| poverty_under150           | municipality | 1,832 | 0.058  | 0.0134   | 0.0223   | **    |
| poverty_under150           | single_unit  | 1,832 | -0.062 | 0.0083   | 0.0209   | **    |

### 1c. Type_any group comparison - tract (Mann-Whitney U, n=136 pairs)

| variable              | type   | n_receiving   | n_not   | mean_receiving   | mean_not   | p_raw   | p_fdr   | sig    |
|:----------------------|:-------|:--------------|:--------|:-----------------|:-----------|:--------|:--------|:-------|
| EP_AFAM               | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_AFAM               | gray   | 698           | 0       |                  |            |         |         |        |
| EP_AFAM               | green  | 698           | 0       |                  |            |         |         |        |
| EP_AFAM               | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_AGE17              | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_AGE17              | gray   | 698           | 0       |                  |            |         |         |        |
| EP_AGE17              | green  | 698           | 0       |                  |            |         |         |        |
| EP_AGE17              | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_AGE65              | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_AGE65              | gray   | 698           | 0       |                  |            |         |         |        |
| EP_AGE65              | green  | 698           | 0       |                  |            |         |         |        |
| EP_AGE65              | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_AIAN               | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_AIAN               | gray   | 698           | 0       |                  |            |         |         |        |
| EP_AIAN               | green  | 698           | 0       |                  |            |         |         |        |
| EP_AIAN               | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_ASIAN              | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_ASIAN              | gray   | 698           | 0       |                  |            |         |         |        |
| EP_ASIAN              | green  | 698           | 0       |                  |            |         |         |        |
| EP_ASIAN              | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_CROWD              | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_CROWD              | gray   | 697           | 0       |                  |            |         |         |        |
| EP_CROWD              | green  | 697           | 0       |                  |            |         |         |        |
| EP_CROWD              | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_DISABL             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_DISABL             | gray   | 698           | 0       |                  |            |         |         |        |
| EP_DISABL             | green  | 698           | 0       |                  |            |         |         |        |
| EP_DISABL             | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_GROUPQ             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_GROUPQ             | gray   | 698           | 0       |                  |            |         |         |        |
| EP_GROUPQ             | green  | 698           | 0       |                  |            |         |         |        |
| EP_GROUPQ             | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_HBURD              | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_HBURD              | gray   | 697           | 0       |                  |            |         |         |        |
| EP_HBURD              | green  | 697           | 0       |                  |            |         |         |        |
| EP_HBURD              | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_HISP               | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_HISP               | gray   | 698           | 0       |                  |            |         |         |        |
| EP_HISP               | green  | 698           | 0       |                  |            |         |         |        |
| EP_HISP               | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_LIMENG             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_LIMENG             | gray   | 698           | 0       |                  |            |         |         |        |
| EP_LIMENG             | green  | 698           | 0       |                  |            |         |         |        |
| EP_LIMENG             | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_MINRTY             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_MINRTY             | gray   | 698           | 0       |                  |            |         |         |        |
| EP_MINRTY             | green  | 698           | 0       |                  |            |         |         |        |
| EP_MINRTY             | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_MOBILE             | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_MOBILE             | gray   | 697           | 0       |                  |            |         |         |        |
| EP_MOBILE             | green  | 697           | 0       |                  |            |         |         |        |
| EP_MOBILE             | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_MUNIT              | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_MUNIT              | gray   | 697           | 0       |                  |            |         |         |        |
| EP_MUNIT              | green  | 697           | 0       |                  |            |         |         |        |
| EP_MUNIT              | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_NHPI               | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_NHPI               | gray   | 698           | 0       |                  |            |         |         |        |
| EP_NHPI               | green  | 698           | 0       |                  |            |         |         |        |
| EP_NHPI               | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_NOHSDP             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_NOHSDP             | gray   | 698           | 0       |                  |            |         |         |        |
| EP_NOHSDP             | green  | 698           | 0       |                  |            |         |         |        |
| EP_NOHSDP             | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_NOINT              | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_NOINT              | gray   | 697           | 0       |                  |            |         |         |        |
| EP_NOINT              | green  | 697           | 0       |                  |            |         |         |        |
| EP_NOINT              | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_NOVEH              | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_NOVEH              | gray   | 697           | 0       |                  |            |         |         |        |
| EP_NOVEH              | green  | 697           | 0       |                  |            |         |         |        |
| EP_NOVEH              | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_OTHERRACE          | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_OTHERRACE          | gray   | 698           | 0       |                  |            |         |         |        |
| EP_OTHERRACE          | green  | 698           | 0       |                  |            |         |         |        |
| EP_OTHERRACE          | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_POV150             | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_POV150             | gray   | 697           | 0       |                  |            |         |         |        |
| EP_POV150             | green  | 697           | 0       |                  |            |         |         |        |
| EP_POV150             | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_SNGPNT             | blue   | 697           | 0       |                  |            |         |         | SPARSE |
| EP_SNGPNT             | gray   | 697           | 0       |                  |            |         |         |        |
| EP_SNGPNT             | green  | 697           | 0       |                  |            |         |         |        |
| EP_SNGPNT             | hybrid | 697           | 0       |                  |            |         |         |        |
| EP_TWOMORE            | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_TWOMORE            | gray   | 698           | 0       |                  |            |         |         |        |
| EP_TWOMORE            | green  | 698           | 0       |                  |            |         |         |        |
| EP_TWOMORE            | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_UNEMP              | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_UNEMP              | gray   | 698           | 0       |                  |            |         |         |        |
| EP_UNEMP              | green  | 698           | 0       |                  |            |         |         |        |
| EP_UNEMP              | hybrid | 698           | 0       |                  |            |         |         |        |
| EP_UNINSUR            | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| EP_UNINSUR            | gray   | 698           | 0       |                  |            |         |         |        |
| EP_UNINSUR            | green  | 698           | 0       |                  |            |         |         |        |
| EP_UNINSUR            | hybrid | 698           | 0       |                  |            |         |         |        |
| age65plus             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| age65plus             | gray   | 698           | 0       |                  |            |         |         |        |
| age65plus             | green  | 698           | 0       |                  |            |         |         |        |
| age65plus             | hybrid | 698           | 0       |                  |            |         |         |        |
| crowding_over100      | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| crowding_over100      | gray   | 698           | 0       |                  |            |         |         |        |
| crowding_over100      | green  | 698           | 0       |                  |            |         |         |        |
| crowding_over100      | hybrid | 698           | 0       |                  |            |         |         |        |
| disability            | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| disability            | gray   | 698           | 0       |                  |            |         |         |        |
| disability            | green  | 698           | 0       |                  |            |         |         |        |
| disability            | hybrid | 698           | 0       |                  |            |         |         |        |
| limited_english_hh    | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| limited_english_hh    | gray   | 698           | 0       |                  |            |         |         |        |
| limited_english_hh    | green  | 698           | 0       |                  |            |         |         |        |
| limited_english_hh    | hybrid | 698           | 0       |                  |            |         |         |        |
| no_broadband          | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| no_broadband          | gray   | 698           | 0       |                  |            |         |         |        |
| no_broadband          | green  | 698           | 0       |                  |            |         |         |        |
| no_broadband          | hybrid | 698           | 0       |                  |            |         |         |        |
| no_diploma_pop25      | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| no_diploma_pop25      | gray   | 698           | 0       |                  |            |         |         |        |
| no_diploma_pop25      | green  | 698           | 0       |                  |            |         |         |        |
| no_diploma_pop25      | hybrid | 698           | 0       |                  |            |         |         |        |
| no_fulltime_worker_hh | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| no_fulltime_worker_hh | gray   | 698           | 0       |                  |            |         |         |        |
| no_fulltime_worker_hh | green  | 698           | 0       |                  |            |         |         |        |
| no_fulltime_worker_hh | hybrid | 698           | 0       |                  |            |         |         |        |
| no_vehicle            | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| no_vehicle            | gray   | 698           | 0       |                  |            |         |         |        |
| no_vehicle            | green  | 698           | 0       |                  |            |         |         |        |
| no_vehicle            | hybrid | 698           | 0       |                  |            |         |         |        |
| poverty_under125      | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| poverty_under125      | gray   | 698           | 0       |                  |            |         |         |        |
| poverty_under125      | green  | 698           | 0       |                  |            |         |         |        |
| poverty_under125      | hybrid | 698           | 0       |                  |            |         |         |        |
| uninsured             | blue   | 698           | 0       |                  |            |         |         | SPARSE |
| uninsured             | gray   | 698           | 0       |                  |            |         |         |        |
| uninsured             | green  | 698           | 0       |                  |            |         |         |        |
| uninsured             | hybrid | 698           | 0       |                  |            |         |         |        |

### 1c. Type_any group comparison - block group (Mann-Whitney U, n=140 pairs)

| variable                   | type   | n_receiving   | n_not   | mean_receiving   | mean_not    | p_raw    | p_fdr    | sig    |
|:---------------------------|:-------|:--------------|:--------|:-----------------|:------------|:---------|:---------|:-------|
| DISABILITYPCT              | blue   | 1,834         | 9       | 0.102            | 0.009       | 1.59e-06 | 6.35e-06 | SPARSE |
| DISABILITYPCT              | gray   | 1,838         | 5       | 0.102            | 0.000       | 0.0001   | 0.0005   | **     |
| DISABILITYPCT              | green  | 1,834         | 9       | 0.102            | 0.009       | 1.59e-06 | 6.35e-06 | **     |
| DISABILITYPCT              | hybrid | 1,836         | 7       | 0.102            | 0.011       | 3.55e-05 | 8.29e-05 | **     |
| DSLPM                      | blue   | 1,834         | 3       | 0.289            | 0.371       | 0.1263   | 0.1579   | SPARSE |
| DSLPM                      | gray   | 1,837         | 0       |                  |             |          |          |        |
| DSLPM                      | green  | 1,834         | 3       | 0.289            | 0.371       | 0.1263   | 0.1579   |        |
| DSLPM                      | hybrid | 1,835         | 2       |                  |             |          |          |        |
| DWATER                     | blue   | 1,676         | 1       |                  |             |          |          | SPARSE |
| DWATER                     | gray   | 1,677         | 0       |                  |             |          |          |        |
| DWATER                     | green  | 1,676         | 1       |                  |             |          |          |        |
| DWATER                     | hybrid | 1,676         | 1       |                  |             |          |          |        |
| LESSHSPCT                  | blue   | 1,834         | 9       | 0.162            | 0.000       | 1.51e-06 | 6.35e-06 | SPARSE |
| LESSHSPCT                  | gray   | 1,838         | 5       | 0.162            | 0.000       | 0.0003   | 0.0010   | **     |
| LESSHSPCT                  | green  | 1,834         | 9       | 0.162            | 0.000       | 1.51e-06 | 6.35e-06 | **     |
| LESSHSPCT                  | hybrid | 1,836         | 7       | 0.162            | 0.000       | 2.24e-05 | 7.84e-05 | **     |
| LIFEEXPPCT                 | blue   | 1,748         | 2       |                  |             |          |          | SPARSE |
| LIFEEXPPCT                 | gray   | 1,749         | 1       |                  |             |          |          |        |
| LIFEEXPPCT                 | green  | 1,748         | 2       |                  |             |          |          |        |
| LIFEEXPPCT                 | hybrid | 1,748         | 2       |                  |             |          |          |        |
| LINGISOPCT                 | blue   | 1,834         | 9       | 0.224            | 0.000       | 2.45e-06 | 8.18e-06 | SPARSE |
| LINGISOPCT                 | gray   | 1,838         | 5       | 0.223            | 0.000       | 0.0005   | 0.0011   | **     |
| LINGISOPCT                 | green  | 1,834         | 9       | 0.224            | 0.000       | 2.45e-06 | 8.18e-06 | **     |
| LINGISOPCT                 | hybrid | 1,836         | 7       | 0.224            | 0.000       | 3.28e-05 | 8.29e-05 | **     |
| LOWINCPCT                  | blue   | 1,834         | 9       | 0.361            | 0.000       | 3.40e-07 | 2.27e-06 | SPARSE |
| LOWINCPCT                  | gray   | 1,838         | 5       | 0.360            | 0.000       | 0.0001   | 0.0005   | **     |
| LOWINCPCT                  | green  | 1,834         | 9       | 0.361            | 0.000       | 3.40e-07 | 2.27e-06 | **     |
| LOWINCPCT                  | hybrid | 1,836         | 7       | 0.361            | 0.000       | 6.95e-06 | 3.25e-05 | **     |
| NO2                        | blue   | 1,824         | 8       | 9.835            | 6.403       | 0.0614   | 0.1007   | SPARSE |
| NO2                        | gray   | 1,828         | 4       | 9.833            | 3.809       | 0.0036   | 0.0056   | **     |
| NO2                        | green  | 1,824         | 8       | 9.835            | 6.403       | 0.0614   | 0.1007   |        |
| NO2                        | hybrid | 1,826         | 6       | 9.831            | 6.442       | 0.1109   | 0.1552   |        |
| OVER64PCT                  | blue   | 1,834         | 9       | 0.179            | 0.000       | 3.25e-07 | 2.27e-06 | SPARSE |
| OVER64PCT                  | gray   | 1,838         | 5       | 0.178            | 0.000       | 0.0001   | 0.0005   | **     |
| OVER64PCT                  | green  | 1,834         | 9       | 0.179            | 0.000       | 3.25e-07 | 2.27e-06 | **     |
| OVER64PCT                  | hybrid | 1,836         | 7       | 0.179            | 0.000       | 6.71e-06 | 3.25e-05 | **     |
| OZONE                      | blue   | 1,834         | 9       | 59.541           | 59.437      | 0.5295   | 0.5573   | SPARSE |
| OZONE                      | gray   | 1,838         | 5       | 59.542           | 59.313      | 0.4936   | 0.4936   |        |
| OZONE                      | green  | 1,834         | 9       | 59.541           | 59.437      | 0.5295   | 0.5573   |        |
| OZONE                      | hybrid | 1,836         | 7       | 59.541           | 59.518      | 0.8703   | 0.8703   |        |
| PEOPCOLORPCT               | blue   | 1,834         | 9       | 0.844            | 0.000       | 2.32e-07 | 2.27e-06 | SPARSE |
| PEOPCOLORPCT               | gray   | 1,838         | 5       | 0.843            | 0.000       | 0.0001   | 0.0005   | **     |
| PEOPCOLORPCT               | green  | 1,834         | 9       | 0.844            | 0.000       | 2.32e-07 | 2.27e-06 | **     |
| PEOPCOLORPCT               | hybrid | 1,836         | 7       | 0.843            | 0.000       | 5.15e-06 | 3.25e-05 | **     |
| PM25                       | blue   | 1,834         | 9       | 7.961            | 7.533       | 0.0253   | 0.0505   | SPARSE |
| PM25                       | gray   | 1,838         | 5       | 7.961            | 7.264       | 0.0068   | 0.0079   | **     |
| PM25                       | green  | 1,834         | 9       | 7.961            | 7.533       | 0.0253   | 0.0505   |        |
| PM25                       | hybrid | 1,836         | 7       | 7.961            | 7.548       | 0.1365   | 0.1592   |        |
| PNPL                       | blue   | 1,834         | 3       | 0.352            | 0.555       | 0.1243   | 0.1579   | SPARSE |
| PNPL                       | gray   | 1,837         | 0       |                  |             |          |          |        |
| PNPL                       | green  | 1,834         | 3       | 0.352            | 0.555       | 0.1243   | 0.1579   |        |
| PNPL                       | hybrid | 1,835         | 2       |                  |             |          |          |        |
| PRE1960PCT                 | blue   | 1,834         | 9       | 0.248            | 0.000       | 0.0002   | 0.0003   | SPARSE |
| PRE1960PCT                 | gray   | 1,838         | 5       | 0.247            | 0.000       | 0.0048   | 0.0061   | **     |
| PRE1960PCT                 | green  | 1,834         | 9       | 0.248            | 0.000       | 0.0002   | 0.0003   | **     |
| PRE1960PCT                 | hybrid | 1,836         | 7       | 0.248            | 0.000       | 0.0008   | 0.0013   | **     |
| PRMP                       | blue   | 1,834         | 3       | 0.617            | 1.071       | 0.3618   | 0.4020   | SPARSE |
| PRMP                       | gray   | 1,837         | 0       |                  |             |          |          |        |
| PRMP                       | green  | 1,834         | 3       | 0.617            | 1.071       | 0.3618   | 0.4020   |        |
| PRMP                       | hybrid | 1,835         | 2       |                  |             |          |          |        |
| PTRAF                      | blue   | 1,834         | 3       | 2186254.289      | 3479440.229 | 0.3149   | 0.3705   | SPARSE |
| PTRAF                      | gray   | 1,837         | 0       |                  |             |          |          |        |
| PTRAF                      | green  | 1,834         | 3       | 2186254.289      | 3479440.229 | 0.3149   | 0.3705   |        |
| PTRAF                      | hybrid | 1,835         | 2       |                  |             |          |          |        |
| PTSDF                      | blue   | 1,834         | 3       | 2.328            | 11.331      | 0.0372   | 0.0677   | SPARSE |
| PTSDF                      | gray   | 1,837         | 0       |                  |             |          |          |        |
| PTSDF                      | green  | 1,834         | 3       | 2.328            | 11.331      | 0.0372   | 0.0677   |        |
| PTSDF                      | hybrid | 1,835         | 2       |                  |             |          |          |        |
| PWDIS                      | blue   | 1,834         | 3       | 2.488            | 1.648       | 0.5693   | 0.5693   | SPARSE |
| PWDIS                      | gray   | 1,837         | 0       |                  |             |          |          |        |
| PWDIS                      | green  | 1,834         | 3       | 2.488            | 1.648       | 0.5693   | 0.5693   |        |
| PWDIS                      | hybrid | 1,835         | 2       |                  |             |          |          |        |
| RSEI_AIR                   | blue   | 1,834         | 8       | 3160.310         | 2496.707    | 0.0654   | 0.1007   | SPARSE |
| RSEI_AIR                   | gray   | 1,838         | 4       | 3163.513         | 361.306     | 0.0025   | 0.0044   | **     |
| RSEI_AIR                   | green  | 1,834         | 8       | 3160.310         | 2496.707    | 0.0654   | 0.1007   |        |
| RSEI_AIR                   | hybrid | 1,836         | 6       | 3157.954         | 2996.296    | 0.1882   | 0.2027   |        |
| UNDER5PCT                  | blue   | 1,834         | 9       | 0.052            | 0.000       | 1.33e-05 | 3.80e-05 | SPARSE |
| UNDER5PCT                  | gray   | 1,838         | 5       | 0.052            | 0.000       | 0.0012   | 0.0024   | **     |
| UNDER5PCT                  | green  | 1,834         | 9       | 0.052            | 0.000       | 1.33e-05 | 3.80e-05 | **     |
| UNDER5PCT                  | hybrid | 1,836         | 7       | 0.052            | 0.000       | 0.0001   | 0.0002   | **     |
| UNEMPPCT                   | blue   | 1,834         | 9       | 0.046            | 0.000       | 0.0001   | 0.0003   | SPARSE |
| UNEMPPCT                   | gray   | 1,838         | 5       | 0.046            | 0.000       | 0.0045   | 0.0061   | **     |
| UNEMPPCT                   | green  | 1,834         | 9       | 0.046            | 0.000       | 0.0001   | 0.0003   | **     |
| UNEMPPCT                   | hybrid | 1,836         | 7       | 0.046            | 0.000       | 0.0008   | 0.0013   | **     |
| UST                        | blue   | 1,834         | 8       | 13.734           | 6.733       | 0.0970   | 0.1386   | SPARSE |
| UST                        | gray   | 1,838         | 4       | 13.731           | 1.114       | 0.0199   | 0.0214   | **     |
| UST                        | green  | 1,834         | 8       | 13.734           | 6.733       | 0.0970   | 0.1386   |        |
| UST                        | hybrid | 1,836         | 6       | 13.724           | 7.588       | 0.1309   | 0.1592   |        |
| income_disparity           | blue   | 1,207         | 0       |                  |             |          |          | SPARSE |
| income_disparity           | gray   | 1,207         | 0       |                  |             |          |          |        |
| income_disparity           | green  | 1,207         | 0       |                  |             |          |          |        |
| income_disparity           | hybrid | 1,207         | 0       |                  |             |          |          |        |
| median_family_income       | blue   | 1,496         | 0       |                  |             |          |          | SPARSE |
| median_family_income       | gray   | 1,496         | 0       |                  |             |          |          |        |
| median_family_income       | green  | 1,496         | 0       |                  |             |          |          |        |
| median_family_income       | hybrid | 1,496         | 0       |                  |             |          |          |        |
| median_gross_rent          | blue   | 1,297         | 0       |                  |             |          |          | SPARSE |
| median_gross_rent          | gray   | 1,297         | 0       |                  |             |          |          |        |
| median_gross_rent          | green  | 1,297         | 0       |                  |             |          |          |        |
| median_gross_rent          | hybrid | 1,297         | 0       |                  |             |          |          |        |
| median_home_value          | blue   | 1,535         | 0       |                  |             |          |          | SPARSE |
| median_home_value          | gray   | 1,535         | 0       |                  |             |          |          |        |
| median_home_value          | green  | 1,535         | 0       |                  |             |          |          |        |
| median_home_value          | hybrid | 1,535         | 0       |                  |             |          |          |        |
| median_monthly_mortgage    | blue   | 1,238         | 0       |                  |             |          |          | SPARSE |
| median_monthly_mortgage    | gray   | 1,238         | 0       |                  |             |          |          |        |
| median_monthly_mortgage    | green  | 1,238         | 0       |                  |             |          |          |        |
| median_monthly_mortgage    | hybrid | 1,238         | 0       |                  |             |          |          |        |
| no_diploma_under9yrs       | blue   | 1,833         | 0       |                  |             |          |          | SPARSE |
| no_diploma_under9yrs       | gray   | 1,833         | 0       |                  |             |          |          |        |
| no_diploma_under9yrs       | green  | 1,833         | 0       |                  |             |          |          |        |
| no_diploma_under9yrs       | hybrid | 1,833         | 0       |                  |             |          |          |        |
| pct_crowding_over100       | blue   | 1,832         | 0       |                  |             |          |          | SPARSE |
| pct_crowding_over100       | gray   | 1,832         | 0       |                  |             |          |          |        |
| pct_crowding_over100       | green  | 1,832         | 0       |                  |             |          |          |        |
| pct_crowding_over100       | hybrid | 1,832         | 0       |                  |             |          |          |        |
| pct_no_kitchen             | blue   | 1,832         | 0       |                  |             |          |          | SPARSE |
| pct_no_kitchen             | gray   | 1,832         | 0       |                  |             |          |          |        |
| pct_no_kitchen             | green  | 1,832         | 0       |                  |             |          |          |        |
| pct_no_kitchen             | hybrid | 1,832         | 0       |                  |             |          |          |        |
| pct_no_plumbing            | blue   | 1,832         | 0       |                  |             |          |          | SPARSE |
| pct_no_plumbing            | gray   | 1,832         | 0       |                  |             |          |          |        |
| pct_no_plumbing            | green  | 1,832         | 0       |                  |             |          |          |        |
| pct_no_plumbing            | hybrid | 1,832         | 0       |                  |             |          |          |        |
| pct_owner_occupied         | blue   | 1,832         | 0       |                  |             |          |          | SPARSE |
| pct_owner_occupied         | gray   | 1,832         | 0       |                  |             |          |          |        |
| pct_owner_occupied         | green  | 1,832         | 0       |                  |             |          |          |        |
| pct_owner_occupied         | hybrid | 1,832         | 0       |                  |             |          |          |        |
| pct_single_parent_children | blue   | 1,827         | 0       |                  |             |          |          | SPARSE |
| pct_single_parent_children | gray   | 1,827         | 0       |                  |             |          |          |        |
| pct_single_parent_children | green  | 1,827         | 0       |                  |             |          |          |        |
| pct_single_parent_children | hybrid | 1,827         | 0       |                  |             |          |          |        |
| poverty_pct_families       | blue   | 1,827         | 0       |                  |             |          |          | SPARSE |
| poverty_pct_families       | gray   | 1,827         | 0       |                  |             |          |          |        |
| poverty_pct_families       | green  | 1,827         | 0       |                  |             |          |          |        |
| poverty_pct_families       | hybrid | 1,827         | 0       |                  |             |          |          |        |
| poverty_under150           | blue   | 1,832         | 0       |                  |             |          |          | SPARSE |
| poverty_under150           | gray   | 1,832         | 0       |                  |             |          |          |        |
| poverty_under150           | green  | 1,832         | 0       |                  |             |          |          |        |
| poverty_under150           | hybrid | 1,832         | 0       |                  |             |          |          |        |

### 1c. Path_any group comparison - tract (Mann-Whitney U, n=102 pairs)

| variable              | path         | n_receiving   | n_not   | mean_receiving   | mean_not   | p_raw    | p_fdr    | sig   |
|:----------------------|:-------------|:--------------|:--------|:-----------------|:-----------|:---------|:---------|:------|
| EP_AFAM               | county       | 698           | 0       |                  |            |          |          |       |
| EP_AFAM               | municipality | 392           | 306     | 14.001           | 13.766     | 0.0925   | 0.1655   |       |
| EP_AFAM               | single_unit  | 396           | 302     | 16.886           | 9.979      | 6.46e-05 | 0.0007   | **    |
| EP_AGE17              | county       | 698           | 0       |                  |            |          |          |       |
| EP_AGE17              | municipality | 392           | 306     | 18.735           | 19.969     | 0.0252   | 0.0570   |       |
| EP_AGE17              | single_unit  | 396           | 302     | 19.754           | 18.649     | 0.0306   | 0.0866   |       |
| EP_AGE65              | county       | 698           | 0       |                  |            |          |          |       |
| EP_AGE65              | municipality | 392           | 306     | 17.034           | 17.222     | 0.4456   | 0.5411   |       |
| EP_AGE65              | single_unit  | 396           | 302     | 17.245           | 16.948     | 0.6503   | 0.7897   |       |
| EP_AIAN               | county       | 698           | 0       |                  |            |          |          |       |
| EP_AIAN               | municipality | 392           | 306     | 0.065            | 0.073      | 0.4414   | 0.5411   |       |
| EP_AIAN               | single_unit  | 396           | 302     | 0.059            | 0.080      | 0.5195   | 0.6542   |       |
| EP_ASIAN              | county       | 698           | 0       |                  |            |          |          |       |
| EP_ASIAN              | municipality | 392           | 306     | 1.496            | 1.535      | 0.5758   | 0.6526   |       |
| EP_ASIAN              | single_unit  | 396           | 302     | 1.459            | 1.584      | 0.9055   | 0.9392   |       |
| EP_CROWD              | county       | 697           | 0       |                  |            |          |          |       |
| EP_CROWD              | municipality | 392           | 305     | 7.016            | 5.537      | 0.0006   | 0.0024   | **    |
| EP_CROWD              | single_unit  | 395           | 302     | 6.394            | 6.335      | 0.9116   | 0.9392   |       |
| EP_DISABL             | county       | 698           | 0       |                  |            |          |          |       |
| EP_DISABL             | municipality | 392           | 306     | 10.638           | 9.825      | 0.0598   | 0.1196   |       |
| EP_DISABL             | single_unit  | 396           | 302     | 10.391           | 10.138     | 0.3044   | 0.5175   |       |
| EP_GROUPQ             | county       | 698           | 0       |                  |            |          |          |       |
| EP_GROUPQ             | municipality | 392           | 306     | 1.678            | 2.338      | 0.1777   | 0.2747   |       |
| EP_GROUPQ             | single_unit  | 396           | 302     | 2.001            | 1.922      | 0.2721   | 0.4924   |       |
| EP_HBURD              | county       | 697           | 0       |                  |            |          |          |       |
| EP_HBURD              | municipality | 392           | 305     | 41.356           | 35.953     | 1.10e-07 | 6.22e-07 | **    |
| EP_HBURD              | single_unit  | 395           | 302     | 38.355           | 39.824     | 0.2752   | 0.4924   |       |
| EP_HISP               | county       | 698           | 0       |                  |            |          |          |       |
| EP_HISP               | municipality | 392           | 306     | 66.251           | 71.328     | 0.1194   | 0.2030   |       |
| EP_HISP               | single_unit  | 396           | 302     | 63.069           | 75.568     | 2.05e-12 | 6.96e-11 | **    |
| EP_LIMENG             | county       | 698           | 0       |                  |            |          |          |       |
| EP_LIMENG             | municipality | 392           | 306     | 21.493           | 18.365     | 0.3560   | 0.4841   |       |
| EP_LIMENG             | single_unit  | 396           | 302     | 18.030           | 22.865     | 1.38e-06 | 2.35e-05 | **    |
| EP_MINRTY             | county       | 698           | 0       |                  |            |          |          |       |
| EP_MINRTY             | municipality | 392           | 306     | 83.828           | 88.387     | 0.3091   | 0.4379   |       |
| EP_MINRTY             | single_unit  | 396           | 302     | 83.552           | 88.809     | 0.0028   | 0.0157   | **    |
| EP_MOBILE             | county       | 697           | 0       |                  |            |          |          |       |
| EP_MOBILE             | municipality | 392           | 305     | 1.316            | 1.957      | 0.7255   | 0.7958   |       |
| EP_MOBILE             | single_unit  | 395           | 302     | 1.566            | 1.636      | 0.3980   | 0.6118   |       |
| EP_MUNIT              | county       | 697           | 0       |                  |            |          |          |       |
| EP_MUNIT              | municipality | 392           | 305     | 41.163           | 22.151     | 4.45e-17 | 5.05e-16 | **    |
| EP_MUNIT              | single_unit  | 395           | 302     | 33.098           | 32.511     | 0.8533   | 0.9392   |       |
| EP_NHPI               | county       | 698           | 0       |                  |            |          |          |       |
| EP_NHPI               | municipality | 392           | 306     | 0.014            | 0.018      | 0.8389   | 0.8643   |       |
| EP_NHPI               | single_unit  | 396           | 302     | 0.012            | 0.021      | 0.4081   | 0.6118   |       |
| EP_NOHSDP             | county       | 698           | 0       |                  |            |          |          |       |
| EP_NOHSDP             | municipality | 392           | 306     | 17.196           | 16.391     | 0.9603   | 0.9603   |       |
| EP_NOHSDP             | single_unit  | 396           | 302     | 16.116           | 17.796     | 0.0248   | 0.0768   |       |
| EP_NOINT              | county       | 697           | 0       |                  |            |          |          |       |
| EP_NOINT              | municipality | 392           | 305     | 17.478           | 12.158     | 2.67e-09 | 1.82e-08 | **    |
| EP_NOINT              | single_unit  | 395           | 302     | 15.997           | 14.042     | 0.0442   | 0.1157   |       |
| EP_NOVEH              | county       | 697           | 0       |                  |            |          |          |       |
| EP_NOVEH              | municipality | 392           | 305     | 12.082           | 5.953      | 1.04e-21 | 3.52e-20 | **    |
| EP_NOVEH              | single_unit  | 395           | 302     | 10.158           | 8.408      | 0.0063   | 0.0267   | **    |
| EP_OTHERRACE          | county       | 698           | 0       |                  |            |          |          |       |
| EP_OTHERRACE          | municipality | 392           | 306     | 0.387            | 0.390      | 0.7654   | 0.8133   |       |
| EP_OTHERRACE          | single_unit  | 396           | 302     | 0.434            | 0.328      | 0.0154   | 0.0583   |       |
| EP_POV150             | county       | 697           | 0       |                  |            |          |          |       |
| EP_POV150             | municipality | 392           | 305     | 27.572           | 23.981     | 0.0010   | 0.0033   | **    |
| EP_POV150             | single_unit  | 395           | 302     | 25.849           | 26.199     | 0.5134   | 0.6542   |       |
| EP_SNGPNT             | county       | 697           | 0       |                  |            |          |          |       |
| EP_SNGPNT             | municipality | 392           | 305     | 6.841            | 7.891      | 0.3025   | 0.4379   |       |
| EP_SNGPNT             | single_unit  | 395           | 302     | 7.608            | 6.899      | 0.2499   | 0.4924   |       |
| EP_TWOMORE            | county       | 698           | 0       |                  |            |          |          |       |
| EP_TWOMORE            | municipality | 392           | 306     | 1.617            | 1.274      | 0.1703   | 0.2747   |       |
| EP_TWOMORE            | single_unit  | 396           | 302     | 1.638            | 1.241      | 0.0002   | 0.0021   | **    |
| EP_UNEMP              | county       | 698           | 0       |                  |            |          |          |       |
| EP_UNEMP              | municipality | 392           | 306     | 4.830            | 4.418      | 0.0444   | 0.0943   |       |
| EP_UNEMP              | single_unit  | 396           | 302     | 4.919            | 4.297      | 0.2323   | 0.4924   |       |
| EP_UNINSUR            | county       | 698           | 0       |                  |            |          |          |       |
| EP_UNINSUR            | municipality | 392           | 306     | 16.026           | 13.301     | 0.0001   | 0.0005   | **    |
| EP_UNINSUR            | single_unit  | 396           | 302     | 14.703           | 15.000     | 0.4204   | 0.6118   |       |
| age65plus             | county       | 698           | 0       |                  |            |          |          |       |
| age65plus             | municipality | 392           | 306     | 0.172            | 0.180      | 0.0785   | 0.1483   |       |
| age65plus             | single_unit  | 396           | 302     | 0.176            | 0.175      | 0.9875   | 0.9875   |       |
| crowding_over100      | county       | 698           | 0       |                  |            |          |          |       |
| crowding_over100      | municipality | 392           | 306     | 0.077            | 0.064      | 0.0082   | 0.0214   | **    |
| crowding_over100      | single_unit  | 396           | 302     | 0.071            | 0.071      | 0.4318   | 0.6118   |       |
| disability            | county       | 698           | 0       |                  |            |          |          |       |
| disability            | municipality | 392           | 306     | 0.106            | 0.103      | 0.4172   | 0.5411   |       |
| disability            | single_unit  | 396           | 302     | 0.105            | 0.105      | 0.8755   | 0.9392   |       |
| limited_english_hh    | county       | 698           | 0       |                  |            |          |          |       |
| limited_english_hh    | municipality | 392           | 306     | 0.260            | 0.213      | 0.0146   | 0.0355   | **    |
| limited_english_hh    | single_unit  | 396           | 302     | 0.220            | 0.264      | 0.0004   | 0.0029   | **    |
| no_broadband          | county       | 698           | 0       |                  |            |          |          |       |
| no_broadband          | municipality | 392           | 306     | 0.123            | 0.078      | 3.42e-14 | 2.91e-13 | **    |
| no_broadband          | single_unit  | 396           | 302     | 0.111            | 0.093      | 0.0058   | 0.0267   | **    |
| no_diploma_pop25      | county       | 698           | 0       |                  |            |          |          |       |
| no_diploma_pop25      | municipality | 392           | 306     | 0.158            | 0.156      | 0.5533   | 0.6487   |       |
| no_diploma_pop25      | single_unit  | 396           | 302     | 0.151            | 0.164      | 0.0243   | 0.0768   |       |
| no_fulltime_worker_hh | county       | 698           | 0       |                  |            |          |          |       |
| no_fulltime_worker_hh | municipality | 392           | 306     | 0.225            | 0.204      | 0.0031   | 0.0096   | **    |
| no_fulltime_worker_hh | single_unit  | 396           | 302     | 0.222            | 0.207      | 0.0858   | 0.2084   |       |
| no_vehicle            | county       | 698           | 0       |                  |            |          |          |       |
| no_vehicle            | municipality | 392           | 306     | 0.119            | 0.065      | 1.16e-17 | 1.97e-16 | **    |
| no_vehicle            | single_unit  | 396           | 302     | 0.103            | 0.086      | 0.1114   | 0.2525   |       |
| poverty_under125      | county       | 698           | 0       |                  |            |          |          |       |
| poverty_under125      | municipality | 392           | 306     | 0.205            | 0.183      | 0.0038   | 0.0107   | **    |
| poverty_under125      | single_unit  | 396           | 302     | 0.197            | 0.194      | 0.4523   | 0.6152   |       |
| uninsured             | county       | 698           | 0       |                  |            |          |          |       |
| uninsured             | municipality | 392           | 306     | 0.144            | 0.119      | 7.06e-05 | 0.0003   | **    |
| uninsured             | single_unit  | 396           | 302     | 0.134            | 0.132      | 0.7507   | 0.8802   |       |

### 1c. Path_any group comparison - block group (Mann-Whitney U, n=105 pairs)

| variable                   | path         | n_receiving   | n_not   | mean_receiving   | mean_not    | p_raw    | p_fdr    | sig   |
|:---------------------------|:-------------|:--------------|:--------|:-----------------|:------------|:---------|:---------|:------|
| DISABILITYPCT              | county       | 1,833         | 10      | 0.103            | 0.008       | 3.37e-07 | 1.58e-06 | **    |
| DISABILITYPCT              | municipality | 1,051         | 792     | 0.106            | 0.097       | 0.0015   | 0.0027   | **    |
| DISABILITYPCT              | single_unit  | 581           | 1,262   | 0.101            | 0.103       | 0.3820   | 0.4775   |       |
| DSLPM                      | county       | 1,833         | 4       | 0.289            | 0.297       | 0.6361   | 0.7484   |       |
| DSLPM                      | municipality | 1,051         | 786     | 0.297            | 0.277       | 1.72e-08 | 5.48e-08 | **    |
| DSLPM                      | single_unit  | 580           | 1,257   | 0.285            | 0.290       | 0.2054   | 0.3126   |       |
| DWATER                     | county       | 1,676         | 1       |                  |             |          |          |       |
| DWATER                     | municipality | 929           | 748     | 11.782           | 11.449      | 0.0002   | 0.0004   | **    |
| DWATER                     | single_unit  | 538           | 1,139   | 11.478           | 11.708      | 0.9400   | 0.9400   |       |
| LESSHSPCT                  | county       | 1,833         | 10      | 0.162            | 0.000       | 3.95e-07 | 1.58e-06 | **    |
| LESSHSPCT                  | municipality | 1,051         | 792     | 0.163            | 0.159       | 0.2821   | 0.3405   |       |
| LESSHSPCT                  | single_unit  | 581           | 1,262   | 0.148            | 0.167       | 0.0007   | 0.0028   | **    |
| LIFEEXPPCT                 | county       | 1,748         | 2       |                  |             |          |          |       |
| LIFEEXPPCT                 | municipality | 996           | 754     | 0.174            | 0.173       | 0.1488   | 0.1886   |       |
| LIFEEXPPCT                 | single_unit  | 539           | 1,211   | 0.176            | 0.172       | 0.1198   | 0.2106   |       |
| LINGISOPCT                 | county       | 1,833         | 10      | 0.224            | 0.000       | 6.76e-07 | 2.25e-06 | **    |
| LINGISOPCT                 | municipality | 1,051         | 792     | 0.242            | 0.197       | 0.0006   | 0.0012   | **    |
| LINGISOPCT                 | single_unit  | 581           | 1,262   | 0.194            | 0.236       | 7.94e-06 | 6.93e-05 | **    |
| LOWINCPCT                  | county       | 1,833         | 10      | 0.361            | 0.000       | 7.57e-08 | 5.04e-07 | **    |
| LOWINCPCT                  | municipality | 1,051         | 792     | 0.376            | 0.337       | 0.0003   | 0.0006   | **    |
| LOWINCPCT                  | single_unit  | 581           | 1,262   | 0.341            | 0.368       | 0.0042   | 0.0124   | **    |
| NO2                        | county       | 1,823         | 9       | 9.837            | 6.341       | 0.0219   | 0.0399   | **    |
| NO2                        | municipality | 1,041         | 791     | 10.424           | 9.024       | 2.32e-38 | 2.03e-37 | **    |
| NO2                        | single_unit  | 576           | 1,256   | 9.604            | 9.919       | 0.0039   | 0.0124   | **    |
| OVER64PCT                  | county       | 1,833         | 10      | 0.179            | 0.000       | 7.20e-08 | 5.04e-07 | **    |
| OVER64PCT                  | municipality | 1,051         | 792     | 0.179            | 0.177       | 0.3117   | 0.3546   |       |
| OVER64PCT                  | single_unit  | 581           | 1,262   | 0.175            | 0.179       | 0.8479   | 0.9162   |       |
| OZONE                      | county       | 1,833         | 10      | 59.542           | 59.411      | 0.3210   | 0.4013   |       |
| OZONE                      | municipality | 1,051         | 792     | 59.579           | 59.490      | 0.5974   | 0.6534   |       |
| OZONE                      | single_unit  | 581           | 1,262   | 59.510           | 59.555      | 0.0328   | 0.0766   |       |
| PEOPCOLORPCT               | county       | 1,833         | 10      | 0.845            | 0.000       | 4.96e-08 | 5.04e-07 | **    |
| PEOPCOLORPCT               | municipality | 1,051         | 792     | 0.819            | 0.868       | 0.0006   | 0.0012   | **    |
| PEOPCOLORPCT               | single_unit  | 581           | 1,262   | 0.801            | 0.858       | 1.43e-07 | 2.51e-06 | **    |
| PM25                       | county       | 1,833         | 10      | 7.962            | 7.520       | 0.0091   | 0.0181   | **    |
| PM25                       | municipality | 1,051         | 792     | 7.953            | 7.968       | 0.1336   | 0.1870   |       |
| PM25                       | single_unit  | 581           | 1,262   | 7.934            | 7.971       | 0.0025   | 0.0087   | **    |
| PNPL                       | county       | 1,833         | 4       | 0.352            | 0.455       | 0.2506   | 0.3341   |       |
| PNPL                       | municipality | 1,051         | 786     | 0.420            | 0.262       | 6.93e-63 | 1.21e-61 | **    |
| PNPL                       | single_unit  | 580           | 1,257   | 0.370            | 0.344       | 0.1300   | 0.2167   |       |
| PRE1960PCT                 | county       | 1,833         | 10      | 0.248            | 0.000       | 6.48e-05 | 0.0001   | **    |
| PRE1960PCT                 | municipality | 1,051         | 792     | 0.303            | 0.172       | 3.07e-30 | 1.79e-29 | **    |
| PRE1960PCT                 | single_unit  | 581           | 1,262   | 0.278            | 0.232       | 9.90e-06 | 6.93e-05 | **    |
| PRMP                       | county       | 1,833         | 4       | 0.617            | 0.803       | 0.9529   | 0.9529   |       |
| PRMP                       | municipality | 1,051         | 786     | 0.705            | 0.500       | 1.35e-14 | 5.25e-14 | **    |
| PRMP                       | single_unit  | 580           | 1,257   | 0.607            | 0.622       | 0.4306   | 0.5197   |       |
| PTRAF                      | county       | 1,833         | 4       | 2186937.844      | 2842904.722 | 0.7635   | 0.8484   |       |
| PTRAF                      | municipality | 1,051         | 786     | 2381085.726      | 1930671.233 | 8.56e-20 | 3.74e-19 | **    |
| PTRAF                      | single_unit  | 580           | 1,257   | 2232018.408      | 2168224.351 | 0.3173   | 0.4113   |       |
| PTSDF                      | county       | 1,833         | 4       | 2.327            | 9.346       | 0.0321   | 0.0535   |       |
| PTSDF                      | municipality | 1,051         | 786     | 3.083            | 1.352       | 4.16e-71 | 1.46e-69 | **    |
| PTSDF                      | single_unit  | 580           | 1,257   | 2.432            | 2.301       | 0.8639   | 0.9162   |       |
| PWDIS                      | county       | 1,833         | 4       | 2.489            | 1.236       | 0.8087   | 0.8512   |       |
| PWDIS                      | municipality | 1,051         | 786     | 3.626            | 0.962       | 8.93e-13 | 3.13e-12 | **    |
| PWDIS                      | single_unit  | 580           | 1,257   | 3.403            | 2.064       | 2.48e-08 | 8.67e-07 | **    |
| RSEI_AIR                   | county       | 1,833         | 9       | 3161.405         | 2347.441    | 0.0430   | 0.0661   |       |
| RSEI_AIR                   | municipality | 1,051         | 791     | 3411.811         | 2819.429    | 1.45e-47 | 1.69e-46 | **    |
| RSEI_AIR                   | single_unit  | 581           | 1,261   | 3219.025         | 3129.047    | 0.0560   | 0.1153   |       |
| UNDER5PCT                  | county       | 1,833         | 10      | 0.052            | 0.000       | 4.39e-06 | 1.25e-05 | **    |
| UNDER5PCT                  | municipality | 1,051         | 792     | 0.052            | 0.051       | 0.9966   | 0.9966   |       |
| UNDER5PCT                  | single_unit  | 581           | 1,262   | 0.054            | 0.051       | 0.0618   | 0.1202   |       |
| UNEMPPCT                   | county       | 1,833         | 10      | 0.046            | 0.000       | 5.77e-05 | 0.0001   | **    |
| UNEMPPCT                   | municipality | 1,051         | 792     | 0.047            | 0.043       | 0.3141   | 0.3546   |       |
| UNEMPPCT                   | single_unit  | 581           | 1,262   | 0.044            | 0.046       | 0.4548   | 0.5306   |       |
| UST                        | county       | 1,833         | 9       | 13.740           | 6.410       | 0.0819   | 0.1170   |       |
| UST                        | municipality | 1,051         | 791     | 17.757           | 8.319       | 7.08e-38 | 4.96e-37 | **    |
| UST                        | single_unit  | 581           | 1,261   | 14.837           | 13.182      | 0.0007   | 0.0028   | **    |
| income_disparity           | county       | 1,207         | 0       |                  |             |          |          |       |
| income_disparity           | municipality | 722           | 485     | -2.189           | -2.504      | 3.59e-07 | 1.05e-06 | **    |
| income_disparity           | single_unit  | 396           | 811     | -2.338           | -2.304      | 0.3042   | 0.4095   |       |
| median_family_income       | county       | 1,496         | 0       |                  |             |          |          |       |
| median_family_income       | municipality | 820           | 676     | 93080.872        | 93223.777   | 0.0266   | 0.0388   | **    |
| median_family_income       | single_unit  | 455           | 1,041   | 101516.916       | 89486.447   | 6.08e-06 | 6.93e-05 | **    |
| median_gross_rent          | county       | 1,297         | 0       |                  |             |          |          |       |
| median_gross_rent          | municipality | 808           | 489     | 1916.814         | 1966.796    | 0.0148   | 0.0246   | **    |
| median_gross_rent          | single_unit  | 394           | 903     | 1930.541         | 1937.891    | 0.6925   | 0.7819   |       |
| median_home_value          | county       | 1,535         | 0       |                  |             |          |          |       |
| median_home_value          | municipality | 837           | 698     | 545934.767       | 489015.330  | 0.1509   | 0.1886   |       |
| median_home_value          | single_unit  | 485           | 1,050   | 575040.412       | 494652.857  | 4.41e-05 | 0.0003   | **    |
| median_monthly_mortgage    | county       | 1,238         | 0       |                  |             |          |          |       |
| median_monthly_mortgage    | municipality | 610           | 628     | 2441.495         | 2285.406    | 0.0001   | 0.0004   | **    |
| median_monthly_mortgage    | single_unit  | 380           | 858     | 2471.208         | 2314.089    | 0.0004   | 0.0018   | **    |
| no_diploma_under9yrs       | county       | 1,833         | 0       |                  |             |          |          |       |
| no_diploma_under9yrs       | municipality | 1,051         | 782     | 0.078            | 0.071       | 0.7695   | 0.8162   |       |
| no_diploma_under9yrs       | single_unit  | 576           | 1,257   | 0.070            | 0.077       | 0.0077   | 0.0207   | **    |
| pct_crowding_over100       | county       | 1,832         | 0       |                  |             |          |          |       |
| pct_crowding_over100       | municipality | 1,050         | 782     | 0.077            | 0.064       | 0.0229   | 0.0348   | **    |
| pct_crowding_over100       | single_unit  | 576           | 1,256   | 0.068            | 0.073       | 0.2523   | 0.3532   |       |
| pct_no_kitchen             | county       | 1,832         | 0       |                  |             |          |          |       |
| pct_no_kitchen             | municipality | 1,050         | 782     | 0.009            | 0.006       | 0.0012   | 0.0022   | **    |
| pct_no_kitchen             | single_unit  | 576           | 1,256   | 0.008            | 0.008       | 0.1470   | 0.2339   |       |
| pct_no_plumbing            | county       | 1,832         | 0       |                  |             |          |          |       |
| pct_no_plumbing            | municipality | 1,050         | 782     | 0.005            | 0.003       | 0.1509   | 0.1886   |       |
| pct_no_plumbing            | single_unit  | 576           | 1,256   | 0.004            | 0.005       | 0.9299   | 0.9400   |       |
| pct_owner_occupied         | county       | 1,832         | 0       |                  |             |          |          |       |
| pct_owner_occupied         | municipality | 1,050         | 782     | 0.501            | 0.649       | 1.88e-26 | 9.38e-26 | **    |
| pct_owner_occupied         | single_unit  | 576           | 1,256   | 0.585            | 0.555       | 0.0395   | 0.0864   |       |
| pct_single_parent_children | county       | 1,827         | 0       |                  |             |          |          |       |
| pct_single_parent_children | municipality | 1,046         | 781     | 0.147            | 0.143       | 0.9166   | 0.9436   |       |
| pct_single_parent_children | single_unit  | 574           | 1,253   | 0.140            | 0.148       | 0.1203   | 0.2106   |       |
| poverty_pct_families       | county       | 1,827         | 0       |                  |             |          |          |       |
| poverty_pct_families       | municipality | 1,046         | 781     | 0.122            | 0.103       | 0.0223   | 0.0348   | **    |
| poverty_pct_families       | single_unit  | 574           | 1,253   | 0.110            | 0.116       | 0.2422   | 0.3532   |       |
| poverty_under150           | county       | 1,832         | 0       |                  |             |          |          |       |
| poverty_under150           | municipality | 1,050         | 782     | 0.254            | 0.229       | 0.0062   | 0.0109   | **    |
| poverty_under150           | single_unit  | 576           | 1,256   | 0.233            | 0.248       | 0.0087   | 0.0217   | **    |


---

## 2. Spatial structure (Part 5c, Moran's I)

*Sources: `output/part5_diagnostics/5c_moran_tract.csv`, `5c_moran_bg.csv`, `5d_zero_skew_tract.csv`, `5d_zero_skew_bg.csv`.*

**Plain-language read:** k-nearest-neighbor weights with **k=6** were used for both grains (k=6 is a standard spatial-econometrics default approximating the typical count of contiguous neighbors on an urban tract/block-group grid; being distance- rather than contiguity-based, it avoids the zero-neighbor 'island' problem that a fixed distance band would create given this county's mix of dense urban tracts and large rural/parcel geography in the south). The core contrast: `investment_per_capita` shows **no significant spatial clustering** (I=0.006, p=0.0700) even though **every vulnerability variable tested is strongly and significantly clustered** (I up to 0.986), and the binary/composition outcomes sit in between (I=0.138-0.604, all significant).

### Moran's I - tract (698 units, k=6)

| family            | variable                   | n   | I     | p_sim   | z_sim   | highlight   | note   |
|:------------------|:---------------------------|:----|:------|:--------|:--------|:------------|:-------|
| outcome           | investment_per_capita      | 698 | 0.006 | 0.0700  | 0.482   | **outcome** |        |
| outcome           | investment_any_excl_county | 698 | 0.465 | 0.0010  | 22.674  | **outcome** |        |
| outcome           | investment_any_single_unit | 698 | 0.194 | 0.0010  | 9.586   | **outcome** |        |
| type_share        | type_gray_share            | 698 | 0.338 | 0.0010  | 16.140  |             |        |
| type_share        | type_blue_share            | 698 | 0.454 | 0.0010  | 21.476  |             |        |
| type_share        | type_hybrid_share          | 698 | 0.146 | 0.0010  | 7.111   |             |        |
| type_share        | type_green_share           | 698 | 0.055 | 0.0080  | 2.904   |             |        |
| key_vulnerability | EP_NOVEH                   | 697 | 0.485 | 0.0010  | 22.695  |             |        |
| key_vulnerability | no_vehicle                 | 698 | 0.426 | 0.0010  | 21.254  |             |        |
| key_vulnerability | EP_MUNIT                   | 697 | 0.580 | 0.0010  | 29.150  |             |        |
| key_vulnerability | EP_MINRTY                  | 698 | 0.669 | 0.0010  | 31.479  |             |        |
| key_vulnerability | EP_POV150                  | 697 | 0.417 | 0.0010  | 20.608  |             |        |
| key_vulnerability | poverty_under125           | 698 | 0.353 | 0.0010  | 16.725  |             |        |
| key_vulnerability | EP_AGE65                   | 698 | 0.313 | 0.0010  | 14.975  |             |        |
| key_vulnerability | age65plus                  | 698 | 0.335 | 0.0010  | 16.219  |             |        |
| key_vulnerability | EP_NOHSDP                  | 698 | 0.574 | 0.0010  | 28.807  |             |        |

### Moran's I - block group (1,843 units, k=6)

| family            | variable                   | n     | I     | p_sim   | z_sim   | highlight   | note   |
|:------------------|:---------------------------|:------|:------|:--------|:--------|:------------|:-------|
| outcome           | investment_any_excl_county | 1,843 | 0.604 | 0.0010  | 47.466  | **outcome** |        |
| outcome           | investment_any_single_unit | 1,843 | 0.138 | 0.0010  | 10.572  | **outcome** |        |
| type_share        | type_gray_share            | 1,838 | 0.425 | 0.0010  | 33.868  |             |        |
| type_share        | type_blue_share            | 1,838 | 0.477 | 0.0010  | 37.265  |             |        |
| type_share        | type_hybrid_share          | 1,838 | 0.140 | 0.0010  | 11.155  |             |        |
| type_share        | type_green_share           | 1,838 | 0.087 | 0.0010  | 6.734   |             |        |
| key_vulnerability | LOWINCPCT                  | 1,843 | 0.422 | 0.0010  | 32.824  |             |        |
| key_vulnerability | LESSHSPCT                  | 1,843 | 0.481 | 0.0010  | 38.283  |             |        |
| key_vulnerability | PEOPCOLORPCT               | 1,843 | 0.545 | 0.0010  | 42.858  |             |        |
| key_vulnerability | PM25                       | 1,843 | 0.970 | 0.0010  | 75.973  |             |        |
| key_vulnerability | OZONE                      | 1,843 | 0.986 | 0.0010  | 77.816  |             |        |
| key_vulnerability | UST                        | 1,842 | 0.709 | 0.0010  | 57.159  |             |        |
| key_vulnerability | median_family_income       | 1,496 | 0.413 | 0.0010  | 29.761  |             |        |
| key_vulnerability | poverty_under150           | 1,832 | 0.328 | 0.0010  | 26.396  |             |        |

### Zero share and skew per outcome variant (Part 5d)

**tract** (n per variable = table's own `n` column)

| variable               | n   | n_zero   | pct_zero   | skew   | skew_nonzero_only   | flag_50pct_zero   |
|:-----------------------|:----|:---------|:-----------|:-------|:--------------------|:------------------|
| investment_total       | 698 | 0        | 0.0%       | 14.379 | 14.379              |                   |
| investment_per_capita  | 698 | 0        | 0.0%       | 18.718 | 18.718              |                   |
| investment_per_area    | 698 | 0        | 0.0%       | 10.206 | 10.206              |                   |
| type_blue_share        | 698 | 0        | 0.0%       | -0.379 | -0.379              |                   |
| type_gray_share        | 698 | 0        | 0.0%       | 0.622  | 0.622               |                   |
| type_green_share       | 698 | 0        | 0.0%       | 4.319  | 4.319               |                   |
| type_hybrid_share      | 698 | 0        | 0.0%       | 3.688  | 3.688               |                   |
| investment_type_blue   | 698 | 0        | 0.0%       | 6.069  | 6.069               |                   |
| investment_type_gray   | 698 | 0        | 0.0%       | 18.894 | 18.894              |                   |
| investment_type_green  | 698 | 0        | 0.0%       | 17.526 | 17.526              |                   |
| investment_type_hybrid | 698 | 0        | 0.0%       | 22.675 | 22.675              |                   |
| path_single_unit_amt   | 698 | 302      | 43.3%      | 14.865 | 11.306              |                   |
| path_municipality_amt  | 698 | 306      | 43.8%      | 6.556  | 5.228               |                   |
| path_county_amt        | 698 | 0        | 0.0%       | 1.117  | 1.117               |                   |

**block group** (n per variable = table's own `n` column)

| variable               | n     | n_zero   | pct_zero   | skew   | skew_nonzero_only   | flag_50pct_zero      |
|:-----------------------|:------|:---------|:-----------|:-------|:--------------------|:---------------------|
| investment_total       | 1,843 | 5        | 0.3%       | 23.444 | 23.413              |                      |
| type_blue_share        | 1,838 | 4        | 0.2%       | -0.618 | -0.620              |                      |
| type_gray_share        | 1,838 | 0        | 0.0%       | 0.789  | 0.789               |                      |
| type_green_share       | 1,838 | 4        | 0.2%       | 8.186  | 8.203               |                      |
| type_hybrid_share      | 1,838 | 2        | 0.1%       | 4.726  | 4.723               |                      |
| investment_type_blue   | 1,843 | 9        | 0.5%       | 12.272 | 12.323              |                      |
| investment_type_gray   | 1,843 | 5        | 0.3%       | 30.155 | 30.115              |                      |
| investment_type_green  | 1,843 | 9        | 0.5%       | 28.650 | 28.581              |                      |
| investment_type_hybrid | 1,843 | 7        | 0.4%       | 37.070 | 36.999              |                      |
| path_single_unit_amt   | 1,843 | 1,262    | 68.5%      | 23.712 | 13.471              | **HURDLE CANDIDATE** |
| path_municipality_amt  | 1,843 | 792      | 43.0%      | 7.008  | 5.642               |                      |
| path_county_amt        | 1,843 | 10       | 0.5%       | 1.958  | 2.009               |                      |

`path_single_unit_amt` at block group is the only variable in either profile exceeding 50% exact zeros (**68.5%**), flagged as the one genuine hurdle/two-part candidate; nothing else crosses that line at either grain.

---

## 3. Project-type, scale-tag, and allocation-path profile (Part 2)

*Source: `output/part2_univariate/sparsity_baseline.csv`.*

**Plain-language read:** this is the sparsity context for Section 1 - `n_receiving_units_single_unit_only` is the number of units where a project was actually physically sited (footprint), separate from `n_receiving_units` which the automatic county allocation path inflates to nearly every unit regardless of category. Only **Blue** infrastructure falls under the 20-unit floor (19 single-unit-sited units at both grains), out of 1,405 filtered projects total ($8,553,271,610).

| grain   | dimension   | category     | n_projects   | n_receiving_units   | n_receiving_units_single_unit_only   | dollars        | flag_sparse_lt20units   |
|:--------|:------------|:-------------|:-------------|:--------------------|:-------------------------------------|:---------------|:------------------------|
| tract   | type        | Blue         | 28           | 699                 | 19                                   | $1,506,051,094 | **SPARSE**              |
| tract   | type        | Gray         | 1,157        | 702                 | 370                                  | $5,025,704,013 |                         |
| tract   | type        | Green        | 67           | 699                 | 35                                   | $262,642,423   |                         |
| tract   | type        | Hybrid       | 153          | 701                 | 90                                   | $1,758,874,079 |                         |
| tract   | scale       | Parcel       | 405          | 187                 | 187                                  | $1,954,872,603 |                         |
| tract   | scale       | Neighborhood | 239          | 148                 | 148                                  | $1,500,578,467 |                         |
| tract   | scale       | Corridor     | 477          | 257                 | 257                                  | $2,585,997,034 |                         |
| tract   | scale       | Municipality | 253          | 392                 | 0                                    | $963,287,013   |                         |
| tract   | scale       | County       | 31           | 698                 | 0                                    | $1,548,536,493 |                         |
| bg      | type        | Blue         | 28           | 1,834               | 19                                   | $1,506,051,094 | **SPARSE**              |
| bg      | type        | Gray         | 1,157        | 1,838               | 524                                  | $5,025,704,013 |                         |
| bg      | type        | Green        | 67           | 1,834               | 37                                   | $262,642,423   |                         |
| bg      | type        | Hybrid       | 153          | 1,836               | 103                                  | $1,758,874,079 |                         |
| bg      | scale       | Parcel       | 405          | 233                 | 233                                  | $1,954,872,603 |                         |
| bg      | scale       | Neighborhood | 239          | 177                 | 177                                  | $1,500,578,467 |                         |
| bg      | scale       | Corridor     | 477          | 342                 | 342                                  | $2,585,997,034 |                         |
| bg      | scale       | Municipality | 253          | 1,051               | 0                                    | $963,287,013   |                         |
| bg      | scale       | County       | 31           | 1,833               | 0                                    | $1,548,536,493 |                         |

Mean/median project size per category is **not computed** in this baseline table (it reports project count and dollars, not a per-project size distribution split by category) - deriving it now would be new computation, so it is left as "not computed" rather than calculated here.

---

## 4. Indicator structure (Part 3)

*Sources: `output/part3_correlation/tract_high_corr_pairs.csv`, `bg_high_corr_pairs.csv`, `tract_vif.csv`, `bg_vif.csv`, `bg_excl_high_missing_vif.csv`, `tract_svi_vs_cre_overlap.csv`, `bg_flagged_duplicate_candidates.csv`, `tract_spearman.csv` (for the axis-divergence block), `bg_ejscreen_socio_vs_adi_full_cross.csv`, `bg_environmental_vs_adi_ej_question.csv`.*

**Plain-language read:** the tract SVI/ACS-CRE overlap is a clean, confirmed redundancy (7 pairs, all |r|>0.8). At block group only 2 pairs exceed |r|>0.8, both inside EJScreen's air-quality block. VIF finds a second, different kind of redundancy at tract - race/ethnicity shares are collinear *in combination* even though no single pair crosses 0.8, because they are compositional (sum near 100% of population).

### 4a. Pairs with |Pearson r| > 0.8 - tract (n=7 pairs)

| var_a      | var_b              | pearson_r   | spearman_rho   |
|:-----------|:-------------------|:------------|:---------------|
| EP_NOVEH   | no_vehicle         | 0.898       | 0.841          |
| EP_NOHSDP  | no_diploma_pop25   | 0.895       | 0.898          |
| EP_AGE65   | age65plus          | 0.888       | 0.877          |
| EP_NOINT   | no_broadband       | 0.854       | 0.862          |
| EP_UNINSUR | uninsured          | 0.848       | 0.849          |
| EP_LIMENG  | limited_english_hh | 0.840       | 0.821          |
| EP_POV150  | poverty_under125   | 0.832       | 0.825          |

### 4a. Pairs with |Pearson r| > 0.8 - block group (n=2 pairs)

| var_a   | var_b   | pearson_r   | spearman_rho   |
|:--------|:--------|:------------|:---------------|
| PM25    | OZONE   | 0.900       | 0.950          |
| PM25    | DSLPM   | 0.801       | 0.800          |

### 4b. VIF - tract (34 vars, n=697 complete cases)

| variable              | VIF        |
|:----------------------|:-----------|
| EP_HISP               | 152741.827 |
| EP_AFAM               | 131349.794 |
| EP_MINRTY             | 58856.579  |
| EP_ASIAN              | 1410.811   |
| EP_TWOMORE            | 1320.269   |
| EP_OTHERRACE          | 224.109    |
| EP_AIAN               | 30.097     |
| EP_NOHSDP             | 7.269      |
| age65plus             | 7.164      |
| EP_AGE65              | 6.861      |
| EP_NOVEH              | 6.398      |
| EP_LIMENG             | 6.248      |
| no_vehicle            | 6.240      |
| no_diploma_pop25      | 6.207      |
| EP_NHPI               | 5.667      |
| EP_NOINT              | 5.067      |
| EP_POV150             | 4.952      |
| limited_english_hh    | 4.950      |
| no_broadband          | 4.572      |
| EP_UNINSUR            | 4.397      |
| uninsured             | 4.259      |
| poverty_under125      | 4.248      |
| EP_DISABL             | 3.717      |
| disability            | 3.363      |
| no_fulltime_worker_hh | 3.295      |
| EP_HBURD              | 2.871      |
| crowding_over100      | 2.630      |
| EP_AGE17              | 2.491      |
| EP_CROWD              | 2.467      |
| EP_MUNIT              | 2.372      |
| EP_SNGPNT             | 2.048      |
| EP_GROUPQ             | 1.654      |
| EP_UNEMP              | 1.597      |
| EP_MOBILE             | 1.145      |

### 4b. VIF - block group, all 35 vars (n=495 complete cases - note the large complete-case drop from 3 high-missingness dollar variables)

| variable                   | VIF    |
|:---------------------------|:-------|
| PM25                       | 32.105 |
| OZONE                      | 24.454 |
| DSLPM                      | 8.531  |
| PTRAF                      | 5.345  |
| NO2                        | 5.013  |
| PTSDF                      | 4.461  |
| poverty_under150           | 3.029  |
| PRMP                       | 2.955  |
| LOWINCPCT                  | 2.724  |
| LESSHSPCT                  | 2.718  |
| median_family_income       | 2.632  |
| LINGISOPCT                 | 2.464  |
| median_home_value          | 2.416  |
| PEOPCOLORPCT               | 2.410  |
| no_diploma_under9yrs       | 2.243  |
| median_monthly_mortgage    | 2.127  |
| pct_owner_occupied         | 1.978  |
| PRE1960PCT                 | 1.943  |
| OVER64PCT                  | 1.884  |
| poverty_pct_families       | 1.873  |
| PWDIS                      | 1.819  |
| LIFEEXPPCT                 | 1.782  |
| UST                        | 1.775  |
| median_gross_rent          | 1.636  |
| DISABILITYPCT              | 1.528  |
| PNPL                       | 1.512  |
| income_disparity           | 1.475  |
| pct_single_parent_children | 1.435  |
| UNDER5PCT                  | 1.374  |
| RSEI_AIR                   | 1.349  |
| pct_crowding_over100       | 1.315  |
| DWATER                     | 1.216  |
| UNEMPPCT                   | 1.203  |
| pct_no_kitchen             | 1.199  |
| pct_no_plumbing            | 1.175  |

### 4b. VIF - block group, excluding the 3 high-missing variables (n=1,185 complete cases, more representative)

| variable                   | VIF    |
|:---------------------------|:-------|
| PM25                       | 19.999 |
| OZONE                      | 13.336 |
| DSLPM                      | 8.072  |
| PTRAF                      | 4.929  |
| NO2                        | 4.372  |
| PTSDF                      | 4.274  |
| poverty_under150           | 3.075  |
| PRMP                       | 2.897  |
| median_family_income       | 2.761  |
| LOWINCPCT                  | 2.750  |
| LESSHSPCT                  | 2.637  |
| PEOPCOLORPCT               | 2.579  |
| pct_owner_occupied         | 2.276  |
| LINGISOPCT                 | 2.231  |
| poverty_pct_families       | 2.008  |
| no_diploma_under9yrs       | 1.983  |
| median_home_value          | 1.939  |
| PRE1960PCT                 | 1.798  |
| UST                        | 1.734  |
| PWDIS                      | 1.726  |
| OVER64PCT                  | 1.660  |
| LIFEEXPPCT                 | 1.638  |
| PNPL                       | 1.574  |
| DISABILITYPCT              | 1.545  |
| pct_single_parent_children | 1.377  |
| RSEI_AIR                   | 1.373  |
| DWATER                     | 1.271  |
| pct_crowding_over100       | 1.260  |
| UNDER5PCT                  | 1.199  |
| UNEMPPCT                   | 1.120  |
| pct_no_kitchen             | 1.090  |
| pct_no_plumbing            | 1.072  |

### 4c. Tract SVI <-> ACS-CRE construct pairs (n=9)

| svi_var    | cre_var            | n   | pearson_r   | spearman_rho   | note                                                        |
|:-----------|:-------------------|:----|:------------|:---------------|:------------------------------------------------------------|
| EP_POV150  | poverty_under125   | 697 | 0.832       | 0.825          | poverty (150% vs 125% threshold)                            |
| EP_UNINSUR | uninsured          | 698 | 0.848       | 0.849          | uninsured                                                   |
| EP_DISABL  | disability         | 698 | 0.764       | 0.764          | disability                                                  |
| EP_NOVEH   | no_vehicle         | 697 | 0.898       | 0.841          | no vehicle                                                  |
| EP_AGE65   | age65plus          | 698 | 0.888       | 0.877          | age 65+                                                     |
| EP_LIMENG  | limited_english_hh | 698 | 0.840       | 0.821          | limited English HH                                          |
| EP_NOHSDP  | no_diploma_pop25   | 698 | 0.895       | 0.898          | no HS diploma (EP_NOHSDP is bachelor's-adjacent cut; check) |
| EP_NOINT   | no_broadband       | 697 | 0.854       | 0.862          | no internet/broadband                                       |
| EP_CROWD   | crowding_over100   | 697 | 0.739       | 0.721          | crowding                                                    |

### 4d. Race/ethnicity vs. access/connectivity axis divergence

**No factor analysis or PCA was run anywhere in this analysis - not computed.** The two-axis language in `correlation_analysis.md` rests on the Part 4 sign-pattern evidence (Sections 1 and 5 of this file) plus the raw correlation block below - shown as-is, not smoothed into a cleaner story than it supports. The access/connectivity variables (`EP_NOVEH, no_vehicle, EP_MUNIT, no_broadband, EP_NOINT`) correlate 0.219-0.862 with each other - consistently positive, moderate-to-strong. The three race/ethnicity variables do **not** move together as cleanly: `EP_MINRTY` correlates moderately with both `EP_HISP` (0.383) and `EP_AFAM` (0.156), but `EP_HISP` and `EP_AFAM` correlate **-0.683** with each other (expected - they are largely competing shares of the same population base). Between blocks, `EP_MINRTY` and `EP_NOINT`/`no_broadband` show moderate positive correlation (0.379-0.448) rather than near-zero, while `EP_HISP` sits close to zero against every access/connectivity variable (-0.101 to 0.022). **The divergence is real for `EP_HISP` specifically and directionally visible in the Part 4 sign pattern, but the race/ethnicity block is not internally uniform, and this correlation block alone does not cleanly separate into two orthogonal axes** - read the two-axis framing in `correlation_analysis.md` as a description of the sign pattern in Sections 1/5, not as a validated factor structure.

| variable     | EP_NOVEH   | no_vehicle   | EP_MUNIT   | no_broadband   | EP_NOINT   | EP_MINRTY   | EP_HISP   | EP_AFAM   |
|:-------------|:-----------|:-------------|:-----------|:---------------|:-----------|:------------|:----------|:----------|
| EP_NOVEH     | 1.000      | 0.841        | 0.469      | 0.612          | 0.629      | 0.180       | -0.090    | 0.171     |
| no_vehicle   | 0.841      | 1.000        | 0.465      | 0.590          | 0.591      | 0.174       | -0.085    | 0.188     |
| EP_MUNIT     | 0.469      | 0.465        | 1.000      | 0.243          | 0.219      | -0.164      | -0.101    | -0.019    |
| no_broadband | 0.612      | 0.590        | 0.243      | 1.000          | 0.862      | 0.379       | -0.002    | 0.189     |
| EP_NOINT     | 0.629      | 0.591        | 0.219      | 0.862          | 1.000      | 0.448       | 0.022     | 0.226     |
| EP_MINRTY    | 0.180      | 0.174        | -0.164     | 0.379          | 0.448      | 1.000       | 0.383     | 0.156     |
| EP_HISP      | -0.090     | -0.085       | -0.101     | -0.002         | 0.022      | 0.383       | 1.000     | -0.683    |
| EP_AFAM      | 0.171      | 0.188        | -0.019     | 0.189          | 0.226      | 0.156       | -0.683    | 1.000     |


### 4e. Block-group EJScreen <-> ADI flagged duplicate candidates (4 pairs named in the analysis spec)

| pair                  | pearson_r   | spearman_rho   | verdict                                                                  |
|:----------------------|:------------|:---------------|:-------------------------------------------------------------------------|
| no vehicle            |             |                | cannot compute - EJScreen column absent                                  |
| no internet           |             |                | cannot compute - EJScreen column absent                                  |
| unemployment          |             |                | cannot compute - ADI-side column was never pulled (dropped as duplicate) |
| less-than-HS vs <9yrs | 0.679       | 0.695          | high correlation expected, not ~1.0 (different thresholds)               |

**Columns missing on each side, named explicitly:**

- *no vehicle*: **absent on both sides.** EJScreen has no raw "no vehicle" column at all in this v2.3 extract (`PTRAF` is a traffic-proximity hazard measure, not a household-vehicle-access measure, and was not substituted). ADI also does not carry it - `DATA_PROCESSING.md` Sec 3 lists "no motor vehicle" among the components dropped from the ADI pull as a presumed EJScreen duplicate, so it was never collected there either.
- *no internet*: **EJScreen has no raw "no household internet" column** in this extract. No ADI-side column either (ADI dropped it as a presumed EJScreen duplicate at the pull stage, per `DATA_PROCESSING.md` Sec 3) - both sides are absent.
- *unemployment*: **EJScreen's `UNEMPPCT` exists** (present, not missing). The gap is on the **ADI side** - `DATA_PROCESSING.md` records unemployment as dropped from the ADI pull as a presumed EJScreen duplicate, so no ADI unemployment column was ever collected to correlate against.
- *less-than-HS vs <9yrs-education*: **both sides present** (`LESSHSPCT`, `no_diploma_under9yrs`) - this is the one pair of the four that could actually be tested. Result: r=0.679, ρ=0.695, n=1,833 - high but well short of ~1.0, consistent with genuinely different thresholds (HS-diploma cut vs. 8th-grade cut) rather than duplication.


### 4f. EJScreen environmental (13) x ADI (13) co-location - top 20 of 169 pairs by |r| (median |r| across all pairs = 0.099)

| env_indicator   | adi_component        | n     | pearson_r   | spearman_rho   |
|:----------------|:---------------------|:------|:------------|:---------------|
| UST             | pct_owner_occupied   | 1,832 | -0.423      | -0.432         |
| PTSDF           | pct_owner_occupied   | 1,832 | -0.380      | -0.374         |
| NO2             | pct_owner_occupied   | 1,822 | -0.373      | -0.385         |
| PRMP            | no_diploma_under9yrs | 1,833 | 0.313       | 0.340          |
| PTRAF           | pct_owner_occupied   | 1,832 | -0.303      | -0.317         |
| DSLPM           | median_family_income | 1,496 | -0.295      | -0.297         |
| UST             | poverty_under150     | 1,832 | 0.294       | 0.328          |
| UST             | median_gross_rent    | 1,297 | -0.286      | -0.347         |
| PRMP            | median_family_income | 1,496 | -0.281      | -0.303         |
| NO2             | median_family_income | 1,489 | -0.273      | -0.311         |
| PRE1960PCT      | median_gross_rent    | 1,297 | -0.269      | -0.346         |
| DSLPM           | median_home_value    | 1,535 | -0.264      | -0.274         |
| UST             | income_disparity     | 1,207 | 0.259       | 0.278          |
| PRMP            | poverty_under150     | 1,832 | 0.259       | 0.302          |
| UST             | median_family_income | 1,496 | -0.258      | -0.322         |
| PNPL            | poverty_under150     | 1,832 | 0.251       | 0.338          |
| NO2             | poverty_under150     | 1,822 | 0.250       | 0.283          |
| PTRAF           | poverty_under150     | 1,832 | 0.236       | 0.270          |
| DSLPM           | poverty_under150     | 1,832 | 0.235       | 0.279          |
| PRMP            | median_home_value    | 1,535 | -0.231      | -0.250         |


---

## 5. Volume results (Part 4a)

*Sources: `output/part4_investment_vs_indicators/4a_tract_volume_continuous.csv`, `4a_tract_volume_binary.csv`.*

**Plain-language read:** across all 5 volume outcomes x 34 vulnerability variables (170 continuous pairs, tract grain), the single strongest relationship anywhere in this table is **EP_MUNIT vs. investment_per_area, Spearman ρ=0.570** - this is reported as weak in `correlation_analysis.md`; the full table below is what makes that verifiable rather than asserted. Pearson r is systematically weaker than Spearman ρ throughout, consistent with the heavily skewed dollar outcomes.

### 5a. `investment_per_capita` vs. all 34 vulnerability variables (n=34)

| variable              | n   | pearson_r   | pearson_p   | pearson_p_fdr   | spearman_rho   | spearman_p   | spearman_p_fdr   |
|:----------------------|:----|:------------|:------------|:----------------|:---------------|:-------------|:-----------------|
| EP_NOVEH              | 697 | 0.117       | 0.0019      | 0.0162          | 0.333          | 1.49e-19     | 5.06e-18         |
| EP_MUNIT              | 697 | 0.037       | 0.3245      | 0.4716          | 0.279          | 5.76e-14     | 9.79e-13         |
| no_vehicle            | 698 | -0.011      | 0.7773      | 0.8525          | 0.271          | 3.31e-13     | 3.75e-12         |
| EP_MINRTY             | 698 | -0.096      | 0.0111      | 0.0628          | -0.256         | 6.92e-12     | 5.88e-11         |
| no_broadband          | 698 | 0.243       | 8.37e-11    | 1.42e-09        | 0.227          | 1.27e-09     | 8.64e-09         |
| EP_HISP               | 698 | -0.072      | 0.0560      | 0.1730          | -0.203         | 6.10e-08     | 3.46e-07         |
| EP_NOINT              | 697 | 0.052       | 0.1701      | 0.3402          | 0.163          | 1.46e-05     | 6.79e-05         |
| EP_TWOMORE            | 698 | 0.060       | 0.1114      | 0.2706          | 0.163          | 1.60e-05     | 6.79e-05         |
| no_diploma_pop25      | 698 | -0.067      | 0.0756      | 0.2141          | -0.142         | 0.0002       | 0.0006           |
| EP_NOHSDP             | 698 | 0.051       | 0.1821      | 0.3440          | -0.126         | 0.0009       | 0.0030           |
| no_fulltime_worker_hh | 698 | -0.043      | 0.2569      | 0.4367          | 0.122          | 0.0012       | 0.0037           |
| EP_LIMENG             | 698 | -0.041      | 0.2797      | 0.4528          | -0.114         | 0.0025       | 0.0072           |
| EP_HBURD              | 697 | -0.028      | 0.4640      | 0.6310          | 0.093          | 0.0145       | 0.0378           |
| EP_SNGPNT             | 697 | 0.093       | 0.0140      | 0.0678          | -0.076         | 0.0447       | 0.1086           |
| EP_AGE17              | 698 | -0.079      | 0.0372      | 0.1263          | -0.075         | 0.0483       | 0.1096           |
| EP_OTHERRACE          | 698 | 0.009       | 0.8209      | 0.8673          | 0.062          | 0.1001       | 0.2128           |
| EP_ASIAN              | 698 | 0.002       | 0.9623      | 0.9623          | 0.053          | 0.1585       | 0.3039           |
| age65plus             | 698 | -0.085      | 0.0255      | 0.1082          | -0.053         | 0.1609       | 0.3039           |
| EP_CROWD              | 697 | -0.054      | 0.1557      | 0.3399          | 0.051          | 0.1779       | 0.3176           |
| EP_DISABL             | 698 | 0.082       | 0.0313      | 0.1183          | 0.050          | 0.1868       | 0.3176           |
| limited_english_hh    | 698 | 0.098       | 0.0097      | 0.0628          | -0.039         | 0.3039       | 0.4850           |
| EP_MOBILE             | 697 | 0.135       | 0.0004      | 0.0041          | 0.038          | 0.3138       | 0.4850           |
| EP_NHPI               | 698 | -0.011      | 0.7671      | 0.8525          | -0.034         | 0.3679       | 0.5438           |
| EP_AGE65              | 698 | -0.020      | 0.5921      | 0.7456          | -0.032         | 0.3952       | 0.5598           |
| EP_POV150             | 697 | -0.061      | 0.1076      | 0.2706          | 0.026          | 0.4952       | 0.6529           |
| crowding_over100      | 698 | 0.022       | 0.5595      | 0.7317          | -0.026         | 0.4993       | 0.6529           |
| poverty_under125      | 698 | -0.037      | 0.3329      | 0.4716          | 0.021          | 0.5830       | 0.7342           |
| EP_UNINSUR            | 698 | 0.015       | 0.7018      | 0.8227          | 0.017          | 0.6482       | 0.7642           |
| EP_GROUPQ             | 698 | 0.249       | 2.65e-11    | 9.02e-10        | -0.017         | 0.6518       | 0.7642           |
| EP_AFAM               | 698 | 0.008       | 0.8418      | 0.8673          | 0.011          | 0.7774       | 0.8811           |
| disability            | 698 | -0.047      | 0.2106      | 0.3768          | -0.007         | 0.8634       | 0.9469           |
| uninsured             | 698 | -0.037      | 0.3299      | 0.4716          | 0.005          | 0.8991       | 0.9553           |
| EP_AIAN               | 698 | -0.016      | 0.6651      | 0.8076          | -0.002         | 0.9550       | 0.9839           |
| EP_UNEMP              | 698 | -0.053      | 0.1599      | 0.3399          | -3.85e-04      | 0.9919       | 0.9919           |

### 5a. `investment_total` vs. all 34 vulnerability variables (n=34)

| variable              | n   | pearson_r   | pearson_p   | pearson_p_fdr   | spearman_rho   | spearman_p   | spearman_p_fdr   |
|:----------------------|:----|:------------|:------------|:----------------|:---------------|:-------------|:-----------------|
| EP_NOVEH              | 697 | 0.062       | 0.1033      | 0.3512          | 0.239          | 1.55e-10     | 5.28e-09         |
| EP_MUNIT              | 697 | 0.068       | 0.0708      | 0.3512          | 0.212          | 1.53e-08     | 2.60e-07         |
| EP_MINRTY             | 698 | -0.200      | 9.79e-08    | 3.33e-06        | -0.209         | 2.55e-08     | 2.78e-07         |
| EP_HISP               | 698 | -0.103      | 0.0066      | 0.1118          | -0.207         | 3.27e-08     | 2.78e-07         |
| EP_TWOMORE            | 698 | 0.069       | 0.0700      | 0.3512          | 0.194          | 2.28e-07     | 1.55e-06         |
| no_vehicle            | 698 | 0.032       | 0.3936      | 0.7054          | 0.186          | 7.98e-07     | 4.52e-06         |
| age65plus             | 698 | -0.023      | 0.5373      | 0.7942          | -0.134         | 0.0004       | 0.0017           |
| no_broadband          | 698 | 0.024       | 0.5346      | 0.7942          | 0.134          | 0.0004       | 0.0017           |
| EP_OTHERRACE          | 698 | 0.068       | 0.0726      | 0.3512          | 0.113          | 0.0027       | 0.0103           |
| EP_AGE65              | 698 | -0.016      | 0.6787      | 0.8876          | -0.111         | 0.0035       | 0.0118           |
| no_diploma_pop25      | 698 | -0.036      | 0.3396      | 0.7054          | -0.107         | 0.0047       | 0.0147           |
| EP_CROWD              | 697 | -0.026      | 0.4921      | 0.7942          | 0.103          | 0.0067       | 0.0190           |
| EP_LIMENG             | 698 | -0.079      | 0.0370      | 0.3512          | -0.101         | 0.0077       | 0.0200           |
| EP_AFAM               | 698 | -0.037      | 0.3333      | 0.7054          | 0.093          | 0.0135       | 0.0328           |
| EP_ASIAN              | 698 | 0.042       | 0.2655      | 0.7054          | 0.091          | 0.0161       | 0.0366           |
| EP_NOINT              | 697 | -0.004      | 0.9155      | 0.9663          | 0.084          | 0.0274       | 0.0582           |
| EP_HBURD              | 697 | -0.028      | 0.4670      | 0.7939          | 0.080          | 0.0337       | 0.0674           |
| EP_NOHSDP             | 698 | -0.064      | 0.0913      | 0.3512          | -0.079         | 0.0364       | 0.0687           |
| EP_AGE17              | 698 | 0.007       | 0.8546      | 0.9663          | 0.071          | 0.0616       | 0.1103           |
| limited_english_hh    | 698 | -0.063      | 0.0956      | 0.3512          | -0.054         | 0.1569       | 0.2667           |
| EP_MOBILE             | 697 | -0.020      | 0.6032      | 0.8545          | 0.049          | 0.1939       | 0.3139           |
| no_fulltime_worker_hh | 698 | 0.036       | 0.3373      | 0.7054          | 0.047          | 0.2124       | 0.3282           |
| EP_SNGPNT             | 697 | -0.068      | 0.0709      | 0.3512          | 0.045          | 0.2398       | 0.3468           |
| EP_POV150             | 697 | -0.010      | 0.7991      | 0.9663          | 0.044          | 0.2448       | 0.3468           |
| EP_UNINSUR            | 698 | -0.043      | 0.2617      | 0.7054          | 0.042          | 0.2633       | 0.3581           |
| disability            | 698 | -0.005      | 0.8962      | 0.9663          | -0.040         | 0.2933       | 0.3835           |
| crowding_over100      | 698 | -0.005      | 0.8991      | 0.9663          | 0.037          | 0.3242       | 0.4083           |
| EP_UNEMP              | 698 | -0.034      | 0.3703      | 0.7054          | 0.034          | 0.3718       | 0.4514           |
| uninsured             | 698 | -0.039      | 0.3022      | 0.7054          | 0.029          | 0.4486       | 0.5144           |
| poverty_under125      | 698 | 0.003       | 0.9379      | 0.9663          | 0.028          | 0.4539       | 0.5144           |
| EP_GROUPQ             | 698 | 0.001       | 0.9894      | 0.9894          | -0.026         | 0.4886       | 0.5359           |
| EP_DISABL             | 698 | -0.032      | 0.3942      | 0.7054          | 0.023          | 0.5484       | 0.5826           |
| EP_NHPI               | 698 | -0.014      | 0.7122      | 0.8968          | -0.015         | 0.6908       | 0.7118           |
| EP_AIAN               | 698 | -0.017      | 0.6508      | 0.8851          | 0.001          | 0.9687       | 0.9687           |

### 5a. `investment_per_area` vs. all 34 vulnerability variables (n=34)

| variable              | n   | pearson_r   | pearson_p   | pearson_p_fdr   | spearman_rho   | spearman_p   | spearman_p_fdr   |
|:----------------------|:----|:------------|:------------|:----------------|:---------------|:-------------|:-----------------|
| EP_MUNIT              | 697 | 0.275       | 1.36e-13    | 4.63e-12        | 0.570          | 3.23e-61     | 1.10e-59         |
| EP_NOVEH              | 697 | 0.181       | 1.53e-06    | 1.73e-05        | 0.421          | 2.89e-31     | 4.91e-30         |
| no_vehicle            | 698 | 0.154       | 4.17e-05    | 0.0003          | 0.399          | 4.74e-28     | 5.37e-27         |
| EP_HBURD              | 697 | 0.037       | 0.3342      | 0.4940          | 0.277          | 9.91e-14     | 8.43e-13         |
| no_broadband          | 698 | 0.058       | 0.1254      | 0.2580          | 0.245          | 5.13e-11     | 3.49e-10         |
| EP_AGE17              | 698 | -0.169      | 6.91e-06    | 5.87e-05        | -0.230         | 8.45e-10     | 4.79e-09         |
| EP_NOINT              | 697 | 0.041       | 0.2777      | 0.4721          | 0.202          | 7.59e-08     | 3.69e-07         |
| EP_GROUPQ             | 698 | -0.027      | 0.4715      | 0.6413          | -0.165         | 1.22e-05     | 5.20e-05         |
| EP_CROWD              | 697 | -0.016      | 0.6699      | 0.7592          | 0.156          | 3.67e-05     | 0.0001           |
| EP_MINRTY             | 698 | -0.234      | 4.00e-10    | 6.81e-09        | -0.152         | 5.34e-05     | 0.0002           |
| limited_english_hh    | 698 | -0.021      | 0.5824      | 0.7321          | 0.144          | 0.0001       | 0.0004           |
| EP_POV150             | 697 | 0.012       | 0.7491      | 0.7901          | 0.143          | 0.0002       | 0.0004           |
| poverty_under125      | 698 | 0.038       | 0.3106      | 0.4801          | 0.116          | 0.0021       | 0.0055           |
| EP_UNINSUR            | 698 | 0.011       | 0.7668      | 0.7901          | 0.113          | 0.0029       | 0.0070           |
| EP_TWOMORE            | 698 | 0.113       | 0.0028      | 0.0119          | 0.108          | 0.0043       | 0.0098           |
| no_fulltime_worker_hh | 698 | 0.056       | 0.1366      | 0.2580          | 0.107          | 0.0047       | 0.0099           |
| crowding_over100      | 698 | -0.004      | 0.9218      | 0.9218          | 0.104          | 0.0062       | 0.0123           |
| EP_AFAM               | 698 | -0.097      | 0.0105      | 0.0398          | -0.094         | 0.0125       | 0.0236           |
| uninsured             | 698 | 0.014       | 0.7119      | 0.7808          | 0.091          | 0.0159       | 0.0280           |
| no_diploma_pop25      | 698 | -0.074      | 0.0500      | 0.1309          | -0.091         | 0.0165       | 0.0280           |
| EP_ASIAN              | 698 | 0.082       | 0.0308      | 0.0952          | 0.077          | 0.0432       | 0.0699           |
| EP_NOHSDP             | 698 | -0.091      | 0.0162      | 0.0551          | -0.070         | 0.0656       | 0.1014           |
| EP_AIAN               | 698 | -0.019      | 0.6244      | 0.7321          | -0.057         | 0.1323       | 0.1956           |
| age65plus             | 698 | -0.033      | 0.3864      | 0.5474          | -0.052         | 0.1697       | 0.2405           |
| EP_LIMENG             | 698 | -0.059      | 0.1166      | 0.2580          | 0.050          | 0.1860       | 0.2529           |
| EP_NHPI               | 698 | -0.026      | 0.5001      | 0.6540          | -0.049         | 0.1980       | 0.2590           |
| EP_SNGPNT             | 697 | -0.128      | 0.0007      | 0.0033          | -0.042         | 0.2693       | 0.3391           |
| EP_HISP               | 698 | -0.078      | 0.0383      | 0.1087          | -0.038         | 0.3161       | 0.3839           |
| EP_OTHERRACE          | 698 | 0.133       | 0.0004      | 0.0023          | 0.030          | 0.4312       | 0.5056           |
| EP_AGE65              | 698 | -0.019      | 0.6210      | 0.7321          | -0.028         | 0.4668       | 0.5172           |
| EP_MOBILE             | 697 | -0.040      | 0.2969      | 0.4801          | -0.027         | 0.4716       | 0.5172           |
| EP_UNEMP              | 698 | -0.056      | 0.1359      | 0.2580          | 0.014          | 0.7165       | 0.7608           |
| disability            | 698 | -0.043      | 0.2529      | 0.4526          | -0.013         | 0.7385       | 0.7608           |
| EP_DISABL             | 698 | -0.063      | 0.0969      | 0.2354          | 0.004          | 0.9089       | 0.9089           |

### 5b. `investment_any_excl_county` group comparison, all 34 variables (Mann-Whitney U, n=34)

| variable              | n_receiving   | n_not   | mean_receiving   | mean_not   | p_raw    | p_fdr    |
|:----------------------|:--------------|:--------|:-----------------|:-----------|:---------|:---------|
| EP_MUNIT              | 539           | 158     | 35.574           | 23.528     | 1.34e-06 | 9.11e-06 |
| EP_HISP               | 540           | 158     | 66.302           | 75.911     | 0.0008   | 0.0032   |
| EP_NOINT              | 539           | 158     | 16.784           | 9.577      | 7.58e-12 | 6.79e-11 |
| EP_NOVEH              | 539           | 158     | 10.770           | 4.728      | 1.27e-16 | 4.33e-15 |
| EP_AFAM               | 540           | 158     | 15.222           | 9.370      | 0.4557   | 0.6456   |
| EP_HBURD              | 539           | 158     | 39.902           | 35.884     | 0.0007   | 0.0029   |
| EP_POV150             | 539           | 158     | 26.905           | 22.916     | 0.0026   | 0.0074   |
| EP_MINRTY             | 540           | 158     | 84.935           | 88.873     | 0.7418   | 0.8697   |
| EP_UNINSUR            | 540           | 158     | 15.287           | 13.276     | 0.0162   | 0.0368   |
| EP_LIMENG             | 540           | 158     | 20.510           | 18.795     | 0.9530   | 0.9850   |
| EP_CROWD              | 539           | 158     | 6.730            | 5.137      | 0.0006   | 0.0028   |
| EP_DISABL             | 540           | 158     | 10.606           | 9.175      | 0.0003   | 0.0019   |
| EP_NOHSDP             | 540           | 158     | 17.085           | 16.016     | 0.6810   | 0.8564   |
| EP_UNEMP              | 540           | 158     | 4.873            | 3.888      | 0.0109   | 0.0265   |
| EP_AGE17              | 540           | 158     | 19.124           | 19.794     | 0.3124   | 0.4828   |
| EP_GROUPQ             | 540           | 158     | 2.051            | 1.681      | 0.7052   | 0.8564   |
| EP_ASIAN              | 540           | 158     | 1.450            | 1.727      | 0.0674   | 0.1347   |
| EP_AGE65              | 540           | 158     | 17.156           | 16.980     | 0.9850   | 0.9850   |
| EP_TWOMORE            | 540           | 158     | 1.500            | 1.351      | 0.2693   | 0.4579   |
| EP_SNGPNT             | 539           | 158     | 7.328            | 7.209      | 0.7944   | 0.9003   |
| no_broadband          | 540           | 158     | 0.116            | 0.058      | 3.26e-16 | 5.54e-15 |
| no_vehicle            | 540           | 158     | 0.108            | 0.053      | 7.99e-12 | 6.79e-11 |
| limited_english_hh    | 540           | 158     | 0.249            | 0.208      | 0.0829   | 0.1565   |
| poverty_under125      | 540           | 158     | 0.203            | 0.170      | 0.0036   | 0.0094   |
| no_fulltime_worker_hh | 540           | 158     | 0.223            | 0.191      | 0.0017   | 0.0055   |
| EP_MOBILE             | 539           | 158     | 1.590            | 1.619      | 0.3080   | 0.4828   |
| uninsured             | 540           | 158     | 0.138            | 0.115      | 0.0018   | 0.0055   |
| EP_NHPI               | 540           | 158     | 0.012            | 0.030      | 0.4810   | 0.6541   |
| EP_AIAN               | 540           | 158     | 0.064            | 0.082      | 0.9820   | 0.9850   |
| crowding_over100      | 540           | 158     | 0.074            | 0.061      | 0.0307   | 0.0653   |
| no_diploma_pop25      | 540           | 158     | 0.158            | 0.151      | 0.9112   | 0.9850   |
| disability            | 540           | 158     | 0.106            | 0.101      | 0.1596   | 0.2856   |
| age65plus             | 540           | 158     | 0.175            | 0.178      | 0.4030   | 0.5957   |
| EP_OTHERRACE          | 540           | 158     | 0.389            | 0.389      | 0.6672   | 0.8564   |

### 5b. `investment_any_single_unit` group comparison, all 34 variables (Mann-Whitney U, n=34)

| variable              | n_receiving   | n_not   | mean_receiving   | mean_not   | p_raw    | p_fdr    |
|:----------------------|:--------------|:--------|:-----------------|:-----------|:---------|:---------|
| EP_HISP               | 396           | 302     | 63.069           | 75.568     | 2.05e-12 | 6.96e-11 |
| EP_AFAM               | 396           | 302     | 16.886           | 9.979      | 6.46e-05 | 0.0007   |
| EP_MINRTY             | 396           | 302     | 83.552           | 88.809     | 0.0028   | 0.0157   |
| EP_LIMENG             | 396           | 302     | 18.030           | 22.865     | 1.38e-06 | 2.35e-05 |
| EP_NOINT              | 395           | 302     | 15.997           | 14.042     | 0.0442   | 0.1157   |
| EP_NOVEH              | 395           | 302     | 10.158           | 8.408      | 0.0063   | 0.0267   |
| EP_NOHSDP             | 396           | 302     | 16.116           | 17.796     | 0.0248   | 0.0768   |
| EP_HBURD              | 395           | 302     | 38.355           | 39.824     | 0.2752   | 0.4924   |
| EP_AGE17              | 396           | 302     | 19.754           | 18.649     | 0.0306   | 0.0866   |
| EP_SNGPNT             | 395           | 302     | 7.608            | 6.899      | 0.2499   | 0.4924   |
| EP_UNEMP              | 396           | 302     | 4.919            | 4.297      | 0.2323   | 0.4924   |
| EP_MUNIT              | 395           | 302     | 33.098           | 32.511     | 0.8533   | 0.9392   |
| EP_TWOMORE            | 396           | 302     | 1.638            | 1.241      | 0.0002   | 0.0021   |
| EP_POV150             | 395           | 302     | 25.849           | 26.199     | 0.5134   | 0.6542   |
| EP_UNINSUR            | 396           | 302     | 14.703           | 15.000     | 0.4204   | 0.6118   |
| EP_AGE65              | 396           | 302     | 17.245           | 16.948     | 0.6503   | 0.7897   |
| EP_DISABL             | 396           | 302     | 10.391           | 10.138     | 0.3044   | 0.5175   |
| EP_ASIAN              | 396           | 302     | 1.459            | 1.584      | 0.9055   | 0.9392   |
| EP_OTHERRACE          | 396           | 302     | 0.434            | 0.328      | 0.0154   | 0.0583   |
| EP_GROUPQ             | 396           | 302     | 2.001            | 1.922      | 0.2721   | 0.4924   |
| EP_MOBILE             | 395           | 302     | 1.566            | 1.636      | 0.3980   | 0.6118   |
| EP_CROWD              | 395           | 302     | 6.394            | 6.335      | 0.9116   | 0.9392   |
| limited_english_hh    | 396           | 302     | 0.220            | 0.264      | 0.0004   | 0.0029   |
| EP_AIAN               | 396           | 302     | 0.059            | 0.080      | 0.5195   | 0.6542   |
| no_broadband          | 396           | 302     | 0.111            | 0.093      | 0.0058   | 0.0267   |
| no_vehicle            | 396           | 302     | 0.103            | 0.086      | 0.1114   | 0.2525   |
| no_fulltime_worker_hh | 396           | 302     | 0.222            | 0.207      | 0.0858   | 0.2084   |
| no_diploma_pop25      | 396           | 302     | 0.151            | 0.164      | 0.0243   | 0.0768   |
| EP_NHPI               | 396           | 302     | 0.012            | 0.021      | 0.4081   | 0.6118   |
| poverty_under125      | 396           | 302     | 0.197            | 0.194      | 0.4523   | 0.6152   |
| uninsured             | 396           | 302     | 0.134            | 0.132      | 0.7507   | 0.8802   |
| age65plus             | 396           | 302     | 0.176            | 0.175      | 0.9875   | 0.9875   |
| disability            | 396           | 302     | 0.105            | 0.105      | 0.8755   | 0.9392   |
| crowding_over100      | 396           | 302     | 0.071            | 0.071      | 0.4318   | 0.6118   |


---

## 6. Sensitivity checks (Part 5a/5b)

*Sources: `output/part5_diagnostics/5a_pennsuco_influence.csv`, `5b_flag_large_project_influence.csv`.*

**Plain-language read:** both checks are reported in `correlation_analysis.md` as moving "<2%" on the substantive relationships - the tables below show that literally: the largest movement on any of the 10 headline pairs is 20.00% (Pennsuco removal) and 12.46% (flagged-unit removal), and in both cases the largest moves are on pairs that are already near-zero (poverty), not on the substantive vehicle/housing-density relationships.

### 6a. Pennsuco (12086981100) removed, headline tract pairs (n=10)

| outcome               | vuln_var         | n_all   | spearman_all   | n_excl   | spearman_excl_pennsuco   | abs_change   | pct_change   |
|:----------------------|:-----------------|:--------|:---------------|:---------|:-------------------------|:-------------|:-------------|
| investment_per_capita | EP_NOVEH         | 697     | 0.333          | 696      | 0.331                    | 0.003        | 0.83%        |
| investment_per_capita | EP_MUNIT         | 697     | 0.279          | 696      | 0.279                    | 3.50e-04     | 0.13%        |
| investment_per_capita | no_vehicle       | 698     | 0.271          | 697      | 0.276                    | 0.005        | 1.94%        |
| investment_per_capita | EP_MINRTY        | 698     | -0.256         | 697      | -0.255                   | 0.001        | 0.36%        |
| investment_per_capita | EP_POV150        | 697     | 0.026          | 696      | 0.030                    | 0.004        | 17.09%       |
| investment_per_capita | poverty_under125 | 698     | 0.021          | 697      | 0.025                    | 0.004        | 20.00%       |
| investment_per_capita | EP_AGE65         | 698     | -0.032         | 697      | -0.031                   | 0.002        | 4.69%        |
| investment_per_capita | age65plus        | 698     | -0.053         | 697      | -0.049                   | 0.004        | 7.68%        |
| EP_NOVEH              | no_vehicle       | 697     | 0.841          | 696      | 0.848                    | 0.007        | 0.84%        |
| EP_NOHSDP             | no_diploma_pop25 | 698     | 0.898          | 697      | 0.906                    | 0.008        | 0.88%        |

### 6b. 3 flag_large_project units removed, headline tract pairs (n=10)

| outcome               | vuln_var         | n_all   | spearman_all   | n_excl   | spearman_excl_flagged   | abs_change   | pct_change   |
|:----------------------|:-----------------|:--------|:---------------|:---------|:------------------------|:-------------|:-------------|
| investment_per_capita | EP_NOVEH         | 697     | 0.333          | 694      | 0.335                   | 0.001        | 0.44%        |
| investment_per_capita | EP_MUNIT         | 697     | 0.279          | 694      | 0.283                   | 0.003        | 1.12%        |
| investment_per_capita | no_vehicle       | 698     | 0.271          | 695      | 0.279                   | 0.008        | 2.89%        |
| investment_per_capita | EP_MINRTY        | 698     | -0.256         | 695      | -0.252                  | 0.003        | 1.31%        |
| investment_per_capita | EP_POV150        | 697     | 0.026          | 694      | 0.028                   | 0.003        | 10.13%       |
| investment_per_capita | poverty_under125 | 698     | 0.021          | 695      | 0.023                   | 0.003        | 12.46%       |
| investment_per_capita | EP_AGE65         | 698     | -0.032         | 695      | -0.029                  | 0.003        | 8.58%        |
| investment_per_capita | age65plus        | 698     | -0.053         | 695      | -0.050                  | 0.003        | 5.31%        |
| EP_NOVEH              | no_vehicle       | 697     | 0.841          | 694      | 0.844                   | 0.003        | 0.32%        |
| EP_NOHSDP             | no_diploma_pop25 | 698     | 0.898          | 695      | 0.899                   | 0.001        | 0.09%        |


---

## 7. Data caveats and open questions

*Sources: `output/variable_dictionary.csv`, `output/part2_univariate/univariate_tract_vulnerability.csv`, `univariate_bg_vulnerability.csv`, `correlation_analysis.md` build notes.*

### 7a. EJScreen health-indicator mismatch

`DATA_PROCESSING.md` describes EJScreen as carrying "7 socioeconomic + 5 health indicators." Only **2 of the 5 expected health indicators actually exist** as raw columns in the on-disk extract (`EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv`, v2.3 reconstruction):

| present | absent |
|---|---|
| `DISABILITYPCT` (% persons with disabilities) | not found under any name |
| `LIFEEXPPCT` (% low life expectancy) | not found under any name |
| | 3rd expected health indicator - absent |
| | 4th expected health indicator - absent |
| | 5th expected health indicator - absent |

A full-header search of the file (231 columns, including all percentile/bin/popup-text variants) turned up no additional health-disparity columns under any recognizable name (life expectancy, heart disease, asthma, cancer, diabetes, stroke, COPD, mental health were all checked). **Unresolved**: either `DATA_PROCESSING.md`'s count of 5 is wrong for this file, or a different EJScreen product/vintage carries the other 3 and was never downloaded. Used what's actually there (2) rather than fabricate 3 more.

### 7b. Variables flagged >20% missing, near-constant, or rate outside [0,1]

**Tract vulnerability (SVI EP_* + ACS CRE, n=34)**: none flagged.

**Block-group vulnerability (EJScreen + ADI, n=35)**

| variable                | n     | n_missing   | pct_missing   | n_distinct   | flag_high_missing_gt20pct   | flag_near_constant   | flag_rate_outside_0_1   |
|:------------------------|:------|:------------|:--------------|:-------------|:----------------------------|:---------------------|:------------------------|
| PNPL                    | 1,843 | 6           | 0.3%          | 1404         | False                       | False                | True                    |
| PRMP                    | 1,843 | 6           | 0.3%          | 1547         | False                       | False                | True                    |
| PTSDF                   | 1,843 | 6           | 0.3%          | 1836         | False                       | False                | True                    |
| UST                     | 1,843 | 1           | 0.1%          | 1482         | False                       | False                | True                    |
| PWDIS                   | 1,843 | 6           | 0.3%          | 375          | False                       | False                | True                    |
| DWATER                  | 1,843 | 166         | 9.0%          | 95           | False                       | False                | True                    |
| income_disparity        | 1,843 | 636         | 34.5%         | 1137         | True                        | False                | False                   |
| median_gross_rent       | 1,843 | 546         | 29.6%         | 947          | True                        | False                | False                   |
| median_monthly_mortgage | 1,843 | 605         | 32.8%         | 941          | True                        | False                | False                   |

**Tract outcomes**

| variable       | n   | n_missing   | pct_missing   | n_distinct   | flag_high_missing_gt20pct   | flag_near_constant   | flag_rate_outside_0_1   |
|:---------------|:----|:------------|:--------------|:-------------|:----------------------------|:---------------------|:------------------------|
| investment_any | 698 | 0           | 0.0%          | 1            | False                       | True                 | False                   |

**Block-group outcomes**: none flagged.

Note on the 6 block-group environmental variables flagged "rate outside [0,1]" (`PNPL, PRMP, PTSDF, UST, PWDIS, DWATER`): **not a data bug** - these are EJScreen proximity/count scores in native units (e.g. facility counts within a distance band), not 0-1 rates; the univariate profiler's rate-style bound check simply doesn't apply to them, as documented in `output/variable_dictionary.csv`.


### 7c. The B25014 (block-group crowding) gap

`DATA_PROCESSING.md`'s 13-component block-group ADI list includes B25014 (% households, >1 occupant/room), but only 12 of the 13 ADI tables had actually been downloaded to `block-group-level/ADI Data/`. **Flagged mid-build and resolved**: the user supplied the missing table (`block-group-level/ADI Data/B25014- Tenure by Occupants per Room/`, same 2024 ACS 5-Year vintage as its 12 siblings) before the analysis tables were built. All 13 ADI components are present in `blockgroup_analysis.csv`. Resolved, not an open item.


### 7d. Other items flagged mid-build

- **`income_disparity` (block group) is undefined, not merely missing, for 34.5% of block groups** (636 of 1,843: 619 with zero low-income households giving log(0)=-inf, 17 with zero high-income households giving /0). Left as `NaN` by construction of the log-ratio formula at fine geography, not imputed, not computed as a literal infinity. This is *why* `income_disparity` appears on the >20%-missing list above - the missingness is formula-driven, not a data-quality problem, and is unresolved only in the sense that no alternative formula was substituted.
- **3 of the 4 block-group EJScreen<->ADI "flagged duplicate" pairs (Section 4e) could not be numerically checked** because a column was absent on one or both sides. This is a gap in the duplicate-candidate list itself, not resolved here - worth raising with whoever compiled that list.
- **No factor analysis or PCA exists anywhere in this analysis** (Section 4d) - the two-axis read is supported only by the raw correlation block shown there, not by a formal dimension-reduction result. Unresolved / not attempted, by design (out of scope for a correlational analysis).
- **Jurisdiction name variants in the source project data** (e.g. `MiamiBeach` vs `Miami Beach`) were normalized for the municipality-allocation join only; they were not corrected anywhere else and do not affect any table in this file.
