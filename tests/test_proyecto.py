# -*- coding: utf-8 -*-
"""Pruebas: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calculos as cal            # noqa: E402
import database as db             # noqa: E402
import recomendaciones as rec     # noqa: E402
import validaciones as val        # noqa: E402


def circuito(**kw):
    base = {"nombre": "T", "tension": 120, "tipo_alimentacion": "monofasico",
            "material": "cobre", "aislamiento_c": 90, "temp_ambiente_c": 30,
            "conductores_portadores": 2, "temp_bornes_c": 75,
            "longitud_m": 10, "breaker_existente_a": None}
    base.update(kw)
    return base


def equipo(nombre="E", p=1000, n=1, v=120, fp=1.0, t="N"):
    return {"nombre": nombre, "potencia_w": p, "cantidad": n, "tension": v,
            "factor_potencia": fp, "tipo_carga": t}


def evaluar(c, eqs):
    calculo = cal.analizar_corrientes(c, eqs)
    return calculo, rec.evaluar(c, eqs, calculo)


class TestCalculos(unittest.TestCase):
    def test_potencia_total(self):
        self.assertEqual(cal.potencia_total([equipo(p=100, n=3), equipo(p=50, n=2)]), 400)

    def test_corriente_monofasica(self):
        r = cal.analizar_corrientes(circuito(), [equipo(p=1200, fp=0.8)])
        self.assertAlmostEqual(r["corriente_total_a"], 12.5)   # 1200/(120*0.8)

    def test_corriente_trifasica(self):
        c = circuito(tension=208, tipo_alimentacion="trifasico")
        r = cal.analizar_corrientes(c, [equipo(p=10000, v=208, fp=1.0)])
        self.assertAlmostEqual(r["corriente_total_a"], 10000 / (3 ** 0.5 * 208), places=4)

    def test_sin_factor_de_potencia_se_registra(self):
        r = cal.analizar_corrientes(circuito(), [equipo(nombre="X", fp=None)])
        self.assertEqual(r["equipos_sin_fp"], ["X"])

    def test_corriente_de_diseno_continua(self):
        r = cal.analizar_corrientes(circuito(), [equipo(p=1200, t="C")])
        self.assertAlmostEqual(r["corriente_diseno_a"], 10 * 1.25)

    def test_factores(self):
        self.assertEqual(cal.factor_temperatura(30, 90), 1.0)
        self.assertEqual(cal.factor_temperatura(38, 75), 0.88)
        self.assertIsNone(cal.factor_temperatura(65, 60))
        self.assertEqual(cal.factor_agrupamiento(3), 1.0)
        self.assertEqual(cal.factor_agrupamiento(5), 0.8)
        self.assertEqual(cal.factor_agrupamiento(12), 0.5)

    def test_breaker_normalizado(self):
        self.assertEqual(cal.breaker_normalizado(16), 20)
        self.assertEqual(cal.breaker_normalizado(20), 20)
        self.assertIsNone(cal.breaker_normalizado(601))

    def test_caida_tension(self):
        # 12 AWG Cu, 20 A, 15 m, 120 V: R = 0.020968/3.31 ohm/m
        pct = cal.caida_tension_pct(20, 15, "12", "cobre", "monofasico", 120)
        self.assertAlmostEqual(pct, 100 * 2 * 20 * (0.020968 / 3.31) * 15 / 120, places=2)


class TestRecomendaciones(unittest.TestCase):
    def test_caso_normal_15a_da_14awg_o_12awg_y_breaker_20(self):
        c = circuito(longitud_m=5)
        calculo, r = evaluar(c, [equipo(p=1800, fp=1.0)])   # 15 A no continua
        self.assertEqual(r["estado"], "COMPLETA")
        self.assertEqual(r["breaker_a"], 15)
        self.assertEqual(r["calibre"], "14")

    def test_el_conductor_siempre_soporta_el_breaker(self):
        for p in (500, 1800, 2500, 4500, 9000):
            c = circuito(longitud_m=10)
            _, r = evaluar(c, [equipo(p=p, v=120)])
            if r["breaker_a"]:
                self.assertGreaterEqual(r["detalle"]["ampacidad_corregida_a"], r["breaker_a"])

    def test_carga_continua_usa_125(self):
        _, r = evaluar(circuito(longitud_m=5), [equipo(p=2400, t="C")])  # 20 A -> 25 A
        self.assertEqual(r["breaker_a"], 25)

    def test_sobrecarga_con_breaker_existente(self):
        c = circuito(breaker_existente_a=20)
        _, r = evaluar(c, [equipo(p=4500)])
        self.assertTrue(any("SOBRECARGA" in a for a in r["advertencias"]))

    def test_datos_insuficientes_no_emite_recomendacion(self):
        c = circuito(material=None, aislamiento_c=None)
        _, r = evaluar(c, [equipo()])
        self.assertEqual(r["estado"], "NO EMITIDA")
        self.assertIsNone(r["conductor"])
        self.assertIsNone(r["breaker_a"])
        self.assertTrue(r["faltantes"])

    def test_sin_longitud_es_parcial(self):
        _, r = evaluar(circuito(longitud_m=None), [equipo()])
        self.assertEqual(r["estado"], "PARCIAL")
        self.assertIsNotNone(r["conductor"])

    def test_sin_factor_de_potencia_es_parcial(self):
        _, r = evaluar(circuito(), [equipo(fp=None)])
        self.assertEqual(r["estado"], "PARCIAL")

    def test_caida_de_tension_aumenta_calibre(self):
        corto = evaluar(circuito(longitud_m=3), [equipo(p=1800)])[1]
        largo = evaluar(circuito(longitud_m=60), [equipo(p=1800)])[1]
        self.assertEqual(corto["calibre"], "14")
        self.assertNotEqual(largo["calibre"], "14")
        self.assertLessEqual(largo["detalle"]["caida_tension_pct"], 3.0)

    def test_temperatura_alta_aumenta_calibre(self):
        # 27.5 A: a 30 C basta 10 AWG (40 A, 90 C); a 55 C el factor 0.76 exige más
        frio = evaluar(circuito(longitud_m=5), [equipo(p=3300)])[1]
        calido = evaluar(circuito(longitud_m=5, temp_ambiente_c=55), [equipo(p=3300)])[1]
        orden = list(__import__("configuracion").AMPACIDAD["cobre"])
        self.assertGreaterEqual(orden.index(calido["calibre"]), orden.index(frio["calibre"]))
        self.assertEqual(calido["detalle"]["factor_temperatura"], 0.76)

    def test_carga_excesiva_no_emite(self):
        _, r = evaluar(circuito(), [equipo(p=200000)])
        self.assertEqual(r["estado"], "NO EMITIDA")

    def test_motor_genera_advertencia(self):
        _, r = evaluar(circuito(), [equipo(t="M", p=750)])
        self.assertTrue(any("motor" in a.lower() for a in r["advertencias"]))


class TestValidaciones(unittest.TestCase):
    def test_numero(self):
        self.assertEqual(val.validar_numero("0,85")[0], 0.85)
        self.assertIsNotNone(val.validar_numero("abc")[1])
        self.assertIsNotNone(val.validar_numero("-5", minimo=0)[1])
        self.assertIsNotNone(val.validar_numero("nan")[1])
        self.assertIsNotNone(val.validar_numero("1.5", entero=True)[1])

    def test_equipo_invalido(self):
        self.assertTrue(val.validar_equipo(equipo(p=0)))
        self.assertTrue(val.validar_equipo(equipo(fp=1.5)))
        self.assertFalse(val.validar_equipo(equipo()))

    def test_tension_incompatible_es_error(self):
        errores, _ = val.validar_para_calculo(circuito(), [equipo(v=240)])
        self.assertTrue(errores)

    def test_circuito_sin_equipos(self):
        errores, _ = val.validar_para_calculo(circuito(), [])
        self.assertTrue(errores)


class TestBaseDeDatos(unittest.TestCase):
    def setUp(self):
        self.con = db.conectar(":memory:")

    def test_ciclo_completo(self):
        id_c = db.crear_circuito(self.con, circuito(nombre="Prueba"))
        db.agregar_equipo(self.con, id_c, equipo())
        c = db.obtener_circuito(self.con, id_c)
        eqs = db.listar_equipos(self.con, id_c)
        calculo, r = evaluar(c, eqs)
        id_an = db.guardar_analisis(self.con, id_c, calculo, r,
                                    {"circuito": c, "equipos": eqs})
        self.assertEqual(len(db.listar_analisis(self.con)), 1)
        self.assertEqual(db.obtener_analisis(self.con, id_an)["recomendacion"]["estado"],
                         r["estado"])

    def test_eliminar_circuito_borra_en_cascada(self):
        id_c = db.crear_circuito(self.con, circuito())
        db.agregar_equipo(self.con, id_c, equipo())
        db.eliminar_circuito(self.con, id_c)
        self.assertEqual(db.listar_equipos(self.con, id_c), [])

    def test_ejemplos(self):
        ids = db.cargar_datos_ejemplo(self.con)
        self.assertEqual(len(ids), 3)
        estados = []
        for i in ids:
            c = db.obtener_circuito(self.con, i)
            eqs = db.listar_equipos(self.con, i)
            self.assertFalse(val.validar_para_calculo(c, eqs)[0])
            estados.append(evaluar(c, eqs)[1]["estado"])
        self.assertEqual(estados[2], "NO EMITIDA")


if __name__ == "__main__":
    unittest.main()
