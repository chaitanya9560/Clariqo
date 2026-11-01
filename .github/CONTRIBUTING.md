# Contributing to Clariqo

The Next.js application is under `web/`. Read the README and the upstream credit before making changes.

## Local checks

Run from `web/`:

```sh
npm ci
npm run typecheck
npm test
npm run build
```

For UI changes, check the affected screen on desktop and mobile. Use synthetic study material and remove private information from screenshots.

## Pull requests

- Explain the problem, the change and how you checked it.
- Add a regression test for a meaningful behavior change when practical.
- Update documentation when setup or behavior changes.
- Keep automated tests under `web/tests/` and manual checks under `web/tests/manual/`.
- Never commit API keys, `.env` files, personal PDFs, saved learning data, caches or generated reports.
- Keep server secrets out of client components; never use `NEXT_PUBLIC_` for secret API keys.

Offline tests use mocked AI calls. Passing tests does not prove live provider access or factual answer quality. Do not send someone else's study material to an external provider without permission.
