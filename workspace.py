"""Request-local storage for the public demo; local use keeps its saved profile."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import time
from collections import deque
from functools import wraps
import threading


@dataclass
class VectorState:
    index: object = None
    metadata: list = field(default_factory=list)


class Workspace:
    """Owned by one Streamlit session, never selected through a URL or filename."""
    def __init__(self):
        self._temp = tempfile.TemporaryDirectory(prefix='clariqo-session-')
        self.root = Path(self._temp.name)
        self.uploads = self.root / 'uploads'
        self.vector_store = self.root / 'vectors'
        self.memory_file = self.root / 'memory.json'
        self.uploads.mkdir()
        self.vector_store.mkdir()
        self.vectors = VectorState()
        self.lock = threading.RLock()
        self.api_calls = deque()

    def close(self):
        self._temp.cleanup()


_CURRENT = ContextVar('clariqo_workspace', default=None)


def current_workspace():
    return _CURRENT.get()


@contextmanager
def use_workspace(workspace):
    token = _CURRENT.set(workspace)
    try:
        yield workspace
    finally:
        _CURRENT.reset(token)


def workspace_locked(fn):
    """Serialize storage changes within a visitor, without blocking other visitors."""
    @wraps(fn)
    def call(*args, **kwargs):
        workspace = current_workspace()
        if workspace is None:
            return fn(*args, **kwargs)
        with workspace.lock:
            return fn(*args, **kwargs)
    return call


def reserve_ai_request():
    """Basic session quota for a public demo, not an abuse-proof account limit."""
    workspace = current_workspace()
    if workspace is None:
        return
    now = time.monotonic()
    with workspace.lock:
        while workspace.api_calls and workspace.api_calls[0] <= now - 3600:
            workspace.api_calls.popleft()
        if len(workspace.api_calls) >= 60:
            raise RuntimeError('This public demo session has reached its 60 AI requests per hour. Please try again later. Routing and generated answers each use requests.')
        workspace.api_calls.append(now)
