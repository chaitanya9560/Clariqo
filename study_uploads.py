"""Stage PDF uploads so failed replacements preserve saved material."""
import copy
import tempfile
from pathlib import Path

import config
import memory
import rag
from workspace import current_workspace, workspace_locked


@workspace_locked
def save_and_index_pdf(uploaded_file):
    name = uploaded_file.name
    if (not name or name in {'.', '..'} or '/' in name or '\\' in name
            or Path(name).name != name or Path(name).suffix.lower() != '.pdf'):
        raise ValueError('Choose a PDF with a plain file name, without folders.')
    if uploaded_file.size > 20 * 1024 * 1024:
        raise ValueError('The PDF limit is 20 MB per file.')

    config.get_uploads_dir().mkdir(parents=True, exist_ok=True)
    target = config.get_uploads_dir() / name
    if current_workspace() is not None:
        saved = [p for p in config.get_uploads_dir().glob('*.pdf') if p != target]
        if len(saved) >= 5:
            raise ValueError('The public demo allows up to 5 PDFs per session.')
        if sum(p.stat().st_size for p in saved) + uploaded_file.size > 50 * 1024 * 1024:
            raise ValueError('The public demo allows up to 50 MB of PDFs per session.')
    if target.is_symlink():
        raise ValueError('This saved file cannot be replaced. Use a different PDF name.')

    with tempfile.TemporaryDirectory(prefix='.upload-', dir=config.get_uploads_dir()) as temp:
        staged = Path(temp) / name
        staged.write_bytes(uploaded_file.getbuffer())

        # Keep the last working index until both indexing and PDF replacement finish.
        rag.load_vector_store()
        import faiss
        previous_index = faiss.clone_index(rag.get_vector_state().index) if rag.get_vector_state().index is not None else None
        previous_metadata = copy.deepcopy(rag.get_vector_state().metadata)
        disk_state = {p: p.read_bytes() if p.exists() else None
                      for p in (rag.get_store_paths()['index'], rag.get_store_paths()['metadata'])}
        try:
            result = rag.process_and_index_pdf(staged, name, record_topic=False)
            # Same filesystem: replace the original only after successful indexing.
            staged.replace(target)
        except Exception:
            rag.get_vector_state().index = previous_index
            rag.get_vector_state().metadata = previous_metadata
            for path, content in disk_state.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            raise

    memory.add_topic_studied(Path(name).stem.replace('_', ' ').title())
    return result
