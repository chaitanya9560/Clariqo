import { RequestSchema } from './schemas';
import { chat, makeQuiz, makePlan } from './service';
import { readJson, takeRateLimit, sameOrigin } from './http';
import { LoginRequired, type Student } from './auth-config';
import { requireStudent } from './supabase/server';
const headers = { 'Cache-Control': 'private, no-store' };
export async function handleStudyPost(request: Request, authenticate: () => Promise<Student> = requireStudent) {
  if (!sameOrigin(request)) return Response.json({ error: 'Cross-origin requests are not allowed.' }, { status: 403, headers });
  let student: Student;
  try { student = await authenticate(); } catch (error) { return Response.json({ error: error instanceof LoginRequired ? error.message : 'Sign-in could not be verified. Try again.' }, { status: error instanceof LoginRequired ? error.status : 503, headers }); }
  if (process.env.DEMO_ACCESS_CODE && request.headers.get('x-demo-code') !== process.env.DEMO_ACCESS_CODE) return Response.json({ error: 'Enter the demo access code supplied by the owner.' }, { status: 401, headers });
  if (!takeRateLimit('student:' + student.id)) return Response.json({ error: 'Too many requests. Wait a few minutes and try again.' }, { status: 429, headers });
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
