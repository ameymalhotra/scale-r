# NOAA Sea Level Rise data: Stage 2 processing

**Data preparation only.** Five NOAA layers were turned into land-area
exposure variables for every Miami-Dade tract and block group. Nothing was
joined to the analysis tables, modelled or correlated with investment. The
GeoPackage was only read, never modified.

Script: `scripts/process_slr.py`. Full run log: `output/slr_processing_log.txt`.
Stage 1 inspection: `slr_inspection.md`. Processed 22 September 2026.

| Output | Rows | Columns |
|---|---|---|
| `slr_tract.csv` | 707 | GEOID + 10 variables |
| `slr_blockgroup.csv` | 1,843 | GEOID + 10 variables |

GEOID is a string with prefix `12086`. Per-layer checkpoints are in
`output/slr_checkpoints/`.

---

## Layers processed and why

| Layer | Variables | Role |
|---|---|---|
| `FL_SE_slr_1_0ft` | `slr_1ft_area_share`, `slr_1ft_any` | primary |
| `FL_SE_slr_2_0ft` | `slr_2ft_area_share`, `slr_2ft_any` | primary |
| `FL_SE_slr_3_0ft` | `slr_3ft_area_share`, `slr_3ft_any` | primary |
| `FL_SE_slr_6_0ft` | `slr_6ft_area_share`, `slr_6ft_any` | primary |
| `FL_SE_low_3_0ft` | `low_3ft_area_share`, `low_3ft_any` | sensitivity |

Ocean-connected inundation (`_slr_`) is the conventional definition of sea
level rise exposure, so it is the primary variable. The unconnected low-lying
layer (`_low_`) is included at one scenario only. Miami-Dade sits on porous
limestone, where water can rise through the ground without a surface
connection to the ocean, so unconnected low areas are not a trivial category.
One scenario is enough to show whether including them changes the picture.
The two kinds are kept as separate columns and never combined.

`gridcode` is ignored. It is constant at 1 in the `_slr_` layers and cannot
be interpreted in `_low_` without NOAA metadata. The shares are computed from
polygon geometry only.

## Variables

- **`{prefix}_area_share`**: inundated land area divided by TIGER `ALAND`.
  This is the primary variable.
- **`{prefix}_any`**: 1 if any land in the unit is inundated, otherwise 0.
- **0 versus NA**: a unit entirely outside the inundation extent gets 0. The
  one unit per grain with `ALAND` = 0 gets NA for all ten variables, since it
  has no land to inundate:
  - tract `12086990000`
  - block group `120869900000`

  These are the county's open-water census units (ocean and bay).

## Method

1. **Read one layer at a time**, limited to the Miami-Dade bounding box
   through the GeoPackage's spatial index. Each layer is released before the
   next is read, and the 4 GB file is never held in memory.
2. **Reproject** NOAA and TIGER from EPSG:4269 to **EPSG:6346** (UTM 17N,
   NAD83(2011)) before any area calculation.
3. **Check validity** of every feature read in every processed layer, and of
   the TIGER tracts, block groups and water features. Repair with
   `make_valid` only where needed.
4. **Clip** to Miami-Dade land (state 12, county 086).
5. **Subdivide** large polygons into pieces of at most 2,000 vertices by
   recursive halving, the same idea as PostGIS `ST_Subdivide`.
6. **Intersect** each unit's land footprint with the pieces. Merge the
   results per unit, so overlapping features are never counted twice, and
   take the area.

### Land footprint

Numerator and denominator are both land. This was a decision made after
checking the data: **NOAA's inundation polygons include existing open
water.** A box of open Biscayne Bay is 100% "inundated" at 1 ft, and TIGER
units extend into the bay. Intersecting raw unit polygons would therefore
count bay water as inundated land and could push shares above 1.

Each unit's land footprint is its TIGER polygon minus TIGER `areawater`
(`tl_2024_12086_areawater`). Only features the Census counts as water
(`AWATER` > 0) are removed. Three stream polygons (MTFCC H3010) have
`ALAND` > 0 and `AWATER` = 0, meaning the Census counts them as land, so
they stay as land. An earlier run removed them, which cut one block group's
footprint to 30% of its `ALAND` and understated its share about threefold.
That run was discarded.

After the fix, footprint area divided by `ALAND` is **0.9992 to 0.9994 for
every unit**, at both grains. The steady 0.07% gap is the UTM scale factor
set against the Census's own area calculation. Because of it, a fully
inundated unit reaches about 0.9993, never exactly 1.

### Performance note

The inspection report estimated about 9 minutes per scenario. A first
attempt that intersected units against the unsplit layer ran for 30+ minutes
on one layer without finishing. The ocean-connected surface is a single
~2.2 million vertex polygon, and it was being reprocessed for every unit it
touched.

Subdividing it first cut each layer to **1 to 5 minutes, about 15 minutes
for all five.** Total area before and after subdivision differs by at most
3e-14 (relative), i.e. floating-point noise.

## Geometry repairs

**None needed.** Zero invalid geometries in all five layers, as read for
Miami-Dade:

| Layer | Features |
|---|---|
| `FL_SE_slr_1_0ft` | 10,256 |
| `FL_SE_slr_2_0ft` | 6,133 |
| `FL_SE_slr_3_0ft` | 5,845 |
| `FL_SE_slr_6_0ft` | 5,682 |
| `FL_SE_low_3_0ft` | 5,434 |

The TIGER tracts (707), block groups (1,843) and water features (2,377) were
also all valid. `make_valid` was never applied.

---

## Validation

### Structure

- **Row counts:** 707 tracts and 1,843 block groups, matching expectations.
- **GEOIDs:** all unique strings with prefix `12086`.
- **Shares within [0, 1]:** yes for every share at both grains, with zero
  out of range. There is no sign of a CRS or geometry problem.

### Monotonicity (every unit checked explicitly)

| Check | Tracts | Block groups |
|---|---|---|
| 2 ft ≥ 1 ft | 0 violations | 0 violations |
| 3 ft ≥ 2 ft | 0 violations | 0 violations |
| 6 ft ≥ 3 ft | 0 violations | 0 violations |
| wet → dry between consecutive scenarios | 0 | 0 |

### Cross-grain nesting

Block groups tile tracts exactly, so the two grains must agree. For all five
layers:

- no wet block group sits in a dry tract;
- no wet tract lacks a wet block group;
- each tract's inundated land area equals the sum over its block groups,
  with a largest difference of 0.00 m².

### Per scenario, tracts (706 with land)

"Entirely inundated" means share ≥ 0.99.

| Variable | Dry | Wet | Entirely inundated | Mean | Median | Median among wet |
|---|---|---|---|---|---|---|
| `slr_1ft` | 592 | 114 | 0 | 0.0094 | 0.0000 | 0.0152 |
| `slr_2ft` | 582 | 124 | 0 | 0.0164 | 0.0000 | 0.0286 |
| `slr_3ft` | 553 | 153 | 0 | 0.0431 | 0.0000 | 0.1050 |
| `slr_6ft` | 226 | 480 | 12 | 0.3393 | 0.2547 | 0.5218 |
| `low_3ft` | 232 | 474 | 0 | 0.0252 | 0.0037 | 0.0095 |

### Per scenario, block groups (1,842 with land)

| Variable | Dry | Wet | Entirely inundated | Mean | Median | Median among wet |
|---|---|---|---|---|---|---|
| `slr_1ft` | 1,592 | 250 | 0 | 0.0069 | 0.0000 | 0.0169 |
| `slr_2ft` | 1,561 | 281 | 0 | 0.0137 | 0.0000 | 0.0315 |
| `slr_3ft` | 1,489 | 353 | 0 | 0.0453 | 0.0000 | 0.1207 |
| `slr_6ft` | 732 | 1,110 | 76 | 0.3275 | 0.1631 | 0.5575 |
| `low_3ft` | 985 | 857 | 0 | 0.0203 | 0.0000 | 0.0118 |

### Units changing from dry to wet

| Step | Tracts | Block groups |
|---|---|---|
| 1 ft → 2 ft | 10 | 31 |
| 2 ft → 3 ft | 29 | 72 |
| 3 ft → 6 ft | 327 | 757 |

Exposure is concentrated and changes slowly up to 3 ft. At 6 ft it becomes
widespread: two-thirds of tracts have some inundated land. For 1–3 ft
analysis, the variable is zero for most units.

### Inundated land area

Of 4,920.9 km² of county land (sum of tract `ALAND`), the inundated land is:

| Scenario | Inundated land | Share of county land |
|---|---|---|
| 1 ft | 739.4 km² | 15.0% |
| 3 ft | 1,450.2 km² | 29.5% |
| 6 ft | 2,974.7 km² | 60.5% |

The 1 ft figure is concentrated: **96% of it lies in five tracts.** They are
the large western and southern wetland tracts that NOAA models as
ocean-connected (011408 alone accounts for 423.5 km²), plus the Biscayne
National Park keys. Almost none of it is urban land. The large wetland tracts dominate the
county total, but they do not distort the per-unit shares.

---

## `_slr_` versus `_low_` at 3 ft (the sensitivity check)

### The two layers are geographically disjoint

At 3 ft on Miami-Dade land:

| Layer | Land area |
|---|---|
| `_slr_` | 1,450.2 km² |
| `_low_` | 144.6 km² |
| overlap | 0.000 km² |

**This contradicts `slr_inspection.md`**, which says the two kinds "overlap
in extent". At a given water level, NOAA assigns each low-lying cell to one
layer or the other, connected or unconnected. Two consequences:

- **Built-in negative relationship.** Land that is ocean-connected cannot
  also be unconnected low land, so the two shares are pushed apart. A unit
  that is mostly `_slr_` has little land left for `_low_`.
- **Adding is safe.** `slr + low` is the true combined share, with nothing
  counted twice. It is used below only to measure the ranking change. It is
  not a column in the output files.

### Results

| | Tracts | Block groups |
|---|---|---|
| Units wet under `_slr_` | 153 | 353 |
| Units wet under `_low_` | 474 | 857 |
| Units wet under either | 548 | 1,110 |
| Wet under `_low_` only | 395 | 757 |
| Mean share, `_slr_` / `_low_` | 0.043 / 0.025 | 0.045 / 0.020 |
| Pearson r, `_slr_` vs `_low_` | −0.018 | −0.042 |
| Spearman, `_slr_` vs `_low_` | −0.106 | −0.148 |
| Spearman, `_slr_` vs `slr + low` | 0.581 | 0.602 |
| Median rank shift, `_slr_` → `slr + low` | 202 | 568 |
| Top-10 overlap, `_slr_` vs `slr + low` | 8/10 | 9/10 |
| Top-50 overlap, `_slr_` vs `slr + low` | 42/50 | 43/50 |
| Top-100 overlap, `_slr_` vs `slr + low` | 70/100 | 87/100 |
| Top-100 overlap, `_slr_` vs `_low_` | 11/100 | 1/100 |

### Reading

- **They measure different places.** Correlation is essentially zero to
  slightly negative, and the most exposed units under one layer are almost
  never the most exposed under the other.
- **Most-exposed units are stable.** Including unconnected low areas barely
  changes which units are most exposed: 8 of the top 10 tracts and 42 of the
  top 50 survive. `_low_` shares are small, mostly around 1% of land among
  wet units.
- **Lower ranks are not stable.** Including `_low_` does change the broad
  picture. It makes 395 otherwise-dry tracts wet, and the overall rank
  correlation drops to about 0.6.
- **Implication.** Any analysis that relies on exposed-versus-not, or on
  ranks across the whole county, should be checked with and without
  `low_3ft`. An analysis driven by the most exposed units is robust to it.

---

## Geography sanity check: top 10 tracts by `slr_3ft_area_share`

| GEOID | 1 ft | 3 ft | 6 ft | low 3 ft | Location | ALAND km² |
|---|---|---|---|---|---|---|
| 12086981200 | 0.443 | 0.954 | 0.980 | 0.002 | Biscayne Bay coastal wetland south of Turkey Point | 24.4 |
| 12086011412 | 0.373 | 0.934 | 0.995 | 0.034 | coastal wetland south and east of Florida City | 183.3 |
| 12086011408 | 0.490 | 0.913 | 0.994 | 0.009 | Everglades National Park | 864.6 |
| 12086004304 | 0.000 | 0.865 | 0.994 | 0.000 | Miami Beach | 0.5 |
| 12086004208 | 0.011 | 0.854 | 0.995 | 0.000 | Miami Beach | 0.1 |
| 12086980100 | 0.586 | 0.793 | 0.982 | 0.001 | Biscayne National Park keys (Elliott Key) | 14.2 |
| 12086004204 | 0.005 | 0.790 | 0.989 | 0.000 | Miami Beach | 0.4 |
| 12086004406 | 0.009 | 0.748 | 0.951 | 0.000 | Miami Beach | 0.2 |
| 12086010613 | 0.501 | 0.725 | 0.786 | 0.021 | Cutler Bay bay shoreline | 7.9 |
| 12086003915 | 0.009 | 0.700 | 0.991 | 0.000 | Miami Beach | 0.8 |

Locations were identified from each tract's representative point and the
places it overlaps. The unincorporated ones are my reading of their
coordinates.

**These look right.** All ten are coastal or low-lying:

- **Five are Miami Beach.** They are mostly dry at 1 ft and 70–87%
  inundated at 3 ft, the known barrier-island profile.
- **Five are coastal wetland or park land** on southern Biscayne Bay and in
  the Everglades. They are already 37–59% inundated at 1 ft.

**Key Biscayne is not in the top 10.** It ranks 70th: its 4 tracts have a
median 3 ft share of 0.059. Other barrier-island places rank higher:

| Place | Tracts | Median 3 ft share | Best rank |
|---|---|---|---|
| Surfside | 1 | 0.447 | 23 |
| Sunny Isles Beach | 6 | 0.344 | 31 |
| Bal Harbour | 1 | 0.210 | 49 |
| Fisher Island | 1 | 0.151 | 61 |

Key Biscayne's comparatively low 3 ft share is what NOAA's surface gives,
not a join error. The monotonicity and nesting checks rule that out. It is
worth keeping in mind if Key Biscayne is expected to be among the most
exposed.

The top of the ranking mixes two kinds of place:

- sparsely populated wetland and park tracts, some very large (864 km²);
- dense, small Miami Beach tracts.

That matters for later analysis, but it is a property of the data, not a
processing fault.

---

## Discrepancies with the inspection report and the brief

1. **`_slr_` and `_low_` do not overlap.** The inspection report says they
   "overlap in extent". At 3 ft they are disjoint on Miami-Dade land, as
   measured above.
2. **The runtime estimate was far off in both directions.** The inspection
   estimate was about 9 minutes per scenario. A naive intersection was much
   slower, 30+ minutes for a single layer. Subdividing was much faster,
   about 15 minutes for all five layers.
3. **Unit polygons include water.** The brief's method (intersect units with
   inundation, divide by ALAND) would count bay water as inundated land,
   because NOAA polygons cover existing water. The land-only footprint
   resolves this. The user confirmed it.

Everything else in the inspection report was confirmed:

- one GeoPackage;
- layer names as documented;
- EPSG:4269 for both NOAA and TIGER;
- no invalid geometries;
- one very large ocean-connected polygon;
- one `ALAND` = 0 unit per grain.
