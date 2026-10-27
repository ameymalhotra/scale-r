import React, { useEffect } from 'react';
import markup from '../exposure/exposureMap.html?raw';
import { mount } from '../exposure/exposureMap.js';
import '../exposure/exposureMap.css';

/** Animated hazard exposure map: sea level rise, storm surge and surface heat over people and projects. */
export default function Exposure() {
  useEffect(() => mount(), []);

  // The map and panel are plain markup driven by exposureMap.js, which owns their state.
  return <div className="viz-exposure" dangerouslySetInnerHTML={{ __html: markup }} />;
}
