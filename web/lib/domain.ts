import type { Chunk, Material, QuizResult, Source, PlanDay, Question } from './types';
const STOP = new Set('the a an of to for is are in on and or it this that what how can you me explain please'.split(' '));
export function tokens(text: string): string[] { return (text.toLowerCase().match(/[\p{L}\p{N}]+/gu) || []).filter(w => w.length > 1 && !STOP.has(w)); }
export function chunkPage(text: string, page: number): Chunk[] {
  const clean = text.replace(/[\t ]+/g, ' ').trim(); const chunks: Chunk[] = [];
  for (let start = 0; start < clean.length; start += 700) chunks.push({ page, text: clean.slice(start, start + 900) });
  return chunks;
}
// Browser-local BM25-style lexical retrieval: no model download or server index.
export function retrieve(materials: Material[], query: string, selected = '', limit = 6): Source[] {
  const chunks = materials.filter(m => !selected || m.id === selected).flatMap(m => m.chunks.map(c => ({ fileName: m.name, ...c })));
  if (!chunks.length || limit <= 0) return [];
  const words = [...new Set(tokens(query))]; if (!words.length) return [];
  const documents = chunks.map(c => tokens(c.text)); const avg = documents.reduce((n, d) => n + d.length, 0) / documents.length || 1;
  const df = words.map(w => documents.filter(d => d.includes(w)).length);
  return chunks.map((chunk, i) => ({ chunk, score: words.reduce((sum, w, wi) => {
    const tf = documents[i].filter(t => t === w).length;
    const idf = Math.log(1 + (chunks.length - df[wi] + .5) / (df[wi] + .5));
    return sum + idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * documents[i].length / avg));
  }, 0) })).filter(x => x.score > 0).sort((a, b) => b.score - a.score).slice(0, limit).map(x => x.chunk);
}
export function materialContext(materials: Material[], selected = '', maxChars = 10000): Source[] {
  const docs = materials.filter(m => !selected || m.id === selected); const budget = Math.floor(maxChars / Math.max(1, docs.length));
  return docs.flatMap(m => { let used = 0; const out: Source[] = [];
    for (const c of m.chunks) { if (used >= budget || out.length >= Math.floor(8 / Math.max(1, docs.length))) break;
      const text = c.text.slice(0, budget - used); out.push({ fileName: m.name, page: c.page, text }); used += text.length; }
    return out;
  });
}
export function grade(questions: Question[], answers: Record<number, string>, topic: string, materialId?: string): QuizResult {
  return { id: crypto.randomUUID(), topic, ...(materialId ? { materialId } : {}), correct: questions.filter((q, i) => answers[i] === q.correct_answer).length, total: questions.length, date: new Date().toISOString(), concepts: questions.map((q, i) => ({ topic: q.subtopic, correct: answers[i] === q.correct_answer })) };
}
export function progress(results: QuizResult[]) {
  const total = results.reduce((n, r) => n + r.total, 0), correct = results.reduce((n, r) => n + r.correct, 0);
  const concepts = new Map<string, { correct: number; total: number }>();
  results.flatMap(r => r.concepts).forEach(c => { const old = concepts.get(c.topic) || { correct: 0, total: 0 }; concepts.set(c.topic, { total: old.total + 1, correct: old.correct + Number(c.correct) }); });
  return { accuracy: total ? Math.round(100 * correct / total) : null, total, weak: [...concepts.entries()].filter(([, v]) => v.correct / v.total < .7).map(([topic]) => topic) };
}
// Without a shared PDF identity, use an exact normalised subject label rather
// than guessing which course an unrelated quiz or subtopic belongs to.
export function weakTopicsForPlan(results: QuizResult[], subject: string, materialId?: string): string[] {
  const normalise = (value: string) => value.normalize('NFKC').toLowerCase().replace(/[\s_-]+/gu, ' ').trim();
  const label = normalise(subject);
  if (!label) return [];
  const matching = results.filter(result => materialId
    ? result.materialId === materialId
    : !result.materialId && normalise(result.topic) === label);
  return progress(matching).weak.slice(0, 20);
}
export function parsePlan(markdown: string, count: number): PlanDay[] {
  const matches = [...markdown.matchAll(/^#{1,4}\s+Day\s+(\d+)\s*[:–—-]\s*(.+)$/gmi)];
  const days = matches.map((m, i) => ({ day: Number(m[1]), title: m[2].trim(), content: markdown.slice((m.index || 0) + m[0].length, matches[i + 1]?.index ?? markdown.length).trim() }));
  if (days.length !== count || days.some((d, i) => d.day !== i + 1 || !d.content)) throw new Error(`The AI plan must include ${count} separate study days. Please try again.`);
  return days;
}
export function normalizeMath(s: string) {
  return s.split(/(```[\s\S]*?```|`[^`\n]*`)/g).map((part, i) => i % 2 ? part : part.replace(/\\\[([\s\S]*?)\\\]/g, (_, x) => `\n$$\n${x}\n$$\n`).replace(/\\\((.*?)\\\)/g, (_, x) => `$${x}$`)).join('');
}
