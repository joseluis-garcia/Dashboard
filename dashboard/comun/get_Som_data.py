"""
Módulo para obtener y visualizar precios de SOM Energía.

Proporciona funciones para:
- Obtener precios de hoy y mañana de SOM Energía
- Crear gráficos interactivos de precios por hora
- Mostrar comparativa de precios hoy vs mañana
"""

import sqlite3
from typing import Tuple, Optional
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dashboard.comun.date_conditions import RangoFechas, get_cache_period
from dashboard.comun.safe_request import safe_request_get
from dashboard.comun.sql_utilities import read_sql_ts, init_db

@st.cache_data
def get_prices_Som_indexada(cache_period: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene precios de hoy y mañana desde la API de SOM Energía.
    
    Obtiene los últimos 48 valores (24 horas de hoy + 24 de mañana)
    de la API de SOM Energía para la tarifa 2.0TD en Península.
    
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['hora', 'hoy', 'mañana']
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df, error = get_prices_Som()
        >>> if not error:
        ...     print(f"Precio hoy: {df['hoy'].mean():.3f}€/kWh")
    """
    BASE_URL = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"

    response, error = safe_request_get(BASE_URL)
    if error:
        return None, error

    try:
        data = response.json()
        prices = data["data"]["curves"]["price_euros_kwh"][-48:]  # últimas 48 horas
        today = prices[:24]
        tomorrow = prices[24:]
        
        df = pd.DataFrame({
            "hora": range(24),
            "hoy": today,
            "mañana": tomorrow
        })
        
        return df, None
        
    except (KeyError, IndexError, ValueError) as e:
        return None, f"Error al parsear datos de SOM Energía: {e}"
    except Exception as e:
        return None, f"Error inesperado en get_prices_Som: {e}"

TZ = ZoneInfo("Europe/Madrid")

def to_utc(dt_local):
    dt_local = dt_local.replace(tzinfo=TZ)
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
    return dt_utc.replace(tzinfo=None)

def build_local_series(data):
    first_local = datetime.fromisoformat(data["first_date"])
    print(f"Primera fecha (local) en datos de SOM: {first_local}")

    prices = data["curves"]["price_euros_kwh"]
    n = len(prices)

    dates_local = [first_local + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame({
        "date_local": dates_local,
        "price": prices
    })
    print(f"DataFrame construido desde API con {len(df)} filas. Rango de fechas (local): {df['date_local'].min()} a {df['date_local'].max()}")

    return df

def insert_prices(conn, data):
    try:
        df = build_local_series(data)

        # 1. Eliminar precios nulos
        df = df[df["price"].notna()].copy()
        
        # 2. Convertir a UTC
        df["date_utc"] = df["date_local"].apply(to_utc)
        print(f"Ultima fecha UTC con datos not null: {df['date_utc'].max()}")

        # 3. Leer última fecha existente en SQLite
        cur = conn.cursor()
        cur.execute("SELECT MAX(datetime) FROM SOM_precio_indexada")
        row = cur.fetchone()
        last_existing_utc = row[0]
        print(f"Última fecha UTC existente en la base de datos: {last_existing_utc}")

        if last_existing_utc is not None:
            last_existing_utc = datetime.fromisoformat(last_existing_utc)
            df = df[df["date_utc"] > last_existing_utc]

        # 4. Insertar solo los nuevos
        if not df.empty:
            df = df.rename(columns={"date_utc": "datetime"})
            df = df.drop(columns=["date_local"])
            df.to_sql("SOM_precio_indexada", conn, if_exists="append", index=False)
            return df, None
        else:
            return None, f"No hay nuevos precios para insertar en SOM_precio_indexada"
    except Exception as e:
        return None, f"Error al insertar precios en la base de datos: {e}"
    
def update_Som_history(
		conn: Optional[sqlite3.Connection] = None) -> Tuple[
			Optional[pd.DataFrame], 
			Optional[str]]:
    """
    Actualiza los precios de SOM Energía en la base de datos a partir de la URL de la API.
    """

    if conn is None:
        # Connect to SQLite database
        conn, error = init_db()
        if error:
            return None, f"Error al conectar a la base de datos: {error}"

    url = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"
    response, error = safe_request_get(url)
    if error:
        return None, f"Obteniendo precios Som: {error}"

    tarifa = response.json()
    return insert_prices(conn, tarifa['data'])

def get_Som_prices_from_measurements(conn: sqlite3.Connection, rango: RangoFechas) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene el histórico de precios de SOM Energía desde la base de datos.
    
    Args:
        conn: Conexión a la base de datos SQLite
        rango: Rango de fechas para filtrar los datos

    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas Index datetime UTC naive, 'price'
        - error: None si es exitoso, mensaje de error si falla

    Example:
        >>> df_prices, error = get_Som_prices_from_measurements(conn, rango)
        >>> if error:
        >>>     mensaje (error)
        >>> else:
        >>>     print(df_prices.head())
    """
    if rango is None:
        query = "SELECT datetime, price FROM SOM_precio_indexada ORDER BY datetime"
    else:
        query = f"SELECT datetime, price FROM SOM_precio_indexada WHERE datetime >= '{rango['start_date']}' AND datetime <= '{rango['end_date']}' ORDER BY datetime"
        
    df, error = read_sql_ts(query, conn)
    return df, error

if __name__ == "__main__":
    df, error = update_Som_history()

    if error:
        print(f"Error: {error}")
    if df is not None:
        print(df.head())
        desde = df['datetime'].min().strftime("%Y-%m-%d %H:%M")
        hasta = df['datetime'].max().strftime("%Y-%m-%d %H:%M")
        print(f"{len(df)} filas insertadas en SOM_precio_indexada desde {desde} hasta {hasta}")

__all__ = ["get_prices_Som_indexada", "update_Som_data", "get_Som_prices_from_measurements"]