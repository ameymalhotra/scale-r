import React from 'react';
import TeamLeadershipCard from './TeamLeadershipCard.jsx';

const LEADERS = [
  {
    role: 'Principal Investigator',
    name: 'Sarbeswar Praharaj',
    bio:
      "Expert in urban informatics and smart city governance, leading the SCALE-R initiative's strategic vision for regional coastal resilience.",
    imageSrc: '/Images/team-sarbeswar-praharaj.png',
    imageAlt:
      'Sarbeswar Praharaj speaking at a podium in front of a welcome screen',
    imagePosition: '68% 34%',
  },
  {
    role: 'Co-Investigator',
    name: 'Shouraseni Sen Roy',
    bio:
      'Specializing in climatology and spatial analysis, focusing on historical climate trends and future impact modeling in South Florida.',
    imageSrc: '/Images/team-shouraseni-sen-roy.png',
    imageAlt: 'Shouraseni Sen Roy standing at a marina with boats in the background',
    imagePosition: 'center 5%',
    mediaWidth: '132.25%',
    mediaHeight: '132.25%',
  },
];

export default function TeamLeadershipSection() {
  return (
    <div className="team-leadership-block">
      <div className="team-section__head">
        <h2 id="team-leadership-heading" className="about-goals-heading">
          <span className="about-heading-highlight">Leadership</span>
        </h2>
      </div>
      <div className="team-leadership-grid">
        {LEADERS.map((m) => (
          <TeamLeadershipCard key={m.name} {...m} />
        ))}
      </div>
    </div>
  );
}
