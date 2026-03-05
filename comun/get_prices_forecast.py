
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import comun.date_conditions as dc
from comun.costes_regulados import costes_regulados

slope = -144.27
intercept = 127.12

#==========================
# Función para obtener el precio estimado a partir de la energía renovable y la demanda previsiones de ESIOS, y el precio spot diario de ESIOS. Se añaden los costes regulados para obtener el precio final estimado.
#==========================
def get_prices_forecast(energy, spot):    
    df_final = energy.merge(spot, on="datetime", how="outer")
    df_final["renovable"] = df_final["eolica"] + df_final["solar"]
    df_final["precio_estimado"] = (df_final["renovable"] / df_final["demanda"] * slope + intercept)
#==========================
# Tanto spot como la estimación estan hechas sin costes regulados, que se añaden al final para obtener el precio final estimado.
#==========================
    df_final = costes_regulados(df_final, 'datetime')
    df_final["precio_estimado"] += df_final["costes_regulados"]
    df_final["precio_spot"] += df_final["costes_regulados"]
    return df_final

@st.cache_data
def grafico_prices_forecast(df_precios):
# =========================
# Prepara gráfico de precios
# =========================
    fig_estimacion = go.Figure()  
    # Añadir rectángulos en los fines de semana
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
    for festivo in dc.festivos:
        fig_estimacion.add_vrect(
            x0=festivo, x1=festivo + pd.Timedelta(days=1),
            fillcolor="indianred",
            opacity=0.15,
            line_width=0
        )
    # Curva de precio estimado
    fig_estimacion.add_trace(go.Scatter(
        x=df_precios["datetime"],
        y=df_precios["precio_estimado"],
        mode="lines",
        name="Precio estimado",
        line=dict(color="orange", width=2)
    ))
    # Curva de precio spot
    fig_estimacion.add_trace(go.Scatter(
        x=df_precios["datetime"],
        y=df_precios["precio_spot"],
        mode="lines",
        name="Precio spot",
        line=dict(color="blue", width=2)
    ))
    fig_estimacion.update_layout(
        legend=dict(
            orientation="h",          # horizontal
            yanchor="top",
            y=-0.3,                   # desplaza la leyenda hacia abajo
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=20, b=20, l=0, r=0),
        xaxis_title="Fecha y hora",
        yaxis_title="€/MWh",
        hovermode="x unified"
    )
    fig_estimacion.update_xaxes( 
        dtick="D1", 
        tickangle=45, 
        showgrid=True, 
        gridcolor="rgba(255,255,255,0.15)")
    # Línea vertical para marcar el día actual
    fig_estimacion.add_vline(x=dc.today, line_width=4, line_dash="dash", line_color="green", name="Hoy")
    return fig_estimacion
