import { studyReturnPath } from '@/lib/study-navigation';
import { redirect } from 'next/navigation';
import LoginScreen from '@/components/LoginScreen';
import { authConfiguration } from '@/lib/auth-config';
import { signedInStudent } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string; mode?: string; next?: string | string[] }> }) {
  const configured = Boolean(authConfiguration());
  const query = await searchParams;
  const returnTo = studyReturnPath(query.next);
  if (configured && await signedInStudent()) redirect(returnTo);
  return <LoginScreen returnTo={returnTo} configured={configured} failed={Boolean(query.error)} initialMode={query.mode === 'signup' ? 'signup' : query.mode === 'reset' ? 'reset' : 'signin'} />;
}
