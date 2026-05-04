import React from 'react';

export default function TeamLeadershipCard({
  role,
  name,
  bio,
  imageSrc,
  imageAlt,
  imagePosition,
  imagePositionX,
  imagePositionY,
}) {
  const pct = (v) => {
    if (typeof v === 'number') return `${v}%`;
    const s = String(v).trim();
    return s.endsWith('%') ? s : `${s}%`;
  };

  const objectPosition =
    imagePositionX != null && imagePositionY != null
      ? `${pct(imagePositionX)} ${pct(imagePositionY)}`
      : imagePosition;

  const imgPos =
    objectPosition != null && String(objectPosition).trim() !== ''
      ? objectPosition
      : undefined;

  return (
    <article className="team-lead-card">
      <div className="team-lead-card__media">
        <img
          className="team-lead-card__img"
          src={imageSrc}
          alt={imageAlt}
          style={imgPos ? { objectPosition: imgPos } : undefined}
        />
        <div className="team-lead-card__overlay" aria-hidden="true" />
      </div>
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
