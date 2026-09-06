"""
04a_mascara_imputacion.py -- observacion 1.4, alcance del problema.

"Las medianas utilizadas para imputar valores faltantes fueron calculadas sobre
los 5051 registros antes de realizar la separacion. Repetir el experimento
calculando las medianas exclusivamente con entrenamiento en cada fold."

Primer paso: saber que celdas estan afectadas. El conjunto entregado ya viene
imputado y no conserva un registro de que celda se relleno, asi que la mascara
se reconstruye por el mismo criterio que usa el Anexo D de la tesis: una celda
cuyo valor coincide exactamente con la mediana global de su variable, en
variables continuas donde ese empate no puede ser casualidad.

Este script cuantifica: cuantas celdas, en que variables, donde caen (prueba o
entrenamiento, que region), y cuanto se mueve cada mediana al recalcularla solo
con entrenamiento -- no solo con el 80% del reparto fijo, sino dentro de cada
pliegue de cada esquema, que es lo que pide la observacion.

No entrena modelos: eso es 04b. Corre en segundos.

Uso:
    python obs4_imputacion/04a_mascara_imputacion.py
    python obs4_imputacion/04a_mascara_imputacion.py --incluir antiguedad
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import salida, pr, tabla_md      # noqa: E402
from comun import datos as D                      # noqa: E402

from estrategias_cv import RandomKFoldCV, SpatialBlockCV   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--incluir", nargs="*", default=[],
                    help="variables discretas a forzar dentro de la mascara (p. ej. antiguedad)")
    ap.add_argument("--excluir", nargs="*", default=[])
    args = ap.parse_args()

    conj = D.cargar()
    gdf = conj.gdf
    diag = D.diagnostico_empates(gdf)
    p_diag = salida("obs4", "diagnostico_empates.csv")
    diag.to_csv(p_diag, index=False)
    pr("variables candidatas (empates exactos con la mediana global):")
    pr(tabla_md(diag.head(12)))

    M = D.mascara_imputacion(gdf, excluir=tuple(args.excluir), incluir=tuple(args.incluir))
    if M.empty:
        pr("la reconstruccion no identifica celdas imputadas")
        return 1
    idx_train = np.where(conj.train_mask)[0]
    comp = D.medianas_comparadas(gdf, M, idx_train)
    p_comp = salida("obs4", "medianas_global_vs_train.csv")
    comp.to_csv(p_comp, index=False)
    pr("\ndesplazamiento de la mediana al usar solo el 80% de entrenamiento:")
    pr(tabla_md(comp))

    # reparto de las celdas afectadas
    reparto = []
    for c in M.columns:
        cel = M[c].values
        reparto.append({
            "variable": c, "n_celdas": int(cel.sum()),
            "en_entrenamiento": int((cel & conj.train_mask).sum()),
            "en_prueba": int((cel & conj.test_mask).sum()),
            "regiones_afectadas": int(len(set(conj.zona[cel].tolist()))),
        })
    rep = pd.DataFrame(reparto)
    filas_afectadas = int(M.any(axis=1).sum())
    p_rep = salida("obs4", "reparto_celdas_imputadas.csv")
    rep.to_csv(p_rep, index=False)

    # desplazamiento dentro de cada pliegue de cada esquema
    esquemas = {
        "RandomKFold": list(RandomKFoldCV(n_splits=5, random_state=42).split(conj.X[conj.train_mask])),
        "SpatialBlock": list(SpatialBlockCV(folds=conj.folds[conj.train_mask]).split(conj.X[conj.train_mask])),
    }
    filas = []
    for nombre, splits in esquemas.items():
        for fid, (tr, _te) in enumerate(splits):
            abs_tr = idx_train[tr]
            c = D.medianas_comparadas(gdf, M, abs_tr)
            for _, r in c.iterrows():
                filas.append({"esquema": nombre, "pliegue": fid, "variable": r["variable"],
                              "mediana_usada_global": r["mediana_usada_global"],
                              "mediana_solo_train_del_pliegue": r["mediana_solo_train"],
                              "dif_pct": r["dif_pct"]})
    # y el reparto fijo 80/20
    for _, r in comp.iterrows():
        filas.append({"esquema": "ConjuntoDePrueba20", "pliegue": 0, "variable": r["variable"],
                      "mediana_usada_global": r["mediana_usada_global"],
                      "mediana_solo_train_del_pliegue": r["mediana_solo_train"],
                      "dif_pct": r["dif_pct"]})
    porf = pd.DataFrame(filas)
    p_porf = salida("obs4", "medianas_por_pliegue.csv")
    porf.to_csv(p_porf, index=False)

    peor = (porf.groupby("variable")["dif_pct"].max().reset_index()
            .rename(columns={"dif_pct": "desplazamiento_maximo_pct"})
            .sort_values("desplazamiento_maximo_pct", ascending=False).round(3))

    md = ["# Observacion 1.4 -- alcance de la imputacion previa a la particion", "",
          f"Celdas reconstruidas como imputadas: {int(M.values.sum())} en "
          f"{len(M.columns)} variables, que afectan a {filas_afectadas} de {conj.n} predios "
          f"({100*filas_afectadas/conj.n:.2f}%).", "",
          "## Identificacion", "",
          "El conjunto entregado no marca las celdas rellenadas. Se identifican por empate",
          "exacto con la mediana global en variables con centenares o miles de valores",
          "distintos, donde ese empate no ocurre por azar. Es una reconstruccion: puede",
          "incluir alguna celda cuyo valor real coincidiera con la mediana, y no puede",
          "detectar imputacion en variables discretas u ordinales.", "",
          tabla_md(diag[diag["imputada"]]), "",
          "## Reparto de las celdas afectadas", "", tabla_md(rep), "",
          "## Desplazamiento de la mediana", "",
          "Recalculada solo con el entrenamiento del reparto fijo:", "", tabla_md(comp), "",
          "Peor desplazamiento observado en cualquier pliegue de cualquier esquema:", "",
          tabla_md(peor), "",
          "## Que falta", "",
          "Esta comprobacion acota la magnitud, no corrige el procedimiento. La correccion",
          "es 04b_protocolo_en_fold.py: rehacer la evaluacion completa imputando dentro de",
          "cada pliegue y comparar contra el mismo protocolo con imputacion global.", ""]
    p_md = salida("obs4", "mascara_imputacion.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    # Copia publica sin predio_join: identificaria registros individuales del
    # catastro restringido (Anexo B). El repositorio de trabajo si conserva la
    # clave para que 04b pueda recalcular la mascara con el mismo criterio.
    p_mask = salida("obs4", "mascara_imputacion.csv")
    M.to_csv(p_mask, index=False)

    pr(f"\nceldas imputadas: {int(M.values.sum())} en {len(M.columns)} variables, "
       f"{filas_afectadas} predios afectados")
    pr(f"\n[csv] {p_diag}\n[csv] {p_comp}\n[csv] {p_rep}\n[csv] {p_porf}\n[csv] {p_mask}\n[md]  {p_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
