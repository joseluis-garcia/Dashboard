import streamlit as st
import pandas as pd
from dashboard.comun.safe_request import safe_request_get
from dashboard.comun.date_conditions import RangoFechas
# =========================
# FUNCIÓN DE DESCARGA indicadores ESIOS
# =========================

API_TOKEN = st.secrets["ESIOS_token"]
BASE_URL = "https://api.esios.ree.es/indicators"

headers = {
    "x-api-key": f"{API_TOKEN}",
    "Accept": "application/json;  application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "Host":"api.esios.ree.es",
    "Cookie":""
}

def get_indicator(indicator_id: list[int], date_range: RangoFechas, time_trunc: str = None):

#======
# Alias Frecuencia
# 'min' o 'T'Minuto'
# 5min'5 minutos
# '15min'15 minutos
# 'h' o 'H' Hora
# 'D'Día
# 'W'Semana
# 'ME'Fin de mes
# 'MS'Inicio de mes
# 'QE'Fin de trimestre
# 'YE'Fin de año
# 'YS'Inicio de año
#======

    url = f"{BASE_URL}/{indicator_id}"

    if time_trunc is not None:
        date_range["time_trunc"] = time_trunc

    response, error = safe_request_get(url, headers=headers, params=date_range)
    if error:
        st.error(f"No se han podido obtener los datos del indicador {indicator_id}.")
        st.error(error)
        return None, error  # Devuelve un DataFrame vacío en caso de error

    json_data = response.json()
    data = json_data["indicator"]["values"]
    variable = json_data["indicator"]["short_name"]

    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["datetime"] = df["datetime"].dt.tz_localize(None)
    df = df.set_index("datetime").sort_index()

    #Como los distintos indicators vienen con diferente timestamp y la funcion de agregación de ESIOS (time_trunc) no garantiza que metodo utiliza debemos hacerlo nosotros
    df_hourly = df.select_dtypes(include='number').resample(time_trunc).mean()
    df_hourly["variable"] = variable

    return df, None