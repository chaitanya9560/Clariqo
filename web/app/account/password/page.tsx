import { redirect } from 'next/navigation';
import PasswordForm from '@/components/PasswordForm';
import { authConfiguration } from '@/lib/auth-config';
import { signedInStudent } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default async function Page() { if (!authConfiguration() || !await signedInStudent()) redirect('/login?mode=reset'); return <PasswordForm />; }
