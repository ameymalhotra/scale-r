import React from 'react';

export default function TeamResearchCard({
  name,
  role,
  imageSrc,
  imageAlt,
  imagePosition,
  imageZoomIn,
}) {
  const imgClassName = [
    'team-research-card__img',
    imageZoomIn && 'team-research-card__img--zoom-in',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <article className="team-research-card">
      <img
        className={imgClassName}
        src={imageSrc}
        alt={imageAlt}
        style={imagePosition ? { objectPosition: imagePosition } : undefined}
      />
      <div className="team-research-card__body">
        <div className="team-research-card__frost">
          <h3 className="team-research-card__name">{name}</h3>
          <p className="team-research-card__role">{role}</p>
        </div>
      </div>
    </article>
  );
}
