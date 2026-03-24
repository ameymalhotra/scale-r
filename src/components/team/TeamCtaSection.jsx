import React from 'react';

export default function TeamCtaSection() {
  return (
    <section className="team-cta-wrap" aria-labelledby="team-cta-heading">
      <div className="team-cta">
        <div className="team-cta__texture" aria-hidden="true">
          <img
            src="/Images/team-stitch-cta-texture.jpg"
            alt=""
            role="presentation"
          />
        </div>
        <div className="team-cta__inner">
          <h2 id="team-cta-heading" className="team-cta__title">
            Want to contribute to environmental resilience?
          </h2>
          <p className="team-cta__text">
            We are always looking for passionate researchers, data scientists, and local stakeholders to join our mission.
          </p>
          <div className="team-cta__actions">
            <button type="button" className="team-cta__btn team-cta__btn--primary">
              View Open Positions
            </button>
            <button type="button" className="team-cta__btn team-cta__btn--ghost">
              Contact Our Team
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
