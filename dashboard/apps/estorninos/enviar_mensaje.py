"""
Este script se encarga de calcular el mensaje que se enviará a Estorninos cada día, con la información relevante del día (previsión meteorológica, precios de excedentes negativos, etc). Se puede ejecutar manualmente o programar su ejecución diaria con un scheduler (ej: cron).
El envío del mensaje se realiza a través de Telegram, utilizando un bot y un canal específico para Estorninos. El mensaje se construye con datos obtenidos de ESIOS (precios de energía), OpenMeteo (previsión meteorológica) y otras fuentes relevantes.
Los datos de TG estan en st.secrets para evitar exponerlos en el código. El mensaje se envía solo si la clave "TG_active" en secrets está activada (True).
"""
import sys
import tomllib
from pathlib import Path
from datetime import date

from dashboard.comun.costes_regulados import costes_regulados

'''
Este código es para independizar la app de Estorninos del resto del proyecto, permitiendo que se ejecute de forma autónoma para calcular y enviar el mensaje diario a Telegram sin necesidad de cargar toda la app ni sus dependencias. Para ello, se carga manualmente el archivo de secrets y se parchea st.secrets antes de cualquier import que lo utilice.'''
BASE_DIR = Path(__file__).parent.parent.parent.parent
secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
project_path = BASE_DIR

# Uso
sys.path.insert(0, str(project_path))

# Cargar secrets y parchear st.secrets ANTES de cualquier import de la app
import streamlit as st

with open(secrets_path, 'rb') as f:
    _secrets = tomllib.load(f)

class FakeSecrets(dict):
    def __getattr__(self, key):
        return self[key]

st.secrets = FakeSecrets(_secrets)

# A partir de aquí todos los imports leen st.secrets normalmente
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_forecast, get_ESIOS_spot
from dashboard.comun.get_openmeteo import get_meteo_today
from dashboard.comun.mensaje import send_TG_message
from dashboard.comun.date_conditions import get_estacion, horas_a_texto

def calcular_mensaje() -> str:
    '''
    Calcula el mensaje a enviar a Estorninos con la información relevante del día.
    Obtiene datos de ESIOS para detectar horas con precios de excedentes negativos, precios muy bajos y muy altos. También obtiene la previsión meteorológica de OpenMeteo para incluirla en el mensaje.
    Returns:
        mensaje: String con el mensaje formateado para enviar a Estorninos
    '''
    
    # Obtener precios de ESIOS para detectar precios excedentes negativos
    df_omie, error_omie = get_ESIOS_spot(None)
    if error_omie:
        return None, f"No se han podido obtener los precios de ESIOS: {error_omie}"
    
    # Convertimos el indice a hora local
    df_omie = costes_regulados(df_omie)
    df_omie = df_omie.tz_convert("Europe/Madrid")  

    # Horas a las que la compensacion de excedentes es negativa
    df_negativos = df_omie[df_omie["Mercado SPOT"] < 0]
    df_omie["Mercado SPOT"] += df_omie["costes_regulados"]

    if not df_negativos.empty:
        #horas_negativo_str = ", ".join(df_negativos.index.hour.astype(str))
        horas_negativo_str = horas_a_texto(df_negativos.index.tolist())

    df_omie_barato=df_omie[df_omie["Mercado SPOT"]<df_omie["Mercado SPOT"].quantile(0.1)]
    horas_barato_str = horas_a_texto(df_omie_barato.index.tolist())
    #horas_barato_str = ", ".join(df_omie_barato.index.hour.astype(str))
    df_omie_caro=df_omie[df_omie["Mercado SPOT"]>df_omie["Mercado SPOT"].quantile(0.9)]
    horas_caro_str = horas_a_texto(df_omie_caro.index.tolist())

    df_meteo = get_meteo_today()  # Madrid
    fecha = date.today()
    estacion = get_estacion(fecha)
    str_fecha = fecha.strftime("%d de %B de %Y").lstrip("0")

    # Aquí va la lógica para calcular el mensaje basado en los datos de ESIOS u otras fuentes
    mensaje = f"¡Hola! Este es un mensaje para Estorninos.\nHoy es: {str_fecha}.\n"
    mensaje += f"Estamos en {estacion} y el clima de hoy en España es:\n"
    for _, row in df_meteo.iterrows():
        mensaje += f"\n-> {row['ciudad']} {row['weather_icon']}  {row['weather_desc']} con temperaturas entre {row['temperature_2m_min']:.1f}°C y {row['temperature_2m_max']:.1f}°C. "
        mensaje += f"Las horas de salida y puesta de sol serán: {row['sunrise']} y {row['sunset']} respectivamente.\n"

    if not df_negativos.empty:
        mensaje += f"\nLas horas con precios de excedentes negativos serán: {horas_negativo_str}.\n"
    mensaje += f"Las horas con precios mas bajos (por debajo del 10% de los precios) serán: {horas_barato_str}.\n"
    mensaje += f"Las horas con precios mas altos (por encima del 90% de los precios) serán: {horas_caro_str}.\n"
    mensaje += "\n¡Que tengas un buen día! 🌞"

    return mensaje

# Calcular y enviar
mensaje = calcular_mensaje()
print(f"Se envia mensaje? {st.secrets.get('TG_active')}")
print(mensaje)

if st.secrets.get("TG_active"):
    send_TG_message(mensaje)
