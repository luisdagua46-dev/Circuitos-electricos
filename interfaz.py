# -*- coding: utf-8 -*-
"""Menús, lectura de datos y presentación de resultados (consola)."""
import calculos as cal
import configuracion as cfg
import database as db
import recomendaciones as rec
import validaciones as val

ANCHO = 66


class Cancelar(Exception):
    """El usuario escribió 'cancelar' durante un formulario."""


# ------------------------------------------------------------------ lectura
def leer(prompt, permitir_cancelar=True):
    texto = input(prompt).strip()
    if permitir_cancelar and texto.lower() == "cancelar":
        raise Cancelar()
    return texto


def pedir_texto(prompt):
    while True:
        valor, err = val.validar_nombre(leer(prompt))
        if err:
            print("  ! " + err)
        else:
            return valor


def pedir_numero(prompt, minimo=None, maximo=None, entero=False,
                 exclusivo_min=False, opcional=False, actual=None):
    """Con opcional=True: Enter conserva 'actual' (None = pendiente) y '-' borra."""
    while True:
        t = leer(prompt)
        if opcional:
            if t == "":
                return actual
            if t == "-":
                return None
        valor, err = val.validar_numero(t, minimo, maximo, entero, exclusivo_min)
        if err:
            print("  ! " + err)
        else:
            return valor


def pedir_opcion(titulo, opciones, opcional=False, actual=None):
    """Devuelve la clave elegida. Con opcional=True Enter conserva 'actual'."""
    print(titulo)
    for k, v in opciones.items():
        print(f"   {k}) {v}")
    while True:
        t = leer("  Opción" + (" (Enter = pendiente/sin cambio, - = borrar)" if opcional else "") + ": ")
        if opcional:
            if t == "":
                return actual
            if t == "-":
                return None
        if t in opciones:
            return t
        print("  ! Opción no válida.")


def titulo(texto):
    print("\n" + "=" * ANCHO)
    print(f" {texto}")
    print("=" * ANCHO)


# --------------------------------------------------------------- formularios
def pedir_condiciones(actual=None):
    """Condiciones de instalación. Los datos desconocidos quedan pendientes."""
    actual = actual or {}
    print("\nCondiciones de instalación. Si no conoce un dato NO lo invente: "
          "pulse Enter y quedará pendiente.")
    r = {}
    k = pedir_opcion("\nMaterial del conductor:", cfg.MATERIALES, True,
                     {"cobre": "1", "aluminio": "2"}.get(actual.get("material")))
    r["material"] = cfg.MATERIALES[k] if k else None
    k = pedir_opcion("\nTemperatura nominal del aislamiento:", cfg.AISLAMIENTOS, True,
                     str(actual["aislamiento_c"]) if actual.get("aislamiento_c") else None)
    r["aislamiento_c"] = int(k) if k else None
    r["temp_ambiente_c"] = pedir_numero(
        "\nTemperatura ambiente en C (0-80) [Enter = pendiente]: ", 0, 80,
        opcional=True, actual=actual.get("temp_ambiente_c"))
    r["conductores_portadores"] = pedir_numero(
        "Conductores portadores de corriente en la misma canalización\n"
        "(incluya los de otros circuitos; mínimo 2 mono / 3 trifásico) [Enter = pendiente]: ",
        2, 100, entero=True, opcional=True, actual=actual.get("conductores_portadores"))
    k = pedir_opcion("\nTemperatura nominal de los bornes del breaker/equipo:",
                     cfg.TEMPERATURAS_BORNES, True,
                     str(actual["temp_bornes_c"]) if actual.get("temp_bornes_c") else None)
    r["temp_bornes_c"] = int(k) if k else None
    r["longitud_m"] = pedir_numero(
        "\nLongitud del circuito, solo ida, en metros [Enter = pendiente]: ",
        0, 5000, exclusivo_min=True, opcional=True, actual=actual.get("longitud_m"))
    r["breaker_existente_a"] = pedir_numero(
        "Breaker ya instalado en A, si existe (para detectar sobrecarga) "
        "[Enter = ninguno]: ", 0, 1000, exclusivo_min=True, opcional=True,
        actual=actual.get("breaker_existente_a"))
    return r


def crear_circuito(con):
    titulo("NUEVO CIRCUITO  (escriba 'cancelar' para abortar)")
    try:
        nombre = pedir_texto("Nombre del circuito: ")
        tension = pedir_numero(
            f"Tensión nominal en V ({cfg.TENSION_MIN_V}-{cfg.TENSION_MAX_V}; "
            "en trifásico, entre líneas): ", cfg.TENSION_MIN_V, cfg.TENSION_MAX_V)
        tipo = cfg.TIPOS_ALIMENTACION[pedir_opcion(
            "\nTipo de alimentación:", {"1": "Monofásico", "2": "Trifásico"})]
        datos = {"nombre": nombre, "tension": tension, "tipo_alimentacion": tipo}
        datos.update(pedir_condiciones())
    except Cancelar:
        print("\nOperación cancelada.")
        return None
    id_c = db.crear_circuito(con, datos)
    print(f"\n✔ Circuito #{id_c} guardado. Ahora registre sus equipos.")
    return id_c


def agregar_equipo(con, circuito):
    titulo(f"NUEVO EQUIPO en '{circuito['nombre']}'  ('cancelar' para abortar)")
    try:
        e = {"nombre": pedir_texto("Nombre del equipo: ")}
        e["potencia_w"] = pedir_numero("Potencia por unidad en W: ", 0,
                                       1_000_000, exclusivo_min=True)
        e["cantidad"] = pedir_numero("Cantidad: ", 1, 10_000, entero=True)
        e["tension"] = pedir_numero(
            f"Tensión del equipo en V [Enter = {circuito['tension']:g}]: ", 1, 1000,
            exclusivo_min=False, opcional=True, actual=circuito["tension"])
        e["factor_potencia"] = pedir_numero(
            "Factor de potencia (0-1) [Enter = desconocido]: ", 0, 1,
            exclusivo_min=True, opcional=True)
        print("\nTipo de carga:")
        for k, v in cfg.TIPOS_CARGA.items():
            print(f"   {k}) {v}")
        while True:
            t = leer("  Tipo [Enter = C, continua: supuesto conservador]: ").upper() or "C"
            if t in cfg.TIPOS_CARGA:
                e["tipo_carga"] = t
                break
            print("  ! Escriba N, C o M.")
    except Cancelar:
        print("\nOperación cancelada.")
        return
    errores = val.validar_equipo(e)
    if errores:
        print("\n".join("  ! " + x for x in errores))
        return
    db.agregar_equipo(con, circuito["id_circuito"], e)
    print("\n✔ Equipo agregado.")


# ------------------------------------------------------------- presentación
def _fmt(x, nd=1):
    return "-" if x is None else f"{x:,.{nd}f}"


def mostrar_resumen(circuito, equipos):
    titulo(f"CIRCUITO #{circuito['id_circuito']}: {circuito['nombre']}")
    print(f"Alimentación : {cfg.NOMBRE_TIPO[circuito['tipo_alimentacion']]}, "
          f"{circuito['tension']:g} V")
    pend = "(pendiente)"
    print(f"Material     : {circuito.get('material') or pend}")
    print(f"Aislamiento  : {str(circuito['aislamiento_c']) + ' C' if circuito.get('aislamiento_c') else pend}")
    print(f"T. ambiente  : {str(circuito['temp_ambiente_c']) + ' C' if circuito.get('temp_ambiente_c') is not None else pend}")
    print(f"Conductores  : {circuito.get('conductores_portadores') or pend}")
    print(f"Bornes       : {str(circuito['temp_bornes_c']) + ' C' if circuito.get('temp_bornes_c') else pend}")
    print(f"Longitud     : {str(circuito['longitud_m']) + ' m' if circuito.get('longitud_m') else pend}")
    print(f"Breaker inst.: {str(circuito['breaker_existente_a']) + ' A' if circuito.get('breaker_existente_a') else 'ninguno'}")
    print("\nEquipos:")
    if not equipos:
        print("  (ninguno registrado)")
        return
    print(f"  {'ID':>3}  {'Equipo':<24}{'W':>8}{'Cant':>6}{'V':>6}{'FP':>6}  Tipo")
    for e in equipos:
        fp = "-" if e["factor_potencia"] is None else f"{e['factor_potencia']:.2f}"
        print(f"  {e['id_equipo']:>3}  {e['nombre'][:23]:<24}{e['potencia_w']:>8g}"
              f"{e['cantidad']:>6}{e['tension']:>6g}{fp:>6}  {e['tipo_carga']}")
    print(f"\n  Potencia total: {_fmt(cal.potencia_total(equipos), 0)} W")


def mostrar_resultado(circuito, calculo, r, fecha=None):
    titulo(f"RESULTADO: {circuito['nombre']}" + (f"  [{fecha}]" if fecha else ""))
    print(f"Circuito: {cfg.NOMBRE_TIPO[circuito['tipo_alimentacion']]}, "
          f"{circuito['tension']:g} V\n")
    print(f"Potencia activa total      : {_fmt(calculo['potencia_total_w'], 0)} W")
    print(f"Potencia aparente          : {_fmt(calculo['potencia_aparente_va'], 0)} VA")
    fpe = calculo["factor_potencia_equivalente"]
    print(f"Factor de potencia equiv.  : {_fmt(fpe, 2)}")
    print(f"Corriente estimada         : {_fmt(calculo['corriente_total_a'], 2)} A"
          + ("  (ESTIMACIÓN, no medición)" if calculo["equipos_sin_fp"] else ""))
    print(f"Corriente de diseño        : {_fmt(calculo['corriente_diseno_a'], 2)} A"
          "  (125 % continuas + no continuas + 25 % motor mayor)")
    print("\n" + "-" * ANCHO)
    print(f" RECOMENDACIÓN PRELIMINAR - estado: {r['estado']}")
    print("-" * ANCHO)
    if r["conductor"]:
        d = r["detalle"]
        print(f"Conductor sugerido : {r['conductor']}, aislamiento {r['aislamiento_c']} C")
        print(f"Breaker sugerido   : {r['breaker_a']:g} A")
        print(f"\n  Ampacidad de tabla {d['ampacidad_tabla_a']} A x factor temp "
              f"{d['factor_temperatura']} x factor agrup. {d['factor_agrupamiento']} "
              f"= {d['ampacidad_corregida_a']} A")
        print(f"  Bornes considerados: {d['temp_bornes_usada_c']} C")
        if d["caida_tension_pct"] is not None:
            print(f"  Caída de tensión   : {d['caida_tension_pct']} % "
                  f"(límite de referencia {d['limite_caida_pct']:g} %)")
    else:
        print("No se emite conductor ni breaker.")
    for titulo_bloque, items in (("Datos faltantes o por verificar", r["faltantes"]),
                                 ("Supuestos", r["supuestos"]),
                                 ("Advertencias", r["advertencias"])):
        if items:
            print(f"\n{titulo_bloque}:")
            for x in items:
                print(f"  - {x}")
    print(f"\nFuente de tablas: {cfg.FUENTE_TABLAS}")
    print(f"\n*** {cfg.AVISO_LEGAL}")


# ------------------------------------------------------------------ acciones
def ejecutar_analisis(con, id_circuito):
    circuito = db.obtener_circuito(con, id_circuito)
    equipos = db.listar_equipos(con, id_circuito)
    errores, avisos = val.validar_para_calculo(circuito, equipos)
    if errores:
        print("\nNo se puede calcular todavía:")
        print("\n".join("  ! " + e for e in errores))
        return
    for a in avisos:
        print("  Aviso: " + a)
    calculo = cal.analizar_corrientes(circuito, equipos)
    r = rec.evaluar(circuito, equipos, calculo)
    mostrar_resultado(circuito, calculo, r)
    if leer("\n¿Guardar este análisis? (s/n): ", False).lower() == "s":
        id_an = db.guardar_analisis(con, id_circuito, calculo, r,
                                    {"circuito": circuito, "equipos": equipos})
        print(f"✔ Análisis #{id_an} guardado.")


def listar_circuitos(con):
    circuitos = db.listar_circuitos(con)
    titulo("CIRCUITOS GUARDADOS")
    if not circuitos:
        print("No hay circuitos. Cree uno o cargue los ejemplos.")
        return circuitos
    print(f"{'ID':>3}  {'Nombre':<42}{'V':>6}  {'Tipo':<10}{'Equipos':>8}")
    for c in circuitos:
        print(f"{c['id_circuito']:>3}  {c['nombre'][:41]:<42}{c['tension']:>6g}  "
              f"{cfg.NOMBRE_TIPO[c['tipo_alimentacion']]:<10}{c['n_equipos']:>8}")
    return circuitos


def consultar_analisis(con):
    filas = db.listar_analisis(con)
    titulo("ANÁLISIS GUARDADOS")
    if not filas:
        print("Aún no hay análisis guardados.")
        return
    print(f"{'ID':>3}  {'Circuito':<38}{'Fecha':<20}{'W':>7}{'A':>8}  Conductor / Breaker")
    for f in filas:
        sug = (f"{f['conductor_sugerido']} / {f['breaker_sugerido']:g} A"
               if f["conductor_sugerido"] else "sin recomendación")
        print(f"{f['id_analisis']:>3}  {f['nombre'][:37]:<38}{f['fecha']:<20}"
              f"{f['potencia_total']:>7.0f}{f['corriente_estimada']:>8.1f}  {sug}")
    t = leer("\nID del análisis a ver en detalle (Enter = volver): ", False)
    if t.isdigit():
        datos = db.obtener_analisis(con, int(t))
        if datos:
            mostrar_resultado(datos["circuito"], datos["calculo"],
                              datos["recomendacion"], datos["fecha"])
        else:
            print("  ! No existe ese análisis.")


def menu_circuito(con, id_circuito):
    while True:
        circuito = db.obtener_circuito(con, id_circuito)
        if circuito is None:
            return
        titulo(f"CIRCUITO #{id_circuito}: {circuito['nombre']}")
        print(" 1. Ver resumen y equipos\n 2. Agregar equipo\n 3. Eliminar equipo\n"
              " 4. Editar condiciones de instalación\n 5. Calcular y mostrar análisis\n"
              " 6. Ver análisis guardados de este circuito\n 7. Eliminar este circuito\n"
              " 0. Volver")
        op = leer("Opción: ", False)
        if op == "1":
            mostrar_resumen(circuito, db.listar_equipos(con, id_circuito))
        elif op == "2":
            agregar_equipo(con, circuito)
        elif op == "3":
            equipos = db.listar_equipos(con, id_circuito)
            mostrar_resumen(circuito, equipos)
            t = leer("ID del equipo a eliminar (Enter = cancelar): ", False)
            if t.isdigit():
                print("✔ Eliminado." if db.eliminar_equipo(con, int(t), id_circuito)
                      else "  ! No existe ese equipo en este circuito.")
        elif op == "4":
            try:
                db.actualizar_condiciones(con, id_circuito, pedir_condiciones(circuito))
                print("\n✔ Condiciones actualizadas.")
            except Cancelar:
                print("\nOperación cancelada.")
        elif op == "5":
            ejecutar_analisis(con, id_circuito)
        elif op == "6":
            filas = db.listar_analisis(con, id_circuito)
            for f in filas:
                print(f"  #{f['id_analisis']}  {f['fecha']}  {f['potencia_total']:.0f} W  "
                      f"{f['corriente_estimada']:.1f} A  {f['conductor_sugerido'] or 'sin recomendación'}")
            if not filas:
                print("  Sin análisis guardados.")
        elif op == "7":
            if leer(f"¿Eliminar '{circuito['nombre']}' y todos sus datos? (s/n): ",
                    False).lower() == "s":
                db.eliminar_circuito(con, id_circuito)
                print("✔ Circuito eliminado.")
                return
        elif op == "0":
            return
        else:
            print("  ! Opción no válida.")


def menu_principal(con):
    titulo(f"DIMENSIONAMIENTO PRELIMINAR DE CIRCUITOS ELÉCTRICOS  v{cfg.VERSION}")
    print(cfg.AVISO_LEGAL)
    while True:
        print("\n--- MENÚ PRINCIPAL ---\n 1. Crear nuevo circuito\n 2. Ver circuitos guardados\n"
              " 3. Trabajar con un circuito (equipos, cálculo)\n 4. Consultar análisis guardados\n"
              " 5. Cargar circuitos de ejemplo\n 0. Salir")
        op = leer("Opción: ", False)
        if op == "1":
            id_c = crear_circuito(con)
            if id_c:
                menu_circuito(con, id_c)
        elif op == "2":
            listar_circuitos(con)
        elif op == "3":
            if listar_circuitos(con):
                t = leer("\nID del circuito (Enter = volver): ", False)
                if t.isdigit() and db.obtener_circuito(con, int(t)):
                    menu_circuito(con, int(t))
                elif t:
                    print("  ! Circuito no encontrado.")
        elif op == "4":
            consultar_analisis(con)
        elif op == "5":
            ids = db.cargar_datos_ejemplo(con)
            print(f"✔ Se crearon los circuitos de ejemplo #{ids[0]}, #{ids[1]} y #{ids[2]}.")
        elif op == "0":
            print("\nHasta luego. Recuerde: estos resultados son preliminares.")
            return
        else:
            print("  ! Opción no válida.")
