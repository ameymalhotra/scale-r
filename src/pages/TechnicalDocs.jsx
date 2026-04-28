import React from 'react';
import './About.css';
import './TechnicalDocs.css';
import DocsHero from '../components/docs/DocsHero.jsx';
import DocsSideNav from '../components/docs/DocsSideNav.jsx';
import DocsIntroSection from '../components/docs/DocsIntroSection.jsx';
import DocsBackgroundSection from '../components/docs/DocsBackgroundSection.jsx';
import DocsDataSourcesSection from '../components/docs/DocsDataSourcesSection.jsx';
import DocsInfrastructureSection from '../components/docs/DocsInfrastructureSection.jsx';
import DocsDisastersSection from '../components/docs/DocsDisastersSection.jsx';
import DocsModelingLayersSection from '../components/docs/DocsModelingLayersSection.jsx';
import DocsUseCasesSection from '../components/docs/DocsUseCasesSection.jsx';
import TeamPageFooter from '../components/team/TeamPageFooter.jsx';

const SECTIONS = [
  { id: 'introduction', label: 'Introduction' },
  { id: 'background', label: 'Background' },
  { id: 'data-sources', label: 'Data Sources' },
  { id: 'infrastructure-types', label: 'Infrastructure Types' },
  { id: 'disaster-focus', label: 'Disaster Focus' },
  { id: 'modeling-layers', label: 'Modeling Layers' },
  { id: 'use-cases', label: 'Benefits & Use Cases' },
];

export default function TechnicalDocs() {
  return (
    <div className="about-root docs-page">
      <DocsHero />

      <div className="docs-layout">
        <DocsSideNav sections={SECTIONS} />

        <main className="docs-content">
          <DocsIntroSection />
          <DocsBackgroundSection />
          <DocsDataSourcesSection />
          <DocsInfrastructureSection />
          <DocsDisastersSection />
          <DocsModelingLayersSection />
          <DocsUseCasesSection />
        </main>
      </div>

      <TeamPageFooter />
    </div>
  );
}
