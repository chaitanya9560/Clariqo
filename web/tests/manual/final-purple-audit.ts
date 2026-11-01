// Read-only live-provider audit. Uses only synthetic study content, no account or cloud writes.
import assert from 'node:assert/strict';
import { chat, makeQuiz, makePlan } from '../../lib/service';
import { grade, progress } from '../../lib/domain';
import { makeFlashcards, makeMindMap } from '../../lib/study-aid-service';
import { mkdirSync, writeFileSync } from 'node:fs';
mkdirSync('../test_results', { recursive: true });
let quotaBlocked = false;
const checks: { name: string; passed: boolean; detail?: string; skipped?: boolean }[] = [];
async function run(name: string, fn: () => Promise<void>) {
  if(quotaBlocked){checks.push({name,passed:false,skipped:true,detail:'Not attempted after a provider usage-limit response.'});writeFileSync('../test_results/final-purple-feature-live.json',JSON.stringify(checks,null,2));console.log('SKIP',name);return;}
  try { await fn(); checks.push({ name, passed: true }); console.log('PASS',name); }
  catch(e) { const detail=e instanceof Error ? e.message : 'Unknown failure'; if(/usage limit/i.test(detail))quotaBlocked=true; checks.push({name,passed:false,detail}); console.log('FAIL',name,detail); }
  writeFileSync('../test_results/final-purple-feature-live.json',JSON.stringify(checks,null,2));
}
const context=[{fileName:'synthetic-java.pdf',page:1,text:'Java is a programming language. Object-oriented programming organizes code into classes and objects. Encapsulation hides internal state. Inheritance allows a class to reuse another class. Polymorphism allows a shared interface to have different implementations. Abstraction exposes essential behavior and hides implementation details.'}];
const base={action:'chat' as const,mode:'chat' as const,hasMaterials:true,history:[],context:[]};
async function main(){
 await run('OOP general answer with a saved PDF but no matching passage',async()=>{const r=await chat({...base,question:'what is oops'});assert.equal(r.origin,'general');assert.match(r.answer,/object.oriented/i);});
 await run('Java question uses the supplied PDF and page references',async()=>{const r=await chat({...base,mode:'pdf',question:'What is encapsulation?',context});assert.equal(r.origin,'pdf');assert.match(r.answer,/encapsulat|internal state/i);assert.equal(r.sources[0]?.page,1);});
 await run('PDF-only rejects unrelated content without internet',async()=>{const r=await chat({...base,mode:'pdf',question:'What is the capital city of France?',context});assert.equal(r.origin,'pdf');assert.deepEqual(r.sources,[]);assert.match(r.answer,/do not cover|matching passage/i);});
 await run('Conversational follow-up retains context',async()=>{const r=await chat({...base,question:'Explain it with a simple example',history:[{role:'user' as const,content:'What is Java encapsulation?'},{role:'assistant' as const,content:'Encapsulation hides internal object state behind methods.'}]});assert.equal(r.origin,'general');assert.match(r.answer,/encapsulat|private|balance/i);});
 await run('Five-question quiz, grading and weak topics',async()=>{const r=await makeQuiz({action:'quiz',topic:'Java object-oriented programming',count:5,difficulty:'Easy',context});assert.equal(r.questions.length,5);const answers=Object.fromEntries(r.questions.map((q,i)=>[i,q.correct_answer]));const score=grade(r.questions,answers,'Java');assert.equal(score.correct,5);assert.equal(progress([score]).accuracy,100);assert.equal(progress([grade(r.questions,{},'Java')]).accuracy,0);});
 await run('Two-day study plan contains tasks and completion-ready days',async()=>{const r=await makePlan({action:'plan',subject:'Java OOP',today:'2026-10-31',examDate:'2026-11-02',hours:1,level:'Beginner',weakTopics:['Encapsulation'],context});assert.equal(r.days.length,2);assert.equal(r.days[1].day,2);assert.ok(r.days.every(d=>d.content.length>10));assert.match(r.markdown,/Exam tips/);});
 await run('Internet mode returns real executed search sources',async()=>{const r=await chat({...base,mode:'web',question:'Search the web for the official Oracle Java documentation for classes and objects.'});assert.equal(r.origin,'web',`Internet response origin: ${r.origin}`);assert.ok(r.webSources.length>0,'No executed search sources returned');assert.ok(r.webSources.every(s=>['http:','https:'].includes(new URL(s.url).protocol)),'Invalid search source protocol');});
 await run('PDF flashcards contain five cards and valid page references',async()=>{const r=await makeFlashcards({action:'flashcards',topic:'Java OOP',count:5,context});assert.equal(r.cards.length,5);assert.ok(r.cards.every(c=>c.sources.length>0&&c.sources.every(s=>s.fileName==='synthetic-java.pdf'&&s.page===1)));});
 await run('General flashcards do not invent PDF sources',async()=>{const r=await makeFlashcards({action:'flashcards',topic:'Java encapsulation',count:5,context:[]});assert.equal(r.cards.length,5);assert.ok(r.cards.every(c=>c.sources.length===0));});
 await run('PDF mind map has one root and supplied references',async()=>{const r=await makeMindMap({action:'mindmap',topic:'Java OOP',context});assert.equal(r.nodes.filter(n=>n.parentId===null).length,1);assert.ok(r.nodes.length>=6);assert.ok(r.nodes.every(n=>n.sources.length>0));});
 console.log('Live feature results:',checks.filter(c=>c.passed).length+'/'+checks.length);process.exitCode=checks.every(c=>c.passed)?0:1;
}
main().catch(()=>{console.error('Audit interrupted');process.exitCode=1;});
