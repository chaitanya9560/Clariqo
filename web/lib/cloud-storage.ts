import type { SupabaseClient } from '@supabase/supabase-js';
import { EMPTY_LEARNING, type Learning, type Material } from './types';
import { materialFromRow, savedLearning } from './saved-data';
const BUCKET = 'study-pdfs';
export function cloudStudyStore(client: SupabaseClient, userId: string) {
  let revision: number | null = null, loaded = false;
  const fileCache = new Map<string, Blob>();
  async function loadStudy() {
    const [materials, profile] = await Promise.all([
      client.from('clariqo_materials').select('*').eq('user_id', userId).order('created_at'),
      client.from('clariqo_learning').select('data,revision').eq('user_id', userId).maybeSingle()
    ]);
    if (materials.error || profile.error) throw new Error('Your saved study space could not be loaded. Check your connection and try again.');
    const docs = (materials.data || []).map(row => materialFromRow(row, userId));
    const learning = profile.data ? savedLearning(profile.data.data) : structuredClone(EMPTY_LEARNING);
    revision = profile.data?.revision ?? null; loaded = true;
    return { materials: docs, learning };
  }
  async function storeLearning(value: Learning) {
    if (!loaded) throw new Error('Wait for your account data to finish loading.');
    const data = savedLearning(value), next = (revision ?? 0) + 1;
    const result = revision === null
      ? await client.from('clariqo_learning').insert({ user_id: userId, data, revision: next }).select('revision').single()
      : await client.from('clariqo_learning').update({ data, revision: next }).eq('user_id', userId).eq('revision', revision).select('revision').maybeSingle();
    if (result.error || !result.data) throw new Error('Your changes could not be saved. Another tab or device may have newer work. Reload before continuing to avoid overwriting it.');
    revision = result.data.revision;
  }
  async function storeMaterial(material: Material) {
    if (!material.file) throw new Error('The original PDF is required for upload.');
    const { data: old, error: lookupError } = await client.from('clariqo_materials').select('storage_path').eq('user_id', userId).eq('id', material.id).maybeSingle();
    if (lookupError) throw new Error('Your library could not be checked. Please try again.');
    const path = `${userId}/${material.id}/${crypto.randomUUID()}.pdf`;
    const { error: uploadError } = await client.storage.from(BUCKET).upload(path, material.file, { contentType: 'application/pdf', upsert: false });
    if (uploadError) throw new Error('The PDF could not be saved privately. Check your connection and account storage.');
    const { error } = await client.from('clariqo_materials').upsert({ id: material.id, user_id: userId, name: material.name, size: material.size, page_count: material.pageCount, chunks: material.chunks, storage_path: path, created_at: material.addedAt }, { onConflict: 'id' });
    if (error) { await client.storage.from(BUCKET).remove([path]); throw new Error('The library update failed. Your previous saved PDF was kept. Each account allows 5 PDFs / 50 MB.'); }
    material.storagePath = path; fileCache.set(path, material.file);
    if (old?.storage_path && old.storage_path !== path) await client.storage.from(BUCKET).remove([old.storage_path]);
  }
  async function materialFile(material: Material) {
    if (material.file) return material.file;
    const path = material.storagePath;
    if (!path || !path.startsWith(`${userId}/${material.id}/`)) throw new Error('This saved PDF is unavailable.');
    const cached = fileCache.get(path); if (cached) return cached;
    const { data, error } = await client.storage.from(BUCKET).download(path);
    if (error || !data) throw new Error('The saved PDF could not be downloaded. Check your connection and try again.');
    fileCache.set(path, data); return data;
  }
  async function deleteMaterial(id: string) {
    const { data: row, error } = await client.from('clariqo_materials').select('storage_path').eq('user_id', userId).eq('id', id).maybeSingle();
    if (error || !row) throw new Error('This PDF is no longer available. Reload your library.');
    const removed = await client.storage.from(BUCKET).remove([row.storage_path]);
    if (removed.error) throw new Error('The PDF could not be removed. Please try again.');
    const deleted = await client.from('clariqo_materials').delete().eq('user_id', userId).eq('id', id);
    if (deleted.error) throw new Error('The library record could not be removed. Please try again.');
    fileCache.delete(row.storage_path);
  }
  async function filesAt(prefix: string) {
    const result: { name: string; id: string | null }[] = [];
    for (let offset = 0; ; offset += 1000) {
      const page = await client.storage.from(BUCKET).list(prefix, { limit: 1000, offset });
      if (page.error) throw new Error('Your private files could not be listed. Please try again.');
      result.push(...page.data); if (page.data.length < 1000) break;
    }
    return result;
  }
  async function clearStudy() {
    const paths: string[] = [];
    for (const folder of await filesAt(userId)) {
      if (folder.id) paths.push(`${userId}/${folder.name}`);
      else for (const file of await filesAt(`${userId}/${folder.name}`)) paths.push(`${userId}/${folder.name}/${file.name}`);
    }
    for (let i = 0; i < paths.length; i += 100) {
      const result = await client.storage.from(BUCKET).remove(paths.slice(i, i + 100));
      if (result.error) throw new Error('Some private files could not be removed. Retry to finish clearing your study data.');
    }
    const results = await Promise.all([client.from('clariqo_materials').delete().eq('user_id', userId), client.from('clariqo_learning').delete().eq('user_id', userId)]);
    if (results.some(r => r.error)) throw new Error('Some saved records could not be cleared. Please try again.');
    revision = null; loaded = true; fileCache.clear();
  }
  return { loadStudy, storeLearning, storeMaterial, deleteMaterial, materialFile, clearStudy };
}
