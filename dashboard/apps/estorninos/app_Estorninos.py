import streamlit as st
import sys
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz

from dashboard.comun import date_conditions as dc
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_forecast
from dashboard.comun.grafico_ESIOS_energy import grafico_ESIOS_energy
from dashboard.comun.grafico_prices_forecast import grafico_prices_forecast
from dashboard.apps.estorninos.historico_spot import load_historico_precios_spot
from dashboard.apps.estorninos.historico_temperaturas import load_historico_temperaturas
from dashboard.comun.mensaje import show_mensaje
from dashboard.comun import sql_utilities as db

conn, error = db.init_db()
if conn is None:
    st.error(f"Error al conectar a la base de datos: {error}")
    sys.exit(1)

# =========================
# Rango temporal de analisis hoy menos 5 dias y hoy mas 10 dias en futuro
# =========================
tz = pytz.timezone("Europe/Madrid")
today = tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0))
start_date = today + timedelta(days=-5)
end_date = today + timedelta(days=10)
# Para probar fechas fijas
# start_date = tz.localize( datetime(2026, 1, 1).replace(minute=0, second=0, microsecond=0))
# end_date = tz.localize( datetime(2026, 1, 8).replace(minute=0, second=0, microsecond=0))
rango = {
    "start_date": start_date,
    "end_date": end_date,
}
dc.date_conditions_init(rango)  # Inicializar condiciones de fecha (festivos, fines de semana, hoy)

# Función para centrar el texto de los headers
def header_centrado(texto):
    st.markdown(
        f"<h2 style='text-align: center;'>{texto}</h2>",
        unsafe_allow_html=True
    )

# =========================
# DEFINICION UI
# =========================
st.markdown("""
<style>

/* Contenedor general de las tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 14px !important;                 /* separación entre pestañas */
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}

/* Cada pestaña (texto y padding) */
.stTabs [data-baseweb="tab"] {
    font-size: 22px !important;           /* tamaño del texto */
    font-weight: 600 !important;          /* grosor */
    padding: 12px 22px !important;        /* tamaño de la pestaña */
    border-radius: 6px !important;
}

/* Pestaña seleccionada */
.stTabs [aria-selected="true"] {
    background-color: #1f77b4 !important; /* color de fondo */
    color: white !important;              /* color del texto */
}

/* Pestañas no seleccionadas */
.stTabs [aria-selected="false"] {
    background-color: #e6e6e6 !important;
    color: #333 !important;
}

</style>
""", unsafe_allow_html=True)
st.set_page_config(layout="wide")
st.title("Visualización de variables ESIOS")

tab_curvas, tab_precios, tab_temperaturas, tab_summary = st.tabs(["Curvas", "Precios", "Temperaturas", "Resumen"])

with tab_curvas:
    st.info(f"Rango de fechas: {rango['start_date']} → {rango['end_date']}")
    st.subheader("Predicción Energia")
    df_energia, error = get_ESIOS_energy_forecast(rango)
    if error:
        st.error(f"Error al obtener datos de energía: {error}")
    else:
        fig_energia = grafico_ESIOS_energy(df_energia)
        st.plotly_chart(fig_energia, width='stretch')
           
# =========================
# Prepara gráfico de precios
# =========================
    st.subheader("Predicción Precios")
    show_mensaje()  

    fig_forecast, error = grafico_prices_forecast(rango)
    if error:
        st.error(f"Error al crear gráfico de precios: {error}")
    else:
        st.plotly_chart(fig_forecast, width='stretch', config={"renderer": "svg"})
# 
with tab_precios:
    fig_precios, ticks_mes = load_historico_precios_spot(conn, True, True)
    st.subheader("Mapa de precios spot histórico")
    st.plotly_chart(fig_precios, width='stretch', key="precios")

# # with tab_peajes:
# #     fig_peajes, ticks_mes = load_historico_peajes(True, True)
# #     st.subheader("Mapa de peajes y cargos histórico")
# #     st.plotly_chart(fig_peajes, width='stretch', key="peajes")

with tab_temperaturas:
    fig_temperaturas, ticks_mes = load_historico_temperaturas(True, True)
    st.subheader("Mapa de temperaturas históricas")
    st.plotly_chart(fig_temperaturas, width='stretch', key="temperaturas")

with tab_summary:
    # Crear subplots con eje Y compartido
    fig_comb = make_subplots(
        rows=1, 
        cols=3,
        column_widths=[0.45, 0.1, 0.45],  # ejeY ocupa poco
        shared_yaxes=True,
        horizontal_spacing=0.05
    )

#     # Convertir px.imshow() a traces limpios
#     trace1 = px_to_trace(fig_precios, colorbar_side="left", colorscale="Turbo")
#     trace2 = px_to_trace(fig_temperaturas, colorbar_side="right", colorscale="RdBu_r")

    fig_precios.data[0].colorbar.update(x=0.15,y=0.53,xref="container")
    fig_temperaturas.data[0].colorbar.update(x=1.1,y=0.53,xref="container")
    # Añadir al subplot
    fig_comb.add_trace(fig_precios.data[0], row=1, col=1)
    fig_comb.add_trace(fig_temperaturas.data[0], row=1, col=3)

# --- Eje Y central (solo etiquetas) ---
    fig_comb.add_trace(
        go.Scatter(
            x=[0]*len(ticks_mes),
            y=ticks_mes,
            text=[d.strftime("%Y-%m") for d in ticks_mes],
            mode="text",
            showlegend=False
        ),
        row=1,
        col=2
    )

    # Hacer que el eje Y exista
    fig_comb.update_yaxes(visible=True, showticklabels=False, row=1, col=2)

    # Ocultar los ejes del subplot central
    fig_comb.update_xaxes(visible=False, row=1, col=2)
    fig_comb.update_yaxes(visible=False, row=1, col=2)

    # Ocultar eje Y del segundo heatmap
    fig_comb.update_yaxes(showticklabels=False, row=1, col=1)
    fig_comb.update_yaxes(showticklabels=False, row=1, col=3)

    # Ajustar layout
    fig_comb.update_layout(
        height=900,
        margin=dict(l=30, r=30, t=40, b=40)
    )

    # Mostrar en Streamlit
    st.subheader("Mapa de temperaturas y precios históricos")
    st.plotly_chart(fig_comb, width='stretch', key="resumen")

