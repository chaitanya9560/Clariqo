import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';
import { authConfiguration } from './lib/auth-config';
export async function proxy(request: NextRequest) {
  const config = authConfiguration();
  if (!config) return NextResponse.next();
  let response = NextResponse.next({ request });
  const client = createServerClient(config.url, config.key, { cookies: {
    getAll() { return request.cookies.getAll(); },
    setAll(values, headers) {
      values.forEach(({ name, value }) => request.cookies.set(name, value));
      response = NextResponse.next({ request });
      values.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      Object.entries(headers || {}).forEach(([name, value]) => response.headers.set(name, String(value)));
    }
  } });
  await client.auth.getClaims();
  response.headers.set('Cache-Control', 'private, no-store');
  return response;
}
export const config = { matcher: ['/', '/login', '/auth/:path*', '/account/:path*'] };
