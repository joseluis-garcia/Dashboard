    
from comun.get_ESIOS_indicator import get_indicator

# Indicadores ESIOS para eólica, solar y demanda
IND_EO = 541   # Previsión eólica
IND_PV = 542   # Previsión solar fotovoltaica
IND_DEM = 603   # Demanda previsión semanal
IND_SPOT = 600   # Precio mercado spot diario

#=========================
# Funciones para obtener datos de energia (eolica, solar y demanda) de ESIOS en el rango de fechas
#=========================
def get_ESIOS_energy(rango):
    df, error = get_indicator(IND_EO, rango)
    if error:
        return None, error
    else:
        eolica = df[["datetime", "value"]].rename(columns={"value": "eolica"})

    df, error = get_indicator(IND_PV, rango)
    if error:
        return None, error
    else:
        solar = df[["datetime", "value"]].rename(columns={"value": "solar"})
        
    demanda, error = get_indicator(IND_DEM, rango)
    if error:
        return None, error
    else:        
        demanda = demanda[["datetime", "value"]].rename(columns={"value": "demanda"})
#=========================
# Combinar datos en un solo DataFrame
#=========================
    df_energy = eolica.merge(solar, on="datetime", how="outer").merge(demanda, on="datetime", how="outer")
    df_energy["renovable"] = df_energy["eolica"] + df_energy["solar"]
    return df_energy, None

#=========================
# Función para obtener datos de precio spot diario de ESIOS en el rango de fechas
#=========================
def get_ESIOS_spot (rango):
    df, error = get_indicator(IND_SPOT, rango)
    if error:
        return None, error
    else:
        spot = df[df['geo_name'] == 'España'] #solo valores de Peninsula
        spot = spot[["datetime", "value"]].rename(columns={"value": "precio_spot"})
        return spot, None