import streamlit as st
from streamlit_js_eval import streamlit_js_eval
# ---------------------------------------------------------
# Verificamos si hay un coockie user_location de la sesión actual, si no lo hay pedimos geolocalización al usuario y guardamos la latitud y longitud en una cookie para futuras visitas. 
# ---------------------------------------------------------
COOKIE_NAME = "user_location"
def get_user_location():

    # Intentar leer cookie
    cookie_value = streamlit_js_eval(
        js_expressions="document.cookie",
        key="read_cookie"
    )
    if cookie_value and "user_location" in cookie_value:
        # Extraer lat/lon de la cookie
        for c in cookie_value.split(";"):
            if "user_location=" in c:
                value = c.split("=")[1]
                lat, lon = value.split(",")
                return float(lat), float(lon)
    else:
        # Pedir geolocalización al usuario
        loc = streamlit_js_eval(
            js_expressions="""
            new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        const lat = pos.coords.latitude;
                        const lon = pos.coords.longitude;
                        document.cookie = "user_location=" + lat + "," + lon + "; path=/; max-age=2592000";
                        resolve(lat + "," + lon);
                    },
                    (err) => resolve("error")
                );
            })
            """,
            key="get_location"
        )

        if loc and loc != "error":
            lat, lon = map(float, loc.split(","))
            return lat, lon
        else:
            return None, None

def borrar_user_location():
    streamlit_js_eval(
        js_expressions='document.cookie = "user_location=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"',
        key="delete_cookie"
    )
    st.experimental_rerun()