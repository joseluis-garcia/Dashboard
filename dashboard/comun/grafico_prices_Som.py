"""
Módulo para visualizar precios de SOM Energía.
"""

from typing import Tuple, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.comun.get_ESIOS_data import get_ESIOS_spot
from dashboard.comun.get_Som_data import get_prices_Som_indexada

@st.cache_data
def grafico_prices_Som() -> Tuple[go.Figure, Optional[str]]:

    """
    Crea gráfico interactivo de precios indexados de SOM Energía.
    
    Muestra:
    - Barras de precios de hoy (coloreadas por rango)
    - Líneas verticales de precios de mañana (cuando este disponibles)
    - Puntos marcadores para mañana
    - Puntos marcadores para las horas que hoy hay precios negativos
    
    Colores:
    - Verde: < 0.1 €/kWh (muy barato)
    - Amarillo: < 0.2 €/kWh (barato)
    - Rojo: >= 0.2 €/kWh (caro)
    - Gris: valores faltantes (NaN)
          
    Returns:
        Tupla (dataframe, error) donde:
        - Figura Plotly (go.Figure): None si ha fallado
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df, error = get_prices_Som()
        >>> if error:
        >>>     mensaje (error)
        >>> else:
        >>>     fig = grafico_prices_Som(df)
        >>>     fig.show()
    """
    # Obtenemos los precios de la web de Som Energia
    df, error = get_prices_Som_indexada()
    if error:
        return None, f"No se han podido obtener los precios de SOM Energía: {error}"
    
    # Obtener precios de ESIOS para detectar precios excedentes negativos
    df_omie, error_omie = get_ESIOS_spot(None)
    if error_omie:
        return None, f"No se han podido obtener los precios de ESIOS: {error_omie}"
    
    # Convertimos el indice a hora local
    local = df_omie.tz_convert("Europe/Madrid")
    # Asegurar que las horas estén en formato numérico
    df_omie["hora_num"] = local.index.hour + local.index.minute / 60
    # Nos quedamos con las horas de precios negativos
    df_omie=df_omie[df_omie["Mercado SPOT"]<0]
    

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

    # Marcas de precios negativos de Omie
    fig.add_trace(
        go.Scatter(
            x=df_omie["hora_num"]+0.4,
            y=df_omie["Mercado SPOT"]/1000,
            mode="markers",
            marker=dict(
                size=8,
                color= "#B83170",
            ),
            name="Precios negativos ESIOS"
        )
    )

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

    return fig, None

__all__ = ["grafico_prices_Som"]
