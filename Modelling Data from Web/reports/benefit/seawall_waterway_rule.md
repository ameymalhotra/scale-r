# Seawall waterway rule: before and after (D-202)

Benefit simulator. 17 Nov 2026. Branch `admin-what-if`. Scripts
`scripts/benefit/build_water_distance.py` and `module_c_projects.py`; tables
in `outputs/benefit/typical_projects/D202_*.csv` and `D202_summary.json`
(before: `outputs/benefit/typical_projects/before_D202/`).

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| FEMA 2027 FIRM database, water lines (S_Wtr_Ln) | Canals, creeks, rivers, inner waterways and connected lakes | 2027 preliminary maps | Already on disk (the same database as the flood zones); nothing downloaded |
| FEMA 2027 FIRM database, water areas (S_Wtr_Ar) | Checked, not used: almost all ponds and golf lakes; it misses Indian Creek, the Miami and Little Rivers, the Biscayne Canal and the Coral Gables Waterway | 2027 | Already on disk |
| Prompt 29 Part 2 runs (D-197, D-198) | The seawall placements and real walls rerun here | 2026 build | Already in the repo |

**Estimated** means calculated from data. **Assumed** means a rule we
chose. The waterway rule and the 1 km cap are assumed rules (the user's).

## The rule

A building behind a seawall counts as protected only if:
1. its nearest open water is the coastal shoreline the wall stands on (FEMA's
   transect baseline), not a canal, creek, river, inner waterway or connected
   lake; and
2. it is within 1 km of the wall (safety cap).

Water lines left out: the open water the coastal study itself faces (Atlantic
Ocean, Biscayne Bay, Florida Bay, Card, Little Card, Barnes and Long Sound,
Manatee Bay, Government Cut), any water line within 30 m of the coastal
shoreline (the same edge of water drawn twice), and closed outlines that touch
no other water (isolated ponds, which do not connect to the sea).

**Coverage check (estimated).** The water lines include the waterways that
matter: in Miami Beach, Indian Creek, Indian Creek Lake, the Biscayne, Normandy
and Bay Harbor waterways and Surprise Lake; in Aventura, the Intracoastal
Waterway, the Oleta River, Dumbfoundling Bay, Little Lake Maule and the
Highland Oaks Canal; elsewhere, the Miami River, Little River (C-7), Biscayne
Canal (C-8), Coral Gables Canal (C-3) and Snake Creek (C-9). Gaps: small
private canals may be missing or unnamed; water lines show where water is,
not whether a canal is tidal (salinity structures are not used), which
matters little within 2 km of the coast; ponds are left out by design.

**How much each part removes (estimated).** Over all 443 shoreline stretches
at +6 and +8 ft, 41,808 building checks were "behind the wall" under the old
rule. The waterway rule removes 22,640 (54%); the 1 km cap on its own removes
1,250 more (3%).

## Before and after

### Typical seawall, 10 placements (550 ft, $1.76M; benefit per dollar at 7%, middle)

| ID | Place | Band | Damage avoided a year at +6 ft, before | After | Buildings protected, before | After | Benefit per $1 at +6 ft, before | After | At +8 ft, before | After |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | Miami Shores | high | $888 | $0 | 2 | 0 | 0.01 | 0.00 | 2.58 | 0.08 |
| S2 | Miami Beach | high | $228,964 | $0 | 119 | 0 | 1.58 | 0.00 | 8.68 | 0.08 |
| S3 | Unincorporated Miami-Dade | high | $3,175 | $0 | 3 | 0 | 0.02 | 0.00 | 6.50 | 0.02 |
| S4 | Miami | high | $82,820 | $0 | 27 | 0 | 0.57 | 0.00 | 3.10 | 0.00 |
| S5 | North Miami | middle | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.15 | 0.00 |
| S6 | Key Biscayne | middle | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.01 | 0.01 |
| S7 | Fisher Island | middle | $5,804 | $5,804 | 4 | 4 | 0.04 | 0.04 | 0.20 | 0.20 |
| S8 | Sunny Isles Beach | low | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| S9 | North Bay Village | low | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| S10 | Coral Gables | low | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 |

At 3% (sensitivity), the +8 ft results for the high-damage places fall from
$4.35 to $14.64 per dollar to $0.00 to $0.14.

### All 443 shoreline stretches, typical wall at +6 ft

| | Before | After |
|---|---|---|
| Stretches that avoid any loss | 161 | 109 |
| Benefit per $1 of at least 0.50 (7%) | 9 | 1 |
| Benefit per $1 of at least 1 (7%) | 6 (all Miami Beach) | 0 |
| Benefit per $1 of at least 1 (3%, sensitivity) | 8 | 1 |
| Best benefit per $1 (7%) | 2.71 | 0.87 |
| Total losses avoided, all stretches | $3.05M a year | $0.80M a year |

### Real walls that were run (7 shoreline, 5 port bulkheads)

| Project | Wall | Damage avoided a year, before | After | Protected, before | After | Benefit per $1, before | After | +8 ft, before | After |
|---|---|---|---|---|---|---|---|---|---|
| SCALER-1333 | Pelican Harbor Marina | $15,175 | $4,152 | 22 | 7 | 0.07 | 0.02 | 1.86 | 0.36 |
| SCALER-0077 | Bay Harbor Islands (75 ft, short, flagged) | $3,175 | $0 | 3 | 0 | 0.15 | 0.00 | 43.44 | 0.00 |
| SCALER-0388 | Homestead Bayfront Marina | $1,252 | $0 | 1 | 0 | 0.01 | 0.00 | 0.01 | 0.00 |
| SCALER-0994 | Crandon Park Marina | $198 | $198 | 1 | 1 | 0.00 | 0.00 | 0.04 | 0.04 |
| SCALER-0614, 0988, 0996 | Vizcaya, Deering Estate, Crandon U-shape | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 5 port bulkheads | PortMiami | $0 | $0 | 0 | 0 | 0.00 | 0.00 | 0.00 to 0.02 | unchanged |

The 5 shoreline walls of at least 200 ft together: $16,600 a year before,
$4,400 after; $0.013 per dollar before, $0.003 after.

Home elevation results do not change.

## What it means for the Part 2 report

- The Part 2 seawall results came almost entirely from buildings that a
  canal or creek next to them would flood anyway. With the waterway rule,
  **no typical +6 ft seawall placement or shoreline stretch returns $1 per
  dollar** at 7%, and at +8 ft the best of the four high-damage placements
  returns $0.08.
- The Part 2 statements to update: "a typical seawall rarely pays back"
  becomes "a typical seawall does not pay back anywhere in our model";
  remove "at +8 ft the same walls return $2.58 to $8.68"; the coastline scan
  numbers as in the table above; Pelican Harbor protects 7 buildings, not 22.
- The reasons it may still understate seawalls stay: tidal and king-tide
  flooding are not in the model, and a canal or creek next to a home is
  often protected by its own seawalls too, which the model does not know
  about. In practice the wall along the bay is usually one part of a
  neighbourhood's defences, not a defence on its own.
