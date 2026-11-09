"""Every data, output and report path for `Modelling Data from Web/`, defined once.

Scripts put `scripts/common` on sys.path and import from here, so a folder
move means changing this file only. Layout: see README.md at the folder top
and DECISIONS.md D-061.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # Modelling Data from Web/
REPO = ROOT.parent                               # the website repo
SCRIPTS = ROOT / "scripts"

# raw downloads, untouched
RAW = ROOT / "data" / "raw"
PROJECT_CSV = RAW / "projects" / "SCALE-R_Database.csv"
BOUNDARY_DIR = RAW / "boundaries"
ACS_TRACT_DIR = RAW / "social" / "acs_tract"
ACS_BG_DIR = RAW / "social" / "acs_blockgroup"
SVI_PATH = RAW / "social" / "svi" / "FLORIDA.csv"
EJSCREEN_DIR = RAW / "social" / "ejscreen"
EJSCREEN_PATH = EJSCREEN_DIR / "EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv"
SLR_DIR = RAW / "physical" / "sea_level_rise" / "FL_SE_slr_data_dist"
SLR_GPKG = SLR_DIR / "FL_SE_slr_final_dist.gpkg"
SURGE_DIR = RAW / "physical" / "storm_surge" / "US_SLOSH_MOM_Inundation_v4_20260617"
FLOOD_ZONE_DIR = RAW / "physical" / "flood_zones"
# FEMA open data for the impact work (D-113): NFIP claims, HMA subapplications
FEMA_RAW_DIR = RAW / "fema"
NFIP_CLAIMS_CSV = FEMA_RAW_DIR / "nfip_claims_miami_dade.csv"
HMA_PROJECTS_CSV = FEMA_RAW_DIR / "hma_projects_miami_dade.csv"
FEMA_DOWNLOAD_LOG = FEMA_RAW_DIR / "download_log.json"
TRACT_REL_2010_2020 = BOUNDARY_DIR / "rel2020" / "tab20_tract20_tract10_natl.txt"
TRACT_2024_ZIP = BOUNDARY_DIR / "tl_2024_12_tract.zip"
# kept outside this folder because website and repo-root scripts use them
NRI_CSV = REPO / "fema_miami_dade_dec_2025.csv"
LST_TIF = REPO / "output" / "lst" / "lst_composite_f.tif"
VIZ_DATA = REPO / "src" / "exposure" / "data"

# tables we built
PROCESSED = ROOT / "data" / "processed"
INVESTMENT_DIR = PROCESSED / "investment"
ANALYSIS_DIR = PROCESSED / "analysis"
HAZARDS_DIR = PROCESSED / "hazards"
EXPOSURE_DIR = PROCESSED / "exposure"
IMPACT_DIR = PROCESSED / "impact"
NFIP_TRACT_YEAR_CSV = IMPACT_DIR / "nfip_claims_tract_year.csv"
HMA_MATCHES_CSV = IMPACT_DIR / "hma_scaler_matches.csv"

# results by analysis
OUTPUTS = ROOT / "outputs"
OUT_PROJECTS = OUTPUTS / "projects"
OUT_CORRELATION = OUTPUTS / "correlation"
OUT_PCA = OUTPUTS / "pca"
OUT_PHYSICAL = OUTPUTS / "physical"
OUT_EXPOSURE_A = OUTPUTS / "exposure" / "stage_a"
OUT_EXPOSURE_B = OUTPUTS / "exposure" / "stage_b"
OUT_EXPOSURE_CK = OUTPUTS / "exposure" / "checkpoints"
OUT_ML = OUTPUTS / "ml"
OUT_IMPACT = OUTPUTS / "impact"

# reports written by scripts
REPORTS = ROOT / "reports"
REPORTS_ANALYSIS = REPORTS / "analysis"
REPORTS_IMPACT = REPORTS / "impact"


def use(*folders):
    """Put sibling script folders (for example "03_physical") on sys.path."""
    for f in folders:
        p = str(SCRIPTS / f)
        if p not in sys.path:
            sys.path.insert(0, p)
