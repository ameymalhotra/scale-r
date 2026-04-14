import React from 'react';
import './About.css';
import './Team.css';
import TeamHero from '../components/team/TeamHero.jsx';
import TeamIntroSection from '../components/team/TeamIntroSection.jsx';
import TeamLeadershipSection from '../components/team/TeamLeadershipSection.jsx';
import TeamResearchGridSection from '../components/team/TeamResearchGridSection.jsx';
import TeamPastResearchersSection from '../components/team/TeamPastResearchersSection.jsx';
import TeamPageFooter from '../components/team/TeamPageFooter.jsx';

export default function Team() {
  return (
    <div className="about-root team-page">
      <TeamHero />

      <TeamIntroSection />

      <section
        className="about-pillars about-section--on-um-orange team-page-roster"
        aria-label="Team members"
      >
        <div className="about-pillars-inner team-page-roster-inner">
          <TeamLeadershipSection />
          <TeamResearchGridSection />
          <TeamPastResearchersSection />
        </div>
      </section>

      <TeamPageFooter />
    </div>
  );
}
