import React from 'react';

const sections = [
  {
    title: 'Research methodology',
    items: [
      {
        label: 'Resilience plans',
        text: 'Structured review of 22 Greater Miami plans to extract prominent concepts, sectoral emphasis, and cross-cutting themes (governance, environment and climate, infrastructure and mobility, land and housing, water and energy, health and equity).',
      },
      {
        label: 'Strategies and solutions',
        text: 'Cataloging proposed measures — from nature-based options to engineered infrastructure — recognizing that adaptation pathways are interconnected and involve trade-offs across systems.',
      },
      {
        label: 'Tool and indicator assessment',
        text: 'Review of 30 U.S. climate resilience tools, with 264+ indicators grouped into social, economic, environmental, institutional, infrastructure, and health domains.',
      },
      {
        label: 'Decision-support criteria',
        text: 'Comparison of tools on data sourcing, indicator breadth, historical vs. projected data, cross-scale relationships, ongoing communication, data/map export, and report generation.',
      },
    ],
  },
  {
    title: 'Dashboard data sources',
    prose:
      'The map application consumes a merged project inventory (local and LMS sources), FEMA National Risk Index and community resilience overlays, critical infrastructure layers (GeoJSON from Supabase Storage), and census tract boundaries for tract-level statistics.',
  },
  {
    title: 'Data pipeline',
    prose:
      'Repository scripts (Python and Node) handle geocoding, merging, classification, and optional summarization. Processed data is seeded to Supabase and published as GeoJSON for the client. See the README and scripts/ directory for runnable entry points.',
  },
  {
    title: 'Application architecture',
    prose:
      'React + Vite power the UI. Mapbox GL JS provides the map. Charting uses Recharts where applicable. Supabase (Postgres + Storage) backs hosted datasets. Search and filtering run in the browser over loaded project features.',
  },
];

export default function TechnicalDocs() {
  return (
    <div className="page-content">
      <div className="page-hero">
        <h1>Technical Documentation</h1>
        <p className="subtitle">
          Data sources, methodology, and system architecture behind the SCALE-R dashboard.
        </p>
      </div>

      <div className="page-body">
        {sections.map((sec, si) => (
          <section className="page-section" key={si}>
            <h2 className="section-title">{sec.title}</h2>

            {sec.items ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {sec.items.map((item, ii) => (
                  <div
                    key={ii}
                    style={{
                      background: '#f7f9f8',
                      borderRadius: 12,
                      padding: '20px 24px',
                      borderLeft: '3px solid #01703a',
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 600,
                        color: '#1a2e23',
                        marginBottom: 6,
                        fontSize: '0.98rem',
                      }}
                    >
                      {item.label}
                    </div>
                    <div className="prose" style={{ fontSize: '0.93rem' }}>
                      {item.text}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="prose">{sec.prose}</div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
