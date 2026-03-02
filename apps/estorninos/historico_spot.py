from pathlib import Path
import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
from comun.date_conditions import getSunDataRange
from datetime import date

@st.cache_data
def load_historico_precios_spot(estaciones=True, efemerides=True):
#==========================
# Datos historicos de precios spot para heatmap
#==========================
#=========================
# Estas corrdenadas se utilizan para graficar las salidas y puestas del sol en el heatmap de precios
#
    Puerta_Sol = dict(lat=40.4169, lon=-3.7033)

# Directorio donde está este archivo (comun/) 
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
# Ruta al JSON dentro de comun/
    repo_root = Path(__file__).resolve().parents[2]
    JSON_PATH = repo_root / "data" / "spot.csv"
  
    df_spot = pd.read_csv(
        JSON_PATH,
        sep=";", 
        encoding="utf-8-sig")
    df_spot["datetime"] = pd.to_datetime(df_spot["datetime"], utc=True)
    df_spot["date"] = df_spot["datetime"].dt.date
    df_spot["hour"] = df_spot["datetime"].dt.hour

#==========================
# Prepara datos spot para heatmap
#==========================
    price_matrix = df_spot.pivot(index="date", columns="hour", values="value")
    price_matrix = price_matrix.fillna(0)
    price_matrix = price_matrix.sort_index()  # Asegura orden por fecha
    price_matrix.index = pd.to_datetime(price_matrix.index)

    fechas = pd.to_datetime(price_matrix.index).sort_values().unique()
    ticks_mes = [f for f in fechas if f.day == 1]
#===========================
# Gráfico de heatmap de precios con Plotly
#===========================

    fig_precios = go.Figure(
        data=go.Heatmap(
            z=price_matrix.values,
            x=price_matrix.columns,
            y=price_matrix.index.strftime("%Y-%m-%d"),  # convierte fechas a string
            colorbar=dict(
                title="Precio €/MWh"   # ← equivalente a labels["color"]
            ),
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
    #===========================
    # Cambios de estación sin año
    #===========================
        cambios_estacion = [
            (3, 20),   # primavera
            (6, 21),   # verano
            (9, 22),   # otoño
            (12, 21)   # invierno
        ]
    #===========================
    # Posiciones en el eje Y de los cambios de estación
    #===========================
        fechas_cambio = []
        for mes, dia in cambios_estacion:
            coincidencias = [f for f in fechas if f.month == mes and f.day == dia]
            fechas_cambio.extend(coincidencias)
    #===========================
    # Añadir líneas horizontales en los cambios de estación
    #===========================
            for f in fechas_cambio:
                fig_precios.add_hline(
                    y=f,
                    line_width=1,
                    line_dash="solid",
                    line_color="#FF00FF"
                )
    if (efemerides):
#===========================
# Datos de salida y puesta del sol para superponer en el heatmap
#===========================
       # df_sun = getSunDataRange(Puerta_Sol,date(2024, 1, 1), date(2025, 12, 31), 15, "Europe/Madrid")
        df_sun = getSunDataRange(Puerta_Sol,date(2024, 1, 1), date(2025, 12, 31), 15, "UTC")
#==========================
# PUNTOS DE SALIDA DEL SOL
#==========================
        fig_precios.add_trace(go.Scatter(
            x=df_sun["sunrise_hour"],
            y=df_sun["date"],
            mode="lines",
            line=dict(color="orange", width=2), 
            name="Salida del sol", 
        )) 
#==========================
# PUNTOS DE PUESTA DEL SOL
#==========================
        fig_precios.add_trace(go.Scatter(
            x=df_sun["sunset_hour"], 
            y=df_sun["date"], 
            mode="lines", 
            line=dict(color="red", width=2), 
            name="Puesta del sol",
        )) 
    return fig_precios, ticks_mes

