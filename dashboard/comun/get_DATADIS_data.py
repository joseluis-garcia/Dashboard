import streamlit as st

import pandas as pd
import sqlite3
import requests
from datetime import datetime, timedelta
import pytz

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

        print (json)

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

    print (url )
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent" : "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        print(response)
        response.raise_for_status() 
        return response.json(), None
    
    except requests.exceptions.RequestException as e:
        message = f"fetching power measurements failed:: {e}"
        message += f"\nStatus Code: {response.status_code}"
        message += f"\nResponse: {response.text}"  # Debug server response
        return None, message

# Function to convert time format. Hour 24:00 has to be replced by next day 00:00
def format_utc_time(row):
    local_datetime_str = row['date'] + ' ' + row['time']
    if (row['time'] == '24:00'):
        date_obj = datetime.strptime(row['date'], '%Y/%m/%d') + timedelta(days=1)
        local_datetime_str = date_obj.strftime("%Y/%m/%d") + ' 00:00'

    local_datetime = datetime.strptime(local_datetime_str, "%Y/%m/%d %H:%M")  
    local_timezone = pytz.timezone('Europe/Madrid')

    # Localize the datetime object (add the local timezone)
    localized_datetime = local_timezone.localize(local_datetime)

    # Convert the localized datetime to UTC
    utc_datetime = localized_datetime.astimezone(pytz.utc)
    return utc_datetime.replace(tzinfo=None)
 
def upodate_DATADIS_data(conn):

    # Load the table into a Pandas DataFrame

    #Previous data recorded until
    df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM DATADIS_v", conn, parse_dates=["maxDate"])
    df["maxDate"] = pd.to_datetime(df["maxDate"])
    maxDate = df["maxDate"].iloc[0]

    year = maxDate.year
    month = maxDate.strftime("%m")
    startDate = f"{year}/{month}"
    print (startDate )

    year = int(datetime.today().year)
    month = int(datetime.today().strftime("%m")) - 1
    if month == 0:
        year = year - 1
        month = 12
    month = f"{month:02d}"

    endDate = f"{year}/{month}"
    print(endDate)

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
    df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y/%m/%d %H:%M")

    # 2. Localizar en Europe/Madrid (gestiona DST automáticamente)
    df["datetime"] = df["datetime"].apply(lambda dt: local_tz.localize(dt))

    # 3. Convertir a UTC
    df["datetime"] = df["datetime"].dt.tz_convert("UTC")

    # 4. Quitar el tzinfo y formatear como string para SQLite (sin +00:00)
    df["datetime"] = df["datetime"].dt.tz_localize(None)


    #df["date"] = df.apply(format_utc_time, axis=1)
    df["consumption_Wh"] = df["consumptionKWh"] * 1000
    df["surplus_Wh"] = df["surplusEnergyKWh"] * 1000
    df.drop(columns=["time","cups","consumptionKWh","obtainMethod","surplusEnergyKWh","generationEnergyKWh","selfConsumptionEnergyKWh"], inplace=True)

        #if df.isna().any().any():
    if (True):
        # print( "Abort -> dataset with NANs")
        # print(df[df.isna().any(axis=1)])
    #else:
        df = df[(df["datetime"] > maxDate) & (df["surplus_Wh"].notna())]
        df = df[df['datetime'] > maxDate]
        print("A insertar en SQLite\n", df.head())
        # Insert data into the table
        # df.to_sql('DATADIS_v', conn,if_exists="append", index=False)

        # # Commit changes and close connection
        # conn.commit()
        # conn.close()

        print("Data successfully inserted into SQLite from DATADIS!")
        return "Data successfully inserted into SQLite from DATADIS!", None
    else:
        print("Some error getting values from DATADIS") 
        return None, "Some error getting values from DATADIS" 
