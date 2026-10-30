'use client';
import { ArrowRight, BookOpen, FileText, Upload, Check } from 'lucide-react';
import type { Learning, Material, PageName } from '@/lib/types';
import { progress } from '@/lib/domain';
export function fileSize(bytes: number) { return bytes < 1048576 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1)} MB`; }
const title = (name: string) => name.replace(/\.pdf$/i, '').replace(/_/g, ' ');
export default function StudyDesk({ materials, learning, selected, disabled, onOpen, onNavigate, onTopic, onAsk }: {
  materials: Material[]; learning: Learning; selected: string; disabled: boolean;
  onOpen: (id: string) => void; onNavigate: (page: PageName) => void; onTopic: (topic: string) => void; onAsk: (question: string) => void;
}) {
  const current = materials.find(m => m.id === selected) || [...materials].sort((a,b) => b.addedAt.localeCompare(a.addedAt))[0];
  const stats = progress(learning.results), plan = learning.plan;
  const nextDays = plan?.days.filter(d => !plan.completed.includes(d.day)).slice(0,3) || [];
  return <div className="study-desk">
    <section className="continue-study" aria-labelledby="continue-heading">
      <div className="paper-thumbnail" aria-hidden="true"><FileText size={32} strokeWidth={1} /><i /><i /><i /></div>
      <div className="continue-copy"><span className="eyebrow">{current ? 'READY TO STUDY' : 'START WITH YOUR NOTES'}</span><h2 id="continue-heading">{current ? title(current.name) : 'A place for your study material.'}</h2><p>{current ? `${current.pageCount} ${current.pageCount === 1 ? 'page' : 'pages'} · ${fileSize(current.size)} · Saved to your account` : 'Upload a PDF to read, ask questions and practise.'}</p><button className="primary" disabled={disabled} onClick={() => current ? onOpen(current.id) : onNavigate('Study Materials')}>{current ? 'Open material' : 'Upload your first PDF'}<ArrowRight size={17} /></button></div>
    </section>
    <div className="desk-grid"><div className="desk-column">
      <section className="desk-section"><div className="section-title"><h2>Your materials</h2><button className="secondary" disabled={disabled} onClick={() => onNavigate('Study Materials')}><Upload size={15} />Upload PDF</button></div>
        {materials.length ? <div className="desk-materials">{materials.map(m => <button className="desk-material" key={m.id} disabled={disabled} onClick={() => onOpen(m.id)}><span className="document-icon"><FileText size={22} strokeWidth={1.3} /></span><span><strong>{title(m.name)}</strong><small>PDF · {m.pageCount} {m.pageCount === 1 ? 'page' : 'pages'} · {fileSize(m.size)}</small></span><ArrowRight size={16} /></button>)}</div> : <div className="desk-empty"><BookOpen size={25} strokeWidth={1.3} /><p>No PDFs yet. Add your notes when you’re ready.</p></div>}
      </section>
      <section className="desk-section"><div className="section-title"><h2>Ask about your notes</h2><span>PDF first</span></div><form className="desk-ask" onSubmit={e => {e.preventDefault(); const question = String(new FormData(e.currentTarget).get('question') || '').trim(); if (question) onAsk(question);}}><label className="sr-only" htmlFor="desk-question">Your study question</label><input id="desk-question" name="question" required maxLength={2000} placeholder="Explain a topic or ask a question…" disabled={disabled} /><button className="send-button" disabled={disabled} aria-label="Open question in Ask Clariqo"><ArrowRight size={20} /></button></form><p className="fine-print">Open your question in chat, then send it when you’re ready.</p></section>
    </div><div className="desk-column">
      <section className="desk-section"><div className="section-title"><h2>Your study plan</h2>{plan && <button className="text-button" disabled={disabled} onClick={() => onNavigate('Study Plan')}>View plan</button>}</div>
      {plan ? <><p className="plan-subject">{plan.subject}</p>{nextDays.length ? nextDays.map(d => <button className="desk-task" key={d.day} disabled={disabled} onClick={() => onNavigate('Study Plan')}><span className="task-square" aria-hidden="true" /><span><small>Day {d.day}</small><strong>{d.title}</strong></span><ArrowRight size={15} /></button>) : <p className="desk-complete"><Check size={17} />All {plan.days.length} study days marked complete.</p>}<p className="fine-print">{plan.completed.length} of {plan.days.length} days complete</p></> : <div className="desk-empty"><p>No plan saved yet. Choose a subject and exam date to map out your revision.</p><button className="text-button" disabled={disabled} onClick={() => onNavigate('Study Plan')}>Create a study plan <ArrowRight size={15} /></button></div>}</section>
      <section className="desk-section"><div className="section-title"><h2>Needs practice</h2><button className="text-button" disabled={disabled} onClick={() => onNavigate('My Progress')}>View progress</button></div>{stats.weak.length ? stats.weak.slice(0,3).map(topic => <button className="desk-focus" key={topic} disabled={disabled} onClick={() => onTopic(topic)}><span>{topic}</span><ArrowRight size={16} /></button>) : <div className="desk-empty"><p>{learning.results.length ? 'No topics below 70% in your saved quiz answers.' : 'Complete a quiz to find the topics that need another look.'}</p><button className="text-button" disabled={disabled} onClick={() => onNavigate('Quiz')}>Start practice <ArrowRight size={15} /></button></div>}</section>
    </div></div>
    <div className="desk-stats"><span><strong>{materials.length} {materials.length === 1 ? 'material' : 'materials'}</strong>Saved in your library</span><span><strong>{learning.results.length} {learning.results.length === 1 ? 'practice session' : 'practice sessions'}</strong>{stats.accuracy === null ? 'No quiz scores yet' : `${stats.accuracy}% overall accuracy`}</span><span><strong>{learning.totalQuestions} {learning.totalQuestions === 1 ? 'question' : 'questions'}</strong>Asked in chat</span></div>
  </div>;
}
