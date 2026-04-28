import React from 'react';

const DISASTER_TYPES = [
  {
    icon: 'flood',
    label: 'Flooding',
    accent: '#0e7aad',
    text:
      'Projects addressing risks from coastal and inland flooding driven by precipitation, tidal influences, and long-term sea-level rise, including stormwater management, drainage systems, and elevation strategies.',
  },
  {
    icon: 'tsunami',
    label: 'Storm Surge',
    accent: '#127ea7',
    text:
      'Projects addressing coastal inundation from storm-driven surges and wave action, including shoreline protection, surge barriers, and coastal defense systems.',
  },
  {
    icon: 'thermostat',
    label: 'Heat and Extreme Temperatures',
    accent: '#f47321',
    text:
      'Projects focused on mitigating rising temperatures and urban heat island effects through cooling strategies, urban greening, shading, and heat-resilient urban design.',
  },
  {
    icon: 'hub',
    label: 'Multi-Hazard',
    accent: '#2e6d54',
    text:
      'Projects designed to address multiple interacting hazards—such as flooding, heat, and infrastructure stress—through integrated and multiscale resilience strategies.',
  },
  {
    icon: 'settings_input_component',
    label: 'Critical Infrastructure',
    accent: '#52606b',
    text:
      'Projects that enhance the resilient operation of essential systems including energy, communications, and transportation under hazard conditions and disruptive events.',
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
        Projects are organized by primary hazard and system stressors to help
        users compare how resilience strategies respond to flooding, coastal
        surge, heat, compound risk, and essential infrastructure disruption.
      </p>

      <ul className="docs-disaster-rows" role="list">
        {DISASTER_TYPES.map((hazard) => (
          <li
            className="docs-disaster-row"
            key={hazard.label}
            style={{ '--disaster-accent': hazard.accent }}
          >
            <span className="docs-disaster-row__icon" aria-hidden>
              <span className="material-symbols-outlined">{hazard.icon}</span>
            </span>
            <div className="docs-disaster-row__body">
              <h3 className="docs-disaster-row__title">{hazard.label}</h3>
              <p className="docs-disaster-row__text">{hazard.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
