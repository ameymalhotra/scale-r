import React from 'react';
import { Link } from 'react-router-dom';

export default function TeamPageFooter() {
  return (
    <footer className="about-footer about-section--on-um-green">
      <div className="about-footer-inner">
        <div className="about-footer-brand">
          <div className="about-footer-logo">SCALE-R</div>
          <p>
            © {new Date().getFullYear()} SCALE-R Miami-Dade.
            <br />
            Supported by NSF &amp; University of Miami.
          </p>
        </div>
        <div className="about-footer-col">
          <h5 className="about-footer-heading">Navigation</h5>
          <Link to="/about">About the project</Link>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/team">Team</Link>
        </div>
        <div className="about-footer-col">
          <h5 className="about-footer-heading">Connect</h5>
          <a href="mailto:spraharaj@miami.edu">Contact Us</a>
          <div className="about-footer-social">
            <a
              href="https://geography.as.miami.edu/research/geo_labs/scale-r/index.html"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="SCALE-R lab website"
            >
              <span className="material-symbols-outlined" aria-hidden>
                public
              </span>
            </a>
            <a href="mailto:spraharaj@miami.edu" aria-label="Email SCALE-R">
              <span className="material-symbols-outlined" aria-hidden>
                mail
              </span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
