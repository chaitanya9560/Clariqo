import { z } from 'zod';
import type { Source } from './types';
export const AidReferenceSchema = z.object({ fileName: z.string().min(1).max(200), page: z.number().int().min(1).max(200) });
const text = (max: number) => z.string().trim().min(1).max(max);
export const CardSchema = z.object({ id: text(80), front: text(500), back: text(2000), sources: z.array(AidReferenceSchema).max(3) });
export const DeckSchema = z.object({ id: text(100), title: text(200), createdAt: z.string().datetime(), sourceNames: z.array(text(200)).max(5), cards: z.array(CardSchema).min(1).max(10), progress: z.record(z.string().max(80), z.enum(['known', 'review'])) }).refine(d => new Set(d.cards.map(c => c.id)).size === d.cards.length && Object.keys(d.progress).every(key => d.cards.some(c => c.id === key)), 'Invalid card progress.');
export const MapNodeSchema = z.object({ id: text(40).regex(/^[a-zA-Z0-9_-]+$/), parentId: z.string().max(40).nullable(), label: text(100), detail: text(1500), sources: z.array(AidReferenceSchema).max(3) });
export function validTree(nodes: { id: string; parentId: string | null }[]) {
  const byId = new Map(nodes.map(n => [n.id, n]));
  if (byId.size !== nodes.length || nodes.filter(n => n.parentId === null).length !== 1) return false;
  return nodes.every(node => {
    const seen = new Set<string>(); let cursor: typeof node | undefined = node;
    while (cursor) {
      if (seen.has(cursor.id) || seen.size >= 4) return false;
      seen.add(cursor.id);
      if (cursor.parentId === null) return true;
      cursor = byId.get(cursor.parentId); if (!cursor) return false;
    }
    return false;
  });
}
export const MindMapSchema = z.object({ id: text(100), title: text(200), createdAt: z.string().datetime(), sourceNames: z.array(text(200)).max(5), nodes: z.array(MapNodeSchema).min(2).max(20) }).refine(m => validTree(m.nodes), 'The mind map must be one connected tree with up to four levels.');
export type FlashcardDeck = z.infer<typeof DeckSchema>;
export type MindMap = z.infer<typeof MindMapSchema>;
export type MapNode = z.infer<typeof MapNodeSchema>;
const indices = z.array(z.number().int().min(1).max(8)).max(3);
const generatedCard = z.object({ front: text(500), back: text(2000), sourceIndices: indices });
const generatedNode = z.object({ id: text(40).regex(/^[a-zA-Z0-9_-]+$/), parentId: z.string().max(40).nullable(), label: text(100), detail: text(1500), sourceIndices: indices });
function references(values: number[], context: Source[]) {
  if (values.some(value => !context[value - 1])) throw new Error('The AI referenced material that was not supplied. Please generate again.');
  return [...new Set(values)].map(i => ({ fileName: context[i - 1].fileName, page: context[i - 1].page })).filter((s,i,all) => all.findIndex(r => r.fileName === s.fileName && r.page === s.page) === i);
}
export function validateCards(value: unknown, count: number, context: Source[]) {
  const cards = z.object({ cards: z.array(generatedCard).length(count) }).parse(value).cards;
  const normalized = cards.map(c => c.front.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ''));
  if (new Set(normalized).size !== count) throw new Error('The AI repeated a flashcard. Please generate again.');
  return cards.map((c, i) => {
    if (context.length && !c.sourceIndices.length) throw new Error('A PDF flashcard is missing its reference. Please generate again.');
    return { id: `card-${i + 1}`, front: c.front, back: c.back, sources: references(c.sourceIndices, context) };
  });
}
export function validateMap(value: unknown, context: Source[]) {
  const nodes = z.object({ nodes: z.array(generatedNode).min(2).max(20) }).parse(value).nodes;
  if (!validTree(nodes)) throw new Error('The AI returned an invalid mind map. Please generate again.');
  return nodes.map(({ sourceIndices, ...node }) => {
    if (context.length && !sourceIndices.length) throw new Error('A PDF concept is missing its reference. Please generate again.');
    return { ...node, sources: references(sourceIndices, context) };
  });
}
