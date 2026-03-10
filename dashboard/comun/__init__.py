"""
Módulo comun - Funciones compartidas entre aplicaciones.

Contiene utilidades para:
- Manejo de fechas y cálculos solares (date_conditions)
- Acceso a APIs externas (ESIOS, OpenMeteo, PVGIS)
- Utilidades de BD (sql_utilities)
- Funciones de seguridad y networking (safe_request)
- Tareas asincrónicas (async_tasks)
"""

from dashboard.comun import date_conditions
from dashboard.comun.sql_utilities import init_db, get_tables_info, read_sql_ts
from dashboard.comun.safe_request import safe_request
from dashboard.comun.async_tasks import run_async, async_placeholder

__all__ = [
    "date_conditions",
    "init_db",
    "get_tables_info",
    "read_sql_ts",
    "safe_request",
    "run_async",
    "async_placeholder",
]
