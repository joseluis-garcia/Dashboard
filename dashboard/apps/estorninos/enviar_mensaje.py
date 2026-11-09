"""
Este script se encarga de calcular el mensaje que se enviará a Estorninos cada día, con la información relevante del día (previsión meteorológica, precios de excedentes negativos, etc). Se puede ejecutar manualmente o programar su ejecución diaria con un scheduler (ej: cron).
El envío del mensaje se realiza a través de Telegram, utilizando un bot y un canal específico para Estorninos. El mensaje se construye con datos obtenidos de ESIOS (precios de energía), OpenMeteo (previsión meteorológica) y otras fuentes relevantes.
Los datos de TG estan en st.secrets para evitar exponerlos en el código. El mensaje se envía solo si la clave "TG_active" en secrets está activada (True).
"""

import sys
import logging
from pathlib import Path
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent.parent  # ajusta los .parent según tu estructura
sys.path.insert(0, str(BASE_DIR))

from dashboard.comun.load_secrets import load_secrets
load_secrets(base_dir=BASE_DIR)  # Carga secrets y parchea st.secrets antes de cualquier import

import streamlit as st
import jenkspy 
import re
import pandas as pd

from datetime import date, datetime, timedelta, timezone

# A partir de aquí todos los imports leen st.secrets normalmente
from dashboard.comun.get_ESIOS_data import get_ESIOS_spot
from dashboard.comun.get_openmeteo import get_meteo_today
from dashboard.comun.mensaje import send_TG_message, send_TG_photo
from dashboard.comun.date_conditions import get_estacion, horas_a_texto, MESES
from dashboard.comun.costes_regulados import costes_regulados

def escape_md(text: str, destino: str = "Telegram") -> str:
    '''
    Escapa caracteres especiales de Markdown en un texto para evitar que se interpreten como formato en Telegram.
    Args:
        text: Texto a escapar
        destino: Destino del mensaje ("Telegram" o "Streamlit")
        Returns: Texto escapado o sin cambiar si el destino no es Telegram
    '''
    if destino != "Telegram":
        return text
    return re.sub(r'([_\*\[\]()~`>#+=|{}.!\-])', r'\\\1', text)

def clasificar_precios(precios: pd.Series, n_clases: int = 3) -> pd.Series:
    breaks = jenkspy.jenks_breaks(precios.values, n_classes=n_clases)
    # breaks = [min, umbral_bajo, umbral_alto, max]
    return pd.cut(
        precios,
        bins=breaks,
        labels=["barato", "normal", "caro"],
        include_lowest=True
    )



def crear_grafico(precios_kwh: pd.Series, breaks: list, fecha: date) -> io.BytesIO:
    """Gráfico de barras con los precios del día, coloreado según barato/normal/caro."""
    colores = precios_kwh.apply(
        lambda p: "#2ecc71" if p <= breaks[1] else ("#e74c3c" if p >= breaks[3] else "#f1c40f")
    )

    # Ancho de barra según la resolución (1 h o 15 min)
    paso = (precios_kwh.index[1] - precios_kwh.index[0]) if len(precios_kwh) > 1 else timedelta(hours=1)
    ancho = paso / timedelta(days=1)  # matplotlib usa días como unidad en fechas

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    ax.bar(precios_kwh.index, precios_kwh.values, width=ancho, align="edge",
           color=colores, edgecolor="white", linewidth=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Precio de la electricidad – {fecha.day} de {MESES[fecha.month-1]} de {fecha.year}")
    ax.set_ylabel("€/kWh")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H", tz=precios_kwh.index.tz))
    ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=2, tz=precios_kwh.index.tz))
    ax.set_xlabel("Hora")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf

def calcular_mensaje(destino = "Telegram") -> str:
    '''
    Calcula el mensaje a enviar a Estorninos con la información relevante del día.
    Obtiene datos de ESIOS para detectar horas con precios de excedentes negativos, precios muy bajos y muy altos. También obtiene la previsión meteorológica de OpenMeteo para incluirla en el mensaje.
    Returns:
        mensaje: String con el mensaje formateado para enviar a Estorninos
    '''

    rango = None  # Se calcula dentro de get_ESIOS_spot para obtener precios del día actual

    # codigo para cuando se ejecuta el script el dia anterior y se quiere obtener el mensaje para el dia siguiente
    tz = timezone(timedelta(hours=1))  # Hora de Madrid (UTC+1)
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today + timedelta(days=1) # Mañana a las 00:00
    end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
    rango = {
        'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S')
    }
    print(f"Obteniendo precios de ESIOS para el rango: {rango['start_date']} a {rango['end_date']}")
    
    df_omie, error_omie = get_ESIOS_spot(rango=rango)
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

    print("Precios de ESIOS + cargos y peajes obtenidos y convertidos a hora local:")
    print(df_omie.head(5))

    precios_kwh = df_omie["Mercado SPOT"] / 1000
    breaks = jenkspy.jenks_breaks(precios_kwh.values, n_classes=4)

    df_omie_barato = df_omie[precios_kwh <= breaks[1]]
    df_omie_caro   = df_omie[precios_kwh >= breaks[3]]

    baratos_kwh = precios_kwh[precios_kwh <= breaks[1]]
    caros_kwh   = precios_kwh[precios_kwh >= breaks[3]]

    precios_baratos_str = f"{baratos_kwh.min():.3f}€/kWh a {baratos_kwh.max():.3f}€/kWh"
    precios_caros_str   = f"{caros_kwh.min():.3f}€/kWh a {caros_kwh.max():.3f}€/kWh"

    horas_barato_str = horas_a_texto(df_omie_barato.index.tolist())
    precios_baratos_str = f"(< {breaks[1]:.3f} €/kWh)"

    #print(f"(< {breaks[1]:.3f} €/kWh)")
    horas_caro_str   = horas_a_texto(df_omie_caro.index.tolist())
    precios_caros_str = f"(> {breaks[3]:.3f} €/kWh)"

    # Aquí va la lógica para calcular el mensaje basado en los datos de ESIOS u otras fuentes
    # Nuevo mensaje a partir de noviembre, se emite a las 21:00 del dia anterior y va sin meteo

    # try:
    #     df_meteo = get_meteo_today()

    # except Exception as e:
    #     logger.warning(f"No se pudo obtener meteo, se omite del mensaje: {e}")
    #     df_meteo = None

    #- fecha = date.today()
    #- estacion = get_estacion(fecha)
    fecha = date.today() + timedelta(days=1)

    str_fecha = f"{fecha.day} de {MESES[fecha.month-1]} de {fecha.year}"

    #- mensaje = escape_md(f"¡Hola! Este es un mensaje para Estorninos.\nHoy es: {str_fecha}.\n", destino)
    #- mensaje += escape_md(f"Estamos en {estacion} y el clima de hoy en España es:\n", destino)
    mensaje = escape_md(f"¡Hola! Mensaje para Estorninos.\nMañana será: {str_fecha}.\n", destino)

    mensaje += "─" * 20
    
    # if df_meteo is not None:
    #     # El bloque meteorológico del mensaje:
    #     for _, row in df_meteo.iterrows():
    #         mensaje += f"\n*{escape_md(row['ciudad'], destino)}*\n"
    #         mensaje += "`" + escape_md(f"{row['weather_icon']} {row['weather_desc']}\n", destino) + "`"
    #         mensaje += escape_md(f"🌡 {row['temperature_2m_min']:.1f}° – {row['temperature_2m_max']:.1f}°C\n", destino)
    #         mensaje += escape_md(f"🌅 {row['sunrise']}  🌇 {row['sunset']}\n", destino)
    #     mensaje += "\n"
    # else:
    #     mensaje += escape_md(f"Error al obtener la previsión meteorológica.\n", destino)

    # Bloque de precios compacto
    mensaje += escape_md(f"💰 Precios electricidad\n", destino)
    mensaje += "─" * 20 + "\n"
    mensaje += escape_md(f"🟢 Baratos -> {horas_barato_str}\n", destino)
    mensaje += escape_md(f"💰 {precios_baratos_str}\n", destino)
    mensaje += escape_md(f"🔴 Caros -> {horas_caro_str}\n", destino)
    mensaje += escape_md(f"💰 {precios_caros_str}\n", destino)
    if not df_negativos.empty:
        mensaje += escape_md(f"⚡ Excedentes negativos -> {horas_negativo_str}\n", destino)
    else:
        mensaje += escape_md(f"⚡ Sin excedentes negativos\n", destino)
  
    mensaje += escape_md("¡Que tengas un buen día! 🌞", destino)
    grafico = crear_grafico(precios_kwh, breaks, fecha)
    return mensaje, grafico

# Calcular y enviar
if __name__ == "__main__":
    mensaje, grafico = calcular_mensaje(destino="Telegram")
    print(f"Se envia mensaje? {st.secrets.get('TG_active')}")

    if mensaje is None:
        print("No se pudo calcular el mensaje, no se envía nada.")
    elif st.secrets.get("TG_active"):
        response, error = send_TG_photo(grafico, mensaje)
        if error:
            print(f"Error al enviar mensaje a Telegram: {error}")
        else:
            print("Mensaje enviado a Telegram con éxito.")
