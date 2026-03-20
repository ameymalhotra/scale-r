import React from 'react';

const engagementItems = [
  {
    title: 'Miami-Dade Environmental Stewards Workshop',
    detail:
      'Stephen P. Clark Government Center, September 26 2024 — county experts from Planning, Resilience, Transportation, Historic Preservation, Planning Research, and Zoning.',
  },
  {
    title: 'Palmer Trinity School Outreach',
    detail:
      'Interaction with Human Geography students and faculty (April 23 2025) to broaden awareness among younger learners.',
  },
  {
    title: 'UN World Urban Forum (WUF12)',
    detail:
      'Cairo, Egypt, November 4–8 2024 — presentation of project findings by Dr. Sarbeswar Praharaj.',
  },
  {
    title: 'Historic Preservation Training',
    detail:
      'Hands-on training with Miami-Dade Office of Historic Preservation on climate resilience, cultural landscapes, and conservation practice.',
  },
  {
    title: 'Smart City Expo Miami',
    detail:
      'September 23–25 2024 — talk titled "Anticipating Change and Designing Future-Ready Communities."',
  },
  {
    title: 'Habitat UNI Roundtable',
    detail:
      'Research and Academia Roundtable at WUF 2024, focused on urban climate resilience through interdisciplinary education.',
  },
];

export default function About() {
  return (
    <div className="page-content">
      {/* ── Hero ────────────────────────────────────────── */}
      <div className="page-hero">
        <h1>About SCALE-R</h1>
        <p className="subtitle">
          Simulating Coastal Adaptation and Local Exposure for Enhanced Resilience
        </p>
      </div>

      {/* ── Body ────────────────────────────────────────── */}
      <div className="page-body">
        {/* Overview */}
        <section className="page-section">
          <h2 className="section-title">Overview</h2>
          <div className="prose">
            <p>
              Since 1980, the U.S. has incurred over $2.7 trillion in costs from climate-related
              disasters. Sea-level rise poses ongoing threats to coastal communities — home to about
              40% of the nation's population. SCALE-R promotes researcher–community partnerships to
              co-develop decision-support tools that visualize, test, and prioritize localized
              adaptation and mitigation strategies to enhance coastal resilience.
            </p>
            <p style={{ marginTop: 16 }}>
              The project uses place-based, participatory methods to incorporate stakeholder knowledge
              into the design and evaluation of solutions. It also trains graduate students and
              researchers, contributing to interdisciplinary STEM education and workforce development.
            </p>
            <p style={{ marginTop: 16 }}>
              This is a collaboration among researchers at the University of Miami's Department of
              Geography and Sustainable Development, School of Architecture, Rosenstiel School of
              Marine, Atmospheric, and Earth Science, College of Engineering, and the Climate
              Resilience Institute.{' '}
              <a
                href="https://geography.as.miami.edu/research/geo_labs/scale-r/index.html"
                target="_blank"
                rel="noopener noreferrer"
              >
                Visit the SCALE-R lab page &rarr;
              </a>
            </p>
          </div>
        </section>

        {/* Goals */}
        <section className="page-section">
          <h2 className="section-title">Advancing Greater Miami's coastal resilience</h2>
          <div className="card-grid cols-3">
            {[
              {
                num: '01',
                heading: 'Equitable partnerships',
                text: 'Building equitable community partnerships that center local stakeholder knowledge and lived experience.',
              },
              {
                num: '02',
                heading: 'Mapping the network',
                text: 'Mapping the complex network of resilience plans, projects, and investments across spatial and temporal scales.',
              },
              {
                num: '03',
                heading: 'Decision-support tools',
                text: 'Designing an integrated decision-support dashboard to facilitate pathways toward a resilient future.',
              },
            ].map((g, i) => (
              <div className="card" key={i}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#01703a', marginBottom: 12, letterSpacing: '1px' }}>{g.num}</div>
                <div style={{ fontWeight: 600, color: '#1a2e23', marginBottom: 8, fontSize: '1.05rem' }}>
                  {g.heading}
                </div>
                <div className="prose" style={{ fontSize: '0.95rem' }}>{g.text}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Plan context */}
        <section className="page-section">
          <h2 className="section-title">Plan and policy context</h2>
          <div className="prose">
            <p>
              The team has systematically reviewed <strong>22 resilience plans</strong> across the
              Greater Miami region — including those from the South Florida Water Management District,
              Southeast Florida Regional Climate Change Compact, Miami-Dade County, the City of Miami,
              Miami Beach, and other local jurisdictions. The analysis reveals how plans emphasize
              themes across six major clusters:
            </p>
          </div>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 10,
              marginTop: 20,
            }}
          >
            {[
              { label: 'Governance & Society', color: '#455a64' },
              { label: 'Environment & Climate', color: '#2e7d32' },
              { label: 'Infrastructure & Mobility', color: '#1565c0' },
              { label: 'Land & Housing', color: '#6d4c41' },
              { label: 'Water & Energy', color: '#00838f' },
              { label: 'Health & Equity', color: '#ad1457' },
            ].map((c) => (
              <span
                className="badge"
                key={c.label}
                style={{ background: c.color, color: '#fff' }}
              >
                {c.label}
              </span>
            ))}
          </div>
        </section>

        {/* Community engagement */}
        <section className="page-section">
          <h2 className="section-title">Community engagement</h2>
          <div className="card-grid cols-2">
            {engagementItems.map((e, i) => (
              <div className="card" key={i} style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    color: '#2e7d32',
                  }}
                >
                  {i + 1}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: '#1a2e23', marginBottom: 4 }}>{e.title}</div>
                  <div className="prose" style={{ fontSize: '0.92rem' }}>{e.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Acknowledgment */}
        <section className="page-section">
          <div
            style={{
              background: '#f5f7f6',
              borderRadius: 12,
              padding: '24px 28px',
              borderLeft: '4px solid #01703a',
            }}
          >
            <div className="prose" style={{ fontSize: '0.93rem' }}>
              This material is based upon work supported by the{' '}
              <strong>National Science Foundation</strong> under Grant No.&nbsp;2435008. Any opinions,
              findings, conclusions, or recommendations expressed are those of the authors and do not
              necessarily reflect the views of the NSF.
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
