import React from 'react';
import TeamResearchCard from './TeamResearchCard.jsx';

const RESEARCHERS = [
  {
    name: 'Sofia Bond',
    role: 'Coastal Management',
    imageSrc: '/Images/team-sofia-bond.jpg',
    imageAlt: 'Sofia Bond smiling in a Miami Waterkeeper polo during a group event',
    imagePosition: '50% 22%',
  },
  {
    name: 'Mirna Obeid',
    role: 'Resilient Design',
    imageSrc: '/Images/team-mirna-obeid.jpg',
    imageAlt: 'Headshot of Mirna Obeid against a light studio background',
    imagePosition: '50% 30%',
  },
  {
    name: 'Trinity Gallegos',
    role: 'Geospatial Technology',
    imageSrc: '/Images/team-trinity-gallegos.png',
    imageAlt:
      'Trinity Gallegos outdoors on campus with trees and soft daylight behind her',
    imagePosition: '50% 24%',
    imageZoomIn: true,
  },
  {
    name: 'Amey Malhotra',
    role: 'Software Developer',
    imageSrc: '/Images/team-amey-malhotra.png',
    imageAlt: 'Headshot of Amey Malhotra in a black polo against a light studio background',
    imagePosition: '50% 28%',
  },
];

export default function TeamResearchGridSection() {
  return (
    <div className="team-research-block">
      <div className="team-section__head">
        <h2 id="team-research-heading" className="about-goals-heading">
          <span className="about-heading-highlight">Research team</span>
        </h2>
      </div>
      <div className="team-research-pill">
        <div className="team-research-grid">
          {RESEARCHERS.map((m) => (
            <TeamResearchCard key={m.name} {...m} />
          ))}
        </div>
      </div>
    </div>
  );
}
