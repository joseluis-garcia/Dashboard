from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from comun.safe_request import safe_request_get

TZ = ZoneInfo("Europe/Madrid")

def to_utc(dt_local):
    dt_local = dt_local.replace(tzinfo=TZ)
    return dt_local.astimezone(ZoneInfo("UTC"))

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
    df = build_local_series(data)

    # 1. Eliminar precios nulos
    df = df[df["price"].notna()].copy()

    # 2. Convertir a UTC
    df["date_utc"] = df["date_local"].apply(to_utc)

    # 3. Leer última fecha existente en SQLite
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM SOM_precio_indexada")
    row = cur.fetchone()
    last_existing_utc = row[0]

    if last_existing_utc is not None:
        last_existing_utc = datetime.fromisoformat(last_existing_utc)
        df = df[df["date_utc"] > last_existing_utc]

    # 4. Insertar solo los nuevos
    if not df.empty:
        df["date"] = df["date_utc"].astype(str)
        df_to_insert = df[["date", "price"]]
        print("Insertaremos:", df_to_insert)
        df_to_insert.to_sql("SOM_precio_indexada", conn, if_exists="append", index=False)

    return df  # opcional: devolver lo insertado

def update_data( conn):
    url = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"
    response, error = safe_request_get(url)
    if error:
        st.error(f"No se han podido obtener los datos de los precios Som.")
        st.error(error)
        return None, error  # Devuelve un DataFrame vacío en caso de error

    tarifa = response.json()
    insert_prices(conn, tarifa['data'])
