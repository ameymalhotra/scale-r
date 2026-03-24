import React from 'react';
import './About.css';
import './Team.css';
import TeamHero from '../components/team/TeamHero.jsx';
import TeamPartnersMarquee from '../components/team/TeamPartnersMarquee.jsx';
import TeamLeadershipSection from '../components/team/TeamLeadershipSection.jsx';
import TeamResearchGridSection from '../components/team/TeamResearchGridSection.jsx';
import TeamCtaSection from '../components/team/TeamCtaSection.jsx';
import TeamPageFooter from '../components/team/TeamPageFooter.jsx';

export default function Team() {
  return (
    <div className="team-root">
      <TeamHero />
      <TeamPartnersMarquee />
      <section className="team-section" aria-label="Team members">
        <TeamLeadershipSection />
        <TeamResearchGridSection />
      </section>
      <TeamCtaSection />
      <TeamPageFooter />
    </div>
  );
}
