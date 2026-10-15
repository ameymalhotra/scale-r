---
title: "Miami-Dade Climate Resilience Investment: Review Memo"
date: "18 September 2026"
papersize: us-letter
margin:
  x: 1in
  y: 1in
fontsize: 9pt
---

```{=typst}
#show table: set text(size: 7.6pt)
#show table: set par(leading: 0.42em)
```
Descriptive and correlational only. No model was fitted. Figures are in the appendix.

## 1. What we did

- **1,405 projects, \$8.55 billion**, covering everything completed, funded or ongoing. The 259 projects marked Planned were excluded: they are proposals, not commitments, and three unbuilt billion-dollar transit lines would otherwise dominate every result.
- **698 census tracts and 1,843 block groups**, both reported in full. Tract is the primary analysis because it is the only grain where the investment question can be asked at all: no hazard-risk layer exists at block group and investment per person is unstable there. Block group is reported as an exposure and deprivation analysis, not as a weaker version of the tract work. Sections 4a, 4b and 4c.
- **27 vulnerability indicators at tract, 37 at block group.** Individual components, not composite index scores, per your instruction.
- **Scope correction applied in this version.** Seven race and ethnicity variables published alongside the vulnerability index, but not part of it and not in your specification, have been removed. Your list named one race measure and that is what remains. This takes the tract set from 34 to 27 and removes the compositional collinearity problem those seven caused.
- **How project dollars reach a unit.** Parcel, neighbourhood and corridor projects go whole to the unit containing their point. Municipality projects are spread across that municipality's units by population. County projects are spread across the county the same way. Your scale classification was used as given; nothing was reclassified.
- **Nine zero-population tracts excluded.** With no residents every rate is zero divided by zero, which is undefined rather than missing, and investment per person cannot be formed. They are airports, the port and similar.
- **No physical-risk layer is included.** This is investment against vulnerability, not the three-way investment by risk by vulnerability question. A decision for you, see section 5.

## 2. What each variable is

Notes flag only threshold approximations, proxies and coverage problems. A blank note means the measure is clean. The block-group environmental measures are proximity or count scores rather than rates.

| Code | Indicator (tract, 698 units, 27 indicators) | Source | Notes |
|----|----|----|----|
|  | ***Economic hardship*** |  |  |
| EP_POV150 | Below 150% of poverty line | SVI |  |
| poverty_under125 | Below 125% of poverty line | ACS | Threshold: framework uses 1.30, nearest published band edge is 1.25 |
| EP_UNEMP | Unemployed | SVI |  |
| no_fulltime_worker_hh | Households with no workers | ACS | Proxy, loose: counts zero-worker households, misses part-time and seasonal |
| EP_HBURD | Housing cost burdened | SVI |  |
| EP_NOHSDP | No high school diploma | SVI |  |
| no_diploma_pop25 | No high school diploma, adults 25+ | ACS | Proxy: person-level measure for a household concept |
|  | ***Housing*** |  |  |
| EP_MUNIT | Multi-unit housing structures | SVI |  |
| EP_MOBILE | Mobile homes | SVI |  |
| EP_CROWD | Crowded housing | SVI |  |
| crowding_over100 | Crowded housing, over 1 per room | ACS | Threshold: ADI uses 0.75 per room, nearest published band edge is 1.00 |
| EP_GROUPQ | Living in group quarters | SVI |  |
|  | ***Access and mobility*** |  |  |
| EP_NOVEH | Households with no vehicle | SVI |  |
| no_vehicle | Households with no vehicle | ACS |  |
| EP_NOINT | No internet access | SVI |  |
| no_broadband | No broadband subscription | ACS | Proxy: complement measure, so includes dial-up and no service |
|  | ***Demographic composition*** |  |  |
| EP_MINRTY | Minority population share | SVI |  |
| EP_LIMENG | Limited English speaking households | SVI |  |
| limited_english_hh | Limited English speaking households | ACS |  |
| EP_AGE65 | Aged 65 and over | SVI |  |
| age65plus | Aged 65 and over | ACS |  |
| EP_AGE17 | Aged 17 and under | SVI |  |
| EP_SNGPNT | Single-parent households | SVI |  |
|  | ***Health*** |  |  |
| EP_UNINSUR | Without health insurance | SVI |  |
| uninsured | Without health insurance | ACS |  |
| EP_DISABL | With a disability | SVI |  |
| disability | With a disability | ACS |  |

```{=typst}
#pagebreak()
```
| Code | Indicator (block group, 1,843 units; 24 of 37, environmental overleaf) | Source | Notes |
|----|----|----|----|
|  | ***Economic hardship*** |  |  |
| LOWINCPCT | Low income | EJScreen |  |
| poverty_under150 | Below 150% of poverty line | ADI |  |
| poverty_pct_families | Families below poverty line | ADI |  |
| median_family_income | Median family income | ADI | 18.8% missing (median suppression) |
| income_disparity | Income disparity, low to high earner ratio | ADI | Undefined for 34.5%: log ratio divides by zero |
| UNEMPPCT | Unemployed | EJScreen |  |
| LESSHSPCT | Less than high school education | EJScreen |  |
| no_diploma_under9yrs | Under 9 years of schooling | ADI |  |
|  | ***Housing*** |  |  |
| median_home_value | Median home value | ADI | 16.7% missing (median suppression) |
| median_gross_rent | Median gross rent | ADI | 29.6% missing (median suppression) |
| median_monthly_mortgage | Median monthly mortgage cost | ADI | 32.8% missing (median suppression) |
| pct_owner_occupied | Owner-occupied homes | ADI |  |
| pct_crowding_over100 | Crowded housing, over 1 per room | ADI | Threshold: ADI uses 0.75 per room, we use 1.00 |
| pct_no_plumbing | Lacking complete plumbing | ADI |  |
| pct_no_kitchen | Lacking complete kitchen | ADI |  |
|  | ***Access and mobility*** |  |  |
| no_vehicle | Households with no vehicle | ACS | Assumed in EJScreen, absent, pulled separately |
| no_broadband | No broadband subscription | ACS | Proxy, as at tract. Also absent from EJScreen |
|  | ***Demographic composition*** |  |  |
| PEOPCOLORPCT | People of colour share | EJScreen | No Hispanic or Black breakdown at this grain |
| LINGISOPCT | Limited English speaking households | EJScreen |  |
| pct_single_parent_children | Single-parent households with children | ADI |  |
| OVER64PCT | Aged 65 and over | EJScreen |  |
| UNDER5PCT | Aged under 5 | EJScreen |  |
|  | ***Health*** |  |  |
| DISABILITYPCT | With a disability | EJScreen | 2 of the 5 health indicators expected |
| LIFEEXPPCT | Low life expectancy | EJScreen | 5.1% missing |

| Code | Indicator (block group, environmental exposure; 13 of 37) | Source | Notes |
|----|----|----|----|
| PM25 | Fine particulate matter | EJScreen |  |
| OZONE | Ozone | EJScreen |  |
| NO2 | Nitrogen dioxide | EJScreen |  |
| DSLPM | Diesel particulate matter | EJScreen |  |
| RSEI_AIR | Air toxics released | EJScreen |  |
| PTRAF | Traffic proximity | EJScreen |  |
| PNPL | Superfund site proximity | EJScreen |  |
| PRMP | Chemical accident risk site proximity | EJScreen |  |
| PTSDF | Hazardous waste site proximity | EJScreen |  |
| UST | Underground storage tanks | EJScreen |  |
| PWDIS | Wastewater discharge | EJScreen |  |
| DWATER | Drinking water non-compliance | EJScreen | 9.0% missing |
| PRE1960PCT | Pre-1960 housing, lead paint indicator | EJScreen |  |

## 3. What we did to the data, and where we are now

1.  Pulled the indicators: 2022 social vulnerability index, 2024 five-year American Community Survey, EJScreen 2024, deprivation index components.
2.  Built the project allocation to both grains and reconciled it to the dollar against the filtered project total.
3.  Filtered to completed, funded and ongoing projects.
4.  Excluded the nine zero-population tracts.
5.  Ran the correlation analysis across all variables and outcomes, with false-discovery-rate adjustment throughout.
6.  Tested whether urban density explains the composition pattern, and rejected that explanation.
7.  Found and corrected an error in the spatial diagnostic, see finding 5.
8.  Decomposed gray infrastructure by sub-type to test whether transit was driving the result.

Where we are now: the descriptive work is complete and the next step is spatial modelling.

## 4. Findings

### 4a. Census tract findings, 698 units

**1. Volume relationships are weak.** How much money a place received is only weakly related to how vulnerable it is, and is unrelated to economic hardship. Against investment per person the strongest of the 27 indicators is households with no vehicle at 0.33. Poverty sits at 0.03, unemployment at 0.00, aged 65 and over at minus 0.03, and no high school diploma at minus 0.13. Effect sizes across the whole analysis run from about 0.13 to 0.31; what makes them credible is their consistency across specifications, not their size.

**2. Composition is where the pattern is.** What kind of infrastructure a place receives is more strongly patterned than how much it receives. Gray share rises and green share falls with car-free households, multi-unit housing and low connectivity.

| Indicator                                   | Gray share | Green share | n   |
|---------------------------------------------|------------|-------------|-----|
| Households with no vehicle                  | +0.305     | −0.284      | 697 |
| No broadband subscription                   | +0.258     | −0.209      | 698 |
| Households with no vehicle (survey measure) | +0.254     | −0.239      | 698 |
| Multi-unit housing structures               | +0.209     | −0.194      | 697 |
| No internet access                          | +0.201     | −0.140      | 697 |

All ten cells survive adjustment. Inside gray the finding rests on drainage and stormwater, 682 projects reaching 298 tracts, which reproduces the pattern on its own and barely moves under a density control. Water and sewer shows larger coefficients, 0.26 and 0.28 against the two car-free measures, but reaches only 21 tracts, so it is suggestive rather than load-bearing. Coastal and seawall projects reach 17 tracts, too few to interpret at all.

**3. It is not transit, and it is not density.** Only two transit projects survive the filter and they reach two tracts between them, so they cannot drive a correlation computed across 698; removing them moves the headline from 0.305 to 0.299. Roads show no access relationship. Density was tested and does not explain the pattern, but the tract-level test proved little, because density never predicted composition there in the first place: its largest correlation with any outcome is 0.08 and against gray share it is 0.03 and not significant. The block-group version of the test is the meaningful one, and there the pattern does survive, attenuating by 14 to 19 percent under a housing density control while staying significant. Separately, the two surviving transit corridors carry 15.1 percent of filtered dollars as single map points, a known distortion; removing them moves every headline result by under 2 percent.

**4. A second axis: minority population share, running the opposite way.** Minority population share runs against gray share at −0.135 and with green share at +0.199, both surviving adjustment, the reverse of the access indicators. **It is not independent of them, and we should be careful saying so:** it correlates 0.45 with no internet access and 0.38 with no broadband, so part of what it measures overlaps the connectivity story. The measure that was close to independent of the access block was Hispanic share, which is one of the seven variables now out of scope. Black share was checked and showed no relationship at any stage, also now out of scope.

**5. A correction we caught.** Investment per person first returned a Moran's I of 0.006, which reads as no spatial clustering at all. That was an artifact of the outcome's extreme skew, where a handful of very large values dominate a variance-based statistic. Rank-transformed, the same measure gives 0.495, and the log transform gives 0.343. Every outcome we tested is spatially clustered once skew is handled. This is the direct reason the next step is a spatial model.

### 4b. Block group findings, 1,843 units

**1. Composition is led by environmental exposure, not access.** The measures that rank highest against gray share here are contamination and air quality, not the car-free and low-connectivity measures that lead at tract. Households with no vehicle, the strongest single indicator at tract, ranks fifth.

| Indicator                              | Gray share | n     |
|----------------------------------------|------------|-------|
| Underground storage tanks              | +0.271     | 1,838 |
| Pre-1960 housing, lead paint indicator | +0.242     | 1,838 |
| Hazardous waste site proximity         | +0.232     | 1,837 |
| Fine particulate matter                | −0.223     | 1,838 |
| Households with no vehicle             | +0.203     | 1,832 |
| Superfund site proximity               | +0.171     | 1,837 |
| Ozone                                  | −0.170     | 1,838 |
| Nitrogen dioxide                       | +0.147     | 1,828 |
| Traffic proximity                      | +0.120     | 1,837 |

All nine survive adjustment. The relationship is not an artifact of roads being built where traffic is: with road projects removed entirely, the remaining gray infrastructure still correlates with all four of the exposure measures we tested that way.

**2. The environmental block is not one thing, and we would value your view.** The redundancy figure shows these measures as one densely intercorrelated group, but against gray share they split by sign. The two that vary smoothly across the whole county, fine particulate matter and ozone, run negative. The measures that mark specific contaminated or industrial sites run positive. Regional air quality and localized point-source contamination therefore point in opposite directions. We offer this as an observation rather than a finding: we did not test it as a hypothesis, and the regional versus localized grouping is our reading after the fact, not a split defined in advance.

**3. The race and ethnicity axis appears here too, in the same direction.** People of colour share runs against gray share at −0.174 and with green share at +0.221, both surviving adjustment, across 1,838 units. This is the same reversal seen at tract, where the access measures run the other way.

**4. The density test at this grain is the meaningful one, and the pattern survives it.** Unlike tract, density does relate to composition here, so the control has something to absorb. Housing density is roughly twice the correlate that population density is against gray share, 0.144 against 0.061. Controlling for housing density, the stronger of the two, the access measures attenuate by 14 to 19 percent and all remain significant. People of colour share barely moves at all, under 1 percent.

**5. This is not an investment analysis, and we do not present it as one.** Three separate reasons, each sufficient on its own. First, no hazard-risk layer exists at this grain: FEMA's national risk index has no block-group product, so the risk side of the question cannot be asked here at all. Second, 31.4 percent of block groups receive investment only through the county-wide distribution, meaning their investment value reflects an automatic population-weighted share rather than anything sited there. Third, investment per person is unstable: the maximum is 1.7 million dollars per person, and one block group of six residents holds 6.6 million dollars. No population floor corrects this, because the extremes are project-concentration artifacts rather than small-denominator artifacts. We therefore scoped block group as an exposure and deprivation analysis.

**Coverage problems specific to this grain.** Several deprivation-index medians are heavily suppressed, missing for between 16.7 and 32.8 percent of block groups, because block groups are small samples. Income disparity is undefined for 34.5 percent, since its log-ratio formula divides by zero wherever an income bracket is empty. EJScreen carries no Hispanic or Black breakdown at this grain, only the combined people of colour measure, so the finer demographic comparison available at tract cannot be made here.

### 4c. How the two analyses differ

|   | Census tract, 698 units | Block group, 1,843 units |
|----|----|----|
| What leads composition | Access and mobility: car-free households, multi-unit housing, low connectivity | Environmental exposure: contamination sites, lead paint indicator, air quality |
| Households with no vehicle | Strongest single indicator, first of 27 | Fifth of 37 |
| Race and ethnicity axis | Appears: gray share down, green share up | Appears, same direction and similar size |
| Density test | Weak: density barely predicts composition, so the control had little to absorb | Meaningful: density does predict composition, and the pattern survives the control |
| Investment analysis supportable | Yes | No: no risk layer at this grain, a third of units receive only an automatic county share, and per-person values are unstable |
| Indicators and sources | 27, vulnerability index plus survey components | 37, EJScreen plus deprivation-index components plus two survey measures |
| Main coverage problems | Essentially none, all measures near complete | Several deprivation medians heavily suppressed; income disparity undefined for about a third of units |

Two things in that table matter more than the rest. **The race and ethnicity axis is the one result that replicates.** Minority population share at tract and people of colour share at block group both push gray share down and green share up, at similar magnitudes, and both survive every control we applied. Almost nothing else holds across both grains: the access measures lead at one and rank mid-table at the other, and the environmental measures that dominate block group have no counterpart in the tract indicator set at all.

**The density evidence is stronger at block group than at tract**, which cuts against calling tract the primary analysis on evidential grounds. It is worth being plain about this. Tract is primary because it is the grain where the investment question can be asked, not because its evidence is stronger. On the density question specifically, the block-group test is the one that carries weight.

## 5. Next step, and what we need from you

All outcomes are spatially clustered, so a spatial specification is required; treating each tract as independent would overstate our confidence. A spatial model separates how much of a unit's investment relates to its own characteristics from how much relates to its neighbours'.

1.  **Which side of the seven duplicate pairs should we keep**, the published vulnerability index indicators or our survey-built versions with the documented threshold departures in section 2? They correlate between 0.83 and 0.90, so keeping both is not viable.
2.  **Any variables to drop or add?**
3.  **Should a physical-risk layer be brought in**, making this the three-way question rather than the two-way one reported here?
4.  **Do you agree with how we scoped block group?** Section 4b sets out the three reasons it cannot carry an investment question. We are asking you to confirm that reasoning, not to rescue a weak analysis: the block-group work is reported in full and its density evidence is the stronger of the two.

```{=typst}
#pagebreak()
```
## Appendix: figures

**Figure 1a. Tract indicators against investment outcomes.** Spearman correlations; starred and bold cells survive false-discovery-rate adjustment. Blue share is marked sparse: only 19 tracts contain a blue project.

![](output/figures_professor/figure1_tract_variables_vs_outcomes.png)

```{=typst}
#pagebreak()
```
**Figure 1b. Block group indicators against investment outcomes.** Same construction as Figure 1a, for comparison against it. Investment per person is absent as a column here: it is unstable at this grain, for the reasons in section 4b, so no correlation was built on it.

![](output/figures_professor/figure1_bg_variables_vs_outcomes.png)

```{=typst}
#pagebreak()
```
**Figure 2a. Redundancy among the tract indicators.** Ordered by construct, so paired measures of the same thing sit together and their correlation shows as a bright block on the diagonal. The seven boxed pairs are question 1 in section 5.

![](output/figures_professor/figure2_tract_indicator_redundancy.png)

```{=typst}
#pagebreak()
```
**Figure 2b. Redundancy among the block group indicators.** Same construction as Figure 2a. The environmental measures form the dense block that section 4b, finding 2 discusses: they intercorrelate heavily here, yet split by sign against gray share.

![](output/figures_professor/figure2_bg_indicator_redundancy.png)

```{=typst}
#pagebreak()
```
**Figure 3. The gray decomposition, tract.** Access indicators against each gray sub-category's share of a tract's investment, before and after a density control. Unit counts are the tracts where a project of that type was sited. Amber marks water and sewer, which clears our 20-unit floor only just. Red marks transit, too sparse to interpret at all.

![](output/figures_professor/figure3_gray_decomposition.png)
