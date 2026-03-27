"""
Módulo de utilidades para requests seguros.

Proporciona wrappers seguros alrededor de requests.get() para manejar
errores de red de forma consistente.
"""

import requests
from typing import Tuple, Optional

def safe_request(
    url: str,
    *,
    method: str = "GET",
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
    json_data: Optional[dict] = None
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """
    Realiza un request seguro con manejo de errores.
    
    Args:
        url: URL para el request
        method: Método HTTP (GET, POST, etc.)
        params: Parámetros de query
        headers: Headers HTTP
        timeout: Timeout en segundos
        json_data: Datos JSON para enviar (para POST, PUT, etc.)
        
    Returns:
        Tupla (response, error) donde:
        - response: objeto Response si exitoso, None si hay error
        - error: mensaje de error si hay error, None si exitoso
        
    Example:
        >>> response, error = safe_request("https://api.example.com/data")
        >>> if error:
        ...     print(f"Error: {error}")
        ... else:
        ...     data = response.json()
    """
    try:
        if method.upper() == "GET":
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
        elif method.upper() == "POST":
            response = requests.post(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                json=json_data
            )
        else:
            response = requests.request(
                method,
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                json=json_data
            )
        
        response.raise_for_status()
        return response, None

    except requests.exceptions.HTTPError as e:
        return None, f"Error HTTP {e.response.status_code}: {e.response.reason}"

    except requests.exceptions.ConnectionError:
        return None, "Error de conexión: no se pudo conectar al servidor"

    except requests.exceptions.Timeout:
        return None, "Timeout: el servidor tardó demasiado en responder"

    except requests.exceptions.RequestException as e:
        return None, f"Error en la petición: {e}"

    except Exception as e:
        return None, f"Error inesperado: {e}"

def safe_request_get(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 60
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """
    Realiza un GET request seguro.
    
    Alias para safe_request() con method="GET".
    
    Args:
        url: URL para el request
        params: Parámetros de query
        headers: Headers HTTP
        timeout: Timeout en segundos
        
    Returns:
        Tupla (response, error)
    """
    return safe_request(
        url,
        method="GET",
        params=params,
        headers=headers,
        timeout=timeout
    )

__all__ = ["safe_request", "safe_request_get"]
