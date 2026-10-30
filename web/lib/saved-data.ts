import { z } from 'zod';
import type { Learning, Material } from './types';
const reference = z.object({ fileName: z.string().max(200), page: z.number().int().min(1).max(200) });
const webReference = z.object({ title: z.string().max(300), url: z.string().url().refine(value => { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password; }) });
const quizResult = z.object({ id: z.string().max(100), topic: z.string().max(200), correct: z.number().int().min(0).max(10), total: z.number().int().min(1).max(10), date: z.string().refine(value => Number.isFinite(Date.parse(value))), concepts: z.array(z.object({ topic: z.string().max(100), correct: z.boolean() })).max(10) }).refine(r => r.correct <= r.total);
export const LearningSchema = z.object({
  totalQuestions: z.number().int().min(0).max(10000000),
  messages: z.array(z.object({ id: z.string().max(100), role: z.enum(['user', 'assistant']), content: z.string().max(60000), sources: z.array(reference).max(8).optional(), webSources: z.array(webReference).max(6).optional(), origin: z.string().max(30).optional(), error: z.boolean().optional() })).max(100),
  results: z.array(quizResult).max(100),
  plan: z.object({ id: z.string().max(100), subject: z.string().max(200), markdown: z.string().max(100000), days: z.array(z.object({ day: z.number().int().min(1).max(14), title: z.string().max(200), content: z.string().max(10000) })).min(1).max(14), completed: z.array(z.number().int().min(1).max(14)).max(14), sourceNames: z.array(z.string().max(200)).max(5) }).nullable()
});
export const MaterialRowSchema = z.object({ id: z.string().uuid(), user_id: z.string().uuid(), name: z.string().min(1).max(200), size: z.number().int().min(1).max(20 * 1024 * 1024), page_count: z.number().int().min(1).max(200), chunks: z.array(z.object({ page: z.number().int().min(1).max(200), text: z.string().max(2000) })).max(1000), storage_path: z.string().min(1).max(300), created_at: z.string() });
export function savedLearning(value: unknown): Learning { return LearningSchema.parse(value); }
export function materialFromRow(value: unknown, userId: string): Material {
  const row = MaterialRowSchema.parse(value);
  if (row.user_id !== userId || !row.storage_path.startsWith(`${userId}/${row.id}/`)) throw new Error('This material does not belong to the signed-in account.');
  return { id: row.id, name: row.name, size: row.size, pageCount: row.page_count, chunks: row.chunks, storagePath: row.storage_path, addedAt: row.created_at };
}
