    
from comun.get_ESIOS_indicator import get_indicator
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
    
def grafico_ESIOS_energy(df_energia):
    #fig = go.Figure()
# --------------------------------------------------------- 
# Crear figura con doble eje Y correctamente
# --------------------------------------------------------- 
    fig = make_subplots( rows=1, cols=1, specs=[[{"secondary_y": True}]] )

    # --- BARRAS DE ENERGIA ---
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
    
    fig.add_trace(
        go.Scatter(
            x=df_energia["datetime"],
            y=df_energia["demanda"],
            mode="lines",
            name="Demanda",
            line=dict(color="blue", width=2)
        )
    )

    # Línea de temperatura
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
    # Asegurar que queda por encima del cloudcover 
    fig.data[-1].update(zorder=10)

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
    
    fig.update_xaxes( dtick="D1", tickangle=45)
    return fig