import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import Markdown from '../components/Markdown';
import { normalizeMath } from '../lib/domain';
test('math renderer shows fractions and square roots as equations', () => { const html = renderToStaticMarkup(createElement(Markdown, { text: 'Area: $\\frac{x^2}{a^2}+\\sqrt{b}$' })); assert.match(html, /class="katex"/); assert.match(html, /<math/); });
test('Markdown does not execute raw HTML or javascript links', () => { const html = renderToStaticMarkup(createElement(Markdown, { text: '<script>alert(1)</script>\n\n[click](javascript:alert(1))' })); assert.ok(!html.includes('<script>')); assert.ok(!html.includes('href="javascript:')); });
test('normalizing equations leaves fenced code and inline code unchanged', () => { const input = '`\\(code\\)`\n```latex\n\\[code\\]\n```\n\\(a+b\\)'; const output = normalizeMath(input); assert.ok(output.includes('`\\(code\\)`')); assert.ok(output.includes('\\[code\\]')); assert.ok(output.endsWith('$a+b$')); });
