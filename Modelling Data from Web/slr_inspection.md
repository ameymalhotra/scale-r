# NOAA Sea Level Rise data: Stage 1 inspection

**Inspection only.** Nothing was processed, joined, clipped or written. The
downloaded files were not modified. Metadata and feature counts were read
without pulling full geometries into memory, except for two Miami-Dade
bounding-box subsets used to measure geometry complexity and estimate
processing time.

Script: `scripts/inspect_slr.py`. Inspected 20 September 2026.

---

## 1a. What is in the download

### Location and size

```
tract-level/Physical Indicators/FL_SE_slr_data_dist/
    FL_SE_slr_final_dist.gpkg      4,087,308,288 bytes  (4.09 GB)
    NOAA_OCM_SLR_Data_README.txt           1,062 bytes
```

**Two things differ from what you described.** The download is **4.09 GB, not
roughly 1 GB.** And it is **a single GeoPackage, not one file per scenario**:
all 42 layers live inside `FL_SE_slr_final_dist.gpkg`. Nothing is missing;
the structure is just different from the per-foot-shapefile layout NOAA also
publishes.

There are **no depth rasters and no mapping-confidence rasters** in this
download. The README describes them, but this distribution is vector only. If
depth in metres above ground matters later, that is a separate download.

### Layers

**42 layers, and they come in two kinds.** This is the most important thing in
this report, because the README draws a distinction your spec does not:

| Kind | Layers | What NOAA says it is |
|---|---|---|
| `FL_SE_slr_*ft` | 21 | **Ocean-connected** inundation at the stated sea level |
| `FL_SE_low_*ft` | 21 | **Unconnected low-lying areas** that may flood |

These are different things. The `_slr_` layers are the inundation surface
proper: water connected to the ocean at that sea level. The `_low_` layers are
depressions below the same elevation that are *not* hydrologically connected
to the ocean, so NOAA flags them separately rather than folding them in. They
overlap in extent but are not nested, and they are not additive.

**Which of the two you want is a decision for you**, and it changes the
variable's meaning. The `_slr_` layers alone are the standard choice for
"inundated at N feet". Including `_low_` captures areas that could pond or
flood without a surface connection, which in a flat, karst county like
Miami-Dade is not a negligible category.

### Scenarios

**21 scenarios per kind, in half-foot steps from 0.0 to 10.0 feet.** Not the
one-foot steps you expected, so there are roughly twice as many as anticipated.

```
0.0  0.5  1.0  1.5  2.0  2.5  3.0  3.5  4.0  4.5  5.0
5.5  6.0  6.5  7.0  7.5  8.0  8.5  9.0  9.5  10.0
```

**Scenarios are encoded in the layer name, not as an attribute.** The naming
is `FL_SE_{kind}_{whole}_{decimal}ft`, so 3.5 feet is `FL_SE_slr_3_5ft`. Both
kinds carry the full set of 21.

### Feature counts

| Layer | Features | | Layer | Features |
|---|---|---|---|---|
| `FL_SE_slr_0_0ft` | 9,785 | | `FL_SE_low_0_0ft` | 7,317 |
| `FL_SE_slr_0_5ft` | 14,418 | | `FL_SE_low_0_5ft` | 6,587 |
| `FL_SE_slr_1_0ft` | 10,412 | | `FL_SE_low_1_0ft` | 9,980 |
| `FL_SE_slr_1_5ft` | 8,349 | | `FL_SE_low_1_5ft` | 11,233 |
| `FL_SE_slr_2_0ft` | 6,423 | | `FL_SE_low_2_0ft` | 8,703 |
| `FL_SE_slr_2_5ft` | 6,656 | | `FL_SE_low_2_5ft` | 7,799 |
| `FL_SE_slr_3_0ft` | 6,329 | | `FL_SE_low_3_0ft` | 8,674 |
| `FL_SE_slr_3_5ft` | 6,859 | | `FL_SE_low_3_5ft` | 11,051 |
| `FL_SE_slr_4_0ft` | 11,723 | | `FL_SE_low_4_0ft` | 15,508 |
| `FL_SE_slr_4_5ft` | 14,647 | | `FL_SE_low_4_5ft` | 15,685 |
| `FL_SE_slr_5_0ft` | 21,614 | | `FL_SE_low_5_0ft` | 15,689 |
| `FL_SE_slr_5_5ft` | 14,068 | | `FL_SE_low_5_5ft` | 16,257 |
| `FL_SE_slr_6_0ft` | 7,309 | | `FL_SE_low_6_0ft` | 21,832 |
| `FL_SE_slr_6_5ft` | 5,500 | | `FL_SE_low_6_5ft` | 31,839 |
| `FL_SE_slr_7_0ft` | 6,624 | | `FL_SE_low_7_0ft` | 61,345 |
| `FL_SE_slr_7_5ft` | 10,331 | | `FL_SE_low_7_5ft` | 95,926 |
| `FL_SE_slr_8_0ft` | 21,472 | | `FL_SE_low_8_0ft` | 84,600 |
| `FL_SE_slr_8_5ft` | 19,450 | | `FL_SE_low_8_5ft` | 82,368 |
| `FL_SE_slr_9_0ft` | 20,004 | | `FL_SE_low_9_0ft` | 60,316 |
| `FL_SE_slr_9_5ft` | 12,968 | | `FL_SE_low_9_5ft` | 41,020 |
| `FL_SE_slr_10_0ft` | 7,749 | | `FL_SE_low_10_0ft` | 58,769 |

Totals: **915,188 features**, of which 242,690 are `_slr_` and 672,498 are
`_low_`.

**Feature count does not track scenario severity**, and this is expected
rather than a fault. Counts fall from 0.5 ft to 3.0 ft, then rise again. As
water rises, separate puddles merge into fewer, larger polygons, then new
areas begin to flood and fragment again. Polygon count is a shape artifact,
not a measure of how much land is wet. Area is the measure, which is why the
Stage 2 variable is an area share.

### Geometry and attributes

**Geometry type:** MultiPolygon, all 42 layers.

**Attributes:** two integer fields on 41 layers, `Id` and `gridcode`. One
layer, `FL_SE_low_7_5ft`, carries a third field `Shape_Leng` (float). That
single inconsistency is cosmetic, but any code that assumes a fixed schema
across layers will trip on it.

| Field | `_slr_` layers | `_low_` layers |
|---|---|---|
| `Id` | sequential row id, 1..n | sequential row id, 1..n |
| `gridcode` | **constant 1** in every layer checked | **highly variable**: 5,323 distinct values in `low_3_0ft`, range 13 to 208,348 |

`gridcode` is constant at 1 across the `_slr_` layers, so it carries no
information there: it is just an inundation flag. In the `_low_` layers it
varies widely and **its meaning is not determinable from the field name or the
README.** It is most likely a raster-derived region identifier from the
polygonisation step, but I am not going to assert that. If the `_low_` layers
are used, this field should either be ignored or checked against NOAA's
metadata first.

**There is no county, region or scenario attribute in any layer.** Nothing
inside the table identifies geography beyond the polygon itself.

### How counties are separated

**They are not.** This is one continuous southeast Florida extent with no
county field, so the Miami-Dade clip in Stage 2a has to be spatial, against
the TIGER county boundary.

Full data extent, in degrees: longitude **-80.882 to -79.973**, latitude
**25.107 to 26.972**.

A bounding-box test against Florida tracts touches seven counties: Broward,
Miami-Dade, Palm Beach, Martin, Monroe, and FIPS 021 and 093. **That
overstates real coverage**, because a rectangle around coastal polygons sweeps
in inland counties the data does not actually reach. Determining true county
coverage means intersecting against county polygons, which is Stage 2 work and
was not done. What is certain is that the extent spans well north of
Miami-Dade, consistent with the "FL_SE" regional naming and with your
recollection of Palm Beach and at least one other county.

For scale: Miami-Dade's own bounding box is longitude -80.874 to -80.063,
latitude 25.137 to 25.979. About **92 percent** of `slr_3_0ft` features and
**63 percent** of `low_3_0ft` features fall inside it, so the Miami-Dade clip
will discard a meaningful share of the `_low_` data but relatively little of
the `_slr_` data.

---

## 1b. Coordinate reference systems

| Layer set | CRS | Type |
|---|---|---|
| All 42 NOAA layers | **EPSG:4269** (NAD83) | geographic, degrees |
| `tl_2024_12_tract.zip` | **EPSG:4269** (NAD83) | geographic, degrees |
| `tl_2024_12_bg.zip` | **EPSG:4269** (NAD83) | geographic, degrees |

**The two sources already agree**, which is better than expected: no datum
shift is involved and the overlay is geometrically safe as-is.

**Reprojection is still required, for both.** EPSG:4269 is geographic, so
distances and areas are in degrees and cannot be used for an area share.
Both layers must go to **EPSG:6346** (UTM 17N, NAD83(2011)) before any area
calculation, which is what this project already uses for centroid assignment.
I confirmed the reprojection runs in about half a second for a Miami-Dade
sized subset, so it costs nothing.

The GeoPackage also declares EPSG:4326 in its spatial-reference table, but no
layer uses it. It is an unused default entry, not a mixed-CRS problem.

---

## 1c. Summary, processing estimate, and data quality

### Scenarios available

**21 sea level increments, 0.0 to 10.0 feet in half-foot steps, each in two
kinds**: ocean-connected inundation (`_slr_`) and unconnected low-lying areas
(`_low_`). 42 layers in total.

### Estimated processing time per scenario

Measured on real data rather than guessed. Reading a Miami-Dade bounding-box
subset is fast because the GeoPackage carries a full spatial index (168 rtree
tables, one set per layer): **0.1 to 0.9 seconds** per layer. Reprojection to
EPSG:6346 is **about 0.5 seconds**. Neither is a constraint.

The intersection is the cost. Timing the overlay of `slr_3_0ft` against
Miami-Dade tracts:

| Tracts intersected | Time |
|---|---|
| 25 | 55.8 s |
| 100 | 69.2 s |

**The cost is almost entirely fixed, not per-unit.** Fitting those two points
gives roughly a 51-second fixed cost plus 0.18 seconds per unit. That fixed
cost is the engine preparing one enormous polygon, described below.
Extrapolating:

| Work | Estimate |
|---|---|
| One scenario, 707 tracts | **about 3 minutes** |
| One scenario, 1,843 block groups | **about 6 minutes** |
| One scenario, both grains | **about 9 minutes** |
| All 21 `_slr_` scenarios, both grains | **about 3.5 hours** |
| All 42 layers, both grains | **about 7 hours** |

Treat these as order-of-magnitude. They come from one layer at one scenario,
and the `_slr_` layers vary tenfold in feature count. The `_low_` layers
should run faster per feature, since they lack the single giant polygon, but
there are far more features in the upper scenarios.

**This is the practical reason to choose scenarios rather than process all
21.** Three or four scenarios is roughly half an hour; the full set is an
afternoon. If you do want the full set, it is worth restructuring the
intersection first rather than paying the 51-second fixed cost 42 times over.

### Data quality

**Geometry validity: clean.** Zero invalid geometries in either layer checked,
`slr_3_0ft` (5,845 features in the Miami-Dade box) and `low_3_0ft` (5,434
features). No `buffer(0)` or `make_valid` repair appears to be needed, though
Stage 2 should still check every processed layer rather than trusting a
two-layer sample.

**CRS: present and consistent.** No missing or undefined CRS on any layer.

**One extreme geometry, and it drives everything.** In `slr_3_0ft`, a single
feature carries **2,176,843 vertices**, against a mean of 385 across the
layer. This is the connected ocean and bay surface as one multipolygon. It is
why the validity check on that layer took 65 seconds while the same check on
`low_3_0ft`, whose largest feature has 49,942 vertices, took 0.4 seconds. It
is not corruption, it is what an ocean-connected surface looks like when
polygonised, but it is the single biggest factor in Stage 2 runtime and worth
knowing about before optimising anything.

**Schema inconsistency:** `FL_SE_low_7_5ft` has a third field the other 41
layers lack. Harmless if code selects fields explicitly.

**`gridcode` in the `_low_` layers is undocumented** and should not be
interpreted without checking NOAA's metadata, as noted above.

**No missing or null attribute values** were found in the layers inspected.

---

## Stopping here, as agreed

Three decisions are needed before Stage 2 can start:

1. **Which scenarios?** 21 are available, not the ten or eleven a one-foot
   series would give. Common choices for planning horizons are 1, 2, 3 and 6
   feet, but this is yours to set.
2. **`_slr_` only, or `_slr_` and `_low_` both?** The README treats them as
   distinct products. Ocean-connected inundation alone is the conventional
   reading of "sea level rise exposure". Including unconnected low-lying areas
   would produce a second family of variables, roughly doubling both the
   processing time and the column count.
3. **Confirm EPSG:6346** for the area calculations. I see no reason to depart
   from it, and it matches the rest of the project.

No scenario has been processed and no output file has been written.
