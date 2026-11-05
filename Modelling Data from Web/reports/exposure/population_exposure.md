# Population exposure layers (prompt 21, Stage A)

**Data preparation and description only.** Residents living on land exposed
to sea level rise, storm surge and surface heat were counted for every
Miami-Dade tract (707) and block group (1,843). Nothing was joined to the
analysis tables, nothing was correlated with investment, and no existing data
table or website output was modified. Built 5 November 2026.

| Output | Rows | Columns |
|---|---|---|
| `exposure_tract.csv` | 707 | GEOID + 79 |
| `exposure_blockgroup.csv` | 1,843 | GEOID + 80 |

Scripts:
- `scripts/04_exposure/build_exposure_layers.py` builds the layers, with checkpoints per
  layer in `outputs/exposure/checkpoints/`.
- `scripts/04_exposure/describe_exposure_layers.py` runs the A6 description and writes
  tables to `outputs/exposure/stage_a/exposure_layers/`.
- `scripts/common/population_surface.py` holds the population surface.

Logs: `outputs/exposure/stage_a/exposure_layers_log.txt`, `outputs/exposure/stage_a/exposure_describe_log.txt`.
County totals: `outputs/exposure/stage_a/exposure_county_totals.csv`. The comparison with the
website's block file: `outputs/exposure/stage_a/exposure_vs_website_blocks.csv`.

---

## 1. Sources

| Input | Publisher | Dataset and version | Period described | Released | Where it came from (local file) | IDs |
|---|---|---|---|---|---|---|
| Residents per block group | US Census Bureau | ACS 5-year, 2024 release, Detailed Table | 2020 to 2024 (5-year average) | 2024 5-year release; release date not recorded in the download | data.census.gov download: `data/raw/social/acs_blockgroup/B01003-Total Population/ACSDT5Y2024.B01003-Data.csv` | B01003_001E, B01003_001M |
| Where residents sit within a block group | US Census Bureau | 2020 Census, TIGER/Line 2020 tabulation blocks with P1 counts | 1 April 2020 | 2021 | `data/raw/boundaries/tl_2020_12_tabblock20.zip` from https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/ | POP20, ALAND20, GEOID20 |
| Tracts, block groups, water, places | US Census Bureau | TIGER/Line 2024 | boundaries as of 1 January 2024 | 2024 | `data/raw/boundaries/tl_2024_12_tract.zip`, `tl_2024_12_bg.zip`, `tl_2024_12086_areawater.zip`, `tl_2024_12_place.zip` | GEOID, ALAND, AWATER, CLASSFP |
| Sea level rise | NOAA Office for Coastal Management | Sea Level Rise Inundation Data, Florida southeast (FL_SE), vector polygons | elevation ground surface of the source lidar; water levels above MHHW. The ground-survey years are not in the local files | layers last changed 13 to 14 February 2023 (GeoPackage contents table) | NOAA OCM Digital Coast (per the README); exact download URL not recorded. `data/raw/physical/sea_level_rise/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg` | layers `FL_SE_slr_{1,2,3,6}_0ft`, `FL_SE_low_3_0ft`; InPort 48105, 48106 |
| Storm surge | NOAA National Hurricane Center | National Storm Surge Hazard Map v4, SLOSH Maximum of MOMs, high tide, reprocessed 06/2026 | hypothetical worst-case storms; ground from NOAA OCM DEMs (cited 2015) and USGS 3DEP (cited 2014); water mask from NHD | 14 June 2026 (metadata pubdate) | `data/raw/physical/storm_surge/US_SLOSH_MOM_Inundation_v4_20260617/` | `us_Category{1..5}_MOM_Inundation_HIGH.tif` |
| Surface heat | USGS (Landsat 8/9), via Microsoft Planetary Computer | Landsat Collection 2 Level-2 surface temperature, summer median composite | June to September 2021 to 2024, overpass about 10:30 to 11 am | composite built 13 October 2026 by `../scripts/python/build_lst_layer.py` | `../output/lst/lst_composite_f.tif` (collection `landsat-c2-l2`, scenes under 30% cloud, at least 3 clear observations per pixel) | band `lwir11`, `qa_pixel` |
| FEMA loss (correlation screen only) | FEMA | National Risk Index, tract table. No version field in the file; inland flooding columns show it postdates the IFLD rebuild (`nri_audit.md`) | not stated in the file | file name says December 2025 | `../fema_miami_dade_dec_2025.csv` | HWAV_EALT, CFLD_EALT, CFLD_EALB, IFLD_EALT, IFLD_EALB, HRCN_EALT, HRCN_EALB |
| Housing units (heat versus density only) | EPA EJScreen v2.3, PEDP / Harvard Dataverse reconstruction | ACS 2018 to 2022 inside EJScreen 2024 | 2018 to 2022 | 2024 | `data/raw/social/ejscreen/EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv` | ACSTOTHU |
| Website comparison only | this project | `src/exposure/data/slr.json`, `surge.json`, `heat.json`, `exposure_blocks.json` | as above | 21 October 2026 | `../src/exposure/data/` | not used as inputs |

**What the local metadata files say about limitations.**

- **NOAA sea level rise.** The README (`NOAA_OCM_SLR_Data_README.txt`) says
  nothing about limitations. It only lists the three InPort metadata
  records, the data types, and contact links. The GeoPackage's own
  metadata entries are empty QGIS templates. So the "modified bathtub" and
  "potential scale, not exact location" wording in the brief comes from
  NOAA's online documentation, not from any file on disk.
- **NHC storm surge.** The XML metadata carries the limitations directly:
  - the maps show "the scale of potential flooding, not the exact location";
  - they do not account for "erosion, subsidence, sea-level change, or future
    construction";
  - they are for use "at a city/community level (not for a parcel level or
    grid cell assessment)";
  - "No single hurricane will produce the regional flooding depicted";
  - the MOMs "represent the worst case scenario".
  `surge_inspection.md` lists the remaining limitations: waves, rainfall,
  missing levees and dependence on the DEM.

---

## 2. Method

### 2.1 Population surface (reused, not rebuilt)

The population surface is the website Exposure page's logic, unchanged:
1. Take ACS 2020 to 2024 total population per block group.
2. Split each block group's count across its 2020 census blocks in proportion
   to their 2020 counts. A block group with nobody in 2020 is split by land
   area instead.
3. Keep only each block's land: the block minus every TIGER 2024 area water
   feature.

That gives 25,805 populated blocks holding **2,738,356 residents, exactly the
ACS county total**. Seven populated blocks lie wholly under mapped water.
They are boats and marinas with Census land area 0, and they keep their full
shape.

**How the website script was handled.** The prompt said not to change
`scripts/website/build_population_exposure.py`. Early in this run I added an
optional `crs` argument to its `load_blocks()`. **That edit was reverted**
with `git checkout`, so the file is identical to its committed version. The
same logic now lives in a new module, `scripts/common/population_surface.py`, which
the build imports. I checked that it reproduces the block checkpoint exactly:
- same 25,805 block IDs in the same order;
- largest difference in residents per block: 0.0;
- largest difference in land area: 0.0 m².

The website script, its JSON files and its images were not rerun or touched.

### 2.2 The core assumption

**Within each census block, residents are assumed to be spread evenly over
the block's land.** So:

> exposed residents in a block = block residents × share of the block's land
> that is exposed

Blocks are summed to block groups (first 12 digits of the block GEOID) and to
tracts (first 11). This is an assumption, not a measurement. Parks, parking
lots, golf courses and canals inside a block are given residents they do not
have (Section 5, item 6). Blocks are used only to place people. No result is
reported for a single block.

### 2.3 Hazard layers

All area work is in EPSG:6346. Each raster is read in its native grid, and
the block land outlines are projected onto that grid. The website images were
not used.

**Sea level rise.** Polygon overlay with exact areas. The steps are those of
`process_slr.py`:
1. read the Miami-Dade bounding box;
2. reproject to EPSG:6346;
3. check validity (0 invalid geometries in every layer);
4. clip to county land;
5. subdivide into pieces of at most 2,000 vertices;
6. intersect with each block's land, union the pieces per block, and take the
   area.

The exposed share is inundated block land divided by block land area.
Layers: ocean-connected `_slr_` at 1, 2, 3 and 6 ft, and unconnected `_low_`
at 3 ft, kept separate. Primary scenario: **3 ft**.

**Storm surge.** Raw pixel values, handled as in `process_surge.py`:
- 255 on land means not inundated, and stays in the denominator;
- 99 is levee, counted separately (0 pixels in Miami-Dade);
- classes 1 to 21 are depth bins.

Two thresholds per category:
- **any inundation**: class 1 or more;
- **more than 3 ft**: class 4 or more.

There is also **`cat5max`**: for each pixel, the deepest class across
Categories 1 to 5. It corrects the known Category 5 hole, where pixels wet at
Category 4 or lower are 255 at Category 5. Primary: **Category 3 and
Category 4, any inundation**. The reading window is the exact one
`process_surge.py` used.

**Surface heat.** The Landsat composite as built. I read it and did not
rebuild it.

| Property | Value |
|---|---|
| CRS | EPSG:32617 (WGS 84 / UTM 17N) |
| Resolution | 30 m |
| Size | 2,524 × 3,110 pixels |
| Data type | float32 |
| Nodata | NaN |
| Band description | "Land surface temperature (degrees F), median composite" |

EPSG:32617 and EPSG:6346 are both UTM zone 17N. They differ only in datum, by
about a metre, which is negligible at 30 m.

Thresholds:
- **primary (as built):** residents on land at or above the county 75th and
  95th percentiles of land pixels;
- **sensitivity:** 100, 105 and 110°F.

> **Update, 5 November 2026 (decision D-036 in `DECISIONS.md`).** The 75th
> percentile columns (`heat_p75_*`) are kept in the tables but are **not
> used**: 96% of residents live above it, so it cannot tell tracts apart.
> The primary heat measures are now the population-weighted mean surface
> temperature (`heat_lst_popwt_mean_f`) and the share of residents at or
> above the 95th percentile, 113.27°F (`heat_p95_pop_share`).

The continuous measure is `heat_lst_popwt_mean_f`: each block's mean surface
temperature over its valid land cells, weighted by the block's residents.
Missing pixels are NA, never 0. Within a block, the exposed share is taken
over valid cells only.

**County percentiles (computed from the raster).** They use the 5,417,536
valid 30 m pixels whose centre falls on county land (tracts minus area
water).

| Percentile | This run | Website `heat.json` | All valid pixels in the raster |
|---|---|---|---|
| 75th | **100.84°F** | 100.7°F | 100.64°F |
| 95th | **113.27°F** | 113.1°F | 113.04°F |

Why the website differs:
- `build_viz_exposure.py` computes its percentiles from a 60 m Web Mercator
  copy made with **average** resampling;
- that copy is clipped to county land at 60 m;
- it is rounded to 0.1°F.

Averaging four pixels into one pulls each pixel toward its neighbours, so the
website's percentiles come out about 0.15°F lower. The raw raster without the
land mask gives 100.64°F and 113.04°F, because it also counts water edges
and off-county pixels.

**Fractional pixel coverage (caution 15).** exactextract is not installed
and nothing was downloaded, so each raster pixel was split into 4 × 4
sub-cells. A block takes the share of its sub-cells that are exposed. Every
raster layer was also computed with the pixel-centre rule, for comparison.

A block holding no sub-cell would take the value of the pixel under its
representative point:
- surge: no block needed this at either resolution;
- heat: none at 4 × 4, and 4 blocks under the pixel-centre rule.

Supersampled cell counts times pixel area reproduce each block's land area
to a median of +0.6%. That gap is the nominal pixel area, 90.2 m², which
holds only near the county's midpoint latitude. It affects shares in the
same way top and bottom, so it does not bias them.

**Not built:**
- **Flood zones.** The FEMA flood zone CSV in
  `data/raw/physical/flood_zones/` has zone codes and areas but
  no geometry. Skipped; still pending.
- **Building footprint sensitivity.** There is no raw Miami-Dade building
  footprint file anywhere on the machine. Only the website's vector tiles
  exist (`public/layers/buildings`, made from `BuildingFootprint2D.geojson`,
  which is not on disk). Skipped. Nothing was downloaded.
- **Summer 2025 Landsat.** Those scenes now exist, but the composite was not
  rerun for 2025.

### 2.4 Variables

The same columns appear in both files. Each scenario key below has
`_pop_exposed`, `_pop_share` and `_land_share` columns.

| Hazard | Scenario keys |
|---|---|
| Sea level rise | `slr_1ft`, `slr_2ft`, `slr_3ft`, `slr_6ft`, `low_3ft` |
| Storm surge | `surge_cat{1..5}_any`, `surge_cat{1..5}_over3ft`, `surge_cat5max_any`, `surge_cat5max_over3ft` |
| Surface heat | `heat_p75`, `heat_p95`, `heat_100f`, `heat_105f`, `heat_110f` |

The three column types:
- `_pop_exposed`: residents on exposed land.
- `_pop_share`: exposed residents divided by unit population. For heat, the
  denominator is residents in blocks with at least one valid pixel. That is
  everyone here.
- `_land_share`: the existing land shares from `slr_*.csv` and `surge_*.csv`,
  carried alongside. For `cat5max` and heat, which had no existing land
  share, it was computed the same way: pixel centres on unit land. Heat land
  shares use valid pixels only.

Other columns:

| Column | Meaning |
|---|---|
| `heat_lst_popwt_mean_f` | population-weighted mean surface temperature |
| `heat_nodata_share` | share of the unit's populated-block land with no valid pixel |
| `heat_land_nodata_share` | the same for all unit land |
| `heat_pop_no_valid_pixel` | residents in blocks with no valid pixel |
| `surge_cat5_hole_pop` | residents on land wet at Category 4 or lower but not wet at Category 5 |
| `surge_cat5_hole_pop_share` | that count divided by unit population |
| `surge_cat5_hole_flag` | 1 where the hole holds at least 1% of the unit's residents. The 1% cut is my choice; the continuous share is in the file |
| `low_pop_flag` | 1 for units under 100 residents |
| `jurisdiction` | the municipality containing the unit's centroid, or Unincorporated Miami-Dade |
| `ALAND` | Census land area |

Block group file only:
- `bg_pop_moe`;
- `bg_pop_cv` = MOE / 1.645 / estimate;
- `bg_low_reliability`: 1 if CV is above 40%, NA where there are no residents.

Tract file only:
- `acs_tract_population`: the ACS tract table, as a cross-check;
- `n_bg_low_reliability`.

Units with no residents (9 tracts, 10 block groups) keep their row. Their
counts are 0 and their population shares are NA. GEOID is a string.

---

## 3. Validation

**Population**
- Residents over all blocks: 2,738,356.0. ACS county total: 2,738,356. They
  match.
- Each unit's population equals the sum of its blocks; the largest difference
  is 0.000000.
- Tract population (summed from ACS block groups) equals the ACS tract table
  (B01001) in all 707 tracts.
- Rows: 707 tracts and 1,843 block groups. GEOIDs are unique strings, all
  starting `12086`.

**Ranges**
- 0 violations: every share is within [0, 1], and exposed residents never
  exceed population, in any column at either grain.
- Block groups sum to tracts exactly: the largest difference over every count
  column is 0.000000.

**Monotonicity**
- 0 violations in sea level rise 1 ≤ 2 ≤ 3 ≤ 6 ft, at both grains.
- 0 violations across the five heat thresholds, in order 100°F, p75
  (100.84°F), 105°F, 110°F, p95 (113.27°F).

**Surge reversals (reported, not forced)**

Units where a higher category exposes fewer residents:

| Step | Tracts | Residents lost | Block groups |
|---|---|---|---|
| Cat 1 → 2 | 4 | 415 | 7 |
| Cat 2 → 3 | 3 | 181 | 5 |
| Cat 3 → 4 | 2 | 1,091 | 6 |
| Cat 4 → 5 | **26** | **16,599** | 59 |
| Cat 4 → cat5max | 0 | 0 | 0 |

**The Category 5 hole:** 18,928 residents live on land wet at Category 4 or
lower that is dry at Category 5. The flag marks 30 tracts and 63 block
groups. The worst are City of Miami tracts 006302 to 007104, for example
006501 with 3,156 residents and 006401 with 2,114.

**Flags**
- `low_pop_flag`: 10 tracts (the 9 empty tracts plus 12086981100, the
  28-person Pennsuco tract) and 16 block groups.
- Block group CV, for the 1,833 block groups with residents:

| CV band | Block groups |
|---|---|
| 12% or less (high) | 93 |
| 12 to 40% (medium) | 1,661 |
| Above 40% (low) | **79** |

The low-reliability block groups have a median population of 785, with a
range of 6 to 2,699.

**Extent and nodata (caution 16)**
- All 25,805 blocks lie wholly inside the surge window and inside the
  Landsat raster.
- Surge has no nodata on land. 255 means dry, and the whole county is inside
  SLOSH coverage.
- Heat: 0.84% of county land pixels have no valid value (cloud, shadow or
  water flags). No populated block lacks a valid pixel, so no resident has
  an NA.
- `heat_nodata_share` is above 10% in 4 tracts. The highest are 000129 in
  Aventura (57%) and 001204 in North Miami (33%). Both come from populated
  water blocks whose full shape is open water, which Landsat masks. Those
  blocks hold 8.5 and 16 residents. All other land in those tracts has data.

**Fractional versus pixel-centre (caution 15).** County totals differ by at
most 1,186 residents (0.05%). Every surge and heat scenario is within 0.1%.
The fractional method matters for small blocks, not for county totals.

**County totals against the website's JSON files**

| Scenario | This run (fractional) | Pixel centre | Website | Difference |
|---|---|---|---|---|
| SLR 1 ft | 8,517 | n/a | 6,764 | +25.9% |
| SLR 2 ft | 18,129 | n/a | 15,853 | +14.4% |
| SLR 3 ft | 80,369 | n/a | 76,503 | +5.1% |
| SLR 6 ft | 887,533 | n/a | 870,976 | +1.9% |
| Surge Cat 1 | 126,081 | 125,996 | 124,521 | +1.3% |
| Surge Cat 2 | 326,210 | 326,151 | 325,017 | +0.4% |
| Surge Cat 3 | 630,821 | 630,904 | 629,975 | +0.1% |
| Surge Cat 4 | 1,159,540 | 1,159,745 | 1,159,065 | +0.0% |
| Surge cat5max (website "Cat 5") | 1,695,791 | 1,696,239 | 1,692,956 | +0.2% |
| Heat ≥ 100°F | 2,656,542 | 2,657,344 | 2,652,814 | +0.1% |
| Heat ≥ 105°F | 2,350,153 | 2,351,339 | 2,346,709 | +0.1% |
| Heat ≥ 110°F | 1,539,073 | 1,538,905 | 1,500,953 | +2.5% |

Why they differ:
- **Sea level rise.** This run intersects NOAA's polygons exactly. The
  website rasterized them to 30 m pixels and counted a pixel only where its
  centre fell inside. That drops the thin flooded strips along seawalls and
  shorelines, which are a large part of the small 1 ft and 2 ft totals.
- **Surge.** The website counts a pixel at Category N if it is wet at N **or
  any lower category**. Raw Category 5 has the hole, so the website's
  "Category 5" is effectively `cat5max`. Its 30 m pixels were also resampled
  by nearest neighbour into Web Mercator.
- **Heat.** The website averages the raster into 60 m pixels and stores each
  temperature in 255 steps between 70 and 135°F, about 0.26°F apart.
  Averaging cools the hottest small spots, so the gap grows with the
  threshold: 0.1% at 100°F, 2.5% at 110°F, 8.4% at 113°F (below).

**Tract totals against `exposure_blocks.json` summed to tracts (addition 2).**
Heat is compared at 113°F for both, because the website's columns are whole
degrees; the tables themselves use the exact p95 of 113.27°F.

| Layer | Website | This run (fractional) | Pixel centre | Cumulative surge, lower bound | Spearman across tracts | Tracts differing by more than 100 | Median abs. difference | Largest |
|---|---|---|---|---|---|---|---|---|
| SLR 3 ft | 76,502 | 80,369 | n/a | n/a | 0.963 | 17 | 0 | 220 |
| Surge Cat 3, any | 629,986 | 630,821 | 630,904 | 631,127 | 0.987 | 10 | 0 | 219 |
| Heat ≥ 113°F | 752,283 | 815,427 | 815,020 | n/a | 0.995 | 262 | 62 | 715 |

What drives each gap:
- **Sea level rise.** Exact polygons rather than 30 m pixel centres. The
  largest tract gaps are in Miami Beach, Sunny Isles Beach and North Miami
  Beach, where flooded land comes in narrow strips. 12086002709 in Miami
  differs by 220.
- **Surge.** Fractional coverage barely matters (630,821 versus 630,904 by
  pixel centre). Counting cumulatively (wet at Category 3 or lower) adds at
  least 306 residents, since 631,127 is a lower bound. The remaining
  difference of 0.1% to 0.2% is the website's coarser, reprojected pixels.
  The largest tract gaps (about 150 to 220) are in City of Miami tracts and
  in 12086000415, where the raw categories reverse.
- **Heat.** The website's 60 m averaging is the main cause, not fractional
  coverage: our fractional and pixel-centre totals differ by only 400. The
  tract ranking is nearly identical (Spearman 0.995), but levels are 8% lower
  on the website. The gap is largest in hot, dense tracts such as
  12086002501 in Miami (+715) and 12086012701 in Hialeah (+476).

---

## 4. Findings (description only)

### 4.1 County residents exposed

| Scenario | Residents | Share of county |
|---|---|---|
| **SLR 3 ft (primary)** | **80,369** | **2.9%** |
| SLR 1 / 2 / 6 ft | 8,517 / 18,129 / 887,533 | 0.3% / 0.7% / 32.4% |
| Unconnected low-lying 3 ft | 47,499 | 1.7% |
| **Surge Cat 3, any (primary)** | **630,821** | **23.0%** |
| **Surge Cat 4, any (primary)** | **1,159,540** | **42.3%** |
| Surge Cat 1 / 2 / 5 raw / cat5max, any | 126,081 / 326,210 / 1,676,863 / 1,695,791 | 4.6% / 11.9% / 61.2% / 61.9% |
| Surge more than 3 ft, Cat 3 / Cat 4 | 259,537 / 667,768 | 9.5% / 24.4% |
| Surface heat ≥ county p75, 100.84°F (**not used**: covers 96% of residents) | 2,626,803 | 95.9% |
| **Surface heat ≥ county p95, 113.27°F (primary)** | **757,550** | **27.7%** |
| Surface heat ≥ 100 / 105 / 110°F | 2,656,542 / 2,350,153 / 1,539,073 | 97.0% / 85.8% / 56.2% |

**The heat 75th percentile barely varies, so it is not used (decision
D-036).** The
county percentiles are taken over all land, including the Everglades and the
western wetlands, which are much cooler than built-up areas. So **96% of
residents live on land hotter than the land-wide 75th percentile**. The
median tract share is 0.999, and the lower quartile is 0.968. As a
between-tract variable it carries almost no information. The 95th percentile
(27.7% of residents; tract median 0.17, interquartile range 0.03 to 0.44) and
the population-weighted mean (tract median 110.6°F, interquartile range 107.7
to 112.7°F) do vary.

After this report, the 75th percentile was dropped as a primary measure. The
population-weighted mean and the 95th percentile share are the primary heat
measures from Stage B onward. The `heat_p75_*` columns stay in the files for
traceability.

### 4.2 Land share versus population share

At tract level, land share and population share rank units almost
identically overall: Spearman +0.93 to +0.99 across all 22 scenarios (block
group +0.90 to +0.99). That is mostly because both are zero, or both are
near one, in the same places. **Where they disagree is at the top of the
ranking, which is what the change was meant to fix.**

Top-10 tracts by each measure, among tracts with 100 or more residents:

| Scenario | Overlap of the two top-10 lists |
|---|---|
| SLR 3 ft | 5 of 10 |
| Surge Cat 3 | 6 of 10 |
| Surge Cat 4 | 8 of 10 |
| Heat p75 | 6 of 10 |
| Heat p95 | 8 of 10 |

**SLR 3 ft is where they disagree most.**

| Tract | Place | Land | Land share | Population share | Exposed residents |
|---|---|---|---|---|---|
| 12086011412 | coastal wetland south and east of Florida City | 183 km² | 0.934 (rank 1) | **0.069** | 449 |
| 12086011408 | Everglades National Park | 865 km² | 0.913 (rank 2) | **0.081** | 425 |

Both drop out of the top 10. Their land floods, but their residents live on
the dry parts. **By population share, all ten of the top tracts are in Miami
Beach**, with 56% to 92% of their residents on land inundated at 3 ft. Five
further Miami Beach tracts enter the list (003916, 003912, 004103, 004405,
003913) in place of the two wetland tracts, Cutler Bay 010613, Miami Beach
004406 and Miami Beach 004301.

Other large disagreements:
- **Surge Cat 4.** Unincorporated tracts 015103, 015201 and 015102 have
  44% to 86% of their land in the Category 4 surge zone but almost no
  residents on it.
- **Everglades tracts.** In the other direction, 12086011500 (2,410 km²) and
  12086011408 have 61% to 65% of their land wet at Category 4 but 99.8% of
  their residents. Their residents live in the inundated settlements, not on
  the dry interior.
- **Heat p95.** Tract 12086012501 has 6% of its land above 113°F but 72% of
  its residents, because they live on the paved part.

### 4.3 How concentrated exposure is

698 populated tracts; the top 10% is 70 tracts.

| Scenario | Tracts with any exposed residents | Share of exposed residents in the top 70 tracts | Tracts holding half |
|---|---|---|---|
| SLR 3 ft | 139 | **94%** | 19 |
| Surge Cat 3, any | 345 | 55% | 62 |
| Surge Cat 4, any | 480 | 34% | 116 |
| Heat p75 | 698 | 18% | 246 |
| Heat p95 | 615 | 35% | 117 |

Sea level rise exposure is concentrated in a few places. Surge and heat
exposure are spread widely.

### 4.4 Jurisdictions

Block group assignment, which reaches all 35 jurisdictions.

**SLR 3 ft**
- Miami Beach has 38,176 exposed residents: 47.5% of the county's exposed
  residents and **half of Miami Beach's own residents**.
- Then Miami (14,926, 3% of its residents), Unincorporated Miami-Dade (5,209),
  Sunny Isles Beach (4,629, 23%), North Miami Beach (3,322) and Surfside
  (1,991, 43%).

**Surge Cat 3**
- The largest counts are Unincorporated Miami-Dade (218,353; 18% of its
  residents), Miami (130,407; 28%), Homestead (71,571) and Miami Beach
  (64,785).
- As a share of their own residents: Florida City 98%, Cutler Bay 93%,
  Homestead 92% and Miami Beach 85%.

**Surge Cat 4.** Unincorporated Miami-Dade holds 45% of the county's exposed
residents.

**Heat p95**
- Unincorporated Miami-Dade 303,485; Hialeah 174,690 (77% of its
  residents); Miami 134,053.
- Hialeah Gardens 90% and Sweetwater 64% of their residents.
- Miami Beach only 15%.

### 4.5 Do the hazards expose the same people?

Overlap within a block cannot be known exactly under the even-spread
assumption, because it depends on where exposed land overlaps inside the
block. Each pair is therefore reported as a bound, summed over blocks:
- **lower bound:** max(0, a + b − 1);
- **independence within the block:** a × b;
- **upper bound:** min(a, b).

| Pair | Residents jointly exposed: lower / independent / upper | Upper bound as share of the smaller group |
|---|---|---|
| SLR 3 ft and Surge Cat 3 | 59,177 / 69,970 / 79,560 | 99% of SLR-exposed |
| SLR 3 ft and Surge Cat 4 | 65,299 / 74,223 / 80,064 | 100% |
| SLR 3 ft and Heat p95 | 6,824 / 8,949 / 11,519 | **14%** |
| Surge Cat 3 and Heat p95 | 58,777 / 69,309 / 80,092 | **13%** of surge-exposed |
| Surge Cat 4 and Heat p95 | 166,665 / 185,122 / 200,747 | 26% of heat-exposed |

**Flood hazards expose the same people. Extreme surface heat mostly exposes
different people.**
- Between 74% and 99% of residents exposed to 3 ft of sea level rise are also
  inside the Category 3 surge zone.
- At most 13% to 14% of flood-exposed residents are also on land above the
  95th percentile of surface temperature.
- Residents above the 95th percentile are concentrated inland (Hialeah,
  Hialeah Gardens, Sweetwater, parts of Miami). Flood exposure is coastal
  and in the south.
- The heat p75 measure overlaps everything, because it covers 96% of
  residents.

### 4.6 Hazard correlation screen

Tables: `outputs/exposure/stage_a/exposure_layers/spearman_matrix_{tract,bg}.csv` and
`screen_pairs_{tract,bg}.csv`.

What was screened:
- Spearman, pairwise complete, compared unrounded, on populated units;
- every population share (22), the population-weighted mean temperature, and
  every land share (22);
- at tract level, also the seven FEMA NRI loss columns.

Results:
- **Tract:** 52 variables, **157 pairs at |rho| ≥ 0.75**.
- **Block group:** 45 variables, **144 pairs**.

Nothing was dropped; the full lists are in the CSVs. What the list contains:
1. **No pair crosses hazard families.** No sea level rise variable reaches
   0.75 with any surge, heat or NRI variable, and so on for every pair of
   families, at both grains.
2. **Within each family, nearly everything clears the line.** This includes:
   - neighbouring scenarios (SLR 1 and 2 ft, +0.94; surge Cat 3 and Cat 4,
     +0.82);
   - population share against land share for the same scenario (+0.93 to
     +0.99);
   - "any" against "more than 3 ft" (+0.89 to +0.93);
   - raw Category 5 against `cat5max` (+0.99);
   - every heat threshold against `heat_lst_popwt_mean_f` (+0.78 to +0.98).
3. **NRI.** Only within-hazard pairs clear the line: CFLD total against
   building loss (+0.998), HRCN (+0.984) and IFLD (+0.972).

How the primary population shares relate to NRI loss:
- coastal flood loss (CFLD): +0.52 to +0.58;
- heat wave loss (HWAV): only **+0.04 to +0.18**. FEMA's heat wave loss
  barely tracks where surfaces are hot.

So, as caution 11 expected, sea level rise and surge share a ground model
and correlate with each other: SLR 3 ft against surge Category 3 is +0.55 at
tract level. **The closest cross-family pair is SLR 3 ft against surge
Category 1, any inundation, at +0.737, just under the line.** Neither
duplicates FEMA's coastal flood loss.

### 4.7 Surface heat versus housing density

Housing units are EJScreen ACSTOTHU per block group; at tract level they are
summed over the tract's block groups. That is a derived measure: the earlier
analysis had no tract-level count of total housing units.

| Grain | Measure | Housing density | Population density |
|---|---|---|---|
| Tract | heat p75 share | +0.21 | +0.27 |
| Tract | heat p95 share | +0.12 | +0.19 |
| Tract | popwt mean | +0.15 | +0.23 |
| Tract | land share above p75 | +0.30 | +0.36 |
| Block group | heat p75 share | +0.15 | +0.20 |
| Block group | heat p95 share | +0.08 | +0.17 |
| Block group | popwt mean | +0.14 | +0.23 |

**The relationship is weak.** Hot surfaces do lean toward denser places, but
density explains little of the variation in where residents' land is
hottest. Hialeah, Hialeah Gardens and Sweetwater have the highest shares
above the 95th percentile, while dense Miami Beach has only 15%. Why some
places run hot was not examined here.

---

## 5. Limitations

1. **Sea level rise maps are a screening tool.** NOAA describes its layers
   as a modified bathtub that shows the potential scale of flooding, not its
   exact location. They leave out erosion, subsidence, future construction,
   wind-driven tides, rainfall, groundwater and drainage. Results are
   reported for block groups and tracts only. Ocean-connected and
   unconnected low-lying land are kept separate.
2. **Storm surge maps are a worst case, not a forecast.** Each category's
   Maximum of MOMs is the highest water from many simulated storms at high
   tide, and NHC says no single hurricane would flood the whole area shown.
   These columns are **potential worst-case surge exposure**. They are not
   expected or likely exposure, not a probability, and must never be added
   to FEMA's expected loss. The raw Category 5 layer has a hole in central
   Miami (18,928 residents, flagged). `cat5max` corrects it.
3. **Surface heat is not air heat.** Landsat measures how hot ground and
   roofs get around 10:30 to 11 am on clear summer days. The World Resources
   Institute calls land surface temperature a poor proxy for the heat people
   experience, and USGS notes errors near clouds and where vegetation has
   changed. The variable is called surface heat exposure. Relative
   thresholds are the main measure and fixed °F thresholds are sensitivity.
   The land-wide 75th percentile turned out to cover 96% of residents
   (Section 4.1).
4. **Census block counts carry privacy noise.** The 2020 census adds noise
   to block counts, an average error of about 5 people per block per Census.
   It mostly cancels when blocks are summed, which is why blocks are only
   used to place people.
5. **Population is where people sleep.** ACS counts residents, not workers
   or visitors, and is a 2020 to 2024 average. Growth since 2020, such as new
   towers, is placed using 2020 block patterns.
6. **Even spread within a block is an assumption.** Parks, lots, golf
   courses and canals inside a block are given residents. The building
   footprint sensitivity could not be run, because no raw footprint file
   exists on disk. Seven populated water blocks (boats, marinas) keep their
   full water shape. They hold few residents but inflate
   `heat_nodata_share` in two tracts.
7. **Survey error at block group.** 79 block groups have a population CV
   above 40% (low reliability). They are flagged, not dropped. Another 1,661
   are medium (12% to 40%).
8. **Small populations give unstable shares.** 10 tracts and 16 block groups
   have fewer than 100 residents, among them the 28-person Pennsuco tract
   12086981100. They are kept in the files but left out of every top-10 list
   above.
9. **Different years in different layers.** The years are in Section 1.
   Population covers 2020 to 2024, placed with 2020 blocks. NOAA's layers
   were last changed in 2023. The surge DEMs are cited to 2014 to 2015 and
   the surge product to 2026. Heat covers summers 2021 to 2024. **The ground
   models behind both flood layers predate many of the projects**, so they do
   not show any protection those projects added.
10. **Results depend on the unit, and they describe areas, not people.** Both
    grains are reported side by side. Findings should be worded as "tracts
    with more exposed residents", never as statements about the people
    themselves.
11. **Hazards overlap.** Sea level rise, surge and the elevation surface come
    from similar ground models, and FEMA's coastal flood loss already
    includes sea level rise and surge. The screen in Section 4.6 found no
    cross-family pair at 0.75, but sea level rise and surge do expose largely
    the same residents (Section 4.5).
12. **Size drives counts.** Exposed-resident counts grow with population.
    Shares belong with per-person outcomes, and counts with totals adjusted
    for population, in Stage B. Nothing in this report correlates a count
    with a count.
13. **Nearby places are alike.** No significance tests were run in Stage A.
    Stage B will report Moran's I and say its p-values are not adjusted for
    spatial dependence.
14. **Thresholds are choices.** The primary scenarios were fixed in advance:
    SLR 3 ft, surge Category 3 and 4, heat p75 and p95 (p75 later dropped,
    replaced by the population-weighted mean). Everything else is
    sensitivity. No threshold was chosen for its result. The 1% cut for the
    Category 5 hole flag is also a choice; the continuous share is in the
    file.
15. **Pixel edges.** Fractional coverage (4 × 4 supersampling) and pixel
    centres differ by at most 0.05% in county totals. Tract-level
    differences are larger for small blocks.
16. **Coverage.** Every block lies inside every hazard layer. Surge has no
    missing values on land. Heat is missing for 0.84% of county land, and for
    no resident.

**Further caveats specific to this run:**
- **The "NRI loss variables in use".** No NRI loss column has yet been
  joined to `tract_analysis.csv` or used in any analysis script. The screen
  therefore uses the loss columns `nri_audit.md` recommended: HWAV_EALT,
  CFLD_EALT, CFLD_EALB, IFLD_EALT, IFLD_EALB, HRCN_EALT and HRCN_EALB.
  Tract 12086990000 (open water, no residents) is not in the NRI file.
- **Tract housing density was derived here.** EJScreen block-group housing
  units were summed to tracts. That source is ACS 2018 to 2022, not the
  2020 to 2024 population.
- **Pending:** FEMA flood zones (no geometry), the building footprint
  sensitivity (no raw file) and summer 2025 Landsat (available, not
  requested).
