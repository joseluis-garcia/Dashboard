import sqlite3
from typing import Tuple, Optional, Dict, Any
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz

from dashboard.comun.date_conditions import RangoFechas
from dashboard.comun.load_secrets import load_secrets
from dashboard.comun.sql_utilities import init_db, read_sql_ts
load_secrets(levels_up=3)  # Carga secrets y parchea st.secrets antes de cualquier import

import streamlit as st 

cups =""
pointType = ""
distributorCode = ""

def getToken(userId, password):
    url = "https://datadis.es/nikola-auth/tokens/login";   
    headers = {"Content-Type":"application/x-www-form-urlencoded"}
    data = {"username" : userId, "password" : password}

    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status() 
        return response.text, None
    
    except requests.exceptions.RequestException as e:
        message = f"Request failed: {e}"
        message += f"\nStatus Code: {response.status_code}"
        message += f"\nResponse: {response.text}"  # Debug server response
        return None, message

def getMeters(token):
    global cups
    global distributorCode
    global pointType

    url = "https://datadis.es/api-private/api/get-supplies-v2"
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent" : "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        json = response.json()

        print ("GetMeters json",json)

        cups = json["supplies"][0]["cups"]
        distributorCode = json["supplies"][0]["distributorCode"]
        pointType = json["supplies"][0]["pointType"]
        return None, None

    
    except requests.exceptions.RequestException as e:
        message = f"fetching meters failed: {e}"
        message += f"\nStatus Code: {response.status_code}"
        message += f"\nResponse: {response.text}"  # Debug server response
        return None, message
    
def getPowerMeasurements(token, startDate, endDate):

    # startDate = "2024/01"
    # endDate = startDate
    url = "http://datadis.es/api-private/api/get-consumption-data-v2"
    url = url + "?cups="  + cups
    url = url + "&distributorCode=" + str(distributorCode)
    url = url + "&startDate=" + startDate
    url = url + "&endDate=" + endDate
    url = url + "&measurementType=0"
    url = url + "&pointType=" + str(pointType)

    print ("GetPowerMeasurements url",url)
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent" : "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        #print("GetPowerMeasurements response", response.json())
        response.raise_for_status() 
        return response.json(), None
    
    except requests.exceptions.RequestException as e:
        message = f"fetching power measurements failed:: {e}"
        message += f"\nStatus Code: {response.status_code}"
        message += f"\nResponse: {response.text}"  # Debug server response
        return None, message

def get_DATADIS_data_from_measurements(conn: sqlite3.Connection, rango: Optional[RangoFechas] = None) -> pd.DataFrame:
    """
    Carga datos historicos de DATADIS para entrenar modelos desde SQL.
    Debe devolver columnas: ['datetime', 'consumption_Wh', 'surplus_Wh']
        
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Tupla (dataframe, error) donde:
         
        - dataframe: Index(['datetime', 'consumption_Wh', 'surplus_Wh']
        - error: None si es exitoso, mensaje de error si falla
    """
    try:
        if rango is None:
            query = 'select datetime, consumption_Wh, surplus_Wh from DATADIS where datetime >= ? and datetime <= ? order by datetime'
        else:
            query = f'select datetime, consumption_Wh, surplus_Wh from DATADIS where datetime >= {rango["start_date"]} and datetime <= {rango["end_date"]} order by datetime'

        df = read_sql_ts(query, conn)

        print("Filas con problemas en DATADIS:",df[df.isna().any(axis=1)])
        df = df.dropna(subset=['consumption_Wh', 'surplus_Wh'])
        return df, None
    
    except Exception as e:
        return None, f"Error al cargar datos de ESIOS para previsión precios: {e}"
    
def update_DATADIS_history(conn: Optional[sqlite3.Connection] = None) -> Tuple[
        Optional[pd.DataFrame], 
        Optional[str]]:

    if conn is None:
        # Connect to SQLite database
        conn, error = init_db()
        if error:
            return None, f"Error al conectar a la base de datos: {error}"

    #Previous data recorded until
    df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM DATADIS", conn, parse_dates=["maxDate"])
    df["maxDate"] = pd.to_datetime(df["maxDate"])
    maxDate = df["maxDate"].iloc[0]

    year = maxDate.year
    month = maxDate.strftime("%m")
    startDate = f"{year}/{month}"

    year = int(datetime.today().year)
    month = int(datetime.today().strftime("%m")) - 1
    if month == 0:
        year = year - 1
        month = 12
    month = f"{month:02d}"

    endDate = f"{year}/{month}"
    print("Getting data from DATADIS: " + startDate + " to " + endDate)

    email = st.secrets.get("DATADIS_email")
    password = st.secrets.get("DATADIS_password")
    token, error = getToken(email, password)
    if error:
        print(error)
        return None, error

    meters, error = getMeters(token)
    if error:
        print(error)
        return None, error
    
    print("Meters obtained: " + cups + " - " + str(distributorCode) + " - " + str(pointType))

    measurements, error = getPowerMeasurements(token, startDate, endDate)
    if error:
        print(error)
        return None, error

    df=pd.json_normalize(measurements,'timeCurve')
    print("Obtenido de DATADIS\n", df.head())

    local_tz = pytz.timezone("Europe/Madrid")

    # 1. Combinar date + time en un string y parsear
    df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y/%m/%d %H:%M") - pd.Timedelta(hours=1)  # Ajuste para que el timestamp refleje las horas 0-23 en lugar de 1-24 como vienen

    # 2. Localizar en Europe/Madrid (gestiona DST automáticamente)
    #df["datetime"] = df["datetime"].apply(lambda dt: local_tz.localize(dt))
    df["datetime"] = (
        df["datetime"]
        .dt.tz_localize("Europe/Madrid", ambiguous='infer')  # gestionar DST automáticamente
        .dt.tz_convert("UTC")
    )

    #Conierte unidades a kWh
    df["consumption_Wh"] = df["consumptionKWh"] * 1000
    df["surplus_Wh"] = df["surplusEnergyKWh"] * 1000
    df.drop(columns=["time","cups","consumptionKWh","obtainMethod","surplusEnergyKWh","generationEnergyKWh","selfConsumptionEnergyKWh"], inplace=True)


    df = df[(df["datetime"] > maxDate) & (df["surplus_Wh"].notna())]

    print("A insertar en SQLite\n", df.head(), df.tail())
    # Insert data into the table
    df.to_sql('DATADIS', conn,if_exists="append", index=False)

    return df, None


if __name__ == "__main__":
    df, error = update_DATADIS_history()

    if error is not None:
        print(f"Error: {error}")
    if df is not None:
        desde = df['datetime'].min() #.strftime("%Y-%m-%d %H:%M")
        hasta = df['datetime'].max() #.strftime("%Y-%m-%d %H:%M")
        print(f"{len(df)} filas insertadas en DATADIS desde {desde} hasta {hasta}")

__all__ = [
    "update_DATADIS_history", 
    "getPowerMeasurements",
    "get_DATADIS_data_from_measurements"]