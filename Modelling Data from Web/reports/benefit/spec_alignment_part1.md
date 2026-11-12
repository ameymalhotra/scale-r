# Aligning to the Flood What-If specification, Part 1: data we can get ourselves

Benefit simulator. 11 Nov 2026. Branch `benefit-simulator`.
Decisions D-160 to D-165 in `DECISIONS.md`.

Note: the specification file (`docs/SCALE-R_Flood_What-If_Spec.docx`) was not
attached, so it is not saved yet. This part follows the summary in the prompt.
The checklist below should be checked against the full document once it is in
`docs/`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| USGS 3D Elevation Program, 1 m DEM, project FL_MiamiDade_D23 | Ground elevation at 5,000 buildings; tile index and metadata | Lidar 27 Dec 2023 to 29 May 2024; published 15 Dec 2025 | National Map API; tiles read over the web |
| NOAA Office for Coastal Management, Coastal Inundation DEM: Florida SE (InPort 70011) | Ground elevation (current) | Compiled Jun 2023 from 2015 and 2018 Miami-Dade lidar | Already in use (Stage 1) |
| FEMA Map Service Center, Miami-Dade product list | What flood products exist | Checked 11 Nov 2026 | Public search |
| FEMA FIRM database 12086C, effective 19 Feb 2027 | Water levels for 5 storm frequencies | Database dated 14 Sep 2026 | Downloaded (199 MB) |
| FEMA Flood Insurance Study, Miami-Dade, volume 1, effective 19 Feb 2027 | Flood sources and models | 2027 | Downloaded (13 MB) |
| Florida DOR 2026 final tax roll (NAL) | Homestead, exemption, assessed and taxable value fields | Roll year 2026 | Already on disk |
| Miami-Dade Property Appraiser, 2026 adopted millage chart | Millage by taxing district | Adopted Oct 2026 | Downloaded |
| Florida DOR, 2025 Miami-Dade adopted millage (TACD file) | Cross-check of the chart | Received 15 Oct 2025 | Downloaded |
| Miami-Dade County open data, "Property Point View" (Property Appraiser) | Which house features are free | Queried 11 Nov 2026 | Field list and counts only; not downloaded |
| USACE National Structure Inventory (NSI) | Foundation type and height | 2026 | Already in use (Stage 1) |
| 44 CFR 60.3; Florida Building Code 2010 edition | Floor height rules by year built | 1972; 15 Mar 2012 | Published rules |

## In short

- **Ground elevation.** The new USGS 1 m lidar map agrees closely with our
  NOAA map at most buildings. The median difference is under 0.1 ft, and only
  3% of buildings differ by more than 1 ft. The USGS map is 6 to 9 years
  newer and shows ground as it is today, including new building pads on
  fill. **Recommendation: switch to USGS 3DEP 1 m.** Nothing has been switched
  yet.
- **FEMA depth grids do not exist** for Miami-Dade, either for the current
  maps or for the new maps effective 19 Feb 2027. The new 2027 FIRM database
  does, however, give **water levels for all five storm frequencies (10%, 4%,
  2%, 1%, 0.2%)**:
  - for coastal storm surge, at 218 shoreline transects;
  - for rainfall and canal flooding, at 1,077 model points.
  This is downloaded and is the best frequency source we have.
- **First-floor elevation** is now estimated for all 627,252 buildings and
  flagged `ffe_estimated = 1`. Building rules for newer homes in flood zones
  raise 21,199 floors, by a median of 1 ft.
- **Tax inputs.** The tax roll has every value field we need. The 2026
  millage rates for all 38 taxing districts are downloaded and checked.
- **House features.** Bedrooms and bathrooms are free from an official
  county layer. Pool is not free. Waterfront can be worked out from maps
  we already have.

## 1. Ground elevation: USGS 3DEP against NOAA

| | NOAA DEM (now) | USGS 3DEP |
|---|---|---|
| Cell size | about 3 m | 1 m |
| Lidar dates (mainland Miami-Dade) | 2015 and 2018 county surveys | 27 Dec 2023 to 29 May 2024 |
| Vertical datum | NAVD88, metres (Geoid 12B) | NAVD88, metres (geoid model to confirm) |
| Coverage of our buildings | all but 33 | 4,994 of 5,000 sampled |
| Size | read over the web | 57 tiles, 13.6 GB (read over the web) |
| Stated vertical accuracy | not tested on the DEM | per USGS lidar standards |

**Ground elevation difference at 5,000 buildings (USGS minus NOAA), feet:**

| Measure | All | Zone AE | Zone AH | Zone X |
|---|---|---|---|---|
| Median | -0.08 | -0.08 | -0.08 | -0.07 |
| Middle half | -0.25 to +0.12 | | | |
| 90% of buildings | -0.53 to +0.57 | | | |
| Median size of difference | 0.20 | 0.23 | 0.20 | 0.19 |
| More than 1 ft apart | 3.1% | 6.3% | 3.3% | 1.9% |
| More than 2 ft apart | 1.6% | | | |

The two maps rank buildings almost identically (correlation 0.96). The 1 m
value under the building and the average over a 3 m square give the same
result, so the gap comes from the survey date, not the cell size.

**Where they disagree most:**
- **By place.** Princeton, Cutler Bay, South Miami Heights and Hialeah
  Gardens are 0.25 to 0.35 ft lower in the new map. Miami Beach has the
  biggest scatter in both directions.
- **NOAA far too high.** At single buildings on Key Biscayne, Miami Beach and
  in Miami, the NOAA map says 14 to 19 ft where the USGS map says 4 to 9 ft.
- **NOAA far too low.** At new homes in Homestead and Hialeah, the NOAA map
  says about 2 ft where the USGS map says 7 to 8 ft. This is likely land
  raised for building since 2018.

**Recommendation (D-160): use USGS 3DEP 1 m.**
- It shows current ground, which matters for a tool that works building by
  building.
- It is finer and comes from one consistent survey.
- County totals will barely change.
- Before switching, the geoid model behind the USGS heights should be
  confirmed. It is expected to differ from NOAA's by centimetres.
- The switch waits for your confirmation.

## 2. FEMA Flood Risk Products and depth grids

**What exists on FEMA's Map Service Center (checked 11 Nov 2026):**

| Product | Current maps (effective 11 Sep 2009) | New maps (effective 19 Feb 2027) |
|---|---|---|
| Flood Risk Database (depth grids) | not listed | not listed |
| Flood Risk Report | not listed | not listed (the study text only says one "may be available") |
| FIRM database | yes, 561 MB (we use the NFHL copy) | yes, 199 MB, **downloaded** |
| Flood Insurance Study | yes | yes, 8 volumes (volume 1 downloaded) |
| Map panels | 202 | 221 |

FEMA's guidance says depth grids, where made, cover the 10%, 4%, 2%, 1% and
0.2% events. In coastal areas often only the 1% grid is made. For
Miami-Dade, none are published.

**What the 2027 FIRM database adds (downloaded, public):**

| Flood source | Storm frequencies | Where | Model |
|---|---|---|---|
| Coastal surge (Atlantic and Biscayne Bay) | 10%, 4%, 2%, 1%, 0.2% | 218 shoreline transects, whole coast | ADCIRC + SWAN surge and wave model, 2018 |
| Rainfall and canal flooding | 10%, 4%, 2%, 1%, 0.2% | 1,077 points along canals and basins | XP-SWMM county basin models, 2007 |
| 1% flood elevations on the map | 1% | AE, AH and VE zones | as above |

Typical coastal still-water levels across the 218 transects (median, ft
NAVD88):

| 10% | 4% | 2% | 1% | 0.2% |
|---|---|---|---|---|
| 2.4 | 2.8 | 5.8 | 6.7 | 8.4 |

These are water levels at points and lines, not depth maps, so Part 2 needs
a way to carry them to each building. I will propose one in Part 2 for you
to confirm. They would replace the current assumption that the 0.2% flood is
as deep as the 1% flood (D-137).

The county also publishes a "Flood Zone Changes Since Last FIRM" map layer.
I found it but did not download it.

## 3. First-floor elevation

Added to the buildings table (no building dropped):
- `ffe_ft_navd88`: the estimated first-floor elevation;
- `ffe_estimated`: 1 for all 627,252 buildings, since no elevation
  certificates are available yet;
- `ffe_rule`: which rule set the floor;
- `ffe_simple_ft_navd88`: the old Stage 2 rule, kept for comparison;
- `year_built_used`: the year built used, with its source.

**Rule: ground plus a typical floor height for the building type and year built.**

Typical floor height above ground by foundation type (from the National
Structure Inventory; assumptions):

| Foundation | Height above ground | Buildings |
|---|---|---|
| Slab | 0.25 to 0.75 ft (median 0.75) | 475,424 |
| Crawlspace | 2 ft | 121,459 |
| Pier or pile | 5.25 to 6.25 ft (6.5 to 9 ft in VE zones) | 29,641 |
| Solid wall | 2 ft | 728 |

Year built (national and state building rules):

| Built | Outside the 1% flood zone | Inside zones A, AE, AH, VE |
|---|---|---|
| 1972 or earlier (before the first flood map, 29 Sep 1972) | ground + foundation height | ground + foundation height |
| 1973 to 2011 | ground + foundation height | at least the 1% flood elevation |
| 2012 or later (Florida Building Code 2010 edition) | ground + foundation height | at least the 1% flood elevation + 1 ft |

**Results:**
- 21,199 buildings are raised by the year-built rule (median 1 ft, 90th
  percentile 3.3 ft).
- Most newer flood-zone buildings (140,072) were already above the 1% level
  on foundation height alone, because 1% depths in AH zones are shallow.
- Buildings with a first floor below the 1% flood level fall from 49,766 to
  31,019.

**Assumptions:**
- Year built is the tax roll's actual year (97% of buildings) or the NSI
  block median.
- The 1% level used is the current (2009) map's. Buildings built under older
  maps may have used a different level.
- Full compliance with the rules is assumed.

**NFIP policies file.** It is not on disk yet:
`~/Downloads/NfipPoliciesV3.parquet.download` is a partial download of
218 MB that stopped at 13:51. Once it is complete, I will report what three
fields add, in block-group summaries only and never as single records:
- `lowestFloorElevation`
- `elevationCertificateIndicator`
- `elevationDifference`

The main use is typical floor height above ground by block group and by
building age, which can check or replace the table above.

## 4. Tax inputs and house features

**Tax roll fields (2026 NAL, 939,447 parcels):**

| Need | Fields | Notes |
|---|---|---|
| Homestead status | `JV_HMSTD`, `AV_HMSTD`, exemption `EXMPT_01` | 451,765 homestead parcels (48%) |
| Assessed value | `AV_SD` (school), `AV_NSD` (non-school) | The 10% cap for non-homestead property applies to non-school value only |
| Save Our Homes cap | just value `JV` minus `AV_SD` on homestead parcels | Median gap is 49% of just value |
| Taxable value | `TV_SD`, `TV_NSD` | After exemptions |
| Other exemptions | `EXMPT_02` to `EXMPT_82` | Additional homestead, seniors, veterans and others |
| Taxing district | `TAX_AUTH_CD` | 38 codes, all matched to millage |

**Millage rates.** These are the 2026 adopted rates for all 38 taxing
district codes, saved in `data/reference/millage_2026_by_code.csv`:
- Totals range from 14.90 to 24.19 mills.
- Every row adds up to its stated total.
- The DOR's 2025 file matches the chart's 2025 column exactly.
- The school part (6.623 mills) is charged on school taxable value and the
  rest on non-school taxable value.

**House features:**

| Feature | Free official source | Paid or by request |
|---|---|---|
| Bedrooms | County "Property Point View" layer: 99.9% of single-family homes, 93% of condos | n/a |
| Bathrooms, half bathrooms, floors | Same layer | n/a |
| Year built, living area | Same layer and the tax roll | n/a |
| Latest sale date and price (any year) | Same layer | n/a |
| Pool | None. Proxy: tax roll special features value, which mixes pools with docks and fences | Property Appraiser bulk files, $50 per file, or a custom request (cost quoted after review) |
| Waterfront | None as a field. Can be derived free from parcel and water polygons we already have | n/a |

The free layer also contains owner names and addresses, so I would request
only the house fields. Nothing has been bought or downloaded.

## Checklist against the specification

| Module | Data | Status | Source |
|---|---|---|---|
| A | Buildings: location, type, stories, value | Have | NSI 2026 |
| A | Ground elevation | Have (NOAA 3 m); Got now (USGS 1 m compared, switch pending) | NOAA; USGS 3DEP |
| A | First-floor elevation | Got now (estimated for all buildings) | NSI + building rules |
| A | Elevation certificates | Still need (requested) | County / NFIP |
| A | Coastal flood levels, several frequencies | Got now (5 frequencies, 218 transects) | FEMA FIRM database 2027 |
| A | Rainfall and canal flood levels, several frequencies | Got now in part (5 frequencies at 1,077 points); gridded rainfall model outputs still need (requested) | FEMA FIRM database 2027 |
| A | FEMA depth grids / Flood Risk Database | Still need (not published for Miami-Dade) | FEMA Map Service Center |
| A | Surge worst cases | Have | NHC SLOSH MOM |
| A | Sea level rise | Have | NOAA SLR |
| B | Depth-damage curves | Have | USACE |
| B | NFIP claims | Have | FEMA OpenFEMA |
| B | NFIP policies | Still need (download incomplete) | FEMA OpenFEMA |
| B | Displacement costs, inflation | Have | FEMA BCA; BLS CPI-U |
| C | Project locations | Have | Project inventory |
| C | Real project dates | Still need (requested) | County / agencies |
| C | Drainage basins and pump capacities | Still need (basin names only, from the 2027 study) | County |
| C | Capital and maintenance costs | Have (FEMA standard values); project-specific still need | FEMA BCA |
| D | Sales | Have (2025 to 2026); older sales available free, not downloaded | DOR NAL; Property Point View |
| D | Bedrooms, bathrooms | Got now (free source found, not downloaded) | Property Point View |
| D | Pool | Still need (paid or by request) | Property Appraiser |
| D | Waterfront | Have the inputs (can derive) | Parcels + water polygons |
| D | Homestead, exemptions, assessed and taxable value | Have | DOR NAL 2026 |
| D | Millage rates | Got now (2026 adopted) | Property Appraiser; DOR |
| Benefit per dollar | Discount rate, project life | Have | FEMA BCA |

## Which numbers are measured and which are assumed

- **Measured:**
  - elevation differences;
  - FEMA water levels;
  - counts of tax roll fields;
  - millage rates.
- **Assumed:**
  - typical floor heights by foundation type;
  - full compliance with the flood-zone building rules;
  - using the 2009 1% flood level for buildings built under older maps.

## Main limitations

- The specification document itself was not provided, so the checklist
  follows the prompt's summary of it.
- The USGS geoid model is not yet confirmed.
- First-floor elevations are all estimated until elevation certificates or
  the NFIP policies file arrive.
- The 2027 FEMA water levels are at points and transects, not grids. How
  they are spread to buildings is a modelling choice for Part 2.
