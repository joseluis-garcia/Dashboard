# # Demanda en tiempo real peninsular
# https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real?start_date=2026-01-01&end_date=2026-01-05&time_trunc=hour

# # Demanda por comunidad autónoma
# https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real?start_date=2026-01-01&end_date=2026-01-05&time_trunc=hour&geo_trunc=electric_system&geo_limit=ccaa&geo_ids=4

# geo_id	ccaa
# 4	    Andalucía
# 5	    Aragón
# 6	    Cantabria
# 7	    Castilla-La Mancha
# 8	    Castilla y León
# 9	    Cataluña
# 10	Euskadi
# 11	Asturias  
# 13	Madrid    
# 14	Navarra   
# 15	Valencia  
# 16	Extremadura
# 17	Galicia  
# 18	Comunitat Valenciana
# 20    La Rioja
# 21    Murcia
# 8742	Canarias
# 8743	Illes Balears
# 8744	Ceuta
# 8745	Melilla

import requests
import pandas as pd

def get_demanda_ccaa(geo_id: int, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Descarga demanda eléctrica diaria de una CCAA desde REData API.
    
    Args:
        geo_id: ID de la comunidad autónoma (ej: 15 = Murcia)
        start_date: Fecha inicio formato 'YYYY-MM-DD'
        end_date: Fecha fin formato 'YYYY-MM-DD'
    
    Returns:
        DataFrame con columnas: datetime, value, percentage, type
    """
    url = (
        f"https://apidatos.ree.es/es/datos/demanda/evolucion"
        f"?start_date={start_date}T00:00"
        f"&end_date={end_date}T23:59"
        f"&time_trunc=day"
        f"&geo_trunc=electric_system"
        f"&geo_limit=ccaa"
        f"&geo_ids={geo_id}"
    )
    print("URL:",url)
    try:
        response = requests.get(url, headers={"Accept": "application/json"})
        response.raise_for_status() 

        data = response.json()

        dfs = []
        for serie in data["included"]:
            df = pd.DataFrame(serie["attributes"]["values"])
            df["type"] = serie["attributes"]["title"]
            dfs.append(df)

        df_final = pd.concat(dfs, ignore_index=True)
        df_final["datetime"] = pd.to_datetime(df_final["datetime"]).dt.tz_localize(None)
        return df_final
    
    except requests.exceptions.RequestException as e:
        message = f"Request failed: {e}"
        message += f"\nStatus Code: {response.status_code}"
        message += f"\nResponse: {response.text}"  # Debug server response
        return None, message

# Ejemplo: Murcia, enero 2026
df = get_demanda_ccaa(geo_id=15, start_date="2026-01-01", end_date="2026-01-03")
print(df)