import { z } from 'zod';
import type { Message, Source } from './types';
type Reference = Omit<Source, 'text'>;
const key = (source: Reference) => JSON.stringify([source.fileName, source.page]);
const unique = (sources: Reference[]) => sources.filter((source, index) => sources.findIndex(other => key(other) === key(source)) === index);
const NOT_IN_MATERIAL = '[NOT_IN_MATERIAL]';
const invalid = () => new Error('The AI reply did not include valid PDF references. Please try again or ask a more specific question.');
// Remove citation wrappers only outside code. Maths, ordinary brackets and code
// examples are left intact. Raw file/page strings never become trusted sources.
export function pdfCitationText(text: string) {
  const mentioned: Reference[] = [];
  const answer = text.split(/(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)/g).map((part, index) => index % 2 ? part : part.replace(
    /[【〖\[]\s*(?:File:\s*)?([^\]\n】〗]+?\.pdf)\s*(?:\||[,;])\s*(?:pages?|p\.?)\s*:?\s*(\d+)\s*[】〗\]]/gi,
    (_marker, fileName: string, page: string) => { mentioned.push({fileName:fileName.trim(),page:Number(page)}); return ''; }
  ).replace(/ +([.,;!?])/g,'$1')).join('').trim();
  return { answer, mentioned: unique(mentioned) };
}
export function pdfAnswerFormat(context: Source[]) {
  return { type:'json_schema',json_schema:{ name:'pdf_answer',strict:true,schema:{
    type:'object',additionalProperties:false,required:['answer','sourceIndices'],properties:{
      answer:{type:'string'},sourceIndices:{type:'array',minItems:0,maxItems:8,items:{type:'integer',enum:context.map((_,index)=>index+1)}}
    }
  }}};
}
export function parsePdfAnswer(raw: string, context: Source[]): {answer:string;sources:Reference[];citationVersion:1} | null {
  let value: {answer:string;sourceIndices:number[]};
  try { value=z.object({answer:z.string().trim().min(1).max(60000),sourceIndices:z.array(z.number().int().min(1).max(context.length)).max(8)}).strict().parse(JSON.parse(raw)); }
  catch { throw invalid(); }
  if(value.answer===NOT_IN_MATERIAL){if(value.sourceIndices.length)throw invalid();return null;}
  if(!value.sourceIndices.length)throw invalid();
  const sources=unique(value.sourceIndices.map(index=>({fileName:context[index-1].fileName,page:context[index-1].page})));
  const cleaned=pdfCitationText(value.answer);
  if(!cleaned.answer || cleaned.mentioned.some(source=>!sources.some(selected=>key(source)===key(selected))))throw invalid();
  return {answer:cleaned.answer,sources,citationVersion:1};
}
export function presentMessage(message: Message) {
  const sources=unique(message.sources||[]);
  if(message.role!=='assistant'||message.origin!=='pdf'&&!sources.length)return {answer:message.content,sources,label:'',note:''};
  const cleaned=pdfCitationText(message.content);
  if(message.citationVersion===1)return {answer:cleaned.answer,sources,label:'Cited PDF pages',note:''};
  const cited=cleaned.mentioned.filter(source=>sources.some(known=>key(source)===key(known)));
  return {
    answer:cleaned.answer,
    sources:cleaned.mentioned.length?cited:sources,
    label:cleaned.mentioned.length?'Pages mentioned in this older answer':'Retrieved pages for this older answer',
    note:sources.length||cleaned.mentioned.length?'This older answer predates citation checks. Open the pages to check its claims.':'',
  };
}
