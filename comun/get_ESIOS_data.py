import pandas as pd
from comun.get_ESIOS_indicator import get_indicator
import comun.date_conditions as dc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    
def grafico_ESIOS_energy(df_energia: pd.DataFrame) -> go.Figure:
# --------------------------------------------------------- 
# Crear figura con doble eje Y correctamente
# --------------------------------------------------------- 
    fig = make_subplots( rows=1, cols=1, specs=[[{"secondary_y": True}]] )

    # --- BARRAS DE ENERGIA ---
    # Añadir la eólica como stack base
    fig.add_trace(
        go.Scatter(
            x=df_energia["datetime"],
            y=df_energia["eolica"],
            mode="lines",
            name="Eólica",
            line=dict(color="#00A000", width=1),
            fillcolor="rgba(0, 200, 0, 0.2)",
            stackgroup="energia"
        )
    )
    # Añadir la solar como stack sobre la eólica
    fig.add_trace(
        go.Scatter(
            x=df_energia["datetime"],
            y=df_energia["solar"],
            name="Solar",
            mode="lines",
            line=dict(color="#E6C300", width=1),
            fillcolor="rgba(230, 195, 0, 0.2)",
            stackgroup="energia"
        )
    )
    fig.update_layout(barmode="stack")
    # Línea de demanda
    fig.add_trace(
        go.Scatter(
            x=df_energia["datetime"],
            y=df_energia["demanda"],
            mode="lines",
            name="Demanda",
            line=dict(color="blue", width=2)
        )
    )
    # Línea de porcentaje renovable sobre demanda
    fig.add_trace(
        go.Scatter(
            x=df_energia["datetime"],
            y=df_energia["renovable"] / df_energia["demanda"] * 100,  # porcentaje de renovable sobre demanda
            mode="lines",
            name="%EO+FV / Demanda",
            line=dict(color="tomato", width=2, shape="spline", smoothing=1.3),
            yaxis="y2"
        )
    )
    # Asegurar que queda por encima 
    fig.data[-1].update(zorder=10)
    # Añadir rectángulos en los fines de semana
    for start, end in dc.weekends:
        fig.add_shape(
            type="rect",
            x0=start,
            x1=end,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color="rgba(150,150,150,0.6)", width=1.5),
            fillcolor="rgba(100,100,100,0.2)",
            layer="above"
    )
    # Añadir rectángulos en los días festivos
    for festivo in dc.festivos:
        fig.add_vrect(
            x0=festivo, x1=festivo + pd.Timedelta(days=1),
            fillcolor="indianred",
            opacity=0.15,
            line_width=0
        )
    # Configuración de ejes
    # Eje izquierdo (temperatura)
    fig.update_yaxes(
        title_text="MW",
        showgrid=True,
        zeroline=False,
        secondary_y=False
    )
    # Eje derecho (porcentajes: cloudcover, precipitación, etc.)
    fig.update_yaxes(
        title_text="%",
        showgrid=False,          # evitamos grid duplicado
        zeroline=False,
        secondary_y=True,
        overlaying="y",          # 👈 superpone el eje derecho sobre el izquierdo
    )
    fig.update_layout(
        title="Previsión de energía eólica, solar y demanda", 
        xaxis_title="Fecha", 
        yaxis_title="MW",
        legend=dict(
                orientation="h",          # horizontal
                yanchor="top",
                y=-0.6,                   # desplaza la leyenda hacia abajo
                xanchor="center",
                x=0.5
            ),
        hovermode="x unified")
    
    # Línea vertical para marcar el día actual
    fig.add_vline(x=dc.today, line_width=4, line_dash="dash", line_color="green", name="Hoy")
    fig.update_xaxes( dtick="D1", tickangle=45)
    return fig