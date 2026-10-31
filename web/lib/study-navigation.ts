import type { PageName } from './types';
export const STUDY_SECTIONS = {
  Dashboard: '',
  'Study Materials': 'materials',
  'Ask AI': 'chat',
  Quiz: 'quiz',
  Flashcards: 'flashcards',
  'Mind Maps': 'mind-maps',
  'My Progress': 'progress',
  'Study Plan': 'study-plan',
} satisfies Record<PageName, string>;
type Query = Pick<URLSearchParams, 'getAll'>;
export function studyPage(query: Query): PageName {
  const values = query.getAll('page');
  if (values.length !== 1) return 'Dashboard';
  return (Object.entries(STUDY_SECTIONS).find(([, slug]) => slug === values[0])?.[0] as PageName | undefined) || 'Dashboard';
}
export function studyHref(page: PageName): string {
  const slug = STUDY_SECTIONS[page];
  return slug ? `/?page=${slug}` : '/';
}
// Push only when changing sections. Next's native-history integration updates
// useSearchParams without reloading the study component or its pending saves.
export function pushStudyPage(page: PageName, location: Pick<Location, 'pathname' | 'search'>, history: Pick<History, 'pushState'>) {
  if (location.pathname === '/' && studyPage(new URLSearchParams(location.search)) === page) return;
  history.pushState(null, '', studyHref(page));
}
// Only return to one of our own canonical study URLs, never an arbitrary URL.
export function studyReturnPath(value: unknown): string {
  if (typeof value !== 'string') return '/';
  return (Object.keys(STUDY_SECTIONS) as PageName[]).map(studyHref).includes(value) ? value : '/';
}
export function studyLoginHref(page: PageName): string {
  const target = studyHref(page);
  return target === '/' ? '/login' : `/login?next=${encodeURIComponent(target)}`;
}
