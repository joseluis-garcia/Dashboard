"""
Módulo para obtener y visualizar predicciones de precios de energía.

Proporciona funciones para:
- Calcular precios estimados basados en energía renovable y demanda
- Agregar costes regulados
- Visualizar precios estimados vs spot
"""

import sqlite3
import streamlit as st

from typing import Optional, Tuple
import pandas as pd
import os
from datetime import datetime, timedelta
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

from dashboard.comun import date_conditions as dc
import dashboard.comun.sql_utilities as db
from dashboard.comun.costes_regulados import costes_regulados
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_forecast, get_ESIOS_spot, get_ESIOS_data_from_measurements

def train_model_lr(df):
    
    #Alternativa lineal
    from sklearn.linear_model import LinearRegression
    X_simple = df[["Renovable_pct"]]
    y = df["Mercado SPOT"]

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

def train_model_rf(df):
    """
    Entrena un RandomForest y devuelve el modelo y métricas.
    """
    X = df[["Eólica", "Solar fotovoltaica", "Demanda real"]]
    y = df["Mercado SPOT"]

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

def clean_dataset(df):
    """
    Limpieza básica:
    - eliminar noches
    - eliminar outliers
    """
    #df = df[df["spot"] > 0]
    df = df[df["Mercado SPOT"] < df["Mercado SPOT"].quantile(0.95)]
    return df

@st.cache_data
def get_prices_forecast(_conn: sqlite3.Connection, rango: dc.RangoFechas, method: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Calcula precios estimados a partir de energía renovable y demanda.
    
    Segun al method elegido, se entrena un modelo de regresión lineal o Random Forest con datos históricos de ESIOS.
    Luego agrega costes regulados para obtener precio final estimado.
    
    Args:
        conn: Conexión a la base de datos SQLite
        rango: Rango de fechas para filtrar los datos
        method: Método de predicción ("lr" para regresión lineal, "rf" para Random Forest)
        
    Returns:
        Tupla (dataframe, error) donde:
        - dataframe: Index(['Solar fotovoltaica', 'Eólica', 'Demanda real', 'renovable',
            'Mercado SPOT', 'precio_estimado', 'periodo', 'peaje', 'cargo',
            'capacidad', 'costes_regulados'] o None si falla
        - error: None si es exitoso, mensaje de error si falla
        
    Example:
        >>> df_prices = get_prices_forecast(conn, rango, method)
        >>> print(df_prices.head())
    """
    #Verifica si existe un modelo precalculado vigente. Se basa en que los datos utilizados para entrenar el modelo ESIOS_data sean mas modernos que la ultima vez que se creo el modelo para detrminar si es necesario o no.
    modelo_path = "modelo_prices.pkl"

    if os.path.exists(modelo_path):
        df_tablas, error = db.get_tables_info(_conn, ["ESIOS_data"])
        last_record = df_tablas.loc[df_tablas['Tabla'] == 'ESIOS_data', 'Hasta'].values[0]
        pre_model_data = joblib.load(modelo_path)
        
        pre_method = pre_model_data["method"]
        pre_model = pre_model_data["model"]
        pre_metrics = pre_model_data["metrics"]

        print(f"Modelo anterior en disco datos hasta {last_record} con metodo {pre_method}")
        debe_reentrenar = (
            datetime.fromtimestamp(os.path.getmtime(modelo_path)) < datetime.strptime(last_record, "%Y-%m-%d %H:%M:%S") or
            method != pre_method 
        )
    else:
        debe_reentrenar = True

    print("Debe reentrenar:", debe_reentrenar)
    if debe_reentrenar:
        df, error = get_ESIOS_data_from_measurements(_conn, None) # Solo para cargar datos y entrenar el modelo, no se usa directamente en el forecast
        if error:
            return None, error
        
        df['Renovable_pct'] = (df['Eólica'] + df['Solar fotovoltaica']) / df['Demanda real']
        df = clean_dataset(df)
        
        if method == "rf":
            print("Obteniendo precios con Random Forest...")
            model, metrics = train_model_rf(df)
            print(metrics)
        else:
            print("Obteniendo precios con regresión lineal...")
            model, metrics = train_model_lr(df)
            print(metrics)

        joblib.dump({"method": method, "model": model, "metrics": metrics}, modelo_path)
    else:
        model = pre_model
        metrics = pre_model

    #Obetenemos los datos futuros de los predictores del modelo que son "Eólica", "Solar fotovoltaica", "Demanda real" para RandomForest y porcentaje de ()"Eólica" + "Solar) /  "Demanda real" para linearRegresion
    df_energy, error = get_ESIOS_energy_forecast(rango)
    if error:
        return None, error
    
    df_spot, error = get_ESIOS_spot(rango)
    if error:
        return None, error
    
    # Combinar energía y spot
    df_final = df_energy.join(df_spot, how="outer")
    # Calcular % de EO + FV sobre la demanda total para la regresion lineal
    df_final["Renovable_pct"] = df_final["Renovable"] / (df_final["Previsión semanal"] + 1e-8)  # Evitar división por cero
    df_final = df_final.rename(columns={"Previsión semanal": "Demanda real", "Previsión eólica": "Eólica"})

    #Realiza la prediccion
    if method == "rf":
        # Predecir precios usando el modelo Random Forest
        X_pred = df_final[["Eólica", "Solar fotovoltaica", "Demanda real"]].fillna(0)

    else:
        # Predecir precios usando regresión lineal
        X_pred = df_final[["Renovable_pct"]].fillna(0)

    df_final["precio_estimado"] = model.predict(X_pred)

    # Agregar costes regulados
    df_final = costes_regulados(df_final)
    
    # Sumar costes regulados a precios (spot y estimado)
    df_final["precio_estimado"] += df_final["costes_regulados"]
    df_final["Mercado SPOT"] += df_final["costes_regulados"]

    return df_final, None

__all__ = ["get_prices_forecast"]
