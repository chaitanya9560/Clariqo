import { openDB, type DBSchema } from 'idb';
import type { Material, Learning } from './types';
import { EMPTY_LEARNING } from './types';
interface StudyDB extends DBSchema { materials: { key: string; value: Material }; learning: { key: string; value: Learning } }
function db() { return openDB<StudyDB>('clariqo-web-v1', 1, { upgrade(db) { db.createObjectStore('materials', { keyPath: 'id' }); db.createObjectStore('learning'); } }); }
export async function loadStudy() { const d = await db(); return { materials: await d.getAll('materials'), learning: await d.get('learning', 'profile') || structuredClone(EMPTY_LEARNING) }; }
export async function storeMaterial(material: Material) { const d = await db(); await d.put('materials', material); }
export async function deleteMaterial(id: string) { const d = await db(); await d.delete('materials', id); }
export async function storeLearning(value: Learning) { const d = await db(); await d.put('learning', value, 'profile'); }
export async function clearStudy() { const d = await db(); const tx = d.transaction(['materials', 'learning'], 'readwrite'); await Promise.all([tx.objectStore('materials').clear(), tx.objectStore('learning').clear()]); await tx.done; }
