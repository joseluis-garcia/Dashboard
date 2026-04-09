import pandas as pd
import requests
from datetime import datetime

# Añadir la raíz del repo al PYTHONPATH
from dashboard.comun import sql_utilities as db

# URL to fetch the CSV data
url = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?&pvcalculation=1&peakpower=1&outputformat=json&lat=40.5656&lon=-3.8998&loss=20&angle=10&aspect=-44&pvtechchoice=crystSi"

# Function to convert time format (assuming UTC already)
def format_utc_time(raw_time):
    dt = datetime.strptime(raw_time, "%Y%m%d:%H%M")  # Convert string to datetime
    return dt.strftime("%Y-%m-%d %H:00:00") 

# Fetch the data from the server
try:
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception('Request error', response)
    data = response.json()

    df = pd.json_normalize(data['outputs'], "hourly")

    df["datetime"] = df["time"].apply(format_utc_time)
    df["power_Wh"] = df["P"]
    df["irradiance"] = df["G(i)"]
    df["sun"] = df["H_sun"]
    df["temperature"] = df["T2m"]
    df["WS10m"] = df["WS10m"]
    df["interval"] = df["Int"]
    df.drop(columns=["time","P","G(i)","H_sun","T2m","WS10m","Int"], inplace=True)

    # Connect to SQLite database
    conn, error = db.init_db()

    # Create the table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PVGIS (
        datetime DATE,
        power_Wh REAL,
        irradiance REAL,
        sun REAL,
        temperature REAL,
        interval REAL
    )
    ''')

    # Insert data into the table
    df.to_sql('PVGIS', conn, if_exists='replace', index=False)

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("Data successfully inserted into SQLite PVGIS_v from PVGIS!")

except Exception as err:
    print(f"Error from PVGIS import {err=}, {type(err)=}")
