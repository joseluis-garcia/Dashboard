import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date
import sqlite3

from dashboard.comun.date_conditions import getSunDataRange
from dashboard.comun.sql_utilities import read_sql_ts
import dashboard.apps.config as TCB

@st.cache_data
def load_historico_precios_spot(_conn: sqlite3.Connection, estaciones=True, efemerides=True) -> tuple[go.Figure, list[pd.Timestamp], str | None]:
    """
    Carga datos históricos de precios spot y prepara un heatmap con Plotly.
    Args:
        _conn: Conexión a la base de datos SQLite
        estaciones: Si True, añade líneas horizontales en los cambios de estación
        efemerides: Si True, añade líneas de salida y puesta del sol
    Returns:
        fig_precios: Gráfico de heatmap de precios con Plotly
        ticks_mes: Lista de fechas para marcar el primer día de cada mes en el eje Y
        error: None si es exitoso, mensaje de error si falla
    """

    df_spot, error = read_sql_ts('select datetime, "Mercado SPOT" as price from ESIOS_data', _conn)
    if error: 
        return None, None, f"Error al cargar datos históricos de precios spot: {error}"
    
    # Convierte el índice a hora local y extrae fecha y hora para el heatmap
    df_spot.index = df_spot.index.tz_convert('Europe/Madrid')
    df_spot["date"] = df_spot.index.date
    df_spot["hour"] = (df_spot.index.hour + 
                      df_spot.index.minute / 60 + 
                      df_spot.index.second / 3600)

    # Prepara datos spot para heatmap
    price_matrix = df_spot.pivot_table(index="date", columns="hour", values="price", aggfunc='mean')
    price_matrix = price_matrix.fillna(0)
    price_matrix = price_matrix.sort_index()  # Asegura orden por fecha
    price_matrix.index = pd.to_datetime(price_matrix.index)

    fechas = pd.to_datetime(price_matrix.index).sort_values().unique()
    ticks_mes = [f for f in fechas if f.day == 1]

    # Gráfico de heatmap de precios con Plotly
    p95 = np.percentile(price_matrix.values, 95) #Quitamos los outliers para mejorar la visualización del heatmap
    fig_precios = go.Figure(
        data=go.Heatmap(
            z=price_matrix.values,
            x=price_matrix.columns,
            y=price_matrix.index.strftime("%Y-%m-%d"),  # convierte fechas a string
            colorbar=dict(
                title="Precio €/MWh"   # ← equivalente a labels["color"]
            ),
            zmax=p95,
            zmin = 0,
            colorscale="Turbo"
        )
    )
    fig_precios.update_yaxes(tickvals=ticks_mes,
                        tickmode="array",
                        ticktext=[d.strftime("%Y-%m-%d") for d in ticks_mes])

    fig_precios.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    fig_precios.update_layout(
        height=900,
        xaxis_title="Hora del día",
        yaxis_title="Fecha",
        yaxis=dict(autorange="reversed"),  # fechas arriba → abajo
        legend=dict(
            orientation="h",        # Horizontal
            yanchor="bottom",
            y=1.02,                 # Un poco por encima del gráfico
            xanchor="center",
            x=0.5                   # Centrada
        )
    )

    if (estaciones):
    # Cambios de estación sin año
        cambios_estacion = [
            (3, 20),   # primavera
            (6, 21),   # verano
            (9, 22),   # otoño
            (12, 21)   # invierno
        ]

    # Posiciones en el eje Y de los cambios de estación
        fechas_cambio = []
        for mes, dia in cambios_estacion:
            coincidencias = [f for f in fechas if f.month == mes and f.day == dia]
            fechas_cambio.extend(coincidencias)

    # Añadir líneas horizontales en los cambios de estación
            for f in fechas_cambio:
                fig_precios.add_hline(
                    y=f,
                    line_width=1,
                    line_dash="solid",
                    line_color="#FF00FF"
                )
    
    if (efemerides):
    # Datos de salida y puesta del sol para superponer en el heatmap
        df_sun = getSunDataRange(TCB.PUERTA_SOL,date(2022, 1, 1), date(2026, 3, 31), 15)

    # PUNTOS DE SALIDA DEL SOL
        fig_precios.add_trace(go.Scatter(
            x=df_sun["sunrise_hour"],
            y=df_sun["date"],
            mode="lines",
            line=dict(color="orange", width=2), 
            name="Salida del sol", 
        )) 

    # PUNTOS DE PUESTA DEL SOL
        fig_precios.add_trace(go.Scatter(
            x=df_sun["sunset_hour"], 
            y=df_sun["date"], 
            mode="lines", 
            line=dict(color="red", width=2), 
            name="Puesta del sol",
        )) 
    
    return fig_precios, ticks_mes, None

