# -*- coding: utf-8 -*-
"""Cálculo de potencia, corriente, factores de corrección y caída de tensión.

Fórmulas (documentadas para que sean verificables, RNF-03):

  Potencia total:        Pt = sum(Pi * ni)
  Monofásico:            I = P / (V * FP)
  Trifásico equilibrado: I = P / (raiz(3) * V_linea * FP)
  Corriente de diseño:   Id = 1.25 * I_continua + I_no_continua
                              + 0.25 * I_motor_mayor
  Caída de tensión (resistiva):
      monofásico: dV = 2 * I * R * L        trifásico: dV = raiz(3) * I * R * L
      con R = rho(75 C) / sección  [ohm/m] y L = longitud de ida [m]
"""
import math

import configuracion as cfg

RAIZ3 = math.sqrt(3)


def divisor_tension(tipo, tension):
    """Tensión efectiva del denominador: V (mono) o raiz(3)*V (trifásico)."""
    return tension if tipo == "monofasico" else RAIZ3 * tension


def potencia_total(equipos):
    """Pt = sum(Pi * ni) en watts."""
    return sum(e["potencia_w"] * e["cantidad"] for e in equipos)


def analizar_corrientes(circuito, equipos):
    """Estima potencia, corriente total y corriente de diseño.

    Si un equipo no tiene factor de potencia se usa 1.0 y se deja registrado
    en 'equipos_sin_fp': la corriente real podría ser mayor.
    """
    denom = divisor_tension(circuito["tipo_alimentacion"], circuito["tension"])
    p_tot = s_tot = i_cont = i_no_cont = i_motor_mayor = 0.0
    sin_fp = []
    for e in equipos:
        p = e["potencia_w"] * e["cantidad"]
        fp = e.get("factor_potencia")
        if not fp:
            sin_fp.append(e["nombre"])
            fp = 1.0
        s = p / fp
        i = s / denom
        p_tot += p
        s_tot += s
        if e["tipo_carga"] == "C":
            i_cont += i
        else:
            i_no_cont += i
        if e["tipo_carga"] == "M":
            i_motor_mayor = max(i_motor_mayor, i / e["cantidad"])
    i_total = i_cont + i_no_cont
    i_diseno = (cfg.FACTOR_CARGA_CONTINUA * i_cont + i_no_cont
                + cfg.FACTOR_MOTOR_MAYOR * i_motor_mayor)
    return {
        "potencia_total_w": p_tot,
        "potencia_aparente_va": s_tot,
        "factor_potencia_equivalente": (p_tot / s_tot) if s_tot else None,
        "corriente_total_a": i_total,
        "corriente_continua_a": i_cont,
        "corriente_no_continua_a": i_no_cont,
        "corriente_motor_mayor_a": i_motor_mayor,
        "corriente_diseno_a": i_diseno,
        "equipos_sin_fp": sin_fp,
    }


def factor_temperatura(temp_c, aislamiento_c):
    """Factor por temperatura ambiente; None si está fuera de tabla."""
    col = cfg.COL[aislamiento_c]
    for fila in cfg.FACTORES_TEMPERATURA:
        if temp_c <= fila[0]:
            return fila[1 + col]
    return None


def factor_agrupamiento(n_conductores):
    """Factor por más de 3 conductores portadores en la misma canalización."""
    for limite, factor in cfg.FACTORES_AGRUPAMIENTO:
        if n_conductores <= limite:
            return factor


def breaker_normalizado(corriente):
    """Menor breaker normalizado >= corriente; None si supera el máximo."""
    for b in cfg.BREAKERS_ESTANDAR:
        if b >= corriente - 1e-9:
            return b
    return None


def resistencia_ohm_m(material, calibre):
    """Resistencia en ohm/m a la temperatura de operación de referencia."""
    rho = cfg.RESISTIVIDAD_20C[material] * (
        1 + cfg.COEF_TEMPERATURA[material] * (cfg.TEMP_RESISTENCIA_C - 20))
    return rho / cfg.AREA_MM2[calibre]


def caida_tension_pct(corriente, longitud_m, calibre, material, tipo, tension):
    """Caída de tensión porcentual (solo resistiva; ignora reactancia)."""
    r = resistencia_ohm_m(material, calibre)
    k = 2 if tipo == "monofasico" else RAIZ3
    return 100.0 * k * corriente * r * longitud_m / tension
