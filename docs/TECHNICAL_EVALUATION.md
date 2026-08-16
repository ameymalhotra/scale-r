# Technical evaluation of the SCALE-R resilience dashboard

This document reports a reproducible technical and performance evaluation of the
SCALE-R dashboard. It is written to be lifted directly into a manuscript: the
tables are numbered to follow **Table 2 (structure of the SCALE-R resilience
projects spatial table)** and each measured value is traceable to a command in
this repository.

Two things are evaluated:

1. **Implementation characteristics** — what the tool is built from, how large it
   is, how the delivered artefact is structured, and how the implemented database
   table conforms to the specification in Table 2 (Tables 3–4).
2. **Front-end performance**, expressed in the **GTmetrix** scoring framework so
   that the locally measured values and a GTmetrix report are directly
   comparable (Tables 5–8).

---

## 1. Evaluation environment and provenance

| Item | Value |
|------|-------|
| Repository commit | `5315adc` (2026-08-15) |
| Evaluation date | 2026-08-16 |
| Build tool | Vite 7.3.1 (`npm run build`) |
| Audit engine | Lighthouse 13.4.1 (headless Chrome 151.0.7922.138) |
| Runtime | Node.js v24.10.0, macOS (Apple silicon) |
| Target under test | Local production preview (`npm run preview`, `http://localhost:4173`) |
| Aggregation | Median of 5 runs per route × form-factor configuration |
| Reproduce with | `npm run audit:perf` |

**Why a local preview.** No production URL is version-controlled in this
repository, so the audited target is the production build served locally. This
removes real network latency, CDN behaviour and TTFB from the measurement; see
§5 (threats to validity) and §6 for the procedure to obtain authoritative
GTmetrix numbers once a public URL is available.

---

## 2. Implementation characteristics

**Table 3. Implementation characteristics of the SCALE-R dashboard**

| Group | Component | Implementation | Measured value |
|-------|-----------|----------------|----------------|
| **Presentation** | Application model | Client-rendered single-page application (no server rendering) | React 19.1.1 + Vite 7.3.1 |
| | Language | JavaScript (JSX); no TypeScript configuration present | 31 non-test `.jsx` modules |
| | Routing | Client-side routing, no server routes | `react-router-dom` 7.13.1, 7 routes |
| | Styling | Hand-authored CSS plus inline styles; Tailwind is declared but has no configuration and no directives in source | 81.4 kB CSS (14.6 kB gzip) |
| | Source size | Front-end source (JS/JSX/CSS) excluding tests | 11,768 lines |
| | Largest module | Single monolithic dashboard component | `Dashboard.jsx`, 4,046 lines (34% of front-end source) |
| **Geospatial** | Map renderer | Mapbox GL JS, WebGL, initialised in an effect after mount | `mapbox-gl` 3.15.0 |
| | Map stylesheet | Loaded from CDN at a version that does not match the bundled library | CSS v2.15.0 vs library v3.15.0 |
| | Thematic layers | Census-tract choropleths (FEMA Risk Rating, resilience index) and seven critical-infrastructure overlays | 4.0 MB + 1.9 MB GeoJSON fetched on load |
| | Charts | Infrastructure-type composition of the active filter set | Recharts 3.5.1 |
| **Data** | Store of record | Supabase PostgreSQL table `projects_merged_conf1` | 1,664 project records |
| | Runtime access path | Anonymous HTTPS `fetch` of a GeoJSON object from Supabase Storage; the client never queries PostgreSQL and does not use the Supabase SDK | 147 kB GeoJSON |
| | Cache policy | Project GeoJSON requested with `cache: 'no-store'` | Revalidated on every load |
| | Coverage | Municipalities represented; aggregate reported project value | 36 municipalities; $22.43 bn |
| **Delivery** | Code splitting | None; all routes are statically imported into one chunk | 1 JS chunk, 696 modules |
| | Bundle size | Single JavaScript chunk shipped to every route | 2,351 kB raw / 668 kB gzip |
| | Static payload | Deployed `dist/`, dominated by unprocessed images copied from `public/` | 84 MB total, 51 MB images |
| | Hosting | Static hosting with SPA rewrite to `index.html` | Vercel (`vercel.json`) |
| | Secrets exposure | Mapbox public token is inlined into the client bundle at build time (expected for `pk.*` tokens, but requires URL restriction) | 1 occurrence in bundle |
| **Quality** | Automated tests | Unit tests for search and formatting, one search integration test, one accessibility sweep | 4 test files (Vitest 1.0.4) |
| | Accessibility tooling | `axe-core` / `jest-axe` executed over all routes | `npm run a11y` |
| | Continuous integration | No workflow is version-controlled | None |
| | End-to-end tests | None | — |

### 2.1 Dependency hygiene

Three declared runtime dependencies are never imported by application source and
are therefore tree-shaken out of the delivered bundle (verified by searching the
built artefact): `firebase` 12.9.0, `xlsx` 0.18.5 and `@supabase/supabase-js`
2.95.3. They do not affect delivered bytes but do enlarge the dependency
surface, the lockfile and the install footprint, and `xlsx` in particular has a
history of advisories. `tailwindcss` is likewise declared without any
configuration file or `@tailwind` directive in source.

---

## 3. Conformance of the implemented schema to Table 2

Table 2 of the manuscript specifies a ten-field spatial table with `NOT NULL`
constraints, an `estimated_cost > 0` check and three enumerated domains. The
implemented table diverges from that specification in three systematic ways:
column names are abbreviated, no declarative constraints are present, and the
enumerated domains are enforced in application code rather than in the database.

**Table 4. Conformance of the implemented table to the Table 2 specification**

| Table 2 field | Implemented column | Declared type | Constraint in database | Conformance |
|---------------|--------------------|---------------|------------------------|-------------|
| `project_name` | `project_na` | `text` | none (nullable) | Renamed, unconstrained |
| `description` | `new_15_25_` | `text` | none (nullable) | Renamed, unconstrained |
| `municipality` | `city` | `text` | none (nullable) | Renamed, unconstrained |
| `latitude` | `latitude` | `double precision` | none (nullable) | Type differs, unconstrained |
| `longitude` | `longitude` | `double precision` | none (nullable) | Type differs, unconstrained |
| `estimated_cost` | `estimated_cost` | `double precision` | no `CHECK (> 0)`; enforced in the client | Constraint relocated to UI |
| `infrastructure_type` | `infrastruc` | `text` | no enumerated domain | Domain relocated to pipeline |
| `disaster_focus` | `disaster_f` | `text` | no enumerated domain | Domain relocated to pipeline |
| `project_status` | `project_status` | `text` | no enumerated domain | Domain relocated to pipeline |
| `source_url` | `link_to_da` | `text` | none (nullable) | Renamed, unconstrained |

Source of truth for the implemented data definition:
[`scripts/js/seed-supabase-merged-conf1.js`](../scripts/js/seed-supabase-merged-conf1.js)
(lines 110–132).

Three observations follow, each material to a methods section:

1. **The abbreviations are an ESRI artefact.** Every renamed column is exactly
   ten characters (`project_na`, `infrastruc`, `disaster_f`, `link_to_da`,
   `implementa`, `new_15_25_`, `project_st`, `project_en`). This is the dBASE
   field-name limit that ArcGIS applies when writing shapefiles, and it has been
   carried through the ArcGIS → CSV → PostgreSQL path unmodified. Table 2 documents
   the intended logical model; the physical table preserves the ingest artefact.
2. **Integrity is advisory, not enforced.** Because the `NOT NULL`, `> 0` and
   enumerated constraints in Table 2 exist only in documentation and in the
   ingest/render code, a row violating them can be inserted successfully. The
   `estimated_cost > 0` rule, for example, is applied when filtering features for
   display rather than on write, so a non-conforming row is stored and then
   silently hidden.
3. **The schema is not version-controlled as a migration.** The `CREATE TABLE`
   statement exists inside a helper function that prints guidance when seeding
   fails, and `supabase/` is git-ignored. There is therefore no migration history
   establishing which schema produced a given published dataset — a reproducibility
   gap worth stating explicitly if the dataset is cited.

Beyond the ten specified fields the table carries nine additional columns
(`id`, `name`, `categories`, `project_st`, `project_en`, `status_category`,
`implementa`, `additional`, `tract_geoid`), which are pipeline and provenance
attributes rather than part of the published logical model.

---

## 4. Performance benchmark in the GTmetrix framework

### 4.1 Scoring method

GTmetrix reports a letter grade derived from two sub-scores:

```
GTmetrix Grade = 0.60 × Performance Score + 0.40 × Structure Score
```

with A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, E ≥ 50, F < 50.

The **Performance Score** is the Lighthouse performance category verbatim, a
weighted composite of Total Blocking Time (30%), Largest Contentful Paint (25%),
Cumulative Layout Shift (25%), First Contentful Paint (10%) and Speed Index
(10%). Because the weighting is identical, the Performance Scores below are
directly comparable to a GTmetrix report obtained under the same throttling.

The **Structure Score** is proprietary to GTmetrix. This evaluation reports a
transparent proxy: the unweighted mean of the front-end best-practice audits
GTmetrix surfaces on its Structure tab. Twenty such audits are considered, of
which sixteen are reported by Lighthouse for these pages and are listed
individually in Table 7. The grade column is therefore an *estimated* GTmetrix
grade, not a GTmetrix result.

### 4.2 Measured results

**Table 5. Front-end performance of the SCALE-R dashboard in the GTmetrix scoring framework**
(median of 5 runs; Lighthouse 13.4.1; production build served locally)

| Route | Form factor | Grade* | Grade % | Perf. | Struct.* | FCP | SI | LCP | TBT | CLS | Requests | Transfer |
|-------|-------------|:------:|--------:|------:|---------:|----:|---:|----:|----:|----:|---------:|---------:|
| `/about` | Desktop | D | 64.4 | 72 | 53 | 1.2 s | 1.2 s | 16.9 s | 0 ms | 0.019 | 31 | 20.51 MB |
| `/about` | Mobile | E | 57.9 | 61 | 53 | 5.6 s | 5.6 s | 104.8 s | 12 ms | 0.014 | 26 | 20.42 MB |
| `/dashboard` | Desktop | C | 73.2 | 82 | 60 | 1.1 s | 1.3 s | 2.7 s | 30 ms | 0.044 | 42 | 7.18 MB |
| `/dashboard` | Mobile | F | 45.0 | 35 | 60 | 5.1 s | 5.1 s | 15.1 s | 1,848 ms | 0.014 | 39 | 7.24 MB |

\* Estimated grade, computed as 0.60 × Performance + 0.40 × Structure, where
Structure is the documented proxy of Table 7 rather than the proprietary GTmetrix
score. Desktop uses the Lighthouse desktop preset (10 Mbps, 40 ms RTT, no CPU
throttling); mobile uses the default emulated mid-tier device (1.6 Mbps, 150 ms
RTT, 4× CPU throttling).

**Table 6. Main-thread cost and run-to-run stability**

| Configuration | Script evaluation | Total main-thread work | Performance across the 5 runs |
|---------------|------------------:|-----------------------:|-------------------------------|
| `/about` desktop | 1 ms | 171 ms | 72, 72, 72, 72, 73 |
| `/about` mobile | 106 ms | 603 ms | 62, 61, 61, 61, 62 |
| `/dashboard` desktop | 1.8 s | 2.1 s | 82, 82, 82, 82, 82 |
| `/dashboard` mobile | 6.9 s | 8.4 s | 34, 34, 35, 35, 35 |

Run-to-run spread is at most one point in every configuration, so the medians in
Table 5 are stable and differences between configurations are not measurement
noise.

### 4.3 Structure audits

**Table 7. Front-end best-practice audits underlying the Structure estimate**
(median score, 0–100; identical on desktop and mobile for every audit)

| Audit | `/about` | `/dashboard` | Observation |
|-------|---------:|-------------:|-------------|
| `image-delivery` | 0 | 100 | 10,738 KiB recoverable on `/about`; estimated LCP effect +7.3 s |
| `render-blocking` | 0 | 0 | 430 ms / 320 ms from two Google Fonts stylesheets and the Mapbox CDN stylesheet |
| `lcp-discovery` | 0 | n/a | Hero image is not discoverable in the initial HTML and carries no `fetchpriority` |
| `network-dependency-tree` | 0 | 0 | Critical path is serialised through SPA bootstrap before any data request begins |
| `unused-javascript` | 0 | 0 | 499 KiB / 349 KiB unused on first paint |
| `bootup-time` | 100 | 0 | 1 ms vs 1.8 s of script evaluation (desktop) |
| `mainthread-work-breakdown` | 100 | 0 | 171 ms vs 2.1 s of main-thread work (desktop) |
| `total-byte-weight` | 50 | 50 | 21,002 KiB / 7,357 KiB transferred |
| `unsized-images` | 50 | 100 | Intrinsic dimensions absent on `/about` imagery |
| `cache-insight` | 50 | 100 | 25 KiB recoverable through cache headers |
| `font-display` | 0 | 100 | 30 ms of blocked text rendering |
| `unused-css-rules` | 100 | 50 | 14 KiB unused on `/dashboard` |
| `document-latency` | 100 | 100 | Pass |
| `duplicated-javascript` | 100 | 100 | Pass |
| `legacy-javascript` | 100 | 100 | Pass |
| `redirects` | 100 | 100 | Pass |

The two routes fail for different reasons, which matters for how the tool is
optimised: `/about` is **transfer-bound** (unoptimised imagery), while
`/dashboard` is **CPU-bound** (script evaluation and GeoJSON parsing). Because the
Structure audits are almost entirely byte- and markup-based, their scores are
identical across form factors; the divergence between desktop and mobile in
Table 5 is therefore attributable entirely to the Performance component.

### 4.4 Defects and remediation

**Table 8. Identified defects, evidence and expected effect of remediation**

| # | Finding | Evidence | Expected effect of remediation |
|---|---------|----------|--------------------------------|
| 1 | `/about` transfers 20.5 MB, dominated by a 3200×2097 / 8.9 MB JPEG and a 2532×1898 / 8.5 MB PNG displayed at ≤1350 px | `image-delivery`: 10,738 KiB recoverable | Roughly a 90% reduction in page weight and the largest single LCP gain available. Requires AVIF/WebP encoding, responsive `srcset` at display resolution, and `fetchpriority="high"` on the hero |
| 2 | Every route downloads one 2,351 kB chunk containing Mapbox GL and Recharts, including routes with no map or chart | `unused-javascript`: 499 KiB unused on `/about`; build emits 1 chunk from 696 modules | Route-level `React.lazy` plus `manualChunks` removes roughly 500 KiB from non-map routes and shortens the critical path |
| 3 | `/dashboard` parses ~6.0 MB of GeoJSON (`femaindex` 4.0 MB, `miami_cities` 1.9 MB) on the main thread at startup | Script evaluation 1.8 s desktop / 6.9 s mobile; TBT 30 ms desktop but 1,848 ms mobile; an exploratory unthrottled run could not measure TBT at all (`NO_TTI_CPU_IDLE_PERIOD` — the main thread never reaches a 5 s idle window) | TBT carries 30% of the Performance Score and is what drives the mobile grade to F, so this is the largest single lever on the dashboard. Options: serve tract geometry as vector tiles/PMTiles, simplify geometry, or move parsing to a Web Worker |
| 4 | Three render-blocking stylesheets are fetched from third-party origins; the Mapbox stylesheet is pinned to v2.15.0 while the bundled library is v3.15.0 | `render-blocking`: 320–430 ms | Self-hosting the fonts and importing the Mapbox stylesheet from the npm package improves FCP and simultaneously eliminates the version skew |
| 5 | Project GeoJSON is requested with `cache: 'no-store'`, preventing any CDN or browser caching | `cache-insight`: 50 | A short `max-age` with revalidation preserves freshness while making repeat visits substantially cheaper |
| 6 | **Runtime defect.** `Dashboard.jsx:2117` calls `LngLatBounds.set()`, which is not part of the Mapbox GL API, so the census-tract layer throws `TypeError` on every load | `errors-in-console` fails; `Error loading census tract data: TypeError: ca.set is not a function` | The exception is caught by the surrounding `try/catch`, so it fails silently: the tract layers are added (that call precedes the fault) but the auto-zoom to tract extent and the diagnostic summary never execute. Replacing the call with `bounds.extend(coord)` restores intended behaviour |
| 7 | No meta description and no `robots.txt` | SEO category 82–83 on both routes | Improves discoverability, relevant for a publicly cited research instrument |
| 8 | Accessibility violations: insufficient colour contrast (`/about`), touch targets below minimum size (mobile `/dashboard`), accessible name not matching visible label (`/dashboard`) | Accessibility category 96 | Restores the category to 100 and addresses WCAG 2.2 conformance for a public-sector audience |
| 9 | No continuous integration, no published source maps, and three declared-but-unimported runtime dependencies | `valid-source-maps` fails; §2.1 | Guards the test and accessibility suites against regression and reduces the dependency surface |

### 4.5 Interpretation

Three findings carry the evaluation.

**The two routes fail for opposite reasons, and each needs a different fix.**
`/about` transfers 20.5 MB and is limited by bytes on the wire: its LCP of 16.9 s
on desktop and 104.8 s on emulated mobile is almost entirely the 8.9 MB hero
image, and its main thread is essentially idle (171 ms). `/dashboard` transfers
one third as much (7.2 MB) yet is limited by computation: 1.8 s of script
evaluation on desktop and 6.9 s on mobile, from parsing ~6.0 MB of GeoJSON on the
main thread. Optimising images would not help the dashboard, and code splitting
would not help the landing page.

**Form factor, not route, determines whether the tool is usable.** The same code
scores 72 and 82 on desktop but 61 and 35 on emulated mobile — a Performance loss
of 11 points on `/about` and 47 points on `/dashboard`, which moves the dashboard
from grade C to grade F. The mechanism is the 4× CPU throttling applied in the
mobile profile, which converts the dashboard's 30 ms desktop TBT into 1,848 ms.
For a public-facing municipal resilience tool, where mobile
access is likely to be common among the community audiences described in the
engagement material, this is the most consequential result in the evaluation.

**Cumulative Layout Shift and interactivity are already sound.** CLS is between
0.014 and 0.044 across all four configurations, comfortably inside the 0.1
"good" threshold, and desktop TBT never exceeds 30 ms. The deficits are
concentrated in payload and startup cost — categories that respond to build
configuration and asset preparation rather than to architectural change. Items 1
and 2 of Table 8 alone address roughly 11 MB of recoverable transfer, and neither
requires modifying application logic.

---

## 5. Threats to validity

| Threat | Effect on reported values |
|--------|---------------------------|
| Target served from `localhost` | Transfer time is near zero, so page weight is under-penalised. A 20 MB page scores far better locally than it would over a real network. Values are therefore an optimistic bound. |
| Simulated throttling | Lighthouse's desktop preset simulates 10 Mbps / 40 ms RTT; GTmetrix defaults to an *unthrottled* real Chrome from Vancouver. Configurations must be matched before comparing absolute numbers. |
| Structure Score is a proxy | GTmetrix's Structure formula is undisclosed; the proxy in Table 7 approximates it but will not reproduce it exactly. |
| Lighthouse version skew | GTmetrix tracks a specific Lighthouse release. Scoring curves change between releases, so cross-tool comparisons should state both versions. |
| Single environment | One machine, one browser build, median of 5. Absolute timings are machine-specific; relative findings are stable. |
| Cold-cache only | Every run is a first visit. Repeat-visit performance, where the 668 kB bundle is cached, is not characterised. |

---

## 6. Obtaining authoritative GTmetrix numbers

The estimated grades above should be replaced with a real GTmetrix report before
publication. Two prerequisites: a publicly reachable deployment URL, and a
GTmetrix API key (Account → API).

```bash
# Deploy first, then benchmark the public URL.
GTMETRIX_API_KEY=<key> node scripts/js/gtmetrix-benchmark.mjs \
  --url=https://<deployment-host> \
  --routes=/about,/dashboard
```

This writes `.lighthouse/gtmetrix-summary.{json,md}` containing the official
`gtmetrix_grade`, `performance_score` and `structure_score` alongside the same
metrics reported in Table 5, plus a link to each hosted report for the
manuscript's supplementary material.

To compare like with like, run the local audit under GTmetrix's default
analysis options (desktop Chrome, unthrottled) or, preferably, pin both tools to
a throttled profile:

```bash
# GTmetrix: Broadband (5/1 Mbps, 30 ms)
GTMETRIX_API_KEY=<key> node scripts/js/gtmetrix-benchmark.mjs \
  --url=https://<deployment-host> --throttle=5000/1000/30
```

---

## 7. Reproducing this evaluation

```bash
npm ci
npm run build          # produces dist/ and reports chunk sizes
npm run preview &      # serves the production build on :4173
npm run audit:perf     # median-of-5 Lighthouse audit, writes .lighthouse/summary.{json,md}
npm test -- --run      # unit and integration tests
npm run a11y           # axe-core sweep across all routes
```

`npm run audit:perf` accepts overrides, for example
`node scripts/js/audit-performance.mjs --url=https://example.org --runs=3 --profiles=desktop`.
Raw Lighthouse JSON for the first run of each configuration is retained in
`.lighthouse/` when `--keep` is passed.
