# Flood What-If in the admin panel: Part 1, plan and data export

Benefit simulator. 17 Nov 2026. Branch `admin-what-if` (created from
`benefit-simulator`). Decision D-199 in `DECISIONS.md`. Export script
`scripts/benefit/export_what_if.py`; the exported files sit in
`outputs/admin_data/what_if/`, which git ignores, so they are never
committed and never in a build.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| Module A (`module_a_depth.parquet`) | Per-building water levels for the five storms by source, ground and first-floor heights, building details | 2026 build (FEMA 2027 levels, NSI buildings) | Already in the repo |
| Module B (`module_b_eyd.parquet`) and its code | Expected yearly damage today (low, middle, high), used to check the export; the damage rules the browser must copy | 2026 build | Already in the repo |
| Module C code (`module_c_projects.py`) | The seawall "behind the wall" rule and the elevation rule | 2026 build | Already in the repo |
| USACE depth-damage curves (Stage 2, D-138) | 112 curves (occupancy, structure or contents, salt or fresh) | 2026 build | Already in the repo |
| FEMA 2027 FIRM database (`S_Tsct_Basln`, `S_Subbasins`) | Coastal shoreline for the 500 m warning; outline of the C-8 and C-9 basins | 2027 preliminary maps | Already in the repo |
| Module D coefficients and the published Miami discount (D-187) | Single-family or condo segment and just value per building; one fixed coefficient per segment for the property value scenario | 2026 tax roll | Already in the repo |
| `docs/PRIVATE_ADMIN_DATA_PLAN.md`, D-095, D-096 | How admin-only data must be stored and served | 5 Nov 2026 | Already in the repo (plan file is local, not committed) |

**Estimated** means calculated from data. **Assumed** means a rule or
input we chose. Everything in this Part is a plan or a measurement of the
export; no model result is new.

## 1. In short

- **Recommendation: run the engine in the browser.** It is a small, exact
  copy of Modules B and C in JavaScript, fed by per-building files that are
  already computed. No server is needed, and results update in well under
  a second.
- **The export is built and checked.** 386,929 of the 627,252 buildings
  are wet in at least one storm today; only those are exported. They are
  split into 438 squares of 2 km by 2 km. All of them together are 21.9 MB
  compressed (57.6 MB uncompressed).
- **A typical project loads little.** A 550 ft seawall needs 5 to 9
  squares, 0.11 to 0.63 MB (median 0.34 MB); decoding the largest set takes
  about 4 ms. The first screen needs about 0.3 MB.
- **The export loses nothing.** Rerunning the Python damage code on the
  exported files gives the same expected yearly damage: total difference
  below one part in 100 million; largest single building difference $3.68
  a year (high case), from storing numbers at single precision.
- **Privacy: the D-095 fix is still not done.** The data can be previewed
  locally now. Before any deploy you need to do the steps in section 4
  (create the private bucket and policy, with one change to allow binary
  files). Nothing may be pushed or deployed until then (D-096).
- **Two choices for you** (section 6): plain JavaScript instead of
  TypeScript, and no new map or coordinate package.

## 2. How the engine runs

### Recommended: in the browser

Module C never re-solves the flood. For a seawall it removes the coastal
water level, storm by storm, for buildings behind the wall when the storm
stays below the crest. For elevation it raises the first floor. Then it
reruns the damage curves and the trapezoid rule for those buildings only.
That is a few hundred lines of arithmetic, so it ports cleanly.

The browser copy would have four parts, each a direct copy of a Python
function:

| Browser function | Copies | What it does |
|---|---|---|
| `levels` | `module_b_eyd.levels` | Highest water level per storm, and whether it is coastal (salt curves) |
| `eventLoss` | `module_b_eyd.event_loss`, `baseline_risk.curve_key`, `flooded_share` | Depth above the first floor, curve lookup with straight-line interpolation (held flat beyond the ends, as `np.interp`), floors reached for non-house buildings |
| `eyd` | `module_b_eyd.eyd` | Losses never fall for rarer storms; trapezoid rule over the five storms; the 0.2% tail kept separate |
| `seawall`, `elevate` | `Model.seawall`, `Model.elevate` | Candidate buildings, the "behind the wall" test (the line from the building to its nearest shoreline point passes within 5 m of the wall), crest test per storm, then the three cases (low, middle, high) |

The wall is drawn in longitude and latitude; the test needs metres (UTM
zone 17N, as in Python). The standard map projection formula is about 40
lines and will be checked against `pyproj` to under 1 cm, so no new package
is needed.

Speed (estimated from the export): the largest typical seawall checks
about 10,000 buildings in 9 squares and recomputes a few hundred to a few
thousand of them, 5 storms by 3 cases. That is well under 50 ms, so the
result can update while a project is dragged.

### Alternative: a small backend

A Python service (for example FastAPI) would run the existing Module C
unchanged, so parity is automatic and no building data reaches the
browser. It would need: a host that runs Python all the time (cost, cold
starts), the 96 MB Module A table on that host, a check of the Supabase
login token on every request, its own deploy and monitoring, and its own
privacy setup. Each drag would wait for the network.

**Recommendation: the browser engine.** It needs no new service, keeps
working offline once loaded, and the parity test (section 5) protects
against the copy drifting from Python. The cost is that the per-building
files reach the admin's browser, which is acceptable because only signed-in
admins can download them (section 4).

## 3. Per-building data for the browser

**Which buildings.** Only buildings wet (water above ground) in at least
one of the five storms today: **386,929** (62% of 627,252). A building that
is never wet has zero damage before and after any seawall or elevation, so
leaving it out cannot change a result (the round-trip check below confirms
the totals).

**Fields per building** (no owner names, addresses, parcel IDs or other
personal fields):

| Group | Fields | Notes |
|---|---|---|
| Identity and place | `fd_id` (NSI building ID), position in metres within the square, longitude and latitude | Coordinates for the engine and for drawing |
| Shoreline | nearest FEMA coastal shoreline point, distance to it | For the "behind the wall" test |
| Heights | ground, first floor (ft NAVD88), whether the floor is estimated | Low case = floor + 1 ft and high case = floor - 1 ft for estimated floors, exactly as Module B; so storing the middle value and the flag gives all three |
| Building | damage curve group (occupancy), foundation type, floors (capped at 60), structure value, contents value, night-time residents | Curve ID is occupancy + foundation + salt or fresh, chosen as in Module B |
| Flags | FEMA 2027 zone VE (salt curves), has a coastal level, in the C-8 or C-9 basin | |
| Water levels, today only | for each storm (10%, 4%, 2%, 1%, 0.2%): coastal level, rainfall/canal/map level, and the highest coastal level of all coastal sources | The third is what Module C uses to decide whether the wall holds |
| Results to check | expected yearly damage low, middle, high, and the 0.2% tail of each | The browser recomputes these at load in tests and must match |
| Allowed parcel fields | 2026 just value allocated to the building, and segment (single-family, condo, other) | Public tax roll fields, used only for the property value scenario; nothing else from the parcel |

**Format.** One small binary file per 2 km square: a short header naming
the columns, then one column after another (numbers at single precision,
codes as single bytes). The browser reads a column straight into a typed
array, with no parsing. Files are gzip-compressed and unpacked in the
browser with the built-in `DecompressionStream`.

**Files and sizes (measured):**

| File | Size | When it loads |
|---|---|---|
| `manifest.json`: list of squares (box, building count, size, total damage), storm list, curve and category lists, published value coefficients | 69 KB | At start |
| `curves.json`: 112 depth-damage curves | 57 KB | At start |
| `shoreline.geojson`: FEMA coastal shoreline, simplified to 2 m | 179 KB | At start |
| `rain_basins.geojson`: C-8 and C-9 outline | 17 KB | At start |
| `overview.bin.gz`: position and middle damage of all 386,929 buildings | 2.86 MB | Only if building shading is switched on at county zoom |
| `tiles/X_Y.bin.gz`: 438 squares, all engine inputs | 21.9 MB in all; median 25 KB, 90th percentile 139 KB, largest 293 KB (5,634 buildings) | On demand, for the squares a project or the view touches |

**Load time (estimated).** The first screen is about 0.3 MB: under half a
second on a 10 Mbit/s connection. A typical seawall (550 ft, Table B
placements S1 to S10) needs 5 to 9 squares, 0.11 to 0.63 MB, so 0.1 to 0.5
seconds at 10 Mbit/s the first time, then nothing (squares are kept in
memory). Unpacking the largest set took 4.3 ms in Node; the overview took
11 ms. At county zoom the map shades the 2 km squares by total damage
(from the manifest); individual buildings are drawn from the squares in
view once zoomed in, or from the overview file if switched on.

**Check that the export is complete (estimated).** We read all 438 files
back, rebuilt the Module A table from them, and reran Module B's own
`compute`:

| Case | Total difference | Largest difference at one building |
|---|---|---|
| Low | 0.00000005% | $0.07 a year |
| Middle | 0.00000002% | $0.34 a year |
| High | 0.0000003% | $3.68 a year |

The small differences come from single precision; they are far inside the
1% parity rule.

## 4. Privacy (D-095)

**How it will work once deployed.** The files go into the private Supabase
Storage bucket `admin-data` under `what_if/`. One read policy lets only
signed-in users for whom `public.is_admin()` is true read it. The view
downloads files with the signed-in admin's session; anyone else gets
nothing. The files are never in `src/` or `public/`, never imported by
code, so no build contains them and the admin JavaScript names only the
bucket, not data. This is the plan already approved in D-095 and D-096;
nothing new is invented.

**Local preview (now).** A small Vite development-only setting serves
`Modelling Data from Web/outputs/admin_data/` at a local address while
`npm run dev` runs, and only then (it does not exist in `npm run build`).
The view uses one loader: local address in development, the private
bucket in production. The view stays behind the admin login in both.

**Status: the D-095 fix is not done.** No bucket exists, nothing is
uploaded, no policy is set. So nothing can be deployed yet, and D-096 says
nothing may be pushed or deployed until it is.

**What you need to do before this can be deployed, step by step:**

1. **Supabase dashboard, SQL editor:** run the step 1 SQL in
   `docs/PRIVATE_ADMIN_DATA_PLAN.md`, **with one change**: the What-If
   squares are binary files, so the allowed file types must include them.
   Use `array['application/json', 'application/geo+json',
   'application/octet-stream']` instead of the two JSON types. The 10 MB
   per-file limit is enough (largest file 2.9 MB).
2. **Same place:** run the two check queries from that plan and confirm the
   bucket is private and has exactly one read policy.
3. **Supabase dashboard, Authentication:** create one test user whose email
   is not in `admin_users`, for the "signed in but not admin" test. Do not
   send me its password.
4. **Tell me to go ahead with the D-095 code change** (moving the existing
   gap map and Scenario data out of `src/`, plan steps 2 to 4). The What-If
   view will use the same loader. The upload script then also uploads
   `what_if/` (about 25 MB, 443 files); it refuses to run if the bucket is
   public. It uses the service-role key already in `.env`, which never
   reaches the browser.
5. **Run test B** from the plan yourself with the test user (expect "Object
   not found"); I run tests A, C and D (logged out gets nothing; admin gets
   200; the build contains no data files).
6. **Decide step 6 of the plan** (the older Scenario commit `a32dbdf`, the
   gap map file already on public GitHub, old Vercel deployments). Only
   then push or deploy, and only when you say so.

## 5. Parity test plan

The browser engine must reproduce Python. Two levels of test, both run with
`npx vitest run`:

1. **Baseline check:** for every exported building, the browser recomputes
   expected yearly damage today (low, middle, high) and must match the
   stored Python value within 0.1% in total and within $5 at any building.
2. **Project check:** a Python script writes a test file of every Part 2
   run: inputs (wall line, crest, or the list of raised homes and height)
   and Python's answers (damage avoided low, middle, high; buildings
   protected). The browser engine reruns each and **damage avoided must
   match within 1%** (or within $1 where Python gives $0):
   - typical seawall, 10 placements, at +6 ft and +8 ft (20 runs);
   - typical FEMA elevation, 10 placements, plus the 5th and 10th home
     (30 runs), and the Elevate Florida case (10 runs);
   - real projects: the 7 shoreline seawalls that ran, at their stated or
     assumed crest and at +8 ft, the 5 port bulkheads, and the Miami Beach
     elevation (SCALER-0684);
   - the 2 coastline-scan stretches with the largest results, as extra
     seawall cases.

The test file holds results and building IDs, so it is written to the
private `outputs/admin_data/` folder, not committed. Where that folder is
missing (for example on another machine) the parity tests are skipped with
a clear message instead of failing; the engine's own unit tests (curve
lookup, trapezoid rule, the wall test on a toy example) always run. The
report for Part 2 will give the largest difference found.

## 6. Choices for you before Part 2

| Choice | Recommendation | Why |
|---|---|---|
| Language for the engine | Plain JavaScript with type comments (JSDoc) | The admin code is all JavaScript (for example `scenarioModel.js`); TypeScript would need a new compiler setup and a lint plugin, which are new packages needing your approval |
| Map and drawing | The existing `mapbox-gl` with our own small line and area drawing; our own projection formula | No new packages. A drawing plugin would be a new package needing approval |
| Where the view lives | `/admin/viz/what-if`, next to the gap map and Scenario views, behind the admin login | Same pattern as the existing views |
| Square size | 2 km | A typical seawall loads 5 to 9 small files; 1 km would mean 4 times more files for little gain |

## 7. What is estimated and what is assumed

| Item | Estimated or assumed | Note |
|---|---|---|
| Buildings exported (386,929) and file sizes | Estimated (measured) | From the export run |
| Load times | Estimated | From file sizes at 10 Mbit/s and Node unpack times; real browser times measured in Part 2 |
| Engine speed under 50 ms | Estimated | From the number of buildings a typical seawall touches; measured in Part 2 |
| Leaving out never-wet buildings changes nothing | Estimated (checked) | Round-trip check, section 3 |
| 2 km squares, single precision, gzip | Assumed (design choice) | Section 6 |
| Parity rule 1% (damage avoided), baseline 0.1% | Assumed (your rule; the baseline rule is ours) | Section 5 |
