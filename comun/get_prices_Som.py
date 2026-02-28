
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from comun.safe_request import safe_request_get
#----------------------------------------------------------
# Función para obtener precios de Som Energia, con manejo de errores y caché de resultados.
# Retorna un DataFrame con columnas "hora", "hoy" y "mañana"
# Las próximas 24 horasde mañana se completan despues de las 14:00 del dia de hoy. Si no van Nan
#----------------------------------------------------------
@st.cache_data
def grafico_prices_Som(df):
    colors = [
        "#CCCCCC" if pd.isna(v) else
        "#00A000" if v < 0.1 else
        "#E6C300" if v < 0.2 else 
        "#CC0000" 
        for v in df["hoy"] 
    ]
    df["hora"] = df["hora"].apply(lambda h: f"{int(h):02d}")
    horas_completas = [f"{h:02d}" for h in range(24)]
    fig = go.Figure()

    # eje X numérico
    df["hora_num"] = df["hora"].apply(lambda h: int(h[:2]))

    # --- BARRAS DE HOY ---
    fig.add_trace(
        go.Bar(
            x=df["hora_num"],
            y=df["hoy"],
            name="Hoy",
            marker_color=colors,
            width=0.8,   # barras finas
            offset=0, # 👈 centra la barra en el tick 
            offsetgroup="hoy",
        )
    )

    # --- LÍNEAS VERTICALES DE MAÑANA ---
    # construir los segmentos verticales
    x_lines = []
    y_lines = []

    for x, y in zip(df["hora_num"], df["mañana"]):
        x_lines += [x + 0.4, x + 0.4, None]      # línea vertical + separador
        y_lines += [0, y, None]      # desde eje X hasta el valor

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
            line=dict(color="rgba(255,0,0,0.5)", width=3),  # color de la línea vertical
            name="Linea Mañana",
            showlegend=False
        )
    )

    # --- MARKERS ARRIBA MAÑANA (SOLO PUNTOS, SIN LÍNEAS) --- 
    fig.add_trace(
        go.Scatter( 
            x=df["hora_num"] + 0.4, 
            y=df["mañana"], 
            mode="markers", 
            marker=dict( 
                size=10, 
                color=colors_mañana, # escala de colores correcta 
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

def get_prices_Som():
    BASE_URL = "https://api.somenergia.coop/data/indexed_prices?tariff=2.0TD&geo_zone=PENINSULA"

    response, error = safe_request_get(BASE_URL)
    if error:
        return None, error
    
    data = response.json()
    prices = data["data"]["curves"]["price_euros_kwh"][-48:]  # lista de 48 valores
    today = prices[:24]
    tomorrow = prices[24:]

    df = pd.DataFrame({
        "hora": range(24),
        "hoy": today,
        "mañana": tomorrow
    })
    return df, None
