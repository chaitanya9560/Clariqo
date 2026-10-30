import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readPdf } from '../lib/pdf';
test('non-PDF input fails before parsing or uploading',async()=>{
 await assert.rejects(readPdf(new File(['hello'],'notes.txt'),()=>{}),/Choose a PDF/);
});
test('PDF above 20 MiB fails before parsing or uploading',async()=>{
 const file={name:'large.pdf',size:20*1024*1024+1,arrayBuffer(){throw new Error('Must not read oversized file');}} as unknown as File;
 await assert.rejects(readPdf(file,()=>{}),/20 MB/);
});
