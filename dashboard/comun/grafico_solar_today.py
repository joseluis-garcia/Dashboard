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
    df1, error = get_WIBEE_today()
    if error:
        return None, error
    
    df1.index = df1.index.tz_localize("UTC").tz_convert("Europe/Madrid")
    local_tz = pytz.timezone("Europe/Madrid")
    df1["hour"] = df1.index.hour + df1.index.minute / 60.0
    
    df2, error = get_WIBEE_today_history(conn)
    if error:
        return None, f"grafico_solar_today: {error}"

    df3, error = get_PVGIS_data(conn)
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
        x=df1['hour'],
        y=df1["solar_Wh"],
        name="Real (15min)",
        mode="lines"
    ))

    fig.add_trace(go.Scatter(
        x=df2.index,
        y=df2["solar_Wh"],
        name="WIBEE average",
        mode="lines",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=df3['hour'],
        y=df3["power_Wh"] * TCB.CURRENT_PEAK_POWER,
        name="PVGIS average",
        mode="lines"
    ))

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