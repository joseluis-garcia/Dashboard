
import requests
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
import base64
from comun.date_conditions import getSunData

def load_icon(relative_path):

    # Directorio donde está este archivo (comun/) 
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
    # Ruta al JSON dentro de comun/
    ICON_PATH = os.path.join(BASE_DIR, relative_path)
    with open(ICON_PATH, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

# =========================
# FUNCIONES PARA GRAFICO de PVGIS
# lat, lon y fecha son necesarios para obtener los datos solares.
# Deben ser coherentes con los datos que se utilizaron para obtener df en get_PVGIS_data
# =========================
def grafico_PVGIS(df, lat, lon, fecha):
    df["hora"] = df["hora"].apply(lambda h: f"{int(h):02d}")
    horas_completas = [f"{h:02d}" for h in range(24)]

    sun_data = getSunData(lat, lon, fecha) 
    fig = go.Figure()

    # eje X numérico
    df["hora_num"] = df["hora"].apply(lambda h: int(h[:2]))

    fig.add_trace(
        go.Scatter(
            x=df["hora_num"],
            y=df["P"],
            mode="lines+markers",
            name=f"Promedio histórico",
            line=dict(color="blue", width=2, shape="spline", smoothing=1.3),
        )
    )

    # Añadir icono PNG en una hora concreta
    # 
    icon_rise = load_icon("icons/sunrise-dark.png") 
    fig.add_layout_image( 
        dict( 
            source=icon_rise, # ruta local o base64 
            x=sun_data["sunrise"], # posición en eje X 
            y=0, # posición en eje Y 
            xref="x",
            yref="paper", 
            sizex=0.5, # tamaño horizontal 
            sizey=0.5, # tamaño vertical 
            xanchor="center", 
            yanchor="middle", 
            layer="above"
        )
    )

    icon_noon = load_icon("icons/10000_clear_small.png")
    fig.add_vline(x=sun_data["noon"], line_width=2, line_dash="dash", line_color="green", name="Mediodía")
    fig.add_layout_image( 
        dict( 
            source=icon_noon, # ruta local o base64 
            x=sun_data["noon"], # posición en eje X 
            y=0, # posición en eje Y 
            xref="x",
            yref="paper", 
            sizex=0.5, # tamaño horizontal 
            sizey=0.5, # tamaño vertical 
            xanchor="center", 
            yanchor="middle", 
            layer="above"
        )
    )

    icon_set = load_icon("icons/sunset-dark.png") 
    fig.add_layout_image( 
        dict( 
            source=icon_set, # ruta local o base64 
            x=sun_data["sunset"], # posición en eje X 
            y=0, # posición en eje Y 
            xref="x",
            yref="paper", 
            sizex=0.5, # tamaño horizontal 
            sizey=0.5, # tamaño vertical 
            xanchor="center", 
            yanchor="middle", 
            layer="above"
        )
    )

    fig.update_xaxes(
        range=[0, 23],
        dtick=1   # para que marque cada hora
    )


    fig.update_layout(
        title=f"Curva promedio de potencia por kWp instalado para hoy", # ({hoy_local.strftime('%d/%m')})",
        xaxis_title="Hora del día",
        yaxis_title="Potencia pico (kW)",
        template="plotly_white",
        xaxis=dict(dtick=1, showgrid=True),
        yaxis=dict(showgrid=True)
    )

    return fig

@st.cache_data
def get_PVGIS_data(lat, lon, fecha):

    BASE_URL = f"https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?&pvcalculation=1&peakpower=1&outputformat=json&startyear=2018&loss=14&lat={lat}&lon={lon}"

    r = requests.get(BASE_URL) #, headers=headers, params=date_range)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data["outputs"]["hourly"])
    # 1️⃣ Convertir time a datetime UTC
    df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", utc=True)

    # convertir a hora local
    df["time_local"] = df["time"].dt.tz_convert("Europe/Madrid")
    df["mes"] = df["time_local"].dt.month
    df["dia"] = df["time_local"].dt.day
    df["hora"] = df["time_local"].dt.hour

    df_prom = df.groupby(["mes", "dia", "hora"], as_index=False)["P"].mean()

    # 4️⃣ Obtener la fecha de hoy en local
    hoy_local = pd.Timestamp.now(tz="Europe/Madrid")
    mes_hoy = fecha.month #hoy_local.month
    dia_hoy = fecha.day #hoy_local.day

    # 5️⃣ Filtrar solo para el día de hoy (mes y día)
    perfil_hoy = df_prom[
        (df_prom["mes"] == mes_hoy) &
        (df_prom["dia"] == dia_hoy)
    ].sort_values("hora")
    return perfil_hoy
