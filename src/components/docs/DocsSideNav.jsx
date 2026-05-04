import React, { useEffect, useRef, useState } from 'react';

/** Matches `.docs-section { scroll-margin-top: 96px }` in TechnicalDocs.css */
const ACTIVATION_OFFSET = 96;

export default function DocsSideNav({ sections }) {
  const [activeId, setActiveId] = useState(sections[0]?.id ?? '');
  const mobileScrollerRef = useRef(null);

  useEffect(() => {
    const ids = sections.map((s) => s.id);
    if (ids.length === 0) return undefined;

    const updateActive = () => {
      const scrollY = window.scrollY;
      const line = scrollY + ACTIVATION_OFFSET + 2;
      const docHeight = document.documentElement.scrollHeight;
      const viewBottom = scrollY + window.innerHeight;

      if (viewBottom >= docHeight - 4) {
        setActiveId(ids[ids.length - 1]);
        return;
      }

      let active = ids[0];
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        const top = el.getBoundingClientRect().top + scrollY;
        if (top <= line) {
          active = id;
        }
      }
      setActiveId(active);
    };

    updateActive();
    const rafId = requestAnimationFrame(() => {
      updateActive();
    });

    window.addEventListener('scroll', updateActive, { passive: true });
    window.addEventListener('resize', updateActive, { passive: true });

    const mainEl = document.querySelector('.docs-content');
    const resizeObserver =
      typeof ResizeObserver !== 'undefined' && mainEl
        ? new ResizeObserver(() => {
            requestAnimationFrame(updateActive);
          })
        : null;
    if (resizeObserver && mainEl) {
      resizeObserver.observe(mainEl);
    }

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('scroll', updateActive);
      window.removeEventListener('resize', updateActive);
      resizeObserver?.disconnect();
    };
  }, [sections]);

  useEffect(() => {
    const scroller = mobileScrollerRef.current;
    if (!scroller) return;
    const activeChip = scroller.querySelector(
      `[data-chip-id="${activeId}"]`,
    );
    if (activeChip && typeof activeChip.scrollIntoView === 'function') {
      activeChip.scrollIntoView({
        behavior: 'smooth',
        inline: 'center',
        block: 'nearest',
      });
    }
  }, [activeId]);

  const scrollTo = (id) => (event) => {
    event.preventDefault();
    const target = document.getElementById(id);
    if (!target) return;
    const top =
      target.getBoundingClientRect().top +
      window.pageYOffset -
      ACTIVATION_OFFSET;
    window.scrollTo({ top, behavior: 'smooth' });
    if (typeof history !== 'undefined' && history.replaceState) {
      history.replaceState(null, '', `#${id}`);
    }
  };

  return (
    <>
      <nav
        className="docs-sidenav"
        aria-label="Technical documentation sections"
      >
        <p className="docs-sidenav__label">On this page</p>
        <ul className="docs-sidenav__list">
          {sections.map((section, index) => {
            const isActive = activeId === section.id;
            return (
              <li className="docs-sidenav__item" key={section.id}>
                <a
                  href={`#${section.id}`}
                  className={`docs-sidenav__link${
                    isActive ? ' docs-sidenav__link--active' : ''
                  }`}
                  onClick={scrollTo(section.id)}
                  aria-current={isActive ? 'true' : undefined}
                >
                  <span className="docs-sidenav__link-index" aria-hidden>
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  {section.label}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <div
        className="docs-sidenav-mobile"
        aria-label="Technical documentation sections (mobile)"
      >
        <div
          className="docs-sidenav-mobile__scroll"
          ref={mobileScrollerRef}
        >
          {sections.map((section) => {
            const isActive = activeId === section.id;
            return (
              <button
                key={section.id}
                type="button"
                data-chip-id={section.id}
                className={`docs-sidenav-mobile__chip${
                  isActive ? ' docs-sidenav-mobile__chip--active' : ''
                }`}
                onClick={scrollTo(section.id)}
                aria-current={isActive ? 'true' : undefined}
              >
                {section.label}
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
