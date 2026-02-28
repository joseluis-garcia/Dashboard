import streamlit as st
import pandas as pd
from comun.safe_request import safe_request_get
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

def get_indicator(indicator_id, date_range):
    url = f"{BASE_URL}/{indicator_id}"

    response, error = safe_request_get(url, headers=headers, params=date_range)
    if error:
        st.error(f"No se han podido obtener los datos del indicador {indicator_id}.")
        st.error(error)
        return None, error  # Devuelve un DataFrame vacío en caso de error

    json_data = response.json()
    data = json_data["indicator"]["values"]
    variable = json_data["indicator"]["short_name"]

    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["variable"] = variable

    return df, None