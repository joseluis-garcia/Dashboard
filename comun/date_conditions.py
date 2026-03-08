from datetime import  datetime, timedelta
import pandas as pd
import pytz
import holidays
import streamlit as st
import ephem
from zoneinfo import ZoneInfo
from typing import TypedDict, List
class RangoFechas(TypedDict):
    start_date: datetime
    end_date: datetime
class SunData(TypedDict):    
    sunrise: float
    sunset: float
    noon: float
class Coord(TypedDict):
    lat: float
    lon: float
today = ""
festivos = []
weekends = []

def date_conditions_init(rango: RangoFechas):
    """
    Inicializa los arrays globales con los dias festivos y fines de semana en el rango de fechas recibido. 
    Estos se utilizarán para determinar los periodos tarifarios y para graficar los rectángulos en el gráfico de precios.
    """
    global today, festivos, weekends
    tz = pytz.timezone("Europe/Madrid")
    today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
    festivos = get_festivos(rango)
    weekends = get_weekends(rango)

#==========================
# Generar lista de días festivos en España para el rango de fechas
#==========================
def get_festivos(rango: RangoFechas) -> List[datetime]:
    """
    Retorna array de dias festivos nacionales en España en el año del rango de fechas recibido.
    Utiliza la librería holidays para obtener los festivos nacionales.
    El resultado se devuelve como un array de objetos datetime con hora 00:00:00, sin zona horaria (naive).
    """
    years = list(range(rango['start_date'].year, rango['end_date'].year+1))
    festivos= holidays.country_holidays("ES", years=years)
    festivos = pd.to_datetime(list(festivos.keys())).normalize()

    start_date = pd.to_datetime(rango['start_date']).tz_localize(None).normalize() 
    end_date = pd.to_datetime(rango['end_date']).tz_localize(None).normalize()

    festivos = festivos[(festivos >= start_date) & (festivos <= end_date)]
    return festivos

#==========================
# Generar rangos de fines de semana
#==========================
def get_weekends(rango: RangoFechas) -> List[datetime]:
    """
    Retorna array de fines de semana en el rango de fechas recibido
    """
    weekends = []
    for d in pd.date_range(rango["start_date"], rango["end_date"]):
        if d.weekday() >= 5:  # 5 = sábado, 6 = domingo
            start = pd.Timestamp(d).normalize()
            end = start + pd.Timedelta(days=1)
            weekends.append((start, end))
    return weekends

# ==========================
# PERIODO 2.0TD P1–P3
# ==========================
def periodo_2_0TD(datetime: datetime) -> str:
    """
    Determina el periodo tarifario P1–P3 para energía en 2.0TD de datetime
    """
    fecha = pd.to_datetime(datetime)
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
# FESTIVOS O FIN DE SEMANA?
# ==========================
def es_festivo_o_fin_de_semana(fecha) -> bool:
    if fecha in festivos:
        return True
    if fecha.weekday() >= 5:  # sábado/domingo
        return True
    return False

#==========================

#==========================
def getSunData(lat: float, lon: float, date: datetime, tz_local: str="Europe/Madrid") -> SunData:
    """
    Función para obtener datos de salida del sol (amanecer, atardecer, etc) usando la librería ephem.
    Devuelve en hora local si se indica tz_local=str, o en UTC si se indica tz_local="UTC".

    Parametros
    - lat: latitud del lugar
    - lon: longitud del lugar
    - date: fecha para la que se quieren obtener los datos (datetime)
    - tz_local: zona horaria para convertir las horas (por defecto "Europe/Madrid", también puede ser "UTC")
    """
    # Configurar observador
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = date

    sun = ephem.Sun(observer)
    sunrise = observer.next_rising(sun).datetime()
    sunset = observer.next_setting(sun).datetime()
    noon = observer.next_transit(sun).datetime()
    sunrise = sunrise.replace(tzinfo=ZoneInfo("UTC"))
    sunset = sunset.replace(tzinfo=ZoneInfo("UTC"))
    noon = noon.replace(tzinfo=ZoneInfo("UTC"))
    if tz_local != "UTC":
        sunrise = sunrise.astimezone(ZoneInfo(tz_local))
        sunset = sunset.astimezone(ZoneInfo(tz_local))
        noon = noon.astimezone(ZoneInfo(tz_local))
    return {    
        "sunrise": sunrise.hour + sunrise.minute/60,
        "sunset": sunset.hour + sunset.minute/60,
        "noon": noon.hour + noon.minute/60
    }
# =========================
# FUNCION PARA OBTENER HORAS DE SALIDA Y PUESTA DEL SOL
# coord: diccionario con latitud y longitud {"lat": 40.4169, "lon": -3.7033}
# start: fecha de inicio
# end: fecha de fin
# delta: intervalo en días
# tz_local: zona horaria para convertir las horas (por defecto "Europe/Madrid", también puede ser "UTC")
# return: dataframe con columnas "date", "sunrise_hour" y "sunset_hour"
# =========================
@st.cache_data
def getSunDataRange(coord: Coord, start: datetime, end: datetime, delta: int, tz_local: str="Europe/Madrid")->pd.DataFrame:
    """
    FUNCION PARA OBTENER HORAS DE SALIDA Y PUESTA DEL SOL
    Parametros
    - coord: diccionario con latitud y longitud {"lat": 40.4169, "lon": -3.7033}
    - start: fecha de inicio
    - end: fecha de fin
    - delta: intervalo en días
    - tz_local: zona horaria para convertir las horas (por defecto "Europe/Madrid", también puede ser "UTC")

    return
    - dataframe con columnas "date", "sunrise_hour" y "sunset_hour"
    """
    rows = []
    d = start  

    while d <= end:
        sun_data = getSunData(coord["lat"], coord["lon"], d, tz_local)
        rows.append({
            "date": d,
            "sunrise_hour": sun_data["sunrise"],
            "sunset_hour": sun_data["sunset"]
        })
        d += timedelta(days=delta)

    return pd.DataFrame(rows)
#=====================

#=====================
def day_of_year_no_leap(date) -> int:
    '''
    funcion para convertir una fecha dada en un indice
    Compute day index (1-365) ignoring February 29"""  
    '''
    # Adjust for leap years by skipping February 29
    day_index = date.timetuple().tm_yday
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        day_index -= 1  # Remove leap day offset
    return day_index