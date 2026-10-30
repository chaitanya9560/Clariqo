"""Select this entrypoint when deploying on Streamlit Community Cloud."""
import os
from pathlib import Path
import runpy
import sys

# Small CPU-only demo deployment; avoid excessive native worker threads.
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
runpy.run_path(str(ROOT / 'cloud_app.py'), run_name='__main__')
