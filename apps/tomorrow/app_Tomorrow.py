import os
import streamlit as st
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
st.write("Current working directory:", os.getcwd())
st.write("Files in root:", os.listdir("/mount/src"))
st.write("Repo root:", repo_root)