"""
Módulo para obtener datos historicos de ESIOS (produccion, demanda, spot).
Actualiza la tabla ESIOS_data en measures.db desde la última fecha registrada hasta el dia actual
"""

from typing import Tuple, Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta, timezone
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_history, get_ESIOS_spot

def update_ESIOS_history(conn) -> Tuple[Optional[pd.DataFrame], Optional[str]]:

    #Previous data recorded until
    df = pd.read_sql_query("SELECT MAX(datetime) as maxDate FROM ESIOS_data", conn, parse_dates=["maxDate"])
    df["maxDate"] = pd.to_datetime(df["maxDate"])
    startDate = df["maxDate"].iloc[0] + timedelta(hours=1)
    strStartDate = startDate.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get the current UTC time
    endDate = datetime.now(timezone.utc) + timedelta(hours=-1)

    # Teniendo probelmas de carga limitamos a 30 dias
    endDate = startDate+ timedelta(days=15)
    # Convert the datetime object to a string
    strEndDate = endDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    rango = {
        'start_date': strStartDate,
        'end_date': strEndDate
    }
    print(f"Solicitando datos spot desde {rango['start_date']} hasta {rango['end_date']}")
    df_spot, error = get_ESIOS_spot(rango)
    if error:
        return None, error
    
    print(f"Solicitando datos energia desde {rango['start_date']} hasta {rango['end_date']}")
    df_energy, error = get_ESIOS_energy_history(rango)
    if error:
        return None, error
    
    print("Uniendo datos de energia y SPOT")
    df_final = pd.concat([df_energy, df_spot], axis=1).reset_index()

    print(f"Insertando filas {df_final.head()} en la base de datos")
    #df_final.to_sql('ESIOS_data', conn, if_exists='append', index=False )

    return f"Insertadas {len(df_final)} en ESIOS_data", None

