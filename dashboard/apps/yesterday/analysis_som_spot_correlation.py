import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dashboard.comun.costes_regulados import costes_regulados
from dashboard.comun.sql_utilities import read_sql_ts

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error


# ============================================================
# 1. CARGA DE DATOS DESDE SQL
# ============================================================

def load_ESIOS_prices(sql_engine):
    """
    Carga datos de producción desde SQL.
    Debe devolver columnas: datetime, production
    """
    query = 'select datetime, "Mercado SPOT" as spot from ESIOS_prices where datetime < "2025-01-01" order by datetime'
    df, error = read_sql_ts(query, sql_engine)

    if error:
        print(f"Error al cargar datos de ESIOS: {error}")
        return None

    return df

def load_Som_data(sql_engine):
    """
    Carga datos de precios Som desde SQL.
    Debe devolver columnas: datetime, production
    """
    query = 'select datetime, price as som from SOM_precios_indexada_real order by datetime'
    df, error = read_sql_ts(query, sql_engine)

    if error:
        print(f"Error al cargar datos de Som: {error}")
        return None

    return df

# ============================================================
# 3. ENTRENAMIENTO DEL MODELO
# ============================================================
def train_model_lr(df):
    
    #Alternativa lineal
    from sklearn.linear_model import LinearRegression
    X_simple = df[["spot"]]
    y = df["som"]

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

def predict_future(model, df_future_weather):
    """
    df_future_weather debe contener:
    radiation, cloud_cover, temperature
    """
    df_future_weather = df_future_weather.copy()
    df_future_weather["predicted_production"] = model.predict(df_future_weather[["temperature", "cloud_cover","radiation"]])
    return df_future_weather

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

def grafico_prediccion_precios(conn):

    df_spot = load_ESIOS_prices(conn)
    df_spot = df_spot[df_spot.index.year >= 2024]

    df_spot = costes_regulados(df_spot) 
    df_som = load_Som_data(conn) * 1000
    df_spot = df_spot[df_spot.index.year >= 2024]

    df_som = costes_regulados(df_som)

    df = pd.merge_asof(
        df_spot.sort_values("datetime"),
        df_som.sort_values("datetime"),
        on="datetime",
        direction="nearest",
        tolerance=pd.Timedelta("5min")  # ajustable
    )
    print("Datos combinados SPOT-SOM:\n", df['datetime'].min(), df['datetime'].max(), df.head())
    df = df.dropna()

    spot_range = np.linspace(df["spot"].min(), df["spot"].max(), 300).reshape(-1, 1)

    model_lr, metrics_lr = train_model_lr(df)
    pred_lr = model_lr.predict(spot_range)
    print("Métricas modelo lineal:", metrics_lr)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["spot"],
        y=df["som"],
        mode="markers",
        marker=dict(size=4, opacity=0.3),
        name="Datos reales"
    ))

    fig.add_trace(go.Scatter(
        x=spot_range.flatten(),
        y=pred_lr,
        mode="lines",
        line=dict(color="red", width=2),
        name=f"Lineal (R²={metrics_lr['r2']:.3f})"
    ))

    fig.update_layout(
        title="Relación radiación → producción",
        xaxis_title="Precio Mercado SPOT",
        yaxis_title="Precio SOM",
        template="plotly_white"
    )

    return fig