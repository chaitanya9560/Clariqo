import { test } from 'node:test';
import assert from 'node:assert/strict';
import { learningSaver, LearningSaveConflict, type SaveState } from '../lib/learning-saver';
import { EMPTY_LEARNING, type Learning } from '../lib/types';
const value=(n:number):Learning=>({...structuredClone(EMPTY_LEARNING),totalQuestions:n});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve!:()=>void;const promise=new Promise<void>(r=>resolve=r);return{promise,resolve};}
test('failed final save stays dirty and retries the identical pending state',async()=>{
 const calls:number[]=[],states:SaveState[]=[];let fail=true;
 const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);if(fail)throw Error('Offline');},s=>states.push(s));
 saver.update(value(1));await assert.rejects(saver.flush(),/Offline/);assert.equal(saver.state().dirty,true);assert.equal(saver.state().status,'unsaved');
 fail=false;saver.retry();await saver.flush();assert.deepEqual(calls,[1,1]);assert.equal(saver.state().status,'saved');assert.equal(saver.state().dirty,false);assert.ok(states.some(s=>s.status==='saving'));
});
test('failed saves retain the latest edits without sending automatic repeated requests',async()=>{
 const calls:number[]=[];let fail=true;const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);if(fail)throw Error('Offline');},()=>{});
 saver.update(value(1));await assert.rejects(saver.flush());saver.update(value(2));saver.update(value(3));await tick();assert.deepEqual(calls,[1]);fail=false;saver.retry();await saver.flush();assert.deepEqual(calls,[1,3]);
});
test('serial saves coalesce pending edits and do not acknowledge newer edits early',async()=>{
 const gate=deferred(),calls:number[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);if(calls.length===1)await gate.promise;},()=>{});
 saver.update(value(1));await tick();saver.update(value(2));saver.update(value(3));assert.equal(saver.state().dirty,true);gate.resolve();await saver.flush();assert.deepEqual(calls,[1,3]);assert.equal(saver.state().dirty,false);
});
test('reverting during an in-flight save writes the original value back afterward',async()=>{
 const gate=deferred(),calls:number[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);if(calls.length===1)await gate.promise;},()=>{});
 saver.update(value(1));await tick();saver.update(value(0));gate.resolve();await saver.flush();assert.deepEqual(calls,[1,0]);assert.equal(saver.state().status,'saved');
});
test('revision conflict retains pending work and cannot be retried into an overwrite',async()=>{
 let calls=0;const saver=learningSaver(value(0),async()=>{calls++;throw new LearningSaveConflict();},()=>{});
 saver.update(value(1));await assert.rejects(saver.flush(),LearningSaveConflict);saver.retry();saver.update(value(2));await tick();assert.equal(calls,1);assert.equal(saver.state().status,'conflict');assert.equal(saver.state().dirty,true);await assert.rejects(saver.flush(),LearningSaveConflict);
});
test('pause waits for an in-flight save, blocks pending writes and reset clears them',async()=>{
 const gate=deferred(),calls:number[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);await gate.promise;},()=>{});
 saver.update(value(1));await tick();saver.update(value(2));const paused=saver.pause();gate.resolve();await paused;saver.reset(value(0));await saver.flush();assert.deepEqual(calls,[1]);assert.equal(saver.state().dirty,false);
});
test('failed clear can resume and save the latest pending edit',async()=>{
 const calls:number[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);},()=>{});await saver.pause();saver.update(value(2));await tick();assert.deepEqual(calls,[]);saver.resume();await saver.flush();assert.deepEqual(calls,[2]);
});
test('stopped account queue neither sends pending edits nor notifies the next session',async()=>{
 const gate=deferred(),calls:number[]=[],states:SaveState[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v.totalQuestions);await gate.promise;},s=>states.push(s));
 saver.update(value(1));await tick();saver.update(value(2));saver.stop();const count=states.length;gate.resolve();await tick();assert.deepEqual(calls,[1]);assert.equal(states.length,count);await assert.rejects(saver.flush(),/no longer active/);
});
test('initial state is not saved again and updates snapshot caller-owned data',async()=>{
 const calls:Learning[]=[];const saver=learningSaver(value(0),async v=>{calls.push(v);},()=>{});saver.update(value(0));await saver.flush();assert.equal(calls.length,0);const edit=value(1);saver.update(edit);edit.totalQuestions=99;await saver.flush();assert.equal(calls[0].totalQuestions,1);
});


test('lost response cannot falsely acknowledge a reversion to the old saved state',async()=>{
 let remote=0,fail=true;const saver=learningSaver(value(0),async v=>{remote=v.totalQuestions;if(fail)throw Error('Response lost after write');},()=>{});
 saver.update(value(1));await assert.rejects(saver.flush());assert.equal(remote,1);saver.update(value(0));assert.equal(saver.state().dirty,true);fail=false;saver.retry();await saver.flush();assert.equal(remote,0);assert.equal(saver.state().dirty,false);
});
