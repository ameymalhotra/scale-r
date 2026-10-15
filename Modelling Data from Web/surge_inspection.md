# NHC SLOSH MOM storm surge: Stage 1 inspection (Miami-Dade)

Source folder: `Modelling Data from Web/tract-level/Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617/`
Inspected 2026-09-22. Read-only: no downloaded file was modified. The only raster reads were windowed reads of the Miami-Dade bounding box (lon -80.87 to -80.12, lat 25.1 to 25.98).

Tooling note: the project `.venv` does not have rasterio, so this inspection used a separate throwaway venv (rasterio 1.5.1, GDAL 3.12.4, geopandas 1.1.4). I left the project venv alone because the SLR job is running from it.

---

## 1a. Structure

**Answer to the key question: there are five separate rasters, one for each hurricane category.** The category is encoded **only in the filename** (`us_Category{N}_MOM_Inundation_HIGH.tif`, N = 1 to 5). Each raster has a single band. The XML `<title>` confirms it (for example, "Category 3 SLOSH MOM Inundation (HIGH Tide Scenario)").

Total size: 4.8 GB. Each category has the same set of 8 files:

| File (per category N) | Cat 1 | Cat 2 | Cat 3 | Cat 4 | Cat 5 |
|---|---|---|---|---|---|
| `.tif` (raster) | 769 MB | 808 MB | 854 MB | 891 MB | 492 MB |
| `.tif.ovr` (pyramids, NEAREST) | 249 MB | 267 MB | 288 MB | 305 MB | 183 MB |
| `.tfw` (world file) | 82 B | 82 B | 82 B | 82 B | 82 B |
| `.tif.xml` (FGDC/ESRI metadata) | 22 KB | 22 KB | 22 KB | 22 KB | 22 KB |
| `.tif.aux.xml` (GDAL stats + histogram) | ~1.3 KB | ~1.3 KB | ~1.3 KB | ~1.3 KB | ~1.3 KB |
| `.tif.vat.dbf` (ESRI value attribute table) | 6.1 KB | 6.4 KB | 6.4 KB | 6.4 KB | 6.4 KB |
| `.tif.vat.dbf.xml` (BuildPyramids log) | 504 B | 504 B | 504 B | 504 B | 504 B |
| `.tif.vat.cpg` (codepage, "UTF-8") | 5 B | 5 B | 5 B | 5 B | 5 B |

The folder also contains a `.claude/` directory, which holds tool settings and no data.

### What the XML metadata says

The five XML files are identical apart from the category number in the title, purpose, and entity table name.

- **Categories:** "SLOSH products do not include Category 5 storms north of the NC/VA border." The Category 5 raster's extent reflects this: its top edge is at 36.76°N, while Categories 1 to 4 reach 46.40°N.
- **MOM:** MEOWs composite up to 100,000 hypothetical storms for each combination of category, forward speed, direction, and initial water level. MOMs take the maximum across all MEOWs for a category and tide level at each cell. "The MOMs represent the worst case scenario for a given category of storm and initial water level under ideal storm conditions." "No single hurricane will produce the regional flooding depicted."
- **High tide:** "A high tide initial water level was used for the storm surge hazard maps." Surge is defined as the rise "over and above the predicted astronomical tides."
- **Processing:** the SLOSH grids were merged into a seamless grid and then processed against a DEM of about 10 m. The DEM combines NOAA OCM lidar, with USGS 3DEP used outside OCM coverage, resampled bilinearly. Surge minus ground elevation gives depth above ground, which is then binned. **Water bodies were masked** using USGS NHD (fall 2020), and an intertidal/estuarine wetland mask was built from a NOAA OCM MHHW raster.
- **Version:** "This update reprocesses the v4 2025 data … to address a bug that impacted results in South Florida. This update is still v4, processed 06_2026." Any older v4 download from Fall 2025 is affected by this bug and must not be mixed with this data.
- **Class definitions (entity table):** 1 = "Less than 1 foot above ground", 2 = "1 to 2 feet" … 20 = "19 to 20 feet", 21 = "Greater than 20 feet", 99 = "Levee Areas". The Louisiana HSDRRS is given as the example of a levee area, and the metadata says the product "should not be used to assess the storm surge hazard within these areas."
- **Stated limitations:**
  - The maps show the scale of flooding, not its exact location.
  - They do not account for erosion, subsidence, sea-level change, or future construction.
  - They are for "city/community level (not for a parcel level or grid cell assessment)".
  - Risk "could extend beyond the areas depicted" because the SLOSH grid extents constrain the coverage.
  - Waves, rainfall, and freshwater flooding are not included.
  - Not all levees are included. Local walls, berms, and pumps may be missing.
  - Vertical accuracy depends on the source DEM.

## 1b. Raster properties

Categories 1 to 4 are identical in every property below. Category 5 differs only in extent.

| Property | Categories 1 to 4 | Category 5 |
|---|---|---|
| CRS | EPSG:4269 (NAD83 geographic) | same |
| Pixel size | 8.98315e-5° (square in degrees) | same (y differs from Cats 1 to 4 at the 1e-20 level, which is negligible) |
| Pixel size at 25.55°N | ≈ 10.0 m N-S × 9.0 m E-W ≈ **90.2 m²** | same |
| Dimensions | 347,032 × 243,836 | 252,314 × 136,550 |
| Bounds (W, S, E, N) | -98.060, 24.492, -66.885, 46.396 | -98.060, 24.492, -75.394, 36.758 |
| Bands / dtype | 1 / uint8 | same |
| Nodata tag | **255** | same |
| Compression | LERC, tiled 128×128 | same |
| Overviews | 2, 4, 8 … 128 (external .ovr) | same |

All five share the same west and south edges and pixel size, so their grids align pixel for pixel. However, the Miami-Dade window starts at a different row in Category 5 (row 119,981, compared with 227,267 for Categories 1 to 4), because its top edge is further south. The window has to be computed from bounds separately for each file. Hard-coding row offsets would give wrong results.

## 1c. Pixel values in the Miami-Dade window

Window size: 8,349 × 9,796 = 81.8 M pixels for each category (about 82 MB as uint8). Each read took about 1.5 s. The pixels are split into three groups:
- **county land:** inside a Miami-Dade tract and outside Census `areawater`
- **Census water:** inside `tl_2024_12086_areawater`
- **outside county:** everything else in the bounding box

Inundated = classes 1 to 21. The table shows counts of county land pixels.

| | Cat 1 | Cat 2 | Cat 3 | Cat 4 | Cat 5 |
|---|---|---|---|---|---|
| County land pixels (bbox) | 54,541,629 | = | = | = | = |
| Land pixels inundated | 6,372,811 (11.7%) | 10,420,493 (19.1%) | 20,836,136 (38.2%) | 31,467,272 (57.7%) | 33,855,573 (62.1%) |
| Land pixels = 255 | 48,168,818 | 44,121,136 | 33,705,493 | 23,074,357 | 20,686,056 |
| **Max class present** | 9 | 12 | 15 | 19 | **21** |
| Class 99 | 0 | 0 | 0 | 0 | 0 |
| Class 0 | 0 | 0 | 0 | 0 | 0 |
| Census-water pixels with a depth class | 0.9% | 1.7% | 2.8% | 3.9% | 4.0% |

The inundated land area rises steadily from Category 1 to Category 5, which is what we expect.

Full frequency tables for land pixels in the Miami-Dade window (classes that are absent are not listed):

- **Cat 1:** 1: 2,516,416 · 2: 1,112,840 · 3: 964,406 · 4: 509,433 · 5: 334,047 · 6: 403,468 · 7: 281,281 · 8: 230,304 · 9: 20,616 · 255: 48,168,818
- **Cat 2:** 1: 1,798,940 · 2: 1,602,912 · 3: 1,529,466 · 4: 1,314,727 · 5: 988,614 · 6: 999,266 · 7: 747,909 · 8: 550,625 · 9: 370,306 · 10: 199,896 · 11: 282,299 · 12: 35,533 · 255: 44,121,136
- **Cat 3:** 1: 2,340,917 · 2: 1,977,086 · 3: 1,659,311 · 4: 1,607,323 · 5: 1,767,174 · 6: 2,206,505 · 7: 2,154,077 · 8: 2,108,704 · 9: 1,658,600 · 10: 1,498,015 · 11: 901,783 · 12: 361,985 · 13: 304,964 · 14: 280,990 · 15: 8,702 · 255: 33,705,493
- **Cat 4:** 1: 958,520 · 2: 1,002,563 · 3: 1,020,778 · 4: 1,365,357 · 5: 1,921,307 · 6: 1,944,716 · 7: 1,903,581 · 8: 1,871,917 · 9: 1,983,126 · 10: 2,437,700 · 11: 2,957,824 · 12: 2,824,868 · 13: 2,240,262 · 14: 2,389,512 · 15: 1,879,453 · 16: 1,367,903 · 17: 1,052,263 · 18: 335,499 · 19: 10,123 · 255: 23,074,357
- **Cat 5:** 1: 832,685 · 2: 917,560 · 3: 838,607 · 4: 869,541 · 5: 964,917 · 6: 1,019,981 · 7: 977,253 · 8: 1,347,571 · 9: 1,786,562 · 10: 1,704,008 · 11: 1,775,279 · 12: 1,673,401 · 13: 2,218,559 · 14: 3,652,639 · 15: 3,000,572 · 16: 2,285,783 · 17: 2,212,262 · 18: 2,160,593 · 19: 1,601,851 · 20: 1,225,596 · 21: 790,353 · 255: 20,686,056

The full tables for the whole window, Census water, and outside-county pixels are in the scratch JSON from this session. They can be regenerated in about 10 s.

### Explicit answers

- **Is 0 used?** No. Value 0 does not appear anywhere in the Miami-Dade window, and the whole-raster histogram in `.aux.xml` shows 0 pixels at value 0 as well. **0 has no meaning in this data.**
- **What does 255 (nodata) mean?** It stands for three different things that the file does not tell apart:
  1. dry land that is not inundated in this category
  2. water bodies masked by NHC (NHD water and the intertidal/estuarine wetland mask)
  3. anything outside the SLOSH grid coverage

  The file has no separate "not inundated" code. Surge depth only exists where there is inundation. **On Census land inside Miami-Dade, 255 has to be treated as "not inundated"** (share numerator = 0, pixel stays in the denominator). This rests on two points. First, the whole county is inside SLOSH coverage: Category 5 inundates 62% of county land, reaching the Everglades interior and Homestead. Second, for our purposes the only other meaning of 255 on land is NHC's water mask. Using rasterio's masked reads would silently drop these pixels from the denominator and inflate every share, so Stage 2 must read raw values.
- **Does 99 (levee) appear in Miami-Dade?** No, 0 pixels in all five categories. The Stage 2 rule "99 never enters a depth calculation" still holds, and `levee_share` will be 0 everywhere.
- **Maximum depth class in Miami-Dade:** 9 (Cat 1), 12 (Cat 2), 15 (Cat 3), 19 (Cat 4), 21 (Cat 5, "more than 20 ft").
- **Open ocean and Biscayne Bay:** the raster extent covers them, but they carry **255**, not a depth. I checked 5×5-pixel samples at the following locations, and every one was 255 in all five categories:
  - the Atlantic east of Key Biscayne and east of Elliott Key
  - central and north Biscayne Bay
  - Card Sound
  - Barnes Sound / Florida Bay

  Across all Census water pixels, 96 to 99% are 255. The remaining 1 to 4% carry depth classes and sit along shorelines, canals, and small lakes where NHD and Census water differ. The land-only mask in Stage 2 excludes these pixels.

Other spot checks, each a 5×5 sample:

| Location | Cat 1 | Cat 3 | Cat 4 | Cat 5 |
|---|---|---|---|---|
| Miami Beach | 1 | 3–4 | 4–6 | 6–7 |
| Homestead | none | 1–3 | 7–8 | 9–11 |
| Everglades interior (25.75, -80.75) | none | none | 7–8 | 11–12 |
| Downtown Miami | none | none | 1 | 2–3 |
| Doral | none | none | none | none |

"None" means 255. The pattern is geographically plausible.

## 1d. Resolution against tracts and block groups

Land-only area = TIGER 2024 polygon minus `tl_2024_12086_areawater`, measured in EPSG:5070 and divided by 90.2 m² per pixel.

| | Tracts (n = 707) | Block groups (n = 1,843) |
|---|---|---|
| Median pixels | 12,790 | 4,184 |
| 25th percentile | 7,018 | 2,404 |
| 5th percentile | 2,391 | 774 |
| 1st percentile | 1,032 | 404 |
| Smallest with land | 522 (12086006722) | **224** (120860090242) |
| Units under 500 px | 0 (excl. water) | 29 |
| Units under 1,000 px | 5 | 148 |
| Zero land | 1: **12086990000** | 1: **120869900000** |

The zero-land units are the all-water offshore tract and block group. They have no land pixels, so their shares genuinely cannot be computed and they will be **NA**. All other units get values.

Coarseness is acceptable. Even the smallest block group (about 224 px) resolves shares in steps of about 0.4%. Precision at block-group level is still limited in a different way: NHC says the product is not meant for "grid cell assessment", and the underlying SLOSH cells are tens to hundreds of metres across, far coarser than the 10 m pixels. Block-group shares will look more precise than the model behind them is.

## 1e. Summary

**Categories available:** all five (1, 2, 3, 4, 5), one raster each. Category 5 covers only Texas to the NC/VA border, which includes Miami-Dade. The proposed 1 / 3 / 5 plan is feasible. Categories 2 and 4 are also available if wanted.

**What each value means:**
| Value | Meaning |
|---|---|
| 0 | Not used. Absent from both the data and the metadata. |
| 1–21 | Depth-above-ground bins. 1 = less than 1 ft … 20 = 19–20 ft, 21 = more than 20 ft. |
| 99 | Levee area, not a depth. Absent in Miami-Dade. |
| 255 (nodata tag) | No surge value. On Miami-Dade land this means **not inundated**. It is also used for water and for areas outside SLOSH coverage. |

**Estimated processing time (Stage 2):** a few minutes in total. Each category needs one windowed read (about 1.5 s). The plan is to rasterize the tract and block-group land polygons once into label grids and reuse them for every category. For each category, a `bincount` over unit × class takes seconds. Peak memory in this inspection was **about 2.2 GB**, mostly from rasterize temporaries. Stage 2 should stay around 2 to 2.5 GB. At inspection time the system had 38% of its 16 GB memory free, and the SLR job was using about 0.9 GB. I expect this to be safe, but I will check memory pressure before starting.

**Data quality issues and decisions to flag:**
1. **255 serves as both nodata and "not inundated".** Stage 2 must not use masked reads or `nodata`-aware zonal tools such as rasterstats defaults. Doing so would drop dry land from the denominator.
2. **NHC's water and wetland mask differs from Census water.**
   - Some Census-land pixels are 255 because NHC masked them as water or intertidal wetland: mangrove fringes, and parts of the Everglades and south Dade coast. These count as "not inundated land", which slightly understates shares in coastal wetland tracts.
   - In the other direction, 1 to 4% of Census water pixels carry depths. The Census water mask removes them.
3. **Category 5 has a different extent from Categories 1 to 4.** Row offsets must be computed from bounds for each file.
4. **MOM values are a worst-case envelope and do not show one storm.** Category 4 and 5 inundate 58 to 62% of county land, including the Everglades interior. This is expected for MOMs, but it squeezes the variation between units at high categories. Many inland tracts may show 100%.
5. **Class 21 has no upper bound, and the classes are bins.** `mean_depth_class` is a mean of bin codes, not of feet. For example, class 1 covers anything under 1 ft.
6. **Version:** the June 2026 reprocessing fixes a South Florida bug. Use only this download.
7. **The data does not match the brief in one small way:** the brief says "class 1 = 0 to 1 ft", while NHC says "less than 1 foot above ground". This is the same bin in practice. Nothing else conflicts with the description.

**Before Stage 2:**
- Confirm the categories (1, 3, 5, or all five).
- Confirm the Census boundary path. I found `Modelling Data from Web/boundaries/` containing `tl_2024_12_tract.zip`, `tl_2024_12_bg.zip` and `tl_2024_12086_areawater.zip`, and read them for 1d, but I need you to confirm this is the right set.
- Decide where rasterio should live. It is not in the project `.venv`. I can install it there after the SLR job finishes, or keep a separate venv.
