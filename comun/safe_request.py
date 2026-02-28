import requests

def safe_request_get(
    url,
    *,
    params=None,
    headers=None,
    timeout=5
):
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        return response, None

    except requests.exceptions.HTTPError as e:
        return None, f"Error HTTP: {e.response.status_code}"

    except requests.exceptions.ConnectionError:
        return None, "Error de conexión: no se pudo conectar al servidor"

    except requests.exceptions.Timeout:
        return None, "Timeout: el servidor tardó demasiado en responder"

    except requests.exceptions.RequestException as e:
        return None, f"Error inesperado en la petición: {e}"
