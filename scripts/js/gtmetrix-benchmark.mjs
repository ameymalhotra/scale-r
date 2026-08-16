#!/usr/bin/env node
/**
 * Runs an authoritative GTmetrix benchmark against a deployed URL via the
 * GTmetrix REST API v2.0 and prints the results in the same shape as
 * scripts/js/audit-performance.mjs, so local and GTmetrix numbers line up.
 *
 * Requires a GTmetrix API key (Account > API in the GTmetrix dashboard) and a
 * publicly reachable URL. Each test consumes API credits.
 *
 * Usage:
 *   GTMETRIX_API_KEY=... node scripts/js/gtmetrix-benchmark.mjs --url=https://example.com
 *   GTMETRIX_API_KEY=... node scripts/js/gtmetrix-benchmark.mjs \
 *     --url=https://example.com --routes=/about,/dashboard \
 *     --location=24 --browser=3 --throttle=5000/1000/30
 *
 * Default analysis options follow the GTmetrix defaults (desktop Chrome,
 * Vancouver, unthrottled) unless overridden.
 */

import { mkdirSync, writeFileSync } from 'node:fs';

const API = 'https://gtmetrix.com/api/2.0';
const OUT_DIR = '.lighthouse';
const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS = 6 * 60 * 1000;

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? true];
  })
);

const apiKey = process.env.GTMETRIX_API_KEY;
if (!apiKey) {
  console.error('GTMETRIX_API_KEY is not set. Create one at https://gtmetrix.com/dashboard/api');
  process.exit(1);
}
if (!args.url) {
  console.error('Pass the deployed base URL, e.g. --url=https://scale-r.example.org');
  process.exit(1);
}

const baseUrl = String(args.url).replace(/\/$/, '');
const routes = String(args.routes ?? '/')
  .split(',')
  .map((r) => r.trim());

const authHeader = `Basic ${Buffer.from(`${apiKey}:`).toString('base64')}`;

async function api(path, init = {}) {
  const res = await fetch(path.startsWith('http') ? path : `${API}${path}`, {
    ...init,
    redirect: 'follow',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/vnd.api+json',
      ...(init.headers ?? {}),
    },
  });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }
  if (!res.ok) {
    const detail = body?.errors?.[0]?.detail ?? body?.raw ?? res.statusText;
    throw new Error(`GTmetrix API ${res.status}: ${detail}`);
  }
  return body;
}

async function startTest(url) {
  const attributes = { url };
  if (args.location) attributes.location = String(args.location);
  if (args.browser) attributes.browser = String(args.browser);
  if (args.throttle) attributes.throttle = String(args.throttle);
  if (args.device) attributes.simulate_device = String(args.device);
  if (args.adblock) attributes.adblock = 1;

  const body = await api('/tests', {
    method: 'POST',
    body: JSON.stringify({ data: { type: 'test', attributes } }),
  });
  return body.data.id;
}

async function waitForReport(testId) {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const body = await api(`/tests/${testId}`);
    // Once complete the API redirects to the report, so the payload type flips to "report".
    if (body.data?.type === 'report') return body.data;

    const state = body.data?.attributes?.state;
    if (state === 'error') {
      throw new Error(`Test failed: ${body.data.attributes.error ?? 'unknown error'}`);
    }
    if (state === 'completed' && body.data.attributes.report) {
      const report = await api(`/reports/${body.data.attributes.report}`);
      return report.data;
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error(`Timed out waiting for test ${testId}`);
}

function fmtMs(ms) {
  if (ms == null) return 'n/a';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const results = [];

  for (const route of routes) {
    const url = `${baseUrl}${route}`;
    process.stderr.write(`Testing ${url} ... `);
    const testId = await startTest(url);
    const report = await waitForReport(testId);
    const a = report.attributes;
    process.stderr.write(`${a.gtmetrix_grade} (${a.performance_score}/${a.structure_score})\n`);

    results.push({
      route,
      url,
      gtmetrixGrade: a.gtmetrix_grade,
      performance: a.performance_score,
      structure: a.structure_score,
      fcpMs: a.first_contentful_paint,
      siMs: a.speed_index,
      lcpMs: a.largest_contentful_paint,
      tbtMs: a.total_blocking_time,
      cls: a.cumulative_layout_shift,
      ttfbMs: a.time_to_first_byte,
      onloadMs: a.onload_time,
      fullyLoadedMs: a.fully_loaded_time,
      transferMB: a.page_bytes != null ? Number((a.page_bytes / 1024 / 1024).toFixed(2)) : null,
      requests: a.page_requests,
      reportUrl: report.links?.report_url,
      testId,
    });
  }

  const meta = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    source: 'GTmetrix REST API v2.0',
    analysisOptions: {
      location: args.location ?? 'account default',
      browser: args.browser ?? 'account default',
      throttle: args.throttle ?? 'unthrottled',
      simulateDevice: args.device ?? 'none',
    },
  };

  writeFileSync(`${OUT_DIR}/gtmetrix-summary.json`, JSON.stringify({ meta, results }, null, 2));

  const header = ['Route', 'Grade', 'Perf', 'Struct', 'FCP', 'SI', 'LCP', 'TBT', 'CLS', 'Reqs', 'Transfer'];
  const md = [
    `| ${header.join(' | ')} |`,
    `| ${header.map(() => '---').join(' | ')} |`,
    ...results.map((r) =>
      `| ${[
        r.route,
        r.gtmetrixGrade,
        r.performance,
        r.structure,
        fmtMs(r.fcpMs),
        fmtMs(r.siMs),
        fmtMs(r.lcpMs),
        fmtMs(r.tbtMs),
        r.cls ?? 'n/a',
        r.requests ?? 'n/a',
        r.transferMB != null ? `${r.transferMB} MB` : 'n/a',
      ].join(' | ')} |`
    ),
  ].join('\n');

  writeFileSync(`${OUT_DIR}/gtmetrix-summary.md`, `${md}\n`);
  console.log(`\n${md}`);
  for (const r of results) console.log(`\n${r.route}: ${r.reportUrl ?? '(no report link)'}`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
