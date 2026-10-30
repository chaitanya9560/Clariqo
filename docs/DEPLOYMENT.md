# Deploy Clariqo on Vercel

This guide is for `vercel-migration`. The earlier Streamlit deployment remains documented on the repository's `main` branch.

| Setting | Value |
| --- | --- |
| Repository | `chaitanya9560/Clariqo` |
| Branch to deploy | `vercel-migration` |
| Root Directory | `web` |
| Framework | Next.js |
| Install | `npm ci` |
| Build | `npm run build` |
| Output | `.next` |

Set these **server-only** environment variables in Vercel:

```dotenv
GROQ_API_KEY=your-own-groq-key
GROQ_MODEL=openai/gpt-oss-120b
```

Optionally add `DEMO_ACCESS_CODE` for a controlled demo. Never prefix the API key with `NEXT_PUBLIC_`.

Import the repository into Vercel, select the `web` root and deploy `vercel-migration`. If the initial import uses `main`, set the intended branch in the project's Git configuration or explicitly deploy from `vercel-migration`. The `web` app is not present on `main`.

After deployment, open the returned URL and test a text PDF, chat, a quiz and a plan in a browser. PDFs stay in browser storage; there are no student accounts or cross-device synchronization. The hosted URL is not verified until the deployment succeeds.

For setup, limits, privacy and troubleshooting, read [the full web guide](../web/README.md). For the checks already performed, see [verification notes](VERCEL_VERIFICATION.md).
