import { createClient } from '@supabase/supabase-js';
const sb = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } });
const { data: draft, error: e1 } = await sb.from('layers_draft').select('config, updated_at, updated_by');
const { data: versions, error: e2 } = await sb.from('layers_versions').select('id, version_no, name, note, is_current, created_at').order('version_no');
console.log('draft error', e1?.message, 'versions error', e2?.message);
console.log('versions', JSON.stringify(versions, null, 1));
const cfg = draft?.[0]?.config;
console.log('draft updated', draft?.[0]?.updated_at, draft?.[0]?.updated_by);
console.log('draft keys', cfg && Object.keys(cfg));
console.log('draft layers', JSON.stringify(cfg?.layers?.map(l => ({ id: l.id, label: l.label, file: l.file, visible: l.visible, mode: l.symbology?.mode })), null, 1));
console.log('order', JSON.stringify(cfg?.order), 'builtins', cfg?.builtins?.length);
const cur = versions?.find(v => v.is_current);
if (cur) { const { data } = await sb.from('layers_versions').select('config').eq('id', cur.id).single(); console.log('live layers', JSON.stringify(data.config.layers?.map(l => l.id)), 'same as draft:', JSON.stringify(data.config) === JSON.stringify(cfg)); }
