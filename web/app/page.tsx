import { redirect } from 'next/navigation';
import StudyApp from '@/components/StudyApp';
import { authConfiguration } from '@/lib/auth-config';
import { signedInStudent } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default async function Page() {
  if (!authConfiguration()) redirect('/login');
  const student = await signedInStudent();
  if (!student) redirect('/login');
  return <StudyApp key={student.id} student={student} />;
}
