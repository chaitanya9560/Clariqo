# Clariqo final feature audit — 31 October 2026

Production: https://clariqo.vercel.app/

Tested source: `0410bad` on `vercel-migration`. Vercel reports READY for this commit. GitHub was fetched and no newer commits appeared on the production branch. The working tree initially contained no pending feature changes. This audit adds a manual test harness and this report; application code was not changed.

## Result

The production site serves the original purple theme. Automated regression, TypeScript, production compilation and public-service checks pass. The site is **not certified bug-free or fully browser-tested**. Two live AI checks hit provider quota, and signed-in browser automation could not run because the tool repeatedly reported “Local browser use is disabled in Work settings,” including after the user said access was enabled.

| Verification | Result | Evidence |
| --- | --- | --- |
| Automated regression | 82/82 pass | `test_results/final-purple-tests.log` |
| TypeScript | Pass | `test_results/final-purple-typecheck.log` |
| Production build | Pass | `test_results/final-purple-build.log` |
| Live public-service checks | 22/22 pass | `test_results/purple-theme-release-live.json` |
| Production dependency audit | Zero reported advisories | `test_results/final-purple-dependencies.json`; not a guarantee of security |
| Live AI feature checks | 8 passed, 2 quota-blocked | `test_results/final-purple-feature-live.json` |
| Signed-in browser test | Blocked | Browser tool reported disabled twice in this turn |

The live AI calls used the configured local Groq key, current service functions and synthetic Java excerpts. They did not pass through the deployed authenticated browser route, so they do not prove browser-to-production integration. No test accounts, emails, uploads or saved production records were created, altered or deleted. No credentials were printed. Test calls consumed a small amount of the shared provider allowance. Further live AI retries were stopped after the harness finished with quota errors.

## Feature coverage

| Feature | What passed | Remaining boundary |
| --- | --- | --- |
| Login, create account and password-reset views | Live HTML, configured state, private/no-store caching, invalid verification-link handling | Real inbox delivery, email confirmation, password changes and sign-in/out clicks not repeated |
| Private account access | Signed-out homepage redirects; chat/cards/maps deny anonymous calls; cross-origin call denied; regression auth guards | No fresh two-account RLS or cross-device test; user previously declined test accounts |
| Dashboard | Source review confirms purple hero, activity counts and links, including flashcards/maps | Current signed-in rendering and mobile layout not visually inspected in this audit |
| PDF library | Regression checks cover owner-path validation, same-ID replacement, failed upload/metadata-save recovery and private downloads | Real browser upload, PDF worker, preview, source-page navigation, download and removal not repeated |
| Upload limits | Code review: 20 MiB/file, 200 pages, 300,000 extracted characters, five PDFs/50 MiB account library | Scanned PDFs have no OCR. Browser rejection paths were not clicked in this pass |
| General chat | Live OOP answer passes even with saved-material flag and no matching passage | No broad factual benchmark |
| PDF-only answers | Live synthetic encapsulation answer and page reference pass; unrelated question refused | Short synthetic excerpts, not a full textbook extraction |
| Follow-up conversation | Live encapsulation follow-up retains subject | Long conversations not stress-tested |
| Internet mode | Live executed search returns sources with safe HTTP/HTTPS URLs | This proves source plumbing, not that every factual claim agrees with each source |
| Quizzes | Live five-question PDF quiz validates; all-correct and unanswered grading, accuracy and weak-topic checks pass | General-topic facts not independently verified; no guarantee that generated answer keys are factually correct |
| Progress | Regression weighted accuracy and weak-subtopic calculations pass | Subject scoping issue below |
| Study plans | Live two-day plan has tasks and tips; date/count validation passes | Longer horizon, task-duration totals and subject relevance not fully validated |
| General flashcards | Live five-card generation passes with no invented PDF references | Browser reveal/rating/export/cloud-save flow not repeated in this turn |
| PDF flashcards | Count/reference/persistence validators pass in automated tests | Fresh live generation hit Groq usage limit; not marked passed |
| Mind maps | Automated root, depth, parent, cycle, reference and persistence validation pass | Fresh live PDF generation hit Groq usage limit; not marked passed |
| Markdown and maths | Existing regression tests pass; safe Markdown renderer reviewed | No new browser rendering screenshot |
| Rate limit and provider errors | Regression bounds and provider-error handling pass; real quota error surfaced | In-memory rate limiter is per server instance, not a global free-tier cost cap |
| Mobile navigation | Escape and outside-click handling retained in source | Browser unavailable, so touch layout, focus and overflow remain unverified |

## Issues still present

### 1. Study plans can receive weak topics from an unrelated subject

Priority: high. Confirmed by deterministic code check and request construction, not by a new generated History plan.

`progress()` aggregates all quiz concepts. `StudyApp.tsx:95` sends `stats.weak` directly to `makePlan` without filtering by the requested subject or selected PDF. A synthetic Biology result returned `Photosynthesis` as a weak topic; the same list would enter a later History plan request. Group results by subject/material and filter before generation.

### 2. A failed cloud save has no automatic retry of the pending state

Priority: high. Source-review finding; a production outage was not induced.

`StudyApp.tsx:42` assigns the snapshot to `lastSaved.current` before `storeLearning` succeeds. If the final save fails, the unchanged state is treated as already saved, and reloading as suggested can discard the unsaved local change. Keep pending state separate from confirmed state and provide retry/recovery. The existing storage test suite checks failure handling, but not this React-effect recovery behavior.

### 3. Section navigation does not survive refresh or support bookmarks

Priority: medium. Confirmed in source.

`StudyApp.tsx:28,53` stores the current page only in React state. Every section uses `/`, refresh starts at Dashboard, and browser Back does not traverse sections. Add URL-backed navigation.

### 4. PDF citation quality still depends on the model

Priority: medium. Confirmed source behavior; raw marker output was not reproduced in the current live sample.

The chat prompt asks for file/page citations, but returned body citations are not validated or converted into dedicated source UI. The separate source chips contain all retrieved pages, not only passages actually used by the answer. Raw file/page strings can remain, and displayed references do not certify claim support. Validate/map citations and distinguish retrieved material from evidence actually cited.

### 5. Plans have a 14-day horizon and exam tips appear inside the last day

Priority: medium/minor. Deterministically reproduced.

A 61-day exam interval returns 14 plan days. The current form now discloses “Up to 14 days,” so the earlier report that there is no warning is outdated. Longer-term scheduling is still unsupported. `parsePlan()` includes the trailing `### Exam tips` section in the final day's content. Separate tips from the day array so completing the last day does not also represent completing the general advice.

### 6. A PDF deletion can partially succeed

Priority: medium. Source-review failure scenario, not exercised against real data.

`cloud-storage.ts:49–55` removes Storage bytes before deleting the metadata record. If Storage removal succeeds and the database deletion fails, the PDF row remains while its file is gone. The existing test covers Storage deletion failing first, not the reverse partial failure. Use recoverable deletion state or explicit reconciliation.

### 7. Shared Groq allowance can block core features

Operational limitation, observed live.

PDF flashcard and mind-map calls received the provider usage-limit message. A later general-card call passed, so this audit does not establish a permanent account-wide outage or the exact token/request quota that was exceeded. Add clear retry guidance and quota-aware behavior. No paid upgrade or billing change was made.

### 8. AI factual correctness remains unproven

Product risk. This pass checks a narrow Java example and structural validity. It does not resolve the earlier reviewer’s French Revolution facts or latest-version/source contradiction reports. Those need repeatable factual fixtures and claim/source checks before claiming reliable academic accuracy.

## Before final sign-off

1. Complete signed-in desktop/mobile browser testing once the tool can access the browser. Include material upload/reuse/preview/download, all answer modes, quiz submission, progress, plan completion, flashcard review/export and map expand/collapse/export.
2. Recheck PDF cards and maps after Groq allowance recovers. Avoid repeated requests while limited.
3. Fix subject filtering and failed-save recovery first. Then address navigation and citation handling.
4. Test deletion and account isolation only with explicit disposable-data authorization. Do not use real student files for destructive tests.

All results above describe this specific commit and pass, not every possible input or future deployment.
