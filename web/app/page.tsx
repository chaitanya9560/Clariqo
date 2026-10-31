import { studyPage, studyLoginHref } from '@/lib/study-navigation';
import { redirect } from 'next/navigation';
import StudyApp from '@/components/StudyApp';
import { authConfiguration } from '@/lib/auth-config';
import { signedInStudent } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default async function Page({ searchParams }: { searchParams: Promise<{ page?: string | string[] }> }) {
  const query = await searchParams;
  const params = new URLSearchParams();
  for (const value of Array.isArray(query.page) ? query.page : query.page === undefined ? [] : [query.page]) params.append('page', value);
  const login = studyLoginHref(studyPage(params));
  if (!authConfiguration()) redirect(login);
  const student = await signedInStudent();
  if (!student) redirect(login);
  return <StudyApp key={student.id} student={student} />;
}
