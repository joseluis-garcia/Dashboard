"""
Módulo de utilidades para manejo de fechas, cálculos solares y periodos tarifarios.

Proporciona funciones para:
- Cálculo de festivos y fines de semana en España
- Determinación de periodos tarifarios (P1, P2, P3)
- Cálculos de salida/puesta del sol
- Normalización de timestamps
"""
import os
import base64
from datetime import datetime, timedelta, date
from typing import TypedDict, List, Tuple, Union, Optional
import pandas as pd
import pytz
import holidays
import streamlit as st
import ephem
from zoneinfo import ZoneInfo
import plotly.graph_objects as go



class RangoFechas(TypedDict):
    """Diccionario que define un rango de fechas."""
    start_date: datetime
    end_date: datetime


class SunData(TypedDict):
    """Datos de salida y puesta del sol."""
    sunrise: float
    sunset: float
    noon: float


class Coord(TypedDict):
    """Coordenadas geográficas (latitud, longitud)."""
    lat: float
    lon: float


# Variables globales para almacenar condiciones de fecha
today: Optional[datetime] = None
festivos: List[datetime] = []
weekends: List[Tuple[Union[pd.Timestamp, datetime], Union[pd.Timestamp, datetime]]] = []


def date_conditions_init(rango: RangoFechas) -> None:
    """
    Inicializa las variables globales de condiciones de fecha.
    
    Calcula y almacena los días festivos y fines de semana del rango especificado.
    Esta función debe ejecutarse antes de usar las otras funciones de este módulo.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date' (datetime con zona horaria)
        
    Raises:
        ValueError: Si el rango es inválido (start_date > end_date)
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 1, 1, tzinfo=pytz.UTC),
        ...     'end_date': datetime(2026, 12, 31, tzinfo=pytz.UTC)
        ... }
        >>> date_conditions_init(rango)
    """
    global today, festivos, weekends
    
    tz = pytz.timezone("Europe/Madrid")
    today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
    festivos = get_festivos(rango)
    weekends = get_weekends(rango)


def get_festivos(rango: RangoFechas) -> List[datetime]:
    """
    Obtiene los días festivos nacionales en España para el rango de fechas.
    
    Utiliza la librería holidays para obtener los festivos nacionales españoles
    y filtra solo los que caen dentro del rango especificado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Lista de datetime con los festivos en el rango (sin zona horaria)
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 1, 1),
        ...     'end_date': datetime(2026, 12, 31)
        ... }
        >>> festivos = get_festivos(rango)
        >>> len(festivos) > 0
        True
    """
    years = list(range(rango['start_date'].year, rango['end_date'].year + 1))
    festivos_dict = holidays.country_holidays("ES", years=years)
    festivos_pd = pd.to_datetime(list(festivos_dict.keys())).normalize()

    start_date = pd.to_datetime(rango['start_date']).tz_localize(None).normalize()
    end_date = pd.to_datetime(rango['end_date']).tz_localize(None).normalize()

    festivos_filtered = festivos_pd[(festivos_pd >= start_date) & (festivos_pd <= end_date)]
    return festivos_filtered.tolist()


def get_weekends(rango: RangoFechas) -> List[Tuple[Union[pd.Timestamp, datetime], Union[pd.Timestamp, datetime]]]:
    """
    Obtiene los rangos de fines de semana en el periodo especificado.
    
    Itera sobre cada día en el rango y crea tuplas (inicio, fin) para cada
    sábado y domingo encontrado.
    
    Args:
        rango: Diccionario con 'start_date' y 'end_date'
        
    Returns:
        Lista de tuplas (inicio_weekend, fin_weekend)
        
    Example:
        >>> rango = {
        ...     'start_date': datetime(2026, 3, 1),
        ...     'end_date': datetime(2026, 3, 31)
        ... }
        >>> weekends = get_weekends(rango)
        >>> len(weekends) > 0
        True
    """
    weekends_list: List[Tuple[Union[pd.Timestamp, datetime], Union[pd.Timestamp, datetime]]] = []
    
    for d in pd.date_range(rango["start_date"], rango["end_date"]):
        if d.weekday() >= 5:  # 5 = sábado, 6 = domingo
            start = pd.Timestamp(d).normalize()
            end = start + pd.Timedelta(days=1)
            weekends_list.append((start, end))
    
    return weekends_list


def periodo_2_0TD(fecha: datetime) -> str:
    """
    Determina el periodo tarifario (P1, P2 o P3) para energía en 2.0TD.
    
    Los periodos en 2.0TD son:
    - P1 (Punta): Lunes-Viernes 10-14h y 18-22h
    - P2 (Llano): Lunes-Viernes 8-10h, 14-18h y 22-00h
    - P3 (Valle): Lunes-Viernes 00-8h, y TODO el fin de semana/festivos
    
    Args:
        fecha: datetime con la hora a verificar
        
    Returns:
        String con el periodo: "P1", "P2" o "P3"
        
    Example:
        >>> from datetime import datetime
        >>> fecha = datetime(2026, 3, 10, 12, 0)  # Martes 12h
        >>> periodo = periodo_2_0TD(fecha)
        >>> periodo
        'P1'
    """
    fecha_pd = pd.to_datetime(fecha)
    h = fecha_pd.hour

    # Festivos y fines de semana → todo P3 (valle)
    if es_festivo_o_fin_de_semana(fecha_pd):
        return "P3"

    # Horario valle (P3): 00:00 - 08:00
    if 0 <= h < 8:
        return "P3"

    # Horario punta (P1): 10:00-14:00 y 18:00-22:00
    if 10 <= h < 14 or 18 <= h < 22:
        return "P1"

    # Horario llano (P2): resto
    return "P2"


def es_festivo_o_fin_de_semana(fecha: Union[datetime, pd.Timestamp]) -> bool:
    """
    Verifica si una fecha es festivo o fin de semana.
    
    Args:
        fecha: datetime o Timestamp a verificar
        
    Returns:
        True si es festivo o fin de semana, False en caso contrario
        
    Example:
        >>> from datetime import datetime
        >>> fecha = datetime(2026, 12, 25)  # Navidad
        >>> es_festivo_o_fin_de_semana(fecha)
        True
    """
    # Convertir a datetime si es Timestamp
    if isinstance(fecha, pd.Timestamp):
        fecha_dt = fecha.to_pydatetime()
    else:
        fecha_dt = fecha

    # Verificar si está en la lista de festivos
    if fecha_dt in festivos:
        return True
    
    # Verificar si es fin de semana (5=sábado, 6=domingo)
    if fecha_dt.weekday() >= 5:
        return True
    
    return False


def get_estacion(fecha: date) -> str:
    año = fecha.year
    equi_mar  = ephem.next_equinox(f"{año}/1/1")
    sols_jun  = ephem.next_solstice(equi_mar)
    equi_sep  = ephem.next_equinox(sols_jun)
    sols_dic  = ephem.next_solstice(equi_sep)

    d = ephem.Date(fecha.strftime("%Y/%m/%d"))

    if d < equi_mar:   return "invierno"
    elif d < sols_jun: return "primavera"
    elif d < equi_sep: return "verano"
    elif d < sols_dic: return "otoño"
    else:              return "invierno"

def getSunData(
    lat: float, 
    lon: float, 
    date: datetime, 
    tz_local: str = "Europe/Madrid"
) -> SunData:
    """
    Obtiene datos de salida y puesta del sol para una ubicación y fecha.
    
    Utiliza la librería ephem para calcular astronomicamente los tiempos
    de salida y puesta del sol.
    
    Args:
        lat: Latitud de la ubicación (en grados decimales)
        lon: Longitud de la ubicación (en grados decimales)
        date: Fecha para la cual calcular (datetime)
        tz_local: Zona horaria para convertir (por defecto "Europe/Madrid")
        
    Returns:
        Diccionario SunData con 'sunrise', 'sunset', 'noon' como horas (float)
        
    Raises:
        ValueError: Si las coordenadas son inválidas
        
    Example:
        >>> sun_data = getSunData(40.4169, -3.7033, datetime(2026, 3, 10))
        >>> sun_data['sunrise']  # Hora de salida
        6.75
    """
    # Configurar observador en la ubicación
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = date

    sun = ephem.Sun(observer)
    sunrise = observer.next_rising(sun).datetime()
    sunset = observer.next_setting(sun).datetime()
    noon = observer.next_transit(sun).datetime()
    
    # Convertir a UTC y luego a zona horaria local
    sunrise = sunrise.replace(tzinfo=ZoneInfo("UTC"))
    sunset = sunset.replace(tzinfo=ZoneInfo("UTC"))
    noon = noon.replace(tzinfo=ZoneInfo("UTC"))
    
    if tz_local != "UTC":
        sunrise = sunrise.astimezone(ZoneInfo(tz_local))
        sunset = sunset.astimezone(ZoneInfo(tz_local))
        noon = noon.astimezone(ZoneInfo(tz_local))
    
    return {
        "amanece": sunrise,
        "ocaso": sunset,
        "mediodia": noon,
        "sunrise": sunrise.hour + sunrise.minute / 60,
        "sunset": sunset.hour + sunset.minute / 60,
        "noon": noon.hour + noon.minute / 60
    }

@st.cache_data
def getSunDataRange(
    coord: Coord, 
    start: datetime, 
    end: datetime, 
    delta: int, 
    tz_local: str = "Europe/Madrid"
) -> pd.DataFrame:
    """
    Obtiene datos de salida y puesta del sol para un rango de fechas.
    
    Calcula los tiempos de salida y puesta del sol para cada día en el rango,
    con un intervalo especificado. Los resultados se cachean automáticamente
    con Streamlit.
    
    Args:
        coord: Diccionario con 'lat' y 'lon' (coordenadas decimales)
        start: Fecha de inicio (datetime)
        end: Fecha de fin (datetime)
        delta: Intervalo en días entre cálculos
        tz_local: Zona horaria para convertir (por defecto "Europe/Madrid")
        
    Returns:
        DataFrame con columnas ['date', 'sunrise_hour', 'sunset_hour']
        
    Example:
        >>> coord = {'lat': 40.4169, 'lon': -3.7033}
        >>> df = getSunDataRange(
        ...     coord,
        ...     datetime(2026, 3, 1),
        ...     datetime(2026, 3, 31),
        ...     delta=1
        ... )
        >>> len(df) > 0
        True
    """
    rows: List[dict] = []
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

def day_of_year_no_leap(date: Union[datetime, pd.Timestamp]) -> int:
    """
    Convierte una fecha a un índice de día del año (1-365, sin contar Feb 29).
    
    Calcula el día del año ignorando los años bisiestos, de modo que el índice
    es siempre entre 1 y 365.
    
    Args:
        date: Fecha a convertir (datetime o Timestamp)
        
    Returns:
        Índice del día del año (1-365)
        
    Example:
        >>> from datetime import datetime
        >>> day_index = day_of_year_no_leap(datetime(2026, 3, 10))
        >>> day_index
        69
    """
    # Convertir a datetime si es Timestamp
    if isinstance(date, pd.Timestamp):
        date = date.to_pydatetime()
    
    # Obtener el día del año
    day_index = date.timetuple().tm_yday
    
    # Ajustar para años bisiestos (restar 1 si es después del 29 de febrero)
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        day_index -= 1
    
    return day_index

def load_icon(relative_path: str) -> str:
    """
    Carga un icono PNG desde la carpeta de recursos como base64.
    
    Carga un archivo de imagen PNG desde la ruta relativa y lo codifica
    en base64 para usar en Plotly como fuente de imagen.
    
    Args:
        relative_path: Ruta relativa al archivo desde comun/
                      (ej: "icons/sunrise-dark.png")
        
    Returns:
        String con datos base64 prefijado para usar en Plotly
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        
    Example:
        >>> icon = load_icon("icons/sunrise-dark.png")
    """
    # Directorio donde está este archivo (comun/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, relative_path)
    
    with open(icon_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    
    return "data:image/png;base64," + encoded

def add_sun_data(fig: go.Figure, lat: float, lon: float, fecha: datetime):

    sun_data = getSunData(lat, lon, fecha, tz_local="Europe/Madrid")
    
    # Icono de salida del sol (sunrise)
    icon_rise = load_icon("icons/sunrise-dark.png")
    fig.add_layout_image(
        dict(
            source=icon_rise,
            x=sun_data["sunrise"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    # Línea vertical de mediodía solar con icono
    icon_noon = load_icon("icons/10000_clear_small.png")
    fig.add_vline(
        x=sun_data["noon"],
        line_width=2,
        line_dash="dash",
        line_color="green",
        name="Mediodía"
    )
    fig.add_layout_image(
        dict(
            source=icon_noon,
            x=sun_data["noon"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    # Icono de puesta del sol (sunset)
    icon_set = load_icon("icons/sunset-dark.png")
    fig.add_layout_image(
        dict(
            source=icon_set,
            x=sun_data["sunset"],
            y=0,
            xref="x",
            yref="paper",
            sizex=0.5,
            sizey=0.5,
            xanchor="center",
            yanchor="middle",
            layer="above"
        )
    )

    return

def local_to_utc(ts_str: str) -> str:
    """
    Convierte una fecha/hora local (sin tz) en Europe/Madrid a UTC (ISO 8601).
    Espera formato 'YYYY-MM-DD HH:MM:SS' o ISO similar.
    """
    TZ_LOCAL = "Europe/Madrid"
    if ts_str is None:
        return None

    # Parse naive
    dt = datetime.fromisoformat(ts_str)

    # Asignar zona horaria local
    dt_local = dt.replace(tzinfo=ZoneInfo(TZ_LOCAL))

    # Convertir a UTC
    dt_utc = dt_local.astimezone(ZoneInfo("UTC"))

    return dt_utc.isoformat(sep=" ")