# Miami-Dade Climate Resilience Investment: Findings and Proposed Next Step

Descriptive and correlational work only. Nothing in this document was fit,
tuned, or validated as a predictive model. Every number comes from the
completed analysis outputs.

---

## 1. What we did

**Investment data.** 1,405 climate-resilience projects totalling
**$8.55 billion**, covering everything marked completed, funded or ongoing.
The 259 projects marked *Planned* were excluded, removing $13.92 billion, or
62 percent of the original dollar total: they are proposals rather than
commitments, and including them would let three unbuilt billion-dollar transit
lines dominate every result.

**Two geographic grains.** 698 census tracts and 1,843 block groups, analysed
separately throughout. We never correlate across grains.

**Vulnerability indicators.** 34 at tract level (CDC Social Vulnerability
Index indicators plus American Community Survey components) and 37 at block
group level (EJScreen indicators plus Area Deprivation Index components). All
are **individual component measures, not composite index scores**, per your
instruction. Section 2 lists every one.

**How project dollars reach a geographic unit.** Projects tagged parcel,
neighbourhood or corridor go whole to the unit containing their point.
Projects tagged municipality are distributed across that municipality's units,
weighted by population; projects tagged county are distributed across the
whole county the same way. **Your scale classification was used exactly as
given. Nothing was reclassified**, including cases where the tag clearly
understates a project's real footprint.

**Sample rule.** Nine tracts with zero population were excluded. This is not a
missing-data problem: with no residents every vulnerability rate is zero
divided by zero, which is undefined rather than absent, and per-person
investment cannot be formed at all. These nine are special-use areas such as
PortMiami, Miami International Airport and Virginia Key. Everything else was
retained, including a 28-person tract holding the highest per-person
investment value in the data.

**Decision point for you: there is no physical-risk layer in any of this.**
This is investment measured against vulnerability, not the three-way
investment by risk by vulnerability question. A tract-level FEMA National Risk
Index file is available and was deliberately left out of scope for this stage.
Bringing it in would change the question we are answering. See Section 6.

---

## 2. What each variable is

Coverage is the share of units with no value. Status flags where a measure
departs from its published definition. The code column is for traceability
only and appears nowhere else in this document.

### 2.1 Tract level, 698 units

| Variable | Source | Definition | Coverage | Status | Code |
|---|---|---|---|---|---|
| **Economic hardship** | | | | | |
| Below 150% of poverty line | SVI | Share of people under 150% of the federal poverty line | 0.1% missing | Clean | EP_POV150 |
| Below 125% of poverty line | ACS | Share of people under 125% of the poverty line | complete | **Threshold approximation**: the CRE framework uses 1.30; we use 1.25 because that is the published ACS band edge | poverty_under125 |
| Unemployed | SVI | Share of civilian labour force unemployed | complete | Clean | EP_UNEMP |
| Households with no workers | ACS | Households with zero workers | complete | **Proxy (loose)** for no full-time worker; counts households with no workers at all, so misses part-time and seasonal work | no_fulltime_worker_hh |
| Housing cost burdened | SVI | Households spending over 30% of income on housing | 0.1% missing | Clean | EP_HBURD |
| No high school diploma | SVI | Adults 25+ without a high school diploma | complete | Clean | EP_NOHSDP |
| No high school diploma (adults 25+) | ACS | Adults 25+ below a high school diploma | complete | **Proxy**: person-level measure standing in for a household-level concept | no_diploma_pop25 |
| **Housing** | | | | | |
| Multi-unit housing structures | SVI | Housing in structures with 10 or more units | 0.1% missing | Clean | EP_MUNIT |
| Mobile homes | SVI | Share of housing that is mobile homes | 0.1% missing | Clean | EP_MOBILE |
| Crowded housing | SVI | Occupied units with more people than rooms | 0.1% missing | Clean | EP_CROWD |
| Crowded housing (over 1 per room) | ACS | Occupied units above 1.0 occupants per room | complete | **Threshold approximation**: ADI uses 0.75 per room; we use 1.00 because that is the published ACS band edge | crowding_over100 |
| Living in group quarters | SVI | People in institutional or group housing | complete | Clean | EP_GROUPQ |
| **Access and mobility** | | | | | |
| Households with no vehicle | SVI | Households without a vehicle | 0.1% missing | Clean | EP_NOVEH |
| Households with no vehicle (ACS) | ACS | Owner plus renter households with no vehicle | complete | Clean | no_vehicle |
| No internet access | SVI | Households without internet | 0.1% missing | Clean | EP_NOINT |
| No broadband subscription | ACS | Households minus those with broadband of any type | complete | **Proxy**: a complement measure, so it counts households with dial-up or no service at all | no_broadband |
| **Demographic composition** | | | | | |
| Minority population share | SVI | All persons except non-Hispanic white | complete | Clean. **Compositional**: this and the seven measures below sum to roughly 100% | EP_MINRTY |
| Hispanic population share | SVI | Hispanic or Latino share | complete | Clean, compositional | EP_HISP |
| Black population share | SVI | Black or African American share | complete | Clean, compositional | EP_AFAM |
| Asian population share | SVI | Asian share | complete | Clean, compositional | EP_ASIAN |
| Two or more races share | SVI | Two or more races | complete | Clean, compositional | EP_TWOMORE |
| Other race share | SVI | Other single race | complete | Clean, compositional | EP_OTHERRACE |
| American Indian / Alaska Native share | SVI | American Indian or Alaska Native | complete | Clean, compositional | EP_AIAN |
| Native Hawaiian / Pacific Islander share | SVI | Native Hawaiian or Pacific Islander | complete | Clean, compositional | EP_NHPI |
| Limited English speaking households | SVI | Households where no adult speaks English well | complete | Clean | EP_LIMENG |
| Limited English speaking households (ACS) | ACS | Same concept, summed across four language groups | complete | Clean | limited_english_hh |
| Aged 65 and over | SVI | Population 65 and older | complete | Clean | EP_AGE65 |
| Aged 65 and over (ACS) | ACS | Population 65 and older, twelve age bands summed | complete | Clean | age65plus |
| Aged 17 and under | SVI | Population 17 and younger | complete | Clean | EP_AGE17 |
| Single-parent households | SVI | Single-parent households with children | 0.1% missing | Clean | EP_SNGPNT |
| **Health** | | | | | |
| Without health insurance | SVI | Uninsured share | complete | Clean | EP_UNINSUR |
| Without health insurance (ACS) | ACS | Uninsured, summed across all age and sex bands | complete | Clean | uninsured |
| With a disability | SVI | Civilian non-institutionalised with a disability | complete | Clean | EP_DISABL |
| With a disability (ACS) | ACS | Same concept, summed across age and sex bands | complete | Clean | disability |

### 2.2 Block group level, 1,843 units

| Variable | Source | Definition | Coverage | Status | Code |
|---|---|---|---|---|---|
| **Economic hardship** | | | | | |
| Low income | EJScreen | Share below twice the poverty level | complete | Clean | LOWINCPCT |
| Below 150% of poverty line | ADI | Share under 150% of poverty line | 0.6% missing | Clean | poverty_under150 |
| Families below poverty line | ADI | Families below the poverty line | 0.9% missing | Clean | poverty_pct_families |
| Median family income | ADI | Median family income in dollars | **18.8% missing** | Clean; suppression is heavier at this grain | median_family_income |
| Income disparity | ADI | Log ratio of households under $10k to households over $50k | **34.5% missing** | **Undefined, not missing**: the log ratio divides by zero wherever a block group has no household in one of the two brackets | income_disparity |
| Unemployed | EJScreen | Unemployed share of labour force | complete | Clean | UNEMPPCT |
| Less than high school education | EJScreen | Adults 25+ without high school completion | complete | Clean | LESSHSPCT |
| Under 9 years of schooling | ADI | Adults 25+ with under 9 years of schooling | 0.5% missing | Clean | no_diploma_under9yrs |
| **Housing** | | | | | |
| Median home value | ADI | Median owner-occupied home value | **16.7% missing** | Clean; block-group median suppression | median_home_value |
| Median gross rent | ADI | Median gross rent | **29.6% missing** | Clean; block-group median suppression | median_gross_rent |
| Median monthly mortgage cost | ADI | Median monthly cost, units with a mortgage | **32.8% missing** | Clean; block-group median suppression | median_monthly_mortgage |
| Owner-occupied homes | ADI | Owner-occupied share of occupied units | 0.6% missing | Clean | pct_owner_occupied |
| Crowded housing (over 1 per room) | ADI | Occupied units above 1.0 per room | 0.6% missing | **Threshold approximation**: ADI defines this at 0.75 per room; we use 1.00 | pct_crowding_over100 |
| Lacking complete plumbing | ADI | Occupied units lacking complete plumbing | 0.6% missing | Clean | pct_no_plumbing |
| Lacking complete kitchen | ADI | Occupied units lacking complete kitchen | 0.6% missing | Clean | pct_no_kitchen |
| **Access and mobility** | | | | | |
| Households with no vehicle | ACS | Owner plus renter households with no vehicle | 0.6% missing | Clean. **Added late**: see note below | no_vehicle |
| No broadband subscription | ACS | Households minus those with broadband of any type | 0.6% missing | **Proxy**, same complement method as tract level, kept consistent on purpose. **Added late** | no_broadband |
| **Demographic composition** | | | | | |
| People of colour share | EJScreen | All persons except non-Hispanic white | complete | Clean. EJScreen carries no separate Hispanic or Black breakdown at this grain | PEOPCOLORPCT |
| Limited English speaking households | EJScreen | Linguistically isolated households | complete | Clean | LINGISOPCT |
| Single-parent households with children | ADI | Single-parent families with own children under 18 | 0.9% missing | Clean | pct_single_parent_children |
| Aged 65 and over | EJScreen | Population over 64 | complete | Clean | OVER64PCT |
| Aged under 5 | EJScreen | Population under 5 | complete | Clean | UNDER5PCT |
| **Health** | | | | | |
| With a disability | EJScreen | Share with a disability | complete | Clean. **1 of the 5 health indicators the spec expected** | DISABILITYPCT |
| Low life expectancy | EJScreen | Share in low life expectancy areas | 5.1% missing | Clean. **2 of the 5 health indicators the spec expected** | LIFEEXPPCT |
| **Environmental exposure** | | | | | |
| Fine particulate matter | EJScreen | Annual average concentration | complete | Clean | PM25 |
| Ozone | EJScreen | Summer season average | complete | Clean | OZONE |
| Nitrogen dioxide | EJScreen | Annual average concentration | 0.6% missing | Clean | NO2 |
| Diesel particulate matter | EJScreen | Diesel particulate in air | 0.3% missing | Clean | DSLPM |
| Air toxics released | EJScreen | Modelled toxic releases to air | 0.1% missing | Clean | RSEI_AIR |
| Traffic proximity | EJScreen | Traffic volume weighted by distance | 0.3% missing | Clean; a proximity score, not a rate | PTRAF |
| Superfund site proximity | EJScreen | Proximity to Superfund sites | 0.3% missing | Clean; proximity score | PNPL |
| Chemical accident risk site proximity | EJScreen | Proximity to risk-management-plan facilities | 0.3% missing | Clean; proximity score | PRMP |
| Hazardous waste site proximity | EJScreen | Proximity to treatment and disposal facilities | 0.3% missing | Clean; proximity score | PTSDF |
| Underground storage tanks | EJScreen | Tank count and leak indicator | 0.1% missing | Clean; count-based score | UST |
| Wastewater discharge | EJScreen | Modelled wastewater discharge indicator | 0.3% missing | Clean; proximity score | PWDIS |
| Drinking water non-compliance | EJScreen | Water system violation points | 9.0% missing | Clean | DWATER |
| Pre-1960 housing (lead paint indicator) | EJScreen | Share of housing built before 1960 | complete | Clean | PRE1960PCT |

### 2.3 Four things in this table you have not seen before

1. **Two thresholds do not match their published definitions.** Poverty is
   measured at 1.25 where the CRE framework uses 1.30, and crowding at 1.00
   occupants per room where ADI uses 0.75. In both cases the published band
   edge in the underlying census table does not fall where the framework
   defines it, so an exact match is not available without microdata.
2. **Three tract measures are proxies, not exact:** the education measure is
   person-level standing in for a household concept; the broadband measure is
   a complement, so it includes dial-up and no-service households; the
   no-workers measure is the loosest, counting households with zero workers
   rather than zero full-time workers.
3. **Four ADI components were dropped at the pull stage** on the expectation
   that EJScreen already carried them. Two of those four, households with no
   vehicle and no household internet, **turned out to be absent from EJScreen
   entirely**. We pulled both separately and added them to the block-group
   set, which is why they are marked added late. The other two, unemployment
   and high school completion, are genuinely present in EJScreen. One
   consequence: we can no longer test whether those four were duplicates,
   because for three of the four pairs one side was never collected.
4. **EJScreen contains 2 of the 5 health indicators the spec expected.** A
   full search of the file, all 231 columns, found only disability and low
   life expectancy. We used what exists rather than substitute.

---

## 3. Figures

### Figure 1. Vulnerability indicators against investment outcomes

![Figure 1a, tract](output/figures_professor/figure1_tract_variables_vs_outcomes.png)

![Figure 1b, block group](output/figures_professor/figure1_bg_variables_vs_outcomes.png)

Rows are grouped by construct. Cells are Spearman correlations; starred and
bold cells survive false-discovery-rate adjustment. The blue share column is
marked sparse because only 19 tracts contain a blue project.

**Two columns you asked for are absent, and we did not substitute anything
for them.** The two binary outcomes, received-anything-excluding-county and
project-sited-here, were tested with a rank-based group comparison rather than
a correlation, so no correlation coefficient exists for them. Their results
appear as a table in Section 4.1 instead. Block-group investment per person is
also absent by earlier decision: it is unstable at that grain, where the
maximum is $1.7 million per person and one six-resident block group holds
$6.6 million.

### Figure 2. Redundancy among the indicators

![Figure 2a, tract](output/figures_professor/figure2_tract_indicator_redundancy.png)

![Figure 2b, block group](output/figures_professor/figure2_bg_indicator_redundancy.png)

Ordered by construct, so duplicate measures sit next to each other and their
correlation appears as a bright block on the diagonal. The seven confirmed
duplicate pairs are boxed in black. The race and ethnicity block, outlined in
dashed green, is compositional: those shares sum to roughly 100 percent, so
they cannot all enter a model together. At 34 by 34 and 37 by 37 the full
matrices remain legible at page size, so no split by construct was needed.

### Figure 3. The gray decomposition

![Figure 3](output/figures_professor/figure3_gray_decomposition.png)

The access and mobility indicators against each gray sub-category's share of a
tract's investment, before and after controlling for population density. The
relationship holds in drainage and stormwater, the one category with a broad
base. It is absent for roads and for the unclassified residual.

**Two different markings, because these are two different problems.** The
transit column is outlined in red: it rests on 2 receiving tracts and cannot
be interpreted at all. Water and sewer is outlined in amber: it clears the
20-unit floor only just, at 21 tracts, and it carries the largest coefficients
in the figure, so those dark cells should be read with caution rather than as
the headline. Every column label now states how many tracts that category
actually reached, so no category's base is hidden.

The five columns cover all of gray. "Other or unclassified" is 23.6 percent of
gray dollars across 109 tracts, and it shows no relationship with any access
indicator, before or after the control.

---

## 4. Findings

### 4.1 Volume relationships are weak

**How much money a place received is only weakly related to how vulnerable it
is, and not related at all to economic hardship.** Against investment per
person, our primary dollar outcome, the strongest of 34 relationships is
households with no vehicle at 0.33. Poverty, unemployment, education and age
show essentially nothing.

| Indicator against investment per person | n | Spearman | FDR p |
|---|---|---|---|
| Households with no vehicle | 697 | **0.333** | <0.0001 |
| Multi-unit housing structures | 697 | 0.279 | <0.0001 |
| Households with no vehicle (ACS) | 698 | 0.271 | <0.0001 |
| Below 150% of poverty line | 697 | 0.026 | 0.653 |
| Below 125% of poverty line | 698 | 0.021 | 0.734 |
| Unemployed | 698 | −0.000 | 0.992 |
| Aged 65 and over | 698 | −0.032 | 0.560 |
| With a disability | 698 | 0.050 | 0.318 |

The two binary outcomes, tested by group comparison rather than correlation,
point the same way. Tracts that received investment outside the automatic
county distribution have more multi-unit housing (35.6 versus 23.5 percent)
and more households with no vehicle (10.8 versus 4.7 percent), while poverty
differs far less (26.9 versus 22.9 percent). All three differences are based
on 539 tracts that received and 158 that did not.

**One caveat against reading 0.33 as a ceiling.** Measured per unit of land
area instead of per person, the relationships are stronger: 0.57 for
multi-unit housing, 0.42 for households with no vehicle. That is close to
mechanical, since investment per land area rises wherever housing is dense,
which is what the multi-unit measure records. These are the highest figures in
the volume analysis and you should see them, but per person remains our
primary outcome.

### 4.2 Composition is where the pattern is, and it is specific

**What kind of infrastructure a place receives is more strongly patterned than
how much it receives.** Gray share rises with car-free households, multi-unit
housing and low connectivity. Green share falls with the same indicators. The
table below is gray as a whole; the decomposition into sub-categories follows
it.

| Indicator | Gray share (all sub-categories) | Green share | n |
|---|---|---|---|
| Households with no vehicle | **+0.305** | **−0.284** | 697 |
| No broadband subscription | +0.258 | −0.209 | 698 |
| Households with no vehicle (ACS) | +0.254 | −0.239 | 698 |
| Multi-unit housing structures | +0.209 | −0.194 | 697 |
| No internet access | +0.201 | −0.140 | 697 |

All ten cells survive FDR adjustment.

**Inside gray, the finding rests on drainage and stormwater**, which is
**682 projects reaching 298 tracts**, much the broadest base of any
sub-category. Drainage alone reproduces the whole pattern: 0.15 with
households with no vehicle, 0.14 with no broadband, 0.14 with no internet
access, 0.10 with multi-unit housing, all still significant after controlling
for density and none of them moving by more than 0.01 under that control.

**Water and sewer shows larger coefficients but cannot carry the finding.**
Its correlations are the biggest in Figure 3, reaching 0.26 and 0.28 with the
two car-free household measures before the density control, but they rest on
**21 tracts**, one above our 20-unit floor. Treat them as suggestive, not
load-bearing.

One movement in Figure 3 is worth naming directly. Water and sewer against
multi-unit housing **collapses from +0.18 to +0.00** once population density
is controlled, and it is the only relationship in that figure that starts
above 0.10 and vanishes entirely. That is a reason to be careful with the
water and sewer column specifically, not with the finding as a whole, since
drainage moves barely at all under the same control.

### 4.3 It is not transit

**The obvious objection, that this is just transit investment following
transit riders, does not hold.** Only 2 transit projects survive the status
filter, and they reach 2 tracts between them. Two units cannot drive a
correlation computed across 698.

Base: 1,157 gray projects at tract grain, n = 698 tracts.

| Gray sub-category | Projects | Share of gray dollars | Tracts reached | Interpretable |
|---|---|---|---|---|
| Drainage and stormwater | 682 | 33.7% | 298 | yes |
| Transit | 2 | 25.8% | **2** | **no, too sparse** |
| Other or unclassified | 283 | 23.6% | 109 | yes |
| Water and sewer | 70 | 7.0% | 21 | with caution |
| Road | 50 | 4.2% | 38 | yes |
| Coastal and seawall | 26 | 3.3% | **17** | **no, too sparse** |
| Power, communications, facilities | 44 | 2.4% | 26 | yes |

Removing transit entirely moves the headline correlation from **0.305 to
0.299**. Roads show no access relationship at all: four of five access
indicators are not significant against road share after the density control.

### 4.4 A second axis: race and ethnicity, running the other way

**Hispanic and minority population share run opposite to the access
indicators: gray share down, green share up.** This is a different pattern,
not a restatement of the first one.

| Indicator | Gray share | Green share | n | FDR p, gray |
|---|---|---|---|---|
| Minority population share | −0.135 | +0.199 | 698 | 0.0018 |
| Hispanic population share | −0.140 | +0.155 | 698 | 0.0011 |
| **Black population share** | **+0.028** | **−0.035** | 698 | **0.575, not significant** |

Two qualifications matter here, and they cut in opposite directions.

**Black population share shows no relationship at either stage**, before or
after any control, so this is not a generic demographic gradient. It is
specific to the Hispanic and overall minority measures.

**Only the Hispanic measure is close to statistically independent of the
access indicators.** Hispanic share correlates between −0.10 and +0.02 with
the five access indicators, so it is effectively a separate axis. The broader
minority share is not: it correlates 0.45 with no internet access and 0.38
with no broadband, so part of what it measures overlaps with the connectivity
story. We would not describe the whole race and ethnicity block as independent
of the access block.

### 4.5 The density check, reported honestly

**We tested whether the composition pattern is really about urban form rather
than deprivation. At tract level the test proved very little, and we want to
be clear about that rather than present it as an exoneration.**

Density never predicted composition at tract level in the first place. The
largest correlation between population density and any outcome is 0.083, and
against gray share it is **0.031, not significant**. A control variable that
is unrelated to the outcome cannot absorb much, so the fact that the
correlations barely moved when we controlled for it is close to uninformative.

| Population density against | n | Spearman | p |
|---|---|---|---|
| Gray share | 698 | 0.031 | 0.408 |
| Green share | 698 | 0.009 | 0.820 |
| Blue share | 698 | −0.027 | 0.473 |
| Hybrid share | 698 | −0.083 | 0.029 |
| Investment per person (rank) | 698 | 0.017 | 0.659 |

**At block group the test is meaningful.** Density does relate to composition
there, and housing density is roughly twice the correlate that population
density is: 0.144 against gray share versus 0.061. Controlling for housing
density, the stronger measure, attenuates the access relationships by
**14 to 19 percent** while they all remain significant. The people-of-colour
relationship barely moves at all, under 1 percent.

So: treat the block-group density test as the real one, and the tract test as
weak evidence at best.

### 4.6 A correction we caught

**Our first spatial result was wrong, and the corrected version changes the
modelling path.** Investment per person initially returned a Moran's I of
0.006 with p = 0.07, which reads as no spatial clustering at all. That was an
artifact of the outcome's extreme skew of 18.7, where a handful of enormous
values dominate a variance-based statistic.

| Transform | n | Moran's I | p | Skew after transform |
|---|---|---|---|---|
| Raw | 698 | 0.006 | 0.070 | 18.72 |
| Log | 698 | **0.343** | **0.001** | 1.98 |
| Rank | 698 | **0.495** | **0.001** | 0.01 |

Rank-transformed, the most robust of the three, gives **0.495**. Every outcome
we tested is spatially clustered once skew is handled. This is the main reason
we are proposing a spatial specification next.

### 4.7 Block group behaves differently, and we would value your view

**At block group, composition is led by environmental proximity rather than by
vehicle access.** This was not what we expected, and we are presenting it as an
open direction rather than a result we have chased down.

| Indicator against gray share, block group | n | Spearman |
|---|---|---|
| Underground storage tanks | 1,838 | **+0.271** |
| Pre-1960 housing (lead paint indicator) | 1,838 | +0.242 |
| Hazardous waste site proximity | 1,837 | +0.232 |
| Fine particulate matter | 1,838 | −0.223 |
| Households with no vehicle | 1,832 | +0.203 |

Households with no vehicle, which is the single strongest indicator at tract
level, ranks fifth here. The environmental relationship is not an artifact of
roads being built where traffic is: removing road projects entirely, the
remaining gray infrastructure still correlates with traffic proximity at 0.127,
nitrogen dioxide at 0.149, underground storage tanks at 0.275 and air toxics
at 0.119, all significant after the density control.

**The environmental indicators are not behaving as one block, and we would
value your reading of this.** Figure 2b shows them as a single densely
intercorrelated group, but against gray share they split by sign, and the
split is not random with respect to what each measure is.

| Against gray share, block group | Spearman |
|---|---|
| **Regional air quality, running negative** | |
| Fine particulate matter | −0.22 |
| Ozone | −0.17 |
| **Localized point-source contamination, running positive** | |
| Underground storage tanks | +0.27 |
| Pre-1960 housing (lead paint indicator) | +0.24 |
| Hazardous waste site proximity | +0.23 |
| Superfund site proximity | +0.17 |
| Nitrogen dioxide | +0.15 |
| Traffic proximity | +0.12 |

All values are from Figure 1b, n between 1,828 and 1,838. The two measures
that vary smoothly across the whole county, fine particulate matter and ozone,
run one way; the measures that mark specific contaminated or industrial sites
run the other. We are offering this as an observation rather than a finding:
we have not tested it as a hypothesis, and grouping the indicators this way
was our reading after the fact, not a split defined in advance.

If it holds up, it bears directly on the block-group question in Section 6,
because it suggests the block-group data is describing where contaminated and
industrial land sits rather than where investment is targeted, which is
closer to an exposure study than an investment study.

---

## 5. Limitations

**Effect sizes are modest.** The relationships we report sit between about
0.13 and 0.31. What makes them credible is not their size but their
consistency: the same pattern appears across two grains, across separate
sub-categories of gray infrastructure, before and after a density control,
and under two different density measures. No single coefficient here would
carry an argument on its own.

**Coastal and seawall projects cannot be interpreted.** They reach 17 tracts,
below the 20-unit floor we set. They run opposite in sign to drainage, which
would be interesting if it were readable. We are listing this as a limitation
and are explicitly not treating it as a finding.

**Water and sewer clears the floor by one unit.** 21 receiving tracts. Its
coefficients are among the strongest we report, which is exactly why the
thinness of its base should be kept in view.

**The six-way gray split is lower confidence than the transit split.** 61
percent of projects classified as drainage also match the road pattern,
because project names bundle functions, as in "Roadway and Drainage
Improvements". They were assigned to drainage by a disclosed priority rule.
The transit versus non-transit split does not have this problem.

**Footprint misrepresentation persists in the data by design.** The two
surviving transit corridors carry 15.1 percent of filtered dollars as single
map points, because we did not reclassify your scale tags. Removing them moves
every headline correlation by under 2 percent, so this is a known distortion
with a measured and small effect.

**Housing density is unavailable at tract level.** No total housing unit table
was pulled at that grain; the available tables count occupied units only,
which would misstate density in coastal areas with high seasonal vacancy. The
tract density control therefore used the weaker of the two density measures.

**Income disparity is undefined for 34.5 percent of block groups.** The ADI
log-ratio formula divides by zero wherever a block group has no household in
one of the two income brackets, which is common at this geography. We left
these undefined rather than impute them.

---

## 6. Proposed next step, and what we need from you

### Proposed: spatial modelling

Every outcome we tested is spatially clustered once skew is handled
(Section 4.6). Treating each tract as an independent observation would
therefore overstate our confidence, because neighbouring tracts are not
independent draws.

A spatial specification separates two things ordinary regression blends
together: how much of a unit's investment relates to **its own**
characteristics, and how much relates to **its neighbours'**. That matters
here directly. If drainage investment concentrates in car-free, multi-unit
neighbourhoods, we want to know whether that is a property of each
neighbourhood or of the wider district it sits in, since those imply different
things about how allocation decisions are made.

### Six questions for you

1. **Which side of the seven duplicate pairs should we keep?** The published
   SVI indicators, or our ACS versions with the documented threshold
   departures in Section 2? These seven pairs correlate between 0.83 and 0.90,
   so keeping both sides is not viable. Two further pairs measuring the same
   construct, crowding at 0.74 and disability at 0.76, fall just under the
   0.8 cutoff and are your call too.
2. **Which single race and ethnicity measure should we use?** The eight shares
   sum to roughly 100 percent and cannot all be included. Hispanic share and
   overall minority share behave differently from each other here, as
   Section 4.4 shows.
3. **Are there variables you want dropped, or added?**
4. **Should we bring a physical-risk layer back in**, which would turn this
   into the three-way investment by risk by vulnerability question rather than
   the two-way one this document reports?
5. **Should block group remain an investment analysis**, or become the
   exposure and deprivation study the data there better supports, given
   Section 4.7?
6. **Is there anything you want dug into further before we start modelling?**
