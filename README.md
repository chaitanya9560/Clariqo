# Clariqo

Clariqo is a local study assistant built with Streamlit. It combines saved study PDFs, Groq chat, practice quizzes, study plans and progress tracking.

## Features

- Upload selectable-text PDFs up to 20 MB, then select, preview and download them from the saved library.
- Chat normally, ask PDF-based questions with page references, or request an internet search. PDF-only mode keeps answers within uploaded material.
- Generate 5- or 10-question quizzes with a selected difficulty and PDF source, and review answers and weak areas.
- Generate a daily exam plan from one PDF, all saved PDFs, or general subject knowledge. Plans contain up to 14 days and can be downloaded as Markdown.
- Save chat, the current plan, completed study days and quiz results locally. These return after reopening the app.

## Local setup

The tested environment is Python 3.11 on an Intel Mac.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-local-mac.lock.txt
cp .env.example .env
```

Edit `.env` locally and supply your own key:

```dotenv
AI_PROVIDER=groq
GROQ_API_KEY=paste_your_groq_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Do not commit the real `.env` file. The app uses your configured account and its API limits; it does not enable billing. The legacy optional Gemini path is not part of the verified setup.

Start the app:

```sh
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open [Clariqo locally](http://127.0.0.1:8501/). The embedding model is downloaded on first use, which requires internet access. The local model cache is excluded from Git.

The exact lock file above records the tested Intel Mac environment. `requirements.txt` lists general dependencies, and `requirements-local-mac.txt` contains the main Intel Mac compatibility constraints. Other platforms require their own installation check.

## Testing

Run the isolated, mocked regression and edge-case tests from the project directory:

```sh
python -m unittest discover -s tests -v
```

The tests use temporary learning data and synthetic PDF fixtures. They do not establish live provider availability or universal accuracy of generated answers. They require neither a real API key nor the user's PDFs/model cache. Reproducible plan-format fixtures are included under `tests/fixtures/`.

For a structured report and function-call inventory:

```sh
python tests/run_deep_audit.py
```

Generated reports go to `test_results/`, which is ignored by Git.

## Saved files and privacy

The app stores uploads under `uploads/`, search data under `data/vector_store/`, and learning state in `data/memory.json`. Memory writes are atomic, and invalid PDF replacements preserve the original PDF and index on handled failures. `.gitignore` excludes saved data, backups, uploaded PDFs, caches, virtual environments, secrets and generated test outputs.

This version has one local learning profile. Separate student accounts, cross-device sync and multi-user isolation are not implemented. Model answers can be wrong, scanned PDFs need OCR, long plan materials may be included only partially, and PDF-only vague follow-ups can miss the intended passage. Saving progress does not guarantee educational correctness.

## Code map

| File | Purpose |
| --- | --- |
| `app.py`, `ui_components.py` | Streamlit pages and display helpers |
| `config.py`, `study_chat.py` | Provider calls, conversation routing and search |
| `rag.py`, `study_uploads.py` | PDF extraction, vectors and safe replacement |
| `quiz.py`, `study_plan.py`, `tools.py` | Study activities and tool routing |
| `memory.py` | Local learning history and recovery |
| `tests/` | Automated tests, sample PDFs and test fixtures |

## Upstream

This project began from [ug8yogesh/AI-Learning-Study-Assistant](https://github.com/ug8yogesh/AI-Learning-Study-Assistant) and has been modified for Clariqo. The downloaded source did not include a license file; no new upstream license is asserted here.
