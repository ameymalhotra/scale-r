# Investment outcome tables — column dictionary & build notes

Built by `scripts/build_investment_tables.py`; diagnostics in
`scripts/report_investment_tables.py` (full output: `output/investment_tables_report.txt`).
Rebuild: `python scripts/build_investment_tables.py && python scripts/report_investment_tables.py`

| file | rows |
|---|---|
| `tract_investment.csv` | 707 (every Miami-Dade tract, zeros kept) |
| `blockgroup_investment.csv` | 1,843 (every Miami-Dade block group, zeros kept) |

**Scope:** projects with `Project_Status` in Completed / Funded / Ongoing.
`Planned` excluded. 1,405 of 1,664 projects, **$8,553,271,609.50**. No risk
layer. No scale tag reclassified.

## Columns

| column | definition |
|---|---|
| `GEOID` | string. 11 digits (tract) / 12 (block group), prefix `12086` |
| `population` | ACS 2024 5-yr total population. Tract: B01001_001E. BG: B01003_001E |
| `investment_total` | allocated dollars (see allocation rules) |
| `investment_per_capita` | `investment_total / population`. **Empty where population = 0** — undefined, not zeroed |
| `investment_per_area` | `investment_total / ALAND`, i.e. **dollars per square metre** of TIGER land area. ×1e6 for $/km². Empty where ALAND = 0 |
| `investment_any` | 1 if `investment_total > 0` |
| `investment_type_{blue,gray,green,hybrid}` | split by `Infrastructure_Type`. Sums to `investment_total` |
| `investment_scale_{parcel,neighborhood,corridor,municipality,county}` | split by allocation path, so each dollar is auditable back to its rule. Sums to `investment_total` |
| `project_count` | distinct projects contributing any dollars. **Inflated by design**: the 31 county-scale projects reach every populated unit, so this is ~34 everywhere |
| `project_count_single_unit` | *(addition beyond the requested columns)* distinct projects landing whole on this unit — the county/municipality distribution netted out |
| `flag_large_project` | 1 if the unit receives any dollars from the 5 SMART Program corridors or 19 SFWMD basin projects. Known footprint misrepresentation; modeled normally, flagged for re-runs |

## Allocation rules (professor's classification, used as given)

- **Parcel / Neighborhood / Corridor** → whole amount to the single unit containing
  the project point. Join keys reused from `output/project_join_keys.csv`.
- **Municipality** → population-weighted across all units in that municipality.
- **County** → population-weighted across all 707 tracts / 1,843 block groups.

Population weighting applies only to the two multi-unit paths.

**Municipality assignment:** each unit is assigned to the incorporated place
(TIGER 2024 `CLASSFP` = `C*`) containing its centroid, computed in EPSG:6346.
CDPs (`U1`/`U2` — Kendall, Westchester, Tamiami, …) are **not** municipalities;
they fold into **Unincorporated Miami-Dade**, treated as its own jurisdiction.

| grain | units in a municipality | Unincorporated Miami-Dade | distinct jurisdictions |
|---|---|---|---|
| tract | 392 | **315** | 33 |
| block group | 1,054 | **789** | 35 |

**Centroid fallback (tract grain only):** El Portal and Bay Harbor Islands
contain no tract centroid. For a municipality with zero centroid-assigned units,
recipients fall back to units whose geometry *intersects* it, still
population-weighted — 12 projects, $18,679,837, 7 tracts. Without this those
dollars have nowhere to land and reconciliation fails. All other 32
municipalities use centroid assignment. Block groups need no fallback.

**Jurisdiction name normalization:** the project file runs some names together
(`MiamiBeach`, `North MiamiBeach`, `MiamiGardens`, `MiamiShores`, `MiamiSprings`,
`MiamiLakes`) and spells two differently from TIGER (`Opa-Locka` → `Opa-locka`,
`Indian Creek Village` → `Indian Creek`). Names only — nothing reclassified.
All 34 municipality names resolve.

**County-tagged projects with a municipal jurisdiction** (Cutler Bay, Miami
Beach, Sunny Isles Beach, and 2 SFWMD) are distributed county-wide, because the
scale tag drives allocation. Used as given, not corrected.

## Audit trail

`output/allocation_audit_tract.csv` / `_bg.csv` — one row per
(project × receiving unit) with `amount`, `scale`, and `path`. Every project's
rows sum to its `Estimated_Cost`; both ledgers reconcile to $8,553,271,609.50.
