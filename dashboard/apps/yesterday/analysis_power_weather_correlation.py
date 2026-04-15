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

def load_production_data(sql_engine):
    """
    Carga datos de producción desde SQL.
    Debe devolver columnas: datetime, production
    """
    query = "select datetime, solar_Wh, power_Wp from WIBEE where datetime > '2020-01-01' order by datetime"
    df = pd.read_sql(query, sql_engine, parse_dates = ["datetime"])
    df['production'] = df['solar_Wh'] / df['power_Wp'] * 6.6
    df = df.drop(columns=['power_Wp', 'solar_Wh'])
    return df

def load_weather_data(sql_engine):
    """
    Carga datos meteorológicos desde SQL.
    Debe devolver columnas: datetime, radiation, cloud_cover, temperature
    """
    query = 'select datetime, temperature, cloud_cover, direct_radiation as radiation from METEO order by datetime'
    #query = 'select date as datetime, temp as temperature, cloudcover as cloud_cover, solarradiation as radiation from VXSING_hours order by datetime'
    df = pd.read_sql(query, sql_engine, parse_dates = ["datetime"])
    return df

# ============================================================
# 2. UNIÓN Y PREPROCESADO
# ============================================================

def merge_datasets(df_prod, df_weather):
    """
    Une producción y meteorología por datetime.
    """
    df = pd.merge_asof(
        df_prod.sort_values("datetime"),
        df_weather.sort_values("datetime"),
        on="datetime",
        direction="nearest",
        tolerance=pd.Timedelta("5min")  # ajustable
    )
    return df.dropna()

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
def train_model_lr(df):
    
    #Alternativa lineal
    from sklearn.linear_model import LinearRegression
    X_simple = df[["radiation"]]
    y = df["production"]

    X_train, X_test, y_train, y_test = train_test_split(X_simple, y, test_size=0.2, random_state=42)

    model_lr = LinearRegression()
    model_lr.fit(X_train, y_train)
    preds_lr = model_lr.predict(X_test)

    metrics = {
        "r2": r2_score(y_test, preds_lr),
        "mae": mean_absolute_error(y_test, preds_lr),
        "feature_importance": dict(zip(X_simple.columns, model_lr.coef_))
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
    X = df[["radiation"]]
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
# ============================================================
# 4. PREDICCIÓN FUTURA
# ============================================================

def predict_future(model, df_future_weather):
    """
    df_future_weather debe contener:
    radiation, cloud_cover, temperature
    """
    df_future_weather = df_future_weather.copy()
    df_future_weather["predicted_production"] = model.predict(df_future_weather[["temperature", "cloud_cover","radiation"]])
    return df_future_weather

def power_weather_correlation( conn):
    # 1. Cargar datos
    df_prod = load_production_data(conn)
    df_weather = load_weather_data(conn)

    # 2. Unir
    df = merge_datasets(df_prod, df_weather)

    # 3. Limpiar
    df = clean_dataset(df)

    # 4. Entrenar
    model, metrics = train_model_rf(df)
    print(metrics)

    # 5. Predecir futuro
    CASA = dict(lat=40.5661,lon=3.8998)
    df_long, error = get_meteo_7D(CASA['lat'], CASA['lon'], 45)
    df_short = get_meteo_hours(df_long, 24)
    df_weather_forecast = df_short.rename(columns={
        "temperature_2m":"temperature",
        "direct_radiation":"radiation",
    })
    print("Datos meteorológicos para predicción futura:\n", df_weather_forecast.head())
    df_weather_forecast["time_local"] = (df_weather_forecast["date"].dt.tz_convert("Europe/Madrid"))
    df_weather_forecast = df_weather_forecast.drop(columns=['precipitation_probability','weather_code','date','time'])

    df_future = predict_future(model, df_weather_forecast)
    print(df_future)
    return df_future

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

def grafico_prediccion_simple(conn):
    # 1. Cargar datos
    df_prod = load_production_data(conn)
    df_weather = load_weather_data(conn)

    # 2. Unir
    df = merge_datasets(df_prod, df_weather)

    # 3. Limpiar
    df = clean_dataset(df)
    # Rango para las líneas de regresión
    rad_range = np.linspace(df["radiation"].min(), df["radiation"].max(), 300).reshape(-1, 1)

    model_lr, metrics_lr = train_model_lr(df)
    model_rf, metrics_rf = train_model_rf(df)

    pred_lr = model_lr.predict(rad_range)
    pred_rf = model_rf.predict(rad_range)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["radiation"],
        y=df["production"],
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

    fig.add_trace(go.Scatter(
        x=rad_range.flatten(),
        y=pred_rf,
        mode="lines",
        line=dict(color="green", width=2),
        name=f"RandomForest (R²={metrics_rf['r2']:.3f})"
    ))

    fig.update_layout(
        title="Relación radiación → producción",
        xaxis_title="Radiación directa (W/m²)",
        yaxis_title="Producción (Wh)",
        template="plotly_white"
    )

    return fig