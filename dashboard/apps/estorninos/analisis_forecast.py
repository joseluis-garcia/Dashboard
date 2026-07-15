"""
Tab de Estorninos: calidad de las previsiones ESIOS.

Compara forecast_snapshots vs real_values y muestra métricas y gráficas
interactivas dentro de Streamlit. Diseñado para colgar de un st.tabs()
en app_Estorninos.py, ver instrucciones de integración al final del fichero.
"""

import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Pares (indicador de previsión -> indicador real). Ajusta nombres/IDs si no
# corresponden exactamente a como los tienes etiquetados en tu pipeline.
INDICATOR_PAIRS = {
    541: {"real_id": 551, "name": "Eólica"},
    542: {"real_id": 1295, "name": "Solar"},
    603: {"real_id": 1293, "name": "Demanda"},
}


# --- Carga y preparación (cacheado 1h, igual que el resto del dashboard) ---
@st.cache_data(ttl=3600, show_spinner="Cargando histórico de previsiones...")
def _cargar_datos(db_path: str):
    conn = sqlite3.connect(db_path)
    forecasts = pd.read_sql(
        "SELECT * FROM forecast_snapshots", conn,
        parse_dates=["fetch_ts", "target_datetime"],
    )
    reales = pd.read_sql(
        "SELECT * FROM real_values", conn, parse_dates=["datetime"]
    )
    conn.close()
    return forecasts, reales


def _construir_dataset(forecasts: pd.DataFrame, reales: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for fc_id, info in INDICATOR_PAIRS.items():
        real_id = info["real_id"]
        f = forecasts[forecasts.indicator_id == fc_id].copy()
        r = reales[reales.indicator_id == real_id][["datetime", "value"]].rename(
            columns={"value": "valor_real"}
        )
        if f.empty or r.empty:
            continue
        merged = f.merge(r, left_on="target_datetime", right_on="datetime", how="inner")
        merged["indicador"] = info["name"]
        frames.append(merged)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["error"] = df["value"] - df["valor_real"]
    df["error_abs"] = df["error"].abs()
    df["error_pct"] = np.where(
        df["valor_real"].abs() > 1e-6, df["error"] / df["valor_real"] * 100, np.nan
    )
    return df


# --- Métricas (formato "long" para que Plotly Express las pinte directo) ---
def _resumen_metricas(df: pd.DataFrame) -> pd.DataFrame:
    resumen = df.groupby("indicador").agg(
        n=("error", "size"),
        MAE=("error_abs", "mean"),
        RMSE=("error", lambda s: np.sqrt((s ** 2).mean())),
        Sesgo=("error", "mean"),
        MAPE=("error_pct", lambda s: s.abs().mean()),
    ).round(2)
    return resumen


def _error_por_horizonte_long(df: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 6, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180]
    df = df.copy()
    df["horizon_bin"] = pd.cut(df["horizon_hours"], bins=bins)
    tabla = df.groupby(["indicador", "horizon_bin"], observed=True)["error_abs"].agg(
        MAE="mean", n="size"
    ).reset_index()
    tabla["horizonte"] = tabla["horizon_bin"].apply(lambda iv: iv.right)
    return tabla

def _error_por_hora_long(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hora"] = df["target_datetime"].dt.hour
    tabla = df.groupby(["indicador", "hora"])["error_abs"].mean().reset_index()
    return tabla.rename(columns={"error_abs": "MAE"})


def _primera_vs_ultima(df: pd.DataFrame) -> pd.DataFrame:
    idx_ultima = df.groupby(["indicador", "target_datetime"])["horizon_hours"].idxmin()
    idx_primera = df.groupby(["indicador", "target_datetime"])["horizon_hours"].idxmax()

    ultima = df.loc[idx_ultima, ["indicador", "target_datetime", "error_abs", "horizon_hours"]]
    ultima = ultima.rename(columns={"error_abs": "MAE_ultima", "horizon_hours": "horizonte_ultima"})

    primera = df.loc[idx_primera, ["indicador", "target_datetime", "error_abs", "horizon_hours"]]
    primera = primera.rename(columns={"error_abs": "MAE_primera", "horizon_hours": "horizonte_primera"})

    comp = ultima.merge(primera, on=["indicador", "target_datetime"])
    comp = comp[comp["horizonte_primera"] > comp["horizonte_ultima"]]

    resumen = comp.groupby("indicador").agg(
        horizonte_medio_primera=("horizonte_primera", "mean"),
        horizonte_medio_ultima=("horizonte_ultima", "mean"),
        MAE_primera=("MAE_primera", "mean"),
        MAE_ultima=("MAE_ultima", "mean"),
    ).round(2)
    resumen["mejora_%"] = ((1 - resumen["MAE_ultima"] / resumen["MAE_primera"]) * 100).round(1)
    return resumen


# --- Render principal, para llamar desde un st.tabs() -----------------------
def mostrar_tab_analisis_forecast(db_path: str = "forecast_tracker.db"):

    print(f"Mostrando análisis de calidad para {db_path}")
    st.subheader("📈 Calidad de las previsiones ESIOS")

    try:
        forecasts, reales = _cargar_datos(db_path)
        # print("FORECAST", forecasts.tail())
        # print("REALES", reales.tail())
        
    except Exception as e:
        st.error(f"No se pudo abrir la base de datos de previsiones: {e}")
        return

    df = _construir_dataset(forecasts, reales)
    if df.empty:
        st.warning(
            "No hay datos cruzados entre previsión y real todavía. "
            "Revisa que los IDs de indicador en INDICATOR_PAIRS coincidan con los tuyos."
        )
        return

    st.caption(
        f"{len(df)} registros cruzados · captura desde "
        f"{df['fetch_ts'].min():%d/%m %H:%M} hasta {df['fetch_ts'].max():%d/%m %H:%M}"
    )

    st.markdown("**Resumen por indicador**")
    st.dataframe(_resumen_metricas(df), width='stretch', height=300)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Error medio según antelación de la previsión**")
        tabla_h = _error_por_horizonte_long(df)
        print("TABLA HORIZONTE", tabla_h.head())
        fig_h = px.line(
            tabla_h, x="horizonte", y="MAE", color="indicador", markers=True, hover_data=["n"],
            labels={"horizonte": "Horas de antelación", "MAE": "Error absoluto medio"},
        )
        st.plotly_chart(fig_h, width='stretch')

    with col2:
        st.markdown("**Error medio por hora del día**")
        tabla_hora = _error_por_hora_long(df)
        fig_hora = px.line(
            tabla_hora, x="hora", y="MAE", color="indicador", markers=True,
            labels={"hora": "Hora del día", "MAE": "Error absoluto medio"},
        )
        st.plotly_chart(fig_hora, width='stretch')

    st.markdown("**Distribución de errores (previsión − real)**")
    fig_box = px.box(df, x="indicador", y="error", points=False)
    st.plotly_chart(fig_box, width='stretch')

    st.markdown("**¿Mejora la previsión al acercarse la hora real?**")
    st.caption("Compara la primera vez que se predijo cada hora (mayor antelación) frente a la última (más próxima al momento real).")
    st.dataframe(_primera_vs_ultima(df), width='stretch', height=300)

    st.markdown("**Serie temporal: previsión más reciente vs valor real**")
    indicador_sel = st.selectbox("Indicador", sorted(df["indicador"].unique()), key="analisis_forecast_indicador")
    sub = df[df.indicador == indicador_sel].sort_values(["target_datetime", "horizon_hours"])
    ultima = sub.groupby("target_datetime").first().reset_index()

    fig_serie = go.Figure()
    fig_serie.add_trace(go.Scatter(x=ultima["target_datetime"], y=ultima["valor_real"], name="Real", line=dict(width=2)))
    fig_serie.add_trace(go.Scatter(x=ultima["target_datetime"], y=ultima["value"], 
                                   name="Previsión (más reciente)", 
                                   line=dict(width=2, dash="dash", color="#FFA15A")))
    fig_serie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig_serie, width='stretch')


# --- Cómo integrarlo en app_Estorninos.py -----------------------------------
#
# from dashboard.apps.estorninos.analisis_forecast import mostrar_tab_analisis_forecast
#
# tab_agenda, tab_mensajes, tab_calidad = st.tabs(
#     ["Agenda semanal", "Mensajes", "Calidad de previsión"]
# )
#
# with tab_calidad:
#     mostrar_tab_analisis_forecast(db_path="ruta/a/tu/forecast_tracker.db")
#
# Ajusta los nombres/orden de las pestañas existentes a como las tengas ya
# definidas en tu app_Estorninos.py actual.
