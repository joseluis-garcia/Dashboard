"""
forecast_snapshots.py

Captura periódica de "vintages" de previsión de ESIOS (indicadores 541/542/603)
y backfill de sus valores reales finales (551/1295/600), para poder evaluar
después cómo mejora la previsión a medida que se acerca la hora real.

ESIOS no conserva el histórico de previsiones intermedias: el indicador de
previsión solo guarda el último valor disponible para cada hora. Por eso este
script debe ejecutarse cada 12h (cron/systemd timer) desde HOY en adelante;
no hay forma de reconstruir el pasado.

Uso standalone (para pruebas locales, sigue tu patrón de load_secrets):
    python forecast_snapshots.py

Uso en scheduler:
    exit 0  -> todas las tareas ok
    exit 1  -> alguna tarea falló (revisar log)
"""

import sqlite3
import time
import sys
from pathlib import Path

import pandas as pd

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # ajusta los .parent según tu estructura
sys.path.insert(0, str(BASE_DIR))

from dashboard.comun.load_secrets import load_secrets
load_secrets(base_dir=BASE_DIR)

from dashboard.comun.get_ESIOS_data import fetch_multiple_indicators# --------------------------------------------------------------------------
# AJUSTAR: imports reales de tu proyecto
# --------------------------------------------------------------------------
# from utils.secrets import load_secrets
# from apis.esios_client import fetch_multiple_indicators
#
# Firma confirmada: fetch_multiple_indicators(indicator_ids, start_date, end_date)
#   -> pd.DataFrame ANCHO, columna 'datetime' en UTC (tz-aware) + una columna
#   por indicador con su NOMBRE CORTO (no el id numérico).
# --------------------------------------------------------------------------

TZ = "Europe/Madrid"

# AJUSTAR: ruta real de tu base de datos
DB_PATH = Path("/mnt/datos/proyectos/dashboard/data/dashboard.db")

# Nombre corto de columna tal y como lo devuelve fetch_multiple_indicators.
# OJO: 542 y 1295 difieren solo en la mayúscula de la "f" ("Fotovoltaica" vs
# "fotovoltaica") - viene así de ESIOS, no es un typo nuestro. Si algún día
# ESIOS cambia el nombre, solo hay que tocarlo aquí.
INDICATOR_NAMES = {
    541: "Previsión eólica",
    542: "Solar fotovoltaica",
    603: "Previsión semanal",   # previsión de demanda
    551: "Eólica",
    1295: "Solar fotovoltaica",
    600: "Mercado SPOT",        # demanda real
}

# Mapeo indicador de previsión -> indicador de valor real/final
FORECAST_TO_REAL = {
    541: 551,   # eólica
    542: 1295,  # solar
    603: 600,   # demanda
}

DAYS_AHEAD = 9  # horizonte máximo publicado por ESIOS para estos indicadores


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS forecast_snapshots (
    indicator_id     INTEGER NOT NULL,
    fetch_ts         TEXT    NOT NULL,   -- ISO8601 naive (Europe/Madrid), hora de captura
    target_datetime  TEXT    NOT NULL,   -- ISO8601 naive (Europe/Madrid), hora prevista
    horizon_hours    REAL    NOT NULL,   -- target_datetime - fetch_ts, en horas
    value             REAL,
    PRIMARY KEY (indicator_id, fetch_ts, target_datetime)
);

CREATE TABLE IF NOT EXISTS real_values (
    indicator_id  INTEGER NOT NULL,
    datetime      TEXT    NOT NULL,      -- ISO8601 naive (Europe/Madrid)
    value          REAL,
    PRIMARY KEY (indicator_id, datetime)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_target
    ON forecast_snapshots (indicator_id, target_datetime);

CREATE INDEX IF NOT EXISTS idx_snapshots_fetch
    ON forecast_snapshots (indicator_id, fetch_ts);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    # OJO: no uses `db_path: Path = DB_PATH` como default -  un default de
    # función se evalúa UNA vez al definirla, así que reasignar DB_PATH
    # después (p.ej. en tests) no tendría efecto. Por eso se resuelve aquí.
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


# --------------------------------------------------------------------------
# Helpers de datetime (siguiendo tus convenciones: tz_localize / tz_convert,
# y siempre se guarda naive en SQLite)
# --------------------------------------------------------------------------

def _strip_tz(series: pd.Series) -> pd.Series:
    """Convierte a Europe/Madrid si hace falta y quita tz antes de guardar."""
    if series.dt.tz is None:
        return series
    return series.dt.tz_convert(TZ).dt.tz_localize(None)


def _wide_to_long(df: pd.DataFrame, indicator_ids: list[int]) -> pd.DataFrame:
    """
    fetch_multiple_indicators devuelve formato ANCHO: 'datetime' (UTC) +
    una columna por indicador con su nombre corto (ver INDICATOR_NAMES).
    Aquí lo pasamos a formato largo con el id numérico, que es lo que
    usamos como clave en las tablas.
    """
    col_by_id = {i: INDICATOR_NAMES[i] for i in indicator_ids}

    missing = [i for i, col in col_by_id.items() if col not in df.columns]
    if missing:
        raise KeyError(
            f"Columnas esperadas no encontradas en el df de ESIOS para "
            f"indicadores {missing}: buscaba {[col_by_id[i] for i in missing]}, "
            f"columnas disponibles: {list(df.columns)}"
        )

    long_df = df.melt(
        id_vars=["datetime"],
        value_vars=list(col_by_id.values()),
        var_name="col_name",
        value_name="value",
    )
    name_to_id = {v: k for k, v in col_by_id.items()}
    long_df["indicator_id"] = long_df["col_name"].map(name_to_id)
    return long_df.drop(columns=["col_name"])


# --------------------------------------------------------------------------
# Captura de snapshots de previsión
# --------------------------------------------------------------------------

def collect_forecast_snapshot(
    indicator_ids: list[int] | None = None,
    days_ahead: int = DAYS_AHEAD,
    conn: sqlite3.Connection | None = None,
) -> int:
    """
    Pide a ESIOS la previsión vigente ahora mismo para los próximos
    `days_ahead` días y la guarda como una "foto" (snapshot) con su
    horizonte calculado. Devuelve el nº de filas insertadas/actualizadas.
    """
    indicator_ids = indicator_ids or list(FORECAST_TO_REAL.keys())
    own_conn = conn is None
    conn = conn or get_connection()

    now = pd.Timestamp.now(tz=TZ).floor("h")
    end = now + pd.Timedelta(days=days_ahead)

    # AJUSTAR: confirmar si start_date/end_date deben ir en Europe/Madrid o
    # en UTC - lo dejo en TZ porque es lo habitual en tu cliente de ESIOS,
    # pero como la respuesta viene en UTC, si tu función NO convierte
    # internamente el rango de entrada, cambia esto a now.tz_convert("UTC")
    # y end.tz_convert("UTC").
    rango = {
        "start_date": now.tz_convert("UTC"),
        "end_date": end.tz_convert("UTC"),
    }
    df, error = fetch_multiple_indicators(indicator_ids, rango)

    if (error is not None) or (df is None):
        raise ValueError(f"fetch_multiple_indicators devolvió errores {error} para {indicator_ids} en rango {rango}")

    if df.empty:
        raise ValueError(f"fetch_multiple_indicators no devolvió datos para {indicator_ids}")
    
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "datetime"})  # la primera columna tras reset_index() es siempre el antiguo índice

    print("Fetch multi", df.head())
    df = _wide_to_long(df, indicator_ids)

    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    # fetch_multiple_indicators devuelve UTC tz-aware; si por lo que sea
    # llegara naive, asumimos que es UTC (nunca local) antes de convertir.
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert(TZ)

    df["horizon_hours"] = (df["datetime"] - now) / pd.Timedelta(hours=1)
    df["target_datetime"] = _strip_tz(df["datetime"])
    df["fetch_ts"] = now.tz_localize(None)  # 'now' ya es tz-aware Europe/Madrid

    out = df[["indicator_id", "fetch_ts", "target_datetime", "horizon_hours", "value"]]
    out = out.dropna(subset=["value"])

    rows = out.to_records(index=False).tolist()
    # normaliza Timestamps a string ISO para el INSERT
    rows = [
        (int(ind), str(fts), str(tgt), float(h), float(v) if v is not None else None)
        for ind, fts, tgt, h, v in rows
    ]

    conn.executemany(
        """
        INSERT INTO forecast_snapshots
            (indicator_id, fetch_ts, target_datetime, horizon_hours, value)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (indicator_id, fetch_ts, target_datetime)
        DO UPDATE SET value = excluded.value, horizon_hours = excluded.horizon_hours
        """,
        rows,
    )
    conn.commit()

    if own_conn:
        conn.close()

    return len(rows)


# --------------------------------------------------------------------------
# Backfill de valores reales
# --------------------------------------------------------------------------

def backfill_real_values(
    lookback_days: int = 3,
    conn: sqlite3.Connection | None = None,
) -> int:
    """
    Rellena los indicadores de valor real/final (551/1295/600) para los
    últimos `lookback_days` días. Se puede llamar cada vez sin problema:
    los valores reales ya están cerrados, no cambian.
    """
    own_conn = conn is None
    conn = conn or get_connection()

    real_ids = list(FORECAST_TO_REAL.values())
    now = pd.Timestamp.now(tz=TZ).floor("h")
    start = now - pd.Timedelta(days=lookback_days)

    # AJUSTAR: mismo comentario que en collect_forecast_snapshot sobre la tz
    # de start_date/end_date.
    rango = {
        "start_date": start.tz_convert("UTC"),
        "end_date": now.tz_convert("UTC"),
    }
    df, error = fetch_multiple_indicators( real_ids, rango )
    if (error is not None) or (df is None):
        raise ValueError(f"fetch_multiple_indicators devolvió errores {error} para {real_ids} en rango {rango}")


    if df.empty:
        raise ValueError(f"fetch_multiple_indicators no devolvió datos para {real_ids}")

    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "datetime"})  # la primera columna tras reset_index() es siempre el antiguo índicedf = df.reset_index()
    print("Fetch real values", df.head())

    df = _wide_to_long(df, real_ids)

    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df["datetime"] = df["datetime"].dt.tz_convert(TZ)
    df["datetime"] = _strip_tz(df["datetime"])
    df = df.dropna(subset=["value"])

    rows = [
        (int(ind), str(dt), float(v))
        for ind, dt, v in df[["indicator_id", "datetime", "value"]].to_records(index=False)
    ]

    conn.executemany(
        """
        INSERT INTO real_values (indicator_id, datetime, value)
        VALUES (?, ?, ?)
        ON CONFLICT (indicator_id, datetime)
        DO UPDATE SET value = excluded.value
        """,
        rows,
    )
    conn.commit()

    if own_conn:
        conn.close()

    return len(rows)


# --------------------------------------------------------------------------
# Runner: patrón de tareas con try/except individual + resumen final
# --------------------------------------------------------------------------

def _run_tasks(tasks, conn):
    results = []
    for name, fn in tasks:
        t0 = time.time()
        try:
            n = fn(conn=conn)
            elapsed = time.time() - t0
            results.append((name, True, n, elapsed, None))
            print(f"[OK]   {name}: {n} filas ({elapsed:.1f}s)")
        except Exception as e:  # noqa: BLE001 - queremos capturar cualquier fallo y seguir
            elapsed = time.time() - t0
            results.append((name, False, 0, elapsed, str(e)))
            print(f"[FAIL] {name}: {e} ({elapsed:.1f}s)")
    return results


def main() -> int:


    conn = get_connection()

    tasks = [
        ("Snapshot previsiones (541/542/603)", lambda conn: collect_forecast_snapshot(conn=conn)),
        ("Backfill valores reales (551/1295/600)", lambda conn: backfill_real_values(conn=conn)),
    ]

    results = _run_tasks(tasks, conn)
    conn.close()

    failed = [r for r in results if not r[1]]
    if failed:
        print(f"\n{len(failed)} tarea(s) fallaron:")
        for name, _, _, _, err in failed:
            print(f"  - {name}: {err}")
        return 1

    print("\nTodas las tareas OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
