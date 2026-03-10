"""
Módulo para obtener datos de producción solar de PVGIS.

Proporciona funciones para:
- Obtener datos históricos de producción solar
- Calcular perfiles de radiación solar diaria
- Visualizar datos solares con gráficos interactivos
"""

from typing import Optional
from datetime import datetime
import os
import base64
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard.comun.date_conditions import getSunData


def load_icon(relative_path: str) -> str:
    """
    Carga un icono PNG desde la carpeta de recursos como base64.
    
    Carga un archivo de imagen PNG desde la ruta relativa y lo codifica
    en base64 para usar en Plotly como fuente de imagen.
    
    Args:
        relative_path: Ruta relativa al archivo desde comun/
                      (ej: "icons/sunrise-dark.png")
        
    Returns:
        String con datos base64 prefijado para usar en Plotly
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        
    Example:
        >>> icon = load_icon("icons/sunrise-dark.png")
    """
    # Directorio donde está este archivo (comun/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, relative_path)
    
    with open(icon_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    
    return "data:image/png;base64," + encoded


def grafico_PVGIS(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    fecha: datetime
) -> go.Figure:
    """
    Crea gráfico de perfil de radiación solar diaria.
    
    Genera un gráfico interactivo con:
    - Línea de potencia solar (promedio histórico)
    - Iconos de salida y puesta del sol
    - Línea vertical de mediodía solar
    - Eje X en horas (0-23)
    
    Args:
        df: DataFrame con columnas ['hora', 'P'] (potencia)
        lat: Latitud de la ubicación (grados decimales)
        lon: Longitud de la ubicación (grados decimales)
        fecha: Fecha para calcular datos solares (datetime)
        
    Returns:
        Figura Plotly (go.Figure)
        
    Example:
        >>> df = pd.DataFrame({'hora': range(24), 'P': [0]*24})
        >>> fig = grafico_PVGIS(df, 40.4169, -3.7033, datetime.now())
        >>> fig.show()
    """
    # Formatear horas como strings
    df["hora"] = df["hora"].apply(lambda h: f"{int(h):02d}")
    
    # Obtener datos del sol
    sun_data = getSunData(lat, lon, fecha, tz_local="Europe/Madrid")
    fig = go.Figure()

    # Convertir horas a números para eje X
    df["hora_num"] = df["hora"].apply(lambda h: int(h[:2]))

    # Línea de potencia solar
    fig.add_trace(
        go.Scatter(
            x=df["hora_num"],
            y=df["P"],
            mode="lines+markers",
            name="Promedio histórico",
            line=dict(color="blue", width=2, shape="spline", smoothing=1.3)
        )
    )

    # Icono de salida del sol (sunrise)
    icon_rise = load_icon("icons/sunrise-dark.png")
    fig.add_layout_image(
        dict(
            source=icon_rise,
            x=sun_data["sunrise"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    # Línea vertical de mediodía solar con icono
    icon_noon = load_icon("icons/10000_clear_small.png")
    fig.add_vline(
        x=sun_data["noon"],
        line_width=2,
        line_dash="dash",
        line_color="green",
        name="Mediodía"
    )
    fig.add_layout_image(
        dict(
            source=icon_noon,
            x=sun_data["noon"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    # Icono de puesta del sol (sunset)
    icon_set = load_icon("icons/sunset-dark.png")
    fig.add_layout_image(
        dict(
            source=icon_set,
            x=sun_data["sunset"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    # Configuración del eje X
    fig.update_xaxes(
        range=[0, 23],
        dtick=1
    )

    # Layout general
    fig.update_layout(
        title="Curva promedio de potencia por kWp instalado para hoy",
        xaxis_title="Hora del día",
        yaxis_title="Potencia pico (kW)",
        template="plotly_white",
        xaxis=dict(dtick=1, showgrid=True),
        yaxis=dict(showgrid=True)
    )

    return fig


@st.cache_data
def get_PVGIS_data(
    lat: float,
    lon: float,
    fecha: datetime
) -> pd.DataFrame:
    """
    Obtiene datos de producción solar histórica de PVGIS.
    
    Obtiene datos horarios de irradiancia y potencia solar histórica
    de PVGIS (v5.3) y filtra solo el día especificado.
    
    Args:
        lat: Latitud de la ubicación (grados decimales)
        lon: Longitud de la ubicación (grados decimales)
        fecha: Fecha para filtrar datos (datetime)
        
    Returns:
        DataFrame con datos horarios del día especificado
        
    Raises:
        requests.exceptions.HTTPError: Si la solicitud a PVGIS falla
        
    Example:
        >>> df = get_PVGIS_data(40.4169, -3.7033, datetime(2026, 3, 10))
        >>> print(df.head())
    """
    # URL de PVGIS v5.3
    base_url = (
        f"https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?"
        f"&pvcalculation=1&peakpower=1&outputformat=json"
        f"&startyear=2018&loss=14&lat={lat}&lon={lon}"
    )

    # Realizar solicitud
    r = requests.get(base_url)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data["outputs"]["hourly"])

    # Convertir time a datetime UTC
    df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", utc=True)

    # Convertir a hora local (Europe/Madrid)
    df["time_local"] = df["time"].dt.tz_convert("Europe/Madrid")
    df["mes"] = df["time_local"].dt.month
    df["dia"] = df["time_local"].dt.day
    df["hora"] = df["time_local"].dt.hour

    # Agrupar por mes, día, hora y calcular promedio de potencia
    df_prom = df.groupby(["mes", "dia", "hora"], as_index=False)["P"].mean()

    # Obtener mes y día de la fecha especificada
    mes_fecha = fecha.month
    dia_fecha = fecha.day

    # Filtrar solo para el día especificado
    perfil_dia = df_prom[
        (df_prom["mes"] == mes_fecha) &
        (df_prom["dia"] == dia_fecha)
    ].sort_values("hora")

    return perfil_dia


__all__ = ["load_icon", "grafico_PVGIS", "get_PVGIS_data"]
