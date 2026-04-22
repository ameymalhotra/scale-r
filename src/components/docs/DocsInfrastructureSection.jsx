import React from 'react';

const INFRASTRUCTURE_TYPES = [
  {
    icon: 'bolt',
    label: 'Energy',
    text:
      'Generation, substations, and distribution assets critical to power continuity during hazard events.',
  },
  {
    icon: 'water_drop',
    label: 'Water & wastewater',
    text:
      'Treatment plants, pump stations, and distribution mains — highly exposed to flood and surge.',
  },
  {
    icon: 'directions_bus',
    label: 'Transportation',
    text:
      'Roads, bridges, transit nodes, and evacuation corridors supporting mobility and emergency response.',
  },
  {
    icon: 'local_hospital',
    label: 'Health & emergency',
    text:
      'Hospitals, clinics, fire and EMS facilities that anchor community response capacity.',
  },
  {
    icon: 'school',
    label: 'Social & community',
    text:
      'Schools, shelters, and community centers that double as refuge and service hubs.',
  },
  {
    icon: 'apartment',
    label: 'Housing & buildings',
    text:
      'Residential and mixed-use stock — the first point of exposure for most residents.',
  },
];

export default function DocsInfrastructureSection() {
  return (
    <section
      id="infrastructure-types"
      className="docs-section docs-section--pill"
      aria-labelledby="docs-infra-heading"
    >
      <h2 id="docs-infra-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">
          Infrastructure Types
        </span>
      </h2>
      <p className="docs-section__lede">
        SCALE-R groups the built environment into six interdependent
        infrastructure classes. Each class carries its own exposure profile and
        its own set of adaptation levers.
      </p>

      <div className="docs-tile-grid">
        {INFRASTRUCTURE_TYPES.map((tile) => (
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
        Placeholder copy · Infrastructure Types
      </span>
    </section>
  );
}
