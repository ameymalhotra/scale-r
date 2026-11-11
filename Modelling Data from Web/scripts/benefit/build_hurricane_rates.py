"""Annual hurricane strike rates by category for Southeast Florida (prompt 27 Stage 2, D-136).

    ../.venv/bin/python -I scripts/benefit/build_hurricane_rates.py

Source: Blake, Landsea and Gibney (2011), NOAA Technical Memorandum NWS NHC-6,
"The Deadliest, Costliest, and Most Intense United States Tropical Cyclones
from 1851 to 2010", Table 10 (hurricane strikes 1851-2010 by Saffir-Simpson
category), row "(Southeast)" under Florida. PDF page 23, printed page 21.

The counts are checked against the PDF text before the table is written, so
nothing is typed in by hand without a check. Writes data/reference/hurricane_strike_rates.csv.
"""
import sys
from pathlib import Path

import pandas as pd
import pypdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

PDF = paths.NHC_DOCS_DIR / "nws-nhc-6.pdf"
URL = "https://www.nhc.noaa.gov/pdf/nws-nhc-6.pdf"
YEARS = 2010 - 1851 + 1          # 160 years of record in Table 10
ROW = "(Southeast) 16 14 11 3 1 45 15"   # categories 1 to 5, all hurricanes, major hurricanes
PDF_PAGE, PRINTED_PAGE = 23, 21


def main():
    text = pypdf.PdfReader(PDF).pages[PDF_PAGE - 1].extract_text()
    assert ROW in " ".join(text.split()), "Table 10 Southeast Florida row not found on the page"
    assert "Table 10." in text and "1851-2010" in text
    counts = [int(x) for x in ROW.split()[1:6]]
    rows = []
    for k in range(1, 6):
        n_exact = counts[k - 1]
        n_at_least = sum(counts[k - 1:])
        rows.append(dict(
            category=k, strikes_exact=n_exact, strikes_at_least=n_at_least, years=YEARS,
            annual_rate_exact=n_exact / YEARS, annual_rate_at_least=n_at_least / YEARS,
            return_period_at_least_years=round(YEARS / n_at_least, 1),
            region="Florida (Southeast), as defined in Appendix A of the memorandum",
            label="assumption (published historical frequency)",
            source_document="NOAA Technical Memorandum NWS NHC-6 (Blake, Landsea and Gibney, August 2011)",
            table="Table 10", url=URL, local_file=str(PDF.relative_to(paths.ROOT)),
            pdf_page=PDF_PAGE, printed_page=PRINTED_PAGE))
    t = pd.DataFrame(rows)
    t.to_csv(paths.HURRICANE_RATES_CSV, index=False)
    print(t[["category", "strikes_exact", "strikes_at_least", "annual_rate_at_least", "return_period_at_least_years"]])


if __name__ == "__main__":
    main()
