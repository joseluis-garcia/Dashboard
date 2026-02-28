import os
import streamlit as st

st.write("Current working directory:", os.getcwd())
st.write("Files in root:", os.listdir("/mount/src"))