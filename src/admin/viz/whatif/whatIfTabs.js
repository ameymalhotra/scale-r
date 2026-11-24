// Tab rules for the Flood What-If side column (D-213, D-214). Pure functions, so the rules are tested
// without a map: the view only carries out what these return.

export const TABS = ['seawall', 'elevation', 'examples'];

/**
 * What happens when a tab button is clicked.
 * Clicking the open tab closes it. Leaving Examples takes the examples away and brings back the
 * user's own projects; opening Examples sets the user's projects aside and loads the examples.
 */
export function tabChange(current, clicked) {
  const next = current === clicked ? null : clicked;
  return {
    next,
    leaveExamples: current === 'examples' && next !== 'examples',
    enterExamples: next === 'examples' && current !== 'examples',
  };
}

/** The projects to show after leaving Examples: the user's own, never an example. */
export function projectsAfterExamples(saved) {
  return (saved || []).filter((p) => !p.example);
}

/** The user's own projects to set aside when Examples opens (kept from an earlier set-aside if any). */
export function setAside(projects, saved) {
  return saved || projects.filter((p) => !p.example);
}

/** One numbered marker per project: what the map must show for a list of projects (D-214). */
export function markerList(projects, sel, centerOf) {
  return projects.map((p, k) => ({ k, num: k + 1, sel: k === sel, at: centerOf(p), name: p.name }))
    .filter((m) => m.at);
}
