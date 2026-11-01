# Final source handoff

Date: 1 November 2026 (India).

The final Next.js website is being merged from `vercel-migration` to `main`. Vercel root directory stays `web`; the site does not use the earlier Python/Streamlit runtime.

## Checks for this handoff

- 127 automated tests passed.
- TypeScript passed.
- Git whitespace checks passed.
- No application behavior was changed by the source cleanup.
- Build, live-service and browser checks from earlier reviews were not repeated for this source-only handoff.

## Cleanup

Removed the old Python source, its tests, requirements, runtime and caches. Kept the Next.js application, its tests, lockfile, example settings, database migration and documentation. Personal PDFs, legacy local study records and old audit outputs were moved to a private local archive outside the repository. The presentation and source ZIP are local deliverables and are not part of the application repository.

Private environment files, installed packages, generated builds, audit outputs and the archive must stay out of Git. Set the real environment values in local or hosting settings; only `web/.env.example` belongs in source control.

## Running and deploying

From `web/`, install with `npm ci`, copy `.env.example` to `.env.local`, fill the settings and run `npm run dev`. For Vercel, use branch `main` and root directory `web`. Existing deployments tracking `vercel-migration` can continue working; production-branch selection is a separate hosting setting.

The [last full review](WEBSITE_REVIEW_AFTER_FOUR_FIXES_2026-10-31.md) lists remaining issues and testing limits. Merging the source does not mean every AI answer is factually correct or every signed-in flow has been retested.
