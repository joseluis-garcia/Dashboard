import pandas as pd
from datetime import date, timedelta, datetime
import pytz

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dashboard.apps.config as TCB
from dashboard.comun import date_conditions as dc
from dashboard.comun.get_prices_forecast import get_prices_forecast

# --- Festivos (opcional) -----------------------------------------------
# Si la librería 'holidays' está disponible se usa para marcar festivos
# como "todo el día valle" en la tarifa 2.0TD. Si no está instalada,
# simplemente se ignoran los festivos y solo se distingue laborable/finde.
try:
    import holidays as _holidays_lib
    _FESTIVOS_ES = _holidays_lib.Spain(years=range(date.today().year, date.today().year + 2))
except ImportError:
    _FESTIVOS_ES = {}


def _es_dia_valle_completo(d: date) -> bool:
    """Sábado, domingo o festivo nacional -> tarifa 2.0TD en valle 24h."""
    return d.weekday() >= 5 or d in _FESTIVOS_ES


def _periodo_2_0TD(hour: int, dia_valle_completo: bool) -> str:
    """Devuelve 'P' (punta), 'L' (llano) o 'V' (valle) para 2.0TD."""
    if dia_valle_completo:
        return "V"
    if hour in (10, 11, 12, 13, 18, 19, 20, 21):
        return "P"
    if hour in (8, 9, 14, 15, 16, 17, 22, 23):
        return "L"
    return "V"


_PERIODO_LABEL = {"P": "Punta", "L": "Llano", "V": "Valle"}


def agenda_ponderada(conn, opcion, peso_eco=0.5):
    """
    conn: Conexión a la base de datos para obtener los datos de precios y renovables
    opcion: 'Precio Estimado' | 'Renovable' | 'Combinado'
    peso_eco: 0.0 (100% económico) .. 1.0 (100% ecológico), solo se usa
              cuando opcion == 'Combinado'. Viene del slider en la app.
    """

    # --- Construir ventana de 7 días desde HOY (no semana natural) -----
    hoy = date.today()
    days = [hoy + timedelta(days=i) for i in range(7)]
    hours = list(range(24))

    tz = pytz.timezone("Europe/Madrid")

    start_utc = tz.localize(datetime(hoy.year, hoy.month, hoy.day, 0, 0, 0)).astimezone(pytz.utc)
    fin_dia = days[-1] + timedelta(days=1)
    end_utc = tz.localize(datetime(fin_dia.year, fin_dia.month, fin_dia.day, 0, 0, 0)).astimezone(pytz.utc)

    rango = {"start_date": start_utc, "end_date": end_utc}
    df_final, error = get_prices_forecast(conn, rango, "rf")
    if error:
        return None, error

    df_final.index = df_final.index.tz_convert("Europe/Madrid")
    df_final["Renovable_pct"] = df_final["Renovable"] / df_final["Demanda real"] * 100

    # --- Normalización por percentil (rank), más robusta que min-max ---
    # 0 = más barato / menos renovable de la ventana, 1 = más caro / más renovable
    df_final["norm_p"] = df_final["precio_estimado"].rank(pct=True)
    df_final["norm_r"] = df_final["Renovable_pct"].rank(pct=True)

    def condicion(dt, opcion):
        precio = df_final.loc[dt, "precio_estimado"]
        renovable = df_final.loc[dt, "Renovable_pct"]
        norm_p = df_final.loc[dt, "norm_p"]   # 0 barato -> 1 caro
        norm_r = df_final.loc[dt, "norm_r"]   # 0 poco renovable -> 1 muy renovable

        precio_bad = norm_p          # 0 bueno .. 1 malo
        renov_bad = 1 - norm_r       # 0 bueno .. 1 malo

        if opcion == "Precio Estimado":
            badness = precio_bad
            label = f"{precio:.1f} €/MW"
        elif opcion == "Renovable":
            badness = renov_bad
            label = f"{renovable:.1f}%"
        else:  # 'Combinado' -> media geométrica ponderada
            # peso_eco=0 -> solo precio; peso_eco=1 -> solo renovable
            eps = 1e-6  # evita 0^0 / log(0) en los extremos
            badness = (precio_bad + eps) ** (1 - peso_eco) * (renov_bad + eps) ** peso_eco
            label = f"{precio:.0f}€ / {renovable:.0f}%"

        # Marca visual para los extremos (decil superior/inferior)
        if badness <= 0.10:
            marca = "⭐ "
        elif badness >= 0.90:
            marca = "⚠️ "
        else:
            marca = ""

        dia_valle = _es_dia_valle_completo(dt.date())
        periodo = _periodo_2_0TD(dt.hour, dia_valle)

        tooltip = (
            f"Precio estimado: {precio:.3f} €/MWh (percentil {norm_p:.2f})<br>"
            f"Renovable/demanda: {renovable:.1f}% (percentil {norm_r:.2f})<br>"
            f"Periodo 2.0TD: {_PERIODO_LABEL[periodo]}<br>"
            f"Índice combinado: {badness:.2f}"
        )
        return badness, marca + label, tooltip, periodo

    # --- Agregado diario para el panel superior -------------------------
    daily = df_final.groupby(df_final.index.date).sum()
    daily["pct"] = daily["Renovable"] / daily["Demanda real"] * 100
    renovable_pct = [f"{daily.loc[d, 'pct']:.0f}%" for d in days]

    z, text, custom = [], [], []
    periodos_por_dia = []  # para las líneas de tarifa

    for h in hours:
        row_z, row_t, row_tt, row_p = [], [], [], []
        for d in days:
            dt = pd.Timestamp(d).replace(hour=h).tz_localize("Europe/Madrid")
            badness, label, tooltip, periodo = condicion(dt, opcion)
            row_z.append(badness)
            row_t.append(label)
            row_tt.append(tooltip)
            row_p.append(periodo)
        z.append(row_z); text.append(row_t); custom.append(row_tt)
        periodos_por_dia.append(row_p)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.15, 0.85],
        vertical_spacing=0.02,
    )

    # --- Panel superior: amanecer / ocaso / % renovable diario ----------
    variables = ["🌅 Amanece", "🌇 Ocaso", "♻️ Renovable"]
    day_labels = [d.strftime("%a %d/%m") for d in days]
    x_idx = list(range(7))  # posiciones numéricas -> permiten dibujar shapes con offsets

    z_info = [[0.5] * 7, [0.5] * 7, [0.5] * 7]

    amanece, ocaso = [], []
    for d in days:
        horas = dc.getSunData(TCB.CASA["lat"], TCB.CASA["lon"], d)
        amanece.append(horas["amanece"].strftime("%H:%M"))
        ocaso.append(horas["ocaso"].strftime("%H:%M"))

    text_info = [amanece, ocaso, renovable_pct]

    fig.add_trace(go.Heatmap(
        z=z_info,
        x=x_idx,
        y=variables,
        text=text_info,
        texttemplate="%{text}",
        textfont=dict(size=11),
        showscale=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
        xgap=2, ygap=2,
    ), row=1, col=1)

    # --- Panel principal: heatmap con gradiente continuo -----------------
    fig.add_trace(go.Heatmap(
        z=z,
        x=x_idx,
        y=hours,
        text=text,
        customdata=custom,
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorscale="RdYlGn",
        reversescale=True,   # 0 (bueno) = verde, 1 (malo) = rojo
        zmin=0, zmax=1,
        showscale=False,
        hovertemplate="%{customdata}<extra></extra>",
        xgap=2, ygap=2,
    ), row=2, col=1)

    fig.update_layout(
        xaxis=dict(
            side="top", showticklabels=True,
            tickvals=x_idx, ticktext=day_labels,
        ),
        yaxis=dict(autorange="reversed"),
        xaxis2=dict(tickvals=x_idx, ticktext=day_labels, showticklabels=False),
        yaxis2=dict(
            autorange="reversed",
            tickvals=hours, ticktext=[f"{h:02d}h" for h in hours],
        ),
        margin=dict(l=40, r=10, t=30, b=10),
        height=700,
    )

    # --- Líneas gruesas: transiciones de periodo 2.0TD -------------------
    # Se agrupan columnas contiguas del mismo tipo de día (laborable / valle
    # completo) para dibujar segmentos limpios en vez de 7 líneas sueltas.
    TRANSICIONES = [7.5, 9.5, 13.5, 17.5, 21.5]  # límites entre P/L/V (horas 8,10,14,18,22)

    grupos = []
    inicio = 0
    for i in range(1, 8):
        actual_valle = _es_dia_valle_completo(days[i - 1])
        siguiente_valle = _es_dia_valle_completo(days[i]) if i < 7 else None
        if i == 7 or actual_valle != siguiente_valle:
            grupos.append((inicio, i - 1, actual_valle))
            inicio = i

    for ini, fin, es_valle in grupos:
        x0, x1 = ini - 0.55, fin + 0.55
        if es_valle:
            # todo el grupo es valle 24h: un único borde grueso alrededor
            fig.add_shape(
                type="rect", xref="x2", yref="y2",
                x0=x0, x1=x1, y0=-1, y1=24,
                line=dict(color="#4472C4", width=5),
                fillcolor="rgba(0,0,0,0)",
                row=2, col=1,
            )
        else:
            for y_line in TRANSICIONES:
                fig.add_shape(
                    type="line", xref="x2", yref="y2",
                    x0=x0, x1=x1, y0=y_line, y1=y_line,
                    line=dict(color="#4472C4", width=5),
                    row=2, col=1,
                )

    return fig, None