import { z } from 'zod';
const source = z.object({ fileName: z.string().min(1).max(200), page: z.number().int().min(1).max(200), text: z.string().min(1).max(2000) });
const context = z.array(source).max(8).refine(s => s.reduce((n, c) => n + c.text.length, 0) <= 12000, 'Too much study context.');
const history = z.array(z.object({ role: z.enum(['user', 'assistant']), content: z.string().max(2500) })).max(6);
export const ChatSchema = z.object({ action: z.literal('chat'), question: z.string().trim().min(1).max(2000), mode: z.enum(['chat', 'pdf', 'web']), hasMaterials: z.boolean().default(false), context, history });
export const QuizSchema = z.object({ action: z.literal('quiz'), topic: z.string().trim().min(1).max(200), count: z.union([z.literal(5), z.literal(10)]), difficulty: z.enum(['Easy', 'Medium', 'Hard']), context });
export const PlanSchema = z.object({ action: z.literal('plan'), subject: z.string().trim().min(1).max(200), examDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), today: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), hours: z.number().min(.5).max(8), level: z.enum(['Beginner', 'Intermediate', 'Advanced']), weakTopics: z.array(z.string().max(100)).max(20), context });
export const FlashcardsSchema = z.object({ action: z.literal('flashcards'), topic: z.string().trim().min(1).max(200), count: z.union([z.literal(5), z.literal(10)]), context });
export const MindMapRequestSchema = z.object({ action: z.literal('mindmap'), topic: z.string().trim().min(1).max(200), context });
export const RequestSchema = z.discriminatedUnion('action', [ChatSchema, QuizSchema, PlanSchema, FlashcardsSchema, MindMapRequestSchema]);
export const QuestionSchema = z.object({ question: z.string().trim().min(5).max(1000), options: z.object({ A: z.string().trim().min(1).max(600), B: z.string().trim().min(1).max(600), C: z.string().trim().min(1).max(600), D: z.string().trim().min(1).max(600) }).strict(), correct_answer: z.enum(['A', 'B', 'C', 'D']), explanation: z.string().trim().min(1).max(2000), subtopic: z.string().trim().min(1).max(100) });
export function validateQuestions(value: unknown, count: number) {
  const questions = z.array(QuestionSchema).length(count).parse(value);
  const normalize = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  if (new Set(questions.map(q => normalize(q.question))).size !== count) throw new Error('The AI repeated a question. Please generate again.');
  if (questions.some(q => new Set(Object.values(q.options).map(normalize)).size !== 4)) throw new Error('The AI repeated answer options. Please generate again.');
  return questions;
}
export function planDayCount(today: string, examDate: string) {
  for (const value of [today, examDate]) {
    const date = new Date(value + 'T00:00:00Z');
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) throw new Error('Choose a valid exam date.');
  }
  const remaining = Math.round((Date.parse(examDate + 'T00:00:00Z') - Date.parse(today + 'T00:00:00Z')) / 86400000);
  if (remaining < 1) throw new Error('Choose an exam date after today.');
  return Math.min(14, remaining);
}
