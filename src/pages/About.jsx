import React from 'react';
import { Link } from 'react-router-dom';
import './About.css';

const engagementItems = [
  {
    title: 'Miami-Dade Environmental Stewards Workshop',
    detail:
      'Stephen P. Clark Government Center, September 26 2024 — county experts from Planning, Resilience, Transportation, Historic Preservation, Planning Research, and Zoning.',
  },
  {
    title: 'Palmer Trinity School Outreach',
    detail:
      'Interaction with Human Geography students and faculty (April 23 2025) to broaden awareness among younger learners.',
  },
  {
    title: 'UN World Urban Forum (WUF12)',
    detail:
      'Cairo, Egypt, November 4–8 2024 — presentation of project findings by Dr. Sarbeswar Praharaj.',
  },
  {
    title: 'Historic Preservation Training',
    detail:
      'Hands-on training with Miami-Dade Office of Historic Preservation on climate resilience, cultural landscapes, and conservation practice.',
  },
  {
    title: 'Smart City Expo Miami',
    detail:
      'September 23–25 2024 — talk titled "Anticipating Change and Designing Future-Ready Communities."',
  },
  {
    title: 'Habitat UNI Roundtable',
    detail:
      'Research and Academia Roundtable at WUF 2024, focused on urban climate resilience through interdisciplinary education.',
  },
];

const partners = [
  { icon: '🏛️', name: 'National Science Foundation' },
  { icon: '🎓', name: 'University of Miami' },
  { icon: '🏙️', name: 'Miami-Dade County' },
  { icon: '🌊', name: 'Rosenstiel School of Marine & Earth Science' },
  { icon: '🌿', name: 'UM Climate Resilience Institute' },
  { icon: '📐', name: 'UM School of Architecture' },
  { icon: '⚙️', name: 'UM College of Engineering' },
  { icon: '🌍', name: 'UN Habitat' },
];

export default function About() {
  return (
    <div className="about-root">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <header className="about-hero">
        <div className="about-hero-bg">
          <img
            src="/Images/about-stitch-hero-coast.jpg"
            alt="Aerial view of Miami-Dade County coastline"
          />
          <div className="about-hero-bg-overlay" />
        </div>

        <div className="about-hero-inner">
          <div>
            <span className="about-label">Project Overview</span>
            <h1 className="about-hero-title">
              The SCALE-R<br />
              <span className="accent">Mission.</span>
            </h1>
            <p className="about-hero-sub">
              Addressing the $2.7 trillion climate challenge through localized
              adaptation and community-driven intelligence in Miami-Dade County.
            </p>
            <Link className="about-hero-cta" to="/dashboard">
              Visit the tool →
            </Link>
          </div>
        </div>
      </header>

      {/* ── Core Pillars ─────────────────────────────────────── */}
      <section className="about-pillars">
        <div className="about-pillars-inner">
          <div className="about-pillars-header">
            <div>
              <span className="about-label">Core Pillars</span>
              <h2>
                Advancing Greater Miami's<br />Coastal Resilience
              </h2>
            </div>
            <p className="about-pillars-header-sub">
              Our framework for systemic change and community empowerment.
            </p>
          </div>

          <div className="about-pillars-grid">
            {/* Pillar 1 — large left (Stitch: groups) */}
            <div className="pillar-card pillar-card-large">
              <div className="pillar-icon-large">
                <span className="material-symbols-outlined" aria-hidden>
                  groups
                </span>
              </div>
              <h3>Equitable Partnerships</h3>
              <p>
                Building bridges between University of Miami researchers and
                neighborhood advocates to ensure solutions are culturally
                relevant, socially just, and center local stakeholder knowledge
                and lived experience.
              </p>
              <div className="pillar-bg-icon" aria-hidden>
                <span className="material-symbols-outlined">groups</span>
              </div>
            </div>

            {/* Pillar 2 — small right (Stitch: hub) */}
            <div className="pillar-card pillar-card-small">
              <div className="pillar-icon-small">
                <span className="material-symbols-outlined" aria-hidden>
                  hub
                </span>
              </div>
              <h3>Mapping the Network</h3>
              <p>
                Systematically reviewing and mapping the complex network of{' '}
                <strong style={{ color: 'rgba(255,255,255,0.9)' }}>
                  22 resilience plans
                </strong>{' '}
                across the Greater Miami region — visualizing social and
                ecological interdependencies to identify critical gaps.
              </p>
            </div>

            {/* Pillar 3 — full-width bottom (Stitch: analytics + trending_up) */}
            <div className="pillar-card pillar-card-wide">
              <div className="pillar-icon-circle">
                <span className="material-symbols-outlined" aria-hidden>
                  analytics
                </span>
              </div>
              <div className="pillar-text">
                <h3>Decision-Support Tools</h3>
                <p>
                  Designing an integrated decision-support dashboard providing
                  policymakers and civic leaders with real-time data
                  visualizations to make informed decisions about infrastructure,
                  protection, and resilience investment priorities.
                </p>
              </div>
              <div className="pillar-trailing-icon" aria-hidden>
                <span className="material-symbols-outlined">trending_up</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Plan & Policy Context ────────────────────────────── */}
      <section className="about-policy">
        <div className="about-policy-inner">
          <span className="about-label">Research Foundation</span>
          <h2>Plan and policy context</h2>
          <p className="body-text">
            The team has systematically reviewed{' '}
            <strong style={{ color: 'rgba(255,255,255,0.9)' }}>
              22 resilience plans
            </strong>{' '}
            across the Greater Miami region — including those from the South
            Florida Water Management District, Southeast Florida Regional
            Climate Change Compact, Miami-Dade County, the City of Miami, Miami
            Beach, and other local jurisdictions. The analysis reveals how plans
            emphasize themes across six major clusters:
          </p>
          <div className="about-badges">
            {[
              { label: 'Governance & Society', color: '#455a64' },
              { label: 'Environment & Climate', color: '#2e7d32' },
              { label: 'Infrastructure & Mobility', color: '#1565c0' },
              { label: 'Land & Housing', color: '#6d4c41' },
              { label: 'Water & Energy', color: '#00838f' },
              { label: 'Health & Equity', color: '#ad1457' },
            ].map((b) => (
              <span
                key={b.label}
                className="about-badge"
                style={{ background: b.color }}
              >
                {b.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Community Engagement ─────────────────────────────── */}
      <section className="about-engagement">
        <div className="about-engagement-inner">
          <span className="about-label">Outreach & Impact</span>
          <h2>Community engagement</h2>
          <div className="engagement-grid">
            {engagementItems.map((e, i) => (
              <div className="engagement-card" key={i}>
                <div className="engagement-num">{i + 1}</div>
                <div>
                  <h4>{e.title}</h4>
                  <p>{e.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Scrolling Partners ───────────────────────────────── */}
      <section className="about-partners">
        <div className="about-partners-inner">
          <span className="partners-label">Strategic Partners</span>
          <div className="marquee-container">
            <div className="marquee-track">
              {/* original set */}
              {partners.map((p) => (
                <div className="partner-item" key={p.name}>
                  <span className="icon">{p.icon}</span>
                  <span className="name">{p.name}</span>
                </div>
              ))}
              {/* duplicate for seamless loop */}
              {partners.map((p) => (
                <div className="partner-item" key={`dup-${p.name}`}>
                  <span className="icon">{p.icon}</span>
                  <span className="name">{p.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Acknowledgment ───────────────────────────────────── */}
      <section className="about-ack">
        <div className="about-ack-inner">
          <p>
            This material is based upon work supported by the{' '}
            <strong style={{ color: 'rgba(255,255,255,0.8)' }}>
              National Science Foundation
            </strong>{' '}
            under Grant No.&nbsp;2435008. Any opinions, findings, conclusions, or
            recommendations expressed are those of the authors and do not
            necessarily reflect the views of the NSF.{' '}
            <a
              href="https://geography.as.miami.edu/research/geo_labs/scale-r/index.html"
              target="_blank"
              rel="noopener noreferrer"
            >
              Visit the SCALE-R lab page →
            </a>
          </p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="about-footer">
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
            <Link to="/docs">Technical Documentation</Link>
            <Link to="/dashboard">Dashboard</Link>
          </div>
          <div className="about-footer-col">
            <h5 className="about-footer-heading">Legal &amp; Portal</h5>
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Partner Portal</a>
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

    </div>
  );
}
