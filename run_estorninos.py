"""
Punto de entrada para Streamlit Cloud.

Configura el PATH y ejecuta la aplicación Estorninos como principal.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al PATH para que encuentre 'dashboard'
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Importar todas las funciones y variables de app_Tomorrow
# Esto ejecutará el código principal de la app
import importlib.util

spec = importlib.util.spec_from_file_location(
    "app_estorninos",
    repo_root / "dashboard" / "apps" / "estorninos" / "app_Estorninos.py"
)
app_estorninos = importlib.util.module_from_spec(spec)
sys.modules["app_estorninos"] = app_estorninos
spec.loader.exec_module(app_estorninos)