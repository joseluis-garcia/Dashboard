import sys
from pathlib import Path

# Agregar raíz al PATH
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Importar la app
from dashboard.apps.tomorrow.app_Tomorrow import *