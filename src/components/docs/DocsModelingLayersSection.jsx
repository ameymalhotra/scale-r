import React from 'react';

const NRI_RATINGS = [
  {
    label: 'Very Low',
    percentile: '0–20%',
    description:
      'Minimal expected annual losses; low hazard exposure and low social vulnerability; strong baseline resilience.',
    accent: '#2e6d54',
  },
  {
    label: 'Relatively Low',
    percentile: '20–40%',
    description:
      'Limited hazard exposure with generally low losses; moderate vulnerability and adequate resilience capacity.',
    accent: '#3d8b5c',
  },
  {
    label: 'Relatively Moderate',
    percentile: '40–60%',
    description:
      'Moderate exposure to hazards with potential for economic and infrastructure impacts; mixed vulnerability and resilience conditions.',
    accent: '#c4a000',
  },
  {
    label: 'Relatively High',
    percentile: '60–80%',
    description:
      'Elevated hazard exposure and expected losses; higher social vulnerability and constrained resilience capacity.',
    accent: '#d97706',
  },
  {
    label: 'Very High',
    percentile: '80–100%',
    description:
      'Significant and recurrent hazard exposure with high expected losses; high vulnerability and limited resilience capacity.',
    accent: '#b91c1c',
  },
];

const CRE_COMPONENTS = [
  { icon: 'payments', label: 'Poverty status' },
  { icon: 'family_restroom', label: 'Number of caregivers in the household' },
  { icon: 'bedroom_parent', label: 'Unit-level crowding' },
  { icon: 'translate', label: 'Communication barrier' },
  { icon: 'work', label: 'Employment' },
  { icon: 'accessibility_new', label: 'Disability status' },
  { icon: 'health_and_safety', label: 'Health insurance coverage' },
  { icon: 'elderly', label: 'Age (65+)' },
  { icon: 'directions_car', label: 'Vehicle access' },
  { icon: 'wifi', label: 'Broadband internet access' },
];

const CRITICAL_INFRA_TYPES = [
  {
    icon: 'local_hospital',
    label: 'Emergency and medical services',
    accent: '#0e7aad',
    text:
      'Essential facilities that support immediate response and medical care during and after hazard events.',
  },
  {
    icon: 'home_health',
    label: 'Risk and recovery shelters',
    accent: '#127ea7',
    text:
      'Locations designated for sheltering populations at risk and supporting post-disaster recovery operations.',
  },
  {
    icon: 'groups',
    label: 'Community centers',
    accent: '#2e6d54',
    text:
      'Hubs for coordination, information, and community support within local networks during emergencies.',
  },
  {
    icon: 'route',
    label: 'Designated evacuation routes',
    accent: '#52606b',
    text:
      'Mapped corridors that support orderly movement away from hazard zones and toward safer areas.',
  },
];

export default function DocsModelingLayersSection() {
  return (
    <section
      id="modeling-layers"
      className="docs-section docs-section--gray"
      aria-labelledby="docs-modeling-heading"
    >
      <h2 id="docs-modeling-heading" className="docs-section__title">
        <span className="docs-section__title-highlight">
          Supporting Modeling Layers
        </span>
      </h2>
      <p className="docs-section__lede">
        The supporting modeling layers integrated into the SCALE-R platform
        include the FEMA National Risk Index and the Census Community
        Resilience Estimates, which provide spatially explicit measures of hazard
        exposure, social vulnerability, and community resilience at the census
        tract level. The integration of local-scale Critical Infrastructure
        datasets further enables users to identify and assess the distribution
        of essential facilities, including emergency services. Combined with
        project-level data, these modeling layers support comparative assessment
        of risk conditions and enable evaluation of how resilience investments
        align with underlying patterns of exposure and vulnerability.
      </p>

      <div
        className="docs-subsection"
        aria-labelledby="docs-modeling-nri-heading"
      >
        <h3 id="docs-modeling-nri-heading" className="docs-subsection__title">
          FEMA National Risk Index
        </h3>
        <div className="docs-subsection__prose">
          <p>
            The FEMA National Risk Index (NRI) is a nationally consistent,
            multi-hazard dataset designed to quantify baseline natural hazard risk
            across U.S. communities. It measures risk by combining two components:
            Expected Annual Loss from natural hazards and a Community Risk
            Factor. Expected Annual Loss is derived from hazard frequency,
            exposure, and historical loss ratios, while the Community Risk Factor
            reflects the interaction between social vulnerability and community
            resilience. In the risk factor formulation, social vulnerability
            represents population sensitivity and susceptibility to harm, acting
            as a consequence-amplifying factor, whereas community resilience
            captures adaptive capacity that reduces impacts. The resulting index
            provides spatially explicit risk scores at the census-tract level,
            enabling standardized comparisons across locations and hazards.
          </p>
          <p>
            NRI ratings represent relative classifications that convert
            percentile-based risk scores into five standardized qualitative
            categories. Within the SCALE-R platform, integrating the National
            Risk Index enhances analytical capability by providing a consistent
            baseline against which resilience investments can be evaluated. In
            Miami-Dade County, just over one-third of census tracts fall into
            relatively high to very high risk categories, underscoring the
            intensity and spatial concentration of vulnerability. By linking NRI
            risk scores to project-level data, SCALE-R enables users to assess
            how adaptation interventions align with underlying patterns of hazard
            exposure, vulnerability, and resilience capacity—shifting knowledge
            from static risk scores to a dynamic evaluation of how investments
            reshape risk conditions and inform strategic decision-making.
          </p>
        </div>

        <p className="docs-nri-ladder__caption" id="docs-nri-ratings-caption">
          NRI rating categories (percentile bands)
        </p>
        <ul
          className="docs-nri-ladder"
          role="list"
          aria-describedby="docs-nri-ratings-caption"
        >
          {NRI_RATINGS.map((row) => (
            <li
              className="docs-nri-rating"
              key={row.label}
              style={{ '--nri-accent': row.accent }}
            >
              <span className="docs-nri-rating__label">{row.label}</span>
              <span className="docs-nri-rating__percentile">{row.percentile}</span>
              <span className="docs-nri-rating__desc">{row.description}</span>
            </li>
          ))}
        </ul>
      </div>

      <div
        className="docs-subsection"
        aria-labelledby="docs-modeling-cre-heading"
      >
        <h3 id="docs-modeling-cre-heading" className="docs-subsection__title">
          Census Community Resilience Estimates
        </h3>
        <div className="docs-subsection__prose">
          <p>
            The U.S. Census Bureau&apos;s Community Resilience Estimates (CRE)
            provide a highly granular measure of social vulnerability, assessing
            the capacity of individuals and households to absorb, endure, and
            recover from the impacts of disasters. Developed using small-area
            estimation techniques with restricted microdata from the 2024 American
            Community Survey (ACS), the CRE produces population estimates based on
            10 individual- and household-level components of social vulnerability.
          </p>
          <p>
            The CRE framework evaluates social vulnerability based on the number
            of resilience measures for which a community falls below defined
            thresholds. Communities with zero components below the threshold are
            classified as having low social vulnerability; those with one or two
            components are classified as moderate social vulnerability; and those
            with three or more components are classified as high social
            vulnerability.
          </p>
          <p>
            The SCALE-R platform maps the share of the population exhibiting three
            or more social vulnerability components at the census tract level.
            Visualizing this measure enhances the platform&apos;s ability to
            identify communities with heightened sensitivity to hazards yet
            limited adaptive capacity. When layered over project-level data, it
            enables users to evaluate whether resilience investments are
            effectively reaching and supporting socially vulnerable populations,
            strengthening equity-informed planning and intervention strategies.
          </p>
        </div>

        <p className="docs-cre-grid__label">Ten CRE components</p>
        <ul className="docs-cre-grid" role="list">
          {CRE_COMPONENTS.map((c) => (
            <li className="docs-cre-component" key={c.label}>
              <span className="docs-cre-component__icon" aria-hidden>
                <span className="material-symbols-outlined">{c.icon}</span>
              </span>
              <span className="docs-cre-component__label">{c.label}</span>
            </li>
          ))}
        </ul>

        <div className="docs-cre-tiers" role="group" aria-label="CRE vulnerability tiers">
          <div className="docs-cre-tier docs-cre-tier--low">
            <span className="docs-cre-tier__name">Low social vulnerability</span>
            <span className="docs-cre-tier__rule">0 components below threshold</span>
          </div>
          <div className="docs-cre-tier docs-cre-tier--moderate">
            <span className="docs-cre-tier__name">Moderate social vulnerability</span>
            <span className="docs-cre-tier__rule">1–2 components below threshold</span>
          </div>
          <div className="docs-cre-tier docs-cre-tier--high">
            <span className="docs-cre-tier__name">High social vulnerability</span>
            <span className="docs-cre-tier__rule">3+ components below threshold</span>
          </div>
        </div>
      </div>

      <div
        className="docs-subsection docs-subsection--last"
        aria-labelledby="docs-modeling-ci-heading"
      >
        <h3 id="docs-modeling-ci-heading" className="docs-subsection__title">
          Critical Infrastructure
        </h3>
        <div className="docs-subsection__prose">
          <p>
            The critical infrastructure layer within the SCALE-R platform maps the
            spatial distribution of essential facilities that support emergency
            response and post-disaster recovery, including emergency and medical
            services, risk and recovery shelters, community centers, and designated
            evacuation routes.
          </p>
          <p>
            These assets, gathered from the Miami-Dade County Emergency Management
            and the Florida Department of Environmental Protection, provide a
            localized view of response capacity and accessibility within local
            networks.
          </p>
          <p>
            Analyzing this information alongside ongoing resilience projects and
            investments helps users evaluate service coverage, identify gaps in
            emergency preparedness, and prioritize strategies to ensure operational
            efficiency and resilience under extreme weather conditions.
          </p>
        </div>

        <ul className="docs-infra-types" role="list">
          {CRITICAL_INFRA_TYPES.map((item) => (
            <li
              className="docs-infra-type"
              key={item.label}
              style={{ '--infra-type-accent': item.accent }}
            >
              <span className="docs-infra-type__icon" aria-hidden>
                <span className="material-symbols-outlined">{item.icon}</span>
              </span>
              <div className="docs-infra-type__body">
                <h4 className="docs-infra-type__title">{item.label}</h4>
                <p className="docs-infra-type__text">{item.text}</p>
              </div>
            </li>
          ))}
        </ul>

        <p className="docs-source-note">
          Sources: Miami-Dade County Emergency Management; Florida Department of
          Environmental Protection.
        </p>
      </div>
    </section>
  );
}
