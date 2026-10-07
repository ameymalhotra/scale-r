import { afterEach, describe, expect, it, vi } from 'vitest';
import { localFiltersApi as api } from './localFiltersApi.js';
import { DEFAULT_FILTER_CONFIG, cloneConfig } from '../filters/filterConfig.js';
import { clearLocalFilterState, readLocalLiveConfig, writeLocalFilterState } from '../filters/localFilters.js';

vi.mock('./api.js', () => ({ fetchFilterState: vi.fn() }));

const live = cloneConfig(DEFAULT_FILTER_CONFIG);
const start = () =>
  writeLocalFilterState({
    draft: null,
    versions: [{ id: 1, version_no: 1, name: null, note: 'First', config: live, is_current: true }],
  });

afterEach(() => clearLocalFilterState());

describe('local filter test mode', () => {
  it('publishes the saved draft in this browser and makes it the local live config', async () => {
    start();
    const draft = cloneConfig(live);
    draft.filters[0].visible = false;
    await api.saveFiltersDraft({}, draft);
    expect(await api.publishFilters({}, 'Hide city', null)).toEqual({ version_id: 2, version_no: 2 });

    const state = await api.fetchFilterState({});
    expect(state.versions.map((v) => [v.version_no, v.is_current])).toEqual([
      [2, true],
      [1, false],
    ]);
    expect(readLocalLiveConfig().filters[0].visible).toBe(false);
  });

  it('switches back to an older version and refuses to delete the live one', async () => {
    start();
    await api.saveFiltersDraft({}, live);
    await api.publishFilters({}, 'Second', null);
    await api.makeFiltersVersionLive({}, 1);
    expect((await api.fetchFilterState({})).versions.find((v) => v.is_current).id).toBe(1);
    await expect(api.deleteFiltersVersion({}, 1)).rejects.toThrow(/cannot be deleted/);
    await api.deleteFiltersVersion({}, 2);
    expect((await api.fetchFilterState({})).versions).toHaveLength(1);
  });
});
