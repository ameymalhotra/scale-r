import React from 'react';

export default function TeamLeadershipCard({ role, name, bio, imageSrc, imageAlt }) {
  return (
    <article className="team-lead-card" tabIndex={0}>
      <img className="team-lead-card__img" src={imageSrc} alt={imageAlt} />
      <div className="team-lead-card__overlay" aria-hidden="true" />
      <div className="team-lead-card__body">
        <span className="team-lead-card__role">{role}</span>
        <h3 className="team-lead-card__name">{name}</h3>
        <div className="team-lead-card__bio">
          <p>{bio}</p>
        </div>
      </div>
    </article>
  );
}
