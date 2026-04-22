import React from 'react';

const USE_CASES = [
  {
    kicker: 'Planner',
    title: 'Prioritizing flood mitigation investment',
    persona: 'City resilience officer preparing an LMS update.',
    scenario:
      'Overlays flood exposure, social sensitivity, and existing project locations to surface tracts with high need but low active investment.',
    outcome:
      'A ranked shortlist of neighborhoods for the next round of drainage, elevation, and green-infrastructure grants.',
  },
  {
    kicker: 'Researcher',
    title: 'Cross-scale resilience comparison',
    persona: 'Academic team studying adaptation across Greater Miami.',
    scenario:
      'Compares tract, municipality, and county-level scores across hazard families to test how local policies track with measured resilience outcomes.',
    outcome:
      'Exportable tables and maps for peer-reviewed analysis and policy briefs.',
  },
  {
    kicker: 'Community',
    title: 'Neighborhood advocacy & planning',
    persona: 'CBO leader preparing a testimony packet.',
    scenario:
      'Filters the map to a single neighborhood, combining hazard layers with pending projects to ground community concerns in shared data.',
    outcome:
      'A one-page evidence brief used in public comment and council engagement.',
  },
];

export default function DocsUseCasesSection() {
  return (
    <section
      id="use-cases"
      className="docs-section docs-section--pill"
      aria-labelledby="docs-use-cases-heading"
    >
      <h2 id="docs-use-cases-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Use Cases</span>
      </h2>
      <p className="docs-section__lede">
        Three illustrative scenarios for how planners, researchers, and
        community stakeholders use SCALE-R day-to-day.
      </p>

      <div className="docs-usecase-grid">
        {USE_CASES.map((uc, idx) => (
          <article className="docs-usecase-card" key={uc.title}>
            <span className="docs-usecase-card__kicker">
              <span className="docs-usecase-card__num" aria-hidden>
                {idx + 1}
              </span>
              {uc.kicker}
            </span>
            <h3 className="docs-usecase-card__title">{uc.title}</h3>
            <p className="docs-usecase-card__persona">{uc.persona}</p>
            <p className="docs-usecase-card__scenario">{uc.scenario}</p>
            <p className="docs-usecase-card__outcome">
              <span className="docs-usecase-card__outcome-label">Outcome</span>
              {uc.outcome}
            </p>
          </article>
        ))}
      </div>

      <span className="docs-placeholder" aria-hidden>
        Placeholder copy · Use Cases
      </span>
    </section>
  );
}
