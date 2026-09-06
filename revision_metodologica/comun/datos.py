"""
datos.py -- carga canonica del conjunto y utilidades de imputacion.

Replica EXACTAMENTE las convenciones del repositorio (los contratos criticos
que fija REPRODUCIBILITY.md): capa puntos_mercado, CRS EPSG:32717, clave predio_join casteada a
int en ambos lados de todo merge, orden determinista por predio_join, y matriz
de covariables construida por modelos/features.build_feature_matrix (one-hot de
uso_suelo_cod, 30 columnas).

Anade lo que necesita la observacion 1.4: reconstruccion de la mascara de celdas
imputadas y re-imputacion con medianas calculadas solo con filas de entrenamiento.
"""
from __future__ import annotations
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import geopandas as gpd

from .rutas import DATOS, SPLIT, FOLDS, pr

from features import build_feature_matrix, COVARIABLES   # noqa: E402  (repo)

# Variables donde la imputacion por mediana es reconstruible: continuas (muchos
# valores distintos) con un numero de empates exactos con la mediana global que
# no puede explicarse por azar. Con 4900+ valores distintos, 3 o mas empates
# exactos delatan relleno; 1 empate es la propia mediana muestral.
UMBRAL_UNICOS = 100
UMBRAL_EMPATES = 3


@dataclass
class Conjunto:
    gdf: gpd.GeoDataFrame
    coords: np.ndarray
    y_ori: np.ndarray
    y_log: np.ndarray
    X: np.ndarray             # one-hot (30 columnas)
    X_cont: np.ndarray        # codificacion continua (27) -- seleccion de bw en GWR
    nombres: list
    train_mask: np.ndarray
    test_mask: np.ndarray
    folds: np.ndarray         # bloques espaciales (fold_assignments.csv)
    zona: np.ndarray          # 10 zonas KMeans de data_split/split.csv
    predio: np.ndarray
    meta: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.gdf)


def _leer_gdf() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(DATOS, layer="puntos_mercado").to_crs(epsg=32717)
    sp = pd.read_csv(SPLIT)
    fo = pd.read_csv(FOLDS)
    for d in (gdf, sp, fo):
        d["predio_join"] = d["predio_join"].astype(int)
    gdf = gdf.merge(fo[["predio_join", "fold"]], on="predio_join", how="left")
    gdf = gdf.merge(sp[["predio_join", "zona", "split"]], on="predio_join", how="left")
    if gdf[["fold", "zona", "split"]].isna().any().any():
        raise SystemExit("merge incompleto: hay predios sin fold/zona/split")
    return gdf.sort_values("predio_join").reset_index(drop=True)


def cargar(gdf: gpd.GeoDataFrame | None = None) -> Conjunto:
    """Carga el conjunto canonico. Si se pasa un gdf (p. ej. re-imputado) se usa
    ese en lugar de leer el archivo, manteniendo el resto de convenciones."""
    if gdf is None:
        gdf = _leer_gdf()
    coords = np.column_stack([gdf.geometry.x, gdf.geometry.y]).astype(float)
    y_ori = gdf["valor_m2"].values.astype(float)
    X, nombres = build_feature_matrix(gdf)
    X_cont, _ = build_feature_matrix(gdf, one_hot=False)
    return Conjunto(
        gdf=gdf, coords=coords, y_ori=y_ori, y_log=np.log(y_ori),
        X=X, X_cont=X_cont, nombres=list(nombres),
        train_mask=(gdf["split"] == "train").values,
        test_mask=(gdf["split"] == "test").values,
        folds=gdf["fold"].values.astype(int),
        zona=gdf["zona"].values.astype(int),
        predio=gdf["predio_join"].values.astype(int),
        meta={"n": len(gdf), "p_onehot": X.shape[1], "p_cont": X_cont.shape[1]},
    )


# ---------------------------------------------------------------------------
# Observacion 1.4: imputacion previa a la particion
# ---------------------------------------------------------------------------

def diagnostico_empates(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Para cada covariable: mediana global, numero de valores identicos a ella,
    numero de valores distintos y si califica como variable imputada."""
    filas = []
    for c in COVARIABLES:
        v = gdf[c].astype(float)
        med = float(v.median())
        empates = int((v == med).sum())
        unicos = int(v.nunique())
        filas.append({
            "variable": c, "mediana_global": med, "n_empates": empates,
            "n_unicos": unicos, "continua": unicos >= UMBRAL_UNICOS,
            "imputada": bool(unicos >= UMBRAL_UNICOS and empates >= UMBRAL_EMPATES),
        })
    return pd.DataFrame(filas).sort_values("n_empates", ascending=False).reset_index(drop=True)


def mascara_imputacion(gdf: gpd.GeoDataFrame, excluir: tuple = (),
                       incluir: tuple = ()) -> pd.DataFrame:
    """DataFrame booleano (filas x variables imputadas) con las celdas que la
    reconstruccion identifica como rellenadas con la mediana global.

    Es una reconstruccion, no un registro: una celda cuyo valor real coincida
    exactamente con la mediana se marca como imputada. Con variables continuas
    de 3000+ valores distintos esos falsos positivos son raros; en `antiguedad`
    (82 valores distintos) no lo son: queda fuera del umbral de continuidad y solo
    entra si se la pide explicitamente con `incluir`.
    """
    diag = diagnostico_empates(gdf)
    vars_imp = [v for v in diag.loc[diag["imputada"], "variable"] if v not in excluir]
    for v in incluir:                      # forzar variables discretas (p. ej. antiguedad)
        if v not in vars_imp and v not in excluir:
            vars_imp.append(v)
    M = pd.DataFrame(index=gdf.index)
    for c in vars_imp:
        v = gdf[c].astype(float)
        M[c] = (v == float(v.median()))
    return M


def reimputar(gdf: gpd.GeoDataFrame, M: pd.DataFrame,
              filas_train: np.ndarray) -> gpd.GeoDataFrame:
    """Devuelve una copia del gdf con las celdas marcadas en M recalculadas con
    la mediana de cada variable estimada SOLO sobre `filas_train` (mascara
    booleana o indices), excluyendo del calculo las propias celdas marcadas."""
    g = gdf.copy()
    tr = np.zeros(len(gdf), dtype=bool)
    tr[np.asarray(filas_train)] = True
    for c in M.columns:
        v = g[c].astype(float).copy()
        celdas = M[c].values
        base = v[tr & ~celdas]
        if len(base) == 0:
            raise SystemExit(f"sin datos observados para recalcular la mediana de {c}")
        v[celdas] = float(base.median())
        g[c] = v
    return g


def medianas_comparadas(gdf: gpd.GeoDataFrame, M: pd.DataFrame,
                        filas_train: np.ndarray) -> pd.DataFrame:
    """Mediana global usada vs mediana recalculada solo con entrenamiento."""
    tr = np.zeros(len(gdf), dtype=bool)
    tr[np.asarray(filas_train)] = True
    filas = []
    for c in M.columns:
        v = gdf[c].astype(float)
        celdas = M[c].values
        med_glob = float(v.median())
        med_tr = float(v[tr & ~celdas].median())
        filas.append({
            "variable": c,
            "n_celdas_imputadas": int(celdas.sum()),
            "pct_celdas": round(100 * celdas.sum() / len(gdf), 3),
            "mediana_usada_global": med_glob,
            "mediana_solo_train": med_tr,
            "dif_abs": abs(med_tr - med_glob),
            "dif_pct": round(100 * abs(med_tr - med_glob) / abs(med_glob), 4) if med_glob else float("nan"),
        })
    return pd.DataFrame(filas).sort_values("dif_pct", ascending=False).reset_index(drop=True)
