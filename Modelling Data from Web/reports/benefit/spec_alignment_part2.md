# Aligning to the Flood What-If specification, Part 2: the four modules

Benefit simulator. 11 Nov 2026. Branch `benefit-simulator`.
Decisions D-166 to D-172 in `DECISIONS.md`. Specification:
`docs/SCALE-R_Flood_What-If_Spec.docx`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| USGS 3DEP 1 m DEM, FL_MiamiDade_D23, with the USGS final DEM report and vendor metadata | Ground elevation at every building; datum check | Lidar Dec 2023 to May 2024 | Read over the web; metadata downloaded |
| FEMA FIRM database 12086C, effective 19 Feb 2027 | Flood zones, base flood elevations, coastal transects, canal model nodes and subbasins, community polygons | Database dated 14 Sep 2026 | Downloaded in Part 1 |
| FEMA FIRM database, effective 11 Sep 2009 (NFHL) | Comparison | Revised 26 Jan 2026 | Already on disk |
| FEMA NFIP Community Status Book (OpenFEMA) | Initial flood map date per community | Refreshed 25 Aug 2026 | OpenFEMA API, 35 Miami-Dade rows |
| Miami-Dade County "Property Point View" (Property Appraiser) | Bedrooms, bathrooms, living area, latest sale | Queried 11 Nov 2026 | Only the allowed fields requested |
| Florida DOR 2026 tax roll (NAL) | Qualification codes for 2025 and 2026 sales | Roll year 2026 | Already on disk |
| USACE National Structure Inventory 2026 | Buildings, values, occupancy, foundation | 2026 | Stage 1 |
| USACE depth-damage curves (go-consequences) | Damage by depth | 2021 | Stage 2 |
| FEMA BCA standard values | Displacement costs | 2025 | Stage 2 |
| NOAA sea level rise inundation | Widening the flood extent under sea level rise | NOAA SLR viewer | Stage 1 |
| FEMA NFIP claims (OpenFEMA) and ACS housing units | Provisional check | Claims 1978 to 2025 (2025 dollars) | Stage 2 |

## In short

- **The model is now four modules.** They are Module A (depth), Module B
  (expected yearly damage), Module C (projects), and Module D (a
  placeholder for the next prompt). Each writes one table keyed by
  building ID (`fd_id`), and the next module reads it. Storm frequencies and
  water level sources are set in one config file, `module_config.json`.
- **Ground elevation is now USGS 3DEP 1 m.** Its datum is confirmed as
  NAVD88 with the GEOID18 model.
- **Water levels: we recommend two methods.**
  - Coastal: use the nearest FEMA transect.
  - Rainfall and canal: use the model point that drains the building's own
    subbasin.
  - Each storm is limited to FEMA's mapped flood extent for that storm.
- **Expected yearly damage (estimated).** The county total is $701 million
  a year in the middle case, with a range of $318 million to $1.9 billion.
  This is four times the Stage 2 figure. Most of it comes from coastal storms
  rarer than the 1% storm. The provisional comparison with insurance claims
  is now further off: residential damage is 16.9 times claims, against 3.1
  in Stage 2. Final calibration still waits for
  the policies file.
- **Seawalls and building elevation work and return results in under 0.1
  seconds.**
  - A 1.5 km seawall on Biscayne Bay in North Miami, crest 8 ft, avoids
    about $1.8 million a year in damage (range $0.7 million to $6.3 million).
  - Raising 2,690 flood-prone homes in a Princeton tract by 3 ft avoids about
    $7.0 million a year ($4.3 million to $9.0 million).

## 1. Decisions from the user, carried out

| Decision | What was done | Result |
|---|---|---|
| Specification copy and check | Saved in `docs/`; Part 1 report updated with a comparison | Floor rule matches; checklist differences listed in Part 1 |
| Switch to USGS 3DEP after confirming the datum | Datum confirmed from USGS metadata; sampled at all buildings | 626,520 from 3DEP; 732 over water or gaps keep NOAA |
| FEMA 2027 as the main water source, 2009 as comparison | Both run through Modules A and B | See section 4 |
| First-floor rule with each community's first flood map date | Community Status Book joined by community | All 35 communities: 29 Sep 1972; no floor changes |
| Bedrooms and bathrooms without personal fields | Only allowed fields requested from the server | 944,398 parcels; see section 2 |
| Compare methods for carrying water levels | Two coastal and three rainfall methods tested | See section 3 |

**Correction to Part 1.** The 2027 rainfall and canal levels cover only the
C-8 and C-9 basins in the north of the county (Biscayne Canal and Snake
Creek). Elsewhere, inland flood zones only have the 1% level. The Part 1
report is corrected.

## 2. House features (for Module D)

- **Kept fields:** parcel ID, bedrooms, full and half bathrooms, living area,
  latest sale price and date.
- **Privacy:** owner names, addresses and coordinates were never requested,
  so they never reached this computer.
- **Bedrooms:** 796,786 parcels have a count.
- **No qualification code in the layer.** It comes from the 2026 tax roll
  where the same sale is listed there. This covers 100,669 sales, all from
  2025 and 2026.
- **Sales added from 2021 onwards:** for 2021 to 2024, the layer adds 92,084
  single-family and 115,821 condo sales. It only holds each property's
  latest sale, so homes sold again since then are missed. These sales have no
  qualification code.
- **Getting the codes:** the free DOR sales files for earlier roll years have
  qualification codes. They were not downloaded because they were not named.
- **Pool data:** skipped (paid) and logged as optional.

## 3. Carrying FEMA water levels to buildings: methods compared

**Checks:**
- **(a)** For buildings inside a 2027 flood zone with a base flood elevation,
  how close is the method's 1% level to that elevation?
- **(b)** Does the method flood the same places FEMA maps as flooding?

Coastal base flood elevations include wave height. The transect levels are
still water. So a small gap is expected, and the spread of the gap matters
most.

**Coastal (502,105 buildings in the coastal study area, 218 transects):**

| Method | Within 0.5 ft of zone elevation | Within 1 ft | 1% zone buildings below the 1% level | Minimal-hazard buildings wrongly below it |
|---|---|---|---|---|
| Nearest transect | 61% | **82%** | 88% | **7.6%** |
| Interpolation along the shoreline | 55% | 77% | 94% | 10.2% |

The two methods differ by a median of only 0.17 ft at the 1% storm.

**Rainfall and canal (92,024 buildings in the C-8 and C-9 subbasins, 1,077 nodes):**

| Method | Within 0.5 ft of zone elevation | Within 1 ft |
|---|---|---|
| Nearest node | 96.5% | 99.5% |
| Node of the building's own subbasin | **100%** | **100%** |
| Average of the 3 nearest nodes | 97.0% | 99.8% |

**Recommendation (D-170).**
- **Coastal:** use the nearest transect. It agrees better with FEMA's own
  elevations and wrongly floods fewer buildings outside the floodplain.
- **Rainfall:** use the node that drains the building's own subbasin. It is
  how FEMA itself set the elevations.

**Extent cap.** Simply filling the land up to a water level also floods
buildings that FEMA maps as outside the floodplain:
- 45,000 buildings in the 0.2% zone were wet in the 1% storm;
- 30,000 buildings outside both zones were wet in the 0.2% storm.

So each storm is limited to FEMA's mapped extent for that storm:
- the 1% storm and more frequent ones reach only the 1% zone;
- the 0.2% storm reaches the 1% and 0.2% zones.

Under sea level rise, NOAA's inundation area for that rise is added. This
adds few buildings (75 to 6,720), so spread beyond today's floodplain is
mostly not captured.

**2009 against 2027 maps.** Where both give a 1% elevation (219,325
buildings), the 2027 one is a median of 0.55 ft higher (10th to 90th
percentile: -0.5 to +3.5 ft):
- 41,690 buildings move into the 1% zone;
- 73,087 move out.

## 4. Module A: depth above the first floor

`depth_above_floor = max(0, water level - first-floor elevation)`, for 5
storms (10%, 4%, 2%, 1%, 0.2%), today and with 1, 2 and 3 ft of sea level
rise. Every building has a value for every storm and scenario, with no
blanks.

**Water level sources after the extent cap:**

| Source | Buildings | Storms |
|---|---|---|
| Coastal transects (nearest) | 386,543 | all 5 |
| Rainfall and canal nodes (own subbasin, C-8 and C-9) | 75,117 | all 5 |
| 2027 map 1% elevation, where neither of the above exists | 68,031 | 1% (0.2% uses the 1% level) |
| 2009 map (comparison only) | 260,450 | 1% (0.2% uses the 1% level) |

**Buildings with water above the first floor:**

| Storm | Today | +3 ft sea level rise | Median depth today (where wet) |
|---|---|---|---|
| 10% (10-year) | 4,581 | 26,481 | 0.5 ft |
| 4% (25-year) | 7,295 | 42,468 | 0.5 ft |
| 2% (50-year) | 72,338 | 207,285 | 0.7 ft |
| 1% (100-year) | 131,971 | 217,344 | 1.1 ft |
| 0.2% (500-year) | 340,047 | 383,589 | 2.2 ft |

The big jump from the 4% to the 2% storm is in FEMA's coastal data: the
median still-water level rises from 2.8 ft to 5.8 ft. The NHC surge maps
stay in the buildings table as worst-case event scenarios only.

**Adding a new storm or a rainfall grid** means adding an entry to `events`
or `sources` in `module_config.json`. The code has a slot for raster depth
grids; nothing else changes.

## 5. Module B: expected yearly damage

- **Formula:** the specification's trapezoid,
  EYD = sum 0.5 x (L_i + L_i+1) x (p_i - p_i+1).
- **Starting point:** loss is 0 at any storm that causes no damage, so the
  curve starts at the most frequent storm with no damage.
- **Damage rules:** kept from Stage 2. Damage covers only the floors the
  water reaches (D-143), and the high end uses whole-building damage for
  non-house buildings (D-148).
- **Range for estimated floors:** following the specification, these floors
  are moved 1 ft up (low) and 1 ft down (high).

**County totals, per year (estimated):**

| Case | Expected yearly damage |
|---|---|
| Low | $318 million |
| **Middle** | **$701 million** |
| High | $1,925 million |
| Beyond the 0.2% storm (middle, reported separately) | $153 million |
| Middle, +1 / +2 / +3 ft sea level rise | $1,082 / $1,541 / $2,088 million |
| Middle, 2009 maps (comparison) | $89 million (+ $14 million beyond 0.2%) |
| Displacement (separate, FEMA standard values) | $37 million |

**Where the middle figure comes from:**
- **By storm range:**
  - 10% to 4%: $53M
  - 4% to 2%: $107M
  - 2% to 1%: $152M
  - 1% to 0.2%: $389M
- **By source:** coastal $695M, map-only $5M, rainfall and canal $1M.
- **By zone:** inside the 1% zone $582M, in the 0.2% zone $119M.
- **By use:** residential $422M, commercial $204M, industrial $41M, public
  $34M.

**Why it is four times Stage 2 ($174M):**
- the 2027 maps' 1% levels are higher and cover more buildings (1% storm
  damage $20.7 billion, against $9.9 billion);
- the 0.2% storm now has its own, much deeper levels (damage $76.6
  billion), where Stage 2 copied the 1% depth;
- three more frequent storms are counted.

For scale, the 0.2% storm damage sits between the worst-case Category 4
($53 billion) and Category 5 ($94 billion) surge maps from Stage 2.

**Provisional comparison with NFIP claims (as Stage 2, 2025 dollars):**

| Measure (694 tracts with 50+ occupied homes) | Stage 2 | Now |
|---|---|---|
| Claims per year | $30.3M | $30.3M |
| Model to claims, all buildings (incl. beyond 0.2%) | 5.6 | 27.9 |
| Model to claims, residential only | 3.1 | 16.9 |
| Rank agreement by tract, all buildings (95% interval) | 0.49 (0.43 to 0.54) | 0.35 (0.28 to 0.41) |
| Rank agreement by tract, residential | 0.47 (0.41 to 0.52) | 0.30 (0.23 to 0.37) |
| Tracts with claims but no modelled damage | 176 | 72 |

- **Better:** fewer tracts with claims but no modelled damage, because
  canal flooding and frequent storms are now included.
- **Worse:** the overall level and the ranking.
- **Likely reason:** the coastal still-water level at the shoreline transect
  is applied undiminished to every building it reaches inland, up to FEMA's
  mapped edge. In reality, surge falls off over land. This mostly affects the
  rare storms that dominate the total.

Nothing has been tuned. Final calibration waits for the policies file, as
agreed. **Treat these dollar figures as provisional.**

## 6. Module C: projects

**Seawall or surge barrier.** The user draws an alignment and gives a crest
height (ft NAVD88).
- **What counts as "behind the wall":** a building is behind it when all
  three hold:
  - the straight line from the building to its nearest point on the coastal
    shoreline crosses the wall (the shoreline is the line FEMA's coastal
    study measures from);
  - it is within 2 km of the shoreline;
  - its ground is below the crest.
- **What the wall does:** for those buildings, coastal water is removed for
  every storm whose coastal level is below the crest. Storms that overtop
  the crest keep their full depth.
- **What it does not do:** water that goes round the ends is not stopped,
  and rainfall flooding is not changed.

**Building elevation.** The selected buildings' first floor is raised by X ft.

**Placeholders.** Pumps and drainage, buyout and green stormwater raise a
clear "not yet available" message. Pumps and drainage need rainfall depths
and drainage basins countywide.

**Run time.** Each scenario recomputes only the affected buildings in 0.02
to 0.07 seconds, after loading the precomputed tables once (0.2 seconds).

## 7. Two test examples

### Example 1: a seawall on Biscayne Bay in North Miami

- **Alignment:** 1.5 km along the Biscayne Bay shoreline in North Miami,
  between about latitude 25.886 and 25.897. It was picked as the 1.5 km
  stretch with the most buildings taking coastal damage (936).

| Crest | Buildings behind it | Storms held back | Damage now, per year | Damage avoided, per year |
|---|---|---|---|---|
| 6 ft NAVD88 | 1,581 | 10% and 4% for all; 2% for 1,281; 1% for 9 | $2.5M ($1.1M to $7.8M) | **$0.57M** ($0.16M to $2.7M) |
| 8 ft NAVD88 | 1,881 | up to the 1% for all; 0.2% for 379 | $2.7M ($1.2M to $8.3M) | **$1.8M** ($0.65M to $6.3M) |
| 8 ft, with 2 ft sea level rise | 1,881 | up to the 2% for 1,557; 1% for 114 | $6.9M ($3.8M to $18.8M) | **$3.1M** ($1.2M to $10.8M) |

**In plain words:**
- A 6 ft wall stops only the frequent, smaller storms, which do little of the
  damage.
- An 8 ft wall holds back storms up to the 100-year level for every building
  behind it. That avoids about two thirds of their expected damage.
- With 2 ft of sea level rise, the same wall is overtopped more often but
  still avoids more dollars, because there is more damage to avoid.

### Example 2: elevating homes in a flood-prone tract in Princeton

- **Tract:** 12086010502 in Princeton, the tract with the highest
  single-family expected damage.
- **Homes:** 2,690 of its 3,031 single-family homes have water above the
  floor in the 1% storm. Most are in the 2027 coastal AE zone, with a
  median 1% depth of 1.7 ft above the floor.
- **Damage now:** $8.5M a year ($5.1M to $11.6M), about $3,100 per home.

| Raise | Damage avoided, per year |
|---|---|
| 2 ft | $5.9M ($3.6M to $6.5M) |
| **3 ft** | **$7.0M** ($4.3M to $9.0M) |
| 5 ft | $8.2M ($5.0M to $10.8M) |

**In plain words:**
- Raising these homes by 3 ft removes about four fifths of their expected
  flood damage.
- Raising them by 5 ft removes almost all of it, except in the rarest storms.

## 8. Which numbers are estimated and which are assumed

- **Measured (data):**
  - ground elevation (USGS lidar);
  - FEMA 2027 water levels and zones;
  - building values and types (NSI);
  - claims.
- **Estimated (our model):**
  - water level at each building (method of D-170);
  - depth;
  - damage;
  - expected yearly damage;
  - losses avoided.
- **Assumed:**
  - first-floor heights (all estimated, D-162), and the ±1 ft range;
  - full compliance with flood-zone building rules;
  - depth-damage curves;
  - the floors-reached rule;
  - no damage from frequent storms where FEMA gives only the 1% level;
  - the 0.2% storm copying the 1% level in those areas;
  - sea level rise added to coastal water only;
  - the seawall rule (no flanking protection, no failure);
  - displacement days.

## 9. Main limitations

- **Coastal still water is applied without falling off inland.** It also
  leaves out wave height. The damage total and the claims gap are likely too
  high, mostly in rare storms.
- **Rainfall and canal flooding has five storms only in the C-8 and C-9
  basins.** Elsewhere only the 1% level exists. Pumps, drainage and green
  infrastructure wait for countywide rainfall depths.
- **Sea level rise does not widen the floodplain much** beyond FEMA's
  current mapped extent (only NOAA's inundation area is added).
- **All first floors are estimated** until elevation certificates or the
  NFIP policies file arrive. The policies download is still incomplete.
- **The seawall rule ignores water coming round the ends**, wall failure,
  and drainage behind the wall.
- **The 2021 to 2024 sales lack qualification codes** for now.
- **These are screening estimates, not design results.**
