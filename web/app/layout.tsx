import type { Metadata } from 'next';
import 'katex/dist/katex.min.css';
import './globals.css';
export const metadata: Metadata = { title: 'Clariqo — Your study companion', description: 'Study your PDFs, ask questions, practise with quizzes and plan your revision.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
