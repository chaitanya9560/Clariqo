"""Stage PDF uploads so failed replacements preserve saved material."""
import copy
import tempfile
from pathlib import Path

import config
import memory
import rag


def save_and_index_pdf(uploaded_file):
    name = uploaded_file.name
    if (not name or name in {'.', '..'} or '/' in name or '\\' in name
            or Path(name).name != name or Path(name).suffix.lower() != '.pdf'):
        raise ValueError('Choose a PDF with a plain file name, without folders.')
    if uploaded_file.size > 20 * 1024 * 1024:
        raise ValueError('The PDF limit is 20 MB per file.')

    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = config.UPLOADS_DIR / name
    if target.is_symlink():
        raise ValueError('This saved file cannot be replaced. Use a different PDF name.')

    with tempfile.TemporaryDirectory(prefix='.upload-', dir=config.UPLOADS_DIR) as temp:
        staged = Path(temp) / name
        staged.write_bytes(uploaded_file.getbuffer())

        # Keep the last working index until both indexing and PDF replacement finish.
        rag.load_vector_store()
        import faiss
        previous_index = faiss.clone_index(rag._FAISS_INDEX) if rag._FAISS_INDEX is not None else None
        previous_metadata = copy.deepcopy(rag._CHUNKS_METADATA)
        disk_state = {p: p.read_bytes() if p.exists() else None
                      for p in (rag.FAISS_INDEX_FILE, rag.METADATA_FILE)}
        try:
            result = rag.process_and_index_pdf(staged, name, record_topic=False)
            # Same filesystem: replace the original only after successful indexing.
            staged.replace(target)
        except Exception:
            rag._FAISS_INDEX = previous_index
            rag._CHUNKS_METADATA = previous_metadata
            for path, content in disk_state.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            raise

    memory.add_topic_studied(Path(name).stem.replace('_', ' ').title())
    return result
