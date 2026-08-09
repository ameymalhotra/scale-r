import React from 'react';

const PROJECT_STATUSES = [
  {
    icon: 'check_circle',
    label: 'Completed',
    accent: '#27ae60',
    text:
      'Project construction or implementation is finished, and the intended infrastructure or intervention is operational.',
  },
  {
    icon: 'construction',
    label: 'Ongoing',
    accent: '#b45309',
    text:
      'Project implementation, construction, installation, or other substantive project activities are currently underway.',
  },
  {
    icon: 'payments',
    label: 'Funded',
    accent: '#0f766e',
    text:
      'Funding has been secured or formally allocated, but substantive construction or implementation has not yet begun.',
  },
  {
    icon: 'event_note',
    label: 'Planned',
    accent: '#2563eb',
    text:
      'Project has been proposed, programmed, designed, or prioritized, but full implementation funding has not yet been secured or allocated.',
  },
];

export default function DocsProjectStatusSection() {
  return (
    <section
      id="project-status"
      className="docs-section"
      aria-labelledby="docs-project-status-heading"
    >
      <h2 id="docs-project-status-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">Project Status</span>
      </h2>
      <p className="docs-section__lede">
        Each project is classified by its stage of implementation—from
        early planning through secured funding, active construction, and
        completed delivery—to support comparison of readiness and progress
        across the resilience portfolio.
      </p>

      <ul className="docs-disaster-rows" role="list">
        {PROJECT_STATUSES.map((status) => (
          <li
            className="docs-disaster-row"
            key={status.label}
            style={{ '--disaster-accent': status.accent }}
          >
            <span className="docs-disaster-row__icon" aria-hidden>
              <span className="material-symbols-outlined">{status.icon}</span>
            </span>
            <div className="docs-disaster-row__body">
              <h3 className="docs-disaster-row__title">{status.label}</h3>
              <p className="docs-disaster-row__text">{status.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
