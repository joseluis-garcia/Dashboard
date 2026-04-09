"""
Módulo para obtener y visualizar precios de SOM Energía.

Proporciona funciones para:
- Obtener precios de hoy y mañana de SOM Energía
- Crear gráficos interactivos de precios por hora
- Mostrar comparativa de precios hoy vs mañana
"""

from dbm import sqlite3
from typing import Tuple, Optional
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dashboard.comun.safe_request import safe_request_get

@st.cache_data
def get_prices_Som_indexada() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
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
    prices = data["curves"]["price_euros_kwh"]
    n = len(prices)

    dates_local = [first_local + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame({
        "date_local": dates_local,
        "price": prices
    })
    return df

def insert_prices(conn, data):
    try:
        df = build_local_series(data)

        # 1. Eliminar precios nulos
        df = df[df["price"].notna()].copy()

        # 2. Convertir a UTC
        df["date_utc"] = df["date_local"].apply(to_utc)

        # 3. Leer última fecha existente en SQLite
        cur = conn.cursor()
        cur.execute("SELECT MAX(datetime) FROM SOM_precio_indexada")
        row = cur.fetchone()
        last_existing_utc = row[0]

        if last_existing_utc is not None:
            last_existing_utc = datetime.fromisoformat(last_existing_utc)
            df = df[df["date_utc"] > last_existing_utc]

        # 4. Insertar solo los nuevos
        if not df.empty:
            df["datetime"] = df["date_utc"].astype(str)
            df_to_insert = df[["datetime", "price"]]
            df_to_insert.to_sql("SOM_precio_indexada", conn, if_exists="append", index=False)
            return f"Insertadas {len(df_to_insert)} filas en SOM_precio_indexada", None
        else:
            return "No hay nuevos precios para insertar en SOM_precio_indexada", None
    except Exception as e:
        return None, f"Error al insertar precios en la base de datos: {e}"
    
def update_Som_history(conn: sqlite3.Connection) -> Tuple[Optional[str], Optional[str]]:
    """
    Actualiza los precios de SOM Energía en la base de datos a partir de la URL de la API.
    """

    url = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"
    response, error = safe_request_get(url)
    if error:
        return None, f"Obteniendo precios Som: {error}"

    tarifa = response.json()
    return insert_prices(conn, tarifa['data'])


__all__ = ["get_prices_Som_indexada", "update_Som_data"]