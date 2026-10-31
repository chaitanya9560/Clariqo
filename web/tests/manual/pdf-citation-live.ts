import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { chat } from '../../lib/service';
const context=[{fileName:'synthetic-java.pdf',page:2,text:'Encapsulation in Java hides internal object state with private fields. Controlled public methods can validate changes to that state.'},{fileName:'synthetic-history.pdf',page:8,text:'The Bastille was stormed on 14 July 1789.'}];
async function main(){
try {
 const r=await chat({action:'chat',question:'What is encapsulation in Java?',mode:'pdf',hasMaterials:true,history:[],context});
 assert.equal(r.origin,'pdf');assert.equal('citationVersion' in r&&r.citationVersion,1);assert.deepEqual(r.sources,[{fileName:'synthetic-java.pdf',page:2}]);assert.match(r.answer,/private|internal state/i);assert.ok(!/[【〖]/.test(r.answer));
 writeFileSync('../test_results/pdf-citation-live.json',JSON.stringify({passed:true,origin:r.origin,sources:r.sources,answer:r.answer},null,2));console.log('PASS real Groq structured PDF answer cites only the Java page.');
} catch(e){const detail=e instanceof Error?e.message:'Unknown error';writeFileSync('../test_results/pdf-citation-live.json',JSON.stringify({passed:false,detail},null,2));console.log('PDF citation live check:',detail);process.exitCode=1;}

}
void main();
