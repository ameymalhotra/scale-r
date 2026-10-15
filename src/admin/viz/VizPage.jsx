import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import gapMarkup from './gapMap.html?raw';
import exposureMarkup from './exposureMap.html?raw';
import { mount as mountGap } from './gapMap.js';
import { mount as mountExposure } from './exposureMap.js';
import './gapMap.css';
import './exposureMap.css';

// Draft visualizations for faculty review. Reachable only from the admin, so the
// public site never links to or loads them.
const VIEWS = {
  gap: { className: 'viz-gap', markup: gapMarkup, mount: mountGap, title: 'Resilience gap map' },
  exposure: { className: 'viz-exposure', markup: exposureMarkup, mount: mountExposure, title: 'Exposure animations' },
};

export default function VizPage({ view }) {
  const { className, markup, mount, title } = VIEWS[view];
  const navigate = useNavigate();

  useEffect(() => {
    document.title = `Draft · ${title} · SCALE-R admin`;
    return mount();
  }, [mount, title]);

  // The panel links are plain markup; route them in-app instead of reloading.
  const onClick = (event) => {
    const link = event.target.closest('a[href^="/admin"]');
    if (!link) return;
    event.preventDefault();
    navigate(link.getAttribute('href'));
  };

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div key={view} className={className} onClick={onClick} dangerouslySetInnerHTML={{ __html: markup }} />
  );
}
