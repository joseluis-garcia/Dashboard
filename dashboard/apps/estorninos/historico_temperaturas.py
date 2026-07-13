from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Tuple, Optional
from datetime import date
import sqlite3

from dashboard.comun.date_conditions import getSunDataRange
from dashboard.comun.sql_utilities import read_sql_ts
import dashboard.apps.config as TCB

@st.cache_data
#se usa _conn para indicar que es un argumento que no se tiene que usar para el cache, ya que no es hashable
def load_historico_temperaturas(_conn: sqlite3.Connection) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga datos históricos de temperaturas y prepara una matriz para heatmap.
    Args:
        _conn: Conexión a la base de datos SQLite
    Returns:
        temp_matrix: DataFrame con temperaturas pivotadas por fecha y hora en hora local Europe/Madrid
        error: None si es exitoso, mensaje de error si falla
    """

    df_temp, error = read_sql_ts(
        "SELECT datetime, temperature FROM METEO",
        _conn
     )
    if error:
        return None, f"No se han podido cargar las temperaturas históricas: {error}"

    # Convertir el índice a hora local y extraer fecha y hora para el heatmap
    df_temp.index = df_temp.index.tz_convert("Europe/Madrid")
    df_temp["date"] = df_temp.index.date
    df_temp["hour"] = df_temp.index.hour
    df_temp = df_temp.drop_duplicates(subset=["date", "hour"], keep="last")
    print(f"Temperaturas históricas cargadas desde: {df_temp.index[0]} hasta {df_temp.index[-1]}, {len(df_temp)} registros")

    # Prepara datos temperatura para heatmap
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
            fig.add_hline(
                y=f,
                line_width=1,
                line_dash="solid",
                line_color="#FF00FF"
            )

def add_efemerides(fig, fechas):
    # Datos de salida y puesta del sol para superponer en el heatmap
    df_sun = getSunDataRange(TCB.PUERTA_SOL,date(2024, 1, 1), date(2025, 12, 31), 15, tz_local="UTC")

    # PUNTOS DE SALIDA DEL SOL
    fig.add_trace(go.Scatter(
        x=df_sun["sunrise_hour"],
        y=df_sun["date"],
        mode="lines",
        line=dict(color="orange", width=2), 
        name="Salida del sol"
    )) 

    # PUNTOS DE PUESTA DEL SOL
    fig.add_trace(go.Scatter(
        x=df_sun["sunset_hour"], 
        y=df_sun["date"], 
        mode="lines", 
        line=dict(color="red", width=2), 
        name="Puesta del sol"
    ))

def grafico_historico_temperaturas(temp_matrix, estaciones=True, efemerides=True):
    """
    Genera un heatmap de temperaturas históricas con opciones para marcar cambios de estación y efemérides.
    Args:
        temp_matrix: DataFrame con temperaturas pivotadas por fecha y hora
        estaciones: Si True, añade líneas para cambios de estación
        efemerides: Si True, añade líneas para salida y puesta del sol
    Returns:
        fig_temperaturas: Figura de Plotly con el heatmap de temperaturas
    """
    fechas = temp_matrix.index.sort_values().unique()
    ticks_mes = [f for f in fechas if f.day == 1]

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
    """
    Genera un heatmap de stress térmico combinando frío y calor, con tooltips detallados.
    Cada dia hora se representa con un color que indica si fue frío (azul), confortable (blanco) o caluroso (rojo), y el tooltip muestra la temperatura exacta y el nivel de stress térmico.
    El valor de stress térmico se calcula como la diferencia entre la temperatura y el umbral correspondiente (tFrio o tCalor), y se muestra en el tooltip para entender cuánto se aleja la temperatura de la zona confortable.

    Args:
        temp_matrix: DataFrame con temperaturas pivotadas por fecha y hora
        tFrio: Temperatura umbral para considerar frío (°C)
        tCalor: Temperatura umbral para considerar calor (°C)

    Returns:
        fig_stress: Figura de Plotly con el heatmap de stress térmico
    """

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


    print(f"Stress térmico calculado desde: {stress_combined.index[0]} hasta {stress_combined.index[-1]}, {len(stress_combined)} registros")
    print("Stress_combined:", stress_combined.head())

    # Matriz de texto para el tooltip
    def stress_text(t):
        if pd.isna(t):
            return ""
        if t <= tFrio:
            return f"Temp: {t:.1f}°C<br>❄️ Stress frío: {tFrio - t:.1f}°C"
        elif t >= tCalor:
            return f"Temp: {t:.1f}°C<br>🌡️ Stress calor: {t - tCalor:.1f}°C"
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
        colorbar=dict(title="Stress térmico (°C)"),
        hovertemplate="Fecha: %{y}<br>Hora: %{x}h<br>%{text}<extra></extra>",
    ))

    fig_stress.update_yaxes(tickvals=ticks_mes,
                        tickmode="array",
                        ticktext=[d.strftime("%Y-%m") for d in ticks_mes])
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

    return fig_stress, stress_combined

def calcular_stress_mensual(stress_combined: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de stress_combined (index=fecha, columnas=0..23 con la
    diferencia de temperatura respecto al límite), calcula la suma mensual
    de los valores positivos (calor) y negativos (frío) por separado, para
    comparar la intensidad de olas de calor/frío entre años.
    """
    df = stress_combined.copy()
    df.index = pd.to_datetime(df.index)

    # clip(lower=0) anula los negativos -> solo queda la parte de calor
    # clip(upper=0) anula los positivos -> solo queda la parte de frío (negativa)
    calor_diario = df.clip(lower=0).sum(axis=1)
    frio_diario = df.clip(upper=0).sum(axis=1)

    resumen = pd.DataFrame({"calor": calor_diario, "frio": frio_diario})
    resumen["year"] = resumen.index.year
    resumen["month"] = resumen.index.month

    mensual = (
        resumen.groupby(["year", "month"])[["calor", "frio"]]
        .sum()
        .reset_index()
    )
    return mensual

import plotly.graph_objects as go
import plotly.express as px

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

def graficar_stress_mensual(mensual: pd.DataFrame) -> go.Figure:
    mensual = mensual.copy()
    mensual["mes_nombre"] = mensual["month"].map(lambda m: MESES[m - 1])

    years = sorted(mensual["year"].unique())
    colores_calor = px.colors.sample_colorscale("OrRd", [i / max(len(years)-1, 1) for i in range(len(years))])
    colores_frio = px.colors.sample_colorscale("Blues", [i / max(len(years)-1, 1) for i in range(len(years))])

    fig = go.Figure()
    for i, year in enumerate(years):
        sub = mensual[mensual["year"] == year].sort_values("month")
        fig.add_trace(go.Bar(
            x=sub["mes_nombre"], y=sub["calor"],
            name=f"{year} calor",
            marker_color=colores_calor[i],
            legendgroup=str(year), offsetgroup=str(year),
        ))
        fig.add_trace(go.Bar(
            x=sub["mes_nombre"], y=sub["frio"],
            name=f"{year} frío",
            marker_color=colores_frio[i],
            legendgroup=str(year), offsetgroup=str(year),
        ))

    fig.update_layout(
        barmode="relative",  # apila calor (+) y frío (-) dentro de cada offsetgroup
        xaxis=dict(categoryorder="array", categoryarray=MESES),
        yaxis_title="Grados-hora acumulados por encima/debajo del límite",
        legend_title="Año",
    )
    fig.add_hline(y=0, line_color="gray", line_width=1)
    return fig

def graficar_stress_mensual_lineas(mensual: pd.DataFrame) -> go.Figure:
    mensual = mensual.copy()
    mensual["mes_nombre"] = mensual["month"].map(lambda m: MESES[m - 1])

    years = sorted(mensual["year"].unique())
    # colores = px.colors.sample_colorscale("Turbo", [i / max(len(years) - 1, 1) for i in range(len(years))])

    paleta = px.colors.qualitative.Vivid
    colores = {year: paleta[i % len(paleta)] for i, year in enumerate(years)}

    fig = go.Figure()
    for i, year in enumerate(years):
        sub = mensual[mensual["year"] == year].sort_values("month")
        color = colores[year]

        fig.add_trace(go.Scatter(
            x=sub["mes_nombre"], y=sub["calor"],
            mode="lines+markers",
            name=f"{year}",
            legendgroup=str(year),
            line=dict(color=color, width=2),
            marker=dict(symbol="triangle-up"),
        ))
        fig.add_trace(go.Scatter(
            x=sub["mes_nombre"], y=sub["frio"],
            mode="lines+markers",
            name=f"{year}",
            legendgroup=str(year),
            line=dict(color=color, width=2, dash="dot"),
            marker=dict(symbol="triangle-down"),
            showlegend=False,  # ya se muestra en la línea de calor del mismo año
        ))

    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MESES),
        yaxis_title="Grados-hora acumulados por encima/debajo del límite",
        legend_title="Año",
    )
    fig.add_hline(y=0, line_color="gray", line_width=1)
    return fig