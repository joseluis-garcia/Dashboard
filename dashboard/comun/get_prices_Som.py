"""
Módulo para obtener y visualizar precios de SOM Energía.

Proporciona funciones para:
- Obtener precios de hoy y mañana de SOM Energía
- Crear gráficos interactivos de precios por hora
- Mostrar comparativa de precios hoy vs mañana
"""

from typing import Tuple, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard.comun.safe_request import safe_request_get


@st.cache_data
def grafico_prices_Som(df: pd.DataFrame) -> go.Figure:
    """
    Crea gráfico interactivo de precios de SOM Energía.
    
    Muestra:
    - Barras de precios de hoy (coloreadas por rango)
    - Líneas verticales de precios de mañana
    - Puntos marcadores para mañana
    
    Colores:
    - Verde: < 0.1 €/kWh (muy barato)
    - Amarillo: < 0.2 €/kWh (barato)
    - Rojo: >= 0.2 €/kWh (caro)
    - Gris: valores faltantes (NaN)
    
    Args:
        df: DataFrame con columnas ['hora', 'hoy', 'mañana']
        
    Returns:
        Figura Plotly (go.Figure)
        
    Example:
        >>> df, _ = get_prices_Som()
        >>> fig = grafico_prices_Som(df)
        >>> fig.show()
    """
    # Mapear colores según precio para hoy
    colors = [
        "#CCCCCC" if pd.isna(v) else
        "#00A000" if v < 0.1 else
        "#E6C300" if v < 0.2 else
        "#CC0000"
        for v in df["hoy"]
    ]
    
    # Formatear horas como strings
    df["hora"] = df["hora"].apply(lambda h: f"{int(h):02d}")
    
    fig = go.Figure()

    # Convertir horas a números para eje X
    df["hora_num"] = df["hora"].apply(lambda h: int(h[:2]))

    # Barras de precios de hoy
    fig.add_trace(
        go.Bar(
            x=df["hora_num"],
            y=df["hoy"],
            name="Hoy",
            marker_color=colors,
            width=0.8,
            offset=0,
            offsetgroup="hoy"
        )
    )

    # Líneas verticales de precios de mañana
    x_lines = []
    y_lines = []

    for x, y in zip(df["hora_num"], df["mañana"]):
        x_lines += [x + 0.4, x + 0.4, None]
        y_lines += [0, y, None]

    # Mapear colores según precio para mañana
    colors_mañana = [
        "#CCCCCC" if pd.isna(v) else
        "#00A000" if v < 0.1 else
        "#E6C300" if v < 0.2 else
        "#CC0000"
        for v in df["mañana"]
    ]

    fig.add_trace(
        go.Scatter(
            x=x_lines,
            y=y_lines,
            mode="lines",
            line=dict(color="rgba(255,0,0,0.5)", width=3),
            name="Linea Mañana",
            showlegend=False
        )
    )

    # Puntos marcadores para mañana
    fig.add_trace(
        go.Scatter(
            x=df["hora_num"] + 0.4,
            y=df["mañana"],
            mode="markers",
            marker=dict(
                size=10,
                color=colors_mañana,
                line=dict(width=1, color="black")
            ),
            name="Mañana"
        )
    )

    fig.update_layout(
        xaxis_title="Hora",
        yaxis_title="€/kWh",
        bargap=0.1,
        template="plotly_white",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        autosize=True,
        height=400
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(24)),
        ticktext=[f"{h:02d}" for h in range(24)]
    )

    return fig


def get_prices_Som() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Obtiene precios de hoy y mañana desde la API de SOM Energía.
    
    Obtiene los últimos 48 valores (24 horas de hoy + 24 de mañana)
    de la API de SOM Energía para la tarifa 2.0TD en Península.
    
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: DataFrame con columnas ['hora', 'hoy', 'mañana']
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df, error = get_prices_Som()
        >>> if not error:
        ...     print(f"Precio hoy: {df['hoy'].mean():.3f}€/kWh")
    """
    BASE_URL = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"

    response, error = safe_request_get(BASE_URL)
    if error:
        return None, error

    try:
        data = response.json()
        prices = data["data"]["curves"]["price_euros_kwh"][-48:]  # últimas 48 horas
        today = prices[:24]
        tomorrow = prices[24:]
        
        df = pd.DataFrame({
            "hora": range(24),
            "hoy": today,
            "mañana": tomorrow
        })
        
        return df, None
        
    except (KeyError, IndexError, ValueError) as e:
        return None, f"Error al parsear datos de SOM Energía: {e}"
    except Exception as e:
        return None, f"Error inesperado en get_prices_Som: {e}"


__all__ = ["get_prices_Som", "grafico_prices_Som"]
