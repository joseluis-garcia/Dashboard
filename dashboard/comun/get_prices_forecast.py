"""
Módulo para obtener y visualizar predicciones de precios de energía.

Proporciona funciones para:
- Calcular precios estimados basados en energía renovable y demanda
- Agregar costes regulados
- Visualizar precios estimados vs spot
"""

from typing import Optional, Tuple
import pandas as pd

import dashboard.apps.config as TCB

from dashboard.comun import date_conditions as dc
from dashboard.comun.costes_regulados import costes_regulados
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_forecast, get_ESIOS_spot

def get_prices_forecast(rango: dc.RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Calcula precios estimados a partir de energía renovable y demanda.
    
    Utiliza la ecuación lineal: precio = (renovable/demanda) * slope + intercept
    Luego agrega costes regulados para obtener precio final estimado.
    
    Args:
        energy: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        spot: DataFrame con columna 'Mercado SPOT'
        
    Returns:
        DataFrame con precios spot, estimados y costes regulados
        
    Example:
        >>> df_energy, _ = get_ESIOS_energy(rango)
        >>> df_spot, _ = get_ESIOS_spot(rango)
        >>> df_prices = get_prices_forecast(df_energy, df_spot)
        >>> print(df_prices.head())
    """
               
    df_energy, error = get_ESIOS_energy_forecast(rango)
    if error:
        return None, error
    
    df_spot, error = get_ESIOS_spot(rango)
    if error:
        return None, error
    
    # Combinar energía y spot
    df_final = df_energy.join(df_spot, how="outer")
    # Calcular energía renovable (ya está en energy, pero por si acaso)
    df_final["renovable"] = df_final["Previsión eólica"] + df_final["Solar fotovoltaica"]
    
    # Calcular precio estimado usando regresión lineal
    # precio_estimado = (renovable/demanda) * slope + intercept
    df_final["precio_estimado"] = (
        df_final["renovable"] / df_final["Previsión semanal"] * TCB.SLOPE + TCB.INTERCEPT
    )

    # Agregar costes regulados
    df_final = costes_regulados(df_final)
    
    # Sumar costes regulados a precios (spot y estimado)
    df_final["precio_estimado"] += df_final["costes_regulados"]
    df_final["Mercado SPOT"] += df_final["costes_regulados"]
    
    return df_final

__all__ = ["get_prices_forecast"]
