# utils/async_tasks.py
import threading
import time
import streamlit as st

@st.cache_resource
def get_task_container():
    return {}   # Aquí guardamos resultados fuera de session_state


def run_async(task_name, func, *args, **kwargs):
    container = get_task_container()

    # Si ya existe, no relanzar
    if task_name in container:
        return

    container[task_name] = {"status": "running", "result": None, "error": None}

    def wrapper():
        try:
            result = func(*args, **kwargs)
            container[task_name]["result"] = result
            container[task_name]["status"] = "done"
        except Exception as e:
            container[task_name]["error"] = str(e)
            container[task_name]["status"] = "error"

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()


def async_placeholder(task_name, render_func, loading_message="Cargando…"):

    poll_interval=2
    container = get_task_container()

    task = container.get(task_name)

    if task is None or task["status"] == "running":
        st.info(loading_message)
        time.sleep(poll_interval)
        st.rerun()
        return

    if task["status"] == "error":
        st.error(f"Error: {task['error']}")
        return

    if task["status"] == "done":
        render_func(task["result"])
