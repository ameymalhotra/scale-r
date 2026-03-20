import React from 'react';

const teamMembers = [
  { name: 'Sarbeswar Praharaj', role: 'Principal Investigator' },
  { name: 'Shouraseni Sen Roy', role: 'Co-Investigator' },
  { name: 'Sofia Bond', role: 'Graduate Research Assistant, Project Management' },
  { name: 'Mirna Obeid', role: 'Research Assistant, Resilient Design' },
  { name: 'Trinity Gallegos', role: 'Graduate Research Assistant, Geospatial Technology' },
  { name: 'Naomi Roos', role: 'Graduate Research Assistant, Stakeholder Engagement' },
];

const pastMembers = [
  { name: 'Ayana Albertini-Fleurant', program: 'MPS in Urban Sustainability & Resilience' },
  { name: 'Anthony Fioravanti', program: 'Master of Real Estate' },
  { name: 'Tyreke Walker', program: 'Bachelor of Architecture' },
  { name: 'Nabanita Majumder', program: 'MPS in Urban Sustainability & Resilience' },
  { name: 'Nina Jean-Louis', program: 'PhD student' },
  { name: 'Jayline Cole', program: 'Bachelor of Architecture' },
];

const palette = ['#01703a', '#1565c0', '#6d4c41', '#00838f', '#ad1457', '#e65100'];

function initials(name) {
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase();
}

export default function Team() {
  return (
    <div className="page-content">
      <div className="page-hero">
        <h1>Team</h1>
        <p className="subtitle">
          The researchers, students, and collaborators behind SCALE-R.
        </p>
      </div>

      <div className="page-body">
        {/* Current team */}
        <section className="page-section">
          <h2 className="section-title">Current members</h2>
          <div className="card-grid cols-3">
            {teamMembers.map((m, i) => (
              <div className="card" key={i} style={{ textAlign: 'center' }}>
                <div
                  style={{
                    width: 80,
                    height: 80,
                    borderRadius: '50%',
                    background: palette[i % palette.length],
                    margin: '0 auto 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: '#fff',
                    letterSpacing: '1px',
                  }}
                >
                  {initials(m.name)}
                </div>
                <div style={{ fontWeight: 600, color: '#1a2e23', fontSize: '1.05rem' }}>
                  {m.name}
                </div>
                <div style={{ color: '#546e7a', fontSize: '0.9rem', marginTop: 4 }}>
                  {m.role}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Past researchers */}
        <section className="page-section">
          <h2 className="section-title">Past researchers and interns</h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 12,
            }}
          >
            {pastMembers.map((m, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 16px',
                  background: '#f7f9f8',
                  borderRadius: 10,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: '#cfd8dc',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    color: '#455a64',
                    flexShrink: 0,
                  }}
                >
                  {initials(m.name)}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: '#1a2e23', fontSize: '0.95rem' }}>
                    {m.name}
                  </div>
                  <div style={{ color: '#78909c', fontSize: '0.82rem' }}>{m.program}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
