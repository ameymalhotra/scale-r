# Investment benefit simulator, Stage 1: data foundation

Prompt 27, Phase 1, Stage 1. Written 11 November 2026 on branch
`benefit-simulator`. Decisions D-119 to D-134 in `DECISIONS.md`.
Data preparation only: no model was fitted and no benefit was estimated.

## In short

- **One table now holds every building in Miami-Dade: 627,252 of them.**
  `data/processed/benefit/buildings.parquet` links each USACE building
  record (NSI 2026) to its tax roll parcel, census tract and block group,
  ground elevation, FEMA flood zone and base flood elevation, storm surge
  depth for hurricane Categories 1 to 5, and sea level rise flooding at 1,
  2, 3 and 6 ft.
- **The links are nearly complete.** 99.4% of buildings sit on a tax roll
  parcel; 99.6% of tax roll records are placed on a parcel map; every
  building has a tract, a flood zone and a surge value; 33 buildings lack a
  ground elevation.
- **Value at risk, two ways (estimated from our data, kept apart):**
  - NSI 2026 building value $414 billion plus contents $305 billion
    (depreciated replacement cost, August 2025 dollars; not market prices).
  - Tax roll market value (just value) on parcels with buildings
    $714 billion (2026 roll).
- **Exposure, at a glance:**
  - 261,899 buildings (42%), with 1.30 million night-time residents, are in
    FEMA's 1% annual chance flood zone.
  - A Category 3 storm's worst-case surge reaches 125,810 buildings and
    598,000 residents; Category 5 reaches 377,479 buildings and 1.72
    million residents.
  - 3 ft of sea level rise floods 6,720 buildings; 6 ft floods 116,810.
- **Standard values and damage curves are in place.** 175 FEMA values, each
  checked against its page, are in `data/reference/fema_standard_values.csv`.
  USACE depth-damage curves for 42 building types are in
  `data/reference/depth_damage_curves.csv`.
- **Four things to know before Stage 2:**
  1. The tax roll's two sale slots only hold 2025 and 2026 sales (44,462
     qualified first sales). Stage 3's before-and-after test cannot use it.
  2. FEMA's flood maps date from 11 September 2009, with new maps pending
     for 19 February 2027. The code is ready to swap them in.
  3. FEMA does not print dollar values for mental stress or lost
     productivity in any document still available, so they stay missing.
  4. The flood insurance policy download is still running (FEMA's server
     is slow). It is only needed for Stage 2 calibration.

---

## 1. Sources

All downloads were made on 10 November 2026 (US Eastern time). Sizes and
SHA-256 checksums are in `data/raw/benefit_download_log.json`.

| Publisher | Dataset and version | Data years vs release | Where downloaded | Local file |
|---|---|---|---|---|
| Florida Department of Revenue | NAL tax roll, 2026 final, Miami-Dade (county 23); 939,447 parcels | values as of 1 Jan 2026; sales 2025 to 2026 / file dated 16 Oct 2026, posted 28 Oct 2026 | floridarevenue.com PTO Data Portal, Tax Roll Data Files/NAL/2026F | `data/raw/dor/Dade_23_Final_NAL_2026.zip` |
| Florida Department of Revenue | 2026 NAL/SDF/NAP User's Guide | 2026 | Data Portal, User Guides | `data/raw/reference_docs/dor/2026_NAL_SDF_NAP_Users_Guide.pdf` |
| Florida Department of Revenue | Parcel polygons, Miami-Dade, 2026 (596,837) and condo unit points (352,530) | 2026 roll / shapefiles dated 27 Jul and 28 Apr 2026, posted 7 Aug 2026 | Data Portal, Map Data/2026F/2026F PAR | `data/raw/dor/miamidade_2026Ppar.zip`, `miamidade_condos_2026.zip` |
| US Army Corps of Engineers | National Structure Inventory 2026, Miami-Dade (627,252 structures). **Used.** | values at August 2025 prices / NSI 2026 release | NSI API, `https://nsi.sec.usace.army.mil/nsiapi/structures?fips=12086&fmt=fc` | `data/raw/nsi/nsi_2026_api_12086.geojson` |
| US Army Corps of Engineers | National Structure Inventory 2022, Florida (comparison only) | 2021 prices / file dated 30 Sep 2022 | NSI download tool | `data/raw/nsi/nsi_2022_12.gpkg.zip` |
| FEMA | National Flood Hazard Layer, Miami-Dade county file | FIRM effective 11 Sep 2009, 60 map revisions to 26 Jan 2026 / database revised 26 Jan 2026 | FEMA Map Service Center | `data/raw/fema/nfhl/12086C_20260125.zip` |
| FEMA (OpenFEMA) | NFIP Redacted Policies, `NfipPolicies` v3 (74.7 million rows nationally) | policy years 2009 onward / data refresh 9 Sep 2026 | `https://www.fema.gov/api/open/v3/NfipPolicies`, by community (D-120) | `data/raw/fema/nfip_policies_miami_dade.csv.gz` (**download still running**) |
| FHFA | Census tract house price index, annual, developmental (`hpi_at_tract.csv`; the brief's `hpi_at_bdl_tract.csv` name no longer exists) | 1976 to 2025 / current FHFA release | `https://www.fhfa.gov/hpi/download/annual/hpi_at_tract.csv`, Miami-Dade rows kept | `data/raw/fhfa/hpi_at_tract_miami_dade.csv` |
| FEMA | BCA Standard Economic Value Methodology Report v13.0 | 2023 dollars mostly / Sep 2024, updated Jul 2025 | fema.gov BCA methodologies page | `data/raw/reference_docs/fema/fema_bca_general-economic-values_2025.pdf` |
| FEMA | BCA Riverine and Coastal Flood Module Methodology Report v6 | / Jan 2025, updated Jun 2025 | same | `..._hazard-methodology-riverine-coastal-flood_2025.pdf` |
| FEMA | BCA Project Configuration and Cost Estimation Methodology Report v6.0 | / Dec 2024, updated Jul 2025 | same | `..._methodology-project-configuration-cost-estimation_2025.pdf` |
| FEMA | BCA Toolkit Help Content | / 28 Aug 2025 | same | `bca-allhelpcontent-pdf-08-28-2025.pdf` |
| FEMA | Economic Benefit Values for Green Infrastructure | 2021 dollars / Jul 2022, updated Jul 2025 | same | `fema_bca_economic-values-green-infrastructure_2025.pdf` |
| FEMA | Ecosystem Service Value Updates | 2021 dollars / Jun 2022 | fema.gov | `fema_ecosystem-service-value-updates_2022.pdf` |
| US Army Corps of Engineers | go-consequences occupancy type library (`structures/occtypes.json`, commit dff647c) | / 27 Dec 2021 | GitHub, USACE/go-consequences | `data/raw/reference_docs/usace/occtypes.json` |
| NOAA National Geodetic Survey | NCAT web API, VERTCON 3.0 (NGVD29 to NAVD88) | / queried 10 Nov 2026 | `https://geodesy.noaa.gov/api/ncat/llh` | `data/reference/ngvd29_to_navd88_grid.csv` |
| NOAA Office for Coastal Management | FL_SE 3 m DEM, NAVD88 (already used by the website) | / file dated 31 May 2023 | read over the web, not stored | `https://coast.noaa.gov/slrdata/DEMs/FL/FL_SE_GCS_3m_NAVDm_v3.tif` |
| Already in the project | NHC surge v4 (06/2026); NOAA sea level rise polygons; TIGER/Line 2024 block groups | see `reports/exposure/population_exposure.md` | | `data/raw/physical/`, `data/raw/boundaries/` |

Not used: the 2023 version of FEMA's economic value report (replaced by
v13) and the NSI 2022 run (kept in `outputs/benefit/stage1_nsi2022/` for
the comparison in section 3).

---

## 2. The tax roll (NAL)

**What it is.** The county property appraiser's 2026 roll as filed with the
state: one row per parcel (939,447), with the appraiser's market value
("just value", `JV`), land value, living area, year built, use codes and
the two most recent sales. Owner names and addresses are in the file but
were never read (D-121).

**Use codes (`DOR_UC`).** The biggest groups are condominium units (004,
391,111), single-family homes (001, 385,301), small multi-family (008,
31,554), vacant residential (000, 22,253) and vacant government land (080,
20,380).

**Missing values.**

| Field | Missing |
|---|---|
| Just value, land value, use codes | 0% |
| Year built (actual and effective), living area, number of buildings | 7.5% (mostly vacant land) |
| Number of residential units | 11.5% |
| Land area | 38.6% (blank for condo units, which have no land of their own) |
| Sale 1 / sale 2 | 88.7% / 98.4% |

**Sales, and which ones count.** The roll only keeps sales from the past
two years: 106,595 parcels have a sale in 2025 or 2026 and 14,698 have a
second one. The state codes each sale (User's Guide pages 17 and 18):

| Codes | Meaning | Use for a price model? |
|---|---|---|
| 01, 02 | Arm's length, qualified by deed examination or documented evidence | **Yes** (44,462 first sales, 2,536 second sales) |
| 03 to 06 | Arm's length, but the property changed after the sale, or several parcels were sold together, or the parcel crosses a county line | No: price does not match the parcel as recorded |
| 11 to 21 | Disqualified by the deed: quit claims, bank or government sales, partial interests, sales by executors | No |
| 30 to 43 | Disqualified on evidence: family sales, forced sales, unusual financing, bulk deals | No |
| 98, 99 | Not yet decided | No |

The most common disqualified codes are 11 (33,279 quit claim and similar
deeds) and 14 (15,724 life-estate transfers).

**What this means for Stage 3.** About 44,000 qualified sales are plenty for
a price model. But they cover only two years, so the "before and after a
nearby project" comparison cannot be done with this file. Older rolls would
be needed; the DOR portal currently lists only the 2026 roll.

## 3. Buildings (NSI 2026) and the switch from 2022

**What it is.** A USACE estimate of every structure: location, use
(occupancy type), floor area, stories, foundation type and height, value of
structure and contents, and residents by day and night. Values are
**depreciated replacement cost, not market prices** (D-134).

**Value basis (from the NSI technical documentation).**
- `val_struct`: depreciated replacement value. `fullrep`: full cost to
  build new ($564 billion in Miami-Dade). "All values are reported in
  August 2025 price levels."
- Contents: depreciated structure value times a ratio by building type
  (0.5 for single-family homes). The documentation warns that USACE EGM
  04-01 assumes 1.0 and that users of EGM damage curves should use the EGM
  ratio. Stage 2 will apply this.
- NSI 2022 used 2021 prices and a simpler depreciation rule (1% a year for
  20 years, then held at 80%).

**NSI 2026 against NSI 2022 (D-130).**

| | NSI 2022 | NSI 2026 |
|---|---|---|
| Structures | 579,117 | 627,252 |
| Structure value | $243.0 billion | $414.1 billion |
| Contents value | $176.0 billion | $305.4 billion |
| Night / day residents | 2.66 / 2.90 million | 2.88 / 2.94 million |
| Price year | 2021 | August 2025 |
| Foundations: slab / crawl space / basement / pile / pier | 289,031 / 170,575 / 109,704 / 7,589 / 1,833 | 419,223 / 121,459 / 56,201 / 15,699 / 13,942 |

By 2020 tract the two agree closely on where buildings are (Spearman 0.96
for counts) and fairly closely on value (0.77).

**Why value rose 70%.** Splitting total value into number of structures ×
floor area per structure × value per square foot:

| | More structures | More floor area per structure | Higher value per sq ft |
|---|---|---|---|
| All structures | 15% | 70% (3,405 to 4,934 sq ft) | 15% ($123 to $134) |
| Single-family homes | 17% | 2% | 81% ($106 to $157) |

So for homes the increase is mostly price level (2021 to 2025) and the new
depreciation method. For the whole stock it is mostly larger floor-area
estimates for apartment, commercial and farm buildings in NSI 2026.

**Basements recoded (D-132).** NSI 2026 marks 56,205 Miami-Dade structures
as having basements, which are almost unknown here because of the high
water table. They were recoded to slab and to "no basement" damage curves.
NSI had given them a first floor 2 ft above ground; they now take the
typical slab height for their type (0.75 ft for 46,994 houses, 0.5 ft for
7,456 apartment buildings, 0.25 ft for 1,755 others). The tax roll has no
foundation field, so it could not refine this. The original NSI values are
kept in the table.

**Other points.** NSI 2026 lists 25,474 farm buildings (AGR1), mostly in
the Redland area; NSI 2022 had 2,539. Every NSI 2026 block code matches our
own block group join.

## 4. How the pieces were linked

| Link | Result |
|---|---|
| Tax roll record → parcel polygon, same parcel ID | 584,494 records (62.2%) |
| Condo unit → its building's master parcel (state condo file) | 351,250 more (37.4%) |
| Condo unit → polygon under its point | 18 more |
| **Tax roll records placed** | **935,762 of 939,447 (99.6%)**; 3,685 not placed, holding $3.2 billion of the roll's $769.5 billion |
| Parcel polygons that match a tax roll record | 590,871 of 596,837 (99.0%) |
| Building → parcel it sits in | 623,522 (99.4%) |
| Building → nearest parcel within 50 ft | 81 more |
| Buildings with no parcel | 3,649 (0.6%) |
| Building → block group and tract (2020 geography) | 627,252 (100%); 707 tracts, 1,843 block groups |
| Building → FEMA flood zone | 627,252 (100%); no overlapping zones |
| Building → ground elevation (NOAA DEM) | 627,219; 33 missing (no ground value in the DEM at the point) |

Several buildings often share a parcel (135,226 buildings are on parcels
with more than one). Parcel values are shared among them by floor area
(`jv_alloc`, D-122), so county totals stay correct.

**Ground elevation check.** NOAA's DEM and NSI's own ground elevation agree
closely: the median difference is 0.22 ft, and the middle half of
buildings differ by 0.02 to 0.43 ft.

## 5. Flood maps

- **Effective maps:** FIRM dated 11 September 2009 (all 251 panels), plus 60
  letters of map revision from February 2010 to January 2026.
  **New maps are pending, effective 19 February 2027.** To use them,
  download the new county file into `data/raw/fema/nfhl/`, change
  `NFHL_COUNTY_ZIP` in `scripts/common/paths.py` and rerun
  `build_buildings.py`. Base flood elevations already in NAVD88 pass
  through unchanged.
- **Zones at buildings:** X 364,970 (of which 34,893 in the 0.2% annual
  chance zone); AH 136,847; AE 123,110; A 1,452; VE 490; D 382.
  261,899 buildings are in the 1% annual chance flood zone (SFHA), holding
  1.30 million night-time residents and $204 billion of structure value.
- **Base flood elevation:** present for 260,450 buildings, 3 to 17 ft,
  median 8 ft, all in NGVD29.
- **Datum conversion (D-131).** The DEM uses NAVD88. Using NOAA's NCAT
  service (VERTCON 3.0) on a county grid, the shift from NGVD29 to NAVD88 is
  between -1.47 and -1.91 ft at these buildings (median -1.55 ft). Both the
  published and converted values are in the table.
- **First look:** after conversion, 101,786 buildings sit on ground below
  their base flood elevation, and 49,751 have a first floor below it.
- **Check:** NSI 2026's own flood zone and base flood elevation fields
  match ours for every building. NSI did not convert the datum.

## 6. Storm surge and sea level rise at buildings

Surge is the NHC worst-case depth for each hurricane category (D-126);
depth is the middle of each 1 ft band.

| Hazard | Buildings | Night residents | Structure value |
|---|---|---|---|
| Surge, Category 1 | 15,244 | 87,055 | $15.7 billion |
| Surge, Category 2 | 57,075 | 279,434 | $41.3 billion |
| Surge, Category 3 | 125,810 | 597,921 | $82.2 billion |
| Surge, Category 4 | 253,275 | 1,163,774 | $165.6 billion |
| Surge, Category 5 | 377,479 | 1,721,504 | $252.1 billion |
| Sea level rise 1 ft | 75 | 87 | under $0.1 billion |
| Sea level rise 2 ft | 506 | 2,341 | $0.4 billion |
| Sea level rise 3 ft | 6,720 | 41,030 | $5.8 billion |
| Sea level rise 6 ft | 116,810 | 656,340 | $91.3 billion |

Another 3,282 buildings are in low-lying areas that 3 ft of sea level rise
would reach but that are not connected to open water. They are flagged
separately. Median surge depth at wet buildings rises from 0.5 ft (Category
1) to 4.5 ft (Category 5).

NHC says its maps show "the scale of potential flooding, not the exact
location", and are not for parcel-level assessment. Building-level surge
values are screening estimates to be summed over areas, not predictions for
one house.

## 7. Flood insurance policies (in progress)

OpenFEMA's current policy file (`NfipPolicies` v3) has no county field,
and filtering on the census code times out. So policies are pulled one NFIP
community at a time, for the 37 Miami-Dade community numbers named in the
claims data. These cover 61,660 of the 61,867 Miami-Dade claims. Only
Miami-Dade census codes are kept, and only 26 of 80 fields (D-120).

**Status:** 4 of 37 communities finished (313,233 policy records). About
2.8 million records remain, 1.88 million of them for unincorporated
Miami-Dade. FEMA's server is returning frequent "service unavailable"
errors, so the download is retrying and will take several more hours. The
file is written only when every community is complete and checked against
FEMA's counts. It is needed only in Stage 2 (claims per insured building),
and its coverage will be reported there.

## 8. FHFA house price index

- 425 Miami-Dade tracts, 1976 to 2025. All 425 codes are valid 2020
  tracts, and 220 exist only in 2020, so the file uses 2020 tracts (D-129).
- **Coverage is thin:** the index exists for 425 of 707 tracts, for 296 in
  2010, and for only 222 in 2025. FHFA leaves out tracts with too few
  repeat sales, which tends to drop condo-heavy and low-sales areas.
- Missing: index 11% of tract-years; annual change 18%.

## 9. FEMA standard values (all labelled "assumption")

`data/reference/fema_standard_values.csv` holds 175 values. For each one,
the script finds the quoted text in the FEMA PDF and records the page, so
no value enters without being on the page cited (D-124).

| Group | Examples (dollar year) | Source and page |
|---|---|---|
| Displacement | lodging, GSA standard rate $110 per room per day (FY2025); meals $68 per person per day (FY2025) less $10 for eating at home; rent while displaced, e.g. single-family $0.91 per sq ft per month plus $1.10 per sq ft one-off (2021); 45 days displaced per foot of water for a one-story house (example curve) | Economic value report v13, PDF pages 11 to 12 (printed 4 to 5); flood module report v6, PDF page 18 (printed 12) |
| Time and roads | lost time $43.11 per hour; traffic delay $36.63 per vehicle-hour (2023) | v13, PDF pages 9 to 10 (printed 2 to 3) |
| Utilities | loss of electricity $213, potable water $150, wastewater $71, communications $151 per person per day (2023) | v13, tables 18, 21, 23 and 26 |
| Discounting | 7% for new analyses; 3.1% (used in 2023 to 2024) kept for sensitivity | Help Content, PDF page 59 |
| Project life | drainage, floodwalls and major infrastructure 50 years; floodplain restoration and flood storage 30; house elevation 30; bioretention and green roofs 35; permeable pavement 30; trees 25; acquisition 100 | Project configuration report v6, PDF pages 20 to 21 |
| Ecosystem services | per acre per year: beaches and dunes $300,649; riparian $37,199; urban green space $15,541; forest $12,589; coastal wetland $8,955; inland wetland $8,171; coral reef $7,120; shellfish reef $2,757 (2021) | Help Content, PDF pages 174 to 176; service-by-service breakdown in the 2022 update, PDF page 18 |
| Green infrastructure | per sq ft per year: bioretention $2.83, permeable pavement $0.64, green roof $0.38; per tree per year $1,048.86 (2021) | Green infrastructure report, PDF page 15 (printed 11) |

**Double counting is flagged in the table.** Green infrastructure "property
value improvement" and the aesthetic, recreation and flood reduction parts
of the ecosystem values overlap with the property value model or with
avoided flood losses. Their rows are marked so Stage 4 can remove them.

**Missing (`fema_standard_values_missing.csv`):**
- **Mental stress and lost productivity.** FEMA's Toolkit Help Content
  describes the method but prints no dollar values. Neither does any other
  FEMA document still available, including the 2019 User Guide and the 2020
  release notes. The 2012 sustainability benefits report is no longer on
  fema.gov, and the FEMA page that once printed the values now returns 404.
  State agency slides quote $2,443 and $8,736; not used (D-133).
- The Miami-Dade local GSA per diem: only the national standard rate is
  printed by FEMA.
- Displacement days for other building types and depths: only one example
  curve is printed.
- Default traffic volumes and detour times for roads.
- A project life for living shorelines: the nearest listed type is
  floodplain restoration (30 years).

## 10. Depth-damage curves

`data/reference/depth_damage_curves.csv` has 2,436 rows: percent damage by
depth (-2 to 16 ft above the first floor) for structure and contents, for
42 NSI building types (D-125).
- **Freshwater curves** for all 42 types: USACE EGM 01-03 for houses and
  HEC-FIA (Galveston) curves for other uses.
- **Saltwater curves** for 16 types: FEMA coastal and NACCS.
- Each depth has a mean and a low-to-high band, for the ranges in Stage 2.
- **Check:** the one-story house curve equals FEMA's printed example
  exactly (13.4% damage at the first floor, 23.3% at 1 ft; flood module
  report, PDF page 18).

## 11. The building table

`data/processed/benefit/buildings.parquet`: 627,252 rows, 103 columns, 96 MB
(git-ignored, rebuilt by the script). Main groups of columns:
- **NSI:** id, building type, floor area, stories, foundation (recoded and
  original), first-floor height, structure, contents and full replacement
  value, residents by day and night, NSI ground elevation.
- **Tax roll (by parcel):** parcel ID and how it was matched, just value
  (parcel total and building share), land value, taxable value, living
  area, year built, use codes, condo unit count, taxing authority, the
  parcel's own sales and the count of qualified sales on the parcel.
- **Geography:** block group and tract (2020).
- **Flood map:** zone, subtype, SFHA flag, base flood elevation (NGVD29 and
  NAVD88) and the datum shift.
- **Hazards:** ground elevation (NOAA DEM, NAVD88, feet and metres); surge
  class and depth for Categories 1 to 5; sea level rise flags at 1, 2, 3
  and 6 ft and the low-lying 3 ft flag.

Missing values in the table: ground elevation 33 rows; parcel and tax roll
fields 0.6%; year built from the tax roll 3.1%; base flood elevation 58%
(blank in zone X, as expected); parcel sales 90% (only 2025 to 2026 sales
exist).

## 12. How to rerun

From `Modelling Data from Web/`, with the repository's `.venv`:

| Step | Command | Time |
|---|---|---|
| Policies (network) | `python3 -I scripts/benefit/download_policies.py` | hours |
| Datum grid (network) | `python3 -I scripts/benefit/fetch_vertcon_grid.py` | 2 minutes |
| Reference tables | `../.venv/bin/python -I scripts/benefit/build_reference_tables.py` | seconds |
| Building table | `../.venv/bin/python -I scripts/benefit/build_buildings.py` | about 12 minutes from scratch (DEM read over the web); checkpoints in `outputs/benefit/stage1/` |
| NSI comparison | `../.venv/bin/python -I scripts/benefit/compare_nsi_versions.py` | 1 minute |
| Summary numbers | `../.venv/bin/python -I scripts/benefit/stage1_summary.py` | 1 minute |
| Download log | `../.venv/bin/python -I scripts/benefit/write_download_log.py` | seconds |

`build_buildings.py` runs the raster sampling (`sample_rasters.py`) in a
separate process, because loading the two geospatial libraries together
crashed Python.

## 13. Limits to carry forward

- **NSI values are modelled, not observed.** Individual records can be
  wrong on use, size, foundation or value; NSI itself recommends using them
  for area totals.
- **Two kinds of value.** NSI is replacement cost (August 2025 dollars);
  the tax roll is appraised market value (2026). They measure different
  things; on single-family homes NSI structure value is about half of the
  just value (median ratio 0.48), mostly because just value includes land.
- **Surge depths are bands and worst cases**, not single storms.
- **The flood maps are 17 years old** and will be replaced in February 2027.
- **Sales cover only 2025 to 2026.**
- **The FHFA index covers only 222 to 425 tracts.**
- **The policies download is not finished.**
