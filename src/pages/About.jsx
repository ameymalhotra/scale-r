import React from 'react';

const containerStyle = {
  maxWidth: 1000,
  margin: '0 auto',
  padding: '32px 24px',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

export default function About() {
  return (
    <div style={containerStyle} className="page-content">
      <h1 style={{ fontSize: '1.75rem', color: '#2c3e50', marginBottom: '16px' }}>
        About the project
      </h1>
      <p style={{ color: '#546e7a', lineHeight: 1.7, marginBottom: '16px' }}>
        [Placeholder] This project provides a comprehensive view of climate resilience efforts
        across Miami-Dade County. SCALE-R brings together adaptation strategies, infrastructure
        projects, and community investments into a single platform for researchers, planners,
        and the public.
      </p>
      <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginTop: '24px', marginBottom: '12px' }}>
        Mission
      </h2>
      <p style={{ color: '#546e7a', lineHeight: 1.7, marginBottom: '16px' }}>
        [Placeholder] Our mission is to support data-driven decision-making for climate
        resilience by mapping projects, risks, and critical infrastructure in one place.
      </p>
      <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginTop: '24px', marginBottom: '12px' }}>
        Key objectives
      </h2>
      <ul style={{ color: '#546e7a', lineHeight: 1.8, paddingLeft: '24px' }}>
        <li>[Placeholder] Inventory and map resilience projects across the county</li>
        <li>[Placeholder] Integrate risk and vulnerability indices with project data</li>
        <li>[Placeholder] Support transparency and public engagement</li>
      </ul>
      <h2 style={{ fontSize: '1.25rem', color: '#2c3e50', marginTop: '24px', marginBottom: '12px' }}>
        Methodology
      </h2>
      <p style={{ color: '#546e7a', lineHeight: 1.7 }}>
        [Placeholder] We combine multiple data sources including local project inventories,
        FEMA National Risk Index, community resilience indices, and critical infrastructure
        layers. Data is standardized, geocoded, and made available through this dashboard.
      </p>
    </div>
  );
}
