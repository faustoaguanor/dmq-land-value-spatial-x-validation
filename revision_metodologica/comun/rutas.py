"""
rutas.py -- localizacion del repositorio y de las salidas.

La carpeta revision_metodologica/ puede vivir dentro del repo (uso local) o
copiarse a /workspace en un pod. En ambos casos la raiz del repo se resuelve asi:

  1. variable de entorno TESIS_REPO (ruta absoluta a .../replicacion)
  2. el directorio padre de revision_metodologica/
  3. busqueda hacia arriba de un directorio que contenga datos/dataset.gpkg

Ademas registra en sys.path los modulos del repo que se reutilizan tal cual
(features.py, gwr_core.py, estrategias_cv.py). Nada de este paquete escribe
dentro del repo: todas las salidas van a revision_metodologica/salidas/.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent          # .../revision_metodologica/comun
BASE = AQUI.parent                              # .../revision_metodologica
SALIDAS = BASE / "salidas"


def _candidatas():
    env = os.environ.get("TESIS_REPO")
    if env:
        yield Path(env).expanduser().resolve()
    yield BASE.parent
    for p in [BASE, *BASE.parents]:
        yield p


def resolver_repo() -> Path:
    for c in _candidatas():
        try:
            if (c / "datos" / "dataset.gpkg").exists() and (c / "modelos" / "features.py").exists():
                return c
        except OSError:
            continue
    raise SystemExit(
        "No se encontro la raiz del repositorio (se busco datos/dataset.gpkg).\n"
        "Define TESIS_REPO=/ruta/a/replicacion o coloca esta carpeta dentro del repo."
    )


REPO = resolver_repo()
DATOS = REPO / "datos" / "dataset.gpkg"
SPLIT = REPO / "data_split" / "split.csv"
FOLDS = REPO / "spatial_cv" / "output" / "fold_assignments.csv"

# Se ANADEN al final, no al principio: modelos/ contiene subdirectorios llamados
# gnnwr, sannwr, gwr, ols... y si esas rutas van primero Python los toma como
# paquetes de espacio de nombres y tapa a los paquetes instalados con el mismo
# nombre (le pasa al paquete de referencia gnnwr de la observacion 1.2).
for _p in (REPO / "modelos", REPO / "modelos" / "gwr", REPO / "spatial_cv"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))


def salida(*partes) -> Path:
    """Devuelve (creando el directorio) una ruta bajo revision_metodologica/salidas/."""
    p = SALIDAS.joinpath(*partes)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def dir_salida(*partes) -> Path:
    p = SALIDAS.joinpath(*partes)
    p.mkdir(parents=True, exist_ok=True)
    return p


def pr(*a, **k):
    print(*a, **k, flush=True)


def tabla_md(df, indice: bool = False) -> str:
    """Tabla markdown sin depender de tabulate."""
    import pandas as pd  # local: evita el import si no se usa
    d = df.reset_index() if indice else df
    cols = [str(c) for c in d.columns]
    filas = [[("" if pd.isna(v) else str(v)) for v in fila] for fila in d.itertuples(index=False)]
    anchos = [max(len(cols[i]), *(len(f[i]) for f in filas)) if filas else len(cols[i])
              for i in range(len(cols))]
    sep = "| " + " | ".join("-" * a for a in anchos) + " |"
    cab = "| " + " | ".join(c.ljust(a) for c, a in zip(cols, anchos)) + " |"
    cuerpo = ["| " + " | ".join(v.ljust(a) for v, a in zip(f, anchos)) + " |" for f in filas]
    return chr(10).join([cab, sep, *cuerpo])
