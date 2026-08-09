import React from 'react';

const INFRASTRUCTURE_TYPES = [
  {
    icon: 'water',
    label: 'Blue',
    accent: '#0e7aad',
    text:
      'Blue infrastructure encompasses natural and engineered water-based systems that mitigate flooding, support adaptation to sea-level rise, improve water quality, and sustain diverse aquatic ecosystems. These interventions advance sustainable water management while alleviating climate-related pressures on coastal environments.',
    examples: [
      'Wetland restoration projects',
      'Stormwater detention systems',
      'Canals and drainage networks',
      'Coastal water management systems',
    ],
  },
  {
    icon: 'park',
    label: 'Green',
    accent: '#005030',
    text:
      'Green infrastructure integrates vegetation, soils, and ecological processes to mitigate urban heat, manage stormwater, improve air and water quality, and support biodiversity. These solutions enhance urban resilience while advancing sustainable development across built and natural environments.',
    examples: [
      'Mangrove restoration',
      'Urban tree canopy and park systems',
      'Green roofs and permeable surfaces',
      'Bioswales and rain gardens',
      'Ecological restoration of endangered lands',
    ],
  },
  {
    icon: 'foundation',
    label: 'Gray',
    accent: '#52606b',
    text:
      'Gray infrastructure comprises conventional engineered systems constructed with materials such as concrete and steel to deliver essential urban services, including stormwater conveyance, flood control, and transportation. While critical for reliability at defined performance thresholds, these systems often entail environmental trade-offs that reduce ecological function.',
    examples: [
      'Seawalls and flood barriers',
      'Stormwater pipes and drainage systems',
      'Elevated roads and transportation networks',
      'Water treatment and pumping facilities',
    ],
  },
  {
    icon: 'hub',
    label: 'Hybrid',
    accent: '#f47321',
    text:
      'Hybrid infrastructure integrates elements of blue, green, and gray systems to deliver adaptive, multi-functional solutions. These approaches combine engineered reliability with ecosystem-based processes to enhance resilience, optimize performance, and provide co-benefits across environmental and urban systems.',
    examples: [
      'Living shorelines',
      'Green-gray drainage systems',
      'Elevated green corridors',
      'Parks designed for flood storage',
      'Permeable pavement systems',
    ],
  },
];

export default function DocsInfrastructureSection() {
  return (
    <section
      id="infrastructure-types"
      className="docs-section docs-section--infra"
      aria-labelledby="docs-infra-heading"
    >
      <h2 id="docs-infra-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">
          Infrastructure Type
        </span>
      </h2>
      <p className="docs-section__lede">
        Resilience projects are categorized into blue, green, gray, and hybrid
        infrastructure to reflect how different systems reduce risk and
        strengthen community resilience. This classification—adapted from the{' '}
        <a
          className="docs-section__lede-link"
          href="https://www.ipcc.ch/report/ar6/wg2/downloads/outreach/IPCC_AR6_WGII_SummaryForAll_Adaptation.pdf"
          target="_blank"
          rel="noopener noreferrer"
        >
          IPCC Sixth Assessment Report
        </a>
        —helps the users to categorize and compare strategies across the
        county-wide geography and highlights which strategies are preferred under
        varying risk and resilience contexts.
      </p>

      <ul className="docs-infra-rows" role="list">
        {INFRASTRUCTURE_TYPES.map((tile) => (
          <li
            className="docs-infra-row"
            key={tile.label}
            style={{ '--infra-accent': tile.accent }}
          >
            <span className="docs-infra-row__icon" aria-hidden>
              <span className="material-symbols-outlined">{tile.icon}</span>
            </span>
            <div className="docs-infra-row__body">
              <h3 className="docs-infra-row__title">{tile.label}</h3>
              <p className="docs-infra-row__text">{tile.text}</p>
              <p className="docs-infra-row__examples-label">Examples</p>
              <div className="docs-infra-row__pills">
                {tile.examples.map((example) => (
                  <span className="docs-infra-pill" key={example}>
                    {example}
                  </span>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
