"""
Punto de entrada para Streamlit Cloud.

Configura el PATH y ejecuta la aplicación Tomorrow como principal.
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
    "app_tomorrow",
    repo_root / "dashboard" / "apps" / "tomorrow" / "app_Tomorrow.py"
)
app_tomorrow = importlib.util.module_from_spec(spec)
sys.modules["app_tomorrow"] = app_tomorrow
spec.loader.exec_module(app_tomorrow)