# -*- coding: utf-8 -*-
"""Validación de datos obligatorios, rangos y formatos (RF-06, RNF-04)."""
import math

import configuracion as cfg


def validar_nombre(texto, max_len=60):
    """Devuelve (valor, error)."""
    t = (texto or "").strip()
    if not t:
        return None, "El nombre no puede estar vacío."
    if len(t) > max_len:
        return None, f"El nombre no puede superar {max_len} caracteres."
    return t, None


def validar_numero(texto, minimo=None, maximo=None, entero=False,
                   exclusivo_min=False):
    """Convierte texto a número (acepta coma decimal). Devuelve (valor, error)."""
    t = (texto or "").strip().replace(",", ".")
    if not t:
        return None, "Debe ingresar un valor."
    try:
        valor = float(t)
    except ValueError:
        return None, "Ingrese un número válido (ejemplo: 1500 o 0.85)."
    if math.isnan(valor) or math.isinf(valor):
        return None, "Ingrese un número válido."
    if entero:
        if valor != int(valor):
            return None, "Debe ser un número entero."
        valor = int(valor)
    if minimo is not None:
        if valor < minimo or (exclusivo_min and valor == minimo):
            signo = ">" if exclusivo_min else ">="
            return None, f"El valor debe ser {signo} {minimo}."
    if maximo is not None and valor > maximo:
        return None, f"El valor debe ser <= {maximo}."
    return valor, None


def validar_equipo(e):
    """Devuelve lista de errores de un equipo (dict)."""
    errores = []
    _, err = validar_nombre(e.get("nombre"))
    if err:
        errores.append(f"Equipo: {err}")
    nombre = e.get("nombre") or "(sin nombre)"
    p = e.get("potencia_w")
    if not isinstance(p, (int, float)) or p <= 0:
        errores.append(f"{nombre}: la potencia debe ser mayor que 0 W.")
    n = e.get("cantidad")
    if not isinstance(n, int) or n < 1:
        errores.append(f"{nombre}: la cantidad debe ser un entero >= 1.")
    t = e.get("tension")
    if not isinstance(t, (int, float)) or t <= 0:
        errores.append(f"{nombre}: la tensión debe ser mayor que 0 V.")
    fp = e.get("factor_potencia")
    if fp is not None and not (0 < fp <= 1):
        errores.append(f"{nombre}: el factor de potencia debe estar en (0, 1].")
    if e.get("tipo_carga") not in cfg.TIPOS_CARGA:
        errores.append(f"{nombre}: tipo de carga inválido.")
    return errores


def validar_circuito(c):
    """Devuelve lista de errores de los datos de un circuito (dict)."""
    errores = []
    _, err = validar_nombre(c.get("nombre"))
    if err:
        errores.append(f"Circuito: {err}")
    v = c.get("tension")
    if not isinstance(v, (int, float)) or not (
            cfg.TENSION_MIN_V <= v <= cfg.TENSION_MAX_V):
        errores.append(f"La tensión debe estar entre {cfg.TENSION_MIN_V} y "
                       f"{cfg.TENSION_MAX_V} V.")
    tipo = c.get("tipo_alimentacion")
    if tipo not in cfg.CONDUCTORES_MINIMOS:
        errores.append("Tipo de alimentación inválido.")
    if c.get("material") not in (None, "cobre", "aluminio"):
        errores.append("Material de conductor inválido.")
    if c.get("aislamiento_c") not in (None, 60, 75, 90):
        errores.append("El aislamiento debe ser 60, 75 o 90 C.")
    if c.get("temp_bornes_c") not in (None, 60, 75):
        errores.append("La temperatura de bornes debe ser 60 o 75 C.")
    n = c.get("conductores_portadores")
    if n is not None and tipo in cfg.CONDUCTORES_MINIMOS \
            and n < cfg.CONDUCTORES_MINIMOS[tipo]:
        errores.append("Los conductores portadores no pueden ser menos que "
                       f"los del propio circuito ({cfg.CONDUCTORES_MINIMOS[tipo]}).")
    for campo, etiqueta in (("longitud_m", "La longitud"),
                            ("breaker_existente_a", "El breaker existente")):
        x = c.get(campo)
        if x is not None and x <= 0:
            errores.append(f"{etiqueta} debe ser mayor que 0.")
    return errores


def validar_para_calculo(circuito, equipos):
    """Devuelve (errores, advertencias). Con errores no se debe calcular."""
    errores = validar_circuito(circuito)
    advertencias = []
    if not equipos:
        errores.append("El circuito no tiene equipos registrados.")
    v = circuito.get("tension") or 0
    for e in equipos:
        errores.extend(validar_equipo(e))
        te = e.get("tension")
        if v and isinstance(te, (int, float)) and te > 0 and te != v:
            if abs(te - v) / v > cfg.TOLERANCIA_TENSION_EQUIPO:
                errores.append(
                    f"{e['nombre']}: tensión {te:g} V incompatible con el "
                    f"circuito de {v:g} V.")
            else:
                advertencias.append(
                    f"{e['nombre']}: tensión {te:g} V difiere de la del "
                    f"circuito ({v:g} V); verifique.")
    return errores, advertencias
