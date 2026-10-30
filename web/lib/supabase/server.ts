import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { authConfiguration, LoginRequired, type Student } from '../auth-config';
export async function serverClient() {
  const config = authConfiguration();
  if (!config) throw new LoginRequired('Account sign-in is not configured yet.', 503);
  const store = await cookies();
  return createServerClient(config.url, config.key, { cookies: {
    getAll() { return store.getAll(); },
    setAll(values) { try { values.forEach(({ name, value, options }) => store.set(name, value, options)); } catch { /* The proxy writes refresh cookies for Server Components. */ } }
  } });
}
export async function signedInStudent(): Promise<Student | null> {
  const client = await serverClient();
  const { data, error } = await client.auth.getUser();
  if (error || !data.user || data.user.is_anonymous || !data.user.email_confirmed_at) return null;
  return { id: data.user.id, email: data.user.email || '', displayName: String(data.user.user_metadata?.full_name || data.user.user_metadata?.name || data.user.email?.split('@')[0] || 'Student').slice(0, 80) };
}
export async function requireStudent() {
  const student = await signedInStudent();
  if (!student) throw new LoginRequired();
  return student;
}
