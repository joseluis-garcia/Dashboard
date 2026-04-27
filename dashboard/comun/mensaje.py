"""
Módulo para mostrar mensajes de información al usuario y gestionar la comunicación via Telegram

Proporciona funciones para:
- Renderizar DataFrames con anchos personalizados
- Mostrar mensajes e información
- Cargar mensajes desde URLs
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd
from dashboard.comun.safe_request import safe_request


def render_df_proportional(
    df: pd.DataFrame,
    widths: Optional[List[float]] = None,
    width_percent: float = 100
) -> None:
    """
    Renderiza un DataFrame como tabla HTML con anchos personalizados.
    
    Crea una tabla HTML con anchos de columna proporcionales configurables,
    mostrada dentro de Streamlit.
    
    Args:
        df: DataFrame a renderizar
        widths: Lista de proporciones (ej: [0.1, 0.3, 0.3, 0.3])
               Si None o vacío, distribuye columnas equitativamente
        width_percent: Ancho total de la tabla en porcentaje (por defecto 100%)
        
    Example:
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        >>> render_df_proportional(df, widths=[0.3, 0.7])
    """
    # Si widths no viene o viene vacío → columnas iguales
    if not widths:
        n = len(df.columns)
        widths = [1 / n] * n

    # Convertir proporciones a porcentajes
    widths_pct = [w * 100 for w in widths]

    # Construir tabla HTML con estilos
    html = f"""
    <style>
    .custom-table {{
        width: {width_percent}%;
        margin-left: auto;
        margin-right: auto;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 12px;
    }}
    .custom-table th, .custom-table td {{
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        line-height: 1 !important;
        border: 1px solid #ddd;
        text-align: right;
        vertical-align: top;
        word-wrap: break-word;
        white-space: normal;
    }}
    </style>
    """

    html += '<table class="custom-table">'

    # Cabecera
    html += "<thead><tr>"
    for col, w in zip(df.columns, widths_pct):
        html += f'<th style="width:{w}%">{col}</th>'
    html += "</tr></thead>"

    # Filas de datos
    html += "<tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for cell in row:
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(ttl=86400)  # Cache 1 día
def show_mensaje() -> None:
    """
    Carga y muestra un mensaje desde una URL externa.
    
    Obtiene un CSV con mensajes desde una URL de SOM Energía
    y lo renderiza como tabla HTML proporcional.
    
    Example:
        >>> show_mensaje()
    """
    MENSAJE_URL = "https://next.somenergia.coop/s/zsqtRiKoCSjzcfW/download"
    #MENSAJE_URL = "https://next.somenergia.coop/s/zsqtRiKoCSjzcfW/download?path=/&files=mensaje_semanal.txt"
    try:
        df_mensaje = pd.read_csv(
            MENSAJE_URL,
            sep="|",
            encoding="utf-8-sig"
        )
        # Renderizar tabla con anchos personalizados
        render_df_proportional(
            df_mensaje,
            widths=[0.1, 0.3, 0.3, 0.3],
            width_percent=100
        )
    except Exception as e:
        st.error(f"Error al cargar mensajes: {e}")


def mostrar_alerta(
    mensaje: str,
    tipo: str = "info"
) -> None:
    """
    Muestra un mensaje de alerta al usuario.
    
    Args:
        mensaje: Texto del mensaje a mostrar
        tipo: Tipo de alerta ("info", "warning", "error", "success")
        
    Example:
        >>> mostrar_alerta("Operación completada", tipo="success")
    """
    if tipo == "error":
        st.error(mensaje)
    elif tipo == "warning":
        st.warning(mensaje)
    elif tipo == "success":
        st.success(mensaje)
    else:
        st.info(mensaje)


def mostrar_recomendacion(
    titulo: str,
    descripcion: str,
    accion: Optional[Any] = None
) -> None:
    """
    Muestra una recomendación personalizada.
    
    Args:
        titulo: Título de la recomendación
        descripcion: Descripción detallada
        accion: Función callback si el usuario hace clic
        
    Example:
        >>> mostrar_recomendacion(
        ...     "Precio bajo ahora",
        ...     "Es buen momento para consumir energía"
        ... )
    """
    with st.container(border=True):
        st.markdown(f"### 💡 {titulo}")
        st.markdown(descripcion)

        if accion:
            if st.button("Actuar", key=titulo):
                accion()


def formatear_precio(
    precio: float,
    moneda: str = "€"
) -> str:
    """
    Formatea un precio para mostrar al usuario.
    
    Args:
        precio: Valor numérico del precio
        moneda: Símbolo de moneda (por defecto "€")
        
    Returns:
        String formateado con 2 decimales
        
    Example:
        >>> formatear_precio(45.678)
        '45.68€'
    """
    return f"{precio:.2f}{moneda}"

def send_TG_message( texto: str):
    TG_token = st.secrets.get("TG_token")

    TG_chat_id_mio = st.secrets.get("TG_chat_id_mio")
    TG_chat_id_canal = st.secrets.get("TG_chat_id_canal")  

    TG_url = f"https://api.telegram.org/bot{TG_token}/sendMessage"
    data = dict(chat_id=TG_chat_id_mio, text= texto)
    response, error = safe_request(TG_url,method="POST", params=data)

    print(response, error)

__all__ = [
    "render_df_proportional",
    "show_mensaje",
    "mostrar_alerta",
    "mostrar_recomendacion",
    "formatear_precio",
    "send_TG_message"
]
