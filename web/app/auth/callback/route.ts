import { NextResponse } from 'next/server';
import { serverClient } from '@/lib/supabase/server';
export async function GET(request: Request) {
  const url = new URL(request.url), code = url.searchParams.get('code');
  if (code) { try { const client = await serverClient(); const { error } = await client.auth.exchangeCodeForSession(code); if (!error) { const r = NextResponse.redirect(new URL('/', url.origin)); r.headers.set('Cache-Control', 'private, no-store'); return r; } } catch { /* Never log authorization codes or tokens. */ } }
  const r = NextResponse.redirect(new URL('/login?error=oauth', url.origin)); r.headers.set('Cache-Control', 'private, no-store'); return r;
}
