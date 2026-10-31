import { test } from 'node:test';
import assert from 'node:assert/strict';
import { STUDY_SECTIONS, studyPage, studyHref, pushStudyPage, studyReturnPath, studyLoginHref } from '../lib/study-navigation';
import type { PageName } from '../lib/types';
test('all eight sections have distinct URLs that survive bookmark or refresh parsing',()=>{
 const pages=Object.keys(STUDY_SECTIONS) as PageName[];assert.equal(pages.length,8);assert.equal(new Set(pages.map(studyHref)).size,8);
 for(const page of pages){const url=new URL(studyHref(page),'https://clariqo.vercel.app');assert.equal(studyPage(url.searchParams),page);assert.equal(studyReturnPath(url.pathname+url.search),studyHref(page));}
});
test('invalid, missing and repeated section parameters safely display Dashboard',()=>{
 for(const query of ['', '?page=unknown', '?page=quiz&page=chat', '?page=https%3A%2F%2Fevil.example', '?page=Quiz'])assert.equal(studyPage(new URLSearchParams(query)),'Dashboard');
 assert.equal(studyPage(new URLSearchParams('?utm_source=demo&page=quiz')),'Quiz');
});
test('navigation creates history entries only for changed sections',()=>{
 const calls:unknown[][]=[];const history={pushState(...args:unknown[]){calls.push(args);}};
 pushStudyPage('Quiz',{pathname:'/',search:''},history);assert.deepEqual(calls,[[null,'','/?page=quiz']]);
 pushStudyPage('Quiz',{pathname:'/',search:'?page=quiz'},history);assert.equal(calls.length,1);
 pushStudyPage('Dashboard',{pathname:'/',search:'?page=quiz'},history);assert.equal(calls[1][2],'/');
});
test('back and forward URLs resolve to their own sections rather than Dashboard',()=>{
 const entries=['/',studyHref('Quiz'),studyHref('Study Plan'),studyHref('Mind Maps')];let index=3;
 assert.equal(studyPage(new URL(entries[--index],'https://clariqo.vercel.app').searchParams),'Study Plan');
 assert.equal(studyPage(new URL(entries[--index],'https://clariqo.vercel.app').searchParams),'Quiz');
 assert.equal(studyPage(new URL(entries[++index],'https://clariqo.vercel.app').searchParams),'Study Plan');
});
test('bookmarked sections preserve a safe destination through the login URL',()=>{
 assert.equal(studyLoginHref('Dashboard'),'/login');
 for(const page of Object.keys(STUDY_SECTIONS) as PageName[]){const login=new URL(studyLoginHref(page),'https://clariqo.vercel.app');assert.equal(studyReturnPath(login.searchParams.get('next')),studyHref(page));}
});
test('login return destinations cannot be external URLs or arbitrary internal paths',()=>{
 for(const unsafe of [undefined,null,[],['/?page=quiz'],'https://evil.example','//evil.example','/\\evil.example','javascript:alert(1)','/api/study','/account/password','/?page=quiz&next=https://evil.example','/?page=unknown','/%2f%2fevil.example',' /?page=quiz'])assert.equal(studyReturnPath(unsafe),'/');
});
