# What does a typical funded flood project look like? (Part 1)

Benefit simulator. 15 Nov 2026. Branch `benefit-simulator`. Decision D-196
in `DECISIONS.md`. Script `scripts/benefit/typical_projects_part1.py`; one
row per flood project in `outputs/benefit/typical_projects/part1_projects.csv`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| SCALE-R resilience investment database (`SCALE-R_Database.csv`, 1,664 projects) | Project name, description, type, hazard, status, place, point location, cost, cost year | Projects reported 2003 to 2026 | Already in the repo |
| BLS CPI-U, US city average, annual | Costs moved to 2025 dollars | 1978 to 2025 | Already on disk (D-144) |
| FEMA BCA Toolkit help content (Aug 2025) | Project useful life and discount rate (for Part 2) | 2025 | Already on disk |
| FDEM, Elevate Florida program snapshot, May 2025 | Programme size, cost share, reconstruction cap | May 2025 | Read online (public PDF) |
| USACE, Miami-Dade Back Bay CSRM Chief's Report, Aug 2024 | Homes to elevate and total cost | October 2023 prices | Read online (public PDF) |
| North Bay Village Ordinance 2021-006 packet; Miami Beach commission discussion, June 2025 (news report) | Seawall cost per linear foot | 2021, 2025 | Web search results only (not read in full) |

**Estimated** means counted or calculated from the database. **Assumed**
means a rule or input we chose.

## In short

- **Real projects Module C can model are few.** Of 1,154 flood projects
  ($13.4 billion in 2025 dollars), 54 are seawalls and 2 are home
  elevations: 4.9% of projects and 3.0% of spending (estimated). Most
  flood money goes to drainage and storm water (41%), canals, levees and
  water control structures (25%) and pumps (17%), which Module C cannot
  model yet.
- **A typical seawall project** (estimated, from the 13 shoreline seawalls
  with a clean cost):
  - cost $1.76M (middle half $0.56M to $2.74M), 2025 dollars;
  - about 550 ft long (from the 5 projects that state a length);
  - crest +6.0 ft NAVD (the only 2 projects that state a crest height);
  - about $3,500 per foot (from the 3 projects with both a clean cost and
    a length).
  These fit together: $1.76M at $3,500 per foot is about 500 ft. The
  unit cost is in line with local published ranges ($1,500 to $3,800 per
  foot).
- **Home elevation: there is no "typical project" in our data.** Only one
  real project: Miami Beach, 2 repetitive-loss homes, $820,682 (about
  $410,000 per home, 2025). A second (Palmetto Bay, $390,050) is a
  repetitive-loss retrofit with no count of homes and may not be
  elevation. A median of one project is not meaningful, so Part 2B needs
  a decision on where the typical elevation project comes from (see the
  last section).
- **Cost problems:** of the 54 seawall projects, 32 are excluded from cost
  statistics: 11 programme totals over many sites or years, 20 where the
  seawall is only one part of a bigger project (parks, roads, docks,
  drainage), 3 likely duplicates (2 also in another group); none look
  like design only.

## 1. How projects were classified (assumed rules)

**Flood project:** hazard "Flooding" or "Coastal Hazards", or name or
description mentioning flooding, storm water, drainage, surge, tides, sea
level rise, seawalls or shorelines. Result: 1,154 of 1,664 projects.

**Type:** name plus description in lower case, first rule that matches:

| Type | Rule (words in name or description) | Module C |
|---|---|---|
| Seawall | "seawall", "sea wall", "bulkhead", "flood wall"; or "living shoreline", "revetment", "berm" with a crest height in ft NAVD. Not a flood wall around one building (that is floodproofing), not plans or studies | Yes |
| Building elevation | "elevat" or "rais" together with home, house, residence, private property or repetitive loss; not roads, generators, parks, tanks, lift stations, seawalls, portals or studies | Yes |
| Pumps | "pump" | No |
| Road raising | road, roadway or street with raise or elevate | No |
| Drainage and storm water | drain, storm water, exfiltration, outfall, culvert, swale, retention, injection well | No |
| Canals, levees, water control structures | canal, dredging, levee, coastal structure, S-structures, basin resiliency, C-111, detention basin | No |
| Beach, dune, breakwater | beach renourishment or erosion, dune, breakwater, nourishment, jetty, sand | No |
| Green and nature-based | mangrove, living shoreline (no crest height), wetland, green infrastructure, bioswale, trees, reefs, habitat | No |
| Shoreline repair, no wall named | shoreline, stabilisation, erosion | No |
| Building floodproofing and hardening | floodproofing, hardening, retrofit, shutters, doors, roofs, generators, lift stations, backflow valves | No |
| Buyouts, plans, sewer, roads and parks, other | as named | No |

17 rows were set by hand after reading them (for example mangrove
trimming, breakwaters, a shoreline master plan, and a flood wall around one
office: not seawalls). The full list is in the script (`NOT_SEAWALL`).

**Location usable:** Spatial_Resolution is Parcel, Corridor or
Neighborhood (the point is at or near the project). Municipality or County
points are not usable.

**Cost:** Estimated_Cost in the year it was reported, moved to 2025 dollars
with annual CPI-U (assumption: Reported_Year is the cost year; 2026 counted
as 2025).

### Example rows: seawalls (5 of 54)

| ID | Name | Place | Location | Cost 2025 | Size in text | Used for cost? |
|---|---|---|---|---|---|---|
| SCALER-0077 | Town of Bay Harbor Islands Seawall Replacement | Bay Harbor Islands | Corridor | $0.26M | 75 linear ft | Yes |
| SCALER-0613 | Resilient Shoreline Stabilization at Kristi House | Miami | Parcel | $1.54M | 550 LF sheet pile seawall and revetment | Yes |
| SCALER-0996 | Crandon Park U-Shape Seawall | County | Parcel | $3.20M | raise to +6.0 ft NAVD | Yes |
| SCALER-0494 | Morningside Park Waterfront Improvements | Miami | Corridor | $20.1M | 1,200 LF seawall, 2,250 LF baywalk | No: seawall one part |
| SCALER-0728 | Citywide Seawall Rehabilitation Program | Miami Beach | Municipality | $10.6M | none | No: programme total |

### Example rows: building elevation (all 2 found)

| ID | Name | Place | Location | Cost 2025 | Homes | Used for cost? |
|---|---|---|---|---|---|---|
| SCALER-0684 | Elevation of 2 Repetitive Loss Private Properties | Miami Beach | Municipality | $0.82M | 2 | Yes |
| SCALER-1462 | Repetitive Loss Retrofit | Palmetto Bay | Municipality | $0.39M | not given | No: number not given, retrofit may not be elevation |

Near misses, not counted as elevation: home buyout (SCALER-1082), drainage
in repetitive-loss areas (SCALER-1313, SCALER-1106), floodproofing of
apartments (SCALER-0690, SCALER-1054), and FEMA HMA statewide elevation
applications (not in our database, see below).

## 2. Flood projects Module C cannot model yet (estimated)

| Type | Projects | Spending 2025 ($M) | Share of flood spending | Median cost ($M) |
|---|---|---|---|---|
| Drainage and storm water | 760 | 5,494 | 40.9% | 0.84 |
| Canals, levees, water control structures | 33 | 3,370 | 25.1% | 4.60 |
| Pumps | 102 | 2,282 | 17.0% | 1.33 |
| Other | 35 | 563 | 4.2% | 0.90 |
| Green and nature-based | 35 | 451 | 3.4% | 2.08 |
| **Seawall (modellable)** | **54** | **398** | **3.0%** | **2.96** |
| Beach, dune, breakwater | 18 | 199 | 1.5% | 2.33 |
| Building floodproofing and hardening | 30 | 157 | 1.2% | 1.50 |
| Road raising | 10 | 127 | 0.9% | 3.65 |
| Buyouts and land acquisition | 1 | 121 | 0.9% | 120.7 |
| Roads, bridges and parks | 21 | 99 | 0.7% | 3.50 |
| Sewer and septic | 21 | 92 | 0.7% | 2.43 |
| Plans, studies and data | 21 | 60 | 0.4% | 0.35 |
| Shoreline repair, no wall named | 11 | 16 | 0.1% | 1.07 |
| **Building elevation (modellable)** | **2** | **1.2** | **0.01%** | **0.61** |
| All flood projects | 1,154 | 13,429 | 100% | |

The largest single items are SFWMD canal and coastal structure programmes
(C-111 South Dade $1.0 billion; C-6 basin $0.87 billion) and the South Dade
TransitWay ($0.46 billion, in "Other"), so spending shares are driven by a
few very large projects.

## 3. Seawalls: summary (estimated)

| | All 54 | With clean cost (22) | Shoreline only, clean cost (13) |
|---|---|---|---|
| Location usable | 47 | 21 | 12 |
| Cost, median (middle 50%), 2025 | $2.96M ($1.67M to $6.88M) | $1.92M ($0.78M to $5.23M) | **$1.76M ($0.56M to $2.74M)** |
| Length stated in text | 5 projects: median 550 ft (315 to 1,200; 75 to 1,440) | | |
| Crest stated in text | 2 projects: +6.0 ft NAVD | | |
| Cost per foot | | 3 projects: $2,800, $3,500, $12,500 | 2 projects: $2,800, $3,500 |
| Kind | 45 bay, river or ocean shoreline; 5 PortMiami bulkheads; 4 canal or lake edges | | |
| Status | 31 ongoing, 12 completed, 10 planned, 1 funded | | |

- **Where:** Miami 16, Miami-Dade County 14 (parks, marinas, PortMiami),
  Miami Beach 7, Aventura 4, Medley 3 (canal and lake edges), Bal Harbour
  2, Surfside 2, and one each in Bay Harbor Islands, Homestead, Key
  Biscayne, Miami Shores, North Bay Village and Sunny Isles Beach. Almost
  all are public waterfront: parks, marinas, street ends and the port.
- **PortMiami bulkheads** ($0.8M to $61.6M; $12,500 per foot for the one
  with a length) are heavy marine structures for port operations. They
  are kept in the counts but should not set the typical project.
- **Canal and lake edges** in Medley and the C-4 floodwall (Belen) protect
  against canal water, not the bay. Module C's surge model applies only on
  the coast; their benefits depend on canal and rainfall flooding that we
  model only in the C-8 and C-9 basins.
- **Typical seawall for Part 2B (suggested):** 550 ft, crest +6.0 ft NAVD,
  $1.76M, $3,500 per ft (range from the middle half of costs: $0.56M to
  $2.74M). The length and crest come from very few projects, so they are
  weak; the cost is better supported.

## 4. Building elevation: summary (estimated)

| | Value |
|---|---|
| Projects | 2 (1 clear) |
| Location usable | 0 (both are municipality points) |
| Cost usable | 1 |
| Homes per project | 2 (one project) |
| Cost per home, 2025 | about $410,000 (one project) |
| Where | Miami Beach; Palmetto Bay |

There is not enough here for a median project or a cost range.

## 5. Cost problems found (estimated)

| Problem | Seawall projects | What we did |
|---|---|---|
| Programme total over many sites or years (citywide programmes, "8 seawalls in Edgewater", "three seawalls") | 11 | Kept in counts, left out of cost statistics |
| Seawall is one part of a larger project (parks, baywalks, roads, docks, pump stations) | 20 | Same |
| Likely duplicate (Jose Marti Park twice; Crandon fuel dock inside the U-shape seawall; Morningside seawalls inside Morningside Park) | 3 (2 also in a group above) | Same |
| Design only | 0 | Bay Harbor Islands includes design but also replacement, so kept |
| Elevation, number of homes not given | 1 | Left out of cost per home |

In all, 32 of 54 seawall projects are left out of the cost statistics; 22
remain (21 with a usable location). No exact duplicates (same name, or
same name and cost) exist in the database.

## 6. Our unit costs against published ones

| Item | Ours (estimated) | Published | Source | Looks reasonable? |
|---|---|---|---|---|
| Seawall replacement, per linear ft | $2,800 to $3,500 (2 shoreline projects) | $1,800 to $3,800 | North Bay Village Ordinance 2021-006 packet (geotechnical report), via search result | Yes |
| | | about $1,500 rising to over $3,000 | Miami Beach staff, June 2025 commission discussion (news report) | Yes |
| Port bulkhead, per ft | $12,500 (1 project) | none found | | Plausible for heavy port structures; not typical |
| Home elevation, per home | about $410,000 (1 project, 2 homes, Miami Beach) | about $267,000 per home (rough: $400M federal at 75% for about 2,000 homes, all project types) | FDEM Elevate Florida snapshot, May 2025 | On the high side, but one project only |
| | | federal share capped at $220,000 hard costs for reconstruction | Same | |
| | | $2.66 billion for up to 2,052 home elevations plus 430 floodproofed buildings, including $0.9 billion contingency | USACE Back Bay Chief's Report (Aug 2024), pages 1 to 2 | Cannot split per home |
| | | $50,000 to $150,000 per home elsewhere in Florida; $100 to $300 per sq ft | News and contractor reports | Ours is above these |

FEMA's BCA documents on disk give project lives and discount rates (for
Part 2: 30 years for residential elevation, 7% discount rate for new
BCAs), but no unit construction costs for seawalls or elevation. We could
not read the per-foot seawall cost in Miami Beach's NIP cost estimates
(AECOM, 2024): its unit price column does not extract as text.

## 7. What Part 2 needs from you

1. **Typical elevation project.** Our database has one real project (2
   homes). Options:
   - use that one project (2 homes, $410,000 per home), labelled weak;
   - take the size and cost per home from FEMA's national HMA project
     list (OpenFEMA "Hazard Mitigation Assistance Projects", elevation
     projects in Florida). This is a new dataset, so it needs your
     approval to download;
   - assume a size and cost (for example 10 homes at about $267,000 per
     home from Elevate Florida), labelled as an assumption.
2. **Seawalls to include in Part 2A.** We suggest the 12 shoreline seawalls
   with a clean cost and a usable location, plus the 9 others with a
   usable location shown separately (5 PortMiami bulkheads, 4 canal and
   lake edges), since their benefits do not mainly come from bay surge.
3. **Seawall length and crest** come from 5 and 2 projects. Where a project
   gives no length, Part 2A would take it from the nearest shoreline
   segment at the project point, capped at cost divided by $3,500 per
   foot. Crest +6.0 ft NAVD unless stated.
