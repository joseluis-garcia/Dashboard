#https://nest.wibeee.com/api/auth/3/buildings/35331/meters/56860/channels/3/data?param=P&start=2025-03-17T23:00:00Z&end=2025-03-18T22:59:59Z&time_unit=hourstime,General,Solar,Aerotermia
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import json

def UTC_to_str( utc_string):

    # Parse the string into a datetime object
    datetime_obj = datetime.strptime(utc_string, "%Y-%m-%dT%H:%M:%SZ")

    # Convert the datetime object back to a string without "T" and "Z"
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

def getToken():
    global userId 
    global token
    #Use the login function
    email = st.secrets["WIBEE_email"]
    #email = "joseluis@garciagruben.org"
    password = st.secrets["WIBEE_password"]
    #password = "P3nascal3s"

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
        return
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return None

def getBuildings():
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
        return
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return None

def getMeters():

    global meterId
    global channels

    url = f"https://nest.wibeee.com/api/auth/3/buildings/{buildingId}/meters"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        json = response.json()
            
        meterId = json[0]["meter"]["id"]
        channels = json[0]["channels"]
        return
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        print("Status Code:", response.status_code)
        print("Response:", response.text)  # Debug server response
        return None

def getPowerMeasurements ( startDate, endDate):

    try:
        for channel in channels:
            url = f"https://nest.wibeee.com/api/auth/3/buildings/{buildingId}/meters/{meterId}/channels/{channel['channel_id']}/data?param=P&start={startDate}&end={endDate}&time_unit=hours"

            #print(url + "\n")

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

def update_WIBEE_data(conn ):

    getToken()
    #print (token)
    getBuildings()
    #print (buildingId)
    getMeters()
    #print (meterId)
    #print (channels)

# Load the table into a Pandas DataFrame
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

        if getPowerMeasurements(strStartDate, strEndDate):
            result = pd.DataFrame()
            for channel in channels:
                # Convert each array to a DataFrame
                df = pd.DataFrame(
                    {'date': channel['data']['time'], 
                    f"{channel['description']}" : channel['data']['P']})
                if result.empty:
                    result = df
                else:
                    # Merge the DataFrames on the 'date' column
                    result = pd.merge(result, df, on="date", how="outer")

            # Sort by date
            result = result.sort_values(by="date")
            result = result.rename(columns={
                'Aerotermia': 'extra_Wh',
                'General': 'general_Wh',
                'Solar': 'solar_Wh'
            })
            result['extra_Wh'] = result['extra_Wh'].abs()
            result['extra'] = 'AEROTERMIA'
            result['power_Wp'] = 6.6
            result['datetime'] = result['date'].apply(UTC_to_str)
            result = result.drop(columns=['date'])
            result.to_sql('WIBEE', conn, if_exists='append', index=False )
            
            # Commit changes and close connection
            conn.commit()
            return None
        else:
            return "No data returned from WIBEE"
    except Exception as e:
        return f"Error getting WIBEE data:{str(e)}"

