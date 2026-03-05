import pandas as pd
import sqlite3
from datetime import datetime
import plotly.graph_objects as go


def define_excedente( row):
    if row["general_Wh"] < 0:
        return {"excedente": row["general_Wh"] * -1, "consumo": row["solar_Wh"] + row["general_Wh"], "autoconsumo": row["solar_Wh"] + row["general_Wh"]}
    else:
        return {"excedente": 0, "consumo": row["general_Wh"] + row["solar_Wh"], "autoconsumo": row["solar_Wh"]}

def get_energia_mes( conn: sqlite3.Connection) -> pd.DataFrame:

    #Previous data recorded until
    query = "SELECT date, general_Wh,solar_Wh, power_Wp from SWIBE_v"
    swibe = pd.read_sql_query(query, conn, parse_dates=["date"])
    # Normalizar por potencia instalada
    swibe['solar_Wh'] = swibe['solar_Wh'] / swibe['power_Wp'] * 6.6
    swibe[["excedente_Wh", "consumo_Wh", "autoconsumo_Wh"]] = swibe.apply(define_excedente, axis=1, result_type="expand")
    swibe['date'] = pd.to_datetime(swibe['date'], format='%Y-%m-%d', errors='coerce')
    
    swibe['year'] = swibe['date'].dt.year
    swibe['month'] = swibe['date'].dt.month
    swibe.drop(columns=['date', 'power_Wp'], inplace=True)
    num_cols = swibe.select_dtypes(include="number").columns.drop(["year", "month"])
    swibe[num_cols] = swibe[num_cols] / 1000

    df_monthly = swibe.groupby([swibe["year"], swibe["month"]]).sum().reset_index()
    df_monthly_solar = df_monthly.pivot(index="year", columns ="month", values= "solar_Wh").reset_index()
    df_monthly_excedente = df_monthly.pivot(index="year", columns ="month", values= "excedente_Wh").reset_index()
    df_monthly_consumo = df_monthly.pivot(index="year", columns ="month", values= "consumo_Wh").reset_index()
    df_monthly_general = df_monthly.pivot(index="year", columns ="month", values= "general_Wh").reset_index()
    df_monthly_autoconsumo = df_monthly.pivot(index="year", columns ="month", values= "autoconsumo_Wh").reset_index()
    return df_monthly, df_monthly_solar, df_monthly_excedente, df_monthly_consumo, df_monthly_general, df_monthly_autoconsumo

def grafico_energia_mes(df_monthly: pd.DataFrame, title: str):
    # Compute min, mean, and max
    fila_actual = df_monthly["year"].max()
    col_actual = datetime.now().month
    df_sin_actual = df_monthly.copy()

    df_sin_actual.loc[df_sin_actual["year"] == fila_actual, col_actual] = pd.NA
    resumen = df_sin_actual.agg(["max", "mean", "min"])
    
    min_values = resumen.iloc[:, 1:].min(axis=0).tolist()   # Min per month
    mean_values = resumen.iloc[:, 1:].mean(axis=0).tolist() # Mean per month
    max_values = resumen.iloc[:, 1:].max(axis=0).tolist()   # Max per month
    df_current_year = df_monthly[df_monthly['year'] == datetime.now().year]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(1, 13)), y=df_current_year.iloc[0, 1:].tolist(), mode='lines+markers', name='Producción', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=list(range(1, 13)), y=min_values, mode='lines+markers', name='Mínimo', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=list(range(1, 13)), y=max_values, mode='lines+markers', name='Máximo', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=list(range(1, 13)), y=mean_values, mode='lines+markers', name='Promedio', line=dict(color='white', dash='dot')))
    fig.update_xaxes(
        type="category",
        tickmode="array",
        tickvals=list(range(1, 13)),
        ticktext=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    )
    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis_title="kWh",
        legend=dict(
                orientation="h",          # horizontal
                yanchor="top",
                y=-0.3,                   # desplaza la leyenda hacia abajo
                xanchor="center",
                x=0.5
            ),
    )
    return fig

def tabla_energia_mes(df_monthly: pd.DataFrame):
    df_monthly_t = df_monthly.pivot(index="year", columns ="month", values= "solar_Wh").reset_index()
    df_monthly_t["Total"] = df_monthly_t.iloc[:, 1:].sum(axis=1)
    return df_monthly_t
