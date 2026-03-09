"""
Módulo para obtener datos de producción solar de PVGIS.

Proporciona funciones para:
- Obtener datos históricos de producción solar
- Calcular perfiles de radiación solar
- Visualizar datos solares con gráficos interactivos
"""

from typing import Tuple, Optional, Dict, Any
from datetime import datetime
import os
import base64
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard.comun.date_conditions import getSunData, Coord


def load_icon(relative_path: str) -> str:
    """
    Carga un icono PNG desde la carpeta de recursos y lo convierte a base64.
    
    Carga un archivo de imagen PNG desde la ruta relativa y lo codifica
    en base64 para usar en Plotly como fuente de imagen.
    
    Args:
        relative_path: Ruta relativa al archivo de imagen desde comun/
                      (ej: "icons/sunrise-dark.png")
        
    Returns:
        String con datos base64 prefijado con "data:image/png;base64,"
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        IOError: Si hay error al leer el archivo
        
    Example:
        >>> icon = load_icon("icons/sunrise-dark.png")
        >>> # icon es ahora una cadena que puede usarse en Plotly
    """
    # Directorio donde está este archivo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Ruta completa al icono
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
        Figura Plotly (go.Figure) con perfil de radiación solar
        
    Example:
        >>> df = pd.DataFrame({
        ...     'hora': ['00', '01', ..., '23'],
        ...     'P': [0, 0, ..., 0]
        ... })
        >>> fig = grafico_PVGIS(df, 40.4169, -3.7033, datetime(2026, 3, 10))
        >>> fig.show()
    """
    # Formatear horas como strings
    df["hora"] = df["hora"].apply(lambda h: f"{int(h):02d}")
    
    # Crear lista de horas completas (00-23)
    horas_completas = [f"{h:02d}" for h in range(24)]

    # Obtener datos del sol
    sun_data = getSunData(lat, lon, fecha, tz_local="Europe/Madrid")
    
    # Crear figura
    fig = go.Figure()

    # Convertir horas a números para el eje X
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
        dtick=1,  # Marcar cada hora
        title_text="Hora del día"
    )

    # Configuración del eje Y
    fig.update_yaxes(
        title_text="Potencia (W/m²)"
    )

    # Layout general
    fig.update_layout(
        title=f"Perfil de radiación solar - {fecha.strftime('%d/%m/%Y')}",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=30, b=0),
        autosize=True,
        height=400
    )

    return fig


def get_PVGIS_data(
    lat: float,
    lon: float,
    fecha: datetime,
    perc: int = 10
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene datos de producción solar histórica de PVGIS.
    
    Obtiene valores horarios de irradiancia y potencia solar para
    una ubicación y fecha especificadas usando la API de PVGIS.
    
    Args:
        lat: Latitud de la ubicación (grados decimales)
        lon: Longitud de la ubicación (grados decimales)
        fecha: Fecha para la cual obtener datos (datetime)
        perc: Percentil de confianza (por defecto 10, rango 1-99)
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con datos horarios de radiación
        - error: None si es exitoso, mensaje de error si falla
        
    Raises:
        Exception: Se captura cualquier error de API
        
    Example:
        >>> df, error = get_PVGIS_data(40.4169, -3.7033, datetime(2026, 3, 10))
        >>> if not error:
        ...     print(df.head())
    """
    try:
        # Formato de fecha para PVGIS: YYYY-MM-DD
        fecha_str = fecha.strftime("%Y-%m-%d")
        
        # URL de la API de PVGIS
        url = (
            f"https://re.jrc.ec.europa.eu/api/v5_2/solardata?"
            f"lat={lat}&lon={lon}&date={fecha_str}&outputformat=json&perc={perc}"
        )
        
        # Realizar solicitud
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extraer datos horarios
        if "outputs" not in data or "hourly" not in data["outputs"]:
            return None, "No se encontraron datos en la respuesta"
        
        hourly_data = data["outputs"]["hourly"]
        
        # Crear DataFrame
        df = pd.DataFrame(hourly_data)
        
        return df, None
        
    except requests.exceptions.Timeout:
        return None, "Timeout: API de PVGIS tardó demasiado en responder"
    except requests.exceptions.HTTPError as e:
        return None, f"Error HTTP en PVGIS: {e.response.status_code}"
    except Exception as err:
        return None, f"Error al obtener datos de PVGIS: {err}"


__all__ = ["get_PVGIS_data", "grafico_PVGIS", "load_icon"]
