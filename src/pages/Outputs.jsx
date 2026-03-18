import React from 'react';

const containerStyle = {
  maxWidth: 1000,
  margin: '0 auto',
  padding: '32px 24px',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

const listStyle = {
  listStyle: 'none',
  padding: 0,
  margin: '24px 0 0 0',
};

const itemStyle = {
  padding: '16px 0',
  borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
  color: '#546e7a',
  lineHeight: 1.6,
};

const placeholderOutputs = [
  { title: 'Resilience project inventory (merged dataset)', type: 'Dataset' },
  { title: 'Interactive dashboard and map', type: 'Tool' },
  { title: 'Technical documentation', type: 'Documentation' },
  { title: 'Publications and reports', type: 'Publication' },
];

export default function Outputs() {
  return (
    <div style={containerStyle} className="page-content">
      <h1 style={{ fontSize: '1.75rem', color: '#2c3e50', marginBottom: '8px' }}>
        Outputs
      </h1>
      <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
        [Placeholder] Project deliverables, datasets, publications, and resources.
      </p>
      <ul style={listStyle}>
        {placeholderOutputs.map((item, i) => (
          <li key={i} style={itemStyle}>
            <strong style={{ color: '#2c3e50' }}>{item.title}</strong>
            <span style={{ marginLeft: '8px', fontSize: '0.85rem', opacity: 0.9 }}>
              — {item.type}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
