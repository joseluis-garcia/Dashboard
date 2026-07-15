"""
update_all.py
Ejecuta todas las actualizaciones de tablas de forma secuencial,
reportando errores al final sin detener el proceso.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # ajusta los .parent según tu estructura
sys.path.insert(0, str(BASE_DIR))

from dashboard.comun.load_secrets import load_secrets
load_secrets(base_dir=BASE_DIR)

from dashboard.comun.get_ESIOS_data import update_ESIOS_history
from dashboard.comun.get_openmeteo import update_openmeteo_history
from dashboard.comun.get_Som_data import update_Som_history
from dashboard.comun.get_WIBEE_data import update_WIBEE_history
# ... añade las que necesites

import traceback
from datetime import datetime

UPDATES = [
    ("ESIOS_data", update_ESIOS_history),
    ("METEO", update_openmeteo_history),
    ("Som_precio_indexada", update_Som_history),
    ("WIBEE", update_WIBEE_history),
]

def run_all_updates():
    resultados = []
    inicio = datetime.now()
    print(f"\n{'='*40}")
    print(f"Inicio actualización: {inicio:%Y-%m-%d %H:%M:%S}")
    print(f"{'='*40}\n")

    for nombre, fn in UPDATES:
        print(f"▶ Actualizando {nombre}...")
        t0 = datetime.now()
        try:
            fn()
            elapsed = (datetime.now() - t0).seconds
            print(f"  ✓ {nombre} OK ({elapsed}s)")
            resultados.append((nombre, "OK", None))
        except Exception as e:
            elapsed = (datetime.now() - t0).seconds
            tb = traceback.format_exc()
            print(f"  ✗ {nombre} FALLO ({elapsed}s): {e}")
            resultados.append((nombre, "FALLO", tb))

    # Resumen final
    print(f"\n{'='*40}")
    print(f"RESUMEN ({(datetime.now()-inicio).seconds}s total)")
    print(f"{'='*40}")
    fallos = [(n, tb) for n, estado, tb in resultados if estado == "FALLO"]
    exitosos = [n for n, estado, _ in resultados if estado == "OK"]

    print(f"  ✓ Exitosos ({len(exitosos)}): {', '.join(exitosos) or '-'}")
    print(f"  ✗ Fallidos ({len(fallos)}): {', '.join(n for n, _ in fallos) or '-'}")

    if fallos:
        print("\nDetalle de errores:")
        for nombre, tb in fallos:
            print(f"\n--- {nombre} ---\n{tb}")

    return len(fallos) == 0  # True si todo fue bien

if __name__ == "__main__":
    exito = run_all_updates()
    exit(0 if exito else 1)  # útil si lo llamas desde cron o CI