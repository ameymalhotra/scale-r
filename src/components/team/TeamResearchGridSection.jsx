import React from 'react';
import TeamResearchCard from './TeamResearchCard.jsx';

const RESEARCHERS = [
  {
    name: 'Sofia Bond',
    role: 'Project Management',
    imageSrc: '/Images/team-stitch-sofia.jpg',
    imageAlt: 'Portrait of Sofia Bond, a young professional researcher with a friendly expression in a bright studio',
  },
  {
    name: 'Mirna Obeid',
    role: 'Resilient Design',
    imageSrc: '/Images/team-stitch-mirna.jpg',
    imageAlt:
      'Portrait of Mirna Obeid, a creative professional in a design studio with architectural plans in the background',
  },
  {
    name: 'Trinity Gallegos',
    role: 'Geospatial Technology',
    imageSrc: '/Images/team-stitch-trinity.jpg',
    imageAlt: 'Portrait of Trinity Gallegos, a tech-focused researcher working with screens showing digital maps',
  },
  {
    name: 'Naomi Roos',
    role: 'Stakeholder Engagement',
    imageSrc: '/Images/team-stitch-naomi.jpg',
    imageAlt: 'Portrait of Naomi Roos, engaging and smiling, professional setting with soft daylight',
  },
];

export default function TeamResearchGridSection() {
  return (
    <div className="team-research-pill">
      <div className="team-section__head">
        <div>
          <h2 className="team-section__title">Research Team</h2>
          <div className="team-section__rule team-section__rule--tertiary" aria-hidden="true" />
        </div>
      </div>
      <div className="team-research-grid">
        {RESEARCHERS.map((m) => (
          <TeamResearchCard key={m.name} {...m} />
        ))}
      </div>
    </div>
  );
}
