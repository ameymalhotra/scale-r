import React from 'react';

const HORIZONS = [
  {
    tag: 'Limitation',
    icon: 'hub',
    title: 'Fragmented Climate Governance & Data',
    text:
      'The primary limitation arises from the complex climate governance structure in Miami-Dade County, which includes 34 municipalities, extensive unincorporated areas under county jurisdiction, and multiple regional agencies responsible for water, transportation, and planning. This fragmented institutional landscape results in data being distributed across disparate systems, making it difficult to systematically collect, standardize, and align project information within a consistent metadata framework.',
    orangeAccent: false,
  },
  {
    tag: 'Limitation',
    icon: 'autorenew',
    title: 'Dynamic Data & Continuous Updates',
    text:
      'Another key challenge is the dynamic nature of resilience, which necessitates continuous updating of project data to ensure accuracy and relevance in decision-support processes. Addressing this requires developing real-time data integration and feedback mechanisms between agencies and the platform to enable timely updates and improve data reliability.',
    orangeAccent: true,
  },
  {
    tag: 'Future Research',
    icon: 'insights',
    title: 'Scenario-Based Resilience Modeling',
    text:
      'While the SCALE-R platform captures a wide range of projects and interventions, its modeling and scenario-based planning capabilities remain foundational. Addressing this gap represents an important direction for future research and methodological advancement. In particular, modeling how resilience investments influence established risk profiles can provide a pathway to move beyond static assessments toward a more dynamic understanding of how interventions reshape risk conditions and inform adaptive responses and decision-making.',
    orangeAccent: false,
  },
];

export default function DocsLimitationsSection() {
  return (
    <section
      id="limitations"
      className="docs-section docs-section--limitations-bleed"
      aria-labelledby="docs-limitations-heading"
    >
      <h2 id="docs-limitations-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">
          Limitations &amp; Future Research
        </span>
      </h2>
      <p className="docs-section__lede">
        Institutional complexity, evolving conditions, and advancing analytical needs
        shape how SCALE-R should grow alongside regional resilience planning.
      </p>

      <ul className="docs-horizon-stack" role="list">
        {HORIZONS.map((item, idx) => {
          const indexLabel = String(idx + 1).padStart(2, '0');
          return (
            <li
              key={item.title}
              className={
                item.orangeAccent
                  ? 'docs-horizon-card docs-horizon-card--research'
                  : 'docs-horizon-card'
              }
            >
              <span className="docs-horizon-card__numeral" aria-hidden>
                {indexLabel}
              </span>
              <div className="docs-horizon-card__head">
                <span className="docs-horizon-card__medallion" aria-hidden>
                  <span className="material-symbols-outlined">{item.icon}</span>
                </span>
                <div className="docs-horizon-card__meta">
                  <span className="docs-horizon-card__tag">{item.tag}</span>
                  <h3 className="docs-horizon-card__title">{item.title}</h3>
                </div>
              </div>
              <span className="docs-horizon-card__rule" aria-hidden />
              <p className="docs-horizon-card__text">{item.text}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
