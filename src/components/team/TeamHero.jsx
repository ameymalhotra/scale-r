import React from 'react';

export default function TeamHero() {
  return (
    <header className="about-hero" aria-labelledby="team-hero-heading">
      <div className="about-hero-bg">
        <img
          src="/Images/about-hero-skyline-1920.jpg"
          alt=""
          decoding="async"
          loading="eager"
        />
      </div>

      <div className="about-hero-inner">
        <div className="about-hero-copy">
          <h1
            id="team-hero-heading"
            className="about-hero-title about-hero-frost"
          >
            Our Team
          </h1>
          <p className="about-hero-sub">
            <span className="about-hero-sub-highlight about-hero-frost">
              The SCALE-R is led by an interdisciplinary research team whose aim is
              to advance our understanding of coastal risks and resilience and
              generate innovative solutions that inform and address the complex
              nature of urban climate adaptation.
            </span>
          </p>
        </div>
      </div>
    </header>
  );
}
