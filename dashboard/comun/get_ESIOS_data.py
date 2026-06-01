"""
Módulo para obtener datos historicos y forecast de ESIOS en base a una lista de indicators. Tambien permite actualizar tabla ESIOS_data en measurements.db

Proporciona funciones
- get_indicator: Obtiene los valores de un indicador ESIOS
- fetch_multiple_indicators: Obtiene multiples indicators de forma asincrona
- get_ESIOS_energy_forecast: Previsiones de energía eólica, solar fotovoltaica y demanda
- get_ESIOS_energy_history: Datos historicos de energía de multiples fuente no CO2
- get_ESIOS_spot: Precio del mercado spot diario
- update_ESIOS_history: Actualiza la tabla ESIOS_data con los datos historicos de energía y precio spot desde la última fecha registrada hasta la fecha actual
"""
import sqlite3
from typing import Tuple, Optional, Dict, Any
import pandas as pd
from datetime import date, datetime, timedelta, timezone

import requests

from dashboard.comun.safe_request import safe_request_get
from dashboard.comun.date_conditions import RangoFechas
from dashboard.comun.sql_utilities import init_db, read_sql_ts
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# FUNCIÓN DE DESCARGA indicadores ESIOS
# =========================

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent  # ajusta los .parent según tu estructura
sys.path.insert(0, str(BASE_DIR))

from dashboard.comun.load_secrets import load_secrets
load_secrets(base_dir=BASE_DIR)  # Carga secrets y parchea st.secrets antes de cualquier import

import streamlit as st 

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
IND_PVPC = 1001    # PVPC - Precio voluntario para el pequeño consumidor diario
IND_EXCEDENTES = 1739 # Excedentes - Precio de los excedentes de energía renovable

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

def get_indicator(indicator_id: int, date_range: RangoFechas, time_trunc: str = 'h') -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene los valores de un indicador ESIOS para un rango de fechas dado.
    Como los datos de ESIOS la función de agregación de ESIOS (time_trunc) no garantiza que método utiliza para agregar, se hace una agregación manual en caso de especificar time_trunc.
    
    Args:
        indicator_id: ID del indicador ESIOS a obtener
        date_range: Diccionario con 'start_date' y 'end_date'
        time_trunc: Frecuencia de agregación temporal. 
        "S" → segundo
        "T" o "min" → minuto
        "H" → hora
        "D" → día
        "B" → día laborable
        "W" → semana
        "M" → fin de mes
        "MS" → inicio de mes
        "Q" → fin de trimestre
        "QS" → inicio de trimestre
        "A" o "Y" → fin de año
        "AS" o "YS" → inicio de año
        Si es None, se mantienen los timestamps originales.
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con una columna con el nombre corto del indicador y el índice como datetime UTC convertido a naive sin tz (datetime)
        - error: None si es exitoso, mensaje de error si falla
    """

    PARAMS = {
        "start_date": date_range['start_date'],
        "end_date": date_range["end_date"],
        "time_agg": 'avg',
        "time_trunc" : 'hour'
    }

    url = f"{BASE_URL}/{indicator_id}"
    response, error = safe_request_get(url, headers=headers, params=PARAMS)
    if error:
        mensaje = f"Error obteniendo datos del indicador {indicator_id}: {error}"
        return None, mensaje  # Devuelve un DataFrame vacío en caso de error
    
    json_data = response.json()
    data = json_data["indicator"]["values"]
    variable = json_data["indicator"]["short_name"]

    df = pd.DataFrame(data)

    # Usamos datetime_utc como columna de tiempo para evitar problemas de horas repetidas en cambio de hora y convertimos en indice
    df["datetime"] = pd.to_datetime(df["datetime_utc"], utc=True)    
    df = df.set_index("datetime").sort_index()
    
    #En IND_SPOT devuelve precios de diversos paises, nos debemos quedar solo con España
    if indicator_id == IND_SPOT:
        df = df[df['geo_name'] == 'España']

    if indicator_id == IND_PVPC:
        df = df[df['geo_name'] == 'Península']

    #Como los distintos indicators vienen con diferente timestamp y la funcion de agregación de ESIOS (time_trunc) no garantiza que metodo utiliza debemos hacerlo nosotros

    if time_trunc:
        df = df.select_dtypes(include='number').resample('h').mean()

    #Cambia el nombre de la columna value por el short_name del indicador para facilitar su uso posterior    
    df = df[[ "value"]].rename(columns={"value": variable})

    return df, None

def fetch_multiple_indicators(indicator_ids: list[int], rango: RangoFechas, max_workers: int = 10) -> pd.DataFrame:
    """
    Obtiene múltiples indicadores de ESIOS de forma paralela.
        Args:
        indicator_ids: Lista de IDs de los indicadores ESIOS a obtener
        date_range: Diccionario con 'start_date' y 'end_date'
        max_workers: Número máximo de hilos para realizar las solicitudes en paralelo
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas con el nombre corto del indicador y el índice como datetime UTC convertido a naive sin tz (datetime)
        - error: None si es exitoso, mensaje de error si falla
    """
    
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
                    return None, f"Error al obtener el indicador {ind_id}: {error}"
                else:
                    dfs.append(result)
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
        - dataframe: DataFrame con columnas ["Previsión eólica", "Solar fotovoltaica", "Previsión semanal", 'Renovable']
         con Renovable = "Previsión eólica" + "Solar fotovoltaica"
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
    df_energy["Renovable"] = df_energy["Previsión eólica"] + df_energy["Solar fotovoltaica"]
    return df_energy, None

def get_ESIOS_energy_history( rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de energía por fuente y demanda de ESIOS.
    
    Obtiene las previsiones de energía eólica, solar fotovoltaica y demanda
    del sistema eléctrico español para el rango de fechas especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas con el nombre corto de los indicadores de fuente de energía y demanda (Mercado SPOT)
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

def get_ESIOS_prices_history( rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de precios de ESIOS.
    
    Obtiene los precios de los mercados PVPC, excedentes y spot para el rango de fechas especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['PVPC', 'Excedentes', 'Spot']
        - error: None si es exitoso, mensaje de error si falla
    """
    indicators = [IND_PVPC, IND_EXCEDENTES, IND_SPOT]
    result, error = fetch_multiple_indicators(indicators, rango)
    if error:
        return None, error

    # excedentes, error = get_indicator(IND_EXCEDENTES, rango, 'h')
    # if error:
    #     return None, error
    # pvpc, error = get_indicator(IND_PVPC, rango, 'h')
    # if error:
    #     return None, error
    # spot, error = get_indicator(IND_SPOT, rango, 'h')
    # if error:
    #     return None, error  
    # result = pd.concat([spot, excedentes, pvpc], axis=1)

    return result, None

def get_ESIOS_spot(rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de precio spot diario de ESIOS.
    
    Obtiene el precio del mercado spot diario para España (Península Ibérica)
    del sistema eléctrico español.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'. Si es None, se obtienen los datos del día actual.
        
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
    if rango is None:
        tz = timezone(timedelta(hours=1))  # Hora de Madrid (UTC+1)
        today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today
        end_date = today + timedelta(days=1) - timedelta(seconds=1)
        rango = {
            'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S')
        }

    # print("RANGO:",rango)
    spot, error = get_indicator(IND_SPOT, rango, 'h')
    if error:
        return None, error

    # print("SPOT:", spot)
    # if rango == None:
    #     hoy = date.today()
    #     df = spot.copy()
    #     df_hoy = df[df.index.tz_convert("Europe/Madrid").normalize() == pd.Timestamp(hoy, tz="Europe/Madrid")]
    #     return df_hoy, None

    return spot, None

def update_ESIOS_history(conn: Optional[sqlite3.Connection] = None) -> Tuple[
        Optional[pd.DataFrame], 
        Optional[str]]:

    if conn is None:
        # Connect to SQLite database
        conn, error = init_db()
        if error:
            return None, f"Error al conectar a la base de datos: {error}"

    try:
        #Previous data recorded until
        df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM ESIOS_data", conn, parse_dates=["maxDate"])
        df["maxDate"] = pd.to_datetime(df["maxDate"])
        startDate = df["maxDate"].iloc[0] + timedelta(hours=1)
        strStartDate = startDate.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Get the current UTC time
        endDate = datetime.now(timezone.utc) + timedelta(hours=-2)

        # Convert the datetime object to a string
        strEndDate = endDate.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        rango = {
            'start_date': strStartDate,
            'end_date': strEndDate
        }
        df_prices, error = get_ESIOS_prices_history(rango)
        if error:
            return None, error
        df_prices["datetime"] = pd.to_datetime(df_prices["datetime"], utc=True).dt.tz_localize(None)
        df_prices.to_sql('ESIOS_prices', conn, if_exists='append', index=False )

        df_energy, error = get_ESIOS_energy_history(rango)
        if error:
            return None, error
        df_energy["datetime"] = pd.to_datetime(df_energy["datetime"], utc=True).dt.tz_localize(None)      
        df_energy.to_sql('ESIOS_data', conn, if_exists='append', index=False )

        return None, None

    except Exception as e:
        return None, f"Error al insertar datos en la tabla ESIOS_data: {e}"

def get_ESIOS_data_from_measurements(conn: sqlite3.Connection, rango: Optional[RangoFechas] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga datos historicos de ESIOS para entrenar modelos desde SQL.
    Debe devolver columnas: ['datetime', 'Eólica', 'Solar fotovoltaica', 'Mercado SPOT', 'Demanda real']
        
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
         
        - dataframe: Index(['datetime', 'Eólica', 'Solar fotovoltaica', 'Mercado SPOT', 'Demanda real']
        - error: None si es exitoso, mensaje de error si falla
    """
    try:
        if rango is None:
            query = 'select datetime, Eólica, "Solar Fotovoltaica", "Mercado SPOT", "Demanda real" from ESIOS_data order by datetime'
        else:
            query = f'select datetime, Eólica, "Solar Fotovoltaica", "Mercado SPOT", "Demanda real" from ESIOS_data where datetime >= {rango["start_date"]} and datetime <= {rango["end_date"]} order by datetime'

        df, error = read_sql_ts(query, conn)
        if error:
            return None, f"Error al ejecutar consulta SQL para ESIOS_data: {error}"

        print("Filas con problemas en ESIOS_data:",df[df.isna().any(axis=1)])
        df = df.dropna(subset=['Eólica', 'Solar fotovoltaica', 'Demanda real'])
        return df, None
    
    except Exception as e:
        return None, f"Error al cargar datos historicos de ESIOS_data: {e}"

if __name__ == "__main__":
    _, error = update_ESIOS_history()

    conn, error = init_db()
    if error:
        print(f"Error al conectar a la base de datos: {error}")


__all__ = [
    "get_ESIOS_energy_forecast", 
    "get_ESIOS_spot",
    "get_ESIOS_energy_history", 
    "update_ESIOS_history", 
    "get_ESIOS_data_from_measurements"]