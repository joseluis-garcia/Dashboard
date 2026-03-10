"""
Módulo para obtener y gestionar ubicación del usuario con cookies.

Proporciona funciones para:
- Obtener ubicación del usuario usando geolocalización JavaScript
- Guardar ubicación en cookies del navegador
- Eliminar cookies de ubicación
"""

from typing import Tuple, Optional
import streamlit as st
from streamlit_js_eval import streamlit_js_eval


COOKIE_NAME = "user_location"


def get_user_location() -> Tuple[Optional[float], Optional[float]]:
    """
    Obtiene la ubicación del usuario desde cookies o geolocalización.
    
    Intenta leer la ubicación de una cookie existente. Si no existe,
    solicita permiso de geolocalización al usuario y guarda las
    coordenadas en una cookie para futuras visitas (30 días).
    
    Retorna:
        Tupla (latitud, longitud) o (None, None) si hay error
        
    Example:
        >>> lat, lon = get_user_location()
        >>> if lat and lon:
        ...     print(f"Ubicación: {lat}, {lon}")
    """
    # Intentar leer cookie existente
    cookie_value = streamlit_js_eval(
        js_expressions="document.cookie",
        key="read_cookie"
    )
    
    if cookie_value and "user_location" in cookie_value:
        # Extraer lat/lon de la cookie
        try:
            for c in cookie_value.split(";"):
                if "user_location=" in c:
                    value = c.split("=")[1]
                    lat, lon = value.split(",")
                    return float(lat), float(lon)
        except (ValueError, IndexError):
            pass  # Si hay error, continuar con geolocalización

    # Solicitar geolocalización al usuario
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
        try:
            lat, lon = map(float, loc.split(","))
            return lat, lon
        except (ValueError, AttributeError):
            return None, None
    else:
        return None, None


def borrar_user_location() -> None:
    """
    Elimina la cookie de ubicación del usuario.
    
    Borra la cookie "user_location" del navegador y recarga la página.
    
    Example:
        >>> if st.button("Resetear ubicación"):
        ...     borrar_user_location()
    """
    streamlit_js_eval(
        js_expressions='document.cookie = "user_location=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"',
        key="delete_cookie"
    )
    st.rerun()


__all__ = ["get_user_location", "borrar_user_location"]
