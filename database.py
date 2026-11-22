# -*- coding: utf-8 -*-
"""Almacenamiento SQLite: circuitos, equipos, análisis y recomendaciones.

Sigue el DER del documento del proyecto (Circuito, Equipo, Analisis,
Recomendacion). Se añadieron columnas para las condiciones de instalación
y para conservar el resultado completo de cada análisis (resultado_json).
"""
import json
import os
import sqlite3
from datetime import datetime

import configuracion as cfg

ESQUEMA = """
CREATE TABLE IF NOT EXISTS circuito (
    id_circuito INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tension REAL NOT NULL,
    tipo_alimentacion TEXT NOT NULL,
    fecha TEXT NOT NULL,
    material TEXT,
    aislamiento_c INTEGER,
    temp_ambiente_c REAL,
    conductores_portadores INTEGER,
    temp_bornes_c INTEGER,
    longitud_m REAL,
    breaker_existente_a REAL
);
CREATE TABLE IF NOT EXISTS equipo (
    id_equipo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_circuito INTEGER NOT NULL REFERENCES circuito(id_circuito) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    potencia_w REAL NOT NULL,
    cantidad INTEGER NOT NULL,
    tension REAL NOT NULL,
    factor_potencia REAL,
    tipo_carga TEXT NOT NULL DEFAULT 'C'
);
CREATE TABLE IF NOT EXISTS analisis (
    id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
    id_circuito INTEGER NOT NULL REFERENCES circuito(id_circuito) ON DELETE CASCADE,
    fecha TEXT NOT NULL,
    potencia_total REAL NOT NULL,
    corriente_estimada REAL NOT NULL,
    observaciones TEXT,
    resultado_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recomendacion (
    id_recomendacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_analisis INTEGER NOT NULL REFERENCES analisis(id_analisis) ON DELETE CASCADE,
    conductor_sugerido TEXT,
    breaker_sugerido REAL,
    advertencias TEXT
);
"""

CAMPOS_CONDICIONES = ["material", "aislamiento_c", "temp_ambiente_c",
                      "conductores_portadores", "temp_bornes_c", "longitud_m",
                      "breaker_existente_a"]


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def conectar(ruta=None):
    """Abre (y crea si no existe) la base de datos."""
    ruta = ruta or cfg.RUTA_BD
    if ruta != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


# ---------------------------------------------------------------- circuitos
def crear_circuito(con, datos):
    campos = ["nombre", "tension", "tipo_alimentacion"] + CAMPOS_CONDICIONES
    with con:
        cur = con.execute(
            f"INSERT INTO circuito ({', '.join(campos)}, fecha) "
            f"VALUES ({', '.join('?' * len(campos))}, ?)",
            [datos.get(c) for c in campos] + [_ahora()])
    return cur.lastrowid


def actualizar_condiciones(con, id_circuito, datos):
    sets = ", ".join(f"{c} = ?" for c in CAMPOS_CONDICIONES)
    with con:
        con.execute(f"UPDATE circuito SET {sets} WHERE id_circuito = ?",
                    [datos.get(c) for c in CAMPOS_CONDICIONES] + [id_circuito])


def obtener_circuito(con, id_circuito):
    fila = con.execute("SELECT * FROM circuito WHERE id_circuito = ?",
                       (id_circuito,)).fetchone()
    return dict(fila) if fila else None


def listar_circuitos(con):
    return [dict(f) for f in con.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM equipo e "
        "WHERE e.id_circuito = c.id_circuito) AS n_equipos "
        "FROM circuito c ORDER BY c.id_circuito")]


def eliminar_circuito(con, id_circuito):
    with con:
        con.execute("DELETE FROM circuito WHERE id_circuito = ?", (id_circuito,))


# ------------------------------------------------------------------ equipos
def agregar_equipo(con, id_circuito, e):
    with con:
        cur = con.execute(
            "INSERT INTO equipo (id_circuito, nombre, potencia_w, cantidad, "
            "tension, factor_potencia, tipo_carga) VALUES (?,?,?,?,?,?,?)",
            (id_circuito, e["nombre"], e["potencia_w"], e["cantidad"],
             e["tension"], e.get("factor_potencia"), e["tipo_carga"]))
    return cur.lastrowid


def listar_equipos(con, id_circuito):
    return [dict(f) for f in con.execute(
        "SELECT * FROM equipo WHERE id_circuito = ? ORDER BY id_equipo",
        (id_circuito,))]


def eliminar_equipo(con, id_equipo, id_circuito):
    with con:
        cur = con.execute(
            "DELETE FROM equipo WHERE id_equipo = ? AND id_circuito = ?",
            (id_equipo, id_circuito))
    return cur.rowcount > 0


# ----------------------------------------------------------------- análisis
def guardar_analisis(con, id_circuito, calculo, recomendacion, snapshot):
    """Guarda análisis + recomendación en una sola transacción."""
    obs = " | ".join(recomendacion["supuestos"] + recomendacion["faltantes"])
    resultado = {"circuito": snapshot["circuito"], "equipos": snapshot["equipos"],
                 "calculo": calculo, "recomendacion": recomendacion}
    with con:
        cur = con.execute(
            "INSERT INTO analisis (id_circuito, fecha, potencia_total, "
            "corriente_estimada, observaciones, resultado_json) "
            "VALUES (?,?,?,?,?,?)",
            (id_circuito, _ahora(), calculo["potencia_total_w"],
             calculo["corriente_total_a"], obs,
             json.dumps(resultado, ensure_ascii=False)))
        id_an = cur.lastrowid
        con.execute(
            "INSERT INTO recomendacion (id_analisis, conductor_sugerido, "
            "breaker_sugerido, advertencias) VALUES (?,?,?,?)",
            (id_an, recomendacion["conductor"], recomendacion["breaker_a"],
             json.dumps(recomendacion["advertencias"], ensure_ascii=False)))
    return id_an


def listar_analisis(con, id_circuito=None):
    sql = ("SELECT a.id_analisis, a.id_circuito, c.nombre, a.fecha, "
           "a.potencia_total, a.corriente_estimada, r.conductor_sugerido, "
           "r.breaker_sugerido FROM analisis a "
           "JOIN circuito c ON c.id_circuito = a.id_circuito "
           "LEFT JOIN recomendacion r ON r.id_analisis = a.id_analisis")
    args = ()
    if id_circuito is not None:
        sql += " WHERE a.id_circuito = ?"
        args = (id_circuito,)
    return [dict(f) for f in con.execute(sql + " ORDER BY a.id_analisis", args)]


def obtener_analisis(con, id_analisis):
    fila = con.execute("SELECT fecha, resultado_json FROM analisis "
                       "WHERE id_analisis = ?", (id_analisis,)).fetchone()
    if not fila:
        return None
    datos = json.loads(fila["resultado_json"])
    datos["fecha"] = fila["fecha"]
    return datos


# ------------------------------------------------------------------ ejemplos
def cargar_datos_ejemplo(con):
    """Crea tres circuitos de demostración: normal, sobrecarga e incompleto."""
    def eq(n, p, c, v, fp, t):
        return {"nombre": n, "potencia_w": p, "cantidad": c, "tension": v,
                "factor_potencia": fp, "tipo_carga": t}

    ejemplos = [
        ({"nombre": "Ejemplo 1 - Sala (caso normal)", "tension": 120,
          "tipo_alimentacion": "monofasico", "material": "cobre",
          "aislamiento_c": 90, "temp_ambiente_c": 30, "conductores_portadores": 2,
          "temp_bornes_c": 75, "longitud_m": 15, "breaker_existente_a": 20},
         [eq("Televisor", 120, 1, 120, 0.9, "N"),
          eq("Lámpara LED", 10, 8, 120, 0.9, "C"),
          eq("Computador", 200, 1, 120, 0.9, "N"),
          eq("Ventilador", 75, 2, 120, 0.85, "N")]),
        ({"nombre": "Ejemplo 2 - Cocina (sobrecarga)", "tension": 120,
          "tipo_alimentacion": "monofasico", "material": "cobre",
          "aislamiento_c": 90, "temp_ambiente_c": 35, "conductores_portadores": 2,
          "temp_bornes_c": 75, "longitud_m": 12, "breaker_existente_a": 20},
         [eq("Calentador de agua", 1800, 1, 120, 1.0, "C"),
          eq("Plancha", 1200, 1, 120, 1.0, "N"),
          eq("Horno eléctrico", 1500, 1, 120, 1.0, "N")]),
        ({"nombre": "Ejemplo 3 - Bodega (datos insuficientes)", "tension": 208,
          "tipo_alimentacion": "trifasico"},
         [eq("Bomba de agua", 3000, 1, 208, None, "M"),
          eq("Iluminación", 400, 1, 208, None, "C")]),
    ]
    ids = []
    for circuito, equipos in ejemplos:
        id_c = crear_circuito(con, circuito)
        for e in equipos:
            agregar_equipo(con, id_c, e)
        ids.append(id_c)
    return ids
