// Run only against disposable test accounts. Credentials arrive on stdin, never in arguments or files.
import assert from 'node:assert/strict';
import { createClient } from '@supabase/supabase-js';
import { cloudStudyStore } from '../../lib/cloud-storage';
import { EMPTY_LEARNING, type Material } from '../../lib/types';
async function main() {
  let raw = ''; for await (const chunk of process.stdin) raw += chunk;
  const config = JSON.parse(raw);
  const clients = config.users.map((u: { token: string }) => createClient(config.url, config.key, { global: { headers: { Authorization: `Bearer ${u.token}` } }, auth: { persistSession: false, autoRefreshToken: false } }));
  const [a, b] = clients, [ua, ub] = config.users;
  const sa = cloudStudyStore(a, ua.id), sb = cloudStudyStore(b, ub.id);
  try {
    assert.deepEqual((await sa.loadStudy()).materials, []);
    assert.deepEqual((await sb.loadStudy()).materials, []);
    await sa.storeLearning({ ...EMPTY_LEARNING, totalQuestions: 2 });
    await sb.storeLearning({ ...EMPTY_LEARNING, totalQuestions: 7 });
    assert.equal((await sa.loadStudy()).learning.totalQuestions, 2);
    assert.equal((await sb.loadStudy()).learning.totalQuestions, 7);
    console.log('PASS separate account learning');
    const stale = cloudStudyStore(a, ua.id); await stale.loadStudy();
    await sa.storeLearning({ ...EMPTY_LEARNING, totalQuestions: 3 });
    await assert.rejects(stale.storeLearning({ ...EMPTY_LEARNING, totalQuestions: 99 }), /newer work/);
    assert.equal((await sa.loadStudy()).learning.totalQuestions, 3);
    console.log('PASS stale device cannot overwrite new progress');
    const makePdf = (): Material => ({ id: crypto.randomUUID(), name: 'isolation-test.pdf', size: 25, pageCount: 1, chunks: [{ page: 1, text: 'Synthetic test notes' }], addedAt: new Date().toISOString(), file: new Blob(['%PDF-1.4\nSynthetic test\n%%EOF'], { type: 'application/pdf' }) });
    const ma = makePdf(), mb = makePdf(); await sa.storeMaterial(ma); await sb.storeMaterial(mb);
    assert.equal((await sa.loadStudy()).materials.length, 1); assert.equal((await sb.loadStudy()).materials.length, 1);
    const restored = (await sa.loadStudy()).materials[0]; assert.match(await (await sa.materialFile(restored)).text(), /Synthetic test/);
    const hidden = await b.from('clariqo_materials').select('*').eq('user_id', ua.id); assert.ifError(hidden.error); assert.equal(hidden.data.length, 0);
    assert.ok((await b.storage.from('study-pdfs').download(ma.storagePath!)).error);
    assert.ok((await b.from('clariqo_learning').insert({ user_id: ua.id, data: EMPTY_LEARNING })).error);
    const anon = createClient(config.url, config.key, { auth: { persistSession: false } }); assert.ok((await anon.from('clariqo_learning').select('*')).error);
    console.log('PASS private PDFs, same filename, owner-only database and storage');
    const bad = { ...ma, size: 21 * 1024 * 1024 }; await assert.rejects(sa.storeMaterial(bad), /previous saved PDF was kept/);
    assert.equal((await sa.loadStudy()).materials[0].storagePath, ma.storagePath);
    console.log('PASS failed replacement preserves existing PDF');
    await sa.clearStudy(); assert.equal((await sa.loadStudy()).materials.length, 0);
    assert.equal((await sb.loadStudy()).materials.length, 1); assert.equal((await sb.loadStudy()).learning.totalQuestions, 7);
    console.log('PASS clearing one account leaves the other unchanged');
  } finally { await sa.clearStudy(); await sb.clearStudy(); }
}
main().catch(() => { console.error('FAIL live account isolation test; no credentials logged'); process.exitCode = 1; });
