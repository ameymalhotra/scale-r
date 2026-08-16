#!/usr/bin/env node
/**
 * Reproducible front-end performance audit for the SCALE-R dashboard.
 *
 * Runs Lighthouse over a set of routes and reports the results in the GTmetrix
 * scoring framework so that locally measured numbers and GTmetrix report numbers
 * can be placed side by side.
 *
 * GTmetrix Grade = 0.60 x Performance Score + 0.40 x Structure Score.
 * The Performance Score is the Lighthouse performance category verbatim, so it is
 * directly comparable. The Structure Score is proprietary to GTmetrix; this script
 * derives a transparent proxy (see STRUCTURE_AUDITS) and labels it as such.
 *
 * Usage:
 *   node scripts/js/audit-performance.mjs
 *   node scripts/js/audit-performance.mjs --url=https://example.com --runs=5
 *   node scripts/js/audit-performance.mjs --routes=/about,/dashboard --profiles=desktop
 *
 * Lighthouse is invoked through npx at a pinned version, so no repository
 * dependency is added and the audit stays reproducible across machines.
 */

import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const LIGHTHOUSE_VERSION = '13.4.1';
const OUT_DIR = '.lighthouse';

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? true];
  })
);

const baseUrl = (args.url ?? 'http://localhost:4173').replace(/\/$/, '');
const runs = Number(args.runs ?? 5);
const routes = String(args.routes ?? '/about,/dashboard')
  .split(',')
  .map((r) => r.trim());
const profiles = String(args.profiles ?? 'desktop,mobile')
  .split(',')
  .map((p) => p.trim());
const keepReports = Boolean(args.keep);

// Lighthouse performance weights, identical to those GTmetrix applies.
const PERF_WEIGHTS = {
  'first-contentful-paint': 0.10,
  'speed-index': 0.10,
  'largest-contentful-paint': 0.25,
  'total-blocking-time': 0.30,
  'cumulative-layout-shift': 0.25,
};

// Front-end best-practice audits corresponding to the GTmetrix Structure tab.
// The proxy score is their unweighted mean, which keeps the derivation inspectable.
const STRUCTURE_AUDITS = [
  'render-blocking-insight',
  'image-delivery-insight',
  'cache-insight',
  'font-display-insight',
  'lcp-discovery-insight',
  'network-dependency-tree-insight',
  'document-latency-insight',
  'duplicated-javascript-insight',
  'legacy-javascript-insight',
  'unused-javascript',
  'unused-css-rules',
  'total-byte-weight',
  'unsized-images',
  'dom-size',
  'bootup-time',
  'mainthread-work-breakdown',
  'third-party-summary',
  'uses-text-compression',
  'redirects',
  'viewport',
];

const PROFILE_FLAGS = {
  desktop: ['--preset=desktop'],
  mobile: [],
};

function letterGrade(pct) {
  if (pct >= 90) return 'A';
  if (pct >= 80) return 'B';
  if (pct >= 70) return 'C';
  if (pct >= 60) return 'D';
  if (pct >= 50) return 'E';
  return 'F';
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function runLighthouse(url, profile, outPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      'npx',
      [
        '--yes',
        `lighthouse@${LIGHTHOUSE_VERSION}`,
        url,
        ...PROFILE_FLAGS[profile],
        '--only-categories=performance,accessibility,best-practices,seo',
        '--output=json',
        `--output-path=${outPath}`,
        '--chrome-flags=--headless=new --no-sandbox',
        '--quiet',
      ],
      { stdio: ['ignore', 'ignore', 'pipe'] }
    );
    let stderr = '';
    child.stderr.on('data', (d) => (stderr += d));
    child.on('close', (code) =>
      code === 0 ? resolve() : reject(new Error(`lighthouse exited ${code}: ${stderr.slice(-500)}`))
    );
  });
}

/** Reduce one Lighthouse result object to the metrics reported in the evaluation. */
function summarize(lhr) {
  const a = lhr.audits;
  const requests = a['network-requests']?.details?.items ?? [];
  const transferBytes = requests.reduce((sum, r) => sum + (r.transferSize || 0), 0);

  const available = STRUCTURE_AUDITS.filter((id) => a[id] && a[id].score !== null);
  const structure = available.reduce((sum, id) => sum + a[id].score, 0) / available.length;

  // A null TBT (NO_TTI_CPU_IDLE_PERIOD) zeroes 30% of the performance weight, so the
  // category score becomes an artefact rather than a measurement. Flag it explicitly.
  const unmeasurable = Object.keys(PERF_WEIGHTS).filter((id) => a[id]?.score === null);

  const auditScores = Object.fromEntries(available.map((id) => [id, a[id].score * 100]));

  return {
    performance: lhr.categories.performance.score * 100,
    accessibility: lhr.categories.accessibility.score * 100,
    bestPractices: lhr.categories['best-practices'].score * 100,
    seo: lhr.categories.seo.score * 100,
    structureProxy: structure * 100,
    auditScores,
    bootupMs: a['bootup-time']?.numericValue ?? null,
    mainThreadMs: a['mainthread-work-breakdown']?.numericValue ?? null,
    fcp: a['first-contentful-paint'].numericValue,
    si: a['speed-index'].numericValue,
    lcp: a['largest-contentful-paint'].numericValue,
    tbt: a['total-blocking-time'].numericValue ?? null,
    cls: a['cumulative-layout-shift'].numericValue,
    ttfb: a['server-response-time']?.numericValue ?? null,
    requests: requests.length,
    transferMB: transferBytes / 1024 / 1024,
    structureAuditCount: available.length,
    unmeasurable,
    lighthouseVersion: lhr.lighthouseVersion,
    userAgent: lhr.environment?.hostUserAgent ?? '',
  };
}

function fmtMs(ms) {
  if (ms == null) return 'n/a';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const results = [];

  for (const route of routes) {
    for (const profile of profiles) {
      const url = `${baseUrl}${route}`;
      const label = `${route === '/' ? '/root' : route}-${profile}`;
      const iterations = [];

      process.stderr.write(`\n${url} [${profile}] `);
      for (let i = 1; i <= runs; i += 1) {
        const outPath = join(OUT_DIR, `${label.replace(/\//g, '')}-run${i}.report.json`);
        await runLighthouse(url, profile, outPath);
        const lhr = JSON.parse(readFileSync(outPath, 'utf8'));
        iterations.push(summarize(lhr));
        if (!keepReports && i !== 1) rmSync(outPath, { force: true });
        process.stderr.write('.');
      }

      const pick = (key) => median(iterations.map((it) => it[key]).filter((v) => v != null));
      const anyUnmeasurable = [...new Set(iterations.flatMap((it) => it.unmeasurable))];

      // Median score per structure audit, so the audit-level table is aggregated
      // the same way as the headline metrics rather than taken from one run.
      const auditMedians = {};
      for (const id of STRUCTURE_AUDITS) {
        const scores = iterations.map((it) => it.auditScores[id]).filter((v) => v != null);
        if (scores.length) auditMedians[id] = Math.round(median(scores));
      }

      const performance = pick('performance');
      const structureProxy = pick('structureProxy');
      const gradePct = 0.6 * performance + 0.4 * structureProxy;

      results.push({
        route,
        profile,
        runs,
        performance: Math.round(performance),
        structureProxy: Math.round(structureProxy),
        gtmetrixGradePct: Number(gradePct.toFixed(1)),
        gtmetrixGrade: letterGrade(gradePct),
        accessibility: Math.round(pick('accessibility')),
        bestPractices: Math.round(pick('bestPractices')),
        seo: Math.round(pick('seo')),
        fcpMs: Math.round(pick('fcp')),
        siMs: Math.round(pick('si')),
        lcpMs: Math.round(pick('lcp')),
        tbtMs: anyUnmeasurable.includes('total-blocking-time') ? null : Math.round(pick('tbt')),
        cls: Number(pick('cls').toFixed(3)),
        requests: Math.round(pick('requests')),
        transferMB: Number(pick('transferMB').toFixed(2)),
        bootupMs: Math.round(pick('bootupMs')),
        mainThreadMs: Math.round(pick('mainThreadMs')),
        unmeasurableMetrics: anyUnmeasurable,
        structureAudits: auditMedians,
        performanceRuns: iterations.map((it) => Math.round(it.performance)),
        tbtRuns: iterations.map((it) => (it.tbt == null ? null : Math.round(it.tbt))),
        lighthouseVersion: iterations[0].lighthouseVersion,
      });
    }
  }

  const meta = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    runsPerConfiguration: runs,
    lighthouseVersion: LIGHTHOUSE_VERSION,
    node: process.version,
    scoring: 'GTmetrix Grade = 0.60 x Performance + 0.40 x Structure; Structure is a documented proxy',
    aggregation: 'median',
  };

  writeFileSync(join(OUT_DIR, 'summary.json'), JSON.stringify({ meta, results }, null, 2));

  const header = [
    'Route',
    'Profile',
    'Grade',
    'Grade %',
    'Perf',
    'Struct*',
    'FCP',
    'SI',
    'LCP',
    'TBT',
    'CLS',
    'Reqs',
    'Transfer',
  ];
  const rows = results.map((r) => [
    r.route,
    r.profile,
    r.gtmetrixGrade,
    r.gtmetrixGradePct.toFixed(1),
    r.performance,
    r.structureProxy,
    fmtMs(r.fcpMs),
    fmtMs(r.siMs),
    fmtMs(r.lcpMs),
    r.tbtMs === null ? 'n/m' : fmtMs(r.tbtMs),
    r.cls.toFixed(3),
    r.requests,
    `${r.transferMB.toFixed(2)} MB`,
  ]);

  // Audit-level table: one column per configuration, median score per audit.
  const auditIds = STRUCTURE_AUDITS.filter((id) => results.some((r) => r.structureAudits[id] != null));
  const auditHeader = ['Audit', ...results.map((r) => `${r.route} ${r.profile}`)];
  const auditRows = auditIds.map((id) => [
    `\`${id}\``,
    ...results.map((r) => (r.structureAudits[id] == null ? 'n/a' : r.structureAudits[id])),
  ]);

  const md = [
    `| ${header.join(' | ')} |`,
    `| ${header.map(() => '---').join(' | ')} |`,
    ...rows.map((r) => `| ${r.join(' | ')} |`),
    '',
    `*Structure is a proxy over ${STRUCTURE_AUDITS.length} best-practice audits, not the proprietary GTmetrix score.`,
    `Median of ${runs} runs. Lighthouse ${LIGHTHOUSE_VERSION}. n/m = not measurable (no CPU idle period).`,
    '',
    '### Structure audit scores (median)',
    '',
    `| ${auditHeader.join(' | ')} |`,
    `| ${auditHeader.map(() => '---').join(' | ')} |`,
    ...auditRows.map((r) => `| ${r.join(' | ')} |`),
    '',
    '### Main-thread cost and per-run spread',
    '',
    '| Configuration | Script eval | Main-thread work | Performance per run |',
    '| --- | --- | --- | --- |',
    ...results.map(
      (r) =>
        `| ${r.route} ${r.profile} | ${fmtMs(r.bootupMs)} | ${fmtMs(r.mainThreadMs)} | ${r.performanceRuns.join(', ')} |`
    ),
  ].join('\n');

  writeFileSync(join(OUT_DIR, 'summary.md'), `${md}\n`);
  console.log(`\n${md}`);
  console.log(`\nWrote ${OUT_DIR}/summary.json and ${OUT_DIR}/summary.md`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
