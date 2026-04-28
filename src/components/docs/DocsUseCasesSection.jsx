import React from 'react';

const BENEFITS = [
  {
    icon: 'map',
    title: 'Analyze Scale and Spatial Patterns of Resilience Infrastructure',
    text:
      'Allows users to examine the composition and spatial organization of blue, green, gray, and hybrid infrastructure to understand how different strategies are deployed across the region, including spatial configurations of clustering, hotspots, and complementarities.',
  },
  {
    icon: 'balance',
    title: 'Assess Gaps and Alignment of Resilience Investments',
    text:
      'Enables stakeholders to compare patterns of hazard exposure, social vulnerability, and resilience capacity with the geographic distribution of projects to identify underserved areas and evaluate whether investments align with community needs.',
  },
  {
    icon: 'hub',
    title: 'Enhance Interagency Coordination',
    text:
      'Provides municipal-county-regional-state agencies with a shared, scalable, integrated platform to visualize and track completed, ongoing, and planned resilience projects and identify synergies to support coordinated planning and implementation.',
  },
  {
    icon: 'account_balance',
    title: 'Support Evidence-Based, Equitable Investment Decisions',
    text:
      'Guides decision-makers through integrated data and modeling layers for strategic allocation of resources, enabling prioritization of interventions that address high-risk conditions while ensuring investments are directed toward communities with the greatest need.',
  },
  {
    icon: 'campaign',
    title: 'Increase Public Awareness and Engagement',
    text:
      'Presents complex resilience data through intuitive, map-based visualizations that make risk, vulnerability, and investment landscape more accessible to a broad audience, supporting greater public understanding, fostering transparency, and encouraging meaningful engagement of community leaders in resilience-building processes.',
  },
];

export default function DocsUseCasesSection() {
  return (
    <section id="use-cases" className="docs-section" aria-labelledby="docs-use-cases-heading">
      <h2 id="docs-use-cases-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Benefits and Use Cases</span>
      </h2>
      <p className="docs-section__lede">
        Five ways SCALE-R supports planners, agencies, researchers, and the
        public across the resilience-investment lifecycle.
      </p>

      <ol className="docs-stepper">
        {BENEFITS.map((benefit, idx) => (
          <li className="docs-stepper__item" key={benefit.title}>
            <span className="docs-stepper__marker" aria-hidden>
              {idx + 1}
            </span>
            <article className="docs-stepper__content">
              <div className="docs-stepper__head">
                <span className="docs-stepper__icon" aria-hidden>
                  <span className="material-symbols-outlined">{benefit.icon}</span>
                </span>
                <h3 className="docs-stepper__title">{benefit.title}</h3>
              </div>
              <p className="docs-stepper__text">{benefit.text}</p>
            </article>
          </li>
        ))}
      </ol>
    </section>
  );
}
