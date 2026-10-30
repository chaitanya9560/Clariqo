import { NextResponse } from 'next/server';
import { serverClient } from '@/lib/supabase/server';
import { recoveryDestination } from '@/lib/email-auth';
export async function GET(request: Request) {
  const url = new URL(request.url), token = url.searchParams.get('token_hash'), type = url.searchParams.get('type');
  if (token && (type === 'email' || type === 'recovery')) {
    try { const client = await serverClient(); const { error } = await client.auth.verifyOtp({ token_hash: token, type });
      if (!error) { const r = NextResponse.redirect(new URL(recoveryDestination(type), url.origin)); r.headers.set('Cache-Control', 'private, no-store'); return r; }
    } catch { /* Never log email tokens. */ }
  }
  const r = NextResponse.redirect(new URL('/login?error=email_link', url.origin)); r.headers.set('Cache-Control', 'private, no-store'); return r;
}
