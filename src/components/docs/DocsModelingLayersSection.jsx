import React from 'react';

const MODELING_LAYERS = [
  {
    title: 'Exposure layer',
    text:
      'Combines hazard surfaces (flood, heat, surge, wind) with infrastructure and population geometries to quantify who and what is at risk.',
    chips: ['FEMA NRI', 'NOAA', 'Census'],
  },
  {
    title: 'Sensitivity layer',
    text:
      'Adds socioeconomic and health sensitivity indicators so that two places with equal exposure can still be distinguished by expected harm.',
    chips: ['CDC PLACES', 'ACS', 'HUD'],
  },
  {
    title: 'Adaptive capacity layer',
    text:
      'Institutional, financial, and infrastructural resources available to absorb, respond to, and recover from hazard events.',
    chips: ['LMS projects', 'Community plans'],
  },
  {
    title: 'Composite resilience index',
    text:
      'Normalizes and aggregates the three layers above into a single tract-level score used for ranking and map visualization.',
    chips: ['Tract-level', 'Normalized'],
  },
];

export default function DocsModelingLayersSection() {
  return (
    <section
      id="modeling-layers"
      className="docs-section docs-section--gray"
      aria-labelledby="docs-modeling-heading"
    >
      <h2 id="docs-modeling-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">
          Supporting Modeling Layers
        </span>
      </h2>
      <p className="docs-section__lede">
        The dashboard composes four modeling layers in sequence. Each layer can
        also be inspected on its own, so users can see how a tract scores along
        any single dimension.
      </p>

      <ol className="docs-layers">
        {MODELING_LAYERS.map((layer, idx) => (
          <li className="docs-layer-row" key={layer.title}>
            <div className="docs-layer-row__num" aria-hidden>
              {idx + 1}
            </div>
            <div className="docs-layer-row__body">
              <h3 className="docs-layer-row__title">{layer.title}</h3>
              <p className="docs-layer-row__text">{layer.text}</p>
              {layer.chips && layer.chips.length > 0 ? (
                <div className="docs-layer-row__chips">
                  {layer.chips.map((chip) => (
                    <span className="docs-chip" key={chip}>
                      {chip}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </li>
        ))}
      </ol>

      <span className="docs-placeholder" aria-hidden>
        Placeholder copy · Modeling Layers
      </span>
    </section>
  );
}
