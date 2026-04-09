import streamlit as st
import pandas as pd
import scipy.stats as stats
import plotly.graph_objects as go
import numpy as np
from dashboard.comun.mensaje import render_df_proportional
from dashboard.comun.sql_utilities import read_sql_ts

def cleanSolar( row):
    # Para cada dia se asume que toda la energia proveniente de los paneles se consume primero en aerotermia
    return row['extra_Wh'] - row['solar_Wh'] if row['extra_Wh'] > row['solar_Wh'] else 0

def get_aerotermia_data( conn):
    #Query historical energy consumption data from WIBEE table
    query = "SELECT datetime, solar_Wh, extra_Wh from WIBEE where extra_Wh > 15 and extra='{0}' order by datetime".format('AEROTERMIA')
    swibe = read_sql_ts(query, conn)
    swibe['energy'] = swibe.apply( cleanSolar, axis = 1)
    swibe['energy'] = swibe["energy"] / 1000 # Convertir a kWh
    swibe = swibe[['energy']]
    aeroMin = swibe.index.min()
    aeroMax = swibe.index.max()
    st.write(f"WIBEE since {aeroMin} to {aeroMax}")

    # Query prices data form precios_indexada
    query = "SELECT * from SOM_precio_indexada order by datetime"
    prices = read_sql_ts(query, conn)
    prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
    prices['price'] = prices['price'] * 1.21
    pricesMin = prices.index.min()
    pricesMax = prices.index.max()
    st.write(f"PRICES since {pricesMin} to {pricesMax}")

    dateMin = max(pricesMin, aeroMin)
    dateMax = min(pricesMax, aeroMax)
    st.write(f"Using data from {dateMin} to {dateMax}")

    df_energy = swibe[(swibe.index >= dateMin) & (swibe.index <= dateMax)]
    df_prices = prices[(prices.index >= dateMin) & (prices.index <= dateMax)]

    # Compute real cost
    df_cost = df_prices.join(df_energy)
    df_cost["cost"] = df_cost["price"] * df_cost["energy"]

    #Get weather data from VXSING
    query = "SELECT datetime, temperature as temp from METEO where datetime >= '{0}' and datetime <= '{1}' order by datetime".format(dateMin, dateMax)
    df_temp = read_sql_ts(query, conn)

    #Merge all data in one final dataframe
    df_final = df_cost.join(df_temp)
    return df_final

def grafico_aerotermia(df_final):
    # Clean days where only standby consumption
    df_final = df_final[df_final['energy'] > 1.6]
    daily_energy = df_final["energy"].resample("D").sum() 
    daily_temp = df_final["temp"].resample("D").mean() 
    df_daily = pd.DataFrame({ "energy_sum": daily_energy, "temp_mean": daily_temp }).dropna()
    fig =  regresion(df_daily, "temp_mean", "energy_sum")

    fig.update_layout(
        template="plotly_dark",  # ideal para Streamlit dark
        xaxis_title="Temperatura (°C)",
        yaxis_title="Energía diaria",
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.05,
            yanchor="bottom"
        )
    )
    return fig

def regresion(df_daily, x_col, y_col):
    x = df_daily[x_col].values
    y = df_daily[y_col].values
    # Regresión
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    # Print the equation
    st.html(f"""
    <p style='line-height: 1.0; margin: 0;'>Consumo diario(kWh) = {intercept:.2f}(kWh)  {slope:.2f}(kWh / ºC) * Temperatura media (ºC)</p>
    """)
    # Ordenar x para línea suave
    x_line = np.linspace(x.min(), x.max(), 200)
    y_line = slope * x_line + intercept

    # Estadísticos necesarios
    n = len(x)
    mean_x = np.mean(x)
    t_value = stats.t.ppf(0.975, df=n-2)  # 95% confianza

    # Error estándar residual
    residuals = y - (slope * x + intercept)
    s_err = np.sqrt(np.sum(residuals**2) / (n - 2))

    # Intervalo confianza
    conf = t_value * s_err * np.sqrt(
        1/n + (x_line - mean_x)**2 / np.sum((x - mean_x)**2)
    )

    upper = y_line + conf
    lower = y_line - conf

    # ---- FIGURA ----
    fig = go.Figure()

    # Scatter
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            name="Datos",
            marker=dict(
                size=4,
                opacity=0.65
            )
        )
    )

    # Banda de confianza
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([x_line, x_line[::-1]]),
            y=np.concatenate([upper, lower[::-1]]),
            fill="toself",
            fillcolor="rgba(100,100,100,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            name="IC 95%"
        )
    )

    # Línea regresión
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="Regresión",
            line=dict(width=3)
        )
    )

    # Métricas en gráfico
    fig.add_annotation(
        x=0.98,
        y=0.98,
        xref="paper",
        yref="paper",
        align="left",
        showarrow=False,
        text=(
            f"<b>R²</b> = {r_value**2:.3f}<br>"
            f"<b>p</b> = {p_value:.3e}<br>"
            f"<b>Slope</b> = {slope:.3f}"
        )
    )
    return fig
    
def tabla_aerotermia(df_final: pd.DataFrame) -> str:
    '''
    Renderiza en una tabla HTML para mostrar el dataframe que contine los datos de aerotermia.
    '''

    df_monthly1 = df_final.resample("ME").sum()
    df_monthly1["date"] = df_monthly1.index.strftime("%Y-%m")

    cols = ["Fecha", "Precio", "Energia"]
    df_print = df_monthly1.copy()
    df_print["Fecha"] = df_print["date"]
    df_print["Precio"] = df_monthly1["price"].map("{:.2f} €".format)
    df_print["Energia"] = df_monthly1["energy"].map("{:.2f} kWh".format)

    return render_df_proportional(
            df_print[cols],
            widths=[0.2, 0.4, 0.4], 
            width_percent=70
        )
