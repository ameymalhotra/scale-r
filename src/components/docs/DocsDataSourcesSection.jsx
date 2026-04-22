import React, { useRef, useState } from 'react';

const DATA_SOURCES = [
  {
    level: 'State',
    items: [
      { source: 'Florida Adaptation Planning Guidebook', year: 2018 },
      { source: 'Florida Senate Local Funding Initiative Requests', year: 2025 },
      { source: 'FDEP Resilient Florida Grants', year: 2022 },
      { source: 'Florida Resilient Coastlines Database', year: 2018 },
      { source: 'FDEP Coastal Permit Applications', year: 2007 },
    ],
  },
  {
    level: 'Regional',
    items: [
      {
        source:
          'South Florida Water Management District Sea Level Rise and Flood Resiliency Plan',
        year: 2025,
      },
    ],
  },
  {
    level: 'County',
    items: [
      { source: 'Miami-Dade County Stormwater Master Plan', year: 2021 },
      {
        source: 'Miami-Dade County Beach Erosion Control Master Plan',
        year: 2006,
      },
      { source: 'Miami-Dade Press Releases', year: 2025 },
      { source: 'Urban Forestry Report', year: 2025 },
      { source: 'Miami-Dade County SMART Plan', year: 2016 },
      { source: 'Little River Adaptation Plan', year: 2022 },
      { source: 'Local Mitigation Strategy Plan', year: 2025 },
      { source: 'Local Mitigation Strategy Dashboard', year: 2026 },
    ],
  },
  {
    level: 'Municipal',
    items: [
      { source: 'Miami Beach Strategic Plan Update', year: 2023 },
      { source: 'Stormwater Master Plan (Cutler Bay)', year: 2024 },
      {
        source: 'Key Biscayne “Elevating Our Island Paradise” Dashboard',
        year: 2025,
      },
      { source: 'Palmetto Bay Stormwater Master Plan', year: 2020 },
      { source: 'Village of Pinecrest Stormwater Master Plan', year: 2015 },
      { source: 'South Miami Stormwater Management Plan', year: 2012 },
      { source: 'South Miami Budget Reports', year: 2025 },
      { source: 'Coral Gables Capital Improvement Plan', year: 2024 },
      { source: 'Miami Lakes Projects Dashboard', year: 2025 },
      { source: 'NoMi Comprehensive Plan', year: 2023 },
      { source: 'NBV100 Master Plan', year: 2020 },
      { source: 'Town of Surfside Capital Improvement Projects', year: 2025 },
      { source: 'City of Homestead Capital Improvement Projects', year: 2025 },
      { source: 'City of Miami Stormwater Master Plan', year: 2024 },
      { source: 'City of Miami Capital Improvement Projects', year: 2025 },
      { source: 'GO Miami Beach', year: 2022 },
      { source: 'City of Miami Beach Active Projects Webpage', year: 2025 },
      { source: 'Miami Forever Climate Ready Strategy', year: 2020 },
      { source: 'Miami Forever Carbon Neutral', year: 2021 },
      { source: 'Miami-Dade Public Works by District Webpage', year: 2025 },
      { source: 'Miami Forever Bond', year: 2024 },
    ],
  },
];

const TOTAL_COUNT = DATA_SOURCES.reduce(
  (acc, group) => acc + group.items.length,
  0,
);

const WRAP_ID = 'docs-sources-wrap';

export default function DocsDataSourcesSection() {
  const [expanded, setExpanded] = useState(false);
  const sectionRef = useRef(null);

  const toggle = () => {
    const nextExpanded = !expanded;
    setExpanded(nextExpanded);

    if (!nextExpanded && sectionRef.current) {
      const target = sectionRef.current;
      const headerOffset = 96;
      const top =
        target.getBoundingClientRect().top + window.pageYOffset - headerOffset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  };

  return (
    <section
      id="data-sources"
      ref={sectionRef}
      className="docs-section"
      aria-labelledby="docs-data-sources-heading"
    >
      <h2 id="docs-data-sources-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Data Sources</span>
      </h2>
      <p className="docs-section__lede">
        SCALE-R compiles resilience project data from state, regional, county,
        and municipal sources, assembling a comprehensive, multi-level view of
        resilience planning across Miami-Dade County.
      </p>

      <div
        id={WRAP_ID}
        className="docs-sources-wrap"
        data-expanded={expanded ? 'true' : 'false'}
        role="region"
        aria-label="Data sources table"
      >
        <table className="docs-sources-table">
          <caption className="visually-hidden">
            Data sources grouped by jurisdictional level
          </caption>
          <thead>
            <tr>
              <th scope="col">Data Source</th>
              <th scope="col" className="docs-sources-table__year">
                Year
              </th>
            </tr>
          </thead>
          {DATA_SOURCES.map((group) => (
            <tbody key={group.level}>
              <tr className="docs-sources-table__group">
                <th colSpan={2} scope="colgroup">
                  {group.level}
                  <span className="docs-sources-table__group-count">
                    {group.items.length}
                  </span>
                </th>
              </tr>
              {group.items.map((item) => (
                <tr key={`${group.level}-${item.source}`}>
                  <td>{item.source}</td>
                  <td className="docs-sources-table__year">
                    <span className="docs-chip">{item.year}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>

        <div className="docs-sources-wrap__fade" aria-hidden />
      </div>

      <button
        type="button"
        className="docs-sources-toggle"
        onClick={toggle}
        aria-expanded={expanded}
        aria-controls={WRAP_ID}
      >
        <span className="material-symbols-outlined" aria-hidden>
          {expanded ? 'expand_less' : 'expand_more'}
        </span>
        {expanded ? 'Show fewer' : `Show all ${TOTAL_COUNT} sources`}
      </button>
    </section>
  );
}
