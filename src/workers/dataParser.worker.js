/**
 * Worker shell: message plumbing only. All of the actual parsing lives in
 * dataParser.core.js so it can also be exercised without a Worker.
 */

import { runTask } from './dataParser.core.js';

self.onmessage = async (event) => {
  const { id, task, payload } = event.data || {};
  try {
    self.postMessage({ id, ok: true, result: await runTask(task, payload) });
  } catch (err) {
    self.postMessage({ id, ok: false, error: err?.message ?? String(err) });
  }
};
