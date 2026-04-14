import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import './About.css';

/** Shared with footer / contact blocks */
const SCALE_R_CONTACT_EMAIL = 'spraharaj@miami.edu';

const goals = [
  {
    title: 'Cross-Sector Partnerships',
    icon: 'groups',
    photoSrc: '/Images/goals/cross-sector.jpg',
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
    icon: 'hub',
    photoSrc: '/Images/goals/mapping.png',
    cardClassName: 'about-goal-card--scrim-middle',
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
    icon: 'analytics',
    photoSrc: '/Images/goals/decision-support-tools.png',
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
  {
    id: 'about-science-block-indicators',
    heading:
      'Which Indicators Would be Useful to Visualize in the New Resilience Tool',
    body:
      'To address the knowledge gap in reconciling the diverse capabilities, goals, scope, and limitations of various resilience decision-support tools, we performed a critical assessment of 30 selected climate resilience tools in the U.S. We identified over 264 indicators across these tools and organized those into six domains (social, economic, environmental, institutional, infrastructure, and health). The Radar chart shows the percentage of indicators falling into each domain. It provides essential guidance for designing future resilience tools, outlining the types of indicators that should be prioritized while addressing existing knowledge gaps.',
    embedSrc: 'https://flo.uri.sh/visualisation/23183668/embed?auto=1',
    iframeTitle:
      'Radar chart of resilience indicator domains across U.S. climate resilience tools',
    frameClass: 'about-flourish-frame--1076-678',
  },
  {
    id: 'about-science-block-decision-support',
    heading:
      'Ensuring a Robust Decision-Support Capability on the Resilience Tool',
    body:
      'Analyzing the 30 selected climate resilience tools in the U.S., we are examining which features enhance user engagement and trust with resilience tools that could support collaborative decision-making. Assessment of existing tools on a range of decision-support criteria informs our design framework and the scope for innovation in the new resilience tool we are developing through this project.',
    embedSrc:
      'https://public.tableau.com/views/AnalysisofResilienceTools/Dashboard1?:embed=y&:showVizHome=no&:hideTabs=y&:toolbar=yes&:origin=viz_share_link',
    iframeTitle:
      'Tableau dashboard: analysis of U.S. climate resilience tools',
    frameClass: 'about-tableau-frame--850-927',
    iframeWidth: 850,
    iframeHeight: 927,
  },
];

const engagementItems = [
  {
    kicker: 'Community engagement',
    title: 'Miami-Dade Environmental Stewards workshop',
    detail:
      'A workshop was held at the Stephen P. Clark Government Center on 26/9/2024 with the Miami-Dade County experts, enabling a discussion between leaders from the Divisions of Planning, Resilience, Transportation, Historic Preservation, Planning Research, and Zoning with the researchers and students involved in this project.',
    imageSrc: '/Images/community-engagement/workshop-new.png',
    imageAlt:
      'Meeting room workshop with participants seated around a long table facing a presentation screen',
    imageObjectPosition: 'center center',
  },
  {
    kicker: 'Community engagement',
    title: 'Awareness and engagement with high school students',
    detail:
      'An interaction with the Human Geography students and faculty was organized at the Palmer Trinity School on April 23, 2025, enabling greater awareness and knowledge dissemination among the young learners in the broader community.',
    imageSrc: '/Images/community-engagement/workshop-replacement.png',
    imageAlt:
      'Classroom presentation with students seated at desks watching a climate change talk',
  },
  {
    kicker: 'Community engagement',
    title: 'Presentation to leaders in the field at the UN World Urban Forum',
    detail:
      'The PI, Dr. Sarbeswar Praharaj, shared the findings from this project at the World Urban Forum 2024 (WUF12) organized by the United Nations Human Settlement Program from 4-8 November 2024, in Cairo, Egypt.',
    imageSrc: '/Images/community-engagement/presentation.jpg',
    imageAlt:
      'Presentation at the UN World Urban Forum with attendees facing a screen',
  },
  {
    kicker: 'Community engagement',
    title: 'Hands-on training for the next generation of students',
    detail:
      'We partnered with the MDC Office of Historic Preservation, providing hands-on training for graduate researchers and students on how climate resilience impacts cultural landscapes and how conservation practices and advocacy can help address these challenges.',
    imageSrc: '/Images/community-engagement/hands-on.jpg',
    imageAlt:
      'Hands-on student training session gathered around a table with materials',
  },
  {
    kicker: 'Community engagement',
    title: 'Global impact through interdisciplinary education and curricula',
    detail:
      "The PI joined a premier Research and Academia Roundtable at the UN-Habitat's World Urban Forum 2024, as a member of Habitat UNI (UN-Habitat's network for university/research partners), and his contribution was focused on advancing urban climate resilience through interdisciplinary education and curricula.",
    imageSrc: '/Images/community-engagement/global-impact.jpg',
    imageAlt:
      'Roundtable and conference setting representing interdisciplinary education at the World Urban Forum',
    imageObjectPosition: '78% center',
  },
  {
    kicker: 'Community engagement',
    title: 'Disseminating knowledge with the Greater Miami stakeholders',
    detail:
      'We are making efforts to engage with key stakeholders and networks to share our findings from this project and gather valuable feedback. One such platform was the Smart City Expo Miami (23 – 25 September 2024), where the PI delivered a talk titled "Anticipating Change and Designing Future-Ready Communities."',
    imageSrc: '/Images/community-engagement/disseminating.jpg',
    imageAlt:
      'Audience watching a presentation at Smart City Expo Miami',
    imageObjectPosition: '32% center',
  },
];

const recentEvents = [
  {
    datetime: 'March 17, 2026 | 8:30 am to 9:50 am',
    session: 'Environmental Justice and Coastal Inequities',
    presentation:
      'Simulating Coastal Adaptation and Local Exposure for Enhanced Resilience (SCALE-R) — Dr. Sarbeswar Praharaj',
    location:
      'American Association of Geographers – AAG Annual Meeting, Union Square 12, 4th Floor, Hilton, Tower 3, San Francisco',
    imageSrc: '/Images/recent-events/aag-2026-session.png',
    imageAlt:
      'AAG 2026 San Francisco promotional graphic for the core session Environmental Justice and Coastal Inequities',
  },
  {
    datetime: 'October 15, 2025 | 11:00 am to 12:30 pm',
    session: 'Geospatial Workflows for a Safe and Equitable World',
    presentation:
      'Using geospatial information dashboards to advance urban resilience — Dr. Sarbeswar Praharaj',
    location:
      'ESRI and University of Southern California, USC Spatial Sciences Institute, Los Angeles',
    imageSrc: '/Images/recent-events/security-first-book.png',
    imageAlt:
      'Book cover for Security First: Geospatial Workflows for a Safe and Equitable World, Esri Press',
    ctaHref: 'https://indiepubs.com/products/security-first-9781589487857',
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
  const [activeEngagementIndex, setActiveEngagementIndex] = useState(0);

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

    const scrollRoot =
      typeof document !== 'undefined' &&
      document.documentElement.classList.contains('route-dashboard')
        ? document.querySelector('main.app-main-scroll')
        : null;

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('goal-reveal--visible');
            io.unobserve(entry.target);
          }
        });
      },
      {
        ...(scrollRoot ? { root: scrollRoot } : {}),
        /* Low threshold + no shrink root: the right column can fall below 20%
           intersection when partially clipped, so it never received --visible. */
        threshold: 0.01,
        rootMargin: '0px',
      },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const handleEngagementStep = (direction) => {
    setActiveEngagementIndex((current) => {
      const nextIndex = current + direction;
      return Math.min(
        Math.max(nextIndex, 0),
        engagementItems.length - 1,
      );
    });
  };
  const canGoToPreviousEngagement = activeEngagementIndex > 0;
  const canGoToNextEngagement =
    activeEngagementIndex < engagementItems.length - 1;

  return (
    <div className="about-root">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <header className="about-hero">
        <div className="about-hero-bg">
          <img
            src="/Images/about-scale-r-hero.jpg"
            alt="Aerial view of Biscayne Bay with boats and the Miami skyline"
          />
        </div>

        <div className="about-hero-inner">
          <div className="about-hero-copy">
            <h1 className="about-hero-title about-hero-frost">SCALE-R</h1>
            <p className="about-hero-tagline about-hero-frost">
              Simulating Coastal Adaptation and Local Exposure for Enhanced Resilience
            </p>
            <p className="about-hero-sub">
              <span className="about-hero-sub-highlight about-hero-frost">
                SCALE-R is an NSF-funded initiative at the University of Miami that
                advances a new paradigm for coastal adaptation — systematically
                mapping interventions and modeling their impact on disaster risk
                reduction across Miami-Dade County
              </span>
            </p>
            <Link className="about-hero-cta" to="/dashboard">
              Visit the SCALE-R Dashboard →
            </Link>
          </div>
        </div>
      </header>

      {/* ── The SCALE-R Difference ─────────────────────────────── */}
      <section
        className="about-difference about-section--on-um-green"
        aria-labelledby="about-difference-heading"
      >
        <div className="about-difference-inner">
          <div className="about-difference-copy">
            <h2
              id="about-difference-heading"
              className="about-goals-heading"
            >
              <span className="about-heading-highlight">
                The SCALE-R Difference
              </span>
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
      <section
        className="about-pillars about-section--on-um-orange"
        aria-labelledby="about-goals-heading"
      >
        <div className="about-pillars-inner">
          <h2 id="about-goals-heading" className="about-goals-heading">
            <span className="about-heading-highlight">Our Goals</span>
          </h2>

          <div className="about-goals-grid" ref={goalsListRef}>
            {goals.map((g, i) => (
              <div
                key={g.title}
                className={[
                  'about-goal-reveal-wrap',
                  'goal-reveal',
                  i % 2 === 0 ? 'goal-reveal--from-left' : 'goal-reveal--from-right',
                ].join(' ')}
              >
              <article
                className={[
                  'about-goal-card',
                  'about-goal-card--photo',
                  g.cardClassName,
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <div className="about-goal-card__media" aria-hidden>
                  <img
                    className="about-goal-card__media-img"
                    src={g.photoSrc}
                    alt=""
                    loading="eager"
                    decoding="async"
                  />
                  <div className="about-goal-card__media-scrim" />
                </div>
                <div className="about-goal-icon">
                  <span className="material-symbols-outlined" aria-hidden>
                    {g.icon}
                  </span>
                </div>
                <h3>{g.title}</h3>
                <p>{g.body}</p>
              </article>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Rigorous science (Flourish) ───────────────────────── */}
      <section
        className="about-science about-section--on-um-green"
        aria-labelledby="about-science-heading"
      >
        <div className="about-science-inner">
          <h2 id="about-science-heading" className="about-science-title">
            <span className="about-heading-highlight">
              A Tool Informed by Rigorous Science
            </span>
          </h2>

          <div className="about-science-blocks">
            {scienceBlocks.map((block) => (
              <article
                key={block.id}
                className="about-science-block"
                aria-labelledby={block.id}
              >
                <h3
                  id={block.id}
                  className="about-science-block-heading"
                >
                  {block.heading}
                </h3>
                <p className="body-text">{block.body}</p>
                <div
                  className={['about-flourish-frame', block.frameClass]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {block.embedSrc ? (
                    block.frameClass?.includes('tableau-frame') ? (
                      <div className="about-tableau-scale-wrap">
                        <iframe
                          className="about-tableau-embed-iframe"
                          src={block.embedSrc}
                          title={block.iframeTitle}
                          loading="lazy"
                          referrerPolicy="no-referrer-when-downgrade"
                          scrolling="no"
                        />
                      </div>
                    ) : (
                      <iframe
                        src={block.embedSrc}
                        title={block.iframeTitle}
                        loading="lazy"
                        referrerPolicy="no-referrer-when-downgrade"
                        {...(block.iframeWidth != null && block.iframeHeight != null
                          ? {
                              width: block.iframeWidth,
                              height: block.iframeHeight,
                            }
                          : {})}
                      />
                    )
                  ) : (
                    <div
                      className="about-flourish-placeholder"
                      role="status"
                      aria-label={block.iframeTitle}
                    >
                      <p>Visualization coming soon</p>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Community Engagement ─────────────────────────────── */}
      <section
        className="about-engagement about-section--on-um-orange"
        aria-labelledby="about-engagement-heading"
      >
        <div className="about-engagement-inner">
          <h2 id="about-engagement-heading">
            <span className="about-heading-highlight">
              Community engagement
            </span>
          </h2>
          <p className="engagement-intro">
            Workshops, outreach, training, and public presentations that connect
            SCALE-R research with practitioners, students, and decision-makers.
          </p>

          <article
            className="engagement-spotlight"
            aria-label="Community engagement highlights"
          >
            <div className="engagement-spotlight__topline">
              <span className="engagement-spotlight__count" aria-live="polite">
                {String(activeEngagementIndex + 1).padStart(2, '0')}
                <span aria-hidden> / </span>
                {String(engagementItems.length).padStart(2, '0')}
              </span>
              <div className="engagement-spotlight__rule" aria-hidden />
              <div className="engagement-spotlight__controls">
                <button
                  type="button"
                  className="engagement-spotlight__control"
                  onClick={() => handleEngagementStep(-1)}
                  aria-label="Show previous community engagement card"
                  disabled={!canGoToPreviousEngagement}
                >
                  <span className="material-symbols-outlined" aria-hidden>
                    arrow_back_ios_new
                  </span>
                </button>
                <button
                  type="button"
                  className="engagement-spotlight__control"
                  onClick={() => handleEngagementStep(1)}
                  aria-label="Show next community engagement card"
                  disabled={!canGoToNextEngagement}
                >
                  <span className="material-symbols-outlined" aria-hidden>
                    arrow_forward_ios
                  </span>
                </button>
              </div>
            </div>

            <div className="engagement-spotlight__viewport">
              <div
                className="engagement-spotlight__track"
                style={{
                  '--engagement-active': String(activeEngagementIndex),
                }}
              >
                {engagementItems.map((item, index) => (
                  <section
                    key={item.title}
                    className={[
                      'engagement-card',
                      index === activeEngagementIndex && 'engagement-card--active',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    data-engagement-index={index}
                    aria-hidden={index !== activeEngagementIndex}
                  >
                    <div className="engagement-card__media">
                      {item.imageSrc ? (
                        <img
                          src={item.imageSrc}
                          alt={item.imageAlt}
                          loading={index === 0 ? 'eager' : 'lazy'}
                          fetchPriority={index === 0 ? 'high' : 'auto'}
                          decoding="async"
                          style={
                            item.imageObjectPosition
                              ? { objectPosition: item.imageObjectPosition }
                              : undefined
                          }
                        />
                      ) : (
                        <div
                          className="engagement-card__media-placeholder"
                          aria-label="Community engagement image placeholder"
                        >
                          <span className="material-symbols-outlined" aria-hidden>
                            image
                          </span>
                          Image coming soon
                        </div>
                      )}
                    </div>

                    <div className="engagement-card__content">
                      <p className="engagement-card__kicker">{item.kicker}</p>
                      <h3>{item.title}</h3>
                      <blockquote className="engagement-card__quote">
                        {item.detail}
                      </blockquote>
                    </div>
                  </section>
                ))}
              </div>
            </div>
          </article>
        </div>
      </section>

      {/* ── Recent events ─────────────────────────────────────── */}
      <section
        className="about-recent-events about-section--on-um-green"
        aria-labelledby="about-recent-events-heading"
      >
        <div className="about-recent-events-inner">
          <h2 id="about-recent-events-heading">
            <span className="about-heading-highlight">Recent events</span>
          </h2>
          <div className="recent-events-list">
            {recentEvents.map((event, i) => {
              const ctaHref =
                event.ctaHref ?? `mailto:${SCALE_R_CONTACT_EMAIL}`;
              const ctaIsExternal = /^https?:\/\//.test(ctaHref);
              return (
              <article
                key={i}
                className={[
                  'recent-event-card',
                  event.imageSrc ? 'recent-event-card--has-image' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {event.imageSrc ? (
                  <div className="recent-event-card__media">
                    <img
                      className="recent-event-card__img"
                      src={event.imageSrc}
                      alt={event.imageAlt ?? ''}
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                ) : null}
                <div className="recent-event-card__body">
                  <h3 className="recent-event-presentation">{event.presentation}</h3>
                  <div className="recent-event-card__details">
                    <p className="recent-event-meta-row recent-event-meta-row--datetime">
                      <span
                        className="material-symbols-outlined recent-event-meta-icon"
                        aria-hidden
                      >
                        calendar_month
                      </span>
                      <span className="recent-event-datetime-chip">{event.datetime}</span>
                    </p>
                    <p className="recent-event-session">
                      <span className="recent-event-session-label">Session</span>
                      {': '}
                      {event.session}
                    </p>
                    <p className="recent-event-meta-row recent-event-meta-row--location">
                      <span
                        className="material-symbols-outlined recent-event-meta-icon"
                        aria-hidden
                      >
                        location_on
                      </span>
                      <span className="recent-event-meta-text">{event.location}</span>
                    </p>
                  </div>
                  <a
                    className="recent-event-contact-btn"
                    href={ctaHref}
                    {...(ctaIsExternal
                      ? { target: '_blank', rel: 'noopener noreferrer' }
                      : {})}
                  >
                    <span className="material-symbols-outlined" aria-hidden>
                      {ctaIsExternal ? 'open_in_new' : 'mail'}
                    </span>
                    Learn More
                  </a>
                </div>
              </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Scrolling Partners ───────────────────────────────── */}
      <section
        className="about-partners about-section--on-light-um"
        aria-labelledby="strategic-partners-heading"
      >
        <div className="about-partners-header">
          <h2 id="strategic-partners-heading" className="about-partners-title">
            <span className="about-heading-highlight">Strategic Partners</span>
          </h2>
        </div>
        <div className="about-partners-marquee">
          <div className="marquee-container">
            <div className="marquee-track">
              <div className="marquee-group">
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
              </div>
              <div className="marquee-group" aria-hidden="true">
                {partners.map((p) => (
                  <div className="partner-item" key={`dup-${p.alt}`}>
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
        </div>
      </section>

      {/* ── Acknowledgment ───────────────────────────────────── */}
      <section
        className="about-ack about-section--on-ack-light"
        aria-labelledby="about-ack-heading"
      >
        <div className="about-ack-inner">
          <h2 id="about-ack-heading">
            <span className="about-heading-highlight">Funding Acknowledgement</span>
          </h2>
          <p>
            This project is based upon work supported by the National Science
            Foundation under{' '}
            <a
              className="about-ack-nsf-link"
              href="https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2435008&HistoricalAwards=false"
              target="_blank"
              rel="noopener noreferrer"
            >
              Grant Number
            </a>{' '}
            (2435008).
          </p>
          <p className="about-ack-disclaimer">
            <strong>Disclaimer:</strong> Any opinions, findings, and conclusions
            or recommendations expressed in this website are those of the
            investigator(s) and do not necessarily reflect the views of the
            National Science Foundation.
          </p>
          <Link className="about-hero-cta" to="/dashboard">
            Visit the SCALE-R Dashboard →
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
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
            <a href={`mailto:${SCALE_R_CONTACT_EMAIL}`}>Contact Us</a>
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
              <a
                href={`mailto:${SCALE_R_CONTACT_EMAIL}`}
                aria-label="Email SCALE-R"
              >
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
