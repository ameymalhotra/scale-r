import React from 'react';

const BACKGROUND_PARAGRAPHS = [
  'Resilience decision-support tools have advanced significantly over the past decade, synthesizing and modeling large, complex datasets to inform risk assessment and strategic planning. These tools typically provide multidimensional analyses that integrate climatic patterns, environmental conditions, social vulnerability, public health, and critical infrastructure systems.',
  'However, most existing approaches primarily assess risk in isolation, with limited attention to how ongoing resilience investments—implemented by diverse actors across multiple governance levels—are actively shaping those risks. As a result, they offer an incomplete picture of how communities are adapting in practice.',
  'Explicitly modeling risks in relation to adaptation and mitigation interventions offers an alternative paradigm for evaluating community resilience. By linking hazards, vulnerabilities, and investments, this approach enables a more dynamic understanding of how resilience strategies reduce exposure, strengthen capacity, and inform future decision-making.',
];

const PULLQUOTE =
  'Addressing climate challenges requires more than identifying risks—it demands integrated modeling of how physical and social vulnerabilities intersect with public investments in adaptation infrastructure, transforming uncertainty into preparedness.';

export default function DocsBackgroundSection() {
  return (
    <section
      id="background"
      className="docs-section docs-section--gray"
      aria-labelledby="docs-background-heading"
    >
      <h2 id="docs-background-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Background</span>
      </h2>
      <div className="docs-prose">
        {BACKGROUND_PARAGRAPHS.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
      <blockquote className="docs-pullquote">{PULLQUOTE}</blockquote>
    </section>
  );
}
