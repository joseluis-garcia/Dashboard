"""
Dashboard Energético - Aplicación integrada para visualización y predicción de precios de energía.

Este paquete contiene tres aplicaciones Streamlit especializadas:
- Yesterday: Análisis histórico de precios, consumo y meteorología
- Tomorrow: Pronóstico de precios y meteorología para el día actual
- Estorninos: Predicción de precios futuros para flexibilidad de demanda

Módulos principales:
- comun: Funciones compartidas entre aplicaciones
- apps: Tres aplicaciones Streamlit independientes

Ejemplo de uso programático:
    >>> from dashboard.comun.get_ESIOS_forecast import get_ESIOS_energy
    >>> from dashboard.comun.date_conditions import DateConditions
    >>> 
    >>> # Crear condiciones de fecha
    >>> conditions = DateConditions.from_rango({...})
    >>> 
    >>> # Obtener datos de energía
    >>> energy_df = get_ESIOS_energy(rango)

Para ejecutar las aplicaciones Streamlit:
    $ streamlit run dashboard/apps/yesterday/app_Yesterday.py
    $ streamlit run dashboard/apps/tomorrow/app_Tomorrow.py
    $ streamlit run dashboard/apps/estorninos/app_Estorninos.py

Documentación:
    Ver ARCHITECTURE.md para detalles sobre la arquitectura
    Ver README.md para instrucciones de instalación y uso
"""

__version__ = "1.0.0"
__author__ = "Tu Nombre"
__email__ = "tu.email@example.com"
__license__ = "MIT"

# Importaciones principales para facilitar acceso
from dashboard.comun import date_conditions
from dashboard.comun.sql_utilities import init_db, get_tables_info, read_sql_ts

__all__ = [
    "date_conditions",
    "init_db",
    "get_tables_info",
    "read_sql_ts",
]
