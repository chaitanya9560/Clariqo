# Clariqo for Vercel

A working Next.js study app, not a landing page. This version lives in `web/` on the `vercel-migration` branch. The original Streamlit app remains on `main`.

## Run locally

Use Node.js 22 or 24 (the build was checked locally on Node 24):

```sh
cd web
npm ci
cp .env.example .env.local
```

Edit `.env.local` and set your own `GROQ_API_KEY`. Then:

```sh
npm run dev
```

Open http://localhost:3000. For a production run, use `npm run build` then `npm start`.

## Deploy on Vercel

1. Import `chaitanya9560/Clariqo` from GitHub.
2. Deploy the **`vercel-migration`** branch. If the importer starts from `main`, change the project's production branch or explicitly create a deployment from `vercel-migration` before deploying this app.
3. Set **Root Directory** to **`web`**. Framework preset: **Next.js**.
4. Add server environment variables:

   ```dotenv
   GROQ_API_KEY=your-own-groq-key
   GROQ_MODEL=openai/gpt-oss-120b
   ```

5. Optionally set `DEMO_ACCESS_CODE` to a private demo code to require it for AI requests. Visitors enter that code in the app; they never receive the Groq key.
6. Leave the standard install/build/output settings: `npm ci`, `npm run build`, `.next`.
7. Deploy. After adding or changing environment variables, redeploy for them to take effect.

Never use `NEXT_PUBLIC_GROQ_API_KEY`, upload `.env.local` or publish the key in an issue. A Vercel preview with deployment protection may require sign-in; use the appropriate public production URL when sharing your demo.

Vercel Hobby and the provider's free access have usage limits. This app does not enable paid billing. In-memory rate limits are best-effort and reset across serverless instances; use `DEMO_ACCESS_CODE` for a controlled demo. A public URL is not a promise of unlimited usage.

## What changed from Streamlit?

| Area | This Vercel branch |
| --- | --- |
| Interface | React / Next.js App Router |
| Server | Stateless Node.js route at `/api/study` |
| PDF extraction | PDF.js runs in the browser |
| PDF search | Browser-local BM25-style text matching; no FAISS or embeddings |
| Saved data | IndexedDB in each browser, including PDF bytes, chat, quiz scores and the current plan |
| AI provider | Groq, with the key used only by the server |
| PDF size | Up to 20 MB; only bounded text excerpts enter the API |
| Accounts | None. Data is per browser profile, not synchronized across devices |

The PDF never crosses Vercel's function request-body limit: the original file stays in the browser, and JSON requests are bounded to 64 KB. Text context is capped at 12,000 characters. Retrieval is lexical, so paraphrases and equations can miss relevant passages. Selected source references show the supplied context pages, not independently verified proof of the generated claims.

## Features

- Dashboard with saved-material, question and quiz metrics.
- Five-PDF library with preview, download, safe same-name replacement and removal.
- Chat with PDF-first, PDF-only and internet-search modes, Markdown and KaTeX math.
- Five- or ten-question quizzes with difficulty, answer review and saved subtopic performance.
- Progress from actual quiz answers, weighted by question count.
- Plans up to 14 days, based on exam date, available time, level, weak topics and optional material excerpts.
- Persisted plan checkboxes and Markdown plan download.

Internet answers require executed search tools and returned URLs. When the configured model or account cannot provide search, the app reports that limitation. It does not fabricate online search success.

## Storage and limits

- Browser storage is shared by people using the same browser profile. There are no student logins.
- Clearing browser/site data removes the library and learning history. Private browsing and storage quotas may prevent persistence.
- Five PDFs / 50 MB total; 20 MB, 200 pages and 300,000 extracted text characters per PDF. No OCR.
- Chat keeps the most recent 100 messages; quiz history keeps the most recent 100 results.
- AI context uses recent conversation and selected excerpts, not an entire library. Plan material is sampled and labelled partial.
- Active unsubmitted quizzes and form choices are not restored after refresh.
- AI can make mistakes. Plans do not automatically rebuild after a quiz.
- Browser storage does not make AI offline: relevant text and prompts go to Groq. Web-enabled calls receive only the current question, without PDF excerpts or chat history.
- The endpoint accepts at most 30 requests per ten minutes per observed IP per running instance. This is not a durable abuse-prevention system, and network address headers must be supplied by a trusted host.

## Checks

```sh
npm run typecheck
npm test
npm run build
```

Tests cover retrieval scope, grading, persistence, dates, malformed generation, provider errors, request bounds, origin checks and the optional demo code. They use mocked AI responses. Live provider checks and browser checks are separate verification steps; passing unit tests is not a guarantee of deployment or answer accuracy.

Official hosting references:

- https://vercel.com/docs/monorepos
- https://vercel.com/docs/functions/limitations
- https://nextjs.org/docs/app/api-reference/file-conventions/route
