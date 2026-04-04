import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './About.css';

const goals = [
  {
    title: 'Cross-Sector Partnerships',
    body: (
      <>
        Fostering meaningful collaborations among academia, communities, and
        government to identify coastal resilience priorities and drive collective
        action.
      </>
    ),
  },
  {
    title: 'Mapping the Resilience Landscape',
    body: (
      <>
        Systematically mapping the network of resilience plans, projects, and
        investments across Miami-Dade County to reveal gaps and opportunities
        for coordinated action across scales.
      </>
    ),
  },
  {
    title: 'Decision-Support Tools',
    body: (
      <>
        Designing an integrated dashboard that supports the collaborative
        evaluation of resilience interventions and scenarios and informs
        pathways toward a more resilient Miami-Dade.
      </>
    ),
  },
];

const scienceBlocks = [
  {
    id: 'about-science-block-concepts',
    heading:
      'Most Prominent Concepts Within the Greater Miami Resilience Plans',
    body:
      'We have systematically reviewed 22 resilience plans in the Greater Miami region, including those from the South Florida Water Management District, Southeast Florida Regional Climate Change Compact, Miami-Dade County, City of Miami, Miami Beach, and other local Councils. The diagram features the most prominent concepts from across these plans, revealing the overarching sentiments and priorities of local and regional authorities.',
    embedSrc: 'https://flo.uri.sh/visualisation/23520251/embed?auto=1',
    iframeTitle:
      'Word cloud of prominent concepts in Greater Miami resilience plans',
    frameClass: 'about-flourish-frame--1076-650',
  },
  {
    id: 'about-science-block-clusters',
    heading:
      'Clusters of Concepts Reveal Sectoral Orientation of the Resilience Plans',
    body:
      'While analyzing the 22 resilience plans in the Greater Miami region, we identified major clusters based on their core characteristics and associations. This interactive chart helps improve understanding of which sectors and themes (e.g., environment and climate, infrastructure and mobility, land and housing, health and equity, water and energy, governance) these plans focus on, as well as those that receive less emphasis.',
    embedSrc: 'https://flo.uri.sh/visualisation/23521400/embed?auto=1',
    iframeTitle:
      'Hierarchy chart of concept clusters in Greater Miami resilience plans',
  },
  {
    id: 'about-science-block-strategies',
    heading:
      'Key Strategies and Solutions Proposed through Resilience Plans',
    body:
      'We analyzed the range of strategies and solutions proposed in the resilience plans and ranked them based on frequency of occurrence. Given that drivers of resilience are complex, interconnected, and mutually reinforcing, we deconstruct the relationships and flows between resilience solutions. These resilience strategies encompass both nature-based solutions (e.g., expanding tree canopy, water conservation, restoring critical habitats, and beach nourishment) and re-engineering infrastructure systems (installing flood barriers, raising roads, and improving stormwater drainage). The dynamic chart reinforces that climate adaptation is not a linear process, and the complex dependencies and trade-offs involved across systems and strategies in resilience planning.',
    embedSrc: 'https://flo.uri.sh/visualisation/23575745/embed?auto=1',
    iframeTitle:
      'Sankey diagram of relationships between resilience strategies and solutions',
    frameClass: 'about-flourish-frame--1055-699',
  },
];

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
  {
    src: '/strategic-partners/miami-dade-county.png',
    alt: 'Miami-Dade County',
  },
  {
    src: '/strategic-partners/university-of-miami.png',
    alt: 'University of Miami',
  },
  {
    src: '/strategic-partners/coral-gables.webp',
    alt: 'City of Coral Gables',
    logoClass: 'partner-logo--boost partner-logo--coral',
  },
  {
    src: '/strategic-partners/miami-waterkeeper.png',
    alt: 'Miami Waterkeeper',
  },
  {
    src: '/strategic-partners/everglades-foundation.png',
    alt: 'The Everglades Foundation',
    logoClass: 'partner-logo--boost',
  },
];

export default function About() {
  const goalsListRef = useRef(null);

  useEffect(() => {
    const root = goalsListRef.current;
    if (!root) return;
    const items = [...root.querySelectorAll('.goal-reveal')];
    if (items.length === 0) return;

    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    if (reduceMotion) {
      items.forEach((el) => el.classList.add('goal-reveal--visible'));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('goal-reveal--visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2, rootMargin: '0px 0px -8% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className="about-root">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <header className="about-hero">
        <div className="about-hero-bg">
          <img
            src="/Images/about-scale-r-hero.png"
            alt="Aerial view of Biscayne Bay with boats and the Miami skyline"
          />
          <div className="about-hero-bg-overlay" />
        </div>

        <div className="about-hero-inner">
          <div className="about-hero-copy">
            <h1 className="about-hero-title">SCALE-R</h1>
            <p className="about-hero-tagline">
              Simulating Coastal Adaptation and Local Exposure for Enhanced Resilience
            </p>
            <p className="about-hero-sub">
              SCALE-R is an NSF-funded initiative at the University of Miami that
              advances a new paradigm for coastal adaptation — systematically
              mapping interventions and modeling their impact on disaster risk
              reduction across Miami-Dade County
            </p>
            <Link className="about-hero-cta" to="/dashboard">
              Visit the tool →
            </Link>
          </div>
        </div>
        <div className="about-hero-bottom-fade" aria-hidden="true" />
      </header>

      {/* ── The SCALE-R Difference ─────────────────────────────── */}
      <section
        className="about-difference"
        aria-labelledby="about-difference-heading"
      >
        <div className="about-difference-inner">
          <div className="about-difference-copy">
            <h2
              id="about-difference-heading"
              className="about-goals-heading"
            >
              The SCALE-R Difference
            </h2>
            <p className="body-text">
              While conventional resilience tools highlight risk and
              vulnerability, SCALE-R foregrounds the solutions and investments
              that drive community resilience.
            </p>
          </div>
        </div>
      </section>

      {/* ── Goals ──────────────────────────────────────────────── */}
      <section className="about-pillars" aria-labelledby="about-goals-heading">
        <div className="about-pillars-inner">
          <h2 id="about-goals-heading" className="about-goals-heading">
            Our Goals
          </h2>

          <div className="about-goals-list" ref={goalsListRef}>
            {goals.map((g, i) => (
              <article
                className={`goal-reveal ${i % 2 === 0 ? 'goal-reveal--from-left' : 'goal-reveal--from-right'}`}
                key={g.title}
              >
                <h3>{g.title}</h3>
                <p>{g.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Rigorous science (Flourish) ───────────────────────── */}
      <section
        className="about-science"
        aria-labelledby="about-science-heading"
      >
        <div className="about-science-inner">
          <h2 id="about-science-heading" className="about-science-title">
            A Tool Informed by Rigorous Science
          </h2>
          <p className="about-science-subtitle">
            Decoding Urban Climate Resilience Planning in Miami
          </p>

          {scienceBlocks.map((block) => (
            <article
              key={block.id}
              className="about-science-block"
              aria-labelledby={block.id}
            >
              <h3 id={block.id} className="about-science-block-heading">
                {block.heading}
              </h3>
              <p className="body-text">{block.body}</p>
              <div
                className={['about-flourish-frame', block.frameClass]
                  .filter(Boolean)
                  .join(' ')}
              >
                <iframe
                  src={block.embedSrc}
                  title={block.iframeTitle}
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ── Plan & Policy Context ────────────────────────────── */}
      <section className="about-policy">
        <div className="about-policy-inner">
          <span className="about-label">Research Foundation</span>
          <h2>Plan and policy context</h2>
          <p className="body-text">
            The team has systematically reviewed{' '}
            <strong>22 resilience plans</strong>{' '}
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
      <section className="about-partners" aria-labelledby="strategic-partners-heading">
        <div className="about-partners-header">
          <h2 id="strategic-partners-heading" className="about-partners-title">
            Strategic Partners
          </h2>
        </div>
        <div className="about-partners-marquee">
          <div className="marquee-container">
            <div className="marquee-track">
              {/* original set */}
              {partners.map((p) => (
                <div className="partner-item" key={p.alt}>
                  <img
                    className={['partner-logo', p.logoClass].filter(Boolean).join(' ')}
                    src={p.src}
                    alt={p.alt}
                    loading="lazy"
                    decoding="async"
                  />
                </div>
              ))}
              {/* duplicate for seamless loop */}
              {partners.map((p) => (
                <div
                  className="partner-item"
                  key={`dup-${p.alt}`}
                  aria-hidden="true"
                >
                  <img
                    className={['partner-logo', p.logoClass].filter(Boolean).join(' ')}
                    src={p.src}
                    alt=""
                    loading="lazy"
                    decoding="async"
                  />
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
            <strong>National Science Foundation</strong>{' '}
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
