
"""
Módulo para obtener precios de OMIE (Operador del Mercado Ibérico).

Proporciona acceso a datos de precios del mercado eléctrico español.
"""

from typing import Tuple, Optional, Dict, Any
import pandas as pd
from dashboard.comun.safe_request import safe_request
from dashboard.comun.date_conditions import RangoFechas


OMIE_API_URL = "https://www.omie.es/api"


def get_OMIE_prices(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene precios del mercado OMIE.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error)
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_OMIE_prices(rango)
    """
    try:
        # Endpoint de OMIE para precios
        url = f"{OMIE_API_URL}/prices"
        
        params = {
            "start": rango['start_date'].isoformat(),
            "end": rango['end_date'].isoformat()
        }
        
        response, error = safe_request(url, params=params)
        if error:
            return None, error
        
        # Parsear respuesta
        data = response.json()
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        
        return df, None
        
    except Exception as e:
        return None, f"Error en OMIE: {e}"


__all__ = ["get_OMIE_prices"]
