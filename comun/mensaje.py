import streamlit as st
import pandas as pd

def render_df_proportional(df, widths, width_percent = 100):

    # Si widths no viene o viene vacío → columnas iguales
    if not widths:
        n = len(df.columns)
        widths = [1 / n] * n
    
    # Convertimos proporciones a %
    widths_pct = [w * 100 for w in widths]

    # Construir tabla HTML
    html = """
    <style>
    .custom-table {
        width: {width_percent}%;
        margin-left: auto;
        margin-right: auto;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 12px;   /* ↓ tamaño del texto */
    }
    .custom-table th, .custom-table td {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        line-height: 1 !important;
        border: 1px solid #ddd;
        text-align: right;
        vertical-align: top;
        word-wrap: break-word;
        white-space: normal;
    }
    </style>
    """

    html += '<table class="custom-table">'
    
    # Cabecera
    html += "<thead><tr>"
    for col, w in zip(df.columns, widths_pct):
        html += f'<th style="width:{w}%">{col}</th>'
    html += "</tr></thead>"

    # Filas
    html += "<tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for cell in row:
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)

@st.cache_data(ttl=86400) # cache 1 dia
def show_mensaje():
    MENSAJE_PATH = "https://next.somenergia.coop/s/MzaQLZS3HmJ4ZEB/download?path=%2F&files=mensaje.csv"
    df_spot = pd.read_csv(
            MENSAJE_PATH,
            sep=",", 
            encoding="utf-8-sig")
    render_df_proportional(df_spot, widths=[0.1, 0.3, 0.3, 0.3], width_percent=100)