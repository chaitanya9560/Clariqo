# Clariqo website test — 31 October 2026

Tested production: https://clariqo.vercel.app, commit `f2826a6`.

Scope: user requested no temporary accounts. No production accounts, study records, or email messages were created, changed, or deleted. Browser control reported disabled in Work settings. This is a code/service audit, not a complete browser end-to-end certification.

## Results

| Check | Result | Evidence / boundary |
| --- | --- | --- |
| Automated regression suite | PASS — 66 tests | Includes chat routing, grading, dates, math rendering, request validation, auth guards, local persistence, cloud-storage failure handling, download ownership, revision conflicts and 20 MiB upload rejection. Cloud-storage tests use a fake client and do not replace real two-account RLS testing. |
| TypeScript | PASS | `npm --prefix web run typecheck` |
| Production build | PASS | `npm --prefix web run build` with local ignored configuration |
| Production dependencies | PASS | npm audit reported zero known production vulnerabilities; this does not guarantee absence of vulnerabilities. |
| Live public site | PASS — 24 checks | Login/signup/reset HTML, protected routes, private cache headers, configured API, missing/forged credentials, cross-origin rejection, invalid confirmation/callback links, 404 response, public JS availability and token-pattern scan, deployment READY. No authenticated browser session used. |
| Live AI general chat | PASS | “what is oops” with saved-material flag and no matching excerpts |
| Live PDF-context answer | PASS | Synthetic Java notes, encapsulation answer and supplied page reference |
| Live PDF-only refusal | PASS | Unrelated question not presented as a PDF answer |
| Live conversational follow-up | PASS | Synthetic encapsulation conversation |
| Live quiz | PASS | Five unique validated questions; grading, accuracy and weak-topic calculation |
| Live study plan | PASS | Two separate days and exam tips from synthetic notes |
| Internet search | INCOMPLETE | Initial strict source-verification assertion failed. The harness initially required HTTPS-only sources although the app accepts safe HTTP/HTTPS; that harness condition is corrected locally. The diagnostic retry hit the provider usage limit. These observations do not establish the original failure's exact cause. Search is not certified working in this pass. No further AI requests made after the quota response. |
| PDF extraction | PASS — 3 fixtures | Installed PDF.js legacy Node parser: text fixture yielded 106 characters, blank fixture yielded zero, corrupt bytes rejected. Browser worker startup, upload, preview and download clicks are not covered by this parser check. |
| Anonymous study-table access | PASS | Public-key requests to both study tables denied. No existing users' study data was read. |
| Supabase security advisors | ONE WARNING | Leaked-password protection is disabled. Supabase documents this feature as Pro-plan-and-above. No plan upgrade was made. |

## Not verified in this pass

- Real email delivery, signup, sign-in/out, password changes, account refresh, or cross-device cloud persistence through browser interactions.
- Live two-account isolation and upload/replacement/deletion; user declined creating test accounts. Existing accounts were not used.
- Mobile/desktop visual layout, focus flow, real PDF browser worker, preview navigation, download clicks, and third-party autofill-extension behavior.
- Sustained load, quota exhaustion timing, or long-duration reliability. AI calls consume shared Groq allowance and can hit provider limits before the request-count ceiling.

## Remaining work

1. Recheck Internet mode once Groq allowance is available; capture the returned origin, tool metadata and safe source URLs before drawing a conclusion.
2. Complete signed-in browser testing using a user-controlled session when browser access is enabled.
3. Verify inbox delivery with a user-initiated signup/reset request.

The test files and this report are included in the repository. No application code was changed by this audit.

References: https://supabase.com/docs/guides/auth/password-security

Detailed machine outputs are in ignored `test_results/full-*` files. They are intentionally not published with the repository.
