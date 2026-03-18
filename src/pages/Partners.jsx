import React from 'react';

const containerStyle = {
  maxWidth: 1000,
  margin: '0 auto',
  padding: '32px 24px',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
  gap: '24px',
  marginTop: '24px',
};

const cardStyle = {
  background: 'rgba(255, 255, 255, 0.9)',
  border: '1px solid rgba(0, 0, 0, 0.08)',
  borderRadius: '12px',
  padding: '24px',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
};

const placeholderPartners = [
  { name: 'Partner Organization 1', description: 'Short description placeholder.' },
  { name: 'Partner Organization 2', description: 'Short description placeholder.' },
];

export default function Partners() {
  return (
    <div style={containerStyle} className="page-content">
      <h1 style={{ fontSize: '1.75rem', color: '#2c3e50', marginBottom: '8px' }}>
        Partners
      </h1>
      <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
        [Placeholder] Our project is made possible through collaboration with the following
        partners.
      </p>
      <div style={gridStyle}>
        {placeholderPartners.map((partner, i) => (
          <div key={i} style={cardStyle}>
            <div
              style={{
                width: 120,
                height: 60,
                background: '#e8e8e8',
                borderRadius: '8px',
                marginBottom: '16px',
              }}
              aria-hidden
            />
            <div style={{ fontWeight: 600, color: '#2c3e50', marginBottom: '8px' }}>
              {partner.name}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#546e7a', lineHeight: 1.5 }}>
              {partner.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
