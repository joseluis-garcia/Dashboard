import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dashboard.comun.sql_utilities import read_sql_ts

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

from dashboard.comun.get_openmeteo import get_meteo_7D, get_meteo_hours

# ============================================================
# 1. CARGA DE DATOS DESDE SQL
# ============================================================

def load_ESIOS_data(sql_engine):
    """
    Carga datos de producción desde SQL.
    Debe devolver columnas: datetime, production
    """
    query = 'select datetime, Eólica as eolica, "Solar Fotovoltaica" as solar, "Mercado SPOT" as spot, "Demanda Real" as demanda from ESIOS_data order by datetime'
    df = pd.read_sql(query, sql_engine, parse_dates = ["datetime"])

    df['renovable'] = (df['eolica'] + df['solar']) / df['demanda']
    print("Filas con problemas:",df[df.isna().any(axis=1)])
    df = df.dropna(subset=['eolica', 'solar', 'demanda'])

    return df

# ============================================================
# 3. ENTRENAMIENTO DEL MODELO
# ============================================================
def train_model_lr(df):
    
    #Alternativa lineal
    from sklearn.linear_model import LinearRegression
    X_simple = df[["renovable"]]
    y = df["spot"]

    X_train, X_test, y_train, y_test = train_test_split(X_simple, y, test_size=0.2, random_state=42)

    model_lr = LinearRegression()
    model_lr.fit(X_train, y_train)
    preds_lr = model_lr.predict(X_test)

    metrics = {
        "r2": r2_score(y_test, preds_lr),
        "mae": mean_absolute_error(y_test, preds_lr),
        "Pendiente": model_lr.coef_[0],
        "Ordenada origen": model_lr.intercept_,
    }

    return model_lr, metrics

def train_model_rf_full(df):
    """
    Entrena un RandomForest y devuelve el modelo y métricas.
    """
    X = df[["temperature", "cloud_cover","radiation"]]
    y = df["production"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "r2": r2_score(y_test, preds),
        "mae": mean_absolute_error(y_test, preds),
        "feature_importance": dict(zip(X.columns, model.feature_importances_))
    }
    return model, metrics

def train_model_rf(df):
    """
    Entrena un RandomForest y devuelve el modelo y métricas.
    """
    X = df[["eolica", "solar", "demanda"]]
    y = df["spot"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "r2": r2_score(y_test, preds),
        "mae": mean_absolute_error(y_test, preds),
        "feature_importance": dict(zip(X.columns, model.feature_importances_))
    }
    return model, metrics
# ============================================================
# 4. PREDICCIÓN FUTURA
# ============================================================
def clean_dataset(df):
    """
    Limpieza básica:
    - eliminar noches
    - eliminar outliers
    """
    #df = df[df["spot"] > 0]
    df = df[df["spot"] < df["spot"].quantile(0.95)]
    return df

def predict_future(model, df_future_weather):
    """
    df_future_weather debe contener:
    radiation, cloud_cover, temperature
    """
    df_future_weather = df_future_weather.copy()
    df_future_weather["predicted_production"] = model.predict(df_future_weather[["temperature", "cloud_cover","radiation"]])
    return df_future_weather

# def power_weather_correlation( conn):
#     # 1. Cargar datos
#     df_prod = load_production_data(conn)
#     df_weather = load_weather_data(conn)

#     # 2. Unir
#     df = merge_datasets(df_prod, df_weather)

#     # 3. Limpiar
#     df = clean_dataset(df)

#     # 4. Entrenar
#     model, metrics = train_model_rf(df)
#     print(metrics)

#     # 5. Predecir futuro
#     CASA = dict(lat=40.5661,lon=3.8998)
#     df_long, error = get_meteo_7D(CASA['lat'], CASA['lon'], 45)
#     df_short = get_meteo_hours(df_long, 24)
#     df_weather_forecast = df_short.rename(columns={
#         "temperature_2m":"temperature",
#         "direct_radiation":"radiation",
#     })
#     print("Datos meteorológicos para predicción futura:\n", df_weather_forecast.head())
#     df_weather_forecast["time_local"] = (df_weather_forecast["date"].dt.tz_convert("Europe/Madrid"))
#     df_weather_forecast = df_weather_forecast.drop(columns=['precipitation_probability','weather_code','date','time'])

#     df_future = predict_future(model, df_weather_forecast)
#     print(df_future)
#     return df_future

def grafico_prediccion_full( df):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time_local"],
        y=df["predicted_production"],
        mode="lines+markers",
        name="Producción prevista",
        line=dict(color="orange", width=2),
        marker=dict(size=4)
    ))

    fig.update_layout(
        title="Producción Fotovoltaica Prevista",
        xaxis_title="Hora",
        yaxis_title="Producción (Wh)",
        template="plotly_white",
        hovermode="x unified"
    )

    return fig

def grafico_prediccion_energia(conn):
    # 1. Cargar datos
    df = load_ESIOS_data(conn)
    df = clean_dataset(df)

    rad_range = np.linspace(df["renovable"].min(), df["renovable"].max(), 300).reshape(-1, 1)

    model_lr, metrics_lr = train_model_lr(df)
    model_rf, metrics_rf = train_model_rf(df)

    print("Métricas modelo lineal:", metrics_lr)
    print("Métricas modelo RF:", metrics_rf)

    pred_lr = model_lr.predict(rad_range)
    #pred_rf = model_rf.predict(rad_range)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["renovable"],
        y=df["spot"],
        mode="markers",
        marker=dict(size=4, opacity=0.3),
        name="Datos reales"
    ))

    fig.add_trace(go.Scatter(
        x=rad_range.flatten(),
        y=pred_lr,
        mode="lines",
        line=dict(color="red", width=2),
        name=f"Lineal (R²={metrics_lr['r2']:.3f})"
    ))

    # fig.add_trace(go.Scatter(
    #     x=rad_range.flatten(),
    #     y=pred_rf,
    #     mode="lines",
    #     line=dict(color="green", width=2),
    #     name=f"RandomForest (R²={metrics_rf['r2']:.3f})"
    # ))

    fig.update_layout(
        title="Relación radiación → producción",
        xaxis_title="% Renovable vs Demanda",
        yaxis_title="Precio Mercado SPOT",
        template="plotly_white"
    )

    return fig