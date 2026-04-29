from datetime import date
from typing import Tuple, Optional
import plotly.graph_objects as go
import pandas as pd
import pytz

import dashboard.apps.config as TCB


from dashboard.comun.get_energy_forecast import predict_future
from dashboard.comun.date_conditions import add_sun_data
from dashboard.comun.get_PVGIS_data import get_PVGIS_data
from dashboard.comun.get_WIBEE_data import get_WIBEE_today, get_WIBEE_today_history
from dashboard.comun.grafico_openmeteo import grafica_openmeteo

def grafico_solar_today(conn, method="rf") -> Tuple[Optional[go.Figure], Optional[str]]:
    """
    Genera un gráfico de la producción solar de hoy con:
    - Línea de producción real (datos WIBEE)
    - Línea de producción promedio histórico (datos WIBEE)  
    - Línea de producción estimada (modelo predictivo basado en datos de hoy)
    - Línea de producción promedio PVGIS (datos PVGIS)
    - Datos de salida: Figura Plotly (go.Figure) y mensaje de error (str) en caso de error

    Args:
        conn: Conexión a la base de datos SQLite
        method: Método de predicción ("lr" para regresión lineal, "rf" para Random Forest)
    Returns:
        fig: Figura Plotly con la evolución de la producción solar de hoy
        error: Mensaje de error en caso de fallo (None si no hay error)
    """

    # Obtenemos datos de producción solar de hoy desde WIBEE
    df_WIBEE_today, error = get_WIBEE_today()
    if error:
        return None, error
    df_WIBEE_today.index = df_WIBEE_today.index.tz_convert("Europe/Madrid") # Convertir a hora local
    df_WIBEE_today["hour"] = df_WIBEE_today.index.hour + df_WIBEE_today.index.minute / 60.0
    
    # Obtenemos histórico de producción WIBEE para comparar con la producción de hoy
    df_WIBEE_history, error = get_WIBEE_today_history(conn)
    if error:
        return None, f"grafico_solar_today: {error}"
    
    #Obtenemos datos de producción solar estimada para hoy a partir PVGIS
    df_PVGIS, error = get_PVGIS_data(conn)
    if error:
        return None, f"Error al obtener datos de PVGIS: {error}"

    #Obtenemos el pronostico de hoy para obtener forecast de producción solar
    hoy = date.today()
    local = grafica_openmeteo.df_cache.copy()

    df_hoy = local[local.index.date == hoy]

    df_hoy['hora']= df_hoy.index.hour + df_hoy.index.minute / 60.0
    energy_forecast, error = predict_future(conn, df_hoy, method=method)

    # Graficar
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=energy_forecast.index,
        y=energy_forecast["predicted_production"],
        name="Previsto (modelo)",
        mode="lines",
        line=dict(dash="dot")
    ))

    fig.add_trace(go.Scatter(
        x=df_WIBEE_today['hour'],
        y=df_WIBEE_today["solar_Wh"],
        name="Real (15min)",
        mode="lines"
    ))

    fig.add_trace(go.Scatter(
        x=df_WIBEE_history.index,
        y=df_WIBEE_history["solar_Wh"],
        name="WIBEE average",
        mode="lines",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=df_PVGIS['hour'],
        y=df_PVGIS["power_Wh"] * TCB.CURRENT_PEAK_POWER,
        name="PVGIS average",
        mode="lines"
    ))

    local_tz = pytz.timezone("Europe/Madrid")
    add_sun_data(fig, TCB.CASA['lat'], TCB.CASA['lon'], pd.Timestamp.now(tz=local_tz).date())

    fig.update_layout(
        title="Solar Wh",
        xaxis_title="Hora",
        yaxis_title="Wh",
        xaxis=dict(dtick=1, showgrid=True),
        yaxis=dict(showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.6,
            xanchor="center",
            x=0.5
        ),
        hovermode="x unified"  # tooltip unificado al pasar el ratón
    )

    return fig, None