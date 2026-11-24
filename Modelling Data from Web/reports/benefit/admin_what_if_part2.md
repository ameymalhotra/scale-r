# Flood What-If in the admin panel: Part 2, the view

Benefit simulator. 17 Nov 2026. Branch `admin-what-if`. Decisions D-199 and
D-200 in `DECISIONS.md`. Plan and data: `admin_what_if_part1.md`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| Per-building export (D-199): Modules A and B, FEMA 2027 water levels, USACE damage curves, NSI buildings | Every number the view shows | 2026 build | `scripts/benefit/export_what_if.py`, private folder `outputs/admin_data/what_if/` |
| Python Module C (`module_c_projects.py`) | The answers the browser must match | 2026 build | `scripts/benefit/what_if_parity_fixture.py` |
| Part 1 and FEMA HMA data (D-196, D-197) | Default costs: $3,500 per foot of seawall, $254,000 per home | 2025 dollars | Already in the repo |
| FEMA BCA guidance (D-197) | 7% discount rate, project life 50 years (seawall) and 30 years (elevation) | 2025 | Already in the repo |
| Module D and Fu and Nijman (2021) (D-187) | Property value: "about zero" from local sales, and the published-discount scenario | 2026 tax roll | Already in the repo |

**Estimated** means calculated from data. **Assumed** means a rule or
input we chose. The view labels each number the same way.

## 1. In short

- **The view is built.** At `/admin/viz/what-if`, behind the admin login,
  you can draw a seawall or raise homes (draw an area, or click homes) and
  see damage avoided (low, middle, high), buildings and residents protected,
  cost, and benefit per dollar at 7% and 3%. Results update while a project
  is dragged. An Examples button loads three Part 2 projects.
- **It matches Python.** Rerunning all 87 Part 2 projects in the browser
  engine gives damage avoided within **0.0002%** of Python (the rule was 1%).
  Damage today for all 386,929 exported buildings matches too.
- **It is fast.** On this MacBook (Apple silicon, 10 cores, Chrome), a
  typical seawall recomputes in a median **3.6 ms** during a drag (9.6 ms
  including the map redraw, 16 ms at worst); raising homes takes under
  **1 ms** (under 10 ms with the redraw). A laptop several times slower
  would still update well within a frame.
- **Checks:** all 192 tests pass (8 new), the build works and contains no
  data files, and the new code passes lint (one older lint error in
  `vite.config.js` was already there).
- **Three things you should decide** (section 6): the seawall "behind the
  wall" rule overcredits buildings far from the wall; the published-discount
  property value scenario can give implausibly large changes; and where the
  model can answer questions at all.
- **Nothing is pushed or deployed.** The data stays private (D-095); see
  section 5 for the older exposures.

## 2. What is in the view

| Part | What it does |
|---|---|
| Map | Buildings shaded by expected yearly damage today (switch on or off); 2 km squares when zoomed out; faint hollow dots for buildings the model expects water never to reach; FEMA coastal shoreline; C-8 and C-9 basins outlined and labelled "rainfall flooding modelled here only" |
| Seawall tool | Click points along the shore, double-click or Finish. Crest slider 4 to 12 ft NAVD88 (default 6). Same "behind the wall" rule as Module C. Warnings: wall under 200 ft; line more than 500 m from FEMA's coastal shoreline; most protected buildings far from the wall (new, section 6) |
| Raise homes tool | Draw an area and raise the N most damaged single-family homes there (with the count of flooding homes in the area and a "Raise all" button), or click homes one by one. Height slider 1 to 6 ft (default 3) |
| Moving projects | Drag a wall or an area; results update as it moves |
| Examples | Typical seawall in Miami Beach, typical elevation in Miami Shores (high damage) and in Brownsville (low damage), numbered on the map and listed with their benefit per dollar |
| Results | Damage avoided a year (low, middle, high); buildings protected; estimated residents (Census-based, usually 2 to 4 a home); cost (editable, default from typical unit costs, labelled assumed); benefit per dollar at 7% (main) and 3% (sensitivity), green at $1 or more, grey below; project life; property value shown separately; time taken |
| Building details | Click a dot: building type, size, estimated residents, damage today, first-floor height above ground (estimated or from records), and the damage with the selected project |
| Read this with | Tidal flooding not included (seawalls understated); rainfall only in C-8 and C-9 (inland understated); floor heights mostly estimated |
| About | One paragraph on how the model works and its limits |

The default seawall cost is length x $3,500 per foot, as asked. For the
typical 550 ft wall that is $1.93M, a little above the Part 2 typical cost
($1.76M), so the Miami Beach example shows $1.44 per dollar here and $1.58
in Part 2. Same damage avoided, different cost.

## 3. Parity with Python (estimated)

| Check | Result | Rule |
|---|---|---|
| Damage today, all 386,929 buildings, low, middle, high | Totals within 0.1%; largest single building $3.68 a year (single precision) | 0.1% in total, $5 a building |
| 87 Part 2 projects: typical seawall at +6 and +8 ft (20), coastline-scan best 2, typical elevation home 1, 5 and 10 (30), Elevate Florida 10 homes (10), real shoreline seawalls and port bulkheads at their crest and +8 ft (24), Miami Beach elevation (1) | Largest difference in damage avoided **0.0002%**; 69 of the 87 have damage avoided above $0, and every $0 in Python is $0 in the browser | 1% |

Test files: `src/admin/viz/whatif/whatIfParity.test.js` (needs the private
data; skipped elsewhere) and `whatIfEngine.test.js` (always runs: curve
lookup, trapezoid rule, map projection against pyproj to under 1 cm,
curve choice, benefit per dollar).

## 4. Speed during a drag (estimated, measured)

Measured on this MacBook in Chrome by moving each project 40 small steps,
as a drag does. "With redraw" adds the map update.

| Project | Engine, median | Engine, worst | With redraw, median | With redraw, worst |
|---|---|---|---|---|
| Typical seawall, Miami Beach (550 ft) | 3.6 ms | 7.7 ms | 9.6 ms | 16.3 ms |
| Raise 1 home in an area (Miami Shores) | under 0.1 ms | 0.1 ms | 0.6 ms | 9.5 ms |
| Raise 10 homes in an area | under 0.1 ms | 1 ms | 0.6 ms | 1.6 ms |

The longest single run in the parity test was the 17,600 ft PortMiami
bulkhead (64 ms), far longer than any wall someone would draw. The first
placement in a new part of the county also downloads 0.1 to 0.6 MB of data
(Part 1).

## 5. The older data exposures (D-095 plan, step 6), in plain language

The D-095 fix keeps the admin data in a private store from now on. It does
not undo copies that already left this computer. There are three:

| What | Who could see it | What I recommend |
|---|---|---|
| **Gap map data** (`src/admin/viz/data/tracts.geojson`): census-tract summaries of investment, flood and heat risk and social vulnerability, all built from public sources; no personal data | Anyone on the internet. It is in the public GitHub repository (`main` and `admin-live-tool`) and its history | **Accept it.** It holds no personal or private data, only tract summaries of public data. Removing it from history means rewriting every branch and asking everyone to re-download the repository, which is disruptive for little gain. Say if you or the professor consider the draft numbers sensitive, and I will plan the history clean-up. |
| **The same gap map data in old website deployments**: every earlier Vercel deployment keeps its own copy | Anyone who has, or finds, an old deployment address | **Delete old preview deployments** in the Vercel dashboard if you want them gone; otherwise accept, as it is the same public-derived data as above. |
| **Scenario data** (`src/admin/viz/scenario/data/`, commit `a32dbdf`, 5 Nov) | **Nobody yet.** It is only on this computer. But it is in the history of `ml-scenario-module`, `benefit-simulator` and `admin-what-if`, so pushing any of them would publish it | **Before any push**, let me rewrite that commit without the data (it is local, so nobody else is affected). This needs your OK because it changes history on three local branches. |

The What-If data was never committed and never deployed: it lives only in
the git-ignored `outputs/admin_data/` folder, and in production it would be
served only from the private bucket.

## 6. Decisions for you

1. **The seawall "behind the wall" rule overcredits buildings far from
   the wall.** For the Miami Beach example, the 119 protected buildings are
   a median 688 m from a 168 m wall, and all share 7 nearest-shoreline
   points on it. FEMA's shoreline skips Indian Creek and the canals, so
   homes beside the creek are "credited" to a wall at the canal mouth. The
   Part 2 best seawall result is therefore probably overstated. The view now
   warns when half the protected buildings are more than 300 m away.
   Options: a distance limit (simple; the distance is a judgement call), or
   a waterway-aware rule (better; needs a public canal and creek layer).
   Nothing changed in the method yet.
2. **The published-discount property value scenario can be implausibly
   large.** It applies a 3% flood-zone discount per unit of damage rate and
   stretches it to homes with far more damage than a typical flood-zone
   home. For 6 heavily flooded homes in North Miami it gives +$1.38M, about
   33% of their value. The view now shows the change as a share of value
   and warns above 5%. A cap (for example at the published 3%) would need
   your decision, as it changes Module D's scenario.
3. **Where the model can answer.** See section 7.

## 7. Where the model can answer, and the gaps

Share of the county's expected yearly damage today ($550M a year, middle),
by the water source that sets the level in the 1% storm (estimated):

| Water source | Damaged buildings | Share of damage | What the view can test |
|---|---|---|---|
| Coastal (FEMA 2027 coastal study) | 192,378 | 76% | Raising homes, anywhere. Seawalls only within 2 km of FEMA's coastal shoreline: 25,721 damaged buildings, 14% of all damage |
| Rainfall and canals (FEMA XP-SWMM model, C-8 and C-9 basins only) | 23,383 | 10% | Raising homes. Seawalls do not stop rain |
| FEMA map flood elevation only (no storm-by-storm levels) | 9,388 | 1% | Raising homes, roughly |
| Flooded only in the rarest storm (0.2%) | 139,477 | 13% | Raising homes |

The warning "This line is X km from FEMA's coastal shoreline" means the
wall is on a river, canal or lake that FEMA's coastal study does not map
(Miami River, Little River, inland canals, lakes). The model decides who a
wall protects by the line from each building to that shoreline, so a wall
far from it protects nobody in the model, or the wrong buildings. Gaps and
how to fill them:

| Gap | How to fill it | Effort |
|---|---|---|
| Seawalls on tidal rivers and canals (and the overcrediting in item 6.1) | Add a public waterway layer (USGS National Hydrography Dataset, or Miami-Dade's canal layer, with South Florida Water Management District salinity structures). Treat tidal canals below the salinity structure as coastal water, and use each building's nearest water, bay or canal, for the "behind the wall" test | About 1 to 2 weeks; needs your approval to download the layers |
| Rainfall and canal flooding outside C-8 and C-9 | Storm-by-storm rainfall levels for the other basins: Miami-Dade County Stormwater Master Plan models, or South Florida Water Management District flood protection studies, where available | Depends on what the county and the District will share; weeks |
| Tidal and king-tide flooding | NOAA high tide flooding thresholds and flood days (Virginia Key), and NOAA Sea Level Rise Viewer layers (D-198) | 2 days to a week |
| Drainage, pumps and green projects | Need the rainfall levels above first | After the rainfall gap |

## 8. Screenshots

Kept in the private folder `outputs/admin_data/what_if_screens/`, because
they show the admin data (D-095), and sent to you directly:
`1_desktop_empty_map.jpg`, `2_desktop_seawall_placed.jpg`,
`3_desktop_elevation_placed.jpg`, `4_desktop_examples.jpg`,
`5_phone_empty_map.jpg`, `6_phone_examples.jpg`.

They were taken on the local development server. The admin login could not
be used for them (my browser tab was not signed in, and I do not enter
passwords), so the view was opened from the browser console with the same
page, styles and code as the `/admin/viz/what-if` route.

## 9. What is estimated and what is assumed

| Item | Estimated or assumed | Note |
|---|---|---|
| Damage before and after, buildings protected | Estimated | Same model as Python (section 3) |
| Residents | Estimated | National Structure Inventory, from the Census; whole numbers, not related to house size |
| Default costs | Assumed | $3,500 per foot (Part 1), $254,000 per home (FEMA South Florida median) |
| 7% discount, 50 and 30 year lives | Assumed (FEMA standard) | |
| 3% discount | Assumed (sensitivity) | |
| Seawall upkeep 1% of cost a year | Assumed | |
| Property value, local sales | Estimated | About zero, no reliable effect (Module D) |
| Property value, published discount | Assumed | Upper bound for heavily flooded homes (section 6) |
| Speed | Estimated (measured) | One laptop |
