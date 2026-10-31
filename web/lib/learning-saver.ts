import type { Learning } from './types';
export type SaveState = { status: 'saved' | 'saving' | 'unsaved' | 'conflict'; dirty: boolean; message: string };
export class LearningSaveConflict extends Error {
  constructor() { super('Another tab or device has newer work saved. Download your unsaved backup before reloading.'); this.name = 'LearningSaveConflict'; }
}
// Keep the last acknowledged snapshot separate from the latest desired state.
// A failed request never advances the acknowledged snapshot or drops pending work.
export function learningSaver(initial: Learning, save: (value: Learning) => Promise<void>, notify: (state: SaveState) => void) {
  let confirmed = JSON.stringify(initial);
  let desired = { snapshot: confirmed, value: structuredClone(initial) };
  let running: Promise<void> | null = null, active = true, paused = false;
  let failure: Error | null = null, uncertain = false;
  function state(): SaveState {
    const dirty = desired.snapshot !== confirmed || running !== null || failure !== null || uncertain;
    return { status: failure ? failure instanceof LearningSaveConflict ? 'conflict' : 'unsaved' : running ? 'saving' : dirty ? 'unsaved' : 'saved', dirty, message: failure?.message || '' };
  }
  function publish() { if (active) notify(state()); }
  function pump() {
    if (!active || paused || running || failure || desired.snapshot === confirmed && !uncertain) { publish(); return; }
    running = Promise.resolve().then(async () => {
      while (active && !paused && !failure && (desired.snapshot !== confirmed || uncertain)) {
        const job = desired;
        try { await save(structuredClone(job.value)); confirmed = job.snapshot; uncertain = false; }
        catch (error) { uncertain = true; failure = error instanceof Error ? error : new Error('Your changes could not be saved. Check your connection and retry.'); }
      }
    }).finally(() => { running = null; publish(); });
    publish();
  }
  return {
    update(value: Learning) {
      if (!active) return;
      desired = { snapshot: JSON.stringify(value), value: structuredClone(value) };
      pump();
    },
    retry() { if (!active || failure instanceof LearningSaveConflict) return; failure = null; pump(); },
    state,
    async flush() {
      if (!active) throw new Error('Your study session is no longer active.');
      pump();
      while (running) await running;
      if (failure) throw failure;
      if (desired.snapshot !== confirmed || uncertain) throw new Error('Your changes are not saved yet. Retry the save before signing out.');
    },
    async pause() { paused = true; if (running) await running; },
    resume() { paused = false; pump(); },
    reset(value: Learning) {
      if (running) throw new Error('Wait for the current save before resetting.');
      confirmed = JSON.stringify(value); desired = { snapshot: confirmed, value: structuredClone(value) }; failure = null; uncertain = false; paused = false; publish();
    },
    stop() { active = false; paused = true; },
  };
}
