# Deploy the public Clariqo demo

## Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud with the GitHub account that owns this repository.
2. Create an app using these fields:

| Field | Value |
| --- | --- |
| Repository | `chaitanya9560/Clariqo` |
| Branch | `main` |
| Main file path | `cloud/app.py` |
| Python version in Advanced settings | `3.11` |

3. In **Advanced settings → Secrets**, enter the following as TOML, replacing the placeholder with your key **in the hosting dashboard only**:

```toml
AI_PROVIDER = "groq"
GROQ_API_KEY = "your-own-key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Top-level Streamlit secrets are made available as environment variables. Do not commit a real secrets file. The cloud dependency file supports the Groq setup; it does not install the optional Gemini client.

4. Deploy and wait for the dependency installation and first model download. The app may need an initial warm-up.
5. Use two separate browsers or an incognito window to verify visitor isolation: upload a synthetic PDF in one session and check it does not appear in the other. Ask a PDF question, submit a quiz and create a plan in each session.

## What is shared?

The server shares its embedding model and configured Groq account. Uploaded documents, FAISS index and learning state are held in a separate server-generated temporary workspace per Streamlit session. Visitors cannot choose a workspace identifier through a URL or upload name.

There are no logins. Do not describe the temporary workspace as a durable student account. Reconnecting is not guaranteed to recover it; a new session or restart can reset it. Temporary files are removed when their workspace object is released or the server's temporary storage is cleared. Immediate cleanup at browser close is not guaranteed.

## Resource limits

- 20 MB per PDF; at most 5 PDFs / 50 MB combined per session.
- Up to 200 pages and 300,000 extracted text characters per PDF.
- 60 AI API calls per hour per session, including routing calls. These limits reset with a new session and do not prevent determined abuse.
- Provider quotas are shared across visitors. CPU and memory limits on the free host can also affect availability. No guaranteed capacity is claimed.

## Verification boundary

The local automated suite checks local behavior, separate-session state, overlapping requests and failure recovery using mocked embeddings and AI responses. The Linux CPU dependency file requires verification on the actual host. A successful local test does not establish deployment success.

After deployment, verify the actual hosted link and logs. Do not publish a guessed URL as a working app. This code does not enable paid billing.

Official reference: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
