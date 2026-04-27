
import pandas as pd
from datetime import date, timedelta, datetime
import pytz

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dashboard.apps.config as TCB
from dashboard.comun import date_conditions as dc
from dashboard.comun.get_prices_forecast import get_prices_forecast

def mostrar_agenda(conn, opcion):
    COLOR_MAP = {"green": "#C0DD97", "amber": "#FAC775", "red": "#F7C1C1"}

    # Construir matriz de la semana
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())

    days = [lunes + timedelta(days=i) for i in range(7)]
    hours = list(range(24))

    tz = pytz.timezone("Europe/Madrid")

    # lunes 00:00 local → UTC
    start_utc = tz.localize(datetime(lunes.year, lunes.month, lunes.day, 0, 0, 0)).astimezone(pytz.utc)

    # domingo 23:59:59 local → UTC  (o lunes siguiente 00:00)
    domingo = lunes + timedelta(days=7)
    end_utc = tz.localize(datetime(domingo.year, domingo.month, domingo.day, 0, 0, 0)).astimezone(pytz.utc)
    
    rango = {
        "start_date": start_utc,
        "end_date": end_utc,
    }
    print("Vamos a obtener precios para agenda")
    df_final, error = get_prices_forecast(conn, rango, 'rf')
    if error:
        return None, error

    df_final.index = df_final.index.tz_convert(tz)
    df_final["Renovable_pct"] = df_final['Renovable'] / df_final['Demanda real'] * 100

    min_r = df_final["Renovable_pct"].min()
    max_r = df_final["Renovable_pct"].max()
    min_p = df_final["precio_estimado"].min()
    max_p = df_final["precio_estimado"].max()

    def condicion(dt, opcion):
        # dt es hora local, buscar en df_final (ya convertido a local)

        precio = df_final.loc[dt, "precio_estimado"]
        norm_p = (precio - min_p) / (max_p - min_p) if max_p > min_p else 0.5

        renovable = df_final.loc[dt, "Renovable_pct"]
        norm_r = (renovable - min_r) / (max_r - min_r) if max_r > min_r else 0.5

        if opcion == 'Precio Estimado':
            norm = norm_p
            label   = f"{precio:.1f} €/MW"
            if norm >= 0.66:   color = "red"
            elif norm >= 0.33: color = "amber"
            else:              color = "green"
        else:
            norm = norm_r
            label   = f"{renovable:.1f}%"
            if norm >= 0.66:   color = "green"
            elif norm >= 0.33: color = "amber"
            else:              color = "red"

        tooltip = f"Renovable sobre demanda: {renovable:.1f}%<br>% Normalizado: {norm_r:.2f}<br>Precio estimado (€/Mw): {precio:.3f}<br>Precio normalizado: {norm_p:.2f}"
        return color, label, tooltip

    # agrupar por fecha local y sumar
    daily = df_final.groupby(df_final.index.date).sum()
    daily["pct"] = daily['Renovable'] / daily['Demanda real'] * 100

    renovable_pct = [f"{daily.loc[d, 'pct']:.0f}%" for d in days]

    z, text, custom = [], [], []
    for h in hours:
        row_z, row_t, row_c, row_tt = [], [], [], []
        for d in days:
            dt = pd.Timestamp(d).replace(hour=h).tz_localize("Europe/Madrid")
            color, label, tooltip = condicion(dt, opcion)

            row_z.append({"green": 0, "amber": 1, "red": 2}[color])
            row_t.append(label)
            row_c.append(color)
            row_tt.append(tooltip)
        z.append(row_z); text.append(row_t); custom.append(row_tt)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.15, 0.85],
        vertical_spacing=0.02,
    )

    # --- Panel superior: una fila por variable (row 2) ---
    variables   = ["🌅 Amanece", "🌇 Ocaso", "♻️ Renovable"]
    day_labels  = [d.strftime("%a %d/%m") for d in days]

    # construir z_info: shape (n_vars, n_dias)
    z_info = [
        [0.5] * 7,   # fila neutra — solo para que tenga alto
        [0.5] * 7,
        [0.5] * 7,
    ]

    amanece = []
    ocaso = []

    for d in days:
        horas = dc.getSunData(TCB.CASA['lat'], TCB.CASA['lon'],d)
        amanece.append(horas['amanece'].strftime("%H:%M"))
        ocaso.append(horas['ocaso'].strftime("%H:%M"))

    text_info = [ amanece, ocaso, renovable_pct]

    fig.add_trace(go.Heatmap(
        z=z_info,
        x=day_labels,
        y=variables,
        text=text_info,
        texttemplate="%{text}",
        textfont=dict(size=11),
        #colorscale=[[0,"#F1EFE8"],[1,"#F1EFE8"]],   # gris neutro plano
        showscale=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
        xgap=2, ygap=2,
    ), row=1, col=1)

    fig.add_trace(go.Heatmap(
        z=z,
        x=[d.strftime("%a %d/%m") for d in days],
        y=[f"{h:02d}h" for h in hours],
        text=text,
        customdata=custom,
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorscale=[[0, "#C0DD97"], [0.5, "#FAC775"], [1, "#F7C1C1"]],
        showscale=False,
        hovertemplate="%{x} %{y}<br>%{customdata}<extra>%{text}</extra>",
        xgap=2, ygap=2,
    ), row=2,col=1)

    fig.update_layout(
        xaxis=dict(side="top", showticklabels=True),
        yaxis=dict(autorange="reversed"),
        xaxis2=dict(showticklabels=False),  # row 2 no repite
        yaxis2=dict(autorange="reversed"),
        margin=dict(l=40, r=10, t=30, b=10),
        height=700,
    )

    return fig, None

