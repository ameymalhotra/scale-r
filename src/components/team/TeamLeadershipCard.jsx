import React from 'react';

const DEFAULT_MEDIA_WIDTH = '135%';
const DEFAULT_MEDIA_HEIGHT = '118%';

export default function TeamLeadershipCard({
  role,
  name,
  bio,
  imageSrc,
  imageAlt,
  imagePosition,
  imagePositionX,
  imagePositionY,
  mediaWidth,
  mediaHeight,
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

  const hasCustomMedia =
    mediaWidth != null || mediaHeight != null;
  const mediaStyle = hasCustomMedia
    ? {
        width: mediaWidth ?? DEFAULT_MEDIA_WIDTH,
        height: mediaHeight ?? DEFAULT_MEDIA_HEIGHT,
      }
    : undefined;

  return (
    <article className="team-lead-card" tabIndex={0}>
      <div className="team-lead-card__media" style={mediaStyle}>
        <img
          className="team-lead-card__img"
          src={imageSrc}
          alt={imageAlt}
          style={imgPos ? { objectPosition: imgPos } : undefined}
        />
      </div>
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
