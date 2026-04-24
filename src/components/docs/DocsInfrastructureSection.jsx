import React from 'react';

const INFRASTRUCTURE_TYPES = [
  {
    icon: 'water',
    label: 'Blue Infrastructure',
    accent: '#0e7aad',
    text:
      'Blue infrastructure includes natural and engineered water systems that manage flooding, improve water quality, and support aquatic ecosystems. These systems play a key role in sustainable water management and reducing pressure on traditional infrastructure.',
    examples: [
      'Stormwater retention ponds',
      'Canals and drainage networks',
      'Wetland restoration projects',
      'Coastal water management systems',
    ],
  },
  {
    icon: 'foundation',
    label: 'Grey Infrastructure',
    accent: '#52606b',
    text:
      'Grey infrastructure refers to traditional engineered systems built with materials like concrete and steel to manage urban services and environmental challenges. While essential for large-scale infrastructure, these systems can have environmental trade-offs.',
    examples: [
      'Seawalls and flood barriers',
      'Stormwater pipes and drainage systems',
      'Roads and transportation networks',
      'Water treatment facilities',
    ],
  },
  {
    icon: 'park',
    label: 'Green Infrastructure',
    accent: '#005030',
    text:
      'Green infrastructure uses vegetation, soil, and natural processes to improve environmental quality and enhance resilience. These solutions help cities adapt to climate impacts such as heat, flooding, and extreme weather while promoting sustainability.',
    examples: [
      'Urban tree canopies and green spaces',
      'Green roofs and rain gardens',
      'Bioswales and permeable surfaces',
      'Urban parks and ecological restoration areas',
    ],
  },
  {
    icon: 'hub',
    label: 'Hybrid Infrastructure',
    accent: '#f47321',
    text:
      'Hybrid infrastructure combines elements of blue, green, and grey systems to deliver more adaptive and sustainable solutions. These approaches balance engineered reliability with environmental benefits.',
    examples: [
      'Living shorelines (natural vegetation + structural support)',
      'Green stormwater systems integrated with drainage networks',
      'Parks designed for flood storage',
      'Multi-functional coastal protection systems',
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
          Infrastructure Types
        </span>
      </h2>
      <p className="docs-section__lede">
        Resilience projects are categorized into blue, green, grey, and hybrid
        infrastructure to reflect how different systems reduce risk and
        strengthen community resilience. This classification helps identify
        spatial patterns, compare strategies across locations, and highlight
        gaps—such as over-reliance on engineered solutions or underuse of
        nature-based approaches.
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
