"""Build the two reference tables for the benefit simulator (prompt 27 Stage 1, items 7 and 8).

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/build_reference_tables.py"

1. data/reference/fema_standard_values.csv (D-124)
   Every value is transcribed from an official FEMA document saved in
   data/raw/reference_docs/fema/. Each row carries a search snippet; the script
   finds that snippet in the PDF text and records the PDF page and printed page
   itself. If a snippet is not found the script stops, so no value can enter
   the table without being on the page cited. Values FEMA does not print are
   listed in MISSING and written to a separate file, never invented.

2. data/reference/depth_damage_curves.csv (D-125)
   USACE depth-damage functions keyed to NSI occupancy codes, from the
   occupancy type library that USACE ships with its consequence model
   (go-consequences, structures/occtypes.json, pinned commit). Only the
   depth-driven curves are kept: the freshwater "depth" curves and, where
   USACE supplies them, the saltwater "depth, salinity" curves.
   Values are percent damage (mean and standard deviation) at each depth in
   feet above the first floor.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pypdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

FEMA_DOCS = paths.REFERENCE_DOCS_DIR / "fema"
USACE_DIR = paths.REFERENCE_DOCS_DIR / "usace"

# document key -> (title, version and date, URL, local file name)
DOCS = {
    "SEV13": ("Benefit-Cost Analysis Sustainment and Enhancements: Standard Economic Value Methodology Report",
              "Version 13.0, September 2024, updated July 2025",
              "https://www.fema.gov/sites/default/files/documents/fema_bca_general-economic-values_2025.pdf",
              "fema_bca_general-economic-values_2025.pdf"),
    "FLOOD6": ("BCA Toolkit Riverine and Coastal Flood Module: Benefit-Cost Analysis Methodology Report",
               "Version 6, January 2025, updated June 2025",
               "https://www.fema.gov/sites/default/files/documents/fema_bca_hazard-methodology-riverine-coastal-flood_2025.pdf",
               "fema_bca_hazard-methodology-riverine-coastal-flood_2025.pdf"),
    "PCCE6": ("Project Configuration and Cost Estimation: Benefit-Cost Analysis Methodology Report",
              "Version 6.0, December 2024, updated July 2025",
              "https://www.fema.gov/sites/default/files/documents/fema_bca_methodology-project-configuration-cost-estimation_2025.pdf",
              "fema_bca_methodology-project-configuration-cost-estimation_2025.pdf"),
    "HELP": ("FEMA BCA Toolkit Help Content", "28 August 2025",
             "https://www.fema.gov/sites/default/files/documents/bca-allhelpcontent-pdf-08-28-2025.pdf",
             "bca-allhelpcontent-pdf-08-28-2025.pdf"),
    "GI": ("FEMA Economic Benefit Values for Green Infrastructure", "July 2022, updated July 2025",
           "https://www.fema.gov/sites/default/files/documents/fema_bca_economic-values-green-infrastructure_2025.pdf",
           "fema_bca_economic-values-green-infrastructure_2025.pdf"),
    "ESV": ("FEMA Ecosystem Service Value Updates", "June 2022",
            "https://www.fema.gov/sites/default/files/documents/fema_ecosystem-service-value-updates_2022.pdf",
            "fema_ecosystem-service-value-updates_2022.pdf"),
}

# (id, category, item, value, unit, dollar_year, applies_to, doc, snippet, note)
# The snippet must occur, whitespace-normalised, on one page of the document.
V = []


def add(vid, cat, item, value, unit, year, applies, doc, snippet, note=""):
    V.append(dict(value_id=vid, category=cat, item=item, value=value, unit=unit, dollar_year=year,
                  applies_to=applies, doc=doc, snippet=snippet, note=note))


# ---- displacement (SEV13 section 2.3; FLOOD6 section 2.9) ----
add("disp_res_lodging_std", "displacement", "Residential lodging, GSA CONUS standard rate (FY2025)", 110,
    "$ per room per day", "FY2025", "residential",
    "SEV13", "For FY2025, the Standard Rate is $110 per room per day",
    "FEMA uses the GSA lodging per diem for the project location; the standard rate applies where GSA has no local rate. The Miami-Dade local rate was not downloaded (see missing list).")
add("disp_res_mie_std", "displacement", "Residential meals and incidentals, GSA CONUS standard rate (FY2025)", 68,
    "$ per person per day", "FY2025", "residential",
    "SEV13", "For FY2025, the standard rate is $68 per person per day")
add("disp_res_food_home", "displacement", "Cost of eating meals at home (deducted from meals per diem)", 10,
    "$ per person per day", "2024 (USDA, rounded)", "residential",
    "SEV13", "Cost of Eating Meals at Home $9 per person per day $10 per person per day")
add("disp_days_per_ft_example", "displacement", "Displacement duration, one-story residence without basement, per foot of flooding (example DDF)", 45,
    "days per foot (45 at 1 ft, 90 at 2 ft ... 225 at 5 ft)", "n/a", "residential, one story, no basement",
    "FLOOD6", "1 23.3% 13.3% 45 45",
    "FEMA prints this as an example of the full DDF (Table 1). The days rise by 45 per foot from 0 days at 0 ft to 225 days at 5 ft.")
for code, label, rent, disr in [
        ("RES1", "Single Family Dwelling", "0.91", "1.10"), ("RES2", "Mobile Home", "0.64", "1.10"),
        ("RES3a-f", "Multi Family Dwelling", "0.82", "1.10"), ("RES4", "Temporary Lodging", "2.74", "1.10"),
        ("RES5", "Institutional Dormitory", "0.55", "1.10"), ("RES1 nursing", "Nursing Home", "1.01", "1.10"),
        ("COM1", "Retail Trade", "1.55", "1.46"), ("COM2", "Wholesale Trade", "0.64", "1.28"),
        ("COM3", "Personal and Repair Services", "1.83", "1.28"), ("COM5", "Banks", "2.29", "1.28"),
        ("COM6", "Hospital", "1.83", "1.83"), ("COM7", "Medical Office/Clinic", "1.83", "1.83"),
        ("COM8", "Entertainment and Recreation", "2.29", "0.00"), ("COM9", "Theaters", "2.29", "0.00"),
        ("COM10", "Parking", "0.46", "0.00"), ("IND1", "Heavy", "0.27", "0.00"), ("IND2", "Light", "0.37", "1.28"),
        ("IND3", "Food/Drugs/Chemicals", "0.37", "1.28"), ("IND4", "Metals/Mineral Processing", "0.27", "1.28"),
        ("IND5", "High Technology", "0.46", "1.28"), ("IND6", "Construction", "0.18", "1.28"),
        ("AGR1", "Agriculture", "0.91", "0.91"), ("REL1", "Church/Membership Organization", "1.37", "1.28"),
        ("GOV1", "General Services", "1.83", "1.28"), ("GOV2", "Emergency Response", "1.83", "1.28"),
        ("EDU1", "Schools/Libraries", "1.37", "1.28"), ("EDU2", "College/Universities", "1.83", "1.28")]:
    snip = f"{label} ("  # the row label is on the page; numbers checked below on the same page
    k = code.split()[0].replace("a-f", "")
    add(f"disp_rent_{code.replace(' ', '_')}", "displacement", f"Rental cost while displaced, {code} {label}", float(rent),
        "$ per sq ft per month", "2021", code, "SEV13", f"{label} (", f"Table 3 (from Hazus). Row value pair: rent {rent}, one-time disruption {disr}.")
    add(f"disp_oneoff_{code.replace(' ', '_')}", "displacement", f"One-time disruption cost, {code} {label}", float(disr),
        "$ per sq ft", "2021", code, "SEV13", f"{label} (")
    V[-2]["check_numbers"] = [rent, disr]
    V[-1]["check_numbers"] = [rent, disr]
# COM4 is split over two lines in the PDF text, so it is checked by its numbers only
add("disp_rent_COM4", "displacement", "Rental cost while displaced, COM4 Professional/Technical/Business", 1.83,
    "$ per sq ft per month", "2021", "COM4", "SEV13", "15 COM4 Professional/Technical/Business")
add("disp_oneoff_COM4", "displacement", "One-time disruption cost, COM4 Professional/Technical/Business", 1.28,
    "$ per sq ft", "2021", "COM4", "SEV13", "15 COM4 Professional/Technical/Business")

# ---- time, roads and utilities (loss of function) ----
add("time_value_hour", "loss of function", "Value of lost time", 43.11, "$ per person-hour", "2023 (BLS Dec 2023)",
    "people's time spent on disaster-related tasks", "SEV13", "The 2024 hourly rate of $43.11")
add("road_delay_vehicle_hour", "loss of function: roads", "Traffic delay for road and bridge closures", 36.63,
    "$ per vehicle per hour", "2023", "detoured vehicles", "SEV13", "a value of $36.63 is applied per vehicle per hour",
    "Needs project-specific traffic counts and detour times; FEMA gives no per-road default.")
add("util_electric", "loss of function: utilities", "Loss of electric service", 213, "$ per person per day", "2023",
    "people served", "SEV13", "Total Economic Impact (rounded to nearest dollar) $213")
add("util_wastewater", "loss of function: utilities", "Loss of wastewater service", 71, "$ per person per day", "2023",
    "people served", "SEV13", "Total Economic Impact (rounded to nearest dollar) $71")
add("util_water", "loss of function: utilities", "Loss of potable water service", 150, "$ per person per day", "2023",
    "people served", "SEV13", "Total Economic Impact (rounded to nearest dollar) $150")
add("util_comms", "loss of function: utilities", "Loss of communications/IT service", 151, "$ per person per day", "2023",
    "people served", "SEV13", "Total Economic Impact (rounded to nearest dollar) $151")

# ---- discounting and project useful life ----
add("discount_rate", "discounting", "Default discount rate for new BCAs", 0.07, "per year (real)", "n/a", "all",
    "HELP", "However, for new BCAs, the default 7% discount rate should be used",
    "FEMA used 3.1% in 2023 and 2024; policy reverted to 7% in 2025 (same page). 3.1% kept as a sensitivity value.")
add("discount_rate_2023_2024", "discounting", "Discount rate used in 2023 and 2024 (sensitivity only)", 0.031,
    "per year (real)", "n/a", "sensitivity", "HELP", "for 2023 and 2024, the discount rate was 3.1%")
for vid, label, yrs, snip in [
        ("pul_acquisition", "Acquisition/Relocation", 100, "Acquisition/Relocation 100 100"),
        ("pul_res_elevation", "Residential Building Elevation", 30, "Residential Building Elevation 30 30–50"),
        ("pul_nonres_elevation", "Non-Residential Building Elevation", 25, "Non-Residential Building Elevation 25 25–50"),
        ("pul_major_infra", "Major Infrastructure (dams, levees)", 50, "Major Infrastructure (dams,"),
        ("pul_floodwall_drainage", "Concrete Infrastructure, Floodwalls, Roads, Bridges, Major Drainage System", 50,
         "Concrete Infrastructure, Floodwalls, Roads, Bridges, Major"),
        ("pul_major_pump", "Major Pump Stations, Substations, Wastewater Systems, or Equipment", 50,
         "Major Pump Stations,"),
        ("pul_minor_pump", "Minor Pump Stations ... (backflow valves etc.)", 5, "Minor Pump Stations,"),
        ("pul_floodplain_restoration", "Floodplain and Stream Restoration", 30, "Floodplain and Stream"),
        ("pul_flood_diversion_storage", "Flood Diversion and Storage", 30, "Flood Diversion and Storage 30"),
        ("pul_bioretention", "Bioretention", 35, "Bioretention 35 35–50"),
        ("pul_green_roofs", "Green Roofs", 35, "Green Roofs 35 35–50"),
        ("pul_permeable_pavement", "Permeable Pavement", 30, "Permeable Pavement 30 30–50"),
        ("pul_urban_trees", "Urban Trees", 25, "Urban Trees 25 25–50")]:
    add(vid, "project useful life", f"Standard project useful life: {label}", yrs, "years", "n/a", label, "PCCE6", snip)

# ---- ecosystem services per acre (land cover) ----
for vid, label, val in [("esv_urban_green", "Urban Green Open Space", "15,541"),
                        ("esv_rural_green", "Rural Green Open Space", "10,632"),
                        ("esv_riparian", "Riparian", "37,199"), ("esv_coastal_wetland", "Coastal Wetlands", "8,955"),
                        ("esv_inland_wetland", "Inland Wetlands", "8,171"), ("esv_forest", "Forests", "12,589"),
                        ("esv_coral_reef", "Coral Reefs", "7,120"), ("esv_shellfish_reef", "Shellfish Reefs", "2,757"),
                        ("esv_beach_dune", "Beaches & Dunes", "300,649")]:
    add(vid, "ecosystem services", f"Ecosystem service value, {label} (total)", float(val.replace(",", "")),
        "$ per acre per year", "2021", label, "HELP", f"Valued at ${val}/acre/year",
        "Total includes aesthetic and recreation value (partly in property prices) and flood and storm hazard reduction (overlaps avoided flood losses). See the esvpart_ rows to remove them.")

# per-service breakdown (ESV Table 4) so double-counted parts can be removed later
ESV_COLS = ["Urban Green Open Space", "Rural Green Open Space", "Riparian", "Forest", "Coastal Wetland",
            "Inland Wetland", "Coral Reefs", "Shellfish Reefs", "Beaches and Dunes"]
ESV_ROWS = {
    "Aesthetic Value": "7,010 7,505 767 1,477 1,648 1,303 327 - 223,840",
    "Air Quality": "201 - 254 711 - - - - -",
    "Climate Regulation": "54 77 96 199 125 56 - - -",
    "Erosion Control": "78 78 13,823 1,672 - - - - -",
    "Habitat": "5,890 2,021 2,547 - 2,420 1,416 2,222 - -",
    "Pollination": "350 350 - - - - - - -",
    "Water Filtration": "- - 6,239 435 1,558 1,584 - 600 -",
    "Water Supply": "- - 272 103 544 643 - - -",
}
for svc, row in ESV_ROWS.items():
    for col, v in zip(ESV_COLS, row.split()):
        if v == "-":
            continue
        add(f"esvpart_{col.lower().replace(' ', '_')}_{svc.lower().replace(' ', '_')}", "ecosystem services (component)",
            f"{svc}, {col}", float(v.replace(",", "")), "$ per acre per year", "2021", col, "ESV",
            f"{svc} {row}")
# rows whose labels wrap over two lines in the PDF: checked by the numbers line alone
for svc, row in {"Biological Control": "- - 199 - - - - - -",
                 "Flood and Storm Hazard Reduction": "316 - 6,052 368 1,035 1,264 3,269 - -",
                 "Food Provisioning": "- - 736 - - - 18 1,905 -",
                 "Recreation/Tourism": "1,642 601 6,215 94 1,624 1,906 1,261 253 76,809",
                 "Research and Education": "- - - - - - 23 - -",
                 "Existence Value": "- - - 7,531 - - - - -"}.items():
    for col, v in zip(ESV_COLS, row.split()):
        if v == "-":
            continue
        add(f"esvpart_{col.lower().replace(' ', '_')}_{svc.lower().replace(' ', '_').replace('/', '_')}",
            "ecosystem services (component)", f"{svc}, {col}", float(v.replace(",", "")), "$ per acre per year",
            "2021", col, "ESV", row)

# ---- green infrastructure (GI Table 3, 2021 USD) ----
GI = [  # benefit, type, value, unit, snippet
    ("Building energy cost savings", "Green roofs", 0.05, "$/sq ft/year", "cost savings $0.05 $17.05"),
    ("Building energy cost savings", "Urban trees", 17.05, "$/tree/year", "cost savings $0.05 $17.05"),
    ("Drought risk reduction", "Permeable pavement", 0.13, "$/sq ft/year", "reduction $0.13 $0.52 $5.53"),
    ("Drought risk reduction", "Bioretention", 0.52, "$/sq ft/year", "reduction $0.13 $0.52 $5.53"),
    ("Drought risk reduction", "Urban trees", 5.53, "$/tree/year", "reduction $0.13 $0.52 $5.53"),
    ("Habitat", "Green roofs", 0.05, "$/sq ft/year", "Habitat $0.05 $0.11 $40.18"),
    ("Habitat", "Bioretention", 0.11, "$/sq ft/year", "Habitat $0.05 $0.11 $40.18"),
    ("Habitat", "Urban trees", 40.18, "$/tree/year", "Habitat $0.05 $0.11 $40.18"),
    ("Heat risk reduction", "Urban trees", 910.28, "$/tree/year", "$910.28"),
    ("Property value improvement", "Green roofs", 0.19, "$/sq ft/year", "$0.19 $0.40 $53.15"),
    ("Property value improvement", "Bioretention", 0.40, "$/sq ft/year", "$0.19 $0.40 $53.15"),
    ("Property value improvement", "Urban trees", 53.15, "$/tree/year", "$0.19 $0.40 $53.15"),
    ("Removal of air pollutants", "Green roofs", 0.001, "$/sq ft/year", "$0.001 $0.004 $2.50"),
    ("Removal of air pollutants", "Bioretention", 0.004, "$/sq ft/year", "$0.001 $0.004 $2.50"),
    ("Removal of air pollutants", "Urban trees", 2.50, "$/tree/year", "$0.001 $0.004 $2.50"),
    ("Stormwater volume and quality", "Green roofs", 0.09, "$/sq ft/year", "$0.09 $0.51 $1.80 $20.17"),
    ("Stormwater volume and quality", "Permeable pavement", 0.51, "$/sq ft/year", "$0.09 $0.51 $1.80 $20.17"),
    ("Stormwater volume and quality", "Bioretention", 1.80, "$/sq ft/year", "$0.09 $0.51 $1.80 $20.17"),
    ("Stormwater volume and quality", "Urban trees", 20.17, "$/tree/year", "$0.09 $0.51 $1.80 $20.17"),
    ("Total", "Green roofs", 0.38, "$/sq ft/year", "Total ($/ft2/year) $0.38 $0.64 $2.83 $1,048.86"),
    ("Total", "Permeable pavement", 0.64, "$/sq ft/year", "Total ($/ft2/year) $0.38 $0.64 $2.83 $1,048.86"),
    ("Total", "Bioretention", 2.83, "$/sq ft/year", "Total ($/ft2/year) $0.38 $0.64 $2.83 $1,048.86"),
    ("Total", "Urban trees", 1048.86, "$/tree/year", "Total ($/ft2/year) $0.38 $0.64 $2.83 $1,048.86"),
    ("Total per acre", "Green roofs", 16596.36, "$/acre/year", "$16,596.36 $27,878.40 $123,449.04"),
    ("Total per acre", "Permeable pavement", 27878.40, "$/acre/year", "$16,596.36 $27,878.40 $123,449.04"),
    ("Total per acre", "Bioretention", 123449.04, "$/acre/year", "$16,596.36 $27,878.40 $123,449.04"),
]
for ben, typ, val, unit, snip in GI:
    note = ""
    if ben == "Property value improvement":
        note = "Do not add to avoided losses: the property value model (Stage 3) measures this directly."
    elif ben == "Total" or ben == "Total per acre":
        note = "Total includes property value improvement; subtract it before adding to avoided losses."
    add(f"gi_{typ.lower().replace(' ', '_')}_{ben.lower().replace(' ', '_')}", "green infrastructure",
        f"{ben}, {typ}", val, unit, "2021", typ, "GI", snip, note)

MISSING = [
    ("Mental stress and anxiety (social benefit)", "residential",
     "Checked 10 Nov 2026 (D-133): BCA Toolkit Help Content (28 Aug 2025, PDF pages 176 to 177) describes the method only (a standard value times residents not displaced); Standard Economic Value report v13, flood module report v6, Toolkit 6.0 release notes (Jul 2020) and Toolkit 6.0 User Guide (May 2019) do not print it. The 2012 Final Sustainability Benefits Methodology Report is not on fema.gov, and the FEMA web page that printed 'Table 5: BCA Social Benefits Values' now returns 404. State agency slides quote $2,443 per person; not used."),
    ("Lost productivity (social benefit)", "residential",
     "Same checks as above: the method (a standard value times working residents not displaced) is described, the dollar value is not printed in any FEMA document still available. State agency slides quote $8,736 per worker; not used."),
    ("GSA lodging and meals per diem for Miami-Dade (local rate)", "residential displacement",
     "FEMA uses the local GSA rate; only the CONUS standard rate is printed in the FEMA report. The GSA site was not in the list of downloads."),
    ("Displacement days for other building types and depths", "displacement",
     "The flood module report prints only the one-story, no-basement example (0 to 5 ft). The full DDF library sits inside the BCA Toolkit, not in a document."),
    ("Loss of function for roads: default traffic volumes or detour times", "roads",
     "FEMA gives a $ per vehicle-hour delay value only; volumes and detour times are project inputs."),
    ("Project useful life for living shorelines or other coastal nature-based projects", "blue projects",
     "No living shoreline row in the PUL tables; floodplain and stream restoration (30 years) is the nearest listed type."),
]


def page_texts(path):
    r = pypdf.PdfReader(str(path))
    return [p.extract_text() or "" for p in r.pages]


def norm(s):
    return re.sub(r"\s+", " ", s.replace("–", "–")).strip()


def printed_page(text):
    for line in text.split("\n")[:4]:
        m = re.search(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
                      r" 20\d\d\s+([ivx]+|\d+)\s*$", line.strip())
        if m:
            return m.group(1)
    for line in text.split("\n")[:3]:
        if re.fullmatch(r"\s*\d{1,3}\s*", line):
            return line.strip()
    return ""


def build_values():
    texts = {k: page_texts(FEMA_DOCS / d[3]) for k, d in DOCS.items()}
    norm_texts = {k: [norm(t) for t in v] for k, v in texts.items()}
    rows = []
    for v in V:
        pages = [i for i, t in enumerate(norm_texts[v["doc"]]) if norm(v["snippet"]) in t]
        if not pages:
            raise SystemExit(f"snippet not found for {v['value_id']}: {v['snippet']!r}")
        i = pages[0]
        if v["doc"] == "HELP" and len(pages) > 1:
            pass  # the help content repeats sections per module; the first occurrence is cited
        for num in v.get("check_numbers", []):
            assert num in norm_texts[v["doc"]][i], f"{v['value_id']}: {num} not on page {i + 1}"
        num_str = f"{v['value']:,}".rstrip("0").rstrip(".") if isinstance(v["value"], float) else str(v["value"])
        title, ver, url, fname = DOCS[v["doc"]]
        rows.append(dict(value_id=v["value_id"], category=v["category"], item=v["item"], value=v["value"],
                         unit=v["unit"], dollar_year=v["dollar_year"], applies_to=v["applies_to"],
                         label="assumption (published standard value)", source_document=title,
                         version_date=ver, url=url, local_file=f"data/raw/reference_docs/fema/{fname}",
                         pdf_page=i + 1, printed_page=printed_page(texts[v["doc"]][i]), note=v["note"]))
    df = pd.DataFrame(rows)
    assert df.value_id.is_unique
    return df


def build_curves():
    commit = (USACE_DIR / "occtypes_commit.txt").read_text().split()
    d = json.loads((USACE_DIR / "occtypes.json").read_text())["occupancytypes"]
    rows = []
    for occ, o in d.items():
        for comp, v in o["componentdamagefunctions"].items():
            for driver, f in v["damagefunctions"].items():
                drivers = sorted(x.strip() for x in driver.split(","))
                if drivers == ["depth"]:
                    water = "fresh"
                elif drivers == ["depth", "salinity"]:
                    water = "salt"
                else:
                    continue
                fn = f["damagefunction"]
                for x, y in zip(fn["xvalues"], fn["ydistributions"]):
                    p = y["parameters"]
                    lo = hi = None
                    if y["type"] == "NormalDistribution":
                        mean, sd = p["mean"], p["standarddeviation"]
                        lo, hi = max(mean - 1.645 * sd, 0), min(mean + 1.645 * sd, 100)
                    elif y["type"] == "TriangularDistribution":
                        mean, sd = (p["min"] + p["mostlikely"] + p["max"]) / 3, None
                        lo, hi = p["min"], p["max"]
                    elif y["type"] == "DeterministicDistribution":
                        mean, sd, lo, hi = p["value"], 0.0, p["value"], p["value"]
                    elif y["type"] == "EmpiricalDistribution":
                        starts, w, cnt = p["binstarts"], p["binwidth"], p["bincounts"]
                        tot = sum(cnt)
                        mean = sum((s + w / 2) * c for s, c in zip(starts, cnt)) / tot
                        sd, lo, hi = None, p["minvalue"], p["maxvalue"]
                    else:
                        raise SystemExit(f"unknown distribution {y['type']}")
                    rows.append(dict(occtype=occ, component=comp, water=water, depth_ft=x,
                                     damage_pct_mean=round(mean, 4), damage_pct_sd=None if sd is None else round(sd, 4),
                                     damage_pct_low=round(lo, 4), damage_pct_high=round(hi, 4),
                                     distribution=y["type"], curve_source=f.get("source", ""),
                                     library="USACE go-consequences structures/occtypes.json",
                                     library_commit=commit[0], library_commit_date=commit[1]))
    return pd.DataFrame(rows)


def main():
    paths.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    vals = build_values()
    vals.to_csv(paths.FEMA_STANDARD_VALUES_CSV, index=False)
    miss = pd.DataFrame(MISSING, columns=["item", "applies_to", "why_missing"])
    miss.to_csv(paths.REFERENCE_DIR / "fema_standard_values_missing.csv", index=False)
    curves = build_curves()
    curves.to_csv(paths.DEPTH_DAMAGE_CSV, index=False)
    print(f"standard values: {len(vals)} rows; missing: {len(miss)}")
    print(vals.groupby("category").size().to_string())
    print(f"depth-damage rows: {len(curves)}; occupancy types: {curves.occtype.nunique()}")
    print(curves.groupby(["component", "water"]).occtype.nunique().to_string())


if __name__ == "__main__":
    main()
