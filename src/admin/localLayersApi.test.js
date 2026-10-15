import { afterEach, describe, expect, it, vi } from 'vitest';
import { localLayersApi as api } from './localLayersApi.js';
import { fetchLayerGeojson, fetchLayerState } from './api.js';
import { EMPTY_LAYER_CONFIG, cloneConfig } from '../layers/layerConfig.js';
import { LOCAL_LAYERS_KEY, readLocalLiveLayerConfig, writeLocalLayerState } from '../layers/localLayers.js';

vi.mock('./api.js', () => ({ fetchLayerState: vi.fn(), fetchLayerGeojson: vi.fn() }));

const live = cloneConfig(EMPTY_LAYER_CONFIG);
const start = () =>
  writeLocalLayerState({
    draft: null,
    versions: [{ id: 1, version_no: 1, name: null, note: 'First', config: live, is_current: true }],
  });

afterEach(() => {
  window.localStorage.removeItem(LOCAL_LAYERS_KEY);
  vi.clearAllMocks();
});

describe('local layer test mode', () => {
  it('seeds from Supabase once, then keeps everything in this browser', async () => {
    fetchLayerState.mockResolvedValue({ draft: null, versions: [] });
    await api.fetchLayerState({});
    await api.fetchLayerState({});
    expect(fetchLayerState).toHaveBeenCalledTimes(1);
  });

  it('publishes the saved draft locally and makes it the local live config', async () => {
    start();
    const draft = cloneConfig(live);
    draft.order = ['heat'];
    await api.saveLayersDraft({}, draft);
    await expect(api.publishLayers({}, '', null)).rejects.toThrow(/note is required/);
    expect(await api.publishLayers({}, 'Add heat', null)).toEqual({ version_id: 2, version_no: 2 });

    const state = await api.fetchLayerState({});
    expect(state.versions.map((v) => [v.version_no, v.is_current])).toEqual([
      [2, true],
      [1, false],
    ]);
    expect(readLocalLiveLayerConfig().order).toEqual(['heat']);
  });

  it('switches back to an older version and refuses to delete the live one', async () => {
    start();
    await api.saveLayersDraft({}, live);
    await api.publishLayers({}, 'Second', null);
    await api.makeLayersVersionLive({}, 1);
    expect((await api.fetchLayerState({})).versions.find((v) => v.is_current).id).toBe(1);
    await expect(api.deleteLayersVersion({}, 1)).rejects.toThrow(/cannot be deleted/);
    await api.deleteLayersVersion({}, 2);
    expect((await api.fetchLayerState({})).versions).toHaveLength(1);
  });

  it('falls back to the real bucket for files not uploaded locally', async () => {
    fetchLayerGeojson.mockResolvedValue({ type: 'FeatureCollection', features: [] });
    expect(await api.fetchLayerGeojson({}, 'layers/real-abc.geojson')).toEqual({ type: 'FeatureCollection', features: [] });
    expect(fetchLayerGeojson).toHaveBeenCalledWith({}, 'layers/real-abc.geojson');
  });
});
