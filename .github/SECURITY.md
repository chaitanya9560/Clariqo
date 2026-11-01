# Reporting a security issue

Never include API keys, personal PDFs, saved chat history or other private data in a public issue or pull request.

If the repository's Security tab offers private vulnerability reporting, use that option. Otherwise, report only that a sensitive issue exists and request a private contact route before sharing details. Do not publish an exploit or credentials in that initial message.

If an API key is exposed, revoke it through the provider and replace it locally. Removing the key from the latest file alone does not remove it from Git history.

The current Next.js website requires account sign-in and uses owner-scoped cloud records and private file storage. Relevant excerpts and prompts go to the server and Groq for AI requests. See the README for current data handling and limits.

Serverless rate limits are best-effort. The optional shared `DEMO_ACCESS_CODE` is an additional control for demos, not a replacement for account authentication. There is no guaranteed response time or formal supported-release policy.
