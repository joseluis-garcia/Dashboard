from datetime import  datetime
import pandas as pd
import pytz
import holidays
import streamlit as st
import ephem
from zoneinfo import ZoneInfo

today = ""
festivos = []
weekends = []

def date_conditions_init(rango):

    global today, festivos, weekends
    tz = pytz.timezone("Europe/Madrid")
    today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
    festivos = get_festivos(rango)
    weekends = get_weekends(rango)

#==========================
# Generar lista de días festivos en España para el rango de fechas
#==========================
def get_festivos(rango):
    years = list(range(rango['start_date'].year, rango['end_date'].year+1))
    festivos= holidays.country_holidays("ES", years=years)
    festivos = pd.to_datetime(list(festivos.keys())).normalize()
    # Rango del eje X (pueden venir como date, datetime o string) 
    start_date = pd.to_datetime(rango['start_date']).tz_localize(None).normalize() 
    end_date = pd.to_datetime(rango['end_date']).tz_localize(None).normalize()
    festivos = festivos[(festivos >= start_date) & (festivos <= end_date)]
    return festivos

#==========================
# Generar rangos de fines de semana
#==========================
def get_weekends(rango):
    print(f"Calculando fines de semana para el rango: {rango['start_date']} a {rango['end_date']}")
    weekends = []
    for d in pd.date_range(rango["start_date"], rango["end_date"]):
        if d.weekday() >= 5:  # 5 = sábado, 6 = domingo
            start = pd.Timestamp(d).normalize()
            end = start + pd.Timedelta(days=1)
            weekends.append((start, end))
    print(f"Fines de semana calculados: {weekends}")
    return weekends

# ==========================
# 3. PERIODO 2.0TD P1–P3
# ==========================
def periodo_2_0TD(fecha) -> str:
    """
    Determina el periodo tarifario P1–P3 para energía en 2.0TD.
    """
    fecha = pd.to_datetime(fecha)
    h = fecha.hour

    # Festivos y fines de semana → todo P3 (valle)
    if es_festivo_o_fin_de_semana(fecha):
        return "P3"

    # Horario valle (P3)
    if 0 <= h < 8:
        return "P3"

    # Horario punta (P1)
    if 10 <= h < 14 or 18 <= h < 22:
        return "P1"

    # Horario llano (P2)
    return "P2"

# ==========================
# 2. FESTIVOS CON `holidays`
# ==========================
def es_festivo_o_fin_de_semana(fecha) -> bool:
    if fecha in festivos:
        return True
    if fecha.weekday() >= 5:  # sábado/domingo
        return True
    return False

#==========================
# Función para obtener datos de salida del sol (amanecer, atardecer, etc) usando la librería ephem.
#==========================
def getSunData(lat, lon, date):
    # Configurar observador
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = date  
    sun = ephem.Sun(observer)
    sunrise = observer.next_rising(sun).datetime().replace(tzinfo=ZoneInfo("UTC"))
    sunrise = sunrise.astimezone(ZoneInfo("Europe/Madrid"))
    sunset = observer.next_setting(sun).datetime().replace(tzinfo=ZoneInfo("UTC"))
    sunset = sunset.astimezone(ZoneInfo("Europe/Madrid"))
    noon = observer.next_transit(sun).datetime().replace(tzinfo=ZoneInfo("UTC"))
    noon = noon.astimezone(ZoneInfo("Europe/Madrid"))
    return {    
        "sunrise": sunrise.hour + sunrise.minute/60,
        "sunset": sunset.hour + sunset.minute/60,
        "noon": noon.hour + noon.minute/60
    }
