'use client';
import { useState, type FormEvent } from 'react';
import { GraduationCap, ArrowRight, BookOpen, ShieldCheck, LoaderCircle, Eye, EyeOff, Mail } from 'lucide-react';
import { browserClient } from '@/lib/supabase/browser';
import { EmailSchema, NewPasswordSchema, authMessage } from '@/lib/email-auth';
type Mode = 'signin' | 'signup' | 'reset';
export default function LoginScreen({ configured, failed = false, initialMode = 'signin' }: { configured: boolean; failed?: boolean; initialMode?: Mode }) {
  const [mode, setMode] = useState<Mode>(initialMode), [busy, setBusy] = useState(false), [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState(''), [password, setPassword] = useState(''), [name, setName] = useState('');
  const [error, setError] = useState(failed ? 'This email link is invalid or has expired. Try signing in or request a new link.' : ''), [notice, setNotice] = useState('');
  const [sentAt, setSentAt] = useState(0);
  function switchMode(next: Mode) { setMode(next); setPassword(''); setShowPassword(false); setError(''); setNotice(''); }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return; setError(''); setNotice('');
    const parsed = EmailSchema.safeParse(email);
    if (!parsed.success) { setError(parsed.error.issues[0].message); return; }
    if (mode === 'signup') { const checked = NewPasswordSchema.safeParse(password); if (!checked.success) { setError(checked.error.issues[0].message); return; } }
    setBusy(true);
    try {
      const client = browserClient();
      if (mode === 'signin') {
        const { data, error } = await client.auth.signInWithPassword({ email: parsed.data, password });
        if (error) { setError(error.code === 'invalid_credentials' ? 'The email or password is incorrect.' : authMessage(error.code)); return; }
        if (!data.user?.email_confirmed_at || !data.session) { setError('Verify your email before signing in.'); return; }
        setPassword(''); window.location.replace('/');
      } else if (mode === 'signup') {
        const { error } = await client.auth.signUp({ email: parsed.data, password, options: { data: { full_name: name.trim().slice(0, 80) } } });
        if (error) { setError(authMessage(error.code)); return; }
        setPassword(''); setSentAt(Date.now()); setNotice('Check your inbox for a verification email. Verify your address, then sign in. If you already have an account, sign in instead.');
      } else {
        const { error } = await client.auth.resetPasswordForEmail(parsed.data);
        if (error) { setError(authMessage(error.code)); return; }
        setSentAt(Date.now()); setNotice('If an account exists for this address, a password-reset email has been sent. Check your inbox and spam folder.');
      }
    } catch { setError('Could not reach the sign-in service. Check your connection and try again.'); }
    finally { setBusy(false); }
  }
  async function resend() {
    if (busy) return; setError('');
    const parsed = EmailSchema.safeParse(email); if (!parsed.success) { setError('Enter your email address first.'); return; }
    if (Date.now() - sentAt < 60000) { setError('Please wait a minute before requesting another email.'); return; }
    setBusy(true);
    try { const { error } = await browserClient().auth.resend({ type: 'signup', email: parsed.data }); if (error) setError(authMessage(error.code)); else { setSentAt(Date.now()); setNotice('If this address has an unverified account, another verification email is on its way.'); } }
    catch { setError('The email request could not be completed. Please try again.'); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-story"><a className="brand" href="/"><span className="brand-mark"><GraduationCap size={23} /></span>clariqo<span className="brand-dot">.</span></a><span className="eyebrow">YOUR SPACE TO UNDERSTAND</span><h1>A little clarity.<br />A lot of <em>progress.</em></h1><p>Keep your notes, questions and revision plans together. Pick up where you left off, on any device.</p><div className="login-illustration" aria-hidden="true"><BookOpen size={85} strokeWidth={1} /></div><span className="login-story-note">Your study journey, one idea at a time.</span></section><section className="login-form"><div className="login-card"><span className="soft-icon"><GraduationCap size={24} /></span><span className="eyebrow">WELCOME TO CLARIQO</span><h2>{mode === 'signup' ? <>Make space<br />for your next idea.</> : mode === 'reset' ? <>A fresh password.<br />A fresh start.</> : <>A fresh start.<br />Or right where you left off.</>}</h2><p>{mode === 'signup' ? 'Create your account and verify your email to begin.' : mode === 'reset' ? 'We’ll send a secure reset link to your email.' : 'Sign in to open your private study space.'}</p>
    {mode !== 'reset' && <div className="auth-tabs" aria-label="Account access"><button type="button" aria-pressed={mode === 'signin'} onClick={() => switchMode('signin')} disabled={busy}>Sign in</button><button type="button" aria-pressed={mode === 'signup'} onClick={() => switchMode('signup')} disabled={busy}>Create account</button></div>}
    {!configured && <div className="alert" role="alert">Login setup is still being completed. Please check back shortly.</div>}{error && <div className="alert" role="alert">{error}</div>}{notice && <div className="notice" role="status"><Mail size={17} />{notice}</div>}
    <form onSubmit={submit} className="email-auth-form">{mode === 'signup' && <label className="field">Name <span className="optional">optional</span><input maxLength={80} autoComplete="name" value={name} onChange={e => setName(e.target.value)} disabled={busy || !configured} placeholder="What should we call you?" /></label>}<label className="field">Email<input type="email" required maxLength={254} autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} disabled={busy || !configured} placeholder="you@example.com" /></label>{mode !== 'reset' && <label className="field">Password<div className="password-input"><input type={showPassword ? 'text' : 'password'} required minLength={mode === 'signup' ? 8 : undefined} maxLength={128} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} disabled={busy || !configured} placeholder={mode === 'signup' ? 'At least 8 characters' : 'Your password'} /><button type="button" className="icon-button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>}
    <button className="primary auth-submit" disabled={!configured || busy}>{busy ? <LoaderCircle size={17} className="spin" /> : null}{busy ? 'Please wait…' : mode === 'signup' ? 'Create account' : mode === 'reset' ? 'Send reset link' : 'Sign in'}{!busy && <ArrowRight size={16} />}</button></form>
    <div className="auth-links">{mode === 'reset' ? <button type="button" className="text-button" onClick={() => switchMode('signin')} disabled={busy}>Back to sign in</button> : <><button type="button" className="text-button" onClick={() => switchMode('reset')} disabled={busy}>Forgot password?</button><button type="button" className="text-button" onClick={() => void resend()} disabled={busy || !configured}>Resend verification</button></>}</div>
    <div className="login-assurance"><ShieldCheck size={16} /><span>Your files and progress belong to your account.</span></div><p className="fine-print">Your email and password are handled securely by Supabase Auth. Relevant study excerpts are sent to Groq when you ask for AI help.</p><a className="text-button" href="https://github.com/chaitanya9560/Clariqo" target="_blank" rel="noreferrer">About the project ↗</a></div></section></main>;
}
