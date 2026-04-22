import React from 'react';

const DISASTER_TYPES = [
  {
    icon: 'flood',
    label: 'Flooding',
    text:
      'Pluvial, fluvial, and tidal flooding — the dominant chronic hazard across Miami-Dade.',
  },
  {
    icon: 'thermostat',
    label: 'Extreme heat',
    text:
      'Rising heat days and urban heat island effects that stress health, energy, and outdoor labor.',
  },
  {
    icon: 'cyclone',
    label: 'Hurricanes & wind',
    text:
      'Tropical cyclones — wind damage, rainfall, and compounding outages across infrastructure.',
  },
  {
    icon: 'tsunami',
    label: 'Storm surge & SLR',
    text:
      'Acute coastal surge layered onto long-term sea level rise exposure along the Miami coast.',
  },
];

export default function DocsDisastersSection() {
  return (
    <section
      id="disaster-focus"
      className="docs-section"
      aria-labelledby="docs-disasters-heading"
    >
      <h2 id="docs-disasters-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Disaster Focus</span>
      </h2>
      <p className="docs-section__lede">
        The dashboard prioritizes four hazard families that most shape
        resilience planning in South Florida. Each is treated as both an acute
        event and a chronic stressor.
      </p>

      <div className="docs-tile-grid docs-tile-grid--disasters">
        {DISASTER_TYPES.map((tile) => (
          <div className="docs-def-tile" key={tile.label}>
            <span className="docs-def-tile__icon" aria-hidden>
              <span className="material-symbols-outlined">{tile.icon}</span>
            </span>
            <h3 className="docs-def-tile__label">{tile.label}</h3>
            <p className="docs-def-tile__text">{tile.text}</p>
          </div>
        ))}
      </div>

      <span className="docs-placeholder" aria-hidden>
        Placeholder copy · Disaster Focus
      </span>
    </section>
  );
}
