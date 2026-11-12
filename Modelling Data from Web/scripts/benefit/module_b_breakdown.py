"""Where the Module B expected yearly damage comes from (prompt 28 Part 2 report).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_b_breakdown.py

Splits the county EYD (mid) by storm interval, by the source that sets the 1%
level, and by the 2027 flood zone. Writes outputs/benefit/spec_alignment/module_b_breakdown.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_b_eyd import EVENTS, P  # noqa: E402

A = pd.read_parquet(paths.MODULE_A_PARQUET, columns=["fd_id", "zone27", "zone27_subtype", "st_damcat"] +
                    [f"wse_{s}_p01" for s in ("coastal", "rain", "map")] + [f"wse_{s}_p002" for s in ("coastal", "rain", "map")])
B = pd.read_parquet(paths.MODULE_B_PARQUET)
L = np.maximum.accumulate(B[[f"loss_{e}_mid" for e in EVENTS]].to_numpy(), axis=1)
parts = 0.5 * (L[:, :-1] + L[:, 1:]) * (P[:-1] - P[1:])
R = {"by_interval_million": {f"{EVENTS[i]}-{EVENTS[i + 1]}": round(float(parts[:, i].sum()) / 1e6, 1) for i in range(len(EVENTS) - 1)}}
src = np.select([A.wse_coastal_p002.notna(), A.wse_rain_p002.notna(), A.wse_map_p002.notna()], ["coastal", "rain", "map"], "none")
R["by_source_million"] = pd.Series(B.eyd_mid.to_numpy()).groupby(src).sum().div(1e6).round(1).to_dict()
zc = np.where(A.zone27.isin(["A", "AE", "AH", "AO", "VE"]), "1% zone",
              np.where(A.zone27_subtype.fillna("").str.startswith("0.2 PCT"), "0.2% zone", "outside"))
R["by_zone_million"] = pd.Series(B.eyd_mid.to_numpy()).groupby(zc).sum().div(1e6).round(1).to_dict()
R["by_damage_category_million"] = pd.Series(B.eyd_mid.to_numpy()).groupby(A.st_damcat.to_numpy()).sum().div(1e6).round(1).to_dict()
R["residential_in_1pct_zone_million"] = round(float(B.eyd_mid[(zc == "1% zone") & B.residential].sum()) / 1e6, 1)
(paths.OUT_BENEFIT / "spec_alignment" / "module_b_breakdown.json").write_text(json.dumps(R, indent=2))
print(json.dumps(R, indent=1))
