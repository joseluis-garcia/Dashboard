"""
Módulo para obtener datos historicos de ESIOS en base a una lista de indicators.

Proporciona funciones
- get_indicator: Obtiene los valores de un indicador ESIOS
- fetch_multiple_indicators: Obtiene multiples indicators de forma asincrona
- get_ESIOS_energy_forecast: Previsiones de energía eólica, solar fotovoltaica y demanda
- get_ESIOS_energy_history: Datos historicos de energía de multiples fuente no CO2
- get_ESIOS_spot: Precio del mercado spot diario
"""
from typing import Tuple, Optional, Dict, Any
import pandas as pd
import streamlit as st

from dashboard.comun.safe_request import safe_request_get
from dashboard.comun.date_conditions import RangoFechas
from dashboard.comun import date_conditions as dc
from dashboard.comun.date_conditions import RangoFechas
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# FUNCIÓN DE DESCARGA indicadores ESIOS
# =========================

API_TOKEN = st.secrets["ESIOS_token"]
BASE_URL = "https://api.esios.ree.es/indicators"

headers = {
    "x-api-key": f"{API_TOKEN}",
    "Accept": "application/json;  application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "Host":"api.esios.ree.es",
    "Cookie":""
}

# Códigos de indicadores ESIOS
# Prevision
IND_EO = 541        # Previsión eólica - Previsión de la producción eólica peninsular
IND_FV = 542        # Solar fotovoltaica - Generación prevista Solar fotovoltaica
IND_DEM = 603       # Previsión semanal - Previsión semanal de la demanda eléctrica peninsular
# Historico
IND_DEMANDA = 1293  # Demanda real - Demanada real
IND_GEN_FV = 1295   # Solar fotovoltaica - Generación T.Real Solar fotovoltaica
IND_GEN_TR = 1296   # Térmica renovable - Generación T.Real Térmica renovable
IND_GEN_EO = 551    # Eólica - Generación T.Real eólica
IND_GEN_HID = 546   # Hidráulica - Generación T.Real hidráulica
IND_GEN_NUC = 549   # Nuclear - Generación T.Real nuclear
# Historica hasta D+1
IND_SPOT = 600      # Mercado SPOT - Precio mercado spot diario
IND_DESV_UP = 686   # Desvíos a subir - Precio de cobro desvíos a subir
IND_DESV_DOWN = 687 # Precio de pago desvíos a bajar - Precio de pago desvíos a bajar

#======
# Alias Frecuencia
# 'min' o 'T'Minuto'
# '5min' 5 minutos
# '15min' 15 minutos
# 'h' o 'H' Hora
# 'D'Día
# 'W'Semana
# 'ME'Fin de mes
# 'MS'Inicio de mes
# 'QE'Fin de trimestre
# 'YE'Fin de año
# 'YS'Inicio de año
#======

def get_indicator(indicator_id: int, date_range: RangoFechas, time_trunc: str = None):

    url = f"{BASE_URL}/{indicator_id}"
    response, error = safe_request_get(url, headers=headers, params=date_range)
    if error:
        st.error(f"No se han podido obtener los datos del indicador {indicator_id}.")
        st.error(error)
        return None, error  # Devuelve un DataFrame vacío en caso de error

    json_data = response.json()
    data = json_data["indicator"]["values"]
    variable = json_data["indicator"]["short_name"]

    df = pd.DataFrame(data)

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["datetime"] = df["datetime"].dt.tz_localize(None)
    df = df.set_index("datetime").sort_index()
    print(f"Retornadas {len(df)} filas")
    
    #En IND_SPOT devuelve precios de diversos paises, nos debemos quedar solo con España
    if indicator_id == IND_SPOT:
        df = df[df['geo_name'] == 'España']
        print(f"Filtradas España {len(df)} filas")
    #Como los distintos indicators vienen con diferente timestamp y la funcion de agregación de ESIOS (time_trunc) no garantiza que metodo utiliza debemos hacerlo nosotros
    if time_trunc is not None:
        df = df.select_dtypes(include='number').resample(time_trunc).mean()
    print(f"Resampling final {len(df)} filas")
    df["variable"] = variable
    return df, None

def fetch_multiple_indicators(indicator_ids: list[int], rango: RangoFechas, max_workers: int = 10) -> pd.DataFrame:

    dfs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_indicator, ind_id, rango, time_trunc="h"): ind_id
            #executor.submit(fetch_indicator, ind_id, start_date, end_date): ind_id
            for ind_id in indicator_ids
        }

        for future in as_completed(futures):
            ind_id = futures[future]
            try:
                result, error = future.result()
                if error:
                    print (f"Error en indicador {ind_id}: {error}")
                else:
                    df_pivot = result[['variable', 'value']].pivot( columns='variable', values='value')
                    df_pivot.columns.name = None
                    dfs.append(df_pivot)
            except Exception as e:
                print(f"Error en indicator {ind_id}: {e}")

    df_final = pd.concat(dfs, axis=1)
    return df_final, None

def get_ESIOS_energy_forecast(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de energía (eólica, solar y demanda) de ESIOS.
    
    Obtiene las previsiones de energía eólica, solar fotovoltaica y demanda
    del sistema eléctrico español para el rango de fechas especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error de API
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_ESIOS_energy(rango)
        >>> if not error:
        ...     print(df.head())
    """
    df_energy, error = fetch_multiple_indicators([IND_EO, IND_FV, IND_DEM], rango)
    if error:
        return None, error
    df_energy["renovable"] = df_energy["Previsión eólica"] + df_energy["Solar fotovoltaica"]
    return df_energy, None

def get_ESIOS_energy_history( rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de energía (eólica, solar y demanda) de ESIOS.
    
    Obtiene las previsiones de energía eólica, solar fotovoltaica y demanda
    del sistema eléctrico español para el rango de fechas especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error de API
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_ESIOS_energy(rango)
        >>> if not error:
        ...     print(df.head())
    """

    indicators = [IND_DEMANDA, IND_GEN_FV, IND_GEN_TR, IND_GEN_EO, IND_GEN_HID, IND_GEN_NUC]
    result, error = fetch_multiple_indicators(indicators, rango)
    return result, error

def get_ESIOS_spot(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de precio spot diario de ESIOS.
    
    Obtiene el precio del mercado spot diario para España (Península Ibérica)
    del sistema eléctrico español.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columna 'Mercado SPOT'
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> df, error = get_ESIOS_spot(rango)
        >>> if not error:
        ...     print(f"Precio promedio: {df['Mercado SPOT'].mean():.2f} €/MWh")
    """
    spot, error = get_indicator(IND_SPOT, rango, 'h')
    if error:
        return None, error

    spot = spot[["value"]].rename(columns={"value": "Mercado SPOT"})
    return spot, None

__all__ = ["get_ESIOS_energy_forecast", "get_ESIOS_spot", "grafico_ESIOS_energy_history"]