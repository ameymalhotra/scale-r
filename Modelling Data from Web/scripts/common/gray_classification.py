"""Sub-classification of Gray-tagged projects, derived from Project_Name +
Project_Description text. No column in SCALE-R_Database.csv distinguishes
project sub-types directly (checked: Project_ID, Project_Name, Latitude,
Longitude, Jurisdiction, Data_Source, Infrastructure_Type, Hazard_Focus,
Project_Description, Project_Status, Estimated_Cost, Reported_Year,
Spatial_Resolution - Hazard_Focus is a hazard category, not an
infrastructure sub-type, and was checked and rejected for this purpose: it
mixes drainage, roads, and coastal projects together under "Flooding" and
"Coastal Hazards" with no sub-type signal).

Two classifications, at two confidence levels:

1. TRANSIT vs NON-TRANSIT (primary, high-confidence). Regex requires a
   transit-SPECIFIC compound term (SMART Program, Metrorail, TransitWay,
   Bus Rapid Transit, etc.) - a first pass using bare "transit", "shuttle",
   "station", "brightline" produced false positives (a marina shuttle boat,
   a drainage pump station described as protecting "transit grids", a
   drainage project merely located "in the vicinity of" a Brightline
   station) - see FALSE_POSITIVE_EXAMPLES below. The tightened pattern
   matches exactly 2 of 1,157 filtered Gray projects, both the surviving
   SMART Program corridors already flagged in flag_large_project.

2. A finer 6-way split (drainage/stormwater, road, coastal/seawall,
   water/sewer, power/comm/facility, other) - LOWER CONFIDENCE, reported
   for descriptive profiling only (Sec 2a). Project names bundle categories
   heavily: 61% of projects matching the drainage pattern ALSO match the
   road pattern (e.g. "Roadway and Drainage Improvement Project"), so a
   priority order is applied (see PRIORITY below) and a project matching
   both is filed under whichever pattern is checked first. Disclosed in
   full so the classification can be checked, not treated as a clean
   partition.
"""
import re

import pandas as pd

# ---------------------------------------------------------------- transit

TRANSIT_PATTERN = re.compile(
    r"\b(SMART\s*Program|Metrorail|Metromover|TransitWay|Trolley|"
    r"Light\s*Rail|Bus\s*Rapid\s*Transit|BRT|Commuter\s*Rail|"
    r"Transit\s*Corridor|Transit\s*Station|Bus\s*Terminal|Bus\s*Shelter|"
    r"Park\s*(?:and|&)\s*Ride)\b", re.IGNORECASE)

# kept for documentation: the loose first-pass pattern that was tried and
# rejected, and the false positives it produced (Project_ID: matched term)
FALSE_POSITIVE_EXAMPLES = {
    "SCALER-0002": ("brightline", "drainage project 'in the vicinity of ... "
                    "aventura brightline station' - not a transit project"),
    "SCALER-0623": ("shuttle", "marina 'shuttle boat' - a boat, not a "
                    "transit shuttle"),
    "SCALER-1167": ("transit", "stormwater pump station described as "
                    "protecting 'regional commercial transit grids' - a "
                    "drainage project, not transit infrastructure"),
    "SCALER-1183": ("transit", "marina mooring/bollard project self-described "
                    "as 'coastal transit infrastructure' (boat transit, not "
                    "public transit)"),
}

# ---------------------------------------------------------- finer 6-way split

PRIORITY = ["coastal_seawall", "drainage_stormwater", "road", "water_sewer",
           "power_comm_facility"]  # checked in this order; first match wins

FINER_PATTERNS = {
    "coastal_seawall": re.compile(
        r"\b(seawall|bulkhead|shoreline|coastal\s*structure|revetment|dune|"
        r"beach\s*renourish|living\s*shoreline|breakwater|jetty|groin)\b",
        re.IGNORECASE),
    "drainage_stormwater": re.compile(
        r"\b(drainage|stormwater|storm\s*water|flood\s*(?:mitigation|"
        r"protection|control|improvement)|pump\s*station|outfall|canal|"
        r"catch\s*basin|culvert|injection\s*well|retention\s*(?:pond|area)|"
        r"detention|swale|check\s*valve)\b", re.IGNORECASE),
    "road": re.compile(
        r"\b(road|roadway|street|avenue|ave|boulevard|blvd|highway|"
        r"intersection|pavement|sidewalk|bridge)\b", re.IGNORECASE),
    "water_sewer": re.compile(
        r"\b(water\s*main|sewer|wastewater|septic|sanitary|potable|"
        r"water\s*treatment)\b", re.IGNORECASE),
    "power_comm_facility": re.compile(
        r"\b(generator|electric|substation|911|communication|"
        r"hardening.*(?:facility|center))\b", re.IGNORECASE),
}


def classify_transit(name, description):
    text = f"{name or ''} || {description or ''}"
    return "transit" if TRANSIT_PATTERN.search(text) else "non_transit"


def classify_finer(name, description):
    text = f"{name or ''} || {description or ''}"
    if TRANSIT_PATTERN.search(text):
        return "transit"
    for cat in PRIORITY:
        if FINER_PATTERNS[cat].search(text):
            return cat
    return "other_unclassified"


def add_classifications(gray_df):
    """gray_df must have Project_Name, Project_Description columns."""
    out = gray_df.copy()
    out["gray_transit_split"] = [
        classify_transit(n, d) for n, d in zip(out["Project_Name"], out["Project_Description"])
    ]
    out["gray_finer_subcat"] = [
        classify_finer(n, d) for n, d in zip(out["Project_Name"], out["Project_Description"])
    ]
    return out
