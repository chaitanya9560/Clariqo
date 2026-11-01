# Deploy Clariqo on Vercel

This guide is for the final Next.js website on `main`. The earlier Streamlit prototype is preserved in Git history.

| Setting | Value |
| --- | --- |
| Repository | `chaitanya9560/Clariqo` |
| Branch to deploy | `main` |
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

Import the repository into Vercel, select the `web` root and deploy `main`. For an existing Vercel project, select `main` as its production branch to follow the final project.

Set the browser-safe Supabase configuration from `web/.env.example` as well, following [email login setup](EMAIL_LOGIN.md). After deployment, test sign-in, a text PDF, chat, a quiz and a plan in a browser. PDFs and learning data are private to the signed-in account. New deployments still need their own checks.

For setup, limits, privacy and troubleshooting, read [the full web guide](../web/README.md). For the checks already performed, see [verification notes](VERCEL_VERIFICATION.md).
