# Clariqo review after fixes 1–4

Date: 31 October 2026 (India). Live site: https://clariqo.vercel.app/

Reviewed source and confirmed READY production deployment: `12186b4`. This pass is a review, not a new application deployment. No existing accounts, files, progress, emails or saved plans were changed. No test accounts were created. Application code is unchanged.

## Fresh results

| Check | Result | Evidence |
| --- | --- | --- |
| Automated regression | 127/127 pass | `test_results/review-current-tests.log` |
| Production build, including TypeScript | Pass | `test_results/review-current-build.log` |
| Public site/auth/asset/API guard checks | 22/22 pass | `test_results/purple-theme-release-live.json` |
| Section bookmarks and login redirects | 18/18 pass | `test_results/navigation-release-live.json` |
| Known production dependency advisories | Zero reported | `test_results/review-current-dependencies.json` |
| Live synthetic AI features | 9 pass, 1 quota-blocked | `test_results/final-purple-feature-live.json` |
| Targeted edge-case reproductions | Remaining issues reproduced | `test_results/review-current/edge-cases.json` |
| Signed-in desktop/mobile browser review | Not available | Browser inventory reports local browser use disabled in Work settings |

The nine live AI passes cover general chat, a PDF answer, PDF-only refusal, conversational follow-up, a five-question quiz with grading, a two-day plan, internet search with executed sources, PDF flashcards and general flashcards. PDF mind-map generation received a Groq usage-limit response. Further AI calls stopped after that response. These calls exercised current service functions with the local configured Groq key and synthetic notes, not an authenticated production browser request. The successful internet check establishes search/source plumbing, not factual agreement for every statement.

## Review of the four fixes

1. **Subject-scoped study-plan priorities:** regression checks still pass. Only the selected PDF’s recorded quiz results, or matching general subject labels, contribute. Old records without PDF identity cannot safely inform a PDF-specific plan. Overall progress intentionally still aggregates subjects.
2. **Failed-save recovery:** serial queue, identical-state retry, pending-edit coalescing, lost-response ambiguity, conflict handling and backup controls remain in place. Tests pass. Pending state is memory-only until saved/downloaded; force-closing can still lose it. There is no backup-import UI. Real outage/recovery clicks were not repeated.
3. **Section URLs:** all eight live bookmarks preserve the login destination. Navigation parsing, duplicate-entry avoidance and safe return-target tests pass. Real signed-in Back/Forward and refresh clicks remain unverified because browser control is disabled. Full refresh preserves the section and saved data, not unsaved form input/unsubmitted quiz state.
4. **PDF citations:** selected excerpt indexes, page validation, de-duplication, refusal/fallback, persistence and legacy labelling tests pass. Live synthetic PDF chat also passes in the broader AI harness. Valid source identity does not prove claim-level support. Nonstandard legacy citation syntax remains a display gap below.

## Remaining findings, in priority order

### R1. PDF removal can leave a broken library entry

Priority: medium. Reproduced with an isolated fake client in `web/tests/manual/review-current-edges.ts`.

`web/lib/cloud-storage.ts:52–59` deletes Storage bytes first and database metadata second. When bytes are removed successfully but the metadata request fails, the function throws while the library row remains. Reload can then show an entry whose file is missing. Fix with a recoverable deletion state/reconciliation strategy. Simply reversing deletion order would trade this for orphaned bytes and is not sufficient on its own.

### R2. Plans stop at 14 days, and general tips belong to the last day

Priority: medium/minor. Deterministically reproduced.

A 61-day exam interval yields 14 days. The form does disclose “Up to 14 days,” so this is a stated limitation rather than the older silent-limit bug. Nevertheless a generated “Final Review” on day 14 may imply a schedule reaches the exam when it does not. Add explicit coverage dates/continuation or support the whole interval.

`web/lib/domain.ts:50–54` slices final-day content to the end of the Markdown, including `### Exam tips`. Separate general tips from daily tasks. Task durations are requested in the prompt but their sum is not checked against the selected hours.

### R3. Some legacy citation formats remain raw

Priority: low, within the earlier citation display problem. Reproduced locally.

`pdfCitationText('Claim 【notes.pdf | pages 1-2】')` retains the page-range marker. Bare `[1]` indexes also remain unchanged. Standard single-page wrappers are handled, while arbitrary variants cannot reliably be inferred. Extend supported syntax without treating guessed pages as verified references. Keep the old-answer warning and distinguish unknown references from valid ones.

### R4. AI availability is constrained by shared Groq quota

Operational limitation, observed this pass.

Nine feature calls passed; PDF mind-map generation then hit the provider usage limit. The error is surfaced honestly and no placeholder map is saved. This does not establish a permanent outage or identify which exact token/request bucket was exhausted. Improve retry guidance/backoff and quota visibility. The app’s in-memory per-process rate limiter is not a global spending/quota cap across serverless instances.

### R5. Factual accuracy still needs a separate benchmark

Product risk, not a newly reproduced factual failure in this pass.

Quiz shape validation checks counts/options/keys, not historical facts. Source indexes check page identity, not whether each claim follows from the passage. The earlier reviewer’s French Revolution and latest-version/source contradiction reports are not resolved by these structural fixes. Use repeatable subject fixtures and independently checked answer keys/claim-source comparisons.

## Feature-level boundaries

- **Login/signup/reset:** live views and invalid-link/auth guards passed. Inbox delivery, confirmation, password changes and sign-out clicks were not repeated.
- **PDF upload/reuse/preview/download:** ownership and upload-failure regressions pass; limits remain 20 MiB/file, five PDFs/50 MiB library, 200 pages and 300,000 text characters. This pass did not run a new browser PDF worker, preview or download flow. No OCR.
- **Chat and internet:** live synthetic responses passed; full-page rendering, maths appearance and source-button navigation are browser-unverified.
- **Quizzes/progress:** live generation and deterministic grading passed. No current factual correctness certification.
- **Plans:** short-plan generation passes; R2 remains.
- **Flashcards:** PDF and general generation passed; save-data validation and review-state regressions pass. No new live account save, export or deletion clicks.
- **Mind maps:** tree/reference validators pass. Live generation blocked by quota; no new expand/collapse/export browser test.
- **Security:** public auth/cross-origin guards and dependency advisory checks pass. No fresh real two-account isolation test because user declined creating disposable accounts. Zero advisories is not a guarantee of security.
- **UI/accessibility/mobile:** purple CSS is served, but no current visual inspection, keyboard/focus/overflow or touch assessment was possible.

## Recommended next work

Fix R1 (recoverable PDF deletion), then R2 (plan horizon and tip separation). Address R3 legacy formatting afterward. Recheck mind-map generation only when allowance recovers. Complete authenticated browser verification before final launch sign-off.

The site is deployable and the tested paths pass. This review cannot honestly label every feature bug-free or fully tested while signed-in browser access and the live mind-map check remain unavailable.
