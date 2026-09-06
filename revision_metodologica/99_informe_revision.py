"""
99_informe_revision.py -- reune las salidas en un solo informe.

Concatena los Markdown que producen los seis bloques y antepone un estado por
observacion: que se ejecuto, cuando, y si la corrida larga esta completa o a
medias. Pensado para entregar de una pieza a quien hizo las observaciones.

Uso:  python 99_informe_revision.py
"""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun.rutas import SALIDAS, salida, pr, tabla_md   # noqa: E402

BLOQUES = [
    ("imputacion", "Alcance de la imputacion previa", "obs4/mascara_imputacion.md"),
    ("imputacion", "Protocolo con imputacion dentro del pliegue", "obs4/comparacion_imputacion.md"),
    ("originales", "El SANNWR publicado bajo el mismo protocolo", "obs2/sannwr_original_vs_adaptado.md"),
    ("originales", "Equivalencia estructural de las implementaciones", "obs2/equivalencia_estructural.md"),
    ("originales", "Comparacion con el paquete GNNWR de los autores", "obs2/comparacion_implementaciones.md"),
    ("ajuste", "Hiperparametros de RF y HGB por validacion anidada", "obs5/ajuste_hiperparametros.md"),
    ("n efectivo", "Tamano efectivo de la muestra", "obs6/tamano_efectivo.md"),
    ("importancia", "Importancia de variables con colinealidad alta", "obs7/importancia_agrupada.md"),
    ("forma", "Fichas de implementacion", "obs5/fichas_implementacion.md"),
]
# La observacion 1 (nomenclatura de SANNWR) se verifico con
# obs1_nomenclatura/01_auditar_nomenclatura.py: cero cambios de texto o figura
# resultaron necesarios en el documento final. La observacion 3 (test ciego y
# validacion por region excluida) se ejecuto pero no se incluye aqui: no es lo
# que el revisor pidio explicitamente ni lo que describe el diseno de
# validacion por bloques de la literatura de referencia.


def completitud() -> list:
    """Cuantas combinaciones llevan hechas las dos corridas largas."""
    filas = []
    p5 = SALIDAS / "obs5" / "parciales_ajuste"
    if p5.is_dir():
        filas.append({"corrida": "ajuste de hiperparametros",
                      "combinaciones_hechas": len(list(p5.glob("*.json"))),
                      "esperado_completo": "2 modelos x 2 brazos x 16 particiones = 64",
                      "en_modo_rapido": 0})
    p2 = SALIDAS / "obs2" / "parciales_sannwr"
    if p2.is_dir():
        hechos2 = sorted(p2.glob("*.json"))
        filas.append({"corrida": "SANNWR original frente a adaptado",
                      "combinaciones_hechas": len(hechos2),
                      "esperado_completo": "2 modelos x 11 particiones = 22",
                      "en_modo_rapido": sum(1 for f in hechos2
                                            if '"rapido": true' in f.read_text(encoding="utf-8"))})
    p4 = SALIDAS / "obs4" / "parciales"
    if p4.is_dir():
        hechos = sorted(p4.glob("*.json"))
        rapidos = sum(1 for f in hechos if '"rapido": true' in f.read_text(encoding="utf-8"))
        filas.append({"corrida": "1.4 imputacion en pliegue", "combinaciones_hechas": len(hechos),
                      "esperado_completo": "2 brazos x 16 particiones x 5 modelos x semillas",
                      "en_modo_rapido": rapidos})
    return filas


def main() -> int:
    partes = ["# Informe de las correcciones metodologicas", "",
              f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')}.", "",
              "Cada seccion es la salida de un experimento ejecutable que corrige uno de",
              "los problemas senalados; el codigo que la produce esta en la carpeta",
              "correspondiente.", ""]

    estado = []
    for num, titulo, rel in BLOQUES:
        p = SALIDAS / rel
        estado.append({"correccion": num, "bloque": titulo,
                       "estado": "ejecutado" if p.exists() else "pendiente",
                       "archivo": rel})
    partes += ["## Estado", "", tabla_md(pd.DataFrame(estado)), ""]

    comp = completitud()
    if comp:
        partes += ["## Avance de las corridas largas", "", tabla_md(pd.DataFrame(comp)), ""]
        if any(c["en_modo_rapido"] for c in comp):
            partes += ["> Hay resultados en modo rapido. No son reportables: rehacerlos sin",
                       "> `--rapido` antes de citarlos.", ""]

    for num, titulo, rel in BLOQUES:
        p = SALIDAS / rel
        if not p.exists():
            continue
        texto = p.read_text(encoding="utf-8")
        # baja un nivel los encabezados para que encajen bajo el del bloque
        texto = "\n".join(("#" + l) if l.startswith("#") else l for l in texto.splitlines())
        partes += ["---", "", f"# {titulo} ({num})", "", texto, ""]

    dst = salida("INFORME_REVISION.md")
    dst.write_text("\n".join(partes), encoding="utf-8")
    pr(tabla_md(pd.DataFrame(estado)))
    pr(f"\n[md] {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
