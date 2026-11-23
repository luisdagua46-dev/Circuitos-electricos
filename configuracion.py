# -*- coding: utf-8 -*-
#Parámetros y tablas de referencia de la aplicación.

import os

VERSION = "1.0"

RUTA_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data", "dimensionamiento.db")

AVISO_LEGAL = (
    "Resultado PRELIMINAR de apoyo académico. No reemplaza el diseño, la "
    "inspección ni la certificación de una instalación por personal "
    "competente. Verifique con la NTC 2050 / RETIE vigentes, las condiciones "
    "reales de instalación y los datos del fabricante."
)

FUENTE_TABLAS = (
    "Ampacidades: NEC/NFPA 70 Tabla 310.16 (<=3 conductores portadores, 30 C). "
    "Factores de temperatura: Tabla 310.15(B)(1). Agrupamiento: 310.15(C)(1). "
    "Breakers normalizados: 240.6(A). Pendiente de verificar contra la NTC 2050 "
    "vigente."
)

# ----------------------------------------------------------------------------
# Datos del circuito
# ----------------------------------------------------------------------------
TIPOS_ALIMENTACION = {"1": "monofasico", "2": "trifasico"}
NOMBRE_TIPO = {"monofasico": "Monofásico", "trifasico": "Trifásico"}
# Conductores portadores de corriente que aporta el propio circuito
CONDUCTORES_MINIMOS = {"monofasico": 2, "trifasico": 3}

TENSION_MIN_V = 12
TENSION_MAX_V = 1000
TOLERANCIA_TENSION_EQUIPO = 0.10   # 10 %: más allá se considera incompatible

TIPOS_CARGA = {
    "N": "No continua (menos de 3 h)",
    "C": "Continua (3 h o más)",
    "M": "Motor",
}

MATERIALES = {"1": "cobre", "2": "aluminio"}
AISLAMIENTOS = {
    "60": "60 C (p. ej. TW)",
    "75": "75 C (p. ej. THW, THWN)",
    "90": "90 C (p. ej. THHN, THWN-2, XHHW-2)",
}
TEMPERATURAS_BORNES = {
    "60": "60 C (valor conservador, habitual en circuitos hasta 100 A)",
    "75": "75 C (solo si el equipo/breaker está marcado para 75 C)",
}

# ----------------------------------------------------------------------------
# Ampacidades (A) por calibre: (60 C, 75 C, 90 C)
# ----------------------------------------------------------------------------
COL = {60: 0, 75: 1, 90: 2}

AMPACIDAD = {
    "cobre": {
        "14": (15, 20, 25), "12": (20, 25, 30), "10": (30, 35, 40),
        "8": (40, 50, 55), "6": (55, 65, 75), "4": (70, 85, 95),
        "3": (85, 100, 115), "2": (95, 115, 130), "1": (110, 130, 145),
        "1/0": (125, 150, 170), "2/0": (145, 175, 195),
        "3/0": (165, 200, 225), "4/0": (195, 230, 260),
        "250": (215, 255, 290), "300": (240, 285, 320),
        "350": (260, 310, 350), "400": (280, 335, 380),
        "500": (320, 380, 430),
    },
    "aluminio": {
        "12": (15, 20, 25), "10": (25, 30, 35), "8": (30, 40, 45),
        "6": (40, 50, 55), "4": (55, 65, 75), "3": (65, 75, 85),
        "2": (75, 90, 100), "1": (85, 100, 115), "1/0": (100, 120, 135),
        "2/0": (115, 135, 150), "3/0": (130, 155, 175),
        "4/0": (150, 180, 205), "250": (170, 205, 230),
        "300": (195, 230, 260), "350": (210, 250, 280),
        "400": (225, 270, 305), "500": (260, 310, 350),
    },
}

# Sección transversal en mm2 (AWG / kcmil) para calcular la resistencia
AREA_MM2 = {
    "14": 2.08, "12": 3.31, "10": 5.26, "8": 8.37, "6": 13.30, "4": 21.15,
    "3": 26.67, "2": 33.62, "1": 42.41, "1/0": 53.49, "2/0": 67.43,
    "3/0": 85.01, "4/0": 107.2, "250": 126.7, "300": 152.0, "350": 177.3,
    "400": 202.7, "500": 253.4,
}

# Resistividad a 20 C (ohm*mm2/m) y coeficiente de temperatura (1/C)
RESISTIVIDAD_20C = {"cobre": 0.017241, "aluminio": 0.02826}
COEF_TEMPERATURA = {"cobre": 0.00393, "aluminio": 0.00403}
TEMP_RESISTENCIA_C = 75   # temperatura de operación para la caída de tensión

# ----------------------------------------------------------------------------
# Factores de corrección
# ----------------------------------------------------------------------------
# (temperatura ambiente máxima del rango en C, factor 60 C, 75 C, 90 C)
# None = no permitido para ese aislamiento. Base: 30 C.
FACTORES_TEMPERATURA = [
    (10, 1.29, 1.20, 1.15), (15, 1.22, 1.15, 1.12), (20, 1.15, 1.11, 1.08),
    (25, 1.08, 1.05, 1.04), (30, 1.00, 1.00, 1.00), (35, 0.91, 0.94, 0.96),
    (40, 0.82, 0.88, 0.91), (45, 0.71, 0.82, 0.87), (50, 0.58, 0.75, 0.82),
    (55, 0.41, 0.67, 0.76), (60, None, 0.58, 0.71), (70, None, 0.33, 0.58),
    (80, None, None, 0.41),
]

# (cantidad máxima de conductores portadores, factor)
FACTORES_AGRUPAMIENTO = [
    (3, 1.00), (6, 0.80), (9, 0.70), (20, 0.50), (30, 0.45), (40, 0.40),
    (float("inf"), 0.35),
]

# ----------------------------------------------------------------------------
# Protecciones
# ----------------------------------------------------------------------------
BREAKERS_ESTANDAR = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
                     110, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450,
                     500, 600]

# Protección máxima para conductores pequeños (NEC 240.4(D))
LIMITE_PROTECCION_PEQUENO = {
    "cobre": {"14": 15, "12": 20, "10": 30},
    "aluminio": {"12": 15, "10": 25},
}

FACTOR_CARGA_CONTINUA = 1.25
FACTOR_MOTOR_MAYOR = 0.25
CAIDA_TENSION_MAX_PCT = 3.0   # valor de referencia para circuitos ramales
