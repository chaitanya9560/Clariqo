# Study desk UI

Developed on `feature/study-desk-ui`; released through `vercel-migration`.

The visual direction uses warm paper surfaces, charcoal text, a forest green accent, serif headings and simple document rows. It avoids gradients, floating decorations, repeated sparkle icons and oversized marketing panels.

## Changes

- Dashboard shows actual saved documents, the currently selected or newest uploaded PDF, upcoming incomplete plan days, weak topics from stored quiz results and account totals.
- New users get empty states rather than sample activity or invented study history. No reading position or last-opened date is claimed because the app does not track them.
- A dashboard question box opens a draft in chat; the student reviews it and sends it there.
- Login, password reset, PDF library, chat, quizzes, progress and plans share colors, type sizes, field styling and spacing.
- Small PDF sizes are shown in KB; page and dashboard-session counts handle singular/plural.
- Mobile navigation closes on Escape or an outside tap. The menu toggle exposes its expanded state.
- Inputs and primary actions have larger mobile targets; reduced-motion preferences are respected.

## Validation

- 66 automated tests pass; TypeScript and the production build pass.
- Browser visual review: dashboard with synthetic data and an empty dashboard, at desktop and a 390-pixel viewport; real local login/signup views at desktop/mobile.
- Browser interaction review: signup/sign-in/reset mode switching and password visibility toggle. No credentials entered, emails sent, or accounts created.
- Dashboard visual review uses static markup generated from the actual StudyDesk component with synthetic fixtures; it is not a signed-in end-to-end session. Other authenticated screens share the stylesheet but have not had browser click-through checks on this branch.

This UI change does not fix or certify quiz factual accuracy, web-source consistency, subject-scoping of plan weak topics, section URLs, raw AI citations, or the 14-day plan limit reported in the separate review. Those need their own behavior changes and tests.
