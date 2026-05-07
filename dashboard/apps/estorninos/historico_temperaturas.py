
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dashboard.comun.date_conditions import getSunDataRange
from dashboard.comun.sql_utilities import read_sql_ts
from typing import Tuple, Optional
from datetime import date

@st.cache_data
def load_historico_temperaturas(_conn):

    df_temp, error = read_sql_ts(
        "SELECT datetime, temperature FROM METEO",
        _conn
     )
    if error:
        return None, f"No se han podido cargar las temperaturas históricas: {error}"

# # Ruta al CSV dentro de comun/
#     current_file = Path(__file__)
#     dashboard_dir = current_file.parents[2]  # Sube a dashboard/
#     csv_path = dashboard_dir / "data" / "temperaturas.csv"

# #==========================
# # Datos historicos de temperaturas para heatmap
# #==========================
#     df_temp = pd.read_csv(
#         csv_path,
#         sep=";", 
#         encoding="utf-8-sig",
#         parse_dates=["datetime"],
#         dayfirst=True,               # importante para formato europeo
#         date_format="%d/%m/%Y %H:%M"
#     )
#    df_temp["datetime"] = pd.to_datetime(df_temp["datetime"])
    df_temp.index = df_temp.index.tz_convert("Europe/Madrid")
    df_temp["date"] = df_temp.index.date
    df_temp["hour"] = df_temp.index.hour
    df_temp = df_temp.drop_duplicates(subset=["date", "hour"], keep="last")
#==========================
# Prepara datos temperatura para heatmap
#==========================
    temp_matrix = df_temp.pivot(
        index="date",
        columns="hour",
        values="temperature",
    )
    temp_matrix = temp_matrix.fillna(0)
    temp_matrix = temp_matrix.sort_index()  # Asegura orden por fecha
    temp_matrix.index = pd.to_datetime(temp_matrix.index)
    return temp_matrix, None

def add_estaciones(fig, fechas):
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
            fig.add_hline(
                y=f,
                line_width=1,
                line_dash="solid",
                line_color="#FF00FF"
            )

def add_efemerides(fig, fechas):
# Estas corrdenadas se utilizan para graficar las salidas y puestas del sol en el heatmap de temperaturas
#
    PUERTA_SOL = dict(lat=40.4169, lon=-3.7033)
#===========================
# Datos de salida y puesta del sol para superponer en el heatmap
#===========================
    df_sun = getSunDataRange(PUERTA_SOL,date(2024, 1, 1), date(2025, 12, 31), 15, tz_local="UTC")
#==========================
# PUNTOS DE SALIDA DEL SOL
#==========================
    fig.add_trace(go.Scatter(
        x=df_sun["sunrise_hour"],
        y=df_sun["date"],
        mode="lines",
        line=dict(color="orange", width=2), 
        name="Salida del sol"
    )) 
#==========================
# PUNTOS DE PUESTA DEL SOL
#==========================
    fig.add_trace(go.Scatter(
        x=df_sun["sunset_hour"], 
        y=df_sun["date"], 
        mode="lines", 
        line=dict(color="red", width=2), 
        name="Puesta del sol"
    ))

def grafico_historico_temperaturas(temp_matrix, estaciones=True, efemerides=True):
    print("TTTTT", type(temp_matrix.index))
    #print(temp_matrix.index.dtype)
    fechas = temp_matrix.index.sort_values().unique()
    ticks_mes = [f for f in fechas if f.day == 1]
#===========================
# Gráfico de heatmap de temperaturas con Plotly
#===========================
    fig_temperaturas = go.Figure(
        data=go.Heatmap(
            z=temp_matrix.values,
            x=temp_matrix.columns,
            y=temp_matrix.index.strftime("%Y-%m-%d"),  # convierte fechas a string

            colorbar=dict(
                title="Temperatura (°C)"   # ← equivalente a labels["color"]
            ),
            colorscale="RdBu_r"
        )
    )
    fig_temperaturas.update_yaxes(tickvals=ticks_mes,
                        tickmode="array",
                        ticktext=[d.strftime("%Y-%m-%d") for d in ticks_mes])
    fig_temperaturas.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    fig_temperaturas.update_layout(
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
        add_estaciones(fig_temperaturas, fechas)

    if (efemerides):
        add_efemerides(fig_temperaturas, fechas)

    return fig_temperaturas

def grafico_stress_termico(temp_matrix, tFrio=15, tCalor=28):
#==========================
# Grafico de strees termico frío y calor superpuestos
    fechas = temp_matrix.index.sort_values().unique()
    ticks_mes = [f for f in fechas if f.day == 1]
    # Calcula matriz de "stress" térmico
    def calc_stress(t):
        if pd.isna(t):
            return None
        if t <= tFrio:
            return tFrio - t      # frío: positivo cuanto más frío
        elif t >= tCalor:
            return t - tCalor      # calor: positivo cuanto más calor
        else:
            return None        # confortable: no se representa

    # Matriz Z combinada: valores negativos = frío, positivos = calor
    stress_combined = temp_matrix.map(lambda t: 
        -(tFrio - t) if (not pd.isna(t) and t <= tFrio)
        else (t - tCalor) if (not pd.isna(t) and t >= tCalor)
        else None
    )

    # Matriz de texto para el tooltip
    def stress_text(t):
        if pd.isna(t):
            return ""
        if t <= tFrio:
            return f"❄️ Stress frío: {tFrio - t:.1f}°C"
        elif t >= tCalor:
            return f"🌡️ Stress calor: {t - tCalor:.1f}°C"
        return ""

    stress_text_matrix = temp_matrix.map(stress_text)

    z = stress_combined.values.astype(float)
    zmin = np.nanmin(z)
    zmax = np.nanmax(z)
    zero_pos = abs(zmin) / (abs(zmin) + abs(zmax))  # posición del 0 en [0,1]

    colorscale = [
        [0.0,                    "#0000ff"],  # azul intenso
        [zero_pos * 0.8,         "#aaccff"],  # azul claro justo antes del 0
        [zero_pos,               "#ffffff"],  # blanco = 0
        [zero_pos + (1 - zero_pos) * 0.4, "#ffaa66"],  # naranja claro justo después del 0
        [1.0,                    "#ff0000"],  # rojo intenso
    ]

    fig_stress = go.Figure(data=go.Heatmap(
        z=stress_combined.values.astype(float),
        x=stress_combined.columns,
        y=stress_combined.index.strftime("%Y-%m-%d"),
        text=stress_text_matrix.values,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        #zmid=0,  # centra la escala en 0 → azul=frío, rojo=calor
        colorbar=dict(title="Stress térmico (°C)"),
        hovertemplate="Fecha: %{y}<br>Hora: %{x}h<br>%{text}<extra></extra>",
    ))

    fig_stress.update_yaxes(tickvals=ticks_mes,
                        tickmode="array",
                        ticktext=[d.strftime("%Y-%m-%d") for d in ticks_mes])
    fig_stress.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    fig_stress.update_layout(
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

    return fig_stress

# Define la temperatura umbral para considerar un día como frío y generar matriz de días fríos para superponer en el heatmap
#==========================
# umbral = st.number_input("Umbral de temperatura", value=5.0)
# df_temp["is_cold"] = df_temp["temperatura"] < umbral
# cold_matrix = df_temp.pivot_table(
#     index="date",
#     columns="hour",
#     values="is_cold",
#     aggfunc="max"   # si hay varios registros por hora, basta con que uno sea frío
# )
# cold_x = cold_matrix.columns.astype(int)
# cold_y = pd.to_datetime(cold_matrix.index).sort_values().unique()
# cold_z = cold_matrix.fillna(0).astype(int).values

#cold_z = cold_matrix.astype(int).values
# cold_x = pd.to_datetime(cold_matrix.columns)
# cold_y = cold_matrix.index.astype(int)
# cold_matrix = df_temp.pivot(
#     index="date",
#     columns="hour",
#     values="temperatura",
# )
# cold_matrix = cold_matrix.fillna(0)
# cold_matrix = cold_matrix.sort_index()  # Asegura orden por fecha
# cold_matrix.index = pd.to_datetime(cold_matrix.index)