import React from 'react';

const containerStyle = {
  maxWidth: 1000,
  margin: '0 auto',
  padding: '32px 24px',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
  gap: '24px',
  marginTop: '24px',
};

const cardStyle = {
  background: 'rgba(255, 255, 255, 0.9)',
  border: '1px solid rgba(0, 0, 0, 0.08)',
  borderRadius: '12px',
  padding: '20px',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
};

const placeholderMembers = [
  { name: 'Team Member 1', role: 'Role placeholder' },
  { name: 'Team Member 2', role: 'Role placeholder' },
  { name: 'Team Member 3', role: 'Role placeholder' },
];

export default function Team() {
  return (
    <div style={containerStyle} className="page-content">
      <h1 style={{ fontSize: '1.75rem', color: '#2c3e50', marginBottom: '8px' }}>
        Team
      </h1>
      <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
        [Placeholder] Meet the people behind the SCALE-R project.
      </p>
      <div style={gridStyle}>
        {placeholderMembers.map((member, i) => (
          <div key={i} style={cardStyle}>
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: '#e0e0e0',
                marginBottom: '12px',
              }}
              aria-hidden
            />
            <div style={{ fontWeight: 600, color: '#2c3e50', marginBottom: '4px' }}>
              {member.name}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#546e7a' }}>{member.role}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
