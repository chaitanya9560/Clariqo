'use client';
import { useState, type FormEvent } from 'react';
import { browserClient } from '@/lib/supabase/browser';
import { NewPasswordSchema } from '@/lib/email-auth';
import { KeyRound, LoaderCircle } from 'lucide-react';
export default function PasswordForm() {
  const [password, setPassword] = useState(''), [confirm, setConfirm] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); if (busy) return; setError(''); const parsed = NewPasswordSchema.safeParse(password);
    if (!parsed.success) { setError(parsed.error.issues[0].message); return; } if (password !== confirm) { setError('The passwords do not match.'); return; }
    setBusy(true); try { const { error } = await browserClient().auth.updateUser({ password }); if (error) throw error; setPassword(''); setConfirm(''); window.location.replace('/'); }
    catch { setError('Your password could not be updated. Request a fresh reset link and try again.'); setBusy(false); }
  }
  return <main className="password-page"><section className="panel"><span className="soft-icon"><KeyRound size={22} /></span><h1>Choose a new password.</h1><p>Use at least 8 characters and keep it somewhere safe.</p>{error && <div className="alert" role="alert">{error}</div>}<form onSubmit={submit} className="email-auth-form"><label className="field">New password<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={password} disabled={busy} onChange={e => setPassword(e.target.value)} /></label><label className="field">Confirm password<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={confirm} disabled={busy} onChange={e => setConfirm(e.target.value)} /></label><button className="primary" disabled={busy}>{busy && <LoaderCircle size={15} className="spin" />}{busy ? 'Saving…' : 'Save password'}</button></form></section></main>;
}
