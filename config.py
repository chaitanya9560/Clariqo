"""
Configuration management for AI Learning & Study Assistant.
Handles paths, environment variables, Gemini API setup, and model parameters.
"""

import os
import sys
import warnings
import re
from urllib.parse import urlsplit
from pathlib import Path
from dotenv import load_dotenv
from workspace import current_workspace, reserve_ai_request

# Suppress deprecation warnings from legacy packages
warnings.filterwarnings("ignore", category=FutureWarning)

# Fix for Windows Python 3.8+ DLL loading (PyTorch / C extensions in virtual environments)
if sys.platform == "win32":
    try:
        site_packages = Path(sys.executable).parent.parent / "Lib" / "site-packages"
        torch_lib = site_packages / "torch" / "lib"
        if torch_lib.exists():
            os.add_dll_directory(str(torch_lib))
    except Exception:
        pass

# Base directory
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(BASE_DIR / ".model-cache"))

# Load environment variables from .env file
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()  # Fallback to system environment

# Directory paths
DATA_DIR = BASE_DIR / "data"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
UPLOADS_DIR = BASE_DIR / "uploads"
MEMORY_FILE = DATA_DIR / "memory.json"

# Ensure necessary directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").strip().lower()
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
AI_PROVIDER_NAME = "Groq" if AI_PROVIDER == "groq" else "Gemini"
AI_MODEL_NAME = GROQ_MODEL_NAME if AI_PROVIDER == "groq" else GEMINI_MODEL_NAME


def is_ai_configured() -> bool:
    if AI_PROVIDER == "gemini":
        return is_gemini_configured()
    if AI_PROVIDER != "groq":
        return False
    key = os.getenv("GROQ_API_KEY", "").strip()
    return bool(key and key not in {"paste_your_groq_key_here", "your_groq_api_key_here"})


def generate_text(prompt: str, system_instruction: str = None, reasoning_effort: str = "low", history=None, response_format=None) -> str:
    options = {"response_format": response_format} if response_format is not None else {}
    return generate_completion(prompt, system_instruction, reasoning_effort, history=history, **options)["answer"]


def generate_completion(prompt: str, system_instruction: str = None, reasoning_effort: str = "low", history=None, web_search: bool = False, response_format=None) -> dict:
    """Call only the chosen provider; never fall back to another account or provider."""
    if AI_PROVIDER == "gemini":
        if web_search:
            raise RuntimeError("Internet search is currently available with the Groq connection only.")
        return {"answer": generate_gemini_text(prompt, system_instruction), "web_sources": [], "searched": False}
    if AI_PROVIDER != "groq":
        raise ValueError("AI_PROVIDER must be groq or gemini in .env.")
    if not is_ai_configured():
        raise ValueError("Add your Groq API key to GROQ_API_KEY in .env, then restart the website.")

    reserve_ai_request()
    import requests
    key = os.getenv("GROQ_API_KEY", "").strip()
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    for message in (history or [])[-6:]:
        if message.get("role") in {"user", "assistant"} and isinstance(message.get("content"), str):
            messages.append({"role": message["role"], "content": message["content"][:1200]})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL_NAME, "messages": messages, "max_completion_tokens": 4096}
    if response_format is not None:
        if web_search:
            raise ValueError("Structured replies cannot be combined with internet search.")
        payload["response_format"] = response_format
    if GROQ_MODEL_NAME.startswith("openai/gpt-oss-"):
        payload["reasoning_effort"] = reasoning_effort
    if web_search:
        payload["tools"] = [{"type": "browser_search"}]
        # Let Groq decline an unnecessary search rather than returning a forced-tool
        # error. The caller still requires executed search and sources before it
        # presents a reply as an internet answer.
        payload["tool_choice"] = "auto"
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=(10, 45),
        )
    except requests.Timeout:
        raise RuntimeError("Groq took too long to reply. Please try again shortly.") from None
    except requests.RequestException:
        raise RuntimeError("Could not connect to Groq. Check your internet connection and try again.") from None

    if response.status_code in (401, 403):
        raise RuntimeError("Groq rejected this API key or account access. Check GROQ_API_KEY in .env.")
    if response.status_code == 429:
        raise RuntimeError("Groq's usage limit was reached. Wait a little before trying again.")
    if response.status_code >= 500:
        raise RuntimeError("Groq is temporarily unavailable. Please try again shortly.")
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", "Request rejected.")
        except (ValueError, AttributeError):
            detail = "Request rejected."
        raise RuntimeError(f"Groq request failed: {str(detail).replace(key, '[REDACTED]')[:500]}")
    try:
        result = response.json()["choices"][0]
        content = result["message"]["content"]
        if result.get("finish_reason") == "length":
            raise RuntimeError("The AI reply was cut short. Try fewer questions or a shorter request.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty reply")
        tools = result["message"].get("executed_tools") or []
        sources = []
        source_by_tool = {}
        seen = set()
        for tool in tools:
            results = (tool.get("search_results") or {}).get("results") or []
            for source in results:
                url = source.get("url", "")
                try:
                    parsed = urlsplit(url)
                    valid = parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username
                except (ValueError, TypeError):
                    valid = False
                if not valid:
                    continue
                source_by_tool.setdefault(str(tool.get("index")), url)
                if url not in seen:
                    sources.append({"title": source.get("title") or parsed.hostname, "url": url})
                    seen.add(url)
        if tools:
            content = re.sub(r"[【〖](\d+)†[^】〗]+[】〗]", lambda m: f" [source](<{source_by_tool[m.group(1)]}>)" if m.group(1) in source_by_tool else "", content)
        return {"answer": content.strip(), "web_sources": sources[:6], "searched": any(t.get("type") == "browser_search" or t.get("name") == "browser.search" for t in tools)}
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError("Groq returned an empty or unreadable reply. Please try again.") from None

# Embedding & Vector Search Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "4"))

def is_gemini_configured() -> bool:
    """Checks if a valid Gemini API key is configured in the server environment."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or GEMINI_API_KEY
    return bool(api_key and api_key != "your_gemini_api_key_here")

# Optional API client helper
def get_gemini_client():
    """
    Initializes and returns the Google Generative AI client or model.
    Raises ValueError if the API key is not configured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. Please ensure the GEMINI_API_KEY environment variable "
            "is configured on the server."
        )

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai

def generate_gemini_text(prompt: str, system_instruction: str = None) -> str:
    """
    Executes a prompt against the configured Gemini model with comprehensive error handling.
    If the requested model encounters Google's API 404 deprecation for new accounts,
    it automatically falls back to gemini-flash-latest so the application never crashes.
    """
    try:
        genai = get_gemini_client()
        model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL_NAME).strip()

        # Initialize generative model
        kwargs = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction

        try:
            model = genai.GenerativeModel(model_name=model_name, **kwargs)
            response = model.generate_content(prompt, request_options={"timeout": 45})
        except Exception as api_err:
            err_str = str(api_err)
            # Automatic resilient fallback for models deprecated by Google's API for new keys
            if "no longer available to new users" in err_str or ("404" in err_str and "gemini-2.5" in model_name):
                fallback_name = "gemini-3.8-flash"
                fallback_model = genai.GenerativeModel(model_name=fallback_name, **kwargs)
                response = fallback_model.generate_content(prompt, request_options={"timeout": 45})
            else:
                raise api_err

        if not response or not response.text:
            return "No response received from Gemini model. Please try again."

        return response.text.strip()
    except ValueError as ve:
        # Missing API Key
        raise ve
    except Exception as e:
        err_msg = str(e)
        saved_key = os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        if saved_key:
            err_msg = err_msg.replace(saved_key, "[REDACTED]")
        model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL_NAME).strip()
        if "free tier is not available" in err_msg.lower():
            raise RuntimeError(
                "Google has disabled free-tier API access for this project. "
                "AI answers, quizzes, and plans are unavailable until an eligible project or provider is configured. "
                "No paid billing has been enabled by this website."
            ) from e
        if "404" in err_msg or "NotFound" in err_msg or "models/" in err_msg:
            raise RuntimeError(
                f"The configured Gemini model '{model_name}' was not found or is unavailable for your API key.\n"
                f"Error details: {err_msg}\n\n"
                "Tip: Set GEMINI_MODEL=gemini-3.8-flash in your .env file."
            ) from e
        elif "API_KEY_INVALID" in err_msg or "400" in err_msg and "API key" in err_msg.lower():
            raise RuntimeError(
                "Invalid Gemini API Key provided. Please verify your GEMINI_API_KEY in the .env file."
            ) from e
        elif "ResourceExhausted" in err_msg or "429" in err_msg:
            raise RuntimeError(
                "Gemini API rate limit exceeded or quota exhausted. Please wait a moment before trying again."
            ) from e
        else:
            raise RuntimeError(
                f"Gemini API error ({type(e).__name__}): {err_msg}\n"
                f"Model: '{model_name}'. Check your internet connection or model availability in .env."
            ) from e


def get_uploads_dir():
    """Use the bound visitor folder, or the original local profile."""
    workspace = current_workspace()
    return workspace.uploads if workspace is not None else UPLOADS_DIR
