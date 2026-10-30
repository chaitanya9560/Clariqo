# Reporting a security issue

Never include API keys, personal PDFs, saved chat history or other private data in a public issue or pull request.

If the repository's Security tab offers private vulnerability reporting, use that option. Otherwise, report only that a sensitive issue exists and request a private contact route before sharing details. Do not publish an exploit or credentials in that initial message.

If an API key is exposed, revoke it through the provider and replace it locally. Removing the key from the latest file alone does not remove it from Git history.

Clariqo has a local saved-profile mode and a cloud demo mode with isolated temporary browser workspaces. Authentication, durable student accounts and production deployment security are not implemented. See the README for data handling and current limits. There is no guaranteed response time or formal supported-release policy at this stage.

On `vercel-migration`, the deployed app stores study data in IndexedDB on the visitor's device. Users sharing a browser profile share that data. Relevant excerpts and prompts go to the server and Groq for AI requests. Serverless rate limits are best-effort; a shared `DEMO_ACCESS_CODE` is available for controlled demos, not student authentication.
