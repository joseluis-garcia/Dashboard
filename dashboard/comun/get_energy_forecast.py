"""
Módulo para obtener predicciones de energia basandose en predicciones meteorologicas.

Proporciona funciones para:
- Calcular produccion fotovoltaica segun "temperature", "cloud_cover","direct_radiation", "hora"
- Hay que darle coordenadas de localizacion
- Para la prevision puede usar RandomForest o LinearRegression
"""

import os
import sqlite3
from datetime import datetime, timedelta

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from dashboard.comun.sql_utilities import read_sql_ts
import dashboard.apps.config as TCB

def load_production_data(conn: sqlite3.Connection):
    """
    Carga datos de producción desde table WIBEE.
    Debe devolver columnas: datetime, production
    """

    query = "select datetime, solar_Wh, power_Wp from WIBEE order by datetime"
    df, error = read_sql_ts(query, conn)
    #df = pd.read_sql(query, conn, parse_dates = ["datetime"])
    # Normalizamos la produccion en funcion de la potencia pico de cada dato "power_Wp" con la instalada actual
    df['production'] = df['solar_Wh'] / df['power_Wp'] * TCB.CURRENT_PEAK_POWER
    df = df.drop(columns=['power_Wp', 'solar_Wh'])
    #df = df.set_index("datetime").sort_index()


    print("NaTs in WIBEE",df[df.index.isna()])







    return df

def load_weather_data(conn: sqlite3.Connection):
    """
    Carga datos meteorológicos desde SQL.
    Debe devolver columnas: datetime, radiation, cloud_cover, temperature
    """
    query = 'select datetime, temperature, cloud_cover, direct_radiation from METEO order by datetime'
    df, error = read_sql_ts(query, conn)
    # df = pd.read_sql(query, sql_engine, parse_dates = ["datetime"])
    # df = df.set_index("datetime").sort_index()
    return df

# ============================================================
# 2. UNIÓN Y PREPROCESADO
# ============================================================

def clean_dataset(df):
    """
    Limpieza básica:
    - eliminar noches
    - eliminar outliers
    """
    df = df[df["production"] > 0]
    df = df[df["production"] < df["production"].quantile(0.99)]
    return df

# ============================================================
# 3. ENTRENAMIENTO DEL MODELO
# ============================================================

def train_model(conn, method):
    """
    Entrena un RandomForest y devuelve el modelo y métricas.
    """
    # 1. Cargar datos
    df_prod = load_production_data(conn)

    df_weather = load_weather_data(conn)

    # 2. Unir
    df = pd.merge_asof(
        df_prod,
        df_weather,
        left_index=True,
        right_index=True,
        direction="nearest",
        tolerance=pd.Timedelta("5min")  # ajustable
    ).dropna()

    # 3. Limpiar
    df = clean_dataset(df)

    df["hora"] = df.index.hour + df.index.minute / 60.0
    y = df["production"]

    print("Buiding model with method", method)
    if method == "rf":
        X = df[["temperature", "cloud_cover","direct_radiation", "hora"]]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            random_state=42
        )
    else:
        X = df[["direct_radiation"]]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    if method == "rf":
        metrics = {
            "r2": r2_score(y_test, preds),
            "mae": mean_absolute_error(y_test, preds),
            "feature_importance": dict(zip(X.columns, model.feature_importances_))
        }
    else:
        metrics = {
            "r2": r2_score(y_test, preds),
            "mae": mean_absolute_error(y_test, preds),
    }
    print("Métricas del modelo:", metrics)
    return model, metrics

# ============================================================
# 4. PREDICCIÓN FUTURA
# ============================================================

def predict_future(conn, df_future_weather, method):
    """
    df_future_weather debe contener:
    radiation, cloud_cover, temperature
    """
    model, metrics = power_weather_correlation(conn, method)

    df_future_energy = df_future_weather.copy()
    if method == "rf":
        df_future_energy["predicted_production"] = model.predict(df_future_weather[["temperature", "cloud_cover","direct_radiation","hora"]])
    else:
        df_future_energy["predicted_production"] = model.predict(df_future_weather[["direct_radiation"]])

    df_future_energy.index = df_future_energy.index.hour
    return df_future_energy, None

def power_weather_correlation( conn, method):
    # Verificamos si el modelo ya está cacheado, si no lo entrenamos y cacheamos
    if not hasattr(power_weather_correlation, "model_cache"): 
        print("power_weather no tiene cache")
        power_weather_correlation.model_cache, metrics = train_model(conn, method=method)

    model = power_weather_correlation.model_cache

    # Verificamos si el modelo está guardado en disco y es reciente, si no lo entrenamos y guardamos
    modelo_path = "modelo_energia.pkl"
    debe_reentrenar = (
        not os.path.exists(modelo_path) or
        datetime.fromtimestamp(os.path.getmtime(modelo_path)) < datetime.now() - timedelta(days=7)
    )
    if debe_reentrenar:
        # entrenar y guardar
        model_cache, metrics = train_model(conn, method=method)
        joblib.dump({"model": model_cache, "metrics": metrics}, modelo_path)
    else:
        pre_model = joblib.load(modelo_path)
        print("Modelo cargado de disco con métricas", pre_model)
        model = pre_model["model"]
        metrics = pre_model["metrics"]

    return model, metrics

# def grafico_prediccion(fig, df):
#     #fig = go.Figure()

#     fig.add_trace(go.Scatter(
#         x=df["time_local"],
#         y=df["predicted_production"],
#         mode="lines+markers",
#         name="Producción prevista",
#         line=dict(color="orange", width=2),
#         marker=dict(size=4)
#     ))

#     fig.update_layout(
#         title="Producción Fotovoltaica Prevista",
#         xaxis_title="Hora",
#         yaxis_title="Producción (Wh)",
#         template="plotly_white",
#         hovermode="x unified"
#     )

#     return fig