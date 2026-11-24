# Investment by surface heat tercile, by project hazard focus

**Descriptive only.** A follow-up to `exposure_vs_investment.md` section 3.4,
which found that the hottest third of tracts received $1,669 per resident and
the coolest third $4,968. This report asks whether money labelled as
Extreme Heat follows the same pattern, and whether a few large projects
drive it. No file was modified; the existing tables were read and summarized.
Run 5 November 2026.

- Script: `scripts/04_exposure/heat_tercile_investment.py`.
- Outputs: `outputs/exposure/heat_terciles/`.
- Log: `outputs/exposure/heat_terciles/heat_terciles_log.txt`.
- Decision: D-069.

## Summary

- **Extreme Heat money avoids the hottest tracts.**
  - The coolest third received **$240 per resident** from projects labelled
    Extreme Heat; the hottest third received **$36**.
  - Projects sited in the tract itself: $231 against $26.
  - Projects sited per 100,000 residents: 2.97 against 0.90.
- **A few projects dominate heat dollars.**
  - The Underline Phase 3 is 54% of the coolest third's sited heat money.
  - The Underline Phase 2 is 48% of the middle third's.
  - One park redesign (SCALER-0595) is 78% of the hottest third's.
- **The gap holds without them.**
  - Dropping those three projects, or the five largest heat projects in the
    county, leaves the coolest third with 4.5 to 7.4 times the hottest
    third's heat dollars per resident.
  - On the project count, which no single project can dominate, the coolest
    third has about 3 times the rate.
- **Most of the overall gap is not flood money.**
  - Flood-related money is about the same in the middle and hottest thirds:
    $1,352 and $1,399 per resident.
  - The biggest single contributor is Infrastructure Failure: $2,052 in the
    coolest third against $165 in the hottest.

These are associations between groups of tracts, not evidence about why
money went where it did.

## Sources

| Input | What it is | Where |
|---|---|---|
| Projects | SCALE-R project database, 1,664 projects; `Hazard_Focus` and `Estimated_Cost` used | `data/raw/projects/SCALE-R_Database.csv` |
| Allocation ledger | one row per project and receiving tract; 1,405 Completed, Funded and Ongoing projects, $8,553,271,610 | `data/processed/investment/allocation_audit_tract.csv` |
| Tract frame | 698 tracts with residents (ACS 2020 to 2024) | `data/processed/analysis/tract_analysis.csv` |
| Surface heat | population-weighted mean Landsat surface temperature, summers 2021 to 2024 | `data/processed/exposure/exposure_tract.csv` (`heat_lst_popwt_mean_f`) |

## Method

**Terciles.** The 698 tracts are split into three equal-count groups by
population-weighted mean surface temperature, exactly as in Stage B.

| Tercile | Tracts | Residents | Temperature range |
|---|---|---|---|
| Coolest | 233 | 875,409 | 97.2 to 108.9°F |
| Middle | 232 | 977,978 | 108.9 to 112.0°F |
| Hottest | 233 | 884,969 | 112.0 to 122.3°F |

**The one tract under 100 residents** (Pennsuco, 28 people) is in the
coolest third. It is kept, as in Stage B. Without it, the coolest third's
pooled figure moves from $4,968 to $4,940.

**Dollars** come from the allocation ledger, so the allocation rules are the
existing ones:
- parcel, neighborhood and corridor projects go whole to the tract
  containing them;
- municipality and county projects are spread by population.

The 698 tracts hold $8,251,695,905. The other $301,575,705 went to the nine
tracts with no residents. **"Sited"** means the parcel, neighborhood and
corridor projects, which no allocation rule spread.

**Hazard focus.** Every project has exactly one `Hazard_Focus` value.
"Flood-related" combines Flooding, Coastal Hazards, and Storms & Hurricanes.

**Three versions of dollars per resident:**
- **pooled:** total dollars in the tercile divided by its total residents.
  This is the headline figure.
- **mean:** the mean of tract dollars per resident.
- **median:** the median of tract dollars per resident.

## Dollars per resident by hazard focus

### All projects

| Hazard focus | Pooled: coolest | middle | hottest | Mean: coolest | middle | hottest | Median: coolest | middle | hottest |
|---|---|---|---|---|---|---|---|---|---|
| **All projects** | **$4,968** | $2,481 | **$1,669** | $9,414 | $3,345 | $1,785 | $1,621 | $754 | $720 |
| Flooding | $1,269 | $961 | $1,086 | $4,523 | $1,055 | $1,171 | $498 | $448 | $392 |
| Storms & Hurricanes | $230 | $131 | $56 | $242 | $151 | $65 | $5 | $2 | $2 |
| Coastal Hazards | $715 | $260 | $256 | $828 | $282 | $274 | $175 | $163 | $163 |
| Infrastructure Failure | $2,052 | $857 | $165 | $2,977 | $1,558 | $162 | $9 | $9 | $9 |
| Multi-Hazard | $462 | $221 | $69 | $561 | $213 | $70 | $31 | $19 | $19 |
| **Extreme Heat** | **$240** | $51 | **$36** | $283 | $86 | $44 | $5 | $5 | $5 |
| Flood-related | $2,215 | $1,352 | $1,399 | $5,593 | $1,488 | $1,510 | $922 | $705 | $566 |

### Sited projects only

| Hazard focus | Pooled: coolest | middle | hottest | Mean: coolest | middle | hottest | Median: coolest | middle | hottest |
|---|---|---|---|---|---|---|---|---|---|
| **All projects** | **$3,732** | $1,719 | **$895** | $8,133 | $2,540 | $1,000 | $289 | $49 | $0 |
| Flooding | $690 | $531 | $669 | $3,959 | $620 | $751 | $0 | $0 | $0 |
| Storms & Hurricanes | $142 | $114 | $42 | $135 | $132 | $50 | $0 | $0 | $0 |
| Coastal Hazards | $450 | $48 | $49 | $544 | $54 | $61 | $0 | $0 | $0 |
| Infrastructure Failure | $1,855 | $810 | $76 | $2,770 | $1,495 | $70 | $0 | $0 | $0 |
| Multi-Hazard | $365 | $173 | $33 | $452 | $162 | $34 | $0 | $0 | $0 |
| **Extreme Heat** | **$231** | $42 | **$26** | $273 | $77 | $34 | $0 | $0 | $0 |
| Flood-related | $1,281 | $693 | $760 | $4,638 | $806 | $863 | $76 | $32 | $0 |

**How to read the three versions**
- **The mean is pulled up by a few tracts with very large amounts per
  resident.** The coolest third's mean of $9,414 falls to $5,735 without the
  28-person Pennsuco tract, which has $862,995 per resident.
- **The median shows the typical tract.** For sited money, the median tract
  in the hottest third received nothing.
- Pooled, mean and median all rank the terciles the same way for all
  projects and for Extreme Heat.

## Extreme Heat projects by tercile

| | Coolest | Middle | Hottest |
|---|---|---|---|
| Heat projects putting any dollars in the tercile | 40 | 26 | 17 |
| Heat projects sited in the tercile | 26 | 11 | 8 |
| Sited heat projects per 100,000 residents | 2.97 | 1.12 | 0.90 |
| Sited heat dollars | $201,887,952 | $41,544,936 | $23,211,688 |

Notes on the counts:
- The sited counts add up to 45, which is every sited Extreme Heat project.
- The "any dollars" counts include the 2 county-wide heat projects, which
  reach every tercile, and municipal projects spread across a city's tracts.
  So they add up to more than the 65 heat projects.

## Caveat: a few projects dominate the heat dollars

Largest sited Extreme Heat projects in each tercile:

| Tercile | Project | Scale | Dollars | Share of the tercile's sited heat dollars |
|---|---|---|---|---|
| Coolest | SCALER-1094 The Underline Phase 3 | Corridor | $109,000,000 | **54%** |
| Coolest | SCALER-0055 Bal Harbour Waterfront Park (Phase A) | Parcel | $22,529,092 | 11% |
| Coolest | SCALER-0982 The Underline Phase 1 | Corridor | $16,524,133 | 8% |
| Middle | SCALER-1093 The Underline Phase 2 | Corridor | $20,115,110 | **48%** |
| Middle | SCALER-0793 Rolling Oaks Regional Park Redevelopment | Parcel | $6,348,263 | 15% |
| Middle | SCALER-0602 Miami River Greenway Curtis Park East | Corridor | $5,757,370 | 14% |
| Hottest | SCALER-0595 Jose Martin Park Adaptive Re-Design (City of Miami) | Parcel | $18,000,000 | **78%** |
| Hottest | SCALER-0783 Dr. Lester B. Brown Park Shade and Heat-Mitigation Improvements | Parcel | $1,730,358 | 7% |
| Hottest | SCALER-0607 Riverside Park Renovations and Enhancements | Parcel | $995,000 | 4% |

Two more cautions about these projects:
- **The Underline is a linear park along the Metrorail line.** Under the
  corridor rule, each phase's whole cost goes to the single tract containing
  its point. In reality it runs through many tracts. This is the known
  corridor footprint issue (D-003, D-006).
- **`Hazard_Focus` is one label per project.** A project labelled Extreme
  Heat, such as a park, may serve other purposes too.

## Sensitivity: does the heat gap hold without the dominant projects?

- **S1** drops The Underline Phases 2 and 3 and SCALER-0595. These are also
  the single largest sited heat project in each tercile.
- **S2** drops the five largest Extreme Heat projects in the county: The
  Underline Phases 1, 2 and 3, Bal Harbour Waterfront Park, and SCALER-0595.

**Extreme Heat dollars per resident (pooled)**

| Run | Measure | Coolest | Middle | Hottest | Coolest ÷ hottest |
|---|---|---|---|---|---|
| Baseline | all heat projects | $239.76 | $50.79 | $35.99 | 6.7 |
| Baseline | sited heat projects | $230.62 | $42.48 | $26.23 | 8.8 |
| S1 | all heat projects | $115.25 | $30.22 | $15.65 | 7.4 |
| S1 | sited heat projects | $106.11 | $21.91 | $5.89 | 18.0 |
| S2 | all heat projects | $70.64 | $30.22 | $15.65 | 4.5 |
| S2 | sited heat projects | $61.50 | $21.91 | $5.89 | 10.4 |

**All projects, dollars per resident (pooled)**

| Run | Measure | Coolest | Middle | Hottest | Coolest ÷ hottest |
|---|---|---|---|---|---|
| Baseline | all projects | $4,967.93 | $2,480.54 | $1,668.77 | 2.98 |
| S1 | all projects | $4,843.42 | $2,459.97 | $1,648.43 | 2.94 |
| S2 | all projects | $4,798.81 | $2,459.97 | $1,648.43 | 2.91 |

**Sited Extreme Heat projects per 100,000 residents**

| Run | Coolest | Middle | Hottest |
|---|---|---|---|
| Baseline | 2.97 | 1.12 | 0.90 |
| S1 | 2.86 | 1.02 | 0.79 |
| S2 | 2.63 | 1.02 | 0.79 |

**The gap holds.**
- Without the dominant projects, the coolest third still has 4.5 to 7.4
  times the hottest third's heat dollars per resident, and 10 to 18 times on
  sited heat projects.
- Dropping SCALER-0595 hurts the hottest third most: it was most of that
  tercile's sited heat money, leaving $5.89 per resident.
- The project count, which no single large project can dominate, gives the
  same order: 2.6 to 3.0 sited heat projects per 100,000 residents in the
  coolest third, 0.8 to 0.9 in the hottest.
- The overall all-projects gap barely moves (2.9 to 3.0 times), because heat
  projects are a small part of total investment.

## Limitations

- **Surface heat is not air heat.** It is ground and roof temperature on
  clear summer mornings (`population_exposure.md` section 5, item 3).
- **One label per project.** `Hazard_Focus` is a single category. A project
  can address heat without being labelled Extreme Heat, and the reverse.
- **Few heat projects.** There are 65 Extreme Heat projects, 45 of them
  sited, so tercile figures move a lot with single projects. The count-based
  measure and the sensitivity runs address this, but the numbers remain
  small.
- **The corridor rule puts a whole linear project in one tract.** That
  matters for The Underline.
- **Areas, not people.** These figures describe groups of tracts. Spatial
  dependence applies as in Stage B, and no significance test was run.
- **Association, not cause.** Cooler tracts differ from hotter ones in many
  ways, including coast, wealth and municipal budgets.
