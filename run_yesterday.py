"""
Punto de entrada para Streamlit Cloud.

Configura el PATH y ejecuta la aplicación Yesterday como principal.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al PATH para que encuentre 'dashboard'
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Importar todas las funciones y variables de app_yesterday
# Esto ejecutará el código principal de la app
import importlib.util

spec = importlib.util.spec_from_file_location(
    "app_yesterday",
    repo_root / "dashboard" / "apps" / "yesterday" / "app_Yesterday.py"
)
app_yesterday = importlib.util.module_from_spec(spec)
sys.modules["app_yesterday"] = app_yesterday
spec.loader.exec_module(app_yesterday)