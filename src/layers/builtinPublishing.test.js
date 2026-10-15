import { describe, expect, it, vi } from 'vitest';
import { writeLayersConfig } from '../../supabase/functions/_shared/publishGeojson.ts';
import { modellingOptions } from './builtinRegistry.js';
import { normalizeLayerConfig } from './layerConfig.js';

describe('layer publishing transport', () => {
  it('writes the complete config consumed by the public map, including admin controls', async () => {
    const config = normalizeLayerConfig(null);
    config.builtins.find((l) => l.id === 'risk').visible = false;
    config.builtins.find((l) => l.id === 'elevation').label = 'Ground Elevation';
    config.order.reverse(); config.overlayOrder.reverse();
    const upload = vi.fn().mockResolvedValue({ error: null });
    const admin = { storage: { from: vi.fn(() => ({ upload })) } };
    await writeLayersConfig(admin, config, 12);
    const [filename, bytes, options] = upload.mock.calls[0];
    expect(admin.storage.from).toHaveBeenCalledWith('project-data');
    expect(filename).toBe('layers_config.json'); expect(options).toMatchObject({ cacheControl: '0', upsert: true });
    const envelope = JSON.parse(new TextDecoder().decode(bytes));
    expect(envelope.version_no).toBe(12);
    expect(normalizeLayerConfig(envelope)).toEqual(config);
    expect(modellingOptions(normalizeLayerConfig(envelope))[1]).toMatchObject({ label: 'Ground Elevation', view: 'custom:elevation' });
    expect(modellingOptions(normalizeLayerConfig(envelope)).some((l) => l.view === 'risk')).toBe(false);
  });
  it('reports storage errors instead of claiming a successful publication', async () => {
    const admin = { storage: { from: () => ({ upload: async () => ({ error: { message: 'Storage unavailable' } }) }) } };
    await expect(writeLayersConfig(admin, normalizeLayerConfig(null), 12)).rejects.toThrow('Storage unavailable');
  });
});
