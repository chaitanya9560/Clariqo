# Vercel branch verification

Checked locally on 30 October 2026, using Node 24.

| Check | Result |
| --- | --- |
| Strict TypeScript check | Passed |
| Next.js production build | Passed |
| Build using only staged source files and the installed Node dependencies | Passed |
| Automated web tests | 46 passed |
| Production dependency audit | 0 reported vulnerabilities at the time of the check |
| Staged source and browser bundle scan for the configured API key | No matches |
| Real Groq conversation | Passed |
| Real PDF-context answer using synthetic study text | Passed with scoped page references |
| Real five-question quiz | Passed |
| Real structured two-day study plan | Passed |
| Real internet search | Passed with returned source URLs |
| PDF worker served by the production build | Passed |

The tests cover local text-retrieval scope, quiz grading, weighted progress, plan dates and day validation, math rendering, blocked raw HTML/javascript links, bounded requests, provider errors, optional demo-code checks, rate-limit behavior and IndexedDB save/restore/delete.

## What still needs checking

Browser control was disabled in the available environment, so a visual click-through and actual browser PDF extraction were not verified. Serving the worker successfully does not establish that every PDF will parse correctly. Test one selectable-text PDF in a browser before presenting the demo.

The app has not been deployed to a Vercel account as part of these checks. After deployment, verify the hosted URL, environment variables and browser storage behavior on that origin. A passing local build is not proof of hosted availability.

The live checks used synthetic material. Provider availability, quotas and correctness of future AI answers are not guaranteed.
