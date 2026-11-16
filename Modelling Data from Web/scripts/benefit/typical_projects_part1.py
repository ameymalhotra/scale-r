"""Typical funded flood projects in Miami-Dade, from the SCALE-R investment database (prompt 29 Part 1, D-196).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/typical_projects_part1.py

1. Flood projects: Hazard_Focus "Flooding" or "Coastal Hazards", or any project whose name or description
   mentions flooding, storm water, drainage, surge, tides, sea level rise, seawalls or shorelines.
2. Each flood project gets one type, from its name and description (lower case), first rule that matches:
   - seawall (Module C can model it): sea wall, seawall, bulkhead, flood wall; or a living shoreline,
     revetment or berm with a crest height in feet; not a flood wall around a single building (that is
     building floodproofing) and not a plan or study;
   - building elevation (Module C can model it): elevation or raising of homes, houses, residences or
     private properties (not roads, generators, parks, tanks);
   - other types, not modellable yet: pumps; drainage and storm water; road raising; canals and
     dredging; green and nature-based (living shorelines without a crest height, mangroves, bioswales,
     wetlands); beach, dune and breakwater; building floodproofing and hardening; buyouts and land
     acquisition; plans, studies and data; other.
3. Location: usable when Spatial_Resolution is Parcel, Corridor or Neighborhood (a point near the
   project), not Municipality or County.
4. Cost problems (flags, decided by reading each seawall and elevation row): programme totals over many
   sites or years; seawall only one part of a larger project (roads, parks, docks, drainage); design or
   planning only; likely duplicates (same site, overlapping scope). Flagged rows stay in the counts but
   not in the cost and unit cost statistics.
5. Costs in 2025 dollars with annual CPI-U (D-144), taking Reported_Year as the cost year (assumption;
   2026 counted as 2025).
6. Size from the text: length in linear feet ("75 linear feet", "1,440 LF", "315 feet of ... bulkhead");
   crest height ("+6.0 feet NAVD"); homes per elevation project ("two ... properties").
Writes outputs/benefit/typical_projects/part1_projects.csv (one row per flood project, with type, flags,
size, cost in 2025 dollars) and part1_summary.json.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "typical_projects"
FLOOD_WORDS = r"flood|storm ?water|drain|surge|tidal|tide|sea.level|sea ?wall|bulkhead|shoreline|inundat"
# name spellings in the database for the same place
JUR = {"MiamiBeach": "Miami Beach", "North MiamiBeach": "North Miami Beach", "MiamiGardens": "Miami Gardens",
       "MiamiShores": "Miami Shores"}
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

RULES = [
    ("pumps", r"pump"),
    ("road raising", r"(road|roadway|street)s? (rais|elevat)|(rais|elevat)\w* (of )?(the )?(road|roadway|street)"),
    ("drainage and storm water", r"drain|storm ?water|exfiltration|outfall|culvert|swale|retention|injection well"),
    ("canals, levees and water control structures", r"canal|dredg|levee|coastal structure|\bs-\d|basin resiliency|c-111|detention basin"),
    ("beach, dune and breakwater", r"beach (renourish|nourish|erosion|restor)|\bdune|breakwater|nourish|jetty|\bsand\b"),
    ("green and nature-based", r"mangrove|living shoreline|wetland|green infra|bioswale|rain garden|tree|native plant|oyster|reef|habitat"),
    ("shoreline repair, no wall named", r"shoreline|stabiliz|erosion"),
    ("building floodproofing and hardening", r"flood ?proof|harden|retrofit|shutter|door|roof|generator|lift station|backflow|valve|energy center|electrical"),
    ("buyouts and land acquisition", r"acquisition|buyout|purchas"),
    ("plans, studies and data", r"study|plan\b|master plan|assessment|model|portal|monitor|sensor|data|vulnerab"),
    ("sewer and septic", r"sewer|septic"),
    ("roads, bridges and parks", r"road|street|bridge|causeway|park|parking|marina"),
]

# Cost flags from reading each seawall and elevation row (rule 4). Keys: Project_ID.
PROGRAMME = {"SCALER-0014": "five-year citywide repair programme", "SCALER-0037": "citywide ARPA programme",
             "SCALER-0728": "citywide rehabilitation programme", "SCALER-0738": "citywide repairs and living shorelines",
             "SCALER-1606": "all town right-of-way seawalls", "SCALER-0530": "eight seawalls in Edgewater",
             "SCALER-0532": "three locations", "SCALER-0509": "three seawalls, Morningside",
             "SCALER-0510": "three seawalls, South Grove", "SCALER-0761": "North Beach seawalls (programme)",
             "SCALER-0707": "Middle Beach seawalls and living shorelines (programme)",
             "SCALER-1462": "repetitive loss properties on the FEMA list (number not given)"}
PART = {"SCALER-0059": "linear park, jetty and cutwalk", "SCALER-0061": "dock, kayak launch and park",
        "SCALER-0056": "seawall and dock", "SCALER-0494": "1,200 LF seawall plus 2,250 LF baywalk",
        "SCALER-0514": "baywalk and retention", "SCALER-0517": "boat ramp, parking, baywalks, drainage",
        "SCALER-0522": "kayak ramp", "SCALER-0566": "park retention and drainage, study and design",
        "SCALER-0568": "roadway, baywalk, storm water", "SCALER-0590": "riverwalk and kayak launch",
        "SCALER-0599": "33,000 sq ft baywalk and drainage", "SCALER-0618": "baywalk and park drainage",
        "SCALER-0734": "floating dock and ADA access", "SCALER-0857": "park improvements",
        "SCALER-0895": "two pump stations", "SCALER-0972": "trails, parking, park facilities",
        "SCALER-1010": "marina piers and floating docks", "SCALER-1358": "over-water connector and plazas",
        "SCALER-1578": "park, docks, mangrove mitigation", "SCALER-1598": "drainage and road reconstruction",
        "SCALER-0420": "seawalls and shoreline enhancement island-wide"}
DUPLICATE = {"SCALER-0590": "same park and seawall as SCALER-0566 (Jose Marti Park)",
             "SCALER-0995": "fuel dock seawall also in SCALER-0996 (Crandon Park)",
             "SCALER-0509": "Morningside seawalls overlap SCALER-0494 (Morningside Park)"}
NOT_SEAWALL = {"SCALER-1020": "flood walls around one office building (dry floodproofing)",
               "SCALER-0170": "mangrove trimming", "SCALER-1404": "shoreline master plan update",
               "SCALER-0687": "mangrove planter design", "SCALER-0676": "baywalk only",
               "SCALER-0600": "greenway", "SCALER-0700": "erosion control research programme",
               "SCALER-0595": "park redesign with green infrastructure and drainage wells",
               "SCALER-0616": "canal dredging", "SCALER-0624": "breakwaters and armoring",
               "SCALER-0758": "breakwater", "SCALER-0409": "offshore breakwater",
               "SCALER-1577": "beach erosion and breakwater", "SCALER-1014": "beach nourishment",
               "SCALER-0404": "beach renourishment", "SCALER-0423": "dune vegetation",
               "SCALER-1472": "shoreline stabilisation (no wall, no crest)"}
PORT = {"SCALER-0886", "SCALER-0887", "SCALER-0971", "SCALER-1182", "SCALER-1269"}
CANAL = {"SCALER-0440", "SCALER-0454", "SCALER-1099", "SCALER-0456", "SCALER-0459"}


def length_ft(t):
    m = re.search(r"([\d,]{2,})\s*(?:linear feet|linear foot|lf\b|feet of|foot|feet)", t)
    if m and "sq" not in t[m.end():m.end() + 6]:
        v = float(m.group(1).replace(",", ""))
        return v if 20 <= v <= 50000 else np.nan
    return np.nan


def crest_ft(t):
    m = re.search(r"\+\s*([\d.]+)\s*(?:feet|ft)\s*navd", t)
    return float(m.group(1)) if m else np.nan


def homes(t):
    m = re.search(r"(\d+|" + "|".join(WORDS) + r")\s+(?:repetitive[- ]loss\s+)?(?:private\s+)?(?:residential\s+)?"
                  r"(?:homes|houses|properties|residences|structures)", t)
    if not m:
        return np.nan
    g = m.group(1)
    return float(WORDS.get(g, g))


def classify(r):
    t, pid = r.text, r.Project_ID
    if pid in NOT_SEAWALL:
        pass
    elif re.search(r"sea ?wall|bulkhead|flood ?wall", t) or (
            re.search(r"living shoreline|revetment|berm", t) and not np.isnan(crest_ft(t))):
        return "seawall"
    if re.search(r"portal|certificate|study", t):
        pass
    elif re.search(r"elevat|rais", t) and re.search(r"home|house|residen|private propert|repetitive", t) and not re.search(
            r"road|generator|park|tank|golf|picnic|seawall|lift station", t):
        return "building elevation"
    if pid == "SCALER-1462":
        return "building elevation"
    for name, rx in RULES:
        if re.search(rx, t):
            return name
    return "other"


def stats(x):
    x = pd.Series(x).dropna()
    if not len(x):
        return None
    return {"n": int(len(x)), "median": round(float(x.median())), "p25": round(float(x.quantile(.25))),
            "p75": round(float(x.quantile(.75))), "min": round(float(x.min())), "max": round(float(x.max()))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(paths.PROJECT_CSV)
    d["Jurisdiction"] = d.Jurisdiction.replace(JUR)
    d["text"] = (d.Project_Name.fillna("") + " | " + d.Project_Description.fillna("")).str.lower()
    flood = d.Hazard_Focus.isin(["Flooding", "Coastal Hazards"]) | d.text.str.contains(FLOOD_WORDS)
    f = d[flood].copy()
    f["type"] = f.apply(classify, axis=1)
    f["modellable"] = f.type.isin(["seawall", "building elevation"])
    cpi = pd.read_csv(paths.CPI_ANNUAL_CSV).set_index("year").factor_to_2025
    f["cost_2025"] = f.Estimated_Cost * f.Reported_Year.clip(upper=2025).map(cpi)
    f["location_usable"] = f.Spatial_Resolution.isin(["Parcel", "Corridor", "Neighborhood"])
    f["flag"] = ""
    for k, lab in [(PROGRAMME, "programme total"), (PART, "seawall is one part"), (DUPLICATE, "likely duplicate")]:
        m = f.Project_ID.isin(k)
        f.loc[m, "flag"] = f.loc[m].apply(lambda r: (r.flag + "; " if r.flag else "") + f"{lab}: {k[r.Project_ID]}", axis=1)
    f.loc[f.modellable & f.text.str.contains(r"\bdesign\b") & ~f.text.str.contains(r"construct|replace|build|install"),
          "flag"] += "design only"
    f["subtype"] = np.where(f.Project_ID.isin(PORT), "port bulkhead",
                            np.where(f.Project_ID.isin(CANAL), "canal or lake edge", ""))
    f["cost_usable"] = f.modellable & f.flag.eq("")
    f["length_ft"] = f.text.map(length_ft)
    f["crest_ft_navd"] = f.text.map(crest_ft)
    f["homes"] = np.where(f.type.eq("building elevation"), f.text.map(homes), np.nan)
    f["cost_per_ft"] = np.where(f.cost_usable, f.cost_2025 / f.length_ft, np.nan)
    f["cost_per_home"] = np.where(f.cost_usable, f.cost_2025 / f.homes, np.nan)
    cols = ["Project_ID", "Project_Name", "Jurisdiction", "Hazard_Focus", "Project_Status", "Spatial_Resolution",
            "Reported_Year", "Estimated_Cost", "cost_2025", "type", "subtype", "modellable", "location_usable",
            "cost_usable", "flag", "length_ft", "crest_ft_navd", "homes", "cost_per_ft", "cost_per_home",
            "Latitude", "Longitude", "Project_Description", "Data_Source"]
    f[cols].to_csv(OUT / "part1_projects.csv", index=False)

    R = {"database_projects": int(len(d)), "flood_projects": int(len(f)),
         "flood_spending_2025_million": round(float(f.cost_2025.sum()) / 1e6, 1), "by_type": {}}
    tot = f.cost_2025.sum()
    for ty, g in f.groupby("type"):
        R["by_type"][ty] = {"projects": int(len(g)), "spending_2025_million": round(float(g.cost_2025.sum()) / 1e6, 1),
                            "share_of_spending": round(float(g.cost_2025.sum() / tot), 3),
                            "median_cost_2025": round(float(g.cost_2025.median()))}
    big = f.cost_2025.nlargest(5)
    R["largest_flood_projects"] = f.loc[big.index, ["Project_ID", "Project_Name", "type", "cost_2025"]].to_dict("records")
    for ty in ["seawall", "building elevation"]:
        g = f[f.type == ty]
        u = g[g.cost_usable]
        R[ty] = {"projects": int(len(g)), "location_usable": int(g.location_usable.sum()),
                 "cost_usable": int(g.cost_usable.sum()),
                 "location_and_cost_usable": int((g.location_usable & g.cost_usable).sum()),
                 "flags": {k: int(g.flag.str.contains(k).sum()) for k in
                           ["programme total", "seawall is one part", "likely duplicate", "design only"]},
                 "subtypes": g.subtype.replace("", "shoreline (bay, river, ocean)").value_counts().to_dict(),
                 "cost_2025_usable": stats(u.cost_2025), "cost_2025_all": stats(g.cost_2025),
                 "length_ft": stats(g.length_ft), "crest_ft_navd": stats(g.crest_ft_navd), "homes": stats(g.homes),
                 "cost_per_ft": stats(u.cost_per_ft), "cost_per_home": stats(u.cost_per_home),
                 "status": g.Project_Status.value_counts().to_dict(),
                 "jurisdictions": g.Jurisdiction.value_counts().to_dict(),
                 "cost_year": g.Reported_Year.value_counts().sort_index().to_dict()}
    (OUT / "part1_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps({k: v for k, v in R.items() if k != "largest_flood_projects"}, indent=1, default=str))


if __name__ == "__main__":
    main()
