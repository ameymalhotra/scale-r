import React from 'react';
import TeamLeadershipCard from './TeamLeadershipCard.jsx';

const LEADERS = [
  {
    role: 'Principal Investigator',
    name: 'Sarbeswar Praharaj',
    bio:
      "Expert in urban informatics and smart city governance, leading the SCALE-R initiative's strategic vision for regional coastal resilience.",
    imageSrc: '/Images/team-stitch-pi.jpg',
    imageAlt:
      'Professional portrait of a male researcher with glasses in a modern lab environment, soft natural lighting',
  },
  {
    role: 'Co-Investigator',
    name: 'Shouraseni Sen Roy',
    bio:
      'Specializing in climatology and spatial analysis, focusing on historical climate trends and future impact modeling in South Florida.',
    imageSrc: '/Images/team-stitch-co-investigator.jpg',
    imageAlt: 'Professional portrait of a female academic in a university setting, bright and clean composition',
  },
];

export default function TeamLeadershipSection() {
  return (
    <div className="team-leadership-block">
      <div className="team-section__head">
        <div>
          <h2 className="team-section__title">Leadership</h2>
          <div className="team-section__rule team-section__rule--secondary" aria-hidden="true" />
        </div>
      </div>
      <div className="team-leadership-grid">
        {LEADERS.map((m) => (
          <TeamLeadershipCard key={m.name} {...m} />
        ))}
      </div>
    </div>
  );
}
