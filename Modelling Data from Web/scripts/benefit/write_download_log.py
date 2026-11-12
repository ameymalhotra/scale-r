"""Record what was downloaded for prompt 27 Stage 1 (URL, date, size, SHA-256) in data/raw/benefit_download_log.json.

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/write_download_log.py"
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

DOR = "https://floridarevenue.com/property/dataportal/Documents/PTO%20Data%20Portal"
FEMA = "https://www.fema.gov/sites/default/files/documents/"
FILES = [  # local path (relative to data/raw), URL, publisher's date for the file
    ("dor/Dade_23_Final_NAL_2026.zip", f"{DOR}/Tax%20Roll%20Data%20Files/NAL/2026F/Dade%2023%20Final%20NAL%202026.zip", "posted 28 Oct 2026; CSV inside dated 16 Oct 2026"),
    ("dor/miamidade_2026Ppar.zip", f"{DOR}/Map%20Data/2026F/2026F%20PAR/miamidade_2026Ppar.zip", "posted 7 Aug 2026; shapefile dated 27 Jul 2026"),
    ("dor/miamidade_condos_2026.zip", f"{DOR}/Map%20Data/2026F/2026F%20PAR/miamidade_condos_2026.zip", "posted 7 Aug 2026; shapefile dated 28 Apr 2026"),
    ("dor/parcel_shapefiles_readme.pdf", f"{DOR}/Map%20Data/parcel%20shapefiles%20readme.pdf", "10 Feb 2026"),
    ("reference_docs/dor/2026_NAL_SDF_NAP_Users_Guide.pdf", f"{DOR}/User%20Guides/2026%20Users%20guide%20and%20quick%20reference/2026_NAL_SDF_NAP_Users_Guide.pdf", "2026"),
    ("nsi/nsi_2022_12.gpkg.zip", "https://nsi.sec.usace.army.mil/downloads/nsi_2022/nsi_2022_12.gpkg.zip", "Last-Modified 30 Sep 2022; comparison only (D-130)"),
    ("nsi/nsi_2026_api_12086.geojson", "https://nsi.sec.usace.army.mil/nsiapi/structures?fips=12086&fmt=fc", "NSI 2026 via API; used (D-130)"),
    ("fema/nfhl/12086C_20260125.zip", "https://hazards.fema.gov/nfhlv2/output/County/12086C_20260125.zip", "NFHL database revised 26 Jan 2026; FIRM effective 11 Sep 2009"),
    ("fhfa/hpi_at_tract_miami_dade.csv", "https://www.fhfa.gov/hpi/download/annual/hpi_at_tract.csv", "Miami-Dade rows of the national file (national SHA-256 in fhfa/sha256.txt); data to 2025"),
    ("reference_docs/usace/occtypes.json", "https://raw.githubusercontent.com/USACE/go-consequences/dff647cabbc1abae3f084e80b7f6a166651d05d8/structures/occtypes.json", "commit 27 Dec 2021"),
    ("reference_docs/fema/fema_bca_general-economic-values_2025.pdf", FEMA + "fema_bca_general-economic-values_2025.pdf", "v13.0, Sep 2024, updated Jul 2025"),
    ("reference_docs/fema/fema_bca_hazard-methodology-riverine-coastal-flood_2025.pdf", FEMA + "fema_bca_hazard-methodology-riverine-coastal-flood_2025.pdf", "v6, Jan 2025, updated Jun 2025"),
    ("reference_docs/fema/fema_bca_methodology-project-configuration-cost-estimation_2025.pdf", FEMA + "fema_bca_methodology-project-configuration-cost-estimation_2025.pdf", "v6.0, Dec 2024, updated Jul 2025"),
    ("reference_docs/fema/bca-allhelpcontent-pdf-08-28-2025.pdf", FEMA + "bca-allhelpcontent-pdf-08-28-2025.pdf", "28 Aug 2025"),
    ("reference_docs/fema/fema_bca_economic-values-green-infrastructure_2025.pdf", FEMA + "fema_bca_economic-values-green-infrastructure_2025.pdf", "Jul 2022, updated Jul 2025"),
    ("reference_docs/fema/fema_ecosystem-service-value-updates_2022.pdf", FEMA + "fema_ecosystem-service-value-updates_2022.pdf", "Jun 2022"),
    ("reference_docs/fema/fema_standard-economic-values-methodology-report_2023.pdf", FEMA + "fema_standard-economic-values-methodology-report_2023.pdf", "v12.0, May 2023; superseded by v13, not used"),
    # Stage 2
    ("reference_docs/nhc/nws-nhc-6.pdf", "https://www.nhc.noaa.gov/pdf/nws-nhc-6.pdf", "Aug 2011 (NOAA Tech. Memo. NWS NHC-6)"),
    ("reference_docs/nhc/return_hurr.jpg", "https://www.nhc.noaa.gov/climo/images/return_hurr.jpg", "HURISK, data to 2010"),
    ("reference_docs/nhc/return_mjrhurr.jpg", "https://www.nhc.noaa.gov/climo/images/return_mjrhurr.jpg", "HURISK, data to 2010"),
    ("bls/cpiu_1978_1987.json", "https://api.bls.gov/publicAPI/v1/timeseries/data/ (POST, CUUR0000SA0, 1978 to 1987)", "downloaded 11 Nov 2026"),
    ("bls/cpiu_1988_1997.json", "https://api.bls.gov/publicAPI/v1/timeseries/data/ (POST, CUUR0000SA0, 1988 to 1997)", "downloaded 11 Nov 2026"),
    ("bls/cpiu_1998_2007.json", "https://api.bls.gov/publicAPI/v1/timeseries/data/ (POST, CUUR0000SA0, 1998 to 2007)", "downloaded 11 Nov 2026"),
    ("bls/cpiu_2008_2017.json", "https://api.bls.gov/publicAPI/v1/timeseries/data/ (POST, CUUR0000SA0, 2008 to 2017)", "downloaded 11 Nov 2026"),
    ("bls/cpiu_2018_2025.json", "https://api.bls.gov/publicAPI/v1/timeseries/data/ (POST, CUUR0000SA0, 2018 to 2025)", "downloaded 11 Nov 2026"),
    # Stage 3: Miami-Dade County open data (publisher MDPublisher), GeoJSON query of all features
    ("mdc_layers/MetroRailStations_gdb_p0.geojson", "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/MetroRailStations_gdb/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson", "downloaded 11 Nov 2026"),
    ("mdc_layers/SchoolSite_gdb_p0.geojson", "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/SchoolSite_gdb/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson", "downloaded 11 Nov 2026"),
    ("mdc_layers/CountyParkBoundaries_PROS_View_for_ALWAYS_ON_p0.geojson", "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/CountyParkBoundaries_PROS_View_for_ALWAYS_ON/FeatureServer/1/query?where=1=1&outFields=*&outSR=4326&f=geojson", "downloaded 11 Nov 2026"),
    ("mdc_layers/MunicipalParkBoundary_gdb_p0.geojson", "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/MunicipalParkBoundary_gdb/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson", "downloaded 11 Nov 2026"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = []
    for rel, url, date in FILES:
        p = paths.RAW / rel
        rows.append({"file": f"data/raw/{rel}", "url": url, "publisher_date": date, "downloaded": "2026-11-10",
                     "bytes": p.stat().st_size, "sha256": sha(p)})
    paths.BENEFIT_DOWNLOAD_LOG.write_text(json.dumps({"note": "NFIP policies: see fema/nfip_policies_download_log.json",
                                                      "files": rows}, indent=2))
    print(f"logged {len(rows)} files")


if __name__ == "__main__":
    main()
