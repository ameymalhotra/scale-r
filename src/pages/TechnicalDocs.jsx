import React from 'react';

const containerStyle = {
  maxWidth: 1000,
  margin: '0 auto',
  padding: '32px 24px',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

const sectionStyle = { marginTop: '28px' };

export default function TechnicalDocs() {
  return (
    <div style={containerStyle} className="page-content">
      <h1 style={{ fontSize: '1.75rem', color: '#2c3e50', marginBottom: '16px' }}>
        Technical Documentation
      </h1>
      <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
        [Placeholder] Technical details for data sources, methodology, and system architecture.
      </p>

      <section style={sectionStyle}>
        <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginBottom: '12px' }}>
          Data sources
        </h2>
        <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
          [Placeholder] Project inventory (merged Our DB + LMS), FEMA National Risk Index,
          community resilience indices, critical infrastructure GeoJSON layers from Supabase
          Storage, and census tract boundaries.
        </p>
      </section>

      <section style={sectionStyle}>
        <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginBottom: '12px' }}>
          Methodology
        </h2>
        <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
          [Placeholder] Geocoding, merging, classification, and summarization pipelines
          (Python/Node). Data is seeded to Supabase and exposed as GeoJSON for the map.
        </p>
      </section>

      <section style={sectionStyle}>
        <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginBottom: '12px' }}>
          Architecture
        </h2>
        <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
          [Placeholder] React + Vite frontend, Mapbox GL for mapping, Recharts for charts,
          Supabase (Postgres + Storage) for data. Client-side search and filtering over
          project GeoJSON.
        </p>
      </section>
    </div>
  );
}
