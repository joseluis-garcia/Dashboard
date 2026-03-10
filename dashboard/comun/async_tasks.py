"""
Módulo para ejecutar tareas en paralelo usando threading.

Proporciona funciones para:
- Ejecutar funciones en threads separados (no async realmente)
- Mostrar placeholders de carga mientras se ejecutan tareas
- Manejar resultados y errores de tareas paralelas
"""

from typing import Callable, Any, Optional, Dict
import threading
import time
import streamlit as st


@st.cache_resource
def get_task_container() -> Dict[str, Dict[str, Any]]:
    """
    Obtiene el contenedor de tareas global (caché de Streamlit).
    
    Retorna un diccionario que persiste entre reruns para almacenar
    el estado y resultados de tareas asincrónicas.
    
    Returns:
        Diccionario para almacenar tareas
        
    Example:
        >>> container = get_task_container()
        >>> container['mi_tarea'] = {"status": "running", ...}
    """
    return {}


def run_async(
    task_name: str,
    func: Callable,
    *args: Any,
    **kwargs: Any
) -> None:
    """
    Ejecuta una función en un thread separado.
    
    Lanza una función en un thread daemon que se ejecuta en paralelo.
    Si la tarea ya existe, no la relanza.
    
    Args:
        task_name: Identificador único de la tarea
        func: Función a ejecutar
        *args: Argumentos posicionales para la función
        **kwargs: Argumentos con nombre para la función
        
    Example:
        >>> def mi_funcion(x, y):
        ...     return x + y
        >>> run_async("suma", mi_funcion, 5, 10)
    """
    container = get_task_container()

    # Si ya existe, no relanzar
    if task_name in container:
        return

    container[task_name] = {"status": "running", "result": None, "error": None}

    def wrapper() -> None:
        """Wrapper que ejecuta la función y captura resultados/errores."""
        try:
            result = func(*args, **kwargs)
            container[task_name]["result"] = result
            container[task_name]["status"] = "done"
        except Exception as e:
            container[task_name]["error"] = str(e)
            container[task_name]["status"] = "error"

    # Crear y lanzar thread daemon
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()


def async_placeholder(
    task_name: str,
    render_func: Callable[[Any], None],
    loading_message: str = "Cargando…"
) -> None:
    """
    Muestra un placeholder mientras se ejecuta una tarea asincrónica.
    
    Verifica el estado de una tarea en ejecución. Si está corriendo,
    muestra un mensaje de carga. Si terminó, ejecuta la función de
    renderizado. Si hay error, muestra el mensaje de error.
    
    Args:
        task_name: Identificador de la tarea a monitorear
        render_func: Función que renderiza el resultado
                    (recibe el resultado como parámetro)
        loading_message: Mensaje a mostrar mientras carga (por defecto "Cargando…")
        
    Example:
        >>> def mostrar_resultado(data):
        ...     st.write(data)
        >>> async_placeholder("mi_tarea", mostrar_resultado, "Por favor espera...")
    """
    poll_interval = 2
    container = get_task_container()

    task = container.get(task_name)

    # Tarea no existe o está en ejecución
    if task is None or task["status"] == "running":
        st.info(loading_message)
        time.sleep(poll_interval)
        st.rerun()
        return

    # Tarea terminó con error
    if task["status"] == "error":
        st.error(f"Error: {task['error']}")
        return

    # Tarea completada exitosamente
    if task["status"] == "done":
        render_func(task["result"])


__all__ = ["get_task_container", "run_async", "async_placeholder"]
