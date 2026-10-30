import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chunkPage, retrieve, materialContext, grade, progress, parsePlan, normalizeMath } from '../lib/domain';
import { planDayCount, validateQuestions, RequestSchema } from '../lib/schemas';
import type { Material, Question } from '../lib/types';
const docs: Material[] = [
  { id: 'a', name: 'cloud.pdf', chunks: [{ page: 1, text: 'Cloud elasticity adds computing resources as workload demand rises.' }, { page: 2, text: 'IaaS provides virtual machines. PaaS provides application platforms.' }], size: 100, pageCount: 2, file: new Blob(), addedAt: '2026-10-30' },
  { id: 'b', name: 'math.pdf', chunks: [{ page: 7, text: 'An ellipse has area pi a b. Integration can derive the area.' }], size: 100, pageCount: 7, file: new Blob(), addedAt: '2026-10-30' }
];
const qs: Question[] = Array.from({ length: 5 }, (_, i) => ({ question: `Which resource property does ${i} describe?`, options: { A: 'one', B: 'two', C: 'three', D: 'four' }, correct_answer: 'B', explanation: 'The second choice is correct.', subtopic: 'Elasticity' }));
test('retrieval ranks a matching passage and preserves page references', () => { const r = retrieve(docs, 'explain cloud elasticity'); assert.equal(r[0].fileName, 'cloud.pdf'); assert.equal(r[0].page, 1); });
test('selected PDF cannot retrieve another document', () => assert.deepEqual(retrieve(docs, 'ellipse integration', 'a'), []));
test('unrelated questions return no fabricated passage', () => assert.deepEqual(retrieve(docs, 'renaissance art painting'), []));
test('empty query and zero result count return empty', () => { assert.deepEqual(retrieve(docs, ''), []); assert.deepEqual(retrieve(docs, 'cloud', '', 0), []); });
test('chunks terminate and keep the end of long pages', () => { const r = chunkPage('resource '.repeat(1000) + 'END', 5); assert.ok(r.length < 20); assert.ok(r.at(-1)?.text.endsWith('END')); assert.ok(r.every(x => x.page === 5 && x.text.length <= 900)); });
test('syllabus sampling respects chosen PDF and text budget', () => { const r = materialContext(docs, 'b', 100); assert.ok(r.every(c => c.fileName === 'math.pdf')); assert.ok(r.reduce((n, c) => n + c.text.length, 0) <= 100); });
test('quiz grading uses actual answers and subtopics', () => { const r = grade(qs, { 0: 'B', 1: 'A' }, 'Cloud'); assert.equal(r.correct, 1); assert.equal(r.total, 5); assert.equal(r.concepts[1].correct, false); });
test('progress is weighted by question count, not average quiz percentage', () => { const one = grade(qs, Object.fromEntries(qs.map((_, i) => [i, 'B'])), 'Cloud'); const two = grade([...qs, ...qs], {}, 'Cloud'); assert.equal(progress([one, two]).accuracy, 33); });
test('no quiz does not invent accuracy or mastery', () => assert.deepEqual(progress([]), { accuracy: null, total: 0, weak: [] }));
test('weak topics reflect actual graded concepts', () => assert.deepEqual(progress([grade(qs, {}, 'Cloud')]).weak, ['Elasticity']));
test('valid plan preserves tasks and final tips', () => { const days = parsePlan('### Day 1: Read\n- Notes\n### Day 2: Practise\n- Quiz\nExam tips: revise', 2); assert.equal(days.length, 2); assert.match(days[1].content, /Exam tips/); });
test('repeated or missing plan days are rejected', () => { assert.throws(() => parsePlan('### Day 1: A\n- Read\n### Day 1: B\n- Quiz', 2)); assert.throws(() => parsePlan('### Day 1: A\n- Read', 2)); });
test('plan dates reject impossible and past dates, cap at fourteen', () => { assert.throws(() => planDayCount('2026-10-30', '2026-02-31')); assert.throws(() => planDayCount('2026-10-30', '2026-10-29')); assert.equal(planDayCount('2026-10-30', '2026-12-01'), 14); });
test('valid questions have exact counts and distinct options', () => assert.equal(validateQuestions(qs, 5).length, 5));
test('duplicate questions and normalized duplicate options fail validation', () => { assert.throws(() => validateQuestions(Array(5).fill(qs[0]), 5)); const bad = structuredClone(qs); bad[0].options.B = 'One!'; assert.throws(() => validateQuestions(bad, 5)); });
test('wrong answer keys, extra options and blank explanations are rejected', () => { for (const change of [{ correct_answer: 'E' }, { explanation: '' }, { options: { ...qs[0].options, E: 'extra' } }]) { assert.throws(() => validateQuestions([{ ...qs[0], ...change }, ...qs.slice(1)], 5)); } });
test('request schema bounds supplied context, history and quiz count', () => { assert.equal(RequestSchema.safeParse({ action: 'quiz', topic: 'x', count: 6, difficulty: 'Easy', context: [] }).success, false); assert.equal(RequestSchema.safeParse({ action: 'chat', question: 'x', mode: 'pdf', context: Array(9).fill({ fileName: 'x', page: 1, text: 'a' }), history: [] }).success, false); });
test('math delimiters become renderer-compatible Markdown', () => assert.equal(normalizeMath('Area \\(a^2\\)'), 'Area $a^2$'));
