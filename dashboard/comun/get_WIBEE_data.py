"""
Módulo para obtener datos historicos y actuales de WIBEE asi como actualizar measurments.db a partir de la url de WIBEE:
 https://nest.wibeee.com/api/auth/3/buildings/35331/meters/56860/channels/3/data?param=P&start=2025-03-17T23:00:00Z&end=2025-03-18T22:59:59Z&time_unit=hourstime,General,Solar,Aerotermia

Proporciona funciones
- getToken: Obtiene el token de autenticación de WIBEE a partir del email y password almacenados en Streamlit secrets 
- getBuildings: Obtiene el ID del edificio registrado en WIBEE asociado al token de autenticación
- getMeters: Obtiene el ID del medidor y los canales asociados al edificio registrado en WIBEE
- getPowerMeasurements: Obtiene las mediciones de potencia para cada canal del medidor registrado en WIBEE en un rango de fechas especificado
- update_WIBEE_data: Actualiza la tabla WIBEE con los datos de producción de energía desde la última fecha registrada hasta la fecha actual
"""
from dbm import sqlite3
from typing import Tuple, Optional, Dict, Any
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone, time
import pytz
import json
from dashboard.comun.date_conditions import RangoFechas
from dashboard.comun.sql_utilities import read_sql_ts
from dashboard.comun.sql_utilities import read_sql_ts

import dashboard.apps.config as TCB


def UTC_to_str( utc_string):

    # Parse the string into a datetime object
    datetime_obj = datetime.strptime(utc_string, "%Y-%m-%dT%H:%M:%SZ")

    # Convert the datetime object back to a string without "T" and "Z"
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

def getToken() -> bool:
    global userId 
    global token
    #Use the login function
    email = st.secrets["WIBEE_email"]
    password = st.secrets["WIBEE_password"]

    url = "https://nest.wibeee.com/api/4/users/login"
    headers_token = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent" : "Mozilla/5.0"
    }
    data = json.dumps({"email" : email, "password" : password})

    try:
        response = requests.post(url, data=data, headers=headers_token)
        if response.status_code != 200:
            raise Exception('Request error', response)
        response.raise_for_status() 
        tmp = response.json()['user']
        token = tmp['token']
        userId = tmp['id']
        return True
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return False

def getBuildings() -> bool:
    global buildingId
    global headers
    url = f"https://nest.wibeee.com/api/auth/3/users/{userId}/buildings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        json = response.json()
        buildingId = json[0]["id"]
        return True
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return False

def getMeters() -> bool:

    global meterId
    global channels

    url = f"https://nest.wibeee.com/api/auth/3/buildings/{buildingId}/meters"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        json = response.json()
            
        meterId = json[0]["meter"]["id"]
        channels = json[0]["channels"]
        return True
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return False

def getPowerMeasurements (rango: RangoFechas, time_unit: Optional[str] = "hours") -> bool:
    try:
        for channel in channels:
            url = f"https://nest.wibeee.com/api/auth/3/buildings/{buildingId}/meters/{meterId}/channels/{channel['channel_id']}/data?param=P&start={rango['start_date']}&end={rango['end_date']}&time_unit={time_unit}"

            response = requests.get(url, headers=headers)
            response.raise_for_status() 
            data = response.json()
            channel["data"] = data["data"]
        return True
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("\nStatus Code:", response.status_code)
        print("\nResponse:", response.text)  # Debug server response
        return False
    
def init_WIBEE_data() -> bool:
    if getToken():
        if getBuildings():
            if getMeters():
                return True
    return False

def get_WIBEE_data(rango: RangoFechas, time_unit: Optional[str] = "hours")-> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene los datos de producción de energía de WIBEE en un rango de fechas especificado y devuelve un DataFrame con los resultados.
    Args:
        rango: Un diccionario con las claves 'start_date' y 'end_date' que contienen las fechas de inicio y fin en formato ISO 8601 (ejemplo: '2025-03-17T23:00:00Z').
    Returns:
        Un tuple con dos elementos:
        - Un DataFrame con los datos de producción de energía obtenidos de WIBEE, o None si ocurrió un error.
        - Un mensaje de error en caso de que ocurra un error, o None si la operación fue exitosa.
    Ejemplo de uso:
        rango = {
            'start_date': '2025-03-17T23:00:00Z',
            'end_date': '2025-03-18T22:59:59Z'
        }
        df, error = get_WIBEE_data(rango)
        if error:
            print("Error al obtener datos de WIBEE:", error)
        else:
            print(df.head())
    """

    if not init_WIBEE_data():
        return None, "Error initializing WIBEE connection"

    if not getPowerMeasurements(rango, time_unit):
        return None, "Error getting power measurements from WIBEE"
    
    try:
        result = pd.DataFrame()
        for channel in channels:
            # Convert each array to a DataFrame
            df = pd.DataFrame(
                {'datetime': channel['data']['time'], 
                f"{channel['description']}" : channel['data']['P']})
            if result.empty:
                result = df
            else:
                # Merge the DataFrames on the 'date' column
                result = pd.merge(result, df, on="datetime", how="outer")

        result = result.rename(columns={
            'Aerotermia': 'extra_Wh',
            'General': 'general_Wh',
            'Solar': 'solar_Wh'
        })
        result['extra_Wh'] = result['extra_Wh'].abs()
        result['extra'] = 'AEROTERMIA'
        result['power_Wp'] = TCB.CURRENT_PEAK_POWER

        result["datetime"] = pd.to_datetime(result["datetime"], utc=True).dt.tz_localize(None)
        result = result.set_index("datetime")
        return result, None
    except Exception as e:
        return None, f"Error al obtener datos de WIBEE: {e}"

def update_WIBEE_history(conn: sqlite3.Connection) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    try:
        #Previous data recorded until
        df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM WIBEE", conn, parse_dates=["maxDate"])
        df["maxDate"] = pd.to_datetime(df["maxDate"])
        startDate = df["maxDate"].iloc[0] + timedelta(hours=1)
        strStartDate = startDate.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Get the current UTC time
        endDate = datetime.now(timezone.utc) + timedelta(hours=-1)
        # Convert the datetime object to a string
        strEndDate = endDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    
        rango = {
            'start_date': strStartDate,
            'end_date': strEndDate
        }
        result, error = get_WIBEE_data(rango)
        if error:
            return None, error
        
        result.to_sql('WIBEE', conn, if_exists='append', index=True, index_label='datetime' )
        return f"Insertadas {len(result)} en WIBEE", None

    except Exception as e:
        return None,f"Error getting WIBEE data:{str(e)}"

def get_WIBEE_today() -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    local_tz = pytz.timezone("Europe/Madrid")
    utc_tz = pytz.utc
    today = datetime.now(local_tz).date()

    start_date = local_tz.localize(datetime.combine(today, time.min))
    end_date   = local_tz.localize(datetime.combine(today, time(23, 59, 59)))

    start_date = start_date.astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date   = end_date.astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    rango = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    #print(f"Obteniendo datos de WIBEE para hoy: {rango['start_date']} - {rango['end_date']}")
    result, error = get_WIBEE_data(rango, time_unit="quarter")
    if error:
        return None, error

    #print(f"Datos de WIBEE obtenidos para hoy: {len(result)} registros\n")
    return result, None
    
def get_WIBEE_today_history(conn: sqlite3.Connection) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    local_tz = pytz.timezone("Europe/Madrid")
    today = datetime.now(local_tz).strftime("%m-%d")

    query = "SELECT datetime, solar_Wh from WIBEE order by datetime"
    df, error = read_sql_ts(query, conn)
    if error:
        return None, f"get_WIBEE_today_history: {error}"
    
    # Convertir UTC a hora local
    df.index = df.index.tz_convert("Europe/Madrid")

    # Nos quedamos con el promedio de todos los mismos dias de los años cargados
    mask = df.index.strftime("%m-%d") == today
    df = df[mask].groupby(df.index[mask].hour).agg({"solar_Wh": "mean"})

    return df, None
    
__all__ = ["update_WIBEE_history", "get_WIBEE_today", "get_WIBEE_today_history"]