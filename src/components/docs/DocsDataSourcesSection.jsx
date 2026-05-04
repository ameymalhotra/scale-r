import React, { useState } from 'react';

/** Visible rows before “expand” per jurisdictional group */
const INITIAL_VISIBLE = {
  State: 2,
  Regional: 2,
  County: 5,
};

/** Collapsed row count per municipal subcategory (City of Miami, Miami Beach, other) */
const MUNICIPAL_INITIAL_VISIBLE = 3;

const DATA_SOURCES = [
  {
    level: 'State',
    items: [
      {
        source: 'FDEP Resilient Florida Grants',
        year: 2025,
        href:
          'https://floridadep.gov/rcp/resilient-florida-program/content/resilient-florida-grants',
      },
      {
        source: 'Florida Resilient Coastlines Program',
        year: 2022,
        href:
          'https://www.arcgis.com/apps/dashboards/1a12ee0edf834aaaa1cd82aa46c436b7',
      },
      {
        source: 'Florida Senate Local Funding Initiative Requests',
        year: 2026,
        href:
          'https://www.flsenate.gov/Session/Appropriations/FY2026-27/LocalFundingRequests',
      },
      {
        source: 'FDEP Coastal Permit Applications',
        year: 2018,
        href:
          'https://geodata.dep.state.fl.us/datasets/FDEP::coastal-permit-applications/explore?location=28.185250%2C-83.494800%2C6',
      },
      {
        source: 'Florida Adaptation Planning Guidebook',
        year: 2018,
        href:
          'https://floridadep.gov/sites/default/files/AdaptationPlanningGuidebook.pdf',
      },
    ],
  },
  {
    level: 'Regional',
    items: [
      {
        source:
          'South Florida Water Management District Sea Level Rise and Flood Resiliency Plan',
        year: 2025,
        href:
          'https://www.sfwmd.gov/our-work/sea-level-rise-and-flood-resiliency-plan',
      },
      {
        source:
          'Southeast Florida Regional Climate Change Compact Regional Climate Action Plan',
        year: 2022,
        href: 'https://southeastfloridaclimatecompact.org/recommendations/',
      },
      {
        source: 'Southeast Florida Priority Climate Action Plan',
        year: 2024,
        href:
          'https://www.epa.gov/system/files/documents/2024-03/southeast-florida-priority-climate-action-plan.pdf',
      },
      {
        source:
          'Central and Southern Florida Flood Resiliency Study',
        year: 2022,
        href:
          'https://www.sfwmd.gov/our-work/central-and-southern-florida-flood-resiliency-study',
      },
      {
        source: 'Strategic Regional Policy Plan',
        year: 2024,
        href: 'https://sfregionalcouncil.org/portfolio-item/srpp/',
      },
    ],
  },
  {
    level: 'County',
    items: [
      {
        source: 'Local Mitigation Strategy Plan',
        year: 2025,
        href:
          'https://www.miamidade.gov/global/emergency/local-mitigation-strategy.page',
      },
      {
        source: 'Resilient305 Strategy',
        year: 2019,
        href: 'https://resilient305.com/yearoneupdate/',
      },
      {
        source: 'Miami-Dade County Sea Level Rise Strategy',
        year: 2021,
        href:
          'https://miami-dade-county-sea-level-rise-strategy-draft-mdc.hub.arcgis.com/',
      },
      {
        source: 'Little River Adaptation Plan',
        year: 2022,
        href:
          'https://adaptation-action-area-in-little-river-mdc.hub.arcgis.com/',
      },
      {
        source:
          'Miami-Dade Transportation Planning Organization Climate Resilience Study',
        year: 2023,
        href:
          'https://miamidadetpo.org/library/studies/mdtpo-climate-resiliency-study-final-report-223-06.pdf',
      },
      {
        source: 'Miami-Dade County Stormwater Master Plan',
        year: 2021,
        href:
          'https://documents.miamidade.gov/mayor/memos/07.31.23-Report-on-the-Countys-Stormwater-Master-Plan-Directive-No-221568.pdf',
      },
      {
        source:
          'Miami-Dade County Beach Erosion Control Master Plan',
        year: 2025,
        href:
          'https://www.miamidade.gov/global/environment/ecosystems/beach-renourishment.page',
      },
      {
        source: 'Miami-Dade Urban Forestry Plan',
        year: 2025,
        href:
          'https://www.miamidade.gov/resources/environment/documents/urban-forestry-plan.pdf',
      },
      {
        source:
          'Miami-Dade Back Bay Coastal Storm Risk Management Feasibility Study',
        year: 2024,
        href:
          'https://www.saj.usace.army.mil/MiamiDadeBackBayCSRMFeasibilityStudy/',
      },
      {
        source: 'Countywide Resilience Hub Network Strategy',
        year: 2024,
        href:
          'https://storymaps.arcgis.com/stories/9f3298ff03034dc580f2f0b4f0190f4e',
      },
      {
        source: 'Extreme Heat Action Plan',
        year: 2022,
        href:
          'https://www.miamidade.gov/resources/environment/documents/2022-heat-action-plan.pdf',
      },
      {
        source:
          'The Strategic Miami Area Rapid Transit (SMART) Plan',
        year: 2016,
        href:
          'https://www.miamidade.gov/global/transportation/corridor-plans.page',
      },
      {
        source: 'Miami-Dade Press Releases',
        year: 2026,
        href:
          'https://www.miamidade.gov/global/navigation/release-index.page',
      },
    ],
  },
  {
    level: 'Municipal',
    subcategories: [
      {
        id: 'city-of-miami',
        label: 'City of Miami',
        items: [
      {
        source: 'Miami Forever Climate Ready',
        year: 2020,
        href:
          'https://www.miami.gov/My-Government/Climate-Change-in-the-City-of-Miami/Climate-Change-Action/MiamiForeverClimateReady',
      },
      {
        source: 'Miami Forever Bond',
        year: 2024,
        href:
          'https://www.miami.gov/My-Government/Departments/Office-of-Capital-Improvements/Miami-Forever-Bond',
      },
      {
        source: 'Miami Forever Bond Capital Improvement Projects',
        year: 2019,
        href:
          'https://datahub-miamigis.opendata.arcgis.com/maps/3fed35b5a6e44af8a8c34f82b1aa838f/explore?location=25.776200%2C-80.242750%2C12',
      },
      {
        source:
          'Miami Forever Carbon Neutral Greenhouse Gas Reduction Plan',
        year: 2021,
        href:
          'https://www.miami.gov/My-Government/Climate-Change-in-the-City-of-Miami/Climate-Change-Action/MiamiForever-Carbon-Neutral',
      },
      {
        source:
          'City of Miami Comprehensive Stormwater Master Plan',
        year: 2021,
        href:
          'https://www.miami.gov/My-Government/Departments/Resilience-and-Public-Works/Stormwater-Master-Plan',
      },
      {
        source: 'Miami Forever Climate Ready: Extreme Heat Plan',
        year: 2023,
        href:
          'https://www.miami.gov/My-Government/Climate-Change-in-the-City-of-Miami/Climate-Change-Action/ExtremeHeatPlan',
      },
      {
        source: 'City of Miami Capital Improvements Projects',
        year: 2026,
        href:
          'https://www.miami.gov/My-Government/Departments/Office-of-Capital-Improvements/Capital-Improvements-Projects-Construction-Notices-Per-District',
      },
      {
        source: 'Resilience and Public Works Projects Per District',
        year: 2026,
        href:
          'https://www.miami.gov/My-Government/Departments/Resilience-and-Public-Works/Resilience-and-Public-Works-Projects-Per-District',
      },
        ],
      },
      {
        id: 'city-of-miami-beach',
        label: 'City of Miami Beach',
        items: [
      {
        source: 'Miami Beach Sea Level Rise Adaptation Plan',
        year: 2025,
        href:
          'https://www.mbrisingabove.com/wp-content/uploads/Adaptation-Plan-FINAL.pdf',
      },
      {
        source: 'Miami Beach Stormwater Modeling and Master Plan',
        year: 2024,
        href:
          'https://www.miamibeachfl.gov/residents/neighborhood-affairs-division/active-projects/other/stormwater-masterplan/',
      },
      {
        source: 'Go Miami Beach General Obligation Bond',
        year: 2022,
        href: 'https://www.gombinfo.com/',
      },
      {
        source: 'Miami Beach Urban Forestry Master Plan',
        year: 2020,
        href:
          'https://www.mbrisingabove.com/wp-content/uploads/2020-CMB-UFMP-Final-compressed.pdf',
      },
      {
        source: 'Miami Beach Strategic Plan Update',
        year: 2023,
        href:
          'https://www.mbrisingabove.com/wp-content/uploads/FY-2024-Strategic-Plan.pdf',
      },
      {
        source: 'Miami Beach Citywide Construction Project Map',
        year: 2026,
        href:
          'https://www.miamibeachfl.gov/city-hall/cip/active-projects/',
      },
      {
        source: 'Cutler Bay Local Mitigation Strategy',
        year: 2024,
        href:
          'https://www.cutlerbay-fl.gov/sites/default/files/fileattachments/public_works/page/2871/2024_lms_annual_report.pdf',
      },
      {
        source: 'Cutler Bay Flood Mitigation Plan',
        year: 2021,
        href:
          'https://www.cutlerbay-fl.gov/sites/default/files/fileattachments/public_works/page/2871/cutler_bay_flood_mitigation_plan_fmp_update.pdf',
      },
      {
        source: 'Cutler Bay Stormwater Master Plan',
        year: 2024,
        href:
          'https://www.cutlerbay-fl.gov/townmanager/page/town-master-plans',
      },
      {
        source: 'Cutler Bay Green Master Plan',
        year: 2018,
        href:
          'https://www.cutlerbay-fl.gov/sites/default/files/fileattachments/town_manager/page/2211/final_green_master_plan_2018.pdf',
      },
      {
        source: 'City of Coral Gables Sustainability Management Plan',
        year: 2015,
        href:
          'https://www.coralgables.com/department/sustainability/sustainability-management-plan',
      },
      {
        source: 'Coral Gables Capital Improvement Plan',
        year: 2026,
        href:
          'https://www.coralgables.com/sites/default/files/2026-03/Capital-Improvement-Program-2026-2030-CH.pdf',
      },
      {
        source:
          'City of Doral Citywide Integrated Sustainability Plan',
        year: 2024,
        href:
          'https://www.cityofdoral.com/files/assets/city/v/1/departments/public-works/green-docs/doral_citywide_integrated_sustainability_plan_final.pdf',
      },
      {
        source:
          'City of Doral Comprehensive Emergency Management Plan',
        year: 2022,
        href:
          'https://www.cityofdoral.com/files/assets/city/v/1/departments/police/emergency-docs/city-of-doral-cemp-2022-opt.pdf',
      },
      {
        source: 'City of North Miami Beach Stormwater Master Plan',
        year: 2020,
        href: 'https://www.citynmb.com/437/Storm-Water',
      },
      {
        source:
          'City of North Miami Citizens Guide to Sustainability and Resiliency',
        year: 2020,
        href: 'https://www.northmiamifl.gov/1406/Sustainability',
      },
      {
        source:
          'City of Miami Springs Vulnerability and Resiliency Assessment and Adaptation Action Plan',
        year: 2025,
        href:
          'https://www.miamisprings-fl.gov/citymanager/page/vulnerability-and-resiliency-assessment-and-adaptation-action-plan',
      },
      {
        source: 'Town of Surfside Capital Improvement Projects',
        year: 2025,
        href:
          'https://www.townofsurfsidefl.gov/redirects/capital-improvement-projects',
      },
      {
        source: 'City of Homestead Capital Improvement Projects',
        year: 2025,
        href:
          'https://www.homesteadfl.gov/638/Capital-Improvement-Projects',
      },
      {
        source: 'Village of Pinecrest Stormwater Master Plan',
        year: 2015,
        href:
          'https://www.pinecrest-fl.gov/Government/Manager/Capital-Improvement-Projects/Stormwater-Master-Plan-Implementation',
      },
      {
        source: 'South Miami Stormwater Management Plan',
        year: 2021,
        href: 'https://www.southmiamifl.gov/322/Stormwater-Management',
      },
      {
        source: 'South Miami Budget Reports',
        year: 2025,
        href: 'https://www.southmiamifl.gov/685/Budget-Reports',
      },
      {
        source: 'Miami Lakes Projects Directory',
        year: 2025,
        href:
          'https://www.miamilakes-fl.gov/our-government/project-directory/',
      },
      {
        source:
          'Key Biscayne “Elevating Our Island Paradise” Dashboard',
        year: 2026,
        href:
          'https://keybiscayne.fl.gov/elevating_our_island_paradise/index.php',
      },
      {
        source: 'Village of Palmetto Bay Stormwater Master Plan',
        year: 2020,
        href:
          'https://www.palmettobay-fl.gov/1236/Stormwater-Master-Plan',
      },
      {
        source: 'Village of Palmetto Bay Resilience Action Plan',
        year: 2024,
        href:
          'https://www.palmettobay-fl.gov/1500/Resilience-Action-Plan',
      },
        ],
      },
    ],
  },
];

function SourceDataRow({ item, id }) {
  return (
    <tr {...(id ? { id } : {})}>
      <td className="docs-sources-table__source">
        <span className="docs-sources-table__source-text">{item.source}</span>
        <a
          href={item.href}
          className="docs-sources-table__link"
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open source: ${item.source}`}
        >
          <span
            className="material-symbols-outlined docs-sources-table__link-icon"
            aria-hidden
          >
            arrow_outward
          </span>
        </a>
      </td>
      <td className="docs-sources-table__year">
        <span className="docs-chip">{item.year}</span>
      </td>
    </tr>
  );
}

export default function DocsDataSourcesSection() {
  const [expandedByLevel, setExpandedByLevel] = useState(() =>
    Object.fromEntries(
      DATA_SOURCES.filter((g) => Array.isArray(g.items)).map((g) => [
        g.level,
        false,
      ]),
    ),
  );

  const [municipalSubExpanded, setMunicipalSubExpanded] = useState(() =>
    Object.fromEntries(
      DATA_SOURCES.find((g) => g.level === 'Municipal').subcategories.map(
        (sub) => [sub.id, false],
      ),
    ),
  );

  const toggleGroup = (level) => {
    setExpandedByLevel((prev) => ({
      ...prev,
      [level]: !prev[level],
    }));
  };

  const toggleMunicipalSub = (id) => {
    setMunicipalSubExpanded((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <section
      id="data-sources"
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

      <div className="docs-sources-table-wrap" role="region" aria-label="Data sources table">
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
          {DATA_SOURCES.map((group) => {
            if (group.subcategories) {
              const totalCount = group.subcategories.reduce(
                (sum, sub) => sum + sub.items.length,
                0,
              );

              return (
                <tbody key={group.level} id={`docs-sources-group-${group.level}`}>
                  <tr className="docs-sources-table__group">
                    <th colSpan={2} scope="colgroup">
                      {group.level}
                      <span className="docs-sources-table__group-count">
                        {totalCount}
                      </span>
                    </th>
                  </tr>
                  {group.subcategories.map((sub) => {
                    const initial = MUNICIPAL_INITIAL_VISIBLE;
                    const expanded = municipalSubExpanded[sub.id];
                    const { items } = sub;
                    const hasMore = items.length > initial;
                    const visibleItems =
                      expanded || !hasMore ? items : items.slice(0, initial);
                    const hiddenCount = items.length - initial;

                    return (
                      <React.Fragment key={sub.id}>
                        {sub.label ? (
                          <tr className="docs-sources-table__subgroup">
                            <th
                              colSpan={2}
                              scope="colgroup"
                              className="docs-sources-table__subgroup-heading"
                            >
                              {sub.label}
                            </th>
                          </tr>
                        ) : null}
                        {visibleItems.map((item, idx) => (
                          <SourceDataRow
                            key={`${sub.id}-${idx}-${item.source}`}
                            item={item}
                            id={idx === 0 ? `panel-municipal-${sub.id}` : undefined}
                          />
                        ))}
                        {hasMore ? (
                          <tr className="docs-sources-table__expand-row">
                            <td colSpan={2}>
                              <button
                                type="button"
                                className="docs-sources-group-toggle"
                                onClick={() => toggleMunicipalSub(sub.id)}
                                aria-expanded={expanded}
                                aria-controls={`panel-municipal-${sub.id}`}
                              >
                                <span
                                  className="material-symbols-outlined"
                                  aria-hidden
                                >
                                  {expanded ? 'expand_less' : 'expand_more'}
                                </span>
                                {expanded
                                  ? 'Show fewer'
                                  : `Show ${hiddenCount} more`}
                              </button>
                            </td>
                          </tr>
                        ) : null}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              );
            }

            const initial = INITIAL_VISIBLE[group.level] ?? 3;
            const expanded = expandedByLevel[group.level];
            const { items } = group;
            const hasMore = items.length > initial;
            const visibleItems =
              expanded || !hasMore ? items : items.slice(0, initial);
            const hiddenCount = items.length - initial;

            return (
              <tbody key={group.level} id={`docs-sources-group-${group.level}`}>
                <tr className="docs-sources-table__group">
                  <th colSpan={2} scope="colgroup">
                    {group.level}
                    <span className="docs-sources-table__group-count">
                      {group.items.length}
                    </span>
                  </th>
                </tr>
                {visibleItems.map((item, idx) => (
                  <SourceDataRow
                    key={`${group.level}-${idx}-${item.source}`}
                    item={item}
                  />
                ))}
                {hasMore ? (
                  <tr className="docs-sources-table__expand-row">
                    <td colSpan={2}>
                      <button
                        type="button"
                        className="docs-sources-group-toggle"
                        onClick={() => toggleGroup(group.level)}
                        aria-expanded={expanded}
                        aria-controls={`docs-sources-group-${group.level}`}
                      >
                        <span className="material-symbols-outlined" aria-hidden>
                          {expanded ? 'expand_less' : 'expand_more'}
                        </span>
                        {expanded ? 'Show fewer' : `Show ${hiddenCount} more`}
                      </button>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            );
          })}
        </table>
      </div>
    </section>
  );
}
