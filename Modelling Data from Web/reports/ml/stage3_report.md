# Machine learning scenario module: Stage 3 report (admin Scenario view)

**Stage 3 of prompt 22, as changed mid-stage: the Scenario dashboard lives in
the admin panel only (D-094).** Built 5 November 2026 on branch
`ml-scenario-module`. Not committed, not pushed, not deployed.

## Short summary

1. **The public site is unchanged.**
   - The public Scenario page, route and nav link I had started were undone.
   - Public source files are identical to HEAD.
   - A production build gives public chunks of the same size and content as
     before Stage 3. Only content hashes and minified names differ.
2. **The Scenario view is in the admin panel** at `/admin/viz/scenario`,
   behind the existing admin login, following the draft-visualization pattern
   (`src/admin/viz/VizPage.jsx`). It has a "Scenarios (preliminary)" link in
   the admin navigation.
3. **A logged-out visitor is sent to the admin login,** and no Scenario data
   is requested. Tests cover signed-out, non-admin and admin access.
4. **One limitation (D-095):** the data files are hashed static assets in the
   build. The login protects the view, not the files. Anyone who finds the
   hashed URLs in the admin JavaScript can fetch them. The existing gap map
   has the same exposure. The fix is a private Supabase Storage bucket for
   admins only, which needs your approval.
5. **Checks:**
   - lint passes;
   - 168 tests in 22 files pass, including 3 new access tests and a nav-link
     check;
   - the build passes;
   - the view was checked in a browser at desktop (1440 × 900) and phone
     (375 × 812) widths.

## 1. What changed on the public site, and how it was undone

| Change made earlier in Stage 3 | Undone how |
|---|---|
| `src/App.jsx`: lazy `Scenario` import, `/scenario` route, `/scenario` route metadata, full-window class for `/scenario` | `git checkout -- src/App.jsx` (back to the committed version) |
| `src/components/Navbar.jsx`: "Scenarios" link | `git checkout -- src/components/Navbar.jsx` |
| `src/pages/Scenario.jsx` (new page) | removed |
| `src/scenario/` (markup, script, styles, data) | moved to `src/admin/viz/scenario/` |

Nothing that existed before Stage 3 was touched on the public site. `git
status` shows no change in `src/` outside `src/admin/`.

**Public build comparison.** I built the pre-Stage-3 commit (HEAD) in a
temporary worktree, with the same `.env` and `.env.local`, and compared it
with the current build:

| Public file | Size before → after | Same content once hashes and minified names are blanked? |
|---|---|---|
| `index` chunk | 153,726 → 153,726 bytes | yes |
| `Team` chunk | 6,414 → 6,414 | yes |
| `TechnicalDocs` chunk | 45,518 → 45,518 | yes |
| `dataParser.core` chunk | 3,825 → 3,825 | yes |
| `index.html` | | yes |

The hashes change only because the admin chunks changed, and the public
`index` chunk embeds their filenames.

The new assets in the build:
- `scenarios-*.json` and the Scenario `tracts-*.geojson`;
- the changed admin chunks, `AdminApp` and `VizPage`.

Scenario code and data URLs appear **only** in the admin `VizPage` and
`AdminApp` chunks. The word "scenario" in the public `index` chunk is
existing About-page text and layer metadata.

## 2. The admin Scenario view

**Files**
- `src/admin/viz/scenario/scenarioMap.html`, `scenarioMap.js` and
  `scenarioMap.css`: plain markup driven by a `mount()` function that
  returns a cleanup. This is the same structure as the Exposure page and the
  admin gap map.
- `src/admin/viz/VizPage.jsx`: adds the `scenario` view.
- `src/admin/AdminApp.jsx`: adds the route `viz/scenario`, inside the
  existing `RequireAdmin`.
- `src/admin/AdminLayout.jsx`: adds the nav link.
- **Data:** `src/admin/viz/scenario/data/` (`tracts.geojson` 1.1 MB,
  `scenarios.json` 0.35 MB, `scores.json` 4 KB). It is written by
  `Modelling Data from Web/scripts/website/build_scenario_data.py` from
  `outputs/ml/dashboard/`. Nothing is hand-edited. The two large files are
  fetched only when the view mounts.

**What the view does**

| Prompt 22 requirement | Built |
|---|---|
| Choropleth with layer toggle | four layers: **gap: need vs investment** (primary, D-092), need, likely investment, need vs expected investment |
| Scenario controls | sea level rise 1, 2, 3, 6 ft; storm surge Categories 1 to 5 (Category 5 corrected); heat now, +1, +2, +3°F |
| Map and county summary update | high-need tracts with no sited project (and residents); residents exposed; tracts with a large gap; tracts expected to have a sited project; tracts beyond the training range |
| Extrapolated tracts marked | diagonal hatching, with the count and residents in the summary |
| Tract panel on click | likely investment, conformal range, need, both gaps, planned projects, top 3 drivers in plain words, jurisdiction, flags |
| Alternative interventions | "Select tracts on the map", then a project type, gives: residents; vulnerable residents; residents exposed to 3 ft sea level rise, Category 3 surge, Category 4 surge and the hottest land; high-need, no-project count before and after; average gap before and after |
| About this model | plain summary, spatial-validation scores, future check, conformal coverage, limitations |
| Preliminary label | a banner at the top |

How some of those pieces behave:
- **Heat** changes need and the gap only. The view says so, and that the
  steps are illustrative uniform warming (D-093).
- **Intervention coverage is computed as in `interventions.py`**, assuming
  the county median $580 per resident for a funded tract. It says "coverage
  only: no damages avoided are estimated".
- **The About panel's limitations are:**
  - it learns past patterns;
  - it shows coverage, not damages avoided;
  - it does not say where money should go;
  - heat steps are illustrative;
  - hatched tracts are extrapolation;
  - it is preliminary, and has no dollar predictions.
- **Likely investment** is the logistic map model's spatial out-of-fold
  probability (D-091). Under a scenario, it is shifted by the monotone
  scenario model's change.

**Checked against the pipeline**

The view's county summary matches `outputs/ml/stage2/scenario_summary.csv`
exactly:

| Scenario | High-need tracts with no sited project | Residents | Tracts with gap ≥ 0.5 | Extrapolated tracts |
|---|---|---|---|---|
| Current | 72 | 275,141 | 85 | 0 |
| 6 ft | 128 | 492,480 | 139 | 56 |
| Heat +3°F | 112 | 434,341 | 122 | |

Two small bugs were found and fixed:
- **The intervention median.** The page took the upper middle value ($586)
  instead of a true median ($580).
- **Label casing.** "limited english" now reads "limited English".

## 3. Access checks

| Check | Result |
|---|---|
| Logged-out visit to `/admin/viz/scenario` (browser) | redirected to `/admin/login`; no Scenario data requested |
| Old public URL `/scenario` | no page; the navbar has no Scenarios link |
| Test: signed out | login form shown, view not rendered |
| Test: signed in, not on the admin allowlist | "No admin access", view not rendered |
| Test: admin | view rendered |
| Admin nav test | "Scenarios (preliminary)" links to `/admin/viz/scenario` |
| Data files in the production build | **reachable by direct URL** (D-095, below) |

**D-095, the data-file limitation.**
- Vite emits the data as hashed files in `dist/assets/`. Only the admin chunk
  names them, but that chunk is itself a public file.
- So the login hides the view, not the data. The existing admin gap map's
  `tracts-*.geojson` works the same way.
- To make the data truly admin-only:
  1. Upload the three files to a **private Supabase Storage bucket**.
  2. Add a read policy that calls the existing `is_admin()`.
  3. Have the view download them with the signed-in admin's session.
- I have not done this. It creates infrastructure and uploads data, so it
  needs your go-ahead.

## 4. Screenshots

All are in `reports/ml/stage3_screenshots/`, taken in the local dev server.

Signing in to the admin panel is for you to do, so I could not screenshot
the view through the login itself. Instead I took these through a temporary
local page that mounted the same admin Scenario module without the router.
The page was deleted afterwards and never committed.

| File | Shows |
|---|---|
| `1_desktop_gap_current.jpg` | desktop, primary gap layer, current conditions |
| `2_desktop_gap_slr6ft_hatched.jpg` | desktop, 6 ft sea level rise: 128 high-need tracts with no project, 56 extrapolated tracts hatched |
| `3_desktop_likely_investment_slr6ft.jpg` | desktop, likely-investment layer under 6 ft |
| `4_phone_gap_current.jpg` | phone width (375 × 812): map above, scrollable panel below |

Phone layout: the panel takes the bottom 55% and scrolls, the map stays
visible above it, and the legend labels no longer overlap. That overlap was
fixed in this stage.

## 5. Not done, and what it needs

- **Committing.** Stage 3 is not committed, per prompt 22.
- **True data protection** (D-095), described above.
- **TabPFN** is still not run (D-082). It needs the Prior Labs license key.
