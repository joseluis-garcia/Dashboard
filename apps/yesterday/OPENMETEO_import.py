import sys
from pathlib import Path

import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Añadir la raíz del repo al PYTHONPATH
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

import comun.sql_utilities as db

# Connect to SQLite database
conn, error = db.init_db()
if error:
    print(error)
    SystemExit

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
params = {
	"latitude": 40.5656,
	"longitude": -3.8998,
	"start_date": "2022-01-01",
	"end_date": "2026-02-28",
	"hourly": ["temperature_2m", "precipitation", "cloud_cover", "global_tilted_irradiance_instant"],      
    "timezone": "auto",
    "azimuth": -45,
    "tilt": 10
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]
print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
hourly_cloud_cover = hourly.Variables(2).ValuesAsNumpy()
hourly_global_tilted_irradiance_instant = hourly.Variables(3).ValuesAsNumpy()

hourly_data = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}
hourly_data["temperature"] = hourly_temperature_2m
hourly_data["precipitation"] = hourly_precipitation
hourly_data["cloud_cover"] = hourly_cloud_cover
hourly_data["direct_radiation"] = hourly_global_tilted_irradiance_instant

hourly_df = pd.DataFrame(data = hourly_data)
hourly_df["datetime"] = (
    pd.to_datetime(hourly_df["date"], utc=True)
      .dt.tz_localize(None)
)
df = hourly_df.set_index("date").sort_index()

# Create the table if it doesn't exist
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS METEO (
	datetime DATE,
	temperature REAL,
	cloud_cover REAL,
	precipitation REAL,
	direct_radiation REAL
)
''')

conn.commit()

# Insert data into the table
df.to_sql('METEO', conn, if_exists='append', index=False)

# Commit changes and close connection

# conn.close()
