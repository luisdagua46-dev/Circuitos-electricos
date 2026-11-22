# -*- coding: utf-8 -*-
"""Evaluación técnica: compara con las tablas de configuracion.py y genera
una sugerencia preliminar de conductor y breaker junto con advertencias.

Regla central (documento del proyecto): si faltan datos críticos NO se emite
recomendación; se informa qué falta. Nunca se deduce el calibre solo de la
potencia.

Criterios aplicados al elegir el conductor (el primero que cumple todo):
  1. Ampacidad de tabla en la columna limitada por bornes/aislamiento
     >= corriente de diseño (regla del 125 % en cargas continuas).
  2. Ampacidad corregida (temperatura y agrupamiento) >= breaker.
     (No se aproxima al siguiente valor normalizado: criterio conservador.)
  3. Breaker <= límite de conductores pequeños (14, 12, 10 AWG).
  4. Si se conoce la longitud: caída de tensión <= límite configurado.
"""
import calculos as cal
import configuracion as cfg


def etiqueta_calibre(calibre, material=None):
    unidad = "kcmil" if calibre.isdigit() and int(calibre) >= 250 else "AWG"
    txt = f"{calibre} {unidad}"
    return f"{txt} {material}" if material else txt


def _revisar_breaker_existente(circuito, calculo, adv):
    b = circuito.get("breaker_existente_a")
    if not b:
        return
    if calculo["corriente_total_a"] > b:
        adv.append(
            f"SOBRECARGA: la corriente estimada ({calculo['corriente_total_a']:.1f} A) "
            f"supera el breaker existente de {b:g} A.")
    elif calculo["corriente_diseno_a"] > b:
        adv.append(
            f"El breaker existente de {b:g} A no cumple el criterio de diseño "
            f"({calculo['corriente_diseno_a']:.1f} A, con 125 % en cargas continuas).")


def _advertencias_generales(circuito, equipos, calculo, adv, sup):
    if any(e["tipo_carga"] == "M" for e in equipos):
        adv.append("Hay motores: la corriente de arranque y el dimensionamiento "
                   "específico de motores (NTC 2050, Sección 430) NO se evalúan "
                   "aquí; solo se sumó el 25 % del motor mayor. Verifique.")
    if circuito["tipo_alimentacion"] == "trifasico":
        sup.append("Carga trifásica equilibrada entre fases y sin armónicos.")
    adv.append("No se evaluó la capacidad de interrupción (cortocircuito) ni la "
               "coordinación de protecciones.")


def evaluar(circuito, equipos, calculo):
    """Devuelve el dict de resultado de la evaluación técnica."""
    adv, faltantes, supuestos = [], [], []
    res = {"estado": "NO EMITIDA", "conductor": None, "calibre": None,
           "aislamiento_c": None, "breaker_a": None, "detalle": {},
           "advertencias": adv, "faltantes": faltantes,
           "supuestos": supuestos}

    material = circuito.get("material")
    aisl = circuito.get("aislamiento_c")
    t_amb = circuito.get("temp_ambiente_c")
    n_cond = circuito.get("conductores_portadores")
    longitud = circuito.get("longitud_m")
    tipo = circuito["tipo_alimentacion"]
    tension = circuito["tension"]

    criticos, otros = [], []
    if material is None:
        criticos.append("Material del conductor (cobre o aluminio)")
    if aisl is None:
        criticos.append("Temperatura nominal del aislamiento (60/75/90 C)")
    if t_amb is None:
        criticos.append("Temperatura ambiente")
    if n_cond is None:
        criticos.append("Cantidad de conductores portadores en la canalización")
    if calculo["equipos_sin_fp"]:
        otros.append("Factor de potencia de: " + ", ".join(calculo["equipos_sin_fp"])
                     + " (se supuso 1.0; la corriente real podría ser mayor)")
    if longitud is None:
        otros.append("Longitud del circuito (caída de tensión no verificada)")
    faltantes.extend(criticos + otros)

    _revisar_breaker_existente(circuito, calculo, adv)
    _advertencias_generales(circuito, equipos, calculo, adv, supuestos)

    if criticos:
        adv.insert(0, "No se puede emitir una recomendación confiable de "
                      "conductor y breaker: faltan datos de instalación.")
        return res

    f_temp = cal.factor_temperatura(t_amb, aisl)
    if f_temp is None:
        adv.insert(0, f"Una temperatura ambiente de {t_amb:g} C está fuera de la "
                      f"tabla para aislamiento de {aisl} C. No se emite recomendación.")
        return res
    f_agr = cal.factor_agrupamiento(n_cond)

    bornes = circuito.get("temp_bornes_c")
    if bornes is None:
        bornes = 60
        supuestos.append("Temperatura de bornes desconocida: se usó 60 C "
                         "(valor conservador).")
    temp_term = min(bornes, aisl)

    i_total = calculo["corriente_total_a"]
    i_diseno = calculo["corriente_diseno_a"]
    breaker = cal.breaker_normalizado(i_diseno)
    if breaker is None:
        adv.insert(0, f"La corriente de diseño ({i_diseno:.0f} A) supera el mayor "
                      f"breaker normalizado de la tabla ({cfg.BREAKERS_ESTANDAR[-1]} A). "
                      "Divida el circuito o consulte a un profesional.")
        return res

    cumplen = []
    for calibre, amps in cfg.AMPACIDAD[material].items():
        amp_term = amps[cfg.COL[temp_term]]
        amp_corr = amps[cfg.COL[aisl]] * f_temp * f_agr
        limite = cfg.LIMITE_PROTECCION_PEQUENO[material].get(calibre)
        if amp_term < i_diseno or amp_corr < breaker:
            continue
        if limite is not None and breaker > limite:
            continue
        cumplen.append((calibre, amps[cfg.COL[aisl]], amp_corr))
    if not cumplen:
        adv.insert(0, "Ningún conductor de la tabla (hasta 500 kcmil) cumple con "
                      "estas condiciones. Divida el circuito o consulte a un profesional.")
        return res

    elegido = cumplen[0]
    caida = None
    if longitud is not None:
        for fila in cumplen:
            caida = cal.caida_tension_pct(i_total, longitud, fila[0], material,
                                          tipo, tension)
            elegido = fila
            if caida <= cfg.CAIDA_TENSION_MAX_PCT:
                break
        else:
            adv.append(f"Con el mayor calibre disponible la caída de tensión "
                       f"({caida:.1f} %) aún supera {cfg.CAIDA_TENSION_MAX_PCT:g} %.")
        if elegido[0] != cumplen[0][0]:
            adv.append(f"Se aumentó el calibre de {etiqueta_calibre(cumplen[0][0])} a "
                       f"{etiqueta_calibre(elegido[0])} para limitar la caída de tensión.")

    calibre, amp_tabla, amp_corr = elegido
    res.update({
        "estado": "PARCIAL" if otros else "COMPLETA",
        "conductor": etiqueta_calibre(calibre, material),
        "calibre": calibre, "aislamiento_c": aisl, "breaker_a": breaker,
        "detalle": {
            "calibre_minimo_por_ampacidad": cumplen[0][0],
            "ampacidad_tabla_a": amp_tabla,
            "ampacidad_corregida_a": round(amp_corr, 1),
            "factor_temperatura": f_temp, "factor_agrupamiento": f_agr,
            "temp_bornes_usada_c": bornes,
            "caida_tension_pct": None if caida is None else round(caida, 2),
            "limite_caida_pct": cfg.CAIDA_TENSION_MAX_PCT,
        },
    })
    supuestos.append("Se aplicó 125 % a cargas continuas y la protección no se "
                     "aproximó al siguiente valor normalizado (criterio conservador).")
    if otros:
        adv.insert(0, "Recomendación PARCIAL: complete los datos pendientes para "
                      "confirmarla.")
    return res
