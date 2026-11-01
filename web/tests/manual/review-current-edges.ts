import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import type { SupabaseClient } from '@supabase/supabase-js';
import { cloudStudyStore } from '../../lib/cloud-storage';
import { parsePlan } from '../../lib/domain';
import { planDayCount } from '../../lib/schemas';
import { pdfCitationText } from '../../lib/pdf-citations';
async function main(){
 let bytesExist=true;const metadataExists=true;
 const client={from(){let deleting=false;const q={select(){return q;},eq(){return q;},maybeSingle:async()=>({data:{storage_path:'audit/doc/file.pdf'},error:null}),delete(){deleting=true;return q;},then(resolve:(value:unknown)=>unknown){return Promise.resolve(deleting?{error:{message:'database temporarily unavailable'}}:{error:null}).then(resolve);}};return q;},storage:{from(){return{remove:async()=>{bytesExist=false;return{error:null};}}}}} as unknown as SupabaseClient;
 await assert.rejects(cloudStudyStore(client,'audit').deleteMaterial('doc'),/library record/);
 assert.equal(bytesExist,false);assert.equal(metadataExists,true);
 const findings={partialDelete:{reproduced:true,bytesExist,metadataExists},plan61Days:planDayCount('2026-10-31','2026-12-31'),tipsInsideFinalDay:parsePlan('### Day 1: Read\n- Read notes\n\n### Exam tips\n- Rest',1)[0].content.includes('Exam tips'),legacyRangeMarker:pdfCitationText('Claim 【notes.pdf | pages 1-2】').answer};
 writeFileSync('../test_results/review-current/edge-cases.json',JSON.stringify(findings,null,2));console.log(JSON.stringify(findings,null,2));
}
void main();
