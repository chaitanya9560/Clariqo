import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { SupabaseClient } from '@supabase/supabase-js';
import { learningSaver, LearningSaveConflict } from '../lib/learning-saver';
import { cloudStudyStore } from '../lib/cloud-storage';
import { EMPTY_LEARNING, type Material } from '../lib/types';
const uid='11111111-1111-4111-8111-111111111111',mid='22222222-2222-4222-8222-222222222222';
function fake(options: { metadataFailure?: boolean; uploadFailure?: boolean; conflict?: boolean; storageFailure?: boolean; learningFailure?: boolean; insertConflict?: boolean; noLearning?: boolean }={}) {
 const calls: {op:string;value?:unknown}[]=[];
 const row={id:mid,user_id:uid,name:'notes.pdf',size:100,page_count:1,chunks:[{page:1,text:'Synthetic notes'}],storage_path:`${uid}/${mid}/old.pdf`,created_at:'2026-10-31'};
 const client={
  from(table:string){
   let operation='select';
   const query={select(){return query;},eq(key:string,value:unknown){calls.push({op:'filter:'+key,value});return query;},order(){return query;},
    insert(value:unknown){operation='insert';calls.push({op:table+':insert',value});return query;},
    update(value:unknown){operation='update';calls.push({op:table+':update',value});return query;},
    upsert(value:unknown){operation='upsert';calls.push({op:table+':upsert',value});return query;},
    delete(){operation='delete';calls.push({op:table+':delete'});return query;},
    single(){return Promise.resolve(result());},maybeSingle(){return Promise.resolve(table==='clariqo_materials'?{data:row,error:null}:operation==='select'&&options.noLearning?{data:null,error:null}:result());},
    then(resolve:(v:unknown)=>unknown,reject?:(e:unknown)=>unknown){return Promise.resolve(operation==='select'&&table==='clariqo_materials'?{data:[row],error:null}:result()).then(resolve,reject);}
   };
   function result(){return {data:operation==='update'?options.conflict?null:{revision:2}:table==='clariqo_learning'?{data:EMPTY_LEARNING,revision:1}:null,error:table==='clariqo_learning'&&operation==='update'&&options.learningFailure?{message:'offline'}:table==='clariqo_learning'&&operation==='insert'&&options.insertConflict?{code:'23505',message:'duplicate'}:operation==='upsert'&&options.metadataFailure?{message:'failed'}:null};}
   return query;
  },
  storage:{from(){return {
   async upload(path:string){calls.push({op:'upload',value:path});return {error:options.uploadFailure?{message:'failed'}:null};},
   async remove(paths:string[]){calls.push({op:'remove',value:paths});return {error:options.storageFailure?{message:'failed'}:null};},
   async download(path:string){calls.push({op:'download',value:path});return {data:new Blob(['synthetic PDF']),error:null};},
   async list(path:string){calls.push({op:'list',value:path});return {data:[],error:null};}
  };}}
 } as unknown as SupabaseClient;
 return {client,calls};
}
const material=():Material=>({id:mid,name:'notes.pdf',size:100,pageCount:1,chunks:[{page:1,text:'Synthetic notes'}],addedAt:'2026-10-31',file:new Blob(['synthetic PDF'])});
test('cloud saves wait for account loading and reject stale revisions',async()=>{
 const f=fake({conflict:true}),store=cloudStudyStore(f.client,uid);
 await assert.rejects(store.storeLearning(EMPTY_LEARNING),/finish loading/);
 await store.loadStudy();await assert.rejects(store.storeLearning(EMPTY_LEARNING),/newer work/);
 assert.ok(f.calls.some(c=>c.op==='filter:revision'&&c.value===1));
});
test('failed PDF metadata save removes only the new upload',async()=>{
 const f=fake({metadataFailure:true}),store=cloudStudyStore(f.client,uid);
 await assert.rejects(store.storeMaterial(material()),/previous saved PDF was kept/);
 const uploaded=f.calls.find(c=>c.op==='upload')!.value;
 assert.deepEqual(f.calls.filter(c=>c.op==='remove').map(c=>c.value),[[uploaded]]);
 assert.notEqual(uploaded,`${uid}/${mid}/old.pdf`);
});
test('failed PDF upload cannot replace metadata or delete previous bytes',async()=>{
 const f=fake({uploadFailure:true});await assert.rejects(cloudStudyStore(f.client,uid).storeMaterial(material()),/could not be saved/);
 assert.ok(!f.calls.some(c=>c.op.endsWith(':upsert')||c.op==='remove'));
});
test('successful same-document replacement uses a new private object then removes old version',async()=>{
 const f=fake(),m=material();await cloudStudyStore(f.client,uid).storeMaterial(m);
 assert.ok(m.storagePath?.startsWith(`${uid}/${mid}/`));
 assert.deepEqual(f.calls.filter(c=>c.op==='remove').map(c=>c.value),[[`${uid}/${mid}/old.pdf`]]);
 assert.ok(f.calls.findIndex(c=>c.op.endsWith(':upsert'))<f.calls.findIndex(c=>c.op==='remove'));
});
test('private downloads validate ownership before requesting bytes and cache repeat reads',async()=>{
 const f=fake(),store=cloudStudyStore(f.client,uid),m={...material(),file:undefined,storagePath:`${uid}/${mid}/old.pdf`};
 await assert.rejects(store.materialFile({...m,storagePath:'another-user/file.pdf'}),/unavailable/);
 assert.equal(f.calls.length,0);
 assert.equal(await (await store.materialFile(m)).text(),'synthetic PDF');await store.materialFile(m);
 assert.equal(f.calls.filter(c=>c.op==='download').length,1);
});
test('failed storage deletion preserves the PDF database record',async()=>{
 const f=fake({storageFailure:true});await assert.rejects(cloudStudyStore(f.client,uid).deleteMaterial(mid),/could not be removed/);
 assert.ok(!f.calls.some(c=>c.op==='clariqo_materials:delete'));
});


test('transient learning-save failure retains the revision and can retry the pending change',async()=>{
 const options={learningFailure:true},f=fake(options),store=cloudStudyStore(f.client,uid);
 const loaded=await store.loadStudy();const saver=learningSaver(loaded.learning,value=>store.storeLearning(value),()=>{});
 saver.update({...loaded.learning,totalQuestions:1});await assert.rejects(saver.flush(),error=>!(error instanceof LearningSaveConflict));
 assert.equal(saver.state().status,'unsaved');options.learningFailure=false;saver.retry();await saver.flush();
 assert.equal(saver.state().dirty,false);assert.deepEqual(f.calls.filter(c=>c.op==='filter:revision').map(c=>c.value),[1,1]);
});
test('concurrent initial insert is a conflict rather than an overwrite or automatic retry',async()=>{
 const f=fake({insertConflict:true,noLearning:true});
 const store=cloudStudyStore(f.client,uid);await store.loadStudy();await assert.rejects(store.storeLearning(EMPTY_LEARNING),LearningSaveConflict);
 assert.equal(f.calls.filter(c=>c.op==='clariqo_learning:update').length,0);
});
