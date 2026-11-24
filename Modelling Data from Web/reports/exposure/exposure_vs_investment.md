# Population exposure against investment (prompt 21, Stage B)

**Descriptive and correlational only.** No model was fitted and nothing was
imputed. The analysis tables were read and joined in memory; none was
modified. Run 5 November 2026.

- Script: `scripts/04_exposure/exposure_vs_investment.py`.
- Outputs: `outputs/exposure/stage_b/`.
- Full log: `outputs/exposure/stage_b/stage_b_log.txt`.

## Short summary

1. **Tracts with more residents exposed to flooding received more investment
   per person.**
   - Spearman with investment per person: sea level rise 3 ft **+0.39**,
     surge Category 3 **+0.36**, surge Category 4 **+0.24**.
   - Projects sited in the tract itself, which no allocation rule spread:
     +0.25, +0.27 and +0.20.
2. **Tracts whose residents live on hotter land received less.**
   - Population-weighted mean surface temperature **−0.27**.
   - Share of residents above 113.27°F **−0.25**.
   - Sited investment: −0.25 and −0.22.
   - The hottest third of tracts received **$1,669 per resident**; the
     coolest third received **$4,968**.
3. **Measuring people instead of land changes almost nothing for flooding.**
   - Across every outcome, the correlation with population share and the
     correlation with land share differ by at most 0.022 for sea level rise
     and surge.
   - For heat above the 95th percentile, the population measure gives
     slightly stronger correlations, by 0.04 to 0.05, and the bootstrap
     intervals exclude zero. The direction never changes.
4. **The coverage gap is large, and largest for heat.** 302 of 698 tracts
   have no project sited in them. They hold the following shares of exposed
   residents:

   | Hazard | Residents exposed in tracts with no sited project | Share of all exposed residents |
   |---|---|---|
   | Sea level rise 3 ft | 25,177 | 31% |
   | Surge Category 3 | 210,204 | 33% |
   | Surge Category 4 | 420,033 | 36% |
   | Heat above 113.27°F | 382,008 | **50%** |

   Those tracts receive only the flat per-person amount their municipality's
   and the county's projects spread across them. The heat gap is mostly in
   Hialeah, and the surge gap mostly in unincorporated south Dade.
5. **Every exposure measure is strongly clustered in space.** Moran's I is
   0.62 to 0.85 at tract and 0.64 to 0.88 at block group, so ordinary
   p-values here overstate significance.
6. **Block groups give the same signs** for the binaries and the type shares.
   Removing the 79 low-reliability block groups changes no correlation by
   more than 0.015.

These are associations between areas. They do not show that exposure drove
funding.

---

## 1. Sources

| Input | Publisher | Version | Period described | Released / built | Where it came from | Rows |
|---|---|---|---|---|---|---|
| Investment outcomes, tract | this project | `tract_analysis.csv` (`scripts/02_social/build_analysis_tables.py`) | projects with status Completed, Funded or Ongoing: 1,405 of 1,664, $8,553,271,609.50 | built before 5 Nov 2026 | `SCALE-R_Database.csv` (SCALE-R project database) | 698 tracts |
| Investment outcomes, block group | this project | `blockgroup_analysis.csv` | same projects | same | same | 1,843 block groups |
| Drainage and stormwater share | this project | Part 7 gray decomposition (`scripts/05_analysis/part7_gray_decomposition.py`) | same projects | 17 Sep 2026 | `outputs/correlation/part7_gray/2b_{tract,bg}_with_subcat_shares.csv` | 698 / 1,843 |
| Population exposure | this project | Stage A (`scripts/04_exposure/build_exposure_layers.py`) | see `population_exposure.md` Section 1 | 5 Nov 2026 | `exposure_tract.csv`, `exposure_blockgroup.csv` | 707 / 1,843 |
| Residents | US Census Bureau | ACS 5-year, 2024 release, B01003 and B01001 | 2020 to 2024 | 2024 5-year release | data.census.gov download | all units |
| Sea level rise | NOAA OCM | FL_SE inundation polygons | ground surface of the source lidar (years not in the local files) | layers changed Feb 2023 | local GeoPackage | |
| Storm surge | NOAA NHC | SLOSH MOM v4, high tide, reprocessed 06/2026 | hypothetical worst-case storms; DEMs cited 2014 to 2015 | 14 Jun 2026 | local GeoTIFFs | |
| Surface heat | USGS Landsat 8/9 C2 L2, via Planetary Computer | summer median composite | Jun to Sep 2021 to 2024 | built 13 Oct 2026 | `../output/lst/lst_composite_f.tif` | |
| Tract and block group geometry (for weights) | US Census Bureau | TIGER/Line 2024 | 1 Jan 2024 | 2024 | `data/raw/boundaries/` | |

---

## 2. What was compared

**Units**
- **Tract:** the existing 698-tract frame, which excludes the 9 tracts with
  no residents.
- **Block group:** `blockgroup_analysis.csv`. Its 1,833 block groups with
  residents enter the correlations, for the binaries and type shares only.
  As decided earlier, there is no per-person outcome at block group.

**Exposure measures.** One per hazard family at the primary scenarios
(decision D-040):

| Family | Primary measure | Main column | Count column | Land comparison |
|---|---|---|---|---|
| Sea level rise | 3 ft, ocean-connected | `slr_3ft_pop_share` | `slr_3ft_pop_exposed` | `slr_3ft_land_share` |
| Storm surge | Category 3, any inundation | `surge_cat3_any_pop_share` | `..._pop_exposed` | `..._land_share` |
| Storm surge | Category 4, any inundation | `surge_cat4_any_pop_share` | `..._pop_exposed` | `..._land_share` |
| Surface heat | population-weighted mean | `heat_lst_popwt_mean_f` | none | none (no land analogue was built) |
| Surface heat | at or above the county 95th percentile, 113.27°F | `heat_p95_pop_share` | `heat_p95_pop_exposed` | `heat_p95_land_share` |

The heat 75th percentile is not used (D-036). Category 5 enters only in its
corrected form, `surge_cat5max_any`, and only as sensitivity. The other
sensitivity scenarios are:
- sea level rise 1, 2 and 6 ft, and unconnected low-lying 3 ft;
- surge Categories 1 and 2, and more than 3 ft at Categories 3 and 4;
- heat at 100, 105 and 110°F.

**Outcomes**, as in the existing analysis:
- investment per person;
- total investment;
- investment per km² of land;
- received anything other than county money (`investment_any_excl_county`);
- has a project sited in the unit (`investment_any_single_unit`);
- type shares: gray, green, blue and hybrid. Blue is **sparse**: 28 projects,
  19 units with sited blue investment;
- the drainage and stormwater share of total investment.

Per person is reported once. Spearman uses ranks, so the raw and rank
versions of investment per person give the same correlation.

**Pairing rule (caution 12)**
- **Shares** (exposure share or mean temperature) go with per-person,
  per-area, binary and type share outcomes.
- **Exposed-resident counts** go only with total investment:
  - as a partial Spearman controlling for population (the result to read);
  - and raw, with a note that a count against a count partly measures size.

**Single-unit investment.** County and municipal money is spread by
population, so the main correlations are repeated on single-unit sited
investment only: sited dollars per person, sited total, and the sited-project
binary.

**Statistics**
- Spearman correlation, pairwise complete.
- Benjamini-Hochberg FDR adjustment within each family of tests:

  | Family | Tests |
  |---|---|
  | tract primary | 89 |
  | tract single-unit | 26 |
  | tract sensitivity | 60 |
  | block group, all | 63 |
  | block group, reliable only | 63 |
  | block group sensitivity | 24 |

- **P-values are not adjusted for spatial dependence.** Section 5 shows why
  that matters.
- Population versus land: the difference between the two correlations, with
  a 2,000-draw bootstrap 95% interval on the same tracts.

---

## 3. Results

### 3.1 Correlations, tract (698)

Population share against each outcome. Spearman rho, with FDR-adjusted
p-value in brackets where it is above 0.05.

| Outcome | SLR 3 ft | Surge Cat 3 | Surge Cat 4 | Heat, popwt mean | Heat ≥ p95 |
|---|---|---|---|---|---|
| Investment per person | **+0.388** | **+0.355** | **+0.238** | **−0.265** | **−0.249** |
| Investment per km² | +0.366 | +0.248 | +0.121 | −0.058 (0.14) | −0.080 |
| Received non-county money | +0.206 | +0.154 | +0.054 (0.17) | −0.046 (0.23) | −0.039 (0.31) |
| Project sited here | +0.155 | +0.192 | +0.139 | −0.179 | −0.151 |
| Gray share | +0.249 | +0.250 | +0.177 | −0.145 | −0.139 |
| Green share | −0.237 | −0.296 | −0.210 | +0.187 | +0.176 |
| Blue share (sparse) | −0.353 | −0.322 | −0.219 | +0.243 | +0.233 |
| Hybrid share | +0.061 (0.12) | +0.097 | +0.084 | −0.159 | −0.132 |
| Drainage and stormwater share | +0.149 | +0.191 | +0.132 | −0.110 | −0.128 |

80 of the 89 primary tract tests clear FDR 0.05. That reflects the sample
size and the spatial clustering more than the strength of the associations.
**Most effects are modest (0.1 to 0.4).**

**Total investment against exposed residents (counts)**

| Exposure | Raw Spearman (size drives both) | Partial, controlling for population |
|---|---|---|
| SLR 3 ft | +0.318 | **+0.384** |
| Surge Cat 3 | +0.357 | **+0.352** |
| Surge Cat 4 | +0.318 | **+0.261** |
| Heat ≥ p95 | −0.116 | **−0.260** |

**Single-unit sited investment only.** No allocation rule spread these
dollars.

| Outcome | SLR 3 ft | Surge Cat 3 | Surge Cat 4 | Heat, popwt mean | Heat ≥ p95 |
|---|---|---|---|---|---|
| Sited dollars per person | +0.251 | +0.265 | +0.204 | −0.251 | −0.221 |
| Project sited here | +0.155 | +0.192 | +0.139 | −0.179 | −0.151 |
| Sited total, partial for population (count) | +0.256 | +0.268 | +0.225 | n/a | −0.215 |

All of these clear FDR 0.05. The pattern holds on money that no allocation
rule spread. For flooding it is weaker, about two-thirds to nine-tenths as
strong as for all investment. For heat it is nearly unchanged. Part of the
all-investment flood correlation comes from municipal money: Miami Beach,
for example, spreads $3,934 per resident to every tract.

**Sensitivity scenarios** (population share against investment per person):

| Scenario | Spearman |
|---|---|
| SLR 1 ft / 2 ft / 6 ft | +0.37 / +0.37 / +0.26 |
| Unconnected low-lying 3 ft | **−0.16** |
| Surge Cat 1 / Cat 2 | +0.40 / +0.37 |
| Surge more than 3 ft, Cat 3 / Cat 4 | +0.33 / +0.29 |
| Surge Cat 5, corrected | **+0.01** |
| Heat ≥ 100 / 105 / 110°F | −0.19 / −0.22 / −0.26 |

The flood association weakens as the scenario widens. At Category 5,
corrected, 62% of residents are exposed, so the measure no longer separates
coastal places from inland ones. Unconnected low-lying land runs the other
way: it lies inland, in places that received less. All values are in
`spearman_tract.csv`.

### 3.2 Population versus land: does measuring people change the relationship?

**Not for flooding, and only slightly for heat.**

| Exposure | Largest change in rho across the 10 tract outcomes (population minus land) | Direction ever changes? |
|---|---|---|
| SLR 3 ft | 0.021 | no |
| Surge Cat 3 | 0.022 | no |
| Surge Cat 4 | 0.016 | no |
| Heat ≥ p95 | **0.047** | no |

**Flooding.** The two correlations agree to about 0.02 everywhere. For
example, for investment per person:

| Exposure | Population share | Land share |
|---|---|---|
| SLR 3 ft | +0.388 | +0.386 |
| Surge Cat 3 | +0.355 | +0.373 |

Some intervals exclude zero, but the differences are too small to matter.

**Heat above the 95th percentile.** The population measure is a little
stronger on every outcome: per person −0.249 against −0.204, gray share
−0.139 against −0.096, blue share +0.233 against +0.186. Each bootstrap
interval excludes zero.

**Why so little changes.** In Stage A, land and population shares ranked
tracts almost identically (Spearman +0.94 to +0.98). They differ mainly in a
handful of large, nearly empty wetland tracts, and those tracts are too few
to move a 698-tract rank correlation. **The change to population matters
most for naming places (Section 3.3), not for county-wide correlations.**

Block group gives the same answer: the largest difference is 0.041, again
for heat. Full tables: `pop_vs_land_tract.csv`, `pop_vs_land_bg.csv`.

### 3.3 The coverage gap

Tracts with exposed residents and **no project sited in them**. They receive
only money that their municipality's and the county's projects spread by
population. The ten tracts under 100 residents are excluded from every list
below.

| Exposure | Exposed residents, county | In tracts with no sited project | Share | Tracts with no sited project that have exposed residents |
|---|---|---|---|---|
| SLR 3 ft | 80,369 | 25,177 | 31% | 38 of 302 |
| Surge Cat 3 | 630,821 | 210,204 | 33% | 115 of 302 |
| Surge Cat 4 | 1,159,540 | 420,033 | 36% | 180 of 302 |
| Heat ≥ p95 | 757,550 | 382,008 | **50%** | 272 of 302 |

How to read the per-person column below:
- A tract with no sited project has an investment per person equal to its
  jurisdiction's flat rate.
- The rates are: Miami Beach $3,934, Homestead $1,789, Miami $879, Hialeah
  $720, and $566 for unincorporated tracts, which receive county money only.
- The SLR list is mostly Miami Beach: high spread-out money, but nothing
  sited in the tract.
- The surge lists are mostly unincorporated south Dade: 12 of 20 at Category
  3 and 14 of 20 at Category 4, which receive county money only. The same
  12 and 14 receive nothing but county money.
- The heat list is mostly Hialeah (14 of 20).

**Sea level rise 3 ft**

| # | Tract | Jurisdiction | Residents | Exposed residents | Share exposed | Investment total | Per person |
|---|---|---|---|---|---|---|---|
| 1 | 12086003915 | Miami Beach | 5,097 | 3,548 | 70% | $20,052,089 | $3,934 |
| 2 | 12086003911 | Miami Beach | 4,363 | 3,439 | 79% | $17,164,462 | $3,934 |
| 3 | 12086003916 | Miami Beach | 4,199 | 2,795 | 67% | $16,519,270 | $3,934 |
| 4 | 12086002709 | Miami | 4,113 | 2,112 | 51% | $3,613,611 | $879 |
| 5 | 12086004204 | Miami Beach | 2,087 | 1,797 | 86% | $8,210,459 | $3,934 |
| 6 | 12086004301 | Miami Beach | 2,686 | 1,490 | 55% | $10,566,983 | $3,934 |
| 7 | 12086004406 | Miami Beach | 2,314 | 1,169 | 51% | $9,103,499 | $3,934 |
| 8 | 12086004208 | Miami Beach | 1,290 | 1,094 | 85% | $5,074,984 | $3,934 |
| 9 | 12086010626 | Unincorporated Miami-Dade | 4,309 | 964 | 22% | $2,436,733 | $565 |
| 10 | 12086002707 | Miami | 2,552 | 882 | 35% | $2,242,143 | $879 |
| 11 | 12086004403 | Miami Beach | 2,548 | 746 | 29% | $10,024,077 | $3,934 |
| 12 | 12086006713 | Miami | 1,782 | 649 | 36% | $1,565,635 | $879 |
| 13 | 12086003909 | Unincorporated Miami-Dade | 1,492 | 610 | 41% | $843,724 | $565 |
| 14 | 12086004207 | Miami Beach | 1,823 | 451 | 25% | $7,171,857 | $3,934 |
| 15 | 12086005104 | Miami | 4,282 | 443 | 10% | $3,762,092 | $879 |
| 16 | 12086011408 | Unincorporated Miami-Dade | 5,236 | 425 | 8% | $2,960,951 | $565 |
| 17 | 12086006718 | Miami | 3,038 | 332 | 11% | $2,669,135 | $879 |
| 18 | 12086003603 | Miami | 2,154 | 259 | 12% | $1,892,467 | $879 |
| 19 | 12086003919 | Unincorporated Miami-Dade | 2,804 | 249 | 9% | $1,585,658 | $565 |
| 20 | 12086003705 | Miami | 1,932 | 232 | 12% | $1,697,422 | $879 |

**Surge Category 3**

| # | Tract | Jurisdiction | Residents | Exposed residents | Share exposed | Investment total | Per person |
|---|---|---|---|---|---|---|---|
| 1 | 12086010502 | Unincorporated Miami-Dade | 13,172 | 12,823 | 97% | $7,448,748 | $565 |
| 2 | 12086010804 | Unincorporated Miami-Dade | 8,140 | 8,008 | 98% | $4,603,159 | $565 |
| 3 | 12086011009 | Homestead | 7,849 | 7,064 | 90% | $14,041,947 | $1,789 |
| 4 | 12086010805 | Unincorporated Miami-Dade | 6,205 | 5,834 | 94% | $3,508,919 | $565 |
| 5 | 12086010709 | Unincorporated Miami-Dade | 5,974 | 5,822 | 97% | $3,378,289 | $565 |
| 6 | 12086010705 | Unincorporated Miami-Dade | 5,745 | 5,699 | 99% | $3,248,789 | $565 |
| 7 | 12086011302 | Homestead | 5,784 | 5,632 | 97% | $10,347,640 | $1,789 |
| 8 | 12086010625 | Cutler Bay | 5,647 | 5,263 | 93% | $3,674,644 | $651 |
| 9 | 12086010621 | Unincorporated Miami-Dade | 5,182 | 5,090 | 98% | $2,930,414 | $565 |
| 10 | 12086011008 | Homestead | 5,165 | 4,814 | 93% | $9,240,242 | $1,789 |
| 11 | 12086010213 | Unincorporated Miami-Dade | 5,189 | 4,794 | 92% | $2,934,372 | $565 |
| 12 | 12086003915 | Miami Beach | 5,097 | 4,699 | 92% | $20,052,089 | $3,934 |
| 13 | 12086003006 | Miami | 5,035 | 4,527 | 90% | $4,423,664 | $879 |
| 14 | 12086010622 | Unincorporated Miami-Dade | 4,611 | 4,515 | 98% | $2,607,514 | $565 |
| 15 | 12086010806 | Unincorporated Miami-Dade | 4,519 | 4,431 | 98% | $2,555,488 | $565 |
| 16 | 12086010208 | Unincorporated Miami-Dade | 4,844 | 4,261 | 88% | $2,739,275 | $565 |
| 17 | 12086003911 | Miami Beach | 4,363 | 4,162 | 95% | $17,164,462 | $3,934 |
| 18 | 12086011408 | Unincorporated Miami-Dade | 5,236 | 4,151 | 79% | $2,960,951 | $565 |
| 19 | 12086010626 | Unincorporated Miami-Dade | 4,309 | 4,097 | 95% | $2,436,733 | $565 |
| 20 | 12086002709 | Miami | 4,113 | 4,065 | 99% | $3,613,611 | $879 |

**Surge Category 4**

| # | Tract | Jurisdiction | Residents | Exposed residents | Share exposed | Investment total | Per person |
|---|---|---|---|---|---|---|---|
| 1 | 12086010502 | Unincorporated Miami-Dade | 13,172 | 12,864 | 98% | $7,448,748 | $565 |
| 2 | 12086010804 | Unincorporated Miami-Dade | 8,140 | 8,111 | 100% | $4,603,159 | $565 |
| 3 | 12086011009 | Homestead | 7,849 | 7,064 | 90% | $14,041,947 | $1,789 |
| 4 | 12086010805 | Unincorporated Miami-Dade | 6,205 | 6,193 | 100% | $3,508,919 | $565 |
| 5 | 12086005202 | Miami | 6,115 | 5,971 | 98% | $5,372,534 | $879 |
| 6 | 12086010709 | Unincorporated Miami-Dade | 5,974 | 5,831 | 98% | $3,378,289 | $565 |
| 7 | 12086011302 | Homestead | 5,784 | 5,784 | 100% | $10,347,640 | $1,789 |
| 8 | 12086019000 | Unincorporated Miami-Dade | 5,902 | 5,714 | 97% | $3,337,573 | $565 |
| 9 | 12086010705 | Unincorporated Miami-Dade | 5,745 | 5,703 | 99% | $3,248,789 | $565 |
| 10 | 12086008313 | Unincorporated Miami-Dade | 5,411 | 5,375 | 99% | $3,059,913 | $565 |
| 11 | 12086019200 | Unincorporated Miami-Dade | 5,323 | 5,279 | 99% | $3,010,149 | $565 |
| 12 | 12086019802 | Unincorporated Miami-Dade | 5,332 | 5,276 | 99% | $3,015,239 | $565 |
| 13 | 12086010625 | Cutler Bay | 5,647 | 5,264 | 93% | $3,674,644 | $651 |
| 14 | 12086011408 | Unincorporated Miami-Dade | 5,236 | 5,226 | 100% | $2,960,951 | $565 |
| 15 | 12086010213 | Unincorporated Miami-Dade | 5,189 | 5,165 | 100% | $2,934,372 | $565 |
| 16 | 12086010621 | Unincorporated Miami-Dade | 5,182 | 5,094 | 98% | $2,930,414 | $565 |
| 17 | 12086008419 | Unincorporated Miami-Dade | 5,272 | 4,959 | 94% | $2,981,309 | $565 |
| 18 | 12086003006 | Miami | 5,035 | 4,898 | 97% | $4,423,664 | $879 |
| 19 | 12086010208 | Unincorporated Miami-Dade | 4,844 | 4,819 | 99% | $2,739,275 | $565 |
| 20 | 12086011008 | Homestead | 5,165 | 4,814 | 93% | $9,240,242 | $1,789 |

**Heat at or above 113.27°F**

| # | Tract | Jurisdiction | Residents | Exposed residents | Share exposed | Investment total | Per person |
|---|---|---|---|---|---|---|---|
| 1 | 12086005708 | Miami | 6,441 | 5,782 | 90% | $5,658,952 | $879 |
| 2 | 12086013500 | Hialeah | 5,444 | 5,419 | 100% | $3,919,497 | $720 |
| 3 | 12086013700 | Hialeah Gardens | 6,284 | 5,127 | 82% | $4,941,421 | $786 |
| 4 | 12086000710 | Hialeah | 4,901 | 4,865 | 99% | $3,528,555 | $720 |
| 5 | 12086013100 | Hialeah | 4,975 | 4,791 | 96% | $3,581,833 | $720 |
| 6 | 12086013802 | Hialeah | 4,506 | 4,506 | 100% | $3,244,168 | $720 |
| 7 | 12086013400 | Hialeah | 4,886 | 4,453 | 91% | $3,517,756 | $720 |
| 8 | 12086001606 | Hialeah | 4,395 | 4,373 | 99% | $3,164,252 | $720 |
| 9 | 12086013000 | Hialeah | 4,388 | 4,317 | 98% | $3,159,212 | $720 |
| 10 | 12086005306 | Miami | 4,275 | 4,220 | 99% | $3,755,941 | $879 |
| 11 | 12086000605 | Hialeah | 4,920 | 4,122 | 84% | $3,542,235 | $720 |
| 12 | 12086012900 | Hialeah | 4,149 | 4,071 | 98% | $2,987,140 | $720 |
| 13 | 12086009322 | Hialeah | 4,032 | 4,032 | 100% | $2,902,904 | $720 |
| 14 | 12086005406 | Miami | 3,976 | 3,902 | 98% | $3,493,245 | $879 |
| 15 | 12086000807 | Hialeah | 3,776 | 3,767 | 100% | $2,718,593 | $720 |
| 16 | 12086009324 | Hialeah | 3,997 | 3,728 | 93% | $2,877,706 | $720 |
| 17 | 12086000720 | Hialeah | 3,671 | 3,627 | 99% | $2,642,997 | $720 |
| 18 | 12086012102 | Unincorporated Miami-Dade | 5,242 | 3,603 | 69% | $2,964,344 | $565 |
| 19 | 12086009314 | Hialeah | 3,819 | 3,556 | 93% | $2,749,552 | $720 |
| 20 | 12086016000 | Unincorporated Miami-Dade | 4,360 | 3,543 | 81% | $2,465,574 | $565 |

**Heat, population-weighted mean (hottest 20)**

| # | Tract | Jurisdiction | Residents | Mean surface temperature | Investment total | Per person |
|---|---|---|---|---|---|---|
| 1 | 12086013500 | Hialeah | 5,444 | 122.3°F | $3,919,497 | $720 |
| 2 | 12086013301 | Hialeah Gardens | 2,852 | 122.1°F | $2,242,669 | $786 |
| 3 | 12086012900 | Hialeah | 4,149 | 119.6°F | $2,987,140 | $720 |
| 4 | 12086009322 | Hialeah | 4,032 | 119.6°F | $2,902,904 | $720 |
| 5 | 12086000710 | Hialeah | 4,901 | 119.5°F | $3,528,555 | $720 |
| 6 | 12086013302 | Hialeah Gardens | 3,776 | 119.2°F | $2,969,256 | $786 |
| 7 | 12086013802 | Hialeah | 4,506 | 118.7°F | $3,244,168 | $720 |
| 8 | 12086000720 | Hialeah | 3,671 | 118.4°F | $2,642,997 | $720 |
| 9 | 12086000713 | Hialeah | 3,032 | 118.1°F | $2,182,938 | $720 |
| 10 | 12086000807 | Hialeah | 3,776 | 118.1°F | $2,718,593 | $720 |
| 11 | 12086000719 | Hialeah | 1,288 | 118.1°F | $927,317 | $720 |
| 12 | 12086013100 | Hialeah | 4,975 | 118.1°F | $3,581,833 | $720 |
| 13 | 12086013400 | Hialeah | 4,886 | 118.1°F | $3,517,756 | $720 |
| 14 | 12086013000 | Hialeah | 4,388 | 117.9°F | $3,159,212 | $720 |
| 15 | 12086009314 | Hialeah | 3,819 | 117.5°F | $2,749,552 | $720 |
| 16 | 12086001606 | Hialeah | 4,395 | 117.4°F | $3,164,252 | $720 |
| 17 | 12086000806 | Hialeah | 4,132 | 117.2°F | $2,974,901 | $720 |
| 18 | 12086013700 | Hialeah Gardens | 6,284 | 117.2°F | $4,941,421 | $786 |
| 19 | 12086009324 | Hialeah | 3,997 | 117.2°F | $2,877,706 | $720 |
| 20 | 12086009061 | Sweetwater | 3,166 | 117.1°F | $6,244,439 | $1,972 |

Files: `coverage_gap_summary.csv`, `coverage_gap_top20.csv`,
`coverage_gap_top20_heat_popwt.csv`.

### 3.4 Investment per exposed resident, by exposure tercile

For each hazard, tracts are split into those with no exposed residents and
then terciles of the exposed share among the rest. Heat's population-weighted
mean, which every tract has, is split into plain terciles. Each column is
total dollars in the group divided by its residents or its exposed residents.

| Exposure | Group | Tracts | Per resident | Sited, per resident | Per exposed resident | Share of tracts with a sited project |
|---|---|---|---|---|---|---|
| SLR 3 ft | none exposed | 556 | $1,765 | $1,002 | n/a | 53% |
| | low (to 2.4%) | 48 | $5,182 | $4,260 | $649,391 | 77% |
| | mid (2.5 to 17%) | 47 | $9,628 | $8,482 | $125,118 | 70% |
| | high (17 to 92%) | 47 | $11,122 | $8,333 | $27,437 | 70% |
| Surge Cat 3 | none exposed | 346 | $1,509 | $801 | n/a | 47% |
| | low (to 14%) | 118 | $1,563 | $800 | $40,690 | 64% |
| | mid (14 to 70%) | 117 | $5,487 | $4,460 | $13,962 | 74% |
| | high (70 to 100%) | 117 | $6,363 | $4,810 | $6,981 | 63% |
| Surge Cat 4 | none exposed | 213 | $1,418 | $735 | n/a | 44% |
| | low (to 40%) | 162 | $1,758 | $963 | $13,841 | 60% |
| | mid (40 to 91%) | 161 | $4,703 | $3,583 | $6,623 | 69% |
| | high (91 to 100%) | 162 | $4,701 | $3,554 | $4,816 | 58% |
| Heat, popwt mean | coolest (97 to 109°F) | 233 | $4,968 | $3,732 | n/a | 65% |
| | middle (109 to 112°F) | 232 | $2,481 | $1,719 | n/a | 59% |
| | hottest (112 to 122°F) | 233 | **$1,669** | **$895** | n/a | **47%** |
| Heat ≥ p95 | none exposed | 75 | $5,510 | $3,906 | n/a | 65% |
| | low (to 11%) | 208 | $4,912 | $3,886 | $124,297 | 62% |
| | mid (11 to 38%) | 207 | $1,897 | $1,120 | $8,296 | 58% |
| | high (38 to 100%) | 208 | **$1,565** | **$791** | $2,400 | **46%** |

**How to read it**
- **Per resident** rises with flood exposure: from $1,765 in tracts with no
  one exposed to sea level rise, to $11,122 in the most exposed third.
- Per resident **falls** with heat: from $4,968 in the coolest third to
  $1,669 in the hottest.
- **Per exposed resident** always falls as exposure rises. That is partly
  arithmetic: dividing by a small exposed count gives large numbers. The
  low-exposure groups, with hundreds of thousands of dollars per exposed
  resident, are not meaningful on their own.
- The most-exposed third has $27,437 per exposed resident for sea level rise
  and $2,400 for heat above the 95th percentile.

**Follow-up: [Investment by surface heat tercile, by project hazard focus](heat_tercile_investment.md).**
It breaks the heat tercile result down by `Hazard_Focus`, gives pooled, mean
and median versions, and drops the projects that dominate the heat dollars.
Extreme Heat projects show the same pattern: the coolest third received $240
per resident from them and the hottest third $36. The gap holds without The
Underline and SCALER-0595.

### 3.5 Spatial clustering (Moran's I)

Method: rank-transformed values, k = 6 nearest neighbours, row-standardised,
999 permutations, seeded (12086, the same seed as parts 5 and 6b), so reruns
give identical results (D-067).

| Exposure | Tract (698) | Block group (1,833) |
|---|---|---|
| SLR 3 ft, population share | 0.660 | 0.745 |
| Surge Cat 3, population share | 0.802 | 0.841 |
| Surge Cat 4, population share | 0.847 | 0.876 |
| Heat, population-weighted mean | 0.631 | 0.667 |
| Heat ≥ p95, population share | 0.620 | 0.642 |

All have permutation p = 0.001, the smallest possible with 999 permutations.

**Every exposure measure is strongly clustered.** Neighbouring tracts are far
more alike than independent draws would be. Investment per person is also
clustered: its rank Moran's I is 0.495 in `outputs/correlation/part6_followup/6b_moran_transforms.csv`.
Correlations between two clustered variables carry much less independent
information than n suggests. The FDR-adjusted p-values
above are therefore **too small**, and the correlations should be read for
size and sign, not significance.

### 3.6 Block group (binaries and type shares only)

| Outcome | SLR 3 ft | Surge Cat 3 | Surge Cat 4 | Heat, popwt mean | Heat ≥ p95 |
|---|---|---|---|---|---|
| Received non-county money | +0.240 | +0.175 | +0.064 | −0.056 | −0.069 |
| Project sited here | +0.135 | +0.154 | +0.118 | −0.150 | −0.127 |
| Gray share | +0.293 | +0.286 | +0.194 | −0.157 | −0.168 |
| Green share | −0.291 | −0.305 | −0.199 | +0.184 | +0.187 |
| Blue share (sparse) | −0.351 | −0.321 | −0.206 | +0.233 | +0.234 |
| Hybrid share | +0.012 (0.61) | +0.032 (0.17) | +0.042 (0.08) | −0.096 | −0.073 |
| Drainage and stormwater share | +0.174 | +0.220 | +0.161 | −0.127 | −0.157 |

This uses all 1,833 block groups with residents. FDR-adjusted p is below
0.05 except where shown in brackets.

**Without the 79 low-reliability block groups** (CV above 40%), n = 1,754,
every correlation moves by 0.015 or less. One sign changes: a correlation
that was already essentially zero (see the hybrid share row). Examples:
- gray share against SLR 3 ft: +0.306 instead of +0.293;
- project sited here against heat, population-weighted mean: −0.149 instead
  of −0.150.

**Population versus land at block group.** The largest difference is 0.041.
The only intervals that exclude zero of any size are for heat above the 95th
percentile, as at tract. For the flood measures, the intervals that exclude
zero all show differences of 0.015 or less.

Files: `spearman_bg.csv`, `pop_vs_land_bg.csv`.

---

## 4. Reading the results together

- **Places with more residents exposed to coastal flooding received more**,
  and more of what they received was gray and drainage infrastructure.
  **Places with more residents on the hottest land received less**, and a
  larger share of what they received was green and blue. The blue share is
  sparse, and type shares are mostly made up of county-wide money spread to
  every tract.
- Measuring people instead of land **does not change these relationships**.
  Its value is in naming the right places, for example Miami Beach rather
  than the Everglades, and in counting how many exposed residents sit in
  tracts with nothing sited in them.
- The largest uncovered group is **heat**. Half the residents on land above
  113°F live in tracts with no project sited in them, mostly in Hialeah.

---

## 5. Limitations

- **The hazard maps predate many of the projects.** Both flood layers are
  built on elevation surveys from before much of this work, so they do not
  show any protection the projects added. Where work was done, exposure may
  look higher than it now is. That would push the flood correlations
  upward. The direction of time is also unknown: these data cannot say
  whether exposure led to funding or the reverse.
- **Correlation does not show that exposure drove funding.** Coastal tracts
  differ from inland ones in many ways, including wealth, municipal budgets,
  density and tourism. Any of these could produce the same pattern. No
  controls were applied, by design.
- **Area-level results only.** Every number describes tracts or block groups,
  not people. "Tracts with more exposed residents received more" does not
  mean exposed people received more.
- **Allocation rules shape the outcomes.** Municipal and county money is
  spread by population, so every tract in a city gets the same amount per
  person from those projects. The single-unit results remove this, and the
  pattern weakens but holds.
- **Spatial dependence.** Exposure is strongly clustered (Moran's I 0.62 to
  0.88), so the p-values overstate significance. They were not adjusted for
  space.
- **Worst-case surge, screening-level sea level rise, and surface heat that
  is not air heat.** All the hazard cautions in `population_exposure.md`
  Section 5 apply here unchanged.
- **Sparse blue.** Blue share rests on 28 projects. Its correlations are
  shown but should not be read as findings.
- **Small and unreliable units.** The ten tracts under 100 residents are
  excluded from every list. The 79 low-reliability block groups were tested
  both ways and change nothing material.
