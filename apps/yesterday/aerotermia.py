import streamlit as st
import pandas as pd
import scipy.stats as stats
import plotly.graph_objects as go
import numpy as np
from comun.mensaje import render_df_proportional

def cleanSolar( row):
    return row['extra_Wh'] - row['solar_Wh'] if row['extra_Wh'] > row['solar_Wh'] else 0

def get_aerotermia_data( conn):
    #Previous data recorded until
    query = "SELECT date, solar_Wh, extra_Wh from SWIBE_v where extra_Wh > 15 and extra='{0}'".format('AEROTERMIA')
    swibe = pd.read_sql_query(query, conn, parse_dates=["date"])
    swibe["datetime"] = pd.to_datetime(swibe["date"])
    swibe['energy'] = swibe.apply( cleanSolar, axis = 1)
    swibe["energy"] = swibe["energy"] / 1000 # Convertir a kWh
    swibe = swibe[["datetime", "energy"]]

    aeroMin = swibe['datetime'].min()
    aeroMax = swibe['datetime'].max()
    st.write(f"SWIBE since {aeroMin} to {aeroMax}")

    query = "SELECT * from precios_indexada_som"
    prices = pd.read_sql_query(query, conn)
    prices['precio'] = pd.to_numeric(prices['precio'], errors='coerce')
    prices['precio'] = prices['precio'] * 1.21
    prices['datetime'] = pd.to_datetime(prices['datetime'])

    pricesMin = prices['datetime'].min()
    pricesMax = prices['datetime'].max()
    st.write(f"PRICES since {pricesMin} to {pricesMax}")

    dateMin = max(pricesMin, aeroMin)
    dateMax = min(pricesMax, aeroMax)
    st.write(f"Using data from {dateMin} to {dateMax}")

    df_energy = swibe[(swibe['datetime'] >= dateMin) & (swibe['datetime'] <= dateMax)]
    df_prices = prices[(prices['datetime'] >= dateMin) & (prices['datetime'] <= dateMax)]

    # Set the date columns as index to align both DataFrames on date
    df_energy.set_index('datetime', inplace=True)
    df_prices.set_index('datetime', inplace=True)

    df_cost=pd.merge(df_prices, df_energy, left_index=True, right_index=True, how='inner')
    # Perform the multiplication on the numeric columns only
    df_cost["cost"] = df_cost["precio"] * df_cost["energy"]

    # Reset the index to bring 'date' back as a column
    df_cost.reset_index(inplace=True)

    #Get weather data from VXSING
    query = "SELECT date as datetime, temp from VXSING_hours where datetime >= '{0}' and datetime <= '{1}'".format(dateMin, dateMax)
    df_temp = pd.read_sql_query(query, conn, parse_dates=['datetime'])
    df_temp['datetime'] = pd.to_datetime(df_temp['datetime'])
    df_final = pd.merge(df_cost, df_temp, on='datetime', how='inner')
    return df_final

def grafico_aerotermia(df_final):
    # Datos
    df_final = df_final.set_index("datetime")
    df_final = df_final[df_final['energy'] > 1.6]
    daily_energy = df_final["energy"].resample("D").sum() 
    daily_temp = df_final["temp"].resample("D").mean() 
    df_daily = pd.DataFrame({ "energy_sum": daily_energy, "temp_mean": daily_temp }).dropna()
    fig =  regresion(df_daily, "temp_mean", "energy_sum")
        # Layout profesional
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

    df_monthly1 = df_final.resample("ME", on="datetime").sum()
    df_monthly1["date"] = df_monthly1.index.strftime("%Y-%m")

    cols = ["Fecha", "Precio", "Energia"]
    df_print = df_monthly1.copy()
    df_print["Fecha"] = df_print["date"]
    df_print["Precio"] = df_monthly1["precio"].map("{:.2f} €".format)
    df_print["Energia"] = df_monthly1["energy"].map("{:.2f} kWh".format)

    return render_df_proportional(
            df_print[cols],
            widths=[0.2, 0.4, 0.4], 
            width_percent=70
        )
