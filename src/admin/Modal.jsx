import React, { useEffect, useRef } from 'react';

export default function Modal({ title, onClose, children, footer, busy = false }) {
  const panelRef = useRef(null);
  const latest = useRef({ onClose, busy });
  latest.current = { onClose, busy };

  useEffect(() => {
    const previous = document.activeElement;
    panelRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape' && !latest.current.busy) latest.current.onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      previous?.focus?.();
    };
  }, []);

  return (
    <div className="admin-modal-backdrop">
      <div
        ref={panelRef}
        className="admin-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-modal-title"
        tabIndex={-1}
      >
        <header className="admin-modal__head">
          <h2 id="admin-modal-title">{title}</h2>
          <button type="button" className="admin-btn admin-btn--small" onClick={onClose} disabled={busy}>
            Close
          </button>
        </header>
        <div className="admin-modal__body">{children}</div>
        {footer && <footer className="admin-modal__foot">{footer}</footer>}
      </div>
    </div>
  );
}
