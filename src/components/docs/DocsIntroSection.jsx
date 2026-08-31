import React from 'react';

const INTRO_PARAGRAPHS = [
  'Resilience planning and decision-making are increasingly critical as climate risks to ecosystems, community health, and urban infrastructure intensify. Miami-Dade County stands among the most vulnerable regions in the United States, facing a growing spectrum of coastal hazards, including sea-level rise, flooding, and extreme weather events.',
  'SCALE-R responds to this challenge by advancing innovative decision-support tools co-developed with planners, policymakers, and communities to integrate and visualize resilience strategies across scales and agencies. The platform maps 1,664 projects representing over $22 billion in investments, creating an unprecedented view of the region’s resilience landscape. By integrating project-level data with multiple risk indices in an interactive geospatial environment, SCALE-R reveals how infrastructure interventions align with patterns of social vulnerability and physical exposure.',
  'The SCALE-R dashboard is intended to support communities in identifying investment priorities, improving coordination, and navigating informed pathways toward a more resilient future.',
];

export default function DocsIntroSection() {
  return (
    <section
      id="introduction"
      className="docs-section"
      aria-labelledby="docs-intro-heading"
    >
      <h2 id="docs-intro-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Introduction</span>
      </h2>
      <div className="docs-prose">
        {INTRO_PARAGRAPHS.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </section>
  );
}
