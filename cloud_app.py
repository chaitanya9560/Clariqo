"""Streamlit Community Cloud entrypoint with isolated visitor workspaces."""
from pathlib import Path
import runpy
import streamlit as st
from workspace import Workspace, use_workspace

if '_private_workspace' not in st.session_state:
    st.session_state['_private_workspace'] = Workspace()

# ContextVars keep concurrent Streamlit script threads out of each other's data.
# Always reset on return, rerun or an exception.
with use_workspace(st.session_state['_private_workspace']):
    runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
