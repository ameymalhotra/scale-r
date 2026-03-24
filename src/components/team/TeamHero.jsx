import React from 'react';

export default function TeamHero() {
  return (
    <section className="team-hero" aria-labelledby="team-hero-heading">
      <div className="team-hero__inner">
        <div className="team-hero__visual">
          <div className="team-hero__glow" aria-hidden="true" />
          <div className="team-hero__frame">
            <img
              src="/Images/about-stitch-hero-coast.jpg"
              alt="Aerial view of Miami-Dade County coastline"
            />
          </div>
        </div>

        <div className="team-hero__content">
          <span className="team-hero__label">Our Collective</span>
          <h1 id="team-hero-heading" className="team-hero__title">
            The Minds <span className="team-hero__accent">Scaling</span>
            <br />
            Resilience
          </h1>
          <p className="team-hero__sub">
            A multidisciplinary collective of researchers, students, and collaborators behind the SCALE-R initiative,
            dedicated to safeguarding our coastal futures.
          </p>
        </div>
      </div>
    </section>
  );
}
