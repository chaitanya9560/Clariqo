import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { complete, safeHttpUrl } from '../lib/provider';
import { chat, makeQuiz, makePlan } from '../lib/service';
import { readJson, takeRateLimit, sameOrigin } from '../lib/http';
import { GET, POST as realPOST } from '../app/api/study/route';
import { handleStudyPost } from '../lib/study-handler';
import { LoginRequired } from '../lib/auth-config';
const student = { id: '11111111-1111-4111-8111-111111111111', email: 'test@example.invalid', displayName: 'Test' };
const POST = (request: Request) => handleStudyPost(request, async () => student);
const originalFetch = globalThis.fetch, originalKey = process.env.GROQ_API_KEY;
let sent: Record<string, unknown>[];
beforeEach(() => { process.env.GROQ_API_KEY = 'test-provider-secret'; delete process.env.DEMO_ACCESS_CODE; sent = []; });
afterEach(() => { globalThis.fetch = originalFetch; if (originalKey === undefined) delete process.env.GROQ_API_KEY; else process.env.GROQ_API_KEY = originalKey; delete process.env.DEMO_ACCESS_CODE; });
function respond(answer: string, extras = {}) { globalThis.fetch = async (_url, init) => { sent.push(JSON.parse(String(init?.body))); return Response.json({ choices: [{ message: { content: answer, ...extras }, finish_reason: 'stop' }] }); }; }
const input = { action: 'chat' as const, question: 'Explain elasticity', mode: 'chat' as const, context: [], history: [], hasMaterials: false };
function request(body: unknown, extra = {}) { return new Request('http://localhost/api/study', { method: 'POST', headers: { 'content-type': 'application/json', ...extra }, body: JSON.stringify(body) }); }
test('missing API key makes no external request', async () => { delete process.env.GROQ_API_KEY; globalThis.fetch = async () => { throw new Error('Must not call'); }; await assert.rejects(complete('hello', 'study'), /not configured/); });
test('key stays in authorization header, not prompt or response', async () => { let headers: HeadersInit | undefined; globalThis.fetch = async (_u, init) => { headers = init?.headers; assert.ok(!String(init?.body).includes('test-provider-secret')); return Response.json({ choices: [{ message: { content: 'Hi' } }] }); }; assert.equal((await complete('hello', 'study')).answer, 'Hi'); assert.equal(new Headers(headers).get('Authorization'), 'Bearer test-provider-secret'); });
test('provider errors and truncation never produce fake success', async () => { for (const status of [401, 429, 500]) { globalThis.fetch = async () => new Response('', { status }); await assert.rejects(complete('x', 'x')); } globalThis.fetch = async () => Response.json({ choices: [{ finish_reason: 'length', message: { content: 'cut' } }] }); await assert.rejects(complete('x', 'x'), /cut short/); });
test('plain conversation does not attach PDFs or enable search', async () => { respond('Hello!'); const r = await chat({ ...input, question: 'Hello' }); assert.equal(r.origin, 'conversation'); assert.ok(!('tools' in sent[0])); });
test('PDF answer carries supplied file/page references', async () => { respond('Elasticity changes resources.'); const r = await chat({ ...input, context: [{ fileName: 'notes.pdf', page: 3, text: 'Cloud elasticity scales resources.' }] }); assert.equal(r.origin, 'pdf'); assert.deepEqual(r.sources, [{ fileName: 'notes.pdf', page: 3 }]); });
test('PDF-only mode never searches even for a current question', async () => { respond('[NOT_IN_MATERIAL]'); const r = await chat({ ...input, mode: 'pdf', question: 'latest news', context: [{ fileName: 'x.pdf', page: 1, text: 'Algebra definitions.' }] }); assert.equal(r.origin, 'pdf'); assert.ok(sent.every(x => !x.tools)); });
test('explicit internet search does not send PDF excerpts or chat history', async () => { globalThis.fetch = async (_u, init) => { sent.push(JSON.parse(String(init?.body))); return Response.json({ choices: [{ message: { content: 'Online answer', executed_tools: [{ type: 'browser_search', index: 0, search_results: { results: [{ title: 'Official docs', url: 'https://example.org/docs' }] } }] } }] }); }; const r = await chat({ ...input, mode: 'web', context: [{ fileName: 'x.pdf', page: 1, text: 'PRIVATE_PDF_TEXT' }], history: [{ role: 'user', content: 'PRIVATE_HISTORY' }] }); assert.equal(r.origin, 'web'); assert.equal(sent.length, 1); assert.ok(!JSON.stringify(sent[0]).includes('PRIVATE_')); });
test('search without executed sources is reported honestly', async () => { respond('I think so'); const r = await chat({ ...input, mode: 'web' }); assert.equal(r.origin, 'error'); assert.deepEqual(r.webSources, []); });
test('unsafe source URLs are not passed through', () => { assert.equal(safeHttpUrl('javascript:alert(1)'), null); assert.equal(safeHttpUrl('https://user:pass@example.org'), null); assert.equal(safeHttpUrl('https://example.org/docs'), 'https://example.org/docs'); });
test('invalid or duplicate AI quiz is rejected', async () => { respond('not JSON'); await assert.rejects(makeQuiz({ action: 'quiz', topic: 'Cloud', difficulty: 'Easy', count: 5, context: [] })); });
test('wrong plan day count is rejected', async () => { respond('### Day 1: Read\n- Notes'); await assert.rejects(makePlan({ action: 'plan', subject: 'Cloud', examDate: '2026-11-01', today: '2026-10-30', hours: 2, level: 'Beginner', weakTopics: [], context: [] }), /2 separate/); });
test('streamed request body is bounded even without Content-Length', async () => { await assert.rejects(readJson(request({ x: 'x'.repeat(65000) })), /too large/); });
test('rate limiter bounds repeated requests and expires windows', () => { for (let i = 0; i < 30; i++) assert.equal(takeRateLimit('test-ip', 100), true); assert.equal(takeRateLimit('test-ip', 100), false); assert.equal(takeRateLimit('test-ip', 600101), true); });
test('health response exposes readiness but no credentials', async () => { const r = await GET(); const text = await r.text(); assert.match(text, /configured/); assert.ok(!text.includes('test-provider-secret')); });
test('API rejects invalid input before contacting provider', async () => { globalThis.fetch = async () => { throw new Error('Must not call'); }; const r = await POST(request({ action: 'quiz', topic: '', count: 3 })); assert.equal(r.status, 400); });
test('API rejects cross-origin requests', async () => { const r = await POST(request(input, { origin: 'https://attacker.example' })); assert.equal(r.status, 403); });
test('optional demo code is enforced', async () => { process.env.DEMO_ACCESS_CODE = 'test-code'; const r = await POST(request(input)); assert.equal(r.status, 401); respond('Hello'); const valid = await POST(request(input, { 'x-demo-code': 'test-code' })); assert.equal(valid.status, 200); });
test('API surfaces provider failure without credential details', async () => { globalThis.fetch = async () => new Response('', { status: 403 }); const r = await POST(request(input)); assert.equal(r.status, 502); assert.ok(!(await r.text()).includes('test-provider-secret')); });
test('structured study plan produces ordered days and preserves exam tips', async () => { respond(JSON.stringify({ days: [{ title: 'Foundations', content: '- Read for 60 minutes\n- Practise for 60 minutes' }, { title: 'Revision', content: '- Review for 120 minutes' }], tips: ['Review errors', 'Take breaks', 'Sleep well'] })); const r = await makePlan({ action: 'plan', subject: 'Cloud', examDate: '2026-11-01', today: '2026-10-30', hours: 2, level: 'Beginner', weakTopics: [], context: [] }); assert.equal(r.days.length, 2); assert.equal(r.days[1].day, 2); assert.match(r.markdown, /Sleep well/); assert.ok(sent[0].response_format); });
test('successful quiz generation returns all validated questions', async () => { const questions = Array.from({ length: 5 }, (_, i) => ({ question: `What does example ${i} describe?`, options: { A: 'Manual scaling', B: 'Elastic resources', C: 'Screen resolution', D: 'Battery life' }, correct_answer: 'B', explanation: 'Resources change with demand.', subtopic: 'Elasticity' })); respond(JSON.stringify(questions)); const r = await makeQuiz({ action: 'quiz', topic: 'Cloud', difficulty: 'Medium', count: 5, context: [] }); assert.equal(r.questions.length, 5); });

test('unauthenticated requests cannot reach the AI provider', async () => { let calls = 0; globalThis.fetch = async () => { calls++; throw new Error('Must not call'); }; const r = await handleStudyPost(request(input), async () => { throw new LoginRequired(); }); assert.equal(r.status, 401); assert.equal(calls, 0); });
test('missing auth configuration fails closed instead of allowing public AI', async () => { const oldUrl = process.env.NEXT_PUBLIC_SUPABASE_URL, oldKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY; delete process.env.NEXT_PUBLIC_SUPABASE_URL; delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY; try { const r = await realPOST(request(input)); assert.equal(r.status, 503); } finally { if (oldUrl) process.env.NEXT_PUBLIC_SUPABASE_URL = oldUrl; if (oldKey) process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = oldKey; } });

test('same-origin check uses the receiving host when Next uses an internal URL', () => {
  assert.equal(sameOrigin(new Request('http://localhost:3001/api/study', { headers: { host: '127.0.0.1:3001', origin: 'http://127.0.0.1:3001' } })), true);
  assert.equal(sameOrigin(new Request('https://internal/api/study', { headers: { host: 'clariqo.vercel.app', origin: 'https://evil.example' } })), false);
});

test('basic questions use general knowledge when a PDF has no matching passage', async () => {
  for (const question of ['what is oops', 'what is java programming']) {
    sent = []; respond('A clear general explanation.');
    const r = await chat({ ...input, question, hasMaterials: true });
    assert.equal(r.origin, 'general'); assert.equal(r.answer, 'A clear general explanation.');
    assert.deepEqual(r.sources, []); assert.deepEqual(r.webSources, []);
    assert.equal(sent.length, 1); assert.ok(!sent[0].tools);
  }
});
test('an insufficient PDF falls back to general chat without a needless search', async () => {
  globalThis.fetch = async (_url, init) => {
    sent.push(JSON.parse(String(init?.body)));
    return Response.json({ choices: [{ message: { content: sent.length === 1 ? '[NOT_IN_MATERIAL]' : 'Java is a programming language.' } }] });
  };
  const r = await chat({ ...input, question: 'what is java programming', hasMaterials: true, context: [{ fileName: 'notes.pdf', page: 1, text: 'PRIVATE_PDF_TEXT' }], history: [{ role: 'user', content: 'I am learning programming' }] });
  assert.equal(r.origin, 'general'); assert.match(r.answer, /Java/); assert.equal(sent.length, 2);
  assert.deepEqual(r.sources, []); assert.deepEqual(r.webSources, []);
  assert.ok(sent.every(call => !call.tools));
  assert.ok(!JSON.stringify(sent[1]).includes('PRIVATE_PDF_TEXT'));
  assert.ok(JSON.stringify(sent[1]).includes('I am learning programming'));
});
test('current information still requires a verified web result in Chat mode', async () => {
  respond('Unverified current information');
  const r = await chat({ ...input, question: 'latest Java release', hasMaterials: true, context: [{ fileName: 'notes.pdf', page: 1, text: 'PRIVATE_PDF_TEXT' }] });
  assert.equal(r.origin, 'error'); assert.equal(sent.length, 1); assert.ok(sent[0].tools);
  assert.ok(!JSON.stringify(sent[0]).includes('PRIVATE_PDF_TEXT'));
});

test('flashcards use the authenticated API and validated PDF references',async()=>{
  respond(JSON.stringify({cards:Array.from({length:5},(_,i)=>({front:`Question ${i+1}?`,back:'A concise answer.',sourceIndices:[1]}))}));
  const r=await POST(request({action:'flashcards',topic:'Java',count:5,context:[{fileName:'notes.pdf',page:2,text:'Java supports objects.'}]}));
  assert.equal(r.status,200);const data=await r.json();assert.equal(data.cards.length,5);assert.deepEqual(data.cards[0].sources,[{fileName:'notes.pdf',page:2}]);
});
test('mind-map API rejects cyclic generated concepts',async()=>{
  respond(JSON.stringify({nodes:[{id:'a',parentId:'b',label:'A',detail:'A concept',sourceIndices:[]},{id:'b',parentId:'a',label:'B',detail:'B concept',sourceIndices:[]}]}));
  const r=await POST(request({action:'mindmap',topic:'Java',context:[]}));assert.equal(r.status,502);assert.match((await r.json()).error,/invalid mind map/);
});
test('study-aid provider failures preserve honest errors rather than saving placeholder content',async()=>{
  globalThis.fetch=async()=>new Response('',{status:429});
  const r=await POST(request({action:'flashcards',topic:'Java',count:5,context:[]}));assert.equal(r.status,502);assert.match((await r.json()).error,/usage limit/);
});
test('new study-aid actions are blocked before provider access when signed out',async()=>{
  let calls=0;globalThis.fetch=async()=>{calls++;throw new Error('Do not call');};
  for(const action of ['flashcards','mindmap']){const r=await handleStudyPost(request({action,topic:'Java',count:5,context:[]}),async()=>{throw new LoginRequired();});assert.equal(r.status,401);}assert.equal(calls,0);
});
test('structured study-aid output accepts null error and refuses insufficient PDF content',async()=>{
  respond(JSON.stringify({nodes:[{id:'root',parentId:null,label:'Java',detail:'Programming language',sourceIndices:[]},{id:'classes',parentId:'root',label:'Classes',detail:'Object blueprints',sourceIndices:[]}],error:null}));
  const good=await POST(request({action:'mindmap',topic:'Java',context:[]}));assert.equal(good.status,200);assert.equal((await good.json()).nodes.length,2);assert.ok(sent[0].response_format);
  respond(JSON.stringify({cards:[],error:'Not covered by excerpts'}));
  const bad=await POST(request({action:'flashcards',topic:'Biology',count:5,context:[{fileName:'java.pdf',page:1,text:'Java classes define objects.'}]}));assert.equal(bad.status,502);assert.match((await bad.json()).error,/could not support/);
});
