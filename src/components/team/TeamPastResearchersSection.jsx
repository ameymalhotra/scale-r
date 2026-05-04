import React from 'react';

const PAST_MEMBERS = [
  {
    name: 'Ayana Albertini-Fleurant',
    role: 'MPS in Urban Sustainability & Resilience student',
  },
  {
    name: 'Anthony Fioravanti',
    role: 'Master of Real Estate Student',
  },
  {
    name: 'Tyreke Walker',
    role: 'Bachelor of Architecture student',
  },
  {
    name: 'Nabanita Majumder',
    role: 'MPS in Urban Sustainability & Resilience student',
  },
  {
    name: 'Nina Jean-Louis',
    role: 'PhD student',
  },
  {
    name: 'Jayline Cole',
    role: 'Bachelor of Architecture student',
  },
  {
    name: 'Noami Roos',
    role: 'MPS in Urban Sustainability & Resilience Student',
  },
  {
    name: 'Varsha Gopal',
    role: 'Master in Urban Design Student',
  },
];

export default function TeamPastResearchersSection() {
  return (
    <div className="team-past-block">
      <div className="team-section__head">
        <h2 id="team-past-heading" className="about-goals-heading">
          <span className="about-heading-highlight">
            Past Researchers and Interns
          </span>
        </h2>
      </div>
      <ul className="team-past-list" role="list" aria-labelledby="team-past-heading">
        {PAST_MEMBERS.map((m) => (
          <li key={m.name} className="team-past-item">
            <span className="team-past-name">{m.name}</span>
            <span className="team-past-role">{m.role}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
