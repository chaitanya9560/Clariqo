import { RequestSchema } from '@/lib/schemas';
import { chat, makeQuiz, makePlan } from '@/lib/service';
import { readJson, takeRateLimit } from '@/lib/http';
export const runtime = 'nodejs';
export const maxDuration = 60;
const headers = { 'Cache-Control': 'no-store' };
export async function GET() { return Response.json({ ok: true, configured: Boolean(process.env.GROQ_API_KEY?.trim() && process.env.GROQ_API_KEY !== 'paste_your_groq_key_here'), accessCodeRequired: Boolean(process.env.DEMO_ACCESS_CODE) }, { headers }); }
export async function POST(request: Request) {
  const origin = request.headers.get('origin');
  if (origin && origin !== new URL(request.url).origin) return Response.json({ error: 'Cross-origin requests are not allowed.' }, { status: 403, headers });
  if (process.env.DEMO_ACCESS_CODE && request.headers.get('x-demo-code') !== process.env.DEMO_ACCESS_CODE) return Response.json({ error: 'Enter the demo access code supplied by the owner.' }, { status: 401, headers });
  const client = request.headers.get('x-vercel-forwarded-for') || request.headers.get('x-forwarded-for') || 'local';
  if (!takeRateLimit(client.split(',')[0].trim())) return Response.json({ error: 'Too many requests. Wait a few minutes and try again.' }, { status: 429, headers });
  let input;
  try { input = RequestSchema.parse(await readJson(request)); }
  catch { return Response.json({ error: 'Invalid request. Check the question, date and selected material, then try again.' }, { status: 400, headers }); }
  try {
    const result = input.action === 'chat' ? await chat(input) : input.action === 'quiz' ? await makeQuiz(input) : await makePlan(input);
    return Response.json(result, { headers });
  } catch (error) {
    const secret = process.env.GROQ_API_KEY;
    let message = error instanceof Error ? error.message : 'The request could not be completed.';
    if (secret) message = message.split(secret).join('[REDACTED]');
    return Response.json({ error: message.slice(0, 500) }, { status: 502, headers });
  }
}
