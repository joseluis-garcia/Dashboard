import streamlit as st
import sys
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from zoneinfo import ZoneInfo
from dashboard.comun.mensaje import send_TG_message
from dashboard.comun import date_conditions as dc
from dashboard.comun.get_ESIOS_data import get_ESIOS_energy_forecast
from dashboard.comun.grafico_ESIOS_energy import grafico_ESIOS_energy
from dashboard.comun.grafico_prices_forecast import grafico_prices_forecast
from dashboard.apps.estorninos.mostrar_agenda import mostrar_agenda
from dashboard.apps.estorninos.historico_spot import load_historico_precios_spot
from dashboard.apps.estorninos.historico_temperaturas import load_historico_temperaturas, grafico_historico_temperaturas, grafico_stress_termico
from dashboard.comun.mensaje import show_mensaje
from dashboard.comun import sql_utilities as db

conn, error = db.init_db()
if conn is None:
    st.error(f"Error al conectar a la base de datos: {error}")
    sys.exit(1)

# =========================
# Rango temporal de analisis hoy menos 5 dias y hoy mas 10 dias en futuro
# =========================
tz = ZoneInfo("Europe/Madrid")
today = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
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
conn, error = db.init_db() # Inicializar acceso a la base de datos
if conn is None:
    st.error(f"Error al conectar a la base de datos: {error}")
    sys.exit(1)
# Función para centrar el texto de los headers
def header_centrado(texto):
    st.markdown(
        f"<h2 style='text-align: center;'>{texto}</h2>",
        unsafe_allow_html=True
    )

# Funciones para autenticación de admin (para enviar mensajes a Telegram)
def check_admin_password(pwd: str) -> bool:
    print(f"Verificando contraseña de administrador: {pwd} contra {st.secrets['ADMIN_password']}")
    return pwd == st.secrets["ADMIN_password"]

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

tab_curvas, tab_agenda, tab_algoritmo, tab_precios, tab_temperaturas, tab_stress = st.tabs(["Curvas", "Agenda", "Algoritmo", "Precios", "Temperaturas","Stress térmico"])

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

    fig_forecast, error = grafico_prices_forecast(conn, rango, method='rf')
    if error:
        st.error(f"Error al crear gráfico de precios: {error}")
    else:
        st.plotly_chart(fig_forecast, width='stretch', config={"renderer": "svg"})
# 

with tab_agenda:
    st.subheader("Agenda")
    st.info(f"Estamos en {dc.get_estacion(today)}")
    col1, col2, col3 = st.columns([3, 3, 3])   # proporciones
    with col1:
        st.markdown(
            "<div style='padding-top: 32px;'>Selecciona criterio para colorear la agenda:</div>",
            unsafe_allow_html=True
        )
    with col2:
        opcion = st.selectbox(" Prueba ", ["Renovable versus Demanda", "Precio Estimado"])
    with col3:
        st.empty()

    fig_agenda, error = mostrar_agenda(conn, opcion)
    if error:
        st.error(error)
    else:
        st.plotly_chart(fig_agenda, width='stretch', key="agenda")

with tab_algoritmo:

    # --- Inicialización ---
    if "show_admin_login" not in st.session_state:
        st.session_state["show_admin_login"] = False
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    st.subheader("Algoritmo")
    st.write("En esta página se desarrollará la lógica para el envio de mensajes a los estorninos a mediante el canal de Telegram al que te puedes suscribir siguiendo este enlace https://t.me/+qsGht4W8dZ4yMjU8")
    st.write("A modo de prueba, si estas autorizado, el texto que escribas en este área se enviará a todos los que se hubieran suscrito al canal <Estorninos de Som> en Telegram")
    comentario = st.text_area("Texto a enviar")
    # --- Botón principal ---
    if st.button("Enviar"):
        if st.session_state["is_admin"]:
            # Ya autenticado, ejecutar directamente
            send_TG_message(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} - Mensaje desde App: {comentario}")
            st.success("Mensaje enviado")
        else:
            # Pedir autenticación
            st.session_state["show_admin_login"] = True

    # --- Form de login
    if st.session_state["show_admin_login"] and not st.session_state["is_admin"]:
        with st.form("admin_login_form"):
            st.markdown("🔒 **Acceso administrador**")
            pwd = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar")
            
            if submitted:
                if check_admin_password(pwd):
                    st.session_state["is_admin"] = True
                    st.session_state["show_admin_login"] = False
                    mensaje, error = send_TG_message(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} - Mensaje desde App: {comentario}")
                    if error:
                        st.error(f"Error al enviar mensaje a Telegram: {error}")
                    else:
                        st.success("Mensaje enviado a Telegram")
                        st.rerun()
                else:
                    st.error("Contraseña incorrecta")

with tab_precios:
    fig_precios, ticks_mes = load_historico_precios_spot(conn, True, True)
    st.subheader("Mapa de precios spot histórico")
    st.plotly_chart(fig_precios, width='stretch', key="precios")

# # with tab_peajes:
# #     fig_peajes, ticks_mes = load_historico_peajes(True, True)
# #     st.subheader("Mapa de peajes y cargos histórico")
# #     st.plotly_chart(fig_peajes, width='stretch', key="peajes")

temp_matrix, error = load_historico_temperaturas(conn)
if error:
    st.error(f"Error al cargar temperaturas históricas: {error}")

with tab_temperaturas:
    fig_temperaturas = grafico_historico_temperaturas(temp_matrix, True, True)
    st.subheader("Mapa de temperaturas históricas")
    st.plotly_chart(fig_temperaturas, width='stretch', key="temperaturas")

with tab_stress:

    st.subheader("Mapa de stress térmico")
    col1,col2 = st.columns(2)
    with col1:
        tMin = st.slider("Frio por debajo de:", -20, 30, 15)
    with col2:
        tMax = st.slider("Calor por encima de:", 15, 45, 28)

    st.write(f"El mapa de stress térmico se calcula a partir de las temperaturas históricas, asignando a cada hora un valor con la diferencia {tMin} - tºC si t < {tMin} y tºC - {tMax} si t >= {tMax}. Las horas con temperaturas confortables entre {tMin} y {tMax} no se representan en el mapa de stress.")
    fig_stress = grafico_stress_termico(temp_matrix, tMin, tMax)
    st.plotly_chart(fig_stress, width='stretch', key="stress")

# with tab_summary:
#     # Crear subplots con eje Y compartido
#     fig_comb = make_subplots(
#         rows=1, 
#         cols=3,
#         column_widths=[0.45, 0.1, 0.45],  # ejeY ocupa poco
#         shared_yaxes=True,
#         horizontal_spacing=0.05
#     )

# #     # Convertir px.imshow() a traces limpios
# #     trace1 = px_to_trace(fig_precios, colorbar_side="left", colorscale="Turbo")
# #     trace2 = px_to_trace(fig_temperaturas, colorbar_side="right", colorscale="RdBu_r")

#     fig_precios.data[0].colorbar.update(x=0.15,y=0.53,xref="container")
#     fig_temperaturas.data[0].colorbar.update(x=1.1,y=0.53,xref="container")
#     # Añadir al subplot
#     fig_comb.add_trace(fig_precios.data[0], row=1, col=1)
#     fig_comb.add_trace(fig_temperaturas.data[0], row=1, col=3)

# # --- Eje Y central (solo etiquetas) ---
#     fig_comb.add_trace(
#         go.Scatter(
#             x=[0]*len(ticks_mes),
#             y=ticks_mes,
#             text=[d.strftime("%Y-%m") for d in ticks_mes],
#             mode="text",
#             showlegend=False
#         ),
#         row=1,
#         col=2
#     )

    # # Hacer que el eje Y exista
    # fig_comb.update_yaxes(visible=True, showticklabels=False, row=1, col=2)

    # # Ocultar los ejes del subplot central
    # fig_comb.update_xaxes(visible=False, row=1, col=2)
    # fig_comb.update_yaxes(visible=False, row=1, col=2)

    # # Ocultar eje Y del segundo heatmap
    # fig_comb.update_yaxes(showticklabels=False, row=1, col=1)
    # fig_comb.update_yaxes(showticklabels=False, row=1, col=3)

    # # Ajustar layout
    # fig_comb.update_layout(
    #     height=900,
    #     margin=dict(l=30, r=30, t=40, b=40)
    # )

    # # Mostrar en Streamlit
    # st.subheader("Mapa de temperaturas y precios históricos")
    # st.plotly_chart(fig_comb, width='stretch', key="resumen")

