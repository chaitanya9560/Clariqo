# Bookmarkable study sections

Each study section now has a distinct URL:

| Section | URL |
| --- | --- |
| Dashboard | `/` |
| Study Materials | `/?page=materials` |
| Ask AI | `/?page=chat` |
| Quiz | `/?page=quiz` |
| Flashcards | `/?page=flashcards` |
| Mind Maps | `/?page=mind-maps` |
| My Progress | `/?page=progress` |
| Study Plan | `/?page=study-plan` |

The rendered section derives from Next.js `useSearchParams`, rather than a component variable that always starts at Dashboard. Section changes use native `history.pushState` through the installed Next.js App Router's history integration. The router updates search parameters and handles Back/Forward while preserving the mounted study component, its pending save queue, selected material and in-session quiz state. Clicking the current section does not create another history entry.

Refreshing or opening a bookmark selects that section after authentication. A signed-out visitor first receives a login URL with an allowlisted `next` destination. Successful password sign-in returns there. External URLs, arbitrary internal endpoints and malformed return targets fall back to Dashboard. Email-confirmation/password-reset callbacks keep their existing destinations.

This preserves the current section, not every unsaved form value. Saved study data still loads from the account after a full refresh. Unsubmitted quizzes and form inputs remain in-session state and may reset on refresh. The failed-save warning and backup controls remain in place. No existing account data is changed by navigation.

Validation: six navigation regression tests cover unique section URLs and refresh parsing, invalid/duplicate parameters, avoiding duplicate history entries, URL interpretation during history traversal, login return targets and open-redirect rejection. The full 109-test regression suite, TypeScript check and production build run before deployment. Installed Next.js App Router source explicitly integrates native history changes with `useSearchParams` and its popstate handler. Browser automation is disabled in Work settings, so real signed-in Back/Forward clicks and refresh were not repeated. Live signed-out section redirects are checked after deployment.
