import React from 'react';

const PARTNER_LABELS = [
  'National Science Foundation',
  'University of Miami',
  'Miami-Dade County',
  'The Nature Conservancy',
];

export default function TeamPartnersMarquee() {
  const doubled = [...PARTNER_LABELS, ...PARTNER_LABELS];
  return (
    <div className="team-marquee" aria-hidden="true">
      <div className="team-marquee__track">
        {doubled.map((label, i) => (
          <span key={`${label}-${i}`} className="team-marquee__item">
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
