import sys
import tomllib
from pathlib import Path

def load_secrets(levels_up: int = 4):
    """
    Parchea st.secrets con el secrets.toml local.
    Llámalo ANTES de importar cualquier módulo que use st.secrets.
    
    levels_up: niveles hasta la raíz del proyecto (donde está .streamlit/)
    """
    import streamlit as st

    base_dir = Path(__file__).parents[levels_up - 1]
    secrets_path = base_dir / ".streamlit" / "secrets.toml"

    sys.path.insert(0, str(base_dir))

    with open(secrets_path, "rb") as f:
        _secrets = tomllib.load(f)

    class FakeSecrets(dict):
        def __getattr__(self, key):
            return self[key]

    st.secrets = FakeSecrets(_secrets)