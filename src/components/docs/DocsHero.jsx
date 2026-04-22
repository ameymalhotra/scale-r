import React from 'react';

export default function DocsHero() {
  return (
    <header className="about-hero" aria-labelledby="docs-hero-heading">
      <div className="about-hero-inner">
        <div className="about-hero-copy">
          <h1 id="docs-hero-heading" className="about-hero-title">
            Technical Documentation
          </h1>
          <p className="docs-hero-tagline">
            How SCALE-R is built: the data, definitions, models, and use cases
            behind the Miami-Dade climate resilience dashboard.
          </p>
        </div>
      </div>
    </header>
  );
}
