'use client';
import { createBrowserClient } from '@supabase/ssr';
import { authConfiguration } from '../auth-config';
export function browserClient() {
  const config = authConfiguration();
  if (!config) throw new Error('Account sign-in is not configured yet.');
  return createBrowserClient(config.url, config.key);
}
