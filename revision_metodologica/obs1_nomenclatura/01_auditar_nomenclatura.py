"""
01_auditar_nomenclatura.py -- observacion 1.1 (denominacion de SANNWR).

"SANNWR no es realmente el SANNWR original [...] deberia denominarse
sistematicamente SANNWR-adaptado en tablas, figuras, resumen, conclusiones y
discusion."

El script no edita nada. Localiza cada aparicion de SANNWR sin el sufijo y la
clasifica en tres categorias:

  ACCION   la mencion designa a la implementacion evaluada (resultados, tablas,
           figuras, conclusiones, resumen): debe llevar el sufijo.
  OK       la mencion designa a la arquitectura publicada de Ni et al. (2022)
           (marco teorico, estado del arte, cita bibliografica, glosario): el
           sufijo seria incorrecto ahi.
  REVISAR  el contexto no permite decidir automaticamente.

Revisa tres superficies: los .tex de la tesis, el texto embebido en los PDF de
las figuras (que es donde el sufijo suele faltar, porque lo escriben los scripts
de figures/) y los literales de etiqueta en los scripts que generan figuras.

Uso:
    python obs1_nomenclatura/01_auditar_nomenclatura.py
    python obs1_nomenclatura/01_auditar_nomenclatura.py --latex /ruta/latex_tesis
    python obs1_nomenclatura/01_auditar_nomenclatura.py --emitir-parches
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import REPO, salida, pr, tabla_md   # noqa: E402

PATRON = re.compile(r"SANNWR(?!-adaptado)")
SUFIJO = "SANNWR-adaptado"

# Pistas de que la frase habla de la arquitectura publicada y no de la implementacion.
PISTAS_PUBLICADA = (
    "ni2022sannwr", "ni et al", "original", "publicad", "propusieron", "propuso",
    "extendieron", "arquitectura", "newacronym", "\\gls", "spatial and attribute",
    "literatura", "estado del arte", "disenno original", "diseno original",
)
# Pistas de que la frase habla de la implementacion evaluada.
PISTAS_IMPLEMENTACION = (
    "rmse", "mae", "usd", "tabla", "figura", "\\caption", "bloque", "pliegue",
    "semilla", "error", "resultado", "&", "moran", "desempen", "ordenamiento",
)
# Archivos donde la mencion casi siempre designa a la implementacion.
ARCHIVOS_IMPLEMENTACION = ("cap5", "cap6", "resumen", "abstract", "anexo_d", "anexo_f")


def clasificar(archivo: str, linea: str) -> str:
    bajo = linea.lower()
    if any(p in bajo for p in PISTAS_PUBLICADA):
        return "OK"
    stem = Path(archivo).stem.lower()
    if any(stem.startswith(a) for a in ARCHIVOS_IMPLEMENTACION):
        return "ACCION"
    if any(p in bajo for p in PISTAS_IMPLEMENTACION):
        return "ACCION"
    return "REVISAR"


def escanear_tex(dir_chapters: Path) -> list:
    filas = []
    for f in sorted(dir_chapters.glob("*.tex")):
        for i, linea in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in PATRON.finditer(linea):
                filas.append({
                    "superficie": "tex", "archivo": str(f), "linea": i,
                    "clasificacion": clasificar(f.name, linea),
                    "extracto": linea.strip()[max(0, m.start() - 60):][:180],
                })
    return filas


def escanear_pdfs(dirs) -> list:
    try:
        import fitz                       # pymupdf
    except ImportError:
        pr("  [aviso] pymupdf no disponible: no se revisa el texto de las figuras")
        return []
    filas = []
    pdfs = sorted({q for d in dirs if Path(d).is_dir() for q in Path(d).rglob("*.pdf")})
    for f in pdfs:
        try:
            with fitz.open(f) as doc:
                texto = "\n".join(p.get_text() for p in doc)
        except Exception as exc:          # noqa: BLE001
            pr(f"  [aviso] no se pudo leer {f.name}: {exc}")
            continue
        n = len(PATRON.findall(texto))
        n_ok = texto.count(SUFIJO)
        if n:
            filas.append({
                "superficie": "figura_pdf", "archivo": str(f), "linea": 0,
                "clasificacion": "ACCION",
                "extracto": f"{n} rotulos 'SANNWR' sin sufijo ({n_ok} con sufijo) en el texto del PDF",
            })
    return filas


def escanear_scripts_figuras() -> list:
    filas = []
    for f in sorted((REPO / "figures").rglob("*.py")):
        for i, linea in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not PATRON.search(linea):
                continue
            # solo interesan los literales que terminan como rotulo en la figura
            es_rotulo = ('"SANNWR"' in linea or "'SANNWR'" in linea)
            filas.append({
                "superficie": "script_figura", "archivo": str(f), "linea": i,
                "clasificacion": "ACCION" if es_rotulo else "REVISAR",
                "extracto": linea.strip()[:180],
            })
    return filas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", default=os.environ.get(
        "TESIS_LATEX", str(REPO.parent.parent / "latex_tesis")),
        help="raiz del proyecto LaTeX (por defecto ../../latex_tesis)")
    ap.add_argument("--emitir-parches", action="store_true",
                    help="escribe un archivo con los reemplazos sugeridos (no los aplica)")
    args = ap.parse_args()

    latex = Path(args.latex)
    filas = []
    if (latex / "chapters").is_dir():
        pr(f"tex     : {latex/'chapters'}")
        filas += escanear_tex(latex / "chapters")
    else:
        pr(f"[aviso] no existe {latex/'chapters'}: se omite el texto")
    pr(f"figuras : PDF bajo {REPO/'figures'} y {latex/'figuras'}")
    filas += escanear_pdfs([REPO / "figures", latex / "figuras"])
    n_png = len(list((latex / "figuras").glob("*.png"))) if (latex / "figuras").is_dir() else 0
    if n_png:
        pr(f"          ({n_png} PNG en el proyecto LaTeX: sin texto extraible, se audita"
           " el script que los genera)")
    pr(f"scripts : {REPO/'figures'}")
    filas += escanear_scripts_figuras()

    df = pd.DataFrame(filas)
    if df.empty:
        pr("\nsin apariciones de SANNWR sin sufijo")
        return 0

    df["archivo_corto"] = df["archivo"].map(lambda p: Path(p).name)
    orden = {"ACCION": 0, "REVISAR": 1, "OK": 2}
    df = df.sort_values(["clasificacion", "superficie", "archivo_corto", "linea"],
                        key=lambda s: s.map(orden) if s.name == "clasificacion" else s)

    dst = salida("obs1", "nomenclatura_sannwr.csv")
    df.to_csv(dst, index=False, encoding="utf-8")

    resumen = df.groupby(["clasificacion", "superficie"]).size().reset_index(name="n")
    pr("\n" + resumen.to_string(index=False))

    md = ["# Observacion 1.1 -- denominacion de SANNWR", "",
          "Regla aplicada: `SANNWR-adaptado` para la implementacion evaluada (distancias",
          "espacial y atributiva combinadas con pesos fijos 0,5/0,5); `SANNWR` a secas solo",
          "cuando la frase designa la arquitectura publicada por Ni et al. (2022).", "",
          "## Recuento", "", tabla_md(resumen), ""]
    for cat in ("ACCION", "REVISAR", "OK"):
        sub = df[df["clasificacion"] == cat]
        if sub.empty:
            continue
        md += [f"## {cat} ({len(sub)})", ""]
        for _, r in sub.iterrows():
            loc = f"{r['archivo_corto']}:{r['linea']}" if r["linea"] else r["archivo_corto"]
            md.append(f"- `{loc}` -- {r['extracto']}")
        md.append("")
    md += ["## Como aplicar", "",
           "1. En los `.tex`, sustituir solo las lineas marcadas ACCION.",
           "2. En los scripts de `figures/`, cambiar el rotulo del modelo y volver a",
           "   generar la figura; el texto embebido en el PDF es lo que ve el lector.",
           "3. Reejecutar este script hasta que ACCION quede en cero.", ""]
    dst_md = salida("obs1", "nomenclatura_sannwr.md")
    dst_md.write_text("\n".join(md), encoding="utf-8")

    if args.emitir_parches:
        acciones = df[(df["clasificacion"] == "ACCION") & (df["superficie"] != "figura_pdf")]
        objetivos = [{"archivo": r["archivo"], "linea": int(r["linea"])}
                     for _, r in acciones.iterrows()]
        p = salida("obs1", "aplicar_nomenclatura.py")
        p.write_text(
            '"""Reemplazos sugeridos por 01_auditar_nomenclatura.py.\n'
            'Revisar la lista antes de ejecutar con --aplicar; sin esa bandera solo muestra\n'
            'el antes y el despues de cada linea.\n"""\n'
            "import re, sys, json\n"
            "from pathlib import Path\n\n"
            f"OBJETIVOS = {json.dumps(objetivos, indent=2)}\n"
            'PATRON = re.compile(r"SANNWR(?!-adaptado)")\n'
            'APLICAR = "--aplicar" in sys.argv\n\n'
            "por_archivo = {}\n"
            "for o in OBJETIVOS:\n"
            "    por_archivo.setdefault(o['archivo'], set()).add(o['linea'])\n"
            "for archivo, lineas in por_archivo.items():\n"
            "    p = Path(archivo)\n"
            "    src = p.read_text(encoding='utf-8').splitlines(keepends=True)\n"
            "    for n in sorted(lineas):\n"
            "        antes = src[n-1]\n"
            "        despues = PATRON.sub('SANNWR-adaptado', antes)\n"
            "        if antes != despues:\n"
            "            print(f'{p.name}:{n}')\n"
            "            print('  -', antes.rstrip())\n"
            "            print('  +', despues.rstrip())\n"
            "            src[n-1] = despues\n"
            "    if APLICAR:\n"
            "        p.write_text(''.join(src), encoding='utf-8')\n"
            "        print(f'[escrito] {p}')\n", encoding="utf-8")
        pr(f"[py]  {p}   (ejecutarlo sin argumentos muestra el diff; --aplicar lo escribe)")

    pr(f"\n[csv] {dst}\n[md]  {dst_md}")
    n_accion = int((df["clasificacion"] == "ACCION").sum())
    pr(f"\npendientes de renombrar: {n_accion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
