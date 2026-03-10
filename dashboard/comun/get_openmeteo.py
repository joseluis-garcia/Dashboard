"""
Módulo para obtener datos meteorológicos de Open-Meteo API.

Proporciona funciones para:
- Obtener previsión meteorológica de 7 días
- Filtrar datos meteorológicos por rango de horas
- Crear gráficos interactivos de meteorología
"""

from typing import Tuple, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import openmeteo_requests
import requests_cache
from retry_requests import retry


@st.cache_data
def grafica_meteo(df: pd.DataFrame) -> go.Figure:
    """
    Crea gráfico interactivo de datos meteorológicos.
    
    Genera un gráfico con:
    - Barras de nubosidad (eje Y derecho, %)
    - Línea de temperatura (eje Y izquierdo, °C)
    - Barras de probabilidad de lluvia (eje Y derecho, %)
    
    Args:
        df: DataFrame con columnas ['time', 'temperature_2m', 'cloud_cover', 
            'precipitation_probability']
        
    Returns:
        Figura Plotly (go.Figure)
        
    Example:
        >>> df, _ = get_meteo_7D(40.4169, -3.7033, 0)
        >>> fig = grafica_meteo(df)
        >>> fig.show()
    """
    # Crear figura con doble eje Y
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )

    # Barras de nubosidad
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cloud_cover"],
            width=60 * 60 * 1000,  # 1 hora en ms
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
            line=dict(color="tomato", width=2, shape="spline", smoothing=1.3)
        )
    )

    # Asegurar que la temperatura queda por encima de nubosidad
    fig.data[-1].update(zorder=10)

    # Barras de probabilidad de lluvia
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
    fig.update_yaxes(
        title_text="Temperatura (°C)",
        showgrid=True,
        zeroline=False,
        secondary_y=False
    )

    fig.update_yaxes(
        title_text="%",
        showgrid=False,
        zeroline=False,
        secondary_y=True,
        overlaying="y"
    )

    fig.update_layout(
        xaxis=dict(title="Fecha y hora"),
        legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"),
        hovermode="x unified",
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=True,
        height=400
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.15)"
    )

    return fig


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
        - dataframe: DataFrame con datos meteorológicos horarios
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df, error = get_meteo_7D(40.4169, -3.7033, 0)
        >>> if not error:
        ...     print(f"Temperatura promedio: {df['temperature_2m'].mean():.1f}°C")
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
                "direct_radiation"
            ],
            "timezone": "UTC",
            "azimuth": azimuth
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
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["weather_code"] = hourly_weather_code
        hourly_data["precipitation_probability"] = hourly_precipitation_probability
        hourly_data["direct_radiation"] = hourly_direct_radiation

        # Crear DataFrame
        hourly_dataframe = pd.DataFrame(data=hourly_data)
        hourly_dataframe["time"] = pd.to_datetime(hourly_dataframe["date"])

        return hourly_dataframe, None

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
    now = pd.Timestamp.now(tz=df_forecast['time'].dt.tz)
    df_hours = df_forecast[
        (df_forecast['time'] >= now) &
        (df_forecast['time'] <= now + pd.Timedelta(hours=hours))
    ]
    return df_hours


__all__ = ["get_meteo_7D", "get_meteo_hours", "grafica_meteo"]
