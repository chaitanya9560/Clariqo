import type { WebSource } from './types';
type ChatMessage = { role: 'user' | 'assistant' | 'system'; content: string };
export function safeHttpUrl(value: unknown): string | null {
  try { if (typeof value !== 'string') return null; const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; } catch { return null; }
}
export async function complete(prompt: string, system: string, options: { history?: ChatMessage[]; web?: boolean; format?: object } = {}) {
  const key = process.env.GROQ_API_KEY?.trim();
  if (!key || key === 'paste_your_groq_key_here') throw new Error('AI is not configured. The owner needs to set GROQ_API_KEY in the hosting environment.');
  const model = process.env.GROQ_MODEL?.trim() || 'openai/gpt-oss-120b';
  const body: Record<string, unknown> = { model, messages: [{ role: 'system', content: system }, ...(options.history || []).slice(-6), { role: 'user', content: prompt }], max_completion_tokens: 4096 };
  if (model.startsWith('openai/gpt-oss-')) body.reasoning_effort = 'low';
  if (options.web) { body.tools = [{ type: 'browser_search' }]; body.tool_choice = 'auto'; }
  if (options.format) body.response_format = options.format;
  let response: Response;
  try { response = await fetch('https://api.groq.com/openai/v1/chat/completions', { method: 'POST', headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: AbortSignal.timeout(25000), cache: 'no-store' }); }
  catch { throw new Error('The AI service did not respond in time. Please try again.'); }
  if ([401, 403].includes(response.status)) throw new Error('The AI provider rejected the configured key or account.');
  if (response.status === 429) throw new Error('The AI provider’s usage limit was reached. Please wait and try again.');
  if (!response.ok) throw new Error('The AI provider is unavailable or rejected this request. Please try again.');
  let data;
  try { data = await response.json(); } catch { throw new Error('The AI provider returned an unreadable reply.'); }
  const choice = data.choices?.[0];
  if (choice?.finish_reason === 'length') throw new Error('The AI reply was cut short. Try a smaller request.');
  const answer = choice?.message?.content;
  if (typeof answer !== 'string' || !answer.trim()) throw new Error('The AI provider returned an empty reply.');
  const tools = Array.isArray(choice.message.executed_tools) ? choice.message.executed_tools : [];
  const webSources: WebSource[] = []; const seen = new Set<string>(); const byTool = new Map<string, string>();
  for (const tool of tools) {
    for (const source of Array.isArray(tool.search_results?.results) ? tool.search_results.results : []) {
      const url = safeHttpUrl(source.url); if (!url) continue;
      byTool.set(String(tool.index), url);
      if (!seen.has(url)) { seen.add(url); webSources.push({ url, title: typeof source.title === 'string' ? source.title.slice(0, 200) : new URL(url).hostname }); }
    }
  }
  const clean = answer.trim().replace(/[【〖](\d+)†[^】〗]+[】〗]/g, (_: string, n: string) => byTool.has(n) ? ` [source](<${byTool.get(n)}>)` : '');
  return { answer: clean, searched: tools.some((t: { type?: string; name?: string }) => t.type === 'browser_search' || t.name === 'browser.search'), webSources: webSources.slice(0, 6) };
}
