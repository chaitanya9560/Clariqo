import { chunkPage } from './domain';
import type { Material } from './types';
export async function readPdf(file: File, onProgress: (value: string) => void): Promise<Material> {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a PDF file.');
  if (file.size > 20 * 1024 * 1024) throw new Error('The PDF limit is 20 MB per file.');
  const pdfjs = await import('pdfjs-dist');
  pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
  const loading = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()), useSystemFonts: true, disableFontFace: true });
  try {
    const pdf = await loading.promise;
    if (pdf.numPages > 200) throw new Error('Use a PDF with up to 200 pages for this demo.');
    const chunks: Material['chunks'] = []; let total = 0;
    for (let page = 1; page <= pdf.numPages; page++) {
      onProgress(`Reading page ${page} of ${pdf.numPages}…`);
      const p = await pdf.getPage(page); const content = await p.getTextContent();
      const text = content.items.map(item => 'str' in item ? item.str + ('hasEOL' in item && item.hasEOL ? '\n' : ' ') : '').join('');
      total += text.length;
      if (total > 300000) throw new Error('This PDF has too much text. Please upload a smaller section.');
      chunks.push(...chunkPage(text, page)); p.cleanup();
    }
    if (total < 25) throw new Error('No readable text was found. Scanned PDFs need OCR, which is not included.');
    return { id: crypto.randomUUID(), name: file.name, size: file.size, pageCount: pdf.numPages, chunks, file, addedAt: new Date().toISOString() };
  } finally { await loading.destroy(); }
}
