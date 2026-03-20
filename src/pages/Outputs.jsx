import React from 'react';

const badgeColors = {
  Tool: { bg: '#e8f5e9', fg: '#2e7d32' },
  Research: { bg: '#e3f2fd', fg: '#1565c0' },
  Dataset: { bg: '#fff3e0', fg: '#e65100' },
  Documentation: { bg: '#f3e5f5', fg: '#7b1fa2' },
};

const outputs = [
  {
    title: 'Interactive resilience dashboard',
    type: 'Tool',
    detail:
      'Map-based exploration of projects, risk overlays, and county-scale data to support transparent, place-based decision support.',
  },
  {
    title: 'Regional resilience plan synthesis',
    type: 'Research',
    detail:
      'Systematic review of 22 Greater Miami resilience plans with thematic and sectoral analysis covering governance, environment, infrastructure, housing, energy, and equity.',
  },
  {
    title: 'Resilience strategies and solutions taxonomy',
    type: 'Research',
    detail:
      'Cataloging nature-based and engineered adaptation measures and mapping the dependencies and trade-offs between them across systems.',
  },
  {
    title: 'National resilience-tool and indicator review',
    type: 'Research',
    detail:
      'Assessment of 30 U.S. climate resilience tools with 264+ indicators organized across social, economic, environmental, institutional, infrastructure, and health domains.',
  },
  {
    title: 'Decision-support design criteria',
    type: 'Research',
    detail:
      'Evaluation of existing tools on data sourcing, indicator breadth, projected data, cross-scale relationships, communication features, and reporting capabilities.',
  },
  {
    title: 'Merged project inventory dataset',
    type: 'Dataset',
    detail:
      'County-scale project inventory combining local and LMS sources, geocoded and standardized for mapping and search.',
  },
  {
    title: 'Technical documentation',
    type: 'Documentation',
    detail:
      'Architecture, data layers, and methodology for reproducing or extending the dashboard pipeline.',
  },
];

export default function Outputs() {
  return (
    <div className="page-content">
      <div className="page-hero">
        <h1>Outputs</h1>
        <p className="subtitle">
          Deliverables and research products from the SCALE-R program.
        </p>
      </div>

      <div className="page-body">
        <section className="page-section">
          <div className="card-grid cols-2">
            {outputs.map((item, i) => {
              const colors = badgeColors[item.type] || { bg: '#eceff1', fg: '#37474f' };
              return (
                <div className="card" key={i}>
                  <span
                    className="badge"
                    style={{
                      background: colors.bg,
                      color: colors.fg,
                      marginBottom: 14,
                    }}
                  >
                    {item.type}
                  </span>
                  <div
                    style={{
                      fontWeight: 600,
                      color: '#1a2e23',
                      fontSize: '1.05rem',
                      marginBottom: 8,
                    }}
                  >
                    {item.title}
                  </div>
                  <div className="prose" style={{ fontSize: '0.93rem' }}>
                    {item.detail}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
