"""
Módulo para obtener y visualizar predicciones de precios de energía.

Proporciona funciones para:
- Calcular precios estimados basados en energía renovable y demanda
- Agregar costes regulados
- Visualizar precios estimados vs spot
"""

from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard.comun import date_conditions as dc
from dashboard.comun.costes_regulados import costes_regulados


# Parámetros de regresión lineal para estimación de precios
SLOPE = -144.27
INTERCEPT = 127.12

def get_prices_forecast(
    energy: pd.DataFrame,
    spot: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula precios estimados a partir de energía renovable y demanda.
    
    Utiliza la ecuación lineal: precio = (renovable/demanda) * slope + intercept
    Luego agrega costes regulados para obtener precio final estimado.
    
    Args:
        energy: DataFrame con columnas ['eolica', 'solar', 'demanda', 'renovable']
        spot: DataFrame con columna 'Mercado SPOT'
        
    Returns:
        DataFrame con precios spot, estimados y costes regulados
        
    Example:
        >>> df_energy, _ = get_ESIOS_energy(rango)
        >>> df_spot, _ = get_ESIOS_spot(rango)
        >>> df_prices = get_prices_forecast(df_energy, df_spot)
        >>> print(df_prices.head())
    """
    # Combinar energía y spot
    df_final = energy.join(spot, how="outer")
    
    # Calcular energía renovable (ya está en energy, pero por si acaso)
    df_final["renovable"] = df_final["Previsión eólica"] + df_final["Solar fotovoltaica"]
    
    # Calcular precio estimado usando regresión lineal
    # precio_estimado = (renovable/demanda) * slope + intercept
    df_final["precio_estimado"] = (
        df_final["renovable"] / df_final["Previsión semanal"] * SLOPE + INTERCEPT
    )

    # Agregar costes regulados
    df_final = costes_regulados(df_final)
    
    # Sumar costes regulados a precios (spot y estimado)
    df_final["precio_estimado"] += df_final["costes_regulados"]
    df_final["Mercado SPOT"] += df_final["costes_regulados"]
    
    return df_final


@st.cache_data
def grafico_prices_forecast(df_precios: pd.DataFrame) -> go.Figure:
    """
    Crea gráfico interactivo de precios estimados vs spot.
    
    Genera un gráfico con:
    - Línea de precio estimado (naranja)
    - Línea de precio spot (azul)
    - Rectángulos para fines de semana y festivos
    - Línea vertical marcando el día actual
    
    Args:
        df_precios: DataFrame con columnas ['precio_estimado', 'Mercado SPOT']
        
    Returns:
        Figura Plotly (go.Figure)
        
    Example:
        >>> df_prices = get_prices_forecast(df_energy, df_spot)
        >>> fig = grafico_prices_forecast(df_prices)
        >>> fig.show()
    """
    fig_estimacion = go.Figure()

    # Añadir rectángulos en los fines de semana
    if dc.weekends:
        for start, end in dc.weekends:
            fig_estimacion.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="rgba(150,150,150,0.6)", width=1.5),
                fillcolor="rgba(100,100,100,0.2)",
                layer="above"
            )

    # Añadir rectángulos en los días festivos
    if dc.festivos:
        for festivo in dc.festivos:
            fig_estimacion.add_vrect(
                x0=festivo,
                x1=festivo + pd.Timedelta(days=1),
                fillcolor="indianred",
                opacity=0.15,
                line_width=0
            )

    # Línea de precio estimado
    fig_estimacion.add_trace(
        go.Scatter(
            x=df_precios.index,
            y=df_precios["precio_estimado"],
            mode="lines",
            name="Precio estimado",
            line=dict(color="orange", width=2)
        )
    )

    # Línea de precio spot
    fig_estimacion.add_trace(
        go.Scatter(
            x=df_precios.index,
            y=df_precios["Mercado SPOT"],
            mode="lines",
            name="Precio spot",
            line=dict(color="blue", width=2)
        )
    )

    # Configuración del layout
    fig_estimacion.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=20, b=20, l=0, r=0),
        xaxis_title="Fecha y hora",
        yaxis_title="€/MWh",
        hovermode="x unified"
    )

    # Configuración del eje X
    fig_estimacion.update_xaxes(
        dtick="D1",
        tickangle=45,
        showgrid=True,
        gridcolor="rgba(255,255,255,0.15)"
    )

    # Línea vertical marcando el día actual
    if dc.today:
        fig_estimacion.add_vline(
            x=dc.today,
            line_width=4,
            line_dash="dash",
            line_color="green",
            name="Hoy"
        )

    return fig_estimacion


__all__ = ["get_prices_forecast", "grafico_prices_forecast"]
