import streamlit as st
import openmeteo_requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests_cache
from retry_requests import retry

@st.cache_data
def grafica_meteo(df):
# --------------------------------------------------------- 
# Crear figura con doble eje Y correctamente
# --------------------------------------------------------- 
    fig = make_subplots( rows=1, cols=1, specs=[[{"secondary_y": True}]] )

    # Línea de nubosidad
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cloud_cover"],
            width=60*60*1000, # 👈 1 hora en ms → barras pegadas y visibles
            name="Nubosidad (%)",
            marker_color="rgba(150,150,150,0.25)",
            yaxis="y2"
        )
    )

    # Línea de temperatura
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["temperature_2m"],
            mode="lines",
            name="Temperatura (°C)",
            line=dict(color="tomato", width=2, shape="spline", smoothing=1.3),
        )
    )
    # Asegurar que queda por encima del cloudcover 
    fig.data[-1].update(zorder=10)

    # --- Probabilidad de lluvia (barras) --- 
    fig.add_trace( 
        go.Bar( 
            x=df["time"], 
            y=df["precipitation_probability"], 
            name="Prob. lluvia (%)", 
            marker_color="#00a000",
            yaxis="y2" 
        )
    )

    # Configuración de ejes
    # Eje izquierdo (temperatura)
    fig.update_yaxes(
        title_text="Temperatura (°C)",
        showgrid=True,
        zeroline=False,
        secondary_y=False
    )

    # Eje derecho (porcentajes: cloudcover, precipitación, etc.)
    fig.update_yaxes(
        title_text="%",
        showgrid=False,          # evitamos grid duplicado
        zeroline=False,
        secondary_y=True,
        overlaying="y",          # 👈 superpone el eje derecho sobre el izquierdo
    )

    fig.update_layout(
        xaxis=dict(title="Fecha y hora"),
        legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"),
        hovermode="x unified",
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=True,
        height=400,
    )

    fig.update_xaxes( 
        showgrid=True, 
        gridcolor="rgba(255,255,255,0.15)")

    return fig

def get_meteo_7D(lat, lon, azimuth):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "cloud_cover", "weather_code", "precipitation_probability", "direct_radiation"],
        "timezone": "auto",
        "azimuth": azimuth,
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
    except Exception as e:
        return None, str(e)  # Devuelve un DataFrame vacío en caso de error

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    # print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    # print(f"Elevation: {response.Elevation()} m asl")
    # print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
    # print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_cloud_cover = hourly.Variables(1).ValuesAsNumpy()
    hourly_weather_code = hourly.Variables(2).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()
    hourly_direct_radiation = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time() + response.UtcOffsetSeconds(), unit = "s", utc = True),
        end =  pd.to_datetime(hourly.TimeEnd() + response.UtcOffsetSeconds(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["cloud_cover"] = hourly_cloud_cover
    hourly_data["weather_code"] = hourly_weather_code
    hourly_data["precipitation_probability"] = hourly_precipitation_probability
    hourly_data["direct_radiation"] = hourly_direct_radiation

    hourly_dataframe = pd.DataFrame(data = hourly_data)

    df = hourly_dataframe
    df["time"] = pd.to_datetime(df["date"])
    return df, None

def get_meteo_hours(df_forecast, hours):
    now = pd.Timestamp.now(tz=df_forecast['time'].dt.tz)
    df_hours = df_forecast[(df_forecast['time'] >= now) &
                 (df_forecast['time'] <= now + pd.Timedelta(hours=hours))]
    return df_hours