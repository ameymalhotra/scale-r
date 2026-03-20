import React from 'react';

const partners = [
  {
    name: 'National Science Foundation',
    description:
      'SCALE-R is supported under NSF Grant No. 2435008, enabling the research, training, and public-facing tools associated with this project.',
  },
  {
    name: 'University of Miami',
    description:
      'Core units include the Department of Geography and Sustainable Development, School of Architecture, Rosenstiel School of Marine, Atmospheric, and Earth Science, College of Engineering, and the Climate Resilience Institute.',
  },
  {
    name: 'Miami-Dade County',
    description:
      'County staff have contributed through workshops and engagement with experts across Planning, Resilience, Transportation, Historic Preservation, Planning Research, and Zoning.',
  },
  {
    name: 'Miami-Dade Office of Historic Preservation',
    description:
      'Hands-on training for graduate researchers and students on how climate resilience impacts cultural landscapes and how conservation practices can help.',
  },
  {
    name: 'Palmer Trinity School',
    description:
      'Outreach with Human Geography students and faculty to raise awareness of coastal resilience issues among the broader community.',
  },
  {
    name: 'United Nations / UN-Habitat',
    description:
      'Dissemination through the World Urban Forum (WUF12, 2024) and Habitat UNI, UN-Habitat\'s network for university and research partners.',
  },
  {
    name: 'Smart City Expo Miami',
    description:
      'A platform for sharing project findings with Greater Miami stakeholders and professional networks.',
  },
];

function abbr(name) {
  return name
    .split(/[\s/]+/)
    .filter((w) => w.length > 1 && w[0] === w[0].toUpperCase())
    .slice(0, 3)
    .map((w) => w[0])
    .join('');
}

export default function Partners() {
  return (
    <div className="page-content">
      <div className="page-hero">
        <h1>Partners</h1>
        <p className="subtitle">
          Institutions, government agencies, schools, and international forums that shape SCALE-R's
          research and community engagement.
        </p>
      </div>

      <div className="page-body">
        <section className="page-section">
          <div className="card-grid cols-3">
            {partners.map((p, i) => (
              <div className="card" key={i}>
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 10,
                    background: '#f0f4f2',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 16,
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    color: '#01703a',
                    letterSpacing: '0.5px',
                  }}
                >
                  {abbr(p.name)}
                </div>
                <div
                  style={{
                    fontWeight: 600,
                    color: '#1a2e23',
                    fontSize: '1.02rem',
                    marginBottom: 8,
                  }}
                >
                  {p.name}
                </div>
                <div className="prose" style={{ fontSize: '0.92rem' }}>
                  {p.description}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
