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
# Benefit simulator downloads (prompt 27, D-119 onward)
NFIP_POLICIES_CSV = FEMA_RAW_DIR / "nfip_policies_miami_dade.csv.gz"
NFIP_POLICIES_LOG = FEMA_RAW_DIR / "nfip_policies_download_log.json"
NFHL_DIR = FEMA_RAW_DIR / "nfhl"
# the flood map in use; to switch to the 19 Feb 2027 maps, download the new county
# NFHL zip into NFHL_DIR and change this one name (D-123, D-131)
NFHL_COUNTY_ZIP = NFHL_DIR / "12086C_20260125.zip"
DOR_DIR = RAW / "dor"                      # Florida DOR tax roll (NAL) and parcel GIS
NSI_DIR = RAW / "nsi"                      # USACE National Structure Inventory
NSI_2026_GEOJSON = NSI_DIR / "nsi_2026_api_12086.geojson"   # used (D-130)
NSI_2022_GPKG_ZIP = NSI_DIR / "nsi_2022_12.gpkg.zip"        # comparison only
FHFA_DIR = RAW / "fhfa"                    # FHFA tract house price index
REFERENCE_DOCS_DIR = RAW / "reference_docs"  # FEMA BCA and Hazus documents (PDFs)
BENEFIT_DOWNLOAD_LOG = RAW / "benefit_download_log.json"
# NOAA DEM read remotely by HTTP range requests, as the website script does
NOAA_DEM_URL = "https://coast.noaa.gov/slrdata/DEMs/FL/FL_SE_GCS_3m_NAVDm_v3.tif"
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
BENEFIT_DIR = PROCESSED / "benefit"
BUILDINGS_PARQUET = BENEFIT_DIR / "buildings.parquet"
REFERENCE_DIR = ROOT / "data" / "reference"
FEMA_STANDARD_VALUES_CSV = REFERENCE_DIR / "fema_standard_values.csv"
DEPTH_DAMAGE_CSV = REFERENCE_DIR / "depth_damage_curves.csv"
VERTCON_GRID_CSV = REFERENCE_DIR / "ngvd29_to_navd88_grid.csv"
HURRICANE_RATES_CSV = REFERENCE_DIR / "hurricane_strike_rates.csv"   # Stage 2 (D-136)
BLS_DIR = RAW / "bls"                                                # CPI-U downloads (D-144)
CPI_ANNUAL_CSV = REFERENCE_DIR / "cpi_u_annual.csv"                  # Stage 2 (D-144)
MDC_LAYERS_DIR = RAW / "mdc_layers"                                   # Miami-Dade open data: Metrorail, schools, parks (Stage 3)
SALES_FEATURES_PARQUET = BENEFIT_DIR / "sales_features.parquet"      # Stage 3 model table
SALES_FEATURES_CSV = BENEFIT_DIR / "sales_features.csv.gz"           # same, for the ML environment (no pyarrow)
NHC_DOCS_DIR = RAW / "reference_docs" / "nhc"                       # NHC memo and return period maps
NFIP_POLICIES_PARQUET_MANUAL = None   # set to the user's full NFIP policies Parquet file when on disk
EAD_BUILDINGS_PARQUET = BENEFIT_DIR / "ead_buildings.parquet"      # Stage 2 output
EAD_TRACT_CSV = BENEFIT_DIR / "ead_tract.csv"                      # Stage 2 output

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
OUT_BENEFIT = OUTPUTS / "benefit"

# reports written by scripts
REPORTS = ROOT / "reports"
REPORTS_ANALYSIS = REPORTS / "analysis"
REPORTS_IMPACT = REPORTS / "impact"
REPORTS_BENEFIT = REPORTS / "benefit"


def use(*folders):
    """Put sibling script folders (for example "03_physical") on sys.path."""
    for f in folders:
        p = str(SCRIPTS / f)
        if p not in sys.path:
            sys.path.insert(0, p)
