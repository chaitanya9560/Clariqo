const windows = new Map<string, { count: number; until: number }>();
export function takeRateLimit(key: string, now = Date.now()) {
  for (const [id, entry] of windows) if (entry.until <= now) windows.delete(id);
  const entry = windows.get(key) || { count: 0, until: now + 600000 };
  if (entry.count >= 30 || (!windows.has(key) && windows.size >= 5000)) return false;
  entry.count++; windows.set(key, entry); return true;
}
export async function readJson(request: Request, limit = 64000) {
  if (!request.headers.get('content-type')?.includes('application/json')) throw new Error('Send a JSON request.');
  if (Number(request.headers.get('content-length') || 0) > limit) throw new Error('Request too large.');
  const reader = request.body?.getReader(); if (!reader) throw new Error('Request is empty.');
  const chunks: Uint8Array[] = []; let length = 0;
  try { while (true) { const { done, value } = await reader.read(); if (done) break; length += value.byteLength; if (length > limit) { await reader.cancel(); throw new Error('Request too large.'); } chunks.push(value); } }
  finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length); let offset = 0; for (const c of chunks) { bytes.set(c, offset); offset += c.length; }
  try { return JSON.parse(new TextDecoder().decode(bytes)); } catch { throw new Error('Invalid JSON request.'); }
}

export function sameOrigin(request: Request) {
  const origin = request.headers.get('origin');
  if (!origin) return true;
  const target = new URL(request.url), host = request.headers.get('host');
  // Next.js may use its internal hostname in request.url. Host is supplied by the
  // receiving HTTP server; browsers cannot override it with a cross-site fetch.
  try {
    const expected = host ? new URL(`${target.protocol}//${host}`) : target;
    return origin === expected.origin;
  } catch { return false; }
}
