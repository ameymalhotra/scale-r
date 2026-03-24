import React from 'react';

export default function TeamResearchCard({ name, role, imageSrc, imageAlt }) {
  return (
    <article className="team-research-card" tabIndex={0}>
      <img className="team-research-card__img" src={imageSrc} alt={imageAlt} />
      <div className="team-research-card__body">
        <div className="team-research-card__frost">
          <h4 className="team-research-card__name">{name}</h4>
          <p className="team-research-card__role">{role}</p>
        </div>
      </div>
    </article>
  );
}
