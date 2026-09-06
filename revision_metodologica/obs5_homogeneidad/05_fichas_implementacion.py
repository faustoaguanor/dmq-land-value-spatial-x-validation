"""
05_fichas_implementacion.py -- observacion 1.5 (homogeneidad de la comparacion).

"La pregunta respondida es mas cercana a: como se comportan estas
implementaciones concretas bajo los tres protocolos, y no estrictamente: que
familia de modelos es superior. Conviene mantener esta distincion en todo el
documento."

Dos entregables:

  1. Una ficha por modelo con lo que hace falta para que el lector juzgue si la
     comparacion es homogenea: de donde sale la especificacion, que se
     implemento, en que se aparta, que hiperparametros se usaron, si se
     ajustaron y con que datos, cuantos parametros libres tiene y que
     transformaciones comparte con los demas. Sale en CSV, en Markdown y en una
     tabla LaTeX lista para anexo.

  2. Un rastreo del texto en busca de afirmaciones que atribuyan el resultado a
     la familia de modelos ("GNNWR supera a...") en lugar de a la implementacion
     evaluada, que es lo que la observacion pide corregir.

Uso:
    python obs5_homogeneidad/05_fichas_implementacion.py
    python obs5_homogeneidad/05_fichas_implementacion.py --latex /ruta/latex_tesis
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import REPO, salida, pr, tabla_md      # noqa: E402
from comun import nombres as N                          # noqa: E402
from comun import entrenadores as E                     # noqa: E402

import gwr_core                                          # noqa: E402

N_TRAIN_REF = 4040        # tamano del entrenamiento del reparto fijo

# Frases que atribuyen el resultado a la arquitectura y no a la implementacion.
PATRONES_ATRIBUCION = [
    (r"\b(GNNWR|SANNWR[\w-]*|GWR|Random Forest|RF)\s+(supera|domina|vence|gana)", "atribuye superioridad a la familia"),
    (r"\bes\s+(superior|mejor)\s+(a|que)\b", "comparativo absoluto"),
    (r"\bdemuestra\s+que\b", "afirmacion de demostracion"),
    (r"(?<!de )(?<!del )(?<!la )\bprueba\s+que\b", "afirmacion de demostracion"),
    (r"\bel\s+mejor\s+modelo\b", "designacion de ganador"),
    (r"\bconfirma\s+que\b", "afirmacion de confirmacion"),
]
# Formulas aceptables que no deben marcarse.
EXCEPCIONES = ("menor error observado", "en este conjunto", "en esta muestra",
               "la implementacion evaluada", "no demuestra", "no prueba")


def parametros_red(n_train: int, n_features: int) -> int:
    total, prev = 0, n_train
    for h in E.DENSE_LAYERS:
        total += prev * h + h                  # lineal
        if E.BATCH_NORM:
            total += 2 * h                     # escala y desplazamiento
        prev = h
    total += prev * n_features + n_features
    total += 1                                 # PReLU compartida
    return total


def fichas() -> pd.DataFrame:
    p = 31          # 30 covariables + intercepto
    comun = {
        "objetivo": "log(valor_m2)",
        "covariables": "27 variables, con uso de suelo en codificacion disyuntiva: 30 columnas",
        "escalado": "media 0 y desviacion 1 ajustadas solo con el entrenamiento de la particion",
        "retransformacion": "exp() con factor de smearing de Duan calculado en el entrenamiento",
        "particiones": "las mismas para los cinco modelos",
    }
    filas = [
        {"modelo": N.OLS, "familia": "regresion global",
         "especificacion": "minimos cuadrados ordinarios",
         "usa_coordenadas": "no",
         "hiperparametros": "ninguno",
         "ajuste_de_hiperparametros": "no aplica",
         "parametros_libres": p,
         "divergencias_declaradas": "ninguna",
         "software": "scikit-learn LinearRegression"},
        {"modelo": N.GWR, "familia": "regresion ponderada geograficamente",
         "especificacion": "GWR con penalizacion Ridge, kernel bisquare adaptativo",
         "usa_coordenadas": "si, como ponderacion explicita",
         "hiperparametros": (f"bandwidth en [{gwr_core.BW_MIN}, {gwr_core.BW_MAX}] vecinos; "
                             f"lambda en {gwr_core.LAMBDA_GRID}; intercepto no penalizado"),
         "ajuste_de_hiperparametros": ("si, dentro del entrenamiento de cada particion: bandwidth "
                                       "por AICc y lambda por validacion espacial anidada; nunca "
                                       "mirando el conjunto evaluado"),
         "parametros_libres": f"{p} coeficientes locales por punto evaluado",
         "divergencias_declaradas": ("Ridge sobre la formulacion clasica, necesario por la "
                                     "colinealidad entre variables de distancia"),
         "software": "implementacion propia (modelos/gwr/gwr_core.py) + mgwr para el bandwidth"},
        {"modelo": N.GNNWR, "familia": "red que aprende la ponderacion",
         "especificacion": "Du et al. (2020): una red estima multiplicadores locales de los coeficientes globales",
         "usa_coordenadas": "si, como vector de distancias a todo el entrenamiento",
         "hiperparametros": (f"capas {E.DENSE_LAYERS}, dropout {E.DROP_OUT}, BatchNorm, "
                             f"Adadelta lr {E.START_LR}, decaimiento {E.WEIGHT_DECAY}, lote {E.BATCH_SIZE}, "
                             f"hasta {E.N_EPOCHS} epocas con paciencia {E.PATIENCE}"),
         "ajuste_de_hiperparametros": ("no: configuracion tomada del articulo original y mantenida fija; "
                                       "no se exploro rejilla sobre estos datos"),
         "parametros_libres": parametros_red(N_TRAIN_REF, p),
         "divergencias_declaradas": ("estandarizacion en vez de minmax; parada temprana con 10% de "
                                     "validacion; recorte de gradiente. Equivalencia con el paquete "
                                     "de los autores: ver observacion 1.2"),
         "software": "implementacion propia en PyTorch"},
        {"modelo": N.SANNWR, "familia": "red que aprende la ponderacion",
         "especificacion": ("Ni et al. (2022) adaptado: la entrada combina distancia espacial y "
                            "atributiva con peso fijo 0,5/0,5"),
         "usa_coordenadas": "si, junto con distancia en el espacio de atributos",
         "hiperparametros": (f"identicos a GNNWR; alpha fijo en {E.ALPHA_SANNWR}, no aprendido"),
         "ajuste_de_hiperparametros": "no; alpha tampoco se ajusto",
         "parametros_libres": parametros_red(N_TRAIN_REF, p),
         "divergencias_declaradas": ("el diseno original integra ambas proximidades de forma aprendida; "
                                     "aqui es una combinacion lineal fija. Por eso el rotulo -adaptado"),
         "software": "implementacion propia en PyTorch"},
        {"modelo": N.SANNWR_ORIG, "familia": "red que aprende la ponderacion",
         "especificacion": ("Ni et al. (2022) sin adaptar: un SAPDNN (red 2 -> "
                            f"{E.SAPDNN_HIDDEN} -> 1 compartida entre pares) aprende a fundir "
                            "la distancia espacial y la atributiva en una sola metrica"),
         "usa_coordenadas": "si, junto con distancia en el espacio de atributos",
         "hiperparametros": (f"identicos a GNNWR mas la capa oculta del SAPDNN ({E.SAPDNN_HIDDEN})"),
         "ajuste_de_hiperparametros": "no; la capa oculta se fijo de antemano",
         "parametros_libres": parametros_red(N_TRAIN_REF, p) + 2 * E.SAPDNN_HIDDEN + E.SAPDNN_HIDDEN + 3,
         "divergencias_declaradas": ("ninguna estructural: es el diseno publicado. Se corre para "
                                     "medir que aporta el componente que la adaptacion sustituye "
                                     "(02d_sannwr_original.py)"),
         "software": "implementacion propia en PyTorch"},
        {"modelo": N.RF, "familia": "aprendizaje automatico tabular",
         "especificacion": "bosque aleatorio sobre las mismas covariables, sin coordenadas",
         "usa_coordenadas": "no",
         "hiperparametros": f"{E.RF_TREES} arboles, resto por defecto de scikit-learn",
         "ajuste_de_hiperparametros": "no; valores por defecto declarados de antemano",
         "parametros_libres": "no comparable (estructura de arboles)",
         "divergencias_declaradas": "ninguna",
         "software": "scikit-learn RandomForestRegressor"},
    ]
    df = pd.DataFrame(filas)
    for k, v in comun.items():
        df[k] = v
    return df


def rastrear_atribucion(dir_chapters: Path) -> pd.DataFrame:
    filas = []
    for f in sorted(dir_chapters.glob("*.tex")):
        for i, linea in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            bajo = linea.lower()
            if any(e in bajo for e in EXCEPCIONES):
                continue
            for patron, motivo in PATRONES_ATRIBUCION:
                m = re.search(patron, linea, flags=re.IGNORECASE)
                if m:
                    filas.append({"archivo": f.name, "linea": i, "motivo": motivo,
                                  "extracto": linea.strip()[max(0, m.start() - 70):][:200]})
                    break
    return pd.DataFrame(filas)


def a_latex(df: pd.DataFrame) -> str:
    cols = [("modelo", "Modelo"), ("especificacion", "Especificacion"),
            ("ajuste_de_hiperparametros", "Ajuste de hiperparametros"),
            ("divergencias_declaradas", "Divergencias declaradas")]
    esc = lambda s: (str(s).replace("&", r"\&").replace("%", r"\%")   # noqa: E731
                     .replace("_", r"\_").replace("#", r"\#"))
    out = [r"\begin{table}[htbp]", r"\centering", r"\small",
           r"\caption{Ficha de las implementaciones comparadas.}",
           r"\label{tab:fichas-implementacion}",
           r"\begin{tabular}{p{2.2cm}p{4cm}p{4cm}p{4cm}}", r"\hline",
           " & ".join(t for _, t in cols) + r" \\", r"\hline"]
    for _, r in df.iterrows():
        out.append(" & ".join(esc(r[c]) for c, _ in cols) + r" \\")
    out += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", default=os.environ.get(
        "TESIS_LATEX", str(REPO.parent.parent / "latex_tesis")))
    args = ap.parse_args()

    df = fichas()
    p_csv = salida("obs5", "fichas_implementacion.csv")
    df.to_csv(p_csv, index=False, encoding="utf-8")
    p_tex = salida("obs5", "fichas_implementacion.tex")
    p_tex.write_text(a_latex(df), encoding="utf-8")

    corto = df[["modelo", "familia", "usa_coordenadas", "ajuste_de_hiperparametros",
                "parametros_libres"]]
    pr(tabla_md(corto))

    chapters = Path(args.latex) / "chapters"
    atrib = rastrear_atribucion(chapters) if chapters.is_dir() else pd.DataFrame()
    if not atrib.empty:
        p_at = salida("obs5", "atribucion_a_la_familia.csv")
        atrib.to_csv(p_at, index=False, encoding="utf-8")
        pr(f"\nfrases que atribuyen el resultado a la familia y no a la implementacion: {len(atrib)}")
        for _, r in atrib.head(15).iterrows():
            pr(f"  {r['archivo']}:{r['linea']}  ({r['motivo']})  {r['extracto'][:110]}")

    md = ["# Observacion 1.5 -- homogeneidad de la comparacion", "",
          "## Que compara realmente el estudio", "",
          "Los cinco modelos comparten objetivo, covariables, codificacion, escalado,",
          "particiones y retransformacion. No comparten origen ni grado de ajuste: dos son",
          "implementaciones propias de arquitecturas publicadas, con hiperparametros tomados",
          "del articulo y no ajustados sobre estos datos; GWR ajusta bandwidth y penalizacion",
          "dentro de cada particion; RF usa los valores por defecto de la biblioteca. Esa",
          "asimetria no invalida la comparacion, pero delimita lo que puede concluirse:",
          "",
          "> El estudio establece como se comportan estas implementaciones concretas, con",
          "> esta configuracion, sobre este conjunto y bajo tres esquemas de evaluacion. No",
          "> establece que familia de modelos es superior: para eso haria falta ajustar cada",
          "> arquitectura con el mismo esfuerzo y verificar equivalencia con las",
          "> implementaciones de referencia.",
          "",
          "## Fichas", "", tabla_md(df.drop(columns=[c for c in
                                                     ("objetivo", "covariables", "escalado",
                                                      "retransformacion", "particiones")
                                                     if c in df])), "",
          "Comun a los cinco: " + "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in
                                            df.iloc[0][["objetivo", "covariables", "escalado",
                                                        "retransformacion", "particiones"]].items()),
          "", "## Frases que conviene reformular", ""]
    if atrib.empty:
        md.append("No se detectaron atribuciones de superioridad a la familia de modelos.")
    else:
        md.append(tabla_md(atrib[["archivo", "linea", "motivo", "extracto"]]))
        md += ["", "Reformulacion sugerida: sustituir \"X supera a Y\" por \"la implementacion de X",
               "evaluada aqui obtiene menor error que la de Y en este conjunto\", y reservar",
               "\"demuestra\" para lo que la evidencia sostenga."]
    md += ["", "La tabla LaTeX lista para anexo esta en `fichas_implementacion.tex`.", ""]
    p_md = salida("obs5", "fichas_implementacion.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    pr(f"\n[csv] {p_csv}\n[tex] {p_tex}\n[md]  {p_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
