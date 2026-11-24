"""The inland rainfall gap: who has no rainfall flooding for frequent storms (prompt 28 follow-up, D-175).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/inland_gap.py

Rainfall and canal levels for the 10%, 4% and 2% storms exist only in the
C-8 and C-9 basins. Everywhere else those storms count as zero rainfall
damage, a known undercount. Groups:
- map only: inside a 1% zone, only the 1% level exists (frequent storms zero);
- coastal only: frequent storms counted for coastal flooding, rainfall missing;
- no flood source: outside every mapped zone and source (nothing counted).
Also the share of NFIP claims in tracts that lie mostly outside C-8 and C-9.
Writes outputs/benefit/spec_alignment/inland_gap.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from baseline_risk import observed_claims  # noqa: E402


def main():
    A = pd.read_parquet(paths.MODULE_A_PARQUET, columns=["fd_id", "GEOID_tract", "residents_night", "zone27", "basin",
                                                          "wse_coastal_p002", "wse_rain_p002", "wse_map_p01", "st_damcat",
                                                          "val_struct"])
    z = pd.read_parquet(paths.FEMA2027_ZONES_PARQUET, columns=["subbasin_node", "zone27_subtype"])
    in_c89 = z.subbasin_node.notna().to_numpy()
    coastal = A.wse_coastal_p002.notna().to_numpy()
    mapo = A.wse_map_p01.notna().to_numpy()
    sfha = A.zone27.isin(["A", "AE", "AH", "AO", "VE"]).to_numpy()
    grp = np.select([in_c89, mapo, coastal], ["C-8 and C-9 (rainfall counted)", "map only (1% level only)",
                                             "coastal only (rainfall missing)"], "no flood source")
    res = A.residents_night.fillna(0).to_numpy()
    g = pd.DataFrame({"g": grp, "res": res, "sfha": sfha, "v": A.val_struct.to_numpy()})
    R = {"by_group": {k: {"buildings": int(len(d)), "residents": int(round(d.res.sum())),
                          "buildings_in_1pct_zone": int(d.sfha.sum()),
                          "structure_value_billion": round(float(d.v.sum()) / 1e9, 1)} for k, d in g.groupby("g")}}
    out = ~in_c89
    R["outside_c8_c9"] = {"buildings": int(out.sum()), "residents": int(round(res[out].sum())),
                          "buildings_in_1pct_zone": int((out & sfha).sum()),
                          "residents_in_1pct_zone": int(round(res[out & sfha].sum()))}
    # claims in tracts mostly outside C-8 and C-9
    share = pd.Series(in_c89).groupby(A.GEOID_tract.to_numpy()).mean()
    obs, _ = observed_claims()
    c = obs.claims_weighted_annual_2025
    c = c[c.index.isin(share.index)]
    R["claims_share_tracts_mostly_outside_c8_c9"] = round(float(c[share.reindex(c.index) < 0.5].sum() / c.sum()), 3)
    R["claims_share_tracts_mostly_inside_c8_c9"] = round(float(c[share.reindex(c.index) >= 0.5].sum() / c.sum()), 3)
    (paths.OUT_BENEFIT / "spec_alignment" / "inland_gap.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
