import React from 'react';
import TeamLeadershipCard from './TeamLeadershipCard.jsx';

const LEADERS = [
  {
    role: 'Principal Investigator',
    name: 'Sarbeswar Praharaj, PhD',
    bio:
      "Expert in urban informatics and smart city governance, leading the SCALE-R initiative's strategic vision for regional coastal resilience.",
    imageSrc: '/Images/team-sarbeswar-praharaj.webp',
    imageAlt:
      'Sarbeswar Praharaj speaking at a podium in front of a welcome screen',
    imagePosition: '58% 42%',
  },
  {
    role: 'Co-Investigator',
    name: 'Shouraseni Sen Roy, PhD',
    bio:
      'Specializing in climatology and spatial analysis, focusing on historical climate trends and future impact modeling in South Florida.',
    imageSrc: '/Images/team-shouraseni-sen-roy.webp',
    imageAlt: 'Shouraseni Sen Roy standing at a marina with boats in the background',
    imagePosition: 'center 30%',
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
