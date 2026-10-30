export function authConfiguration() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!url || !key) return null;
  try { const parsed = new URL(url); if (!['https:', 'http:'].includes(parsed.protocol)) return null; } catch { return null; }
  return { url, key };
}
export class LoginRequired extends Error {
  constructor(message = 'Please sign in to use Clariqo.', public status = 401) { super(message); }
}
export type Student = { id: string; email: string; displayName: string };
