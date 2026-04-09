import pandas as pd
from dashboard.comun.date_conditions import day_of_year_no_leap
from dashboard.comun.sql_utilities import read_sql_ts

def get_PVGIS_data(conn) -> pd.DataFrame:

    date = pd.Timestamp.now().date()
    dayIndex = day_of_year_no_leap(date)
    
    query = f"select hour,power_Wh from PVGIS_sintesis where dayIndex = {dayIndex} order by hour"
    try:
        df = pd.read_sql_query(query, conn)
        return df, None
    except Exception as e:
        return None, f"Error al obtener datos de PVGIS: {e}"


