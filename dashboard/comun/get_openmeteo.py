"""
Módulo para obtener datos meteorológicos de Open-Meteo API.

Proporciona funciones para:
- Obtener previsión meteorológica de 7 días
- Filtrar datos meteorológicos por rango de horas
- Crear gráficos interactivos de meteorología
"""

from typing import Tuple, Optional
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import openmeteo_requests
import requests_cache
from retry_requests import retry
import sqlite3
from typing import Tuple, Optional, Dict, Any
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta, timezone

from dashboard.comun import sql_utilities as db
import dashboard.apps.config as TCB

'''
params = {
	"latitude": [40.4165, 41.9831,37.3828],
	"longitude": [-3.7026, 2.8249, -5.9732],
	"hourly": "temperature_2m",
	"models": ["icon_global", "icon_eu"],
}
'''

WEATHER_CODE_SPANISH_ICON = {
    0:  ("Cielo despejado", "☀️"),

    1:  ("Mayormente despejado", "🌤️"),
    2:  ("Parcialmente nublado", "⛅"),
    3:  ("Cubierto", "☁️"),

    45: ("Niebla", "🌫️"),
    48: ("Niebla con escarcha", "🌫️❄️"),

    51: ("Llovizna ligera", "🌦️"),
    53: ("Llovizna moderada", "🌦️"),
    55: ("Llovizna intensa", "🌧️"),

    56: ("Llovizna helada ligera", "🌧️🧊"),
    57: ("Llovizna helada intensa", "🌧️❄️"),

    61: ("Lluvia ligera", "🌦️"),
    63: ("Lluvia moderada", "🌧️"),
    65: ("Lluvia intensa", "🌧️🌧️"),

    66: ("Lluvia helada ligera", "🌧️🧊"),
    67: ("Lluvia helada intensa", "🌧️❄️"),

    71: ("Nieve ligera", "🌨️"),
    73: ("Nieve moderada", "🌨️❄️"),
    75: ("Nieve intensa", "❄️❄️"),

    77: ("Granos de nieve", "🌨️"),

    80: ("Chubascos ligeros", "🌦️"),
    81: ("Chubascos moderados", "🌧️"),
    82: ("Chubascos violentos", "⛈️🌧️"),

    85: ("Chubascos de nieve ligeros", "🌨️"),
    86: ("Chubascos de nieve intensos", "❄️🌨️"),

    95: ("Tormenta", "⛈️"),
    96: ("Tormenta con granizo ligero", "⛈️🌨️"),
    99: ("Tormenta con granizo intenso", "⛈️❄️"),
}

def get_meteo_7D(
    lat: float,
    lon: float,
    azimuth: float
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene previsión meteorológica de 7 días de Open-Meteo.
    
    Obtiene datos horarios de temperatura, nubosidad, código de clima,
    precipitación y radiación directa para los próximos 7 días.
    
    Args:
        lat: Latitud (grados decimales)
        lon: Longitud (grados decimales)
        azimuth: Azimut para radiación solar
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con datos meteorológicos horarios en hora local (index datetime, columnas: temperature, cloud_cover, weather_code, precipitation_probability, direct_radiation)
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df, error = get_meteo_7D(40.4169, -3.7033, 0)
        >>> if not error:
        ...     print(f"Temperatura promedio: {df['temperature'].mean():.1f}°C")
    """
    try:
        # Setup API client con cache y retry
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # URL de la API
        url = "https://api.open-meteo.com/v1/forecast"

        # Parámetros de la solicitud
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "cloud_cover",
                "weather_code",
                "precipitation_probability",
                "global_tilted_irradiance_instant"
            ],
            "timezone": TCB.TIMEZONE_LOCAL,
            "azimuth": azimuth,
            "tilt": 10
        }

        # Realizar solicitud
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Procesar datos horarios
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_cloud_cover = hourly.Variables(1).ValuesAsNumpy()
        hourly_weather_code = hourly.Variables(2).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()
        hourly_direct_radiation = hourly.Variables(4).ValuesAsNumpy()


        # Crear rango de fechas
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(
                    hourly.Time() + response.UtcOffsetSeconds(),
                    unit="s",
                    utc=True
                ),
                end=pd.to_datetime(
                    hourly.TimeEnd() + response.UtcOffsetSeconds(),
                    unit="s",
                    utc=True
                ),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
        }

        # Agregar variables horarias
        hourly_data["temperature"] = hourly_temperature_2m
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["weather_code"] = hourly_weather_code
        hourly_data["precipitation_probability"] = hourly_precipitation_probability
        hourly_data["direct_radiation"] = hourly_direct_radiation

        # Crear DataFrame
        df_hourly = pd.DataFrame(data=hourly_data)
        df_hourly = df_hourly.set_index("date").sort_index()

        return df_hourly, None

    except Exception as e:
        return None, f"Error al obtener datos meteorológicos: {str(e)}"

def get_meteo_hours(
    df_forecast: pd.DataFrame,
    hours: int
) -> pd.DataFrame:
    """
    Filtra datos meteorológicos para un rango de horas a partir de ahora.
    
    Obtiene los datos meteorológicos desde la hora actual hasta N horas
    en el futuro.
    
    Args:
        df_forecast: DataFrame con datos meteorológicos (debe tener columna 'time')
        hours: Número de horas hacia el futuro
        
    Returns:
        DataFrame filtrado con datos para las próximas N horas
        
    Example:
        >>> df_7d, _ = get_meteo_7D(40.4169, -3.7033, 0)
        >>> df_24h = get_meteo_hours(df_7d, 24)
        >>> print(f"Datos para próximas 24h: {len(df_24h)} registros")
    """
    now = pd.Timestamp.now(tz=df_forecast.index.tz)
    df_hours = df_forecast[
        (df_forecast.index >= now) &
        (df_forecast.index <= now + pd.Timedelta(hours=hours))
    ]
    return df_hours

def openmeteo_daily_to_df(response, city_name) -> Dict[str, Any]:
    daily = response.Daily()
    row={"ciudad": city_name}
    hora = datetime.fromtimestamp(daily.Variables(0).ValuesInt64AsNumpy()[0], tz=ZoneInfo("Europe/Madrid"))
    row["sunrise"] = hora.strftime("%H:%M").lstrip("0")
    hora = datetime.fromtimestamp(daily.Variables(1).ValuesInt64AsNumpy()[0], tz=ZoneInfo("Europe/Madrid"))
    row["sunset"] = hora.strftime("%H:%M").lstrip("0")
    row["weather_code"] = daily.Variables(2).ValuesAsNumpy()[0]
    row["temperature_2m_max"] = daily.Variables(3).ValuesAsNumpy()[0]
    row["temperature_2m_min"] = daily.Variables(4).ValuesAsNumpy()[0]
    return row


def get_meteo_today()-> pd.DataFrame:
    """
    Obtiene los datos meteorológicos para el día actual.
    
    Returns:
        DataFrame con los datos meteorológicos para el día actual
        
    Example:
        >>> df_today = get_meteo_today()
        >>> print(f"Datos para hoy: {len(df_today)} registros")
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": [40.4165, 41.9831,37.3828],
        "longitude": [-3.7026, 2.8249, -5.9732],
        "daily": ["sunrise", "sunset", "weather_code", "temperature_2m_max", "temperature_2m_min"],
        "timezone": "Europe/Madrid",
        "forecast_days": 1,
    }
    responses = openmeteo.weather_api(url, params = params)

    cities = ["Madrid", "Girona", "Sevilla"]
    rows = []

    for city, resp in zip(cities, responses):
        rows.append( openmeteo_daily_to_df(resp, city))

    daily_dataframe = pd.DataFrame(rows)
    daily_dataframe["weather_desc"] = daily_dataframe["weather_code"].map(lambda c: WEATHER_CODE_SPANISH_ICON[c][0])
    daily_dataframe["weather_icon"] = daily_dataframe["weather_code"].map(lambda c: WEATHER_CODE_SPANISH_ICON[c][1])

    return daily_dataframe


def update_openmeteo_history(
		conn: Optional[sqlite3.Connection] = None) -> Tuple[
			Optional[pd.DataFrame], 
			Optional[str]]:

    if conn is None:
        # Connect to SQLite database
        conn, error = db.init_db()
        if error:
            return None, f"Error al conectar a la base de datos: {error}"

    #Previous data recorded until
    df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM METEO", conn, parse_dates=["maxDate"])
    df["maxDate"] = pd.to_datetime(df["maxDate"])
    startDate = df["maxDate"].iloc[0] + pd.Timedelta(days=1)
    # Get the current UTC time
    endDate = datetime.now(timezone.utc) + timedelta(days=-1)

    # Convert the datetime object to a string
    strStartDate = startDate.strftime("%Y-%m-%d")
    strEndDate = endDate.strftime("%Y-%m-%d")
	
    params = {
        "latitude": TCB.CASA['lat'],
        "longitude": TCB.CASA['lon'],
        "start_date": strStartDate,
        "end_date": strEndDate,
        "hourly": ["temperature_2m", "precipitation", "cloud_cover", "global_tilted_irradiance_instant"],      
        "timezone": TCB.TIMEZONE_LOCAL,
        "azimuth": TCB.AZIMUTH,
        "tilt": 10
    }

	# Setup the Open-Meteo API client with cache and retry on error
    print(f"Solicitando datos meteorológicos desde {params['start_date']} hasta {params['end_date']}")
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    #openmeteo = openmeteo_requests.Client(session = retry_session)

	# Make sure all required weather variables are listed here
	# The order of variables in hourly or daily is important to assign them correctly below
	
    url = "https://archive-api.open-meteo.com/v1/archive"
    print(f"Solicitando datos meteorológicos desde {params['start_date']} hasta {params['end_date']}")

    responses = openmeteo_requests.Client().weather_api(url, params=params)
    if not responses:
        return None, "No se recibieron datos de Open-Meteo"

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    hourly = response.Hourly()
	  
	# Process hourly data. The order of variables needs to be the same as requested.
    hourly_data = {
        "datetime": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"),
        "temperature": hourly.Variables(0).ValuesAsNumpy(),
        "precipitation": hourly.Variables(1).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(2).ValuesAsNumpy(),
        "direct_radiation": hourly.Variables(3).ValuesAsNumpy()
    }
	
    hourly_df = pd.DataFrame(data = hourly_data)

    hourly_df["datetime"] = (
        pd.to_datetime(hourly_df["datetime"], utc=True)
        .dt.tz_localize(None)
    )

    df = hourly_df.set_index("datetime").sort_index()

    try:
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
        df.to_sql('METEO', conn, if_exists='append', index=True)
        return f"Insertadas {len(df)} filas en METEO desde {df.index.min()} hasta {df.index.max()}", None
	
    except Exception as e:
        return None, f"Error al insertar datos en la base de datos: {e}"

if __name__ == "__main__":
	df, resultado = update_openmeteo_history()

	if resultado is not None:
		print(f"Resultado: {resultado}")

	if df is not None:
		print(f"Datos insertados:\n{df.head()}")
		
__all__ = ["get_meteo_7D", "get_meteo_hours"]
