# Failed-save recovery

The old learning-state effect marked its snapshot as saved before Supabase confirmed it. A failed last save was not retried unless the user made another change, and reloading could discard that work.

The learning save queue now separates the last confirmed snapshot from the latest requested snapshot. It writes serially, coalesces newer pending edits, and advances its confirmed state only after a successful response. A failed or uncertain write leaves the latest work pending, even when the user changes it back to the previously saved value. Data objects are cloned before entering the queue.

The app shows a persistent unsaved-work banner with **Retry save** and **Download unsaved backup**. The banner remains across section changes. Coming back online also retries a transient failure. Retries are event-driven, not a repeating request loop. The backup is JSON learning state (chat, quizzes, plans and study tools), not a PDF archive or an automatic restore file.

Before leaving or refreshing, the browser is asked to warn if changes remain pending. Browser prompts depend on browser support and user interaction. Sign-out waits for confirmed saves and stops if a save fails. This prevents deliberate sign-out from silently discarding pending changes.

Revision conflicts remain protected. If another tab/device has newer data, the queue preserves pending local work, offers a backup, and does not retry into a blind overwrite. After downloading the backup, reload to view the saved version. Existing snapshot/revision checks remain in place. Network failures and missing-row/duplicate-insert revision conflicts now have separate handling.

Clearing study data explicitly pauses and drains the queue before deletion. After successful clearing, the queue resets to empty rather than recreating deleted state. If clearing fails, the queue resumes. Unmounting or changing accounts stops queued writes and notifications for the old session; already-sent requests cannot be recalled.

Limits: unsaved changes remain in memory until saved or downloaded. There is no new automatic browser-storage cache or backup-import UI. A crash, force-close, or ignoring the browser warning can still lose pending work. A response lost after a successful server write can produce a revision conflict on retry; preserving/exporting both versions is safer than forcing an overwrite.

Validation: deterministic regression tests cover failed final saves, retrying identical data, keeping the newest pending edits, serial writes, reverting during an in-flight write, lost-response ambiguity, revision conflicts, pause/reset, resuming after failed clear, stopped sessions and snapshot cloning. Cloud-store integration tests cover transient retry without advancing the revision and concurrent initial insert conflicts. Existing account data was not changed and no live outage was induced. The full suite and production build are run before deployment. Browser control was unavailable in this session.
