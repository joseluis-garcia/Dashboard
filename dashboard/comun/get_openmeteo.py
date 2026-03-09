"""
Módulo para obtener datos meteorológicos de Open-Meteo API.

Proporciona funciones para obtener y visualizar:
- Previsión meteorológica de 7 días
- Temperatura, nubosidad, precipitación
- Gráficos interactivos de datos meteorológicos
"""

from typing import Tuple, Optional, Dict, Any, List
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
    Crea gráfico de datos meteorológicos.
    
    Genera un gráfico interactivo con:
    - Barras de nubosidad (eje Y izquierdo)
    - Línea de temperatura (eje Y izquierdo)
    - Barras de probabilidad de lluvia (eje Y derecho)
    
    Args:
        df: DataFrame con columnas ['time', 'temperature_2m', 'cloud_cover', 
            'precipitation_probability']
        
    Returns:
        Figura Plotly (go.Figure) con datos meteorológicos
        
    Example:
        >>> df = get_meteo_7D(40.4169, -3.7033, 0)
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

    # Asegurar que temperatura queda por encima de nubosidad
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
    azimuth: float = 0
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene previsión meteorológica de 7 días de Open-Meteo.
    
    Obtiene datos horarios de temperatura, nubosidad, radiación directa
    y probabilidad de precipitación para los próximos 7 días.
    
    Args:
        lat: Latitud de la ubicación (grados decimales)
        lon: Longitud de la ubicación (grados decimales)
        azimuth: Azimut para radiación solar (por defecto 0)
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con datos meteorológicos horarios
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error de API
        
    Example:
        >>> df, error = get_meteo_7D(40.4169, -3.7033)
        >>> if not error:
        ...     print(df.head())
    """
    try:
        # Setup API client con cache y retry
        cache_session = requests_cache.CachedSession(
            '.cache',
            expire_after=3600
        )
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
        hourly_data = {
            "time": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                periods=hourly.Variables(0).ValuesAsNumpy().shape[0],
                freq=pd.DateOffset(hours=1)
            ),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "cloud_cover": hourly.Variables(1).ValuesAsNumpy(),
            "weather_code": hourly.Variables(2).ValuesAsNumpy(),
            "precipitation_probability": hourly.Variables(3).ValuesAsNumpy(),
            "direct_radiation": hourly.Variables(4).ValuesAsNumpy()
        }

        df = pd.DataFrame(hourly_data)
        return df, None

    except Exception as err:
        error = f"Error al obtener datos meteorológicos: {err}"
        return None, error


__all__ = ["get_meteo_7D", "grafica_meteo"]
