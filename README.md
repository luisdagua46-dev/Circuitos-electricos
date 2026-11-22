# Sistema de apoyo para el dimensionamiento preliminar de circuitos eléctricos

Proyecto académico en Python (consola + SQLite) — Autor: Luis Dagua — v1.0

Registra circuitos y equipos, calcula potencia y corriente estimada y entrega una
**sugerencia preliminar** de conductor y breaker, con supuestos, advertencias y
datos faltantes. Si faltan datos críticos, **no emite recomendación**.

> ⚠️ Herramienta de apoyo académico. No reemplaza el diseño, la inspección ni la
> certificación de una instalación por personal competente.
> Las tablas de `configuracion.py` están transcritas de la Tabla 310.16 del NEC
> (base de la NTC 2050) y **deben verificarse** contra la NTC 2050 / RETIE vigentes.

## Características
- Circuitos monofásicos y trifásicos (RF-01, RF-02, RF-09) y equipos con potencia, cantidad, tensión, FP y tipo de carga (RF-03).
- Potencia total `Pt = Σ(Pi·ni)` e intensidad `I = P/(V·FP)` o `P/(√3·V·FP)` (RF-04, RF-05).
- Validación de entradas y detección de datos faltantes (RF-06, RNF-04).
- Selección de conductor por ampacidad, factor de temperatura, agrupamiento, bornes, regla del 125 % en cargas continuas, límite de conductores pequeños y caída de tensión (RF-07, RF-08).
- Detección de sobrecarga frente a un breaker ya instalado.
- Persistencia en SQLite y consulta de análisis guardados (RF-10).

## Requisitos e instalación
1. Python 3.8 o superior (`python --version`).
2. Clonar o descargar el proyecto y abrir una terminal en su carpeta.
3. (Opcional) entorno virtual: `python -m venv .venv` y activarlo.
4. `pip install -r requirements.txt` (no instala nada: no hay dependencias externas).

## Ejecución
```
python main.py                                   # usa data/dimensionamiento.db
python main.py --bd data/dimensionamiento_prueba.db   # base con 3 ejemplos y análisis
```
Pruebas: `python -m unittest discover -s tests -v`

## Uso rápido
1. Menú **5** carga tres ejemplos: caso normal, sobrecarga y datos insuficientes.
2. Menú **3** → elija un circuito → opción **5** para calcular.
3. Para un circuito propio: menú **1**, registre equipos (opción 2) y calcule (opción 5).
4. Si no conoce un dato de instalación, pulse Enter: queda *pendiente* y el programa lo advierte.
   Escriba `cancelar` en cualquier formulario para abortarlo.

## Estructura
```
main.py             punto de entrada
interfaz.py         menús, lectura de datos y resultados
validaciones.py     datos obligatorios, rangos y formatos
calculos.py         potencia, corriente, factores y caída de tensión
recomendaciones.py  evaluación técnica y advertencias
database.py         SQLite (circuito, equipo, analisis, recomendacion)
configuracion.py    tablas de referencia y parámetros
tests/              pruebas unitarias
data/               base de datos de prueba
docs/               documento del proyecto (visión, manuales, diagramas)
```

## Limitaciones
No evalúa: corriente de arranque ni dimensionamiento de motores (NTC 2050 §430),
capacidad de interrupción, coordinación de protecciones, reactancia en la caída de
tensión, cargas no lineales/armónicos, ni desequilibrio entre fases. La protección
no se aproxima al siguiente valor normalizado (criterio conservador). No cubre
canalizaciones enterradas ni conductores de otras tablas de ampacidad.
