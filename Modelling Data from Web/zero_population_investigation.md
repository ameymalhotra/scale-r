# Zero- and low-population units: investigation

**Read-only.** `tract_investment.csv` and `blockgroup_investment.csv` were not
modified. No unit was dropped or filtered, and no placeholder population was
substituted anywhere.

Script: `scripts/investigate_zero_population.py` → `output/zero_population_report.txt`
(full per-unit evidence). Rebuild: `python scripts/investigate_zero_population.py > output/zero_population_report.txt`

**Identification basis.** Each unit is identified from data, in this order:
TIGER 2024 area landmarks (`AREALM`) intersecting it, TIGER point landmarks
(`POINTLM`) inside it, the census place containing its centroid, and the names
and descriptions of the projects allocated to it. Every label below carries its
evidence. Where the sources support no label, the unit is called
**unidentified** rather than guessed at.

---

## Step 1 — The zero-population units

### Tracts (9 units, 4 carrying investment)

| GEOID | ALAND (m²) | AWATER (m²) | investment | projects | what it is | basis |
|---|---|---|---|---|---|---|
| `12086981000` | 2,462,945 | 3,851,012 | **$233,405,639** | 9 | **PortMiami / Dodge Island** (+ Watson Island) | point landmark "Cruise Ship Docks Port of Miaimi", "Miami Yacht Club"; 9 project names say PortMiami / Miami SeaPort |
| `12086980400` | 7,554,780 | 19,394,069 | **$62,470,066** | 10 | **Virginia Key + Crandon Park** (north Key Biscayne) | no TIGER landmark; identified from project names — Marine Stadium, Virginia Key Rowing Center, Virginia Key Beach, Crandon Park ×4 |
| `12086980600` | 6,223,469 | 3,841,684 | **$4,200,000** | 2 | **Black Point Marina / South Dade Landfill**, Biscayne National Park edge | area landmark "Biscayne Natl Pk"; point landmark "Black Point Marina"; project names |
| `12086980800` | 6,403,671 | 49,575 | **$1,500,000** | 1 | **Miami-Opa Locka Executive Airport** (+ work release centre) | area landmark "Opa-Locka Work Release Ctr"; point landmark "Opa-Locka Executive Arprt"; project description names the airport |
| `12086980100` | 14,159,817 | 37,115,504 | $0 | 0 | **Biscayne National Park — Elliott Key / former Islandia** | area landmark "Biscayne Natl Pk"; point landmarks "Elliott Key Visitor Ctr", "Islandia" |
| `12086980200` | 5,293,068 | 108,043 | $0 | 0 | **Kendall-Tamiami Executive Airport** | point landmark "Kendall-Tamiami Executive Arprt" |
| `12086980900` | 4,978,586 | 4,148,725 | $0 | 0 | **Everglades National Park** | area landmark "Everglades Natl Pk" |
| `12086981200` | 24,435,992 | 55,343,179 | $0 | 0 | **Turkey Point Nuclear Power Plant** / Biscayne NP | area landmark "Biscayne Natl Pk"; point landmark "Turkey Point Nuclear Power Plant" |
| `12086990000` | **0** | 820,018,619 | $0 | 0 | **Open water** — Biscayne Bay / Atlantic. Zero land area | ALAND = 0; area landmark "Biscayne Natl Pk" |

**The $233M tract is PortMiami.** All 9 of its projects arrived by the
**single-unit path** (none is municipality- or county-distributed), and all 9 are
port infrastructure — shore power, bulkheads, berths, seawall, storm bollards:

| amount | scale tag | type | status | project |
|---|---|---|---|---|
| $125,000,000 | Neighborhood | Gray | Completed | Port Miami Shore Power Project |
| $60,000,000 | Neighborhood | Gray | Ongoing | North Bulkhead Improvement Project (PortMiami) |
| $19,547,316 | Neighborhood | Gray | Ongoing | Berth 10 Bulkhead Resiliency |
| $17,518,350 | Neighborhood | Gray | Ongoing | South Bulkhead Repairs (Bays 165–177) |
| $9,600,000 | Corridor | Hybrid | Completed | Construction of New Seawall - Area 2 |
| $750,000 | Neighborhood | Gray | Completed | Cruise Berth 6 Stormwater Improvements |
| $619,858 | Parcel | Gray | Completed | Concrete Panels - Miami SeaPort |
| $300,000 | Corridor | Hybrid | Completed | Watson Island Baywalk |
| $70,115 | Parcel | Gray | Completed | Storm Bollards - Miami SeaPort |

Virginia Key / Crandon Park (`12086980400`) is the same story: 10 projects,
all single-unit path, led by the $48.9M Marine Stadium Restoration.

**Every dollar in every zero-population unit arrived by the single-unit path.**
None of it is municipality- or county-distributed — population weighting gives a
zero-population unit zero weight, so the distributed paths correctly deliver
nothing there. Full per-project detail for all four is in the report file.

### Block groups (10 units, 5 carrying investment)

Nine are the single-block-group versions of the nine special-use tracts above
(identical geometry, GEOID = tract + `1`), with identical investment. The tenth
is new:

| GEOID | ALAND | AWATER | investment | projects | what it is | basis |
|---|---|---|---|---|---|---|
| `120869810001` | 2,462,945 | 3,851,012 | $233,405,639 | 9 | PortMiami / Dodge Island | as above |
| `120869804001` | 7,554,780 | 19,394,069 | $62,470,066 | 10 | Virginia Key + Crandon Park | as above |
| `120869806001` | 6,223,469 | 3,841,684 | $4,200,000 | 2 | Black Point Marina / South Dade Landfill | as above |
| `120869808001` | 6,403,671 | 49,575 | $1,500,000 | 1 | Miami-Opa Locka Executive Airport | as above |
| **`120860002043`** | 976,224 | 0 | **$400,000** | 1 | **Miami Gardens-441 Shopping Center / Miami Industrial Park** | point landmarks "Miami Gardens-441 Shopping Ctr", "Miami Industrial Park" |
| `120869801001` | 14,159,817 | 37,115,504 | $0 | 0 | Biscayne NP — Elliott Key / Islandia | as above |
| `120869802001` | 5,293,068 | 108,043 | $0 | 0 | Kendall-Tamiami Executive Airport | as above |
| `120869809001` | 4,978,586 | 4,148,725 | $0 | 0 | Everglades National Park | as above |
| `120869812001` | 24,435,992 | 55,343,179 | $0 | 0 | Turkey Point Nuclear Power Plant | as above |
| `120869900000` | **0** | 820,018,619 | $0 | 0 | Open water | as above |

**Nothing here is unidentified.** All 9 tracts and all 10 block groups resolve to
a named facility, park, airport, port, or open water.

---

## Step 2 — Is this really binary?

### Tracts: yes, almost exactly binary

**The tract population distribution has a hard gap.** Below 572 residents there
is nothing but the nine zeros and a single 28-person tract:

| GEOID | pop | investment | per capita | what it is |
|---|---|---|---|---|
| (9 tracts) | **0** | $301,575,705 total | **undefined** | the special-use units above |
| `12086981100` | **28** | $24,163,860 | **$862,995** | **Thompson Park / Pennsuco** — northwest quarry & campground area (point landmarks "Thompson Park Campground", "Pennsuco") |
| `12086007801` | 572 | $1,731,922 | $3,028 | Pinecrest Gardens area, Coral Gables |
| `12086980500` | 575 | $1,633,177 | $2,840 | **Miami International Airport** (point landmarks "Miami Air…", "Airport Industrial Ctr", "Hialeah Yards") |
| `12086007503` | 844 | $2,208,744 | $2,617 | University of Miami, Coral Gables |
| `12086006716` | 949 | $7,433,775 | $7,833 | Brickell / Financial District Station |
| `12086003708` | 953 | $837,289 | $879 | Bayside Marketplace / Miamarina |
| `12086980700` | 1,125 | $3,564,297 | $3,168 | Homestead ARB airport |
| `12086006606` | 1,181 | $1,037,606 | $879 | Miami |
| … | ≥1,254 | | | ordinary residential tracts |

Percentiles: 1% = 0, **2% = 974**, 5% = 1,688, median = 3,835.

**Where it becomes usable: immediately above 28.** Once past the 28-person
Thompson Park tract, the next-smallest tract has 572 residents and a per-capita
value of $3,028 — an ordinary number. There is no gradient of "nearly as
problematic" tracts to worry about. Counts confirm it: **9 tracts below 50, and
still only 10 below 500.**

### Block groups: no, it is a gradient

| GEOID | pop | investment | per capita | what it is |
|---|---|---|---|---|
| (10 BGs) | **0** | $301,975,705 | **undefined** | special-use units above |
| `120860067162` | **6** | $6,605,266 | **$1,100,878** | Brickell / Financial District Station |
| `120860067201` | **27** | $2,223,698 | **$82,359** | Fifth Street Station, Miami |
| `120869811001` | **28** | $24,163,860 | **$862,995** | Thompson Park / Pennsuco |
| `120860110092` | 74 | $125,815 | $1,700 | Homestead |
| `120860026004` | 77 | $67,584 | $878 | Miami |
| `120860039213` | 96 | $346,764 | $3,612 | Miami Beach |
| `120860090262` | 129 | $72,949 | $565 | Fountainebleau CDP |
| `120860001301` | 169 | $362,843 | $2,147 | Sunny Isles Beach |
| `120860037104` | 176 | $2,526,312 | $14,354 | Miami |
| … | | | | (full 30 in the report file) |

Three BGs — `120860017052`, `120860041034`, `120860062011` (pop 210, 277, 288) —
are **unidentified**: no landmark, no place, and no single-unit project to name
them.

Percentiles: 0.5% = 1.3, **1% = 181**, 2% = 330, 5% = 449, median = 1,356.
Counts: **10 below 50 is not the story — 13 below 50, 16 below 100, 25 below 250,
and 112 below 500.** The block-group distribution runs continuously down to
single digits, so no natural break exists.

*Note:* many low-population units sit at per-capita exactly **$565.50** — that is
the county-allocation floor identified in the last build ($1.549B county dollars
÷ 2,738,356 residents), not a real local value.

---

## Step 3 — What each population floor buys

### Tracts (total allocated $8,553,271,610)

| floor | units excluded | % units | dollars excluded | % dollars | remaining | **max per-capita** | p99 | p95 |
|---|---|---|---|---|---|---|---|---|
| keep all | 0 | 0.0% | $0 | 0.00% | 707 | $862,995 | $40,453 | $11,954 |
| **pop == 0** | **9** | 1.3% | **$301,575,705** | **3.53%** | 698 | **$862,995** | $40,453 | $11,954 |
| **pop < 50** | **10** | 1.4% | **$325,739,565** | **3.81%** | 697 | **$389,381** | $37,002 | $11,804 |
| pop < 100 | 10 | 1.4% | $325,739,565 | 3.81% | 697 | $389,381 | $37,002 | $11,804 |
| pop < 250 | 10 | 1.4% | $325,739,565 | 3.81% | 697 | $389,381 | $37,002 | $11,804 |
| pop < 500 | 10 | 1.4% | $325,739,565 | 3.81% | 697 | $389,381 | $37,002 | $11,804 |

**Floors of 50, 100, 250 and 500 are the same rule at tract level** — all exclude
the identical 10 units for the identical $325.7M. The only real choice is
0 vs 50, and the extra 0.28 percentage points of investment buys the removal of
the single worst per-capita value: max falls **$862,995 → $389,381**, a 55% cut,
by dropping one 28-person tract holding $24.2M.

**What remains at the top after a floor of 50 is not a population artifact.** The
new maximum, $389,381, is tract `12086001205` — population 2,413, holding the
**$927M SMART Northeast Corridor** (`flag_large_project = 1`). That is the
known footprint problem, not a small-denominator problem, and no population
floor addresses it.

### Block groups (total allocated $8,553,271,610)

| floor | units excluded | % units | dollars excluded | % dollars | remaining | **max per-capita** | p99 | p95 |
|---|---|---|---|---|---|---|---|---|
| keep all | 0 | 0.0% | $0 | 0.00% | 1,843 | $1,702,228 | $56,922 | $9,352 |
| **pop == 0** | **10** | 0.5% | **$301,975,705** | **3.53%** | 1,833 | **$1,702,228** | $56,922 | $9,352 |
| pop < 50 | 13 | 0.7% | $334,968,530 | 3.92% | 1,830 | $1,702,228 | $50,391 | $8,514 |
| pop < 100 | 16 | 0.9% | $335,508,693 | 3.92% | 1,827 | $1,702,228 | $50,537 | $8,552 |
| pop < 250 | 25 | 1.4% | $343,441,498 | 4.02% | 1,818 | $1,702,228 | $50,976 | $8,337 |
| **pop < 500** | **112** | **6.1%** | **$1,245,600,669** | **14.56%** | 1,731 | $1,386,876 | $41,112 | $8,270 |

**At block-group level no floor tames the extremes.** The maximum stays pinned at
**$1,702,228 per person** through a floor of 250, because that unit —
`120860042061` — has **383 residents**, above every floor up to 500, and holds the
**$640M Miami Beach Convention Center**. Going to a 500 floor finally removes it,
but costs **14.56% of all allocated investment** and still leaves a maximum of
$1,386,876 (BG `120860012052`, population 674, holding the $927M SMART Northeast
Corridor).

The block-group per-capita extremes are **project-concentration artifacts, not
population artifacts**. A population floor is the wrong instrument for them.

---

## Step 4 — Are these units already unusable on the predictor side?

### Tracts: yes, completely — and the break is exactly at zero

| | zero-population tracts (9) | bottom-30, non-zero (21) |
|---|---|---|
| missing from the SVI file entirely | **1 of 9** (`12086990000`, the water tract) | 0 of 21 |
| **all 24 SVI `EP_*` indicators NA** (−999) | **8 of 9** | 0 of 21 |
| ACS CRE tables with a **zero denominator** | **10 of 10, in all 9 tracts** | 0 of 21 |
| ACS tables with an NA denominator | 0 | 0 |

**Every one of the 9 zero-population tracts is already unusable as a predictor
row.** Either SVI carries no value at all (all 24 indicators are −999, the SVI
missing code) or the tract is absent from the SVI file; and all ten ACS CRE
tables report a universe total of **0**, so every rate is 0/0 — undefined, not
merely missing. Nothing can be estimated for these rows on either side of the
equation.

**And the 21 next-smallest tracts are completely clean** — zero missing SVI
indicators, zero zero-denominators, including the 28-person Thompson Park tract
and the 575-person Miami International Airport tract. The predictor-side break is
exactly at population 0, with no degradation above it.

This strengthens the case for exclusion at tract level: these rows will be
dropped by any model that touches SVI or an ACS rate, **whether or not you
address the per-capita problem**. The only question is whether they are dropped
explicitly, or silently.

### Block groups: partly — and the split matters

| | zero-population BGs (10) | bottom-30, non-zero (20) |
|---|---|---|
| missing from EJScreen entirely | **0 of 10** | 0 of 20 |
| **all 13 EJScreen environmental indicators NA** | **0 of 10** | 0 of 20 |
| EJScreen env indicators NA (range) | 0–10 of 13 (4 units have 7, one has 10, three have 1, one has 0) | 0–2 of 13 |
| ADI tables with a **zero denominator** | **8 of 12, in all 10 BGs** | 0–2 |
| ADI values **suppressed** (`-` / `**`) | **4 of 12, in all 10 BGs** | **≥1 in 20 of 20** |

**The two sides diverge at block group.** The ADI demographic components are
fully dead — 8 of 12 tables have a zero denominator and the other 4 are
suppressed, so all 12 are unusable in all 10 zero-population BGs. But **EJScreen's
environmental indicators survive**: they are place-based pollution and hazard
measures that exist whether or not anyone lives there, and not one of the 10 BGs
has them all missing.

So a zero-population block group is **usable in an exposure-only specification
and unusable in any specification containing an ADI component**.

Separately: **all 20 of the low-population non-zero BGs carry at least one
suppressed ADI value.** Small block groups are degraded well above zero, which is
consistent with the ACS block-group suppression warning already in
`DATA_PROCESSING.md` §3.

*Data note:* EJScreen's own `ACSTOTPOP` disagrees with B01003 for some units
(e.g. `120869811001`: 244 vs 28) — different ACS vintages. Reported, not reconciled.

---

## Decision needed

The numbers for each candidate rule. No recommendation picked.

### Option 1 — Exclude true zeros only (population == 0)

| | tract | block group |
|---|---|---|
| units excluded | 9 (1.3%) | 10 (0.5%) |
| investment excluded | **$301,575,705 (3.53%)** | **$301,975,705 (3.53%)** |
| units remaining | 698 | 1,833 |
| max per-capita after | **$862,995** | **$1,702,228** |
| p99 after | $40,453 | $56,922 |

Matches exactly what the predictor side already forces at tract level (all 9 are
unusable on SVI and every ACS rate). Makes the silent drop explicit and
documented. Removes PortMiami's $233M and Virginia Key's $62M from the analysis.
Does **not** fix the worst per-capita value at either grain.

### Option 2 — Population floor of 50

| | tract | block group |
|---|---|---|
| units excluded | 10 (1.4%) | 13 (0.7%) |
| investment excluded | **$325,739,565 (3.81%)** | **$334,968,530 (3.92%)** |
| max per-capita after | **$389,381** (−55%) | **$1,702,228** (unchanged) |
| p99 after | $37,002 | $50,391 |

At tract level this is the only floor that changes anything beyond Option 1: for
an extra 0.28 pp of investment it removes the 28-person Thompson Park tract and
halves the maximum. Floors of 100, 250 and 500 are **identical to this one at
tract level** — same 10 units, same $325.7M. At block group it removes three more
units and leaves the maximum untouched.

### Option 3 — Population floor of 250 or 500

| | tract (250 or 500) | BG (250) | BG (500) |
|---|---|---|---|
| units excluded | 10 (1.4%) | 25 (1.4%) | **112 (6.1%)** |
| investment excluded | $325,739,565 (3.81%) | $343,441,498 (4.02%) | **$1,245,600,669 (14.56%)** |
| max per-capita after | $389,381 | $1,702,228 | $1,386,876 |

**At tract level this is Option 2 under another name** — no additional unit is
excluded. At block group, 250 buys nothing over 50 (max unchanged), and 500 costs
**14.56% of all allocated investment** while still leaving a $1.39M-per-person
maximum. The BG extremes are large projects in small-but-real populations, not
empty units.

### Option 4 — Retain all units, restrict per-capita to a subset of specifications

Keep all 707 / 1,843 rows. Use `investment_total` (and `investment_per_area`) as
the outcome in total-dollar specifications, where zero-population units are
perfectly valid observations — PortMiami really did receive $233M — and use
`investment_per_capita` only in specifications where the population denominator
is meaningful, applying the floor there alone.

- costs **$0** of investment in the total-dollar specifications
- but at tract level the 9 zero-population rows **will still be dropped** by any
  model containing an SVI indicator or an ACS rate (all 24 SVI indicators NA,
  all 10 ACS denominators zero) — so this option only preserves them for an
  exposure-only or unconditional specification
- at block group the same rows **can** survive an EJScreen-environmental
  specification (0 of 10 have all environmental indicators missing) but not any
  ADI specification (all 12 components dead in all 10)

### Cross-cutting note

Whatever rule you choose, it does not address the largest per-capita outliers,
which are **flagged large projects in normally-populated units**: tract
`12086001205` (2,413 residents, $927M SMART Northeast Corridor, $389,381 per
person) and BG `120860042061` (383 residents, $640M Convention Center,
$1,702,228 per person). Those are the `flag_large_project` re-run, not a
population question.
