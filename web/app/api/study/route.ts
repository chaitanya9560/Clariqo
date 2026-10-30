import { handleStudyPost } from '@/lib/study-handler';
export const runtime = 'nodejs';
export const maxDuration = 60;
const headers = { 'Cache-Control': 'private, no-store' };
export async function GET() { return Response.json({ ok: true, authRequired: true, configured: Boolean(process.env.GROQ_API_KEY?.trim() && process.env.GROQ_API_KEY !== 'paste_your_groq_key_here'), accessCodeRequired: Boolean(process.env.DEMO_ACCESS_CODE) }, { headers }); }
export async function POST(request: Request) { return handleStudyPost(request); }
