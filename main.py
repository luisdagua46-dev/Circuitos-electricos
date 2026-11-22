# -*- coding: utf-8 -*-
"""Punto de entrada. Uso:  python main.py [--bd ruta/a/base.db]"""
import argparse
import sys

import database
import interfaz


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Dimensionamiento preliminar de circuitos eléctricos")
    parser.add_argument("--bd", help="ruta de la base de datos SQLite "
                                     "(por defecto data/dimensionamiento.db)")
    args = parser.parse_args(argv)

    for flujo in (sys.stdout, sys.stdin):          # evita errores de acentos
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    con = database.conectar(args.bd)
    try:
        interfaz.menu_principal(con)
    except (EOFError, KeyboardInterrupt):
        print("\n\nPrograma finalizado.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
