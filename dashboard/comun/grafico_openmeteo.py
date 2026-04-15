"""
Módulo para graficar datos meteorológicos de Open-Meteo API.

Proporciona funciones para:
- Crear gráficos interactivos de meteorología
"""

from typing import Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.comun.get_openmeteo import get_meteo_7D, get_meteo_hours

def grafica_openmeteo( 
    lat: float,
    lon: float,
    azimuth: float,
    time_unit: Optional[int] = None
) -> Tuple[Optional[go.Figure], Optional[str]]:
    """
    Crea gráfico interactivo de datos meteorológicos. La primera vez que se llama cachea los datos de 7 dias para la ubicación dada y los reutiliza en llamadas posteriores con los mismos parámetros de latitud, longitud y azimut. Si se especifica time_unit, filtra los datos para mostrar solo las próximas horas indicadas. Si cambian los parámetros de latitud, longitud o azimut se recarga la previsión de 7 días para la nueva ubicación y orientación.
    
    Genera un gráfico con:
    - Barras de nubosidad (eje Y derecho, %)
    - Línea de temperatura (eje Y izquierdo, °C)
    - Barras de probabilidad de lluvia (eje Y derecho, %)
    
    Args:
        lat: Latitud (grados decimales)
        lon: Longitud (grados decimales)
        azimuth: Azimut para radiación solar
        time_unit: Número de horas para filtrar los datos. Si None se grafican 7 dias completos.
        
    Returns:
        Figura Plotly (go.Figure)
        error si lo hubiera
        
    Example:
        >>> fig, error = grafica_meteo() grafica con datos de 7 días
        >>> fig, error = grafica_meteo(24) grafica con datos de las próximas 24 horas
        >>> fig.show()
    """
    cache_key = {lat,lon,azimuth}
    if (not hasattr(grafica_openmeteo, "df_cache") or 
        grafica_openmeteo.df_cache is None or 
        grafica_openmeteo.cache_key != cache_key):
        grafica_openmeteo.df_cache, error = get_meteo_7D(lat, lon, azimuth)
        if error:
            return None, f"grafica_openmeteo: {error}"
        grafica_openmeteo.cache_key = cache_key

    df = grafica_openmeteo.df_cache
    
    if time_unit is not None:
        df = get_meteo_hours(df, time_unit)

    # Obtener datos meteorológicos
    # Crear figura con doble eje Y
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )

    # Barras de nubosidad
    fig.add_trace(
        go.Bar(
            x=df.index,
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
            x=df.index,
            y=df["temperature"],
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
            x=df.index,
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

    return fig, None


__all__ = ["grafica_openmeteo"]
