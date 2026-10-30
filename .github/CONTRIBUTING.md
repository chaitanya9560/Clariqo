# Contributing to Clariqo

Clariqo is a local study-assistant prototype. Small fixes, clear bug reports and improvements to the documentation are welcome. Check the README's upstream licensing note before reusing or redistributing the code.

## Before making a change

1. Read the README and set up the project locally.
2. Check existing issues before opening a new one.
3. Explain the problem and the expected result. Keep each change focused.

## Local checks

Run from the project root:

```sh
python -m unittest discover -s tests -v
```

For interface changes, also check the affected page in the browser. Describe what you checked and include a screenshot with private information removed when useful.

## Pull requests

- Explain the problem, the change and how you checked it.
- Add a regression test for a meaningful behavior change when practical.
- Update documentation if setup or behavior changes.
- Keep tests and fixtures under `tests/`; use synthetic study material.
- Never commit API keys, `.env`, personal PDFs, saved learning data, caches or generated test reports.

The offline test suite uses mocked AI calls. A passing suite does not confirm live provider access or factual answer quality. Do not send someone else's study material to an external provider without their permission.
