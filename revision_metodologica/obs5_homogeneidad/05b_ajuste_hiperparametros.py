"""
05b_ajuste_hiperparametros.py -- la observacion sobre el ajuste de Random Forest.

"No se hizo ajuste de hiperparametros para Random Forest": corrio con los valores
por defecto de la biblioteca mientras GWR elegia bandwidth y penalizacion dentro
de cada particion. La comparacion no era homogenea en esfuerzo de ajuste, y un
modelo puede quedar injustamente por debajo o por encima por esa razon.

La correccion es rehacer la evaluacion con RF (y HGB) eligiendo hiperparametros
por validacion cruzada espacial ANIDADA dentro del entrenamiento de cada
particion, con el mismo procedimiento que ya usaba GWR para su penalizacion:
KMeans sobre las coordenadas del entrenamiento, dejar un grupo fuera por turno,
criterio MAE en USD/m2. El conjunto evaluado no interviene.

Se corren los dos brazos, por defecto y ajustado, con la misma semilla y la misma
particion, de modo que la diferencia sea atribuible al ajuste.

Rejillas declaradas de antemano (comun/ajuste.py):
  RF   n_estimators [300, 800] x max_features [1.0, 0.5, 0.33] x
       min_samples_leaf [1, 2, 5]                                 = 18 configuraciones
  HGB  max_iter [400, 800] x learning_rate [0.05, 0.1] x
       max_leaf_nodes [31, 63] x min_samples_leaf [10, 20]        = 16 configuraciones

Coste medido en un portatil: ajustar RF sobre 4040 predios tarda unos 5 min por
particion (54 ajustes internos); el brazo por defecto, 8 s. Con los tres esquemas
(16 particiones) y los dos modelos, unas 2-3 h en local. No necesita GPU.

Uso:
    python obs5_homogeneidad/05b_ajuste_hiperparametros.py
    python obs5_homogeneidad/05b_ajuste_hiperparametros.py --modelos RF
    python obs5_homogeneidad/05b_ajuste_hiperparametros.py --esquemas BloquesEspaciales
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import SALIDAS, salida, pr, tabla_md      # noqa: E402
from comun import datos as D, nombres as N                 # noqa: E402
from comun import entrenadores as E, ajuste as A           # noqa: E402
from comun.metricas import metricas                        # noqa: E402

from estrategias_cv import RandomKFoldCV, SpatialBlockCV    # noqa: E402

PARCIALES = SALIDAS / "obs5" / "parciales_ajuste"
DESPLAZAMIENTO = {"RandomKFold": 0, "BloquesEspaciales": 1000, "ConjuntoDePrueba20": 3000}


def particiones(conj, esquema):
    idx_train = np.where(conj.train_mask)[0]
    if esquema == "ConjuntoDePrueba20":
        return [(0, idx_train, np.where(conj.test_mask)[0])]
    if esquema == "RandomKFold":
        sp = RandomKFoldCV(n_splits=5, random_state=42).split(conj.X[conj.train_mask])
    else:
        sp = SpatialBlockCV(folds=conj.folds[conj.train_mask]).split(conj.X[conj.train_mask])
    return [(i, idx_train[tr], idx_train[te]) for i, (tr, te) in enumerate(sp)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="+", default=N.AJUSTABLES, choices=N.AJUSTABLES)
    ap.add_argument("--esquemas", nargs="+",
                    default=["ConjuntoDePrueba20", "RandomKFold", "BloquesEspaciales"],
                    choices=["ConjuntoDePrueba20", "RandomKFold", "BloquesEspaciales"])
    ap.add_argument("--brazos", nargs="+", default=["defecto", "ajustado"],
                    choices=["defecto", "ajustado"])
    ap.add_argument("--semillas", type=int, nargs="+", default=[42])
    ap.add_argument("--rehacer", action="store_true")
    args = ap.parse_args()

    PARCIALES.mkdir(parents=True, exist_ok=True)
    conj = D.cargar()
    for m in args.modelos:
        pr(f"rejilla {m}: {A.coste_estimado(conj, None, m)}")
    total = (len(args.modelos) * len(args.brazos) * len(args.semillas)
             * sum(len(particiones(conj, e)) for e in args.esquemas))
    pr(f"corridas={total}   (el brazo ajustado es el lento)")

    hecho, t_ini = 0, time.time()
    for esquema in args.esquemas:
        for fid, idx_tr, idx_te in particiones(conj, esquema):
            for modelo in args.modelos:
                for brazo in args.brazos:
                    for semilla in args.semillas:
                        s = semilla + DESPLAZAMIENTO[esquema] + fid
                        k = f"{esquema}_f{fid}_{modelo.lower()}_{brazo}_s{semilla}"
                        p_json = PARCIALES / f"{k}.json"
                        if p_json.exists() and not args.rehacer:
                            hecho += 1
                            continue
                        pr(f"  [{hecho+1}/{total}] {esquema} / pliegue {fid} / {modelo} / {brazo}")
                        t0 = time.time()
                        r = E.entrenar(conj, idx_tr, idx_te, modelo, semilla=s, etiqueta=k,
                                       ajustar=(brazo == "ajustado"), verboso=True)
                        m = metricas(conj.y_ori[idx_te], r.pred_log_test,
                                     conj.y_log[idx_te], r.s_M)
                        reg = {"esquema": esquema, "pliegue": int(fid), "modelo": modelo,
                               "brazo": brazo, "semilla": int(semilla),
                               "n_train": int(len(idx_tr)), "n_eval": int(len(idx_te)),
                               "segundos": round(time.time() - t0, 1),
                               "hiperparametros": json.dumps(r.extras.get("hiperparametros", {}),
                                                             ensure_ascii=False),
                               **m}
                        p_json.write_text(json.dumps(reg, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
                        hecho += 1
                        pr(f"      RMSE={m['RMSE']:.2f}  MAE={m['MAE']:.2f}  "
                           f"({reg['segundos']:.0f} s)")

    filas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PARCIALES.glob("*.json"))]
    if not filas:
        pr("sin resultados")
        return 1
    df = pd.DataFrame(filas)
    p_res = salida("obs5", "ajuste_por_pliegue.csv")
    df.to_csv(p_res, index=False)

    agg = (df.groupby(["esquema", "modelo", "brazo"])
             .agg(RMSE=("RMSE", "mean"), RMSE_sd=("RMSE", "std"), MAE=("MAE", "mean"),
                  R2=("R2", "mean"), pliegues=("pliegue", "nunique"),
                  minutos=("segundos", lambda x: round(x.sum() / 60, 1)))
             .reset_index().round(3))
    p_agg = salida("obs5", "ajuste_resumen.csv")
    agg.to_csv(p_agg, index=False)

    pareado = agg.pivot_table(index=["esquema", "modelo"], columns="brazo",
                              values=["RMSE", "MAE"]).reset_index()
    pareado.columns = ["_".join([c for c in col if c]).strip() for col in pareado.columns]
    if "RMSE_defecto" in pareado and "RMSE_ajustado" in pareado:
        pareado["ganancia_RMSE"] = (pareado["RMSE_defecto"] - pareado["RMSE_ajustado"]).round(3)
        pareado["ganancia_pct"] = (100 * pareado["ganancia_RMSE"]
                                   / pareado["RMSE_defecto"]).round(2)
    p_par = salida("obs5", "ajuste_pareado.csv")
    pareado.to_csv(p_par, index=False)

    # que configuracion gana, y con que estabilidad entre particiones
    elegidas = (df[df["brazo"] == "ajustado"]
                .groupby(["modelo", "hiperparametros"]).size()
                .reset_index(name="veces_elegida")
                .sort_values(["modelo", "veces_elegida"], ascending=[True, False]))
    p_el = salida("obs5", "ajuste_configuraciones_elegidas.csv")
    elegidas.to_csv(p_el, index=False)

    md = ["# Ajuste de hiperparametros de los modelos de arboles", "",
          "La objecion era que Random Forest corrio con los valores por defecto mientras",
          "GWR ajustaba los suyos dentro de cada particion. Aqui se le da el mismo trato:",
          "validacion cruzada espacial anidada dentro del entrenamiento, criterio MAE en",
          "USD/m2, rejilla declarada de antemano, sin mirar el conjunto evaluado.", "",
          f"Modelos: {', '.join(args.modelos)}. Semillas: {args.semillas}.", "",
          "## Por defecto frente a ajustado", "", tabla_md(pareado), "",
          "## Configuraciones que elige el procedimiento", "", tabla_md(elegidas), "",
          "## Detalle", "", tabla_md(agg), "",
          "## Como leerlo", "",
          "Si la ganancia es practicamente nula y el procedimiento termina eligiendo la",
          "configuracion por defecto, la objecion queda respondida de la mejor manera",
          "posible para el documento: el resultado no dependia de no haber ajustado. Si la",
          "ganancia es apreciable, hay que rehacer las tablas del capitulo con el brazo",
          "ajustado, porque entonces la comparacion original si estaba sesgada en contra de",
          "los modelos de arboles.", "",
          "Queda declarado lo que este experimento no hace: las dos redes mantienen la",
          "configuracion de sus articulos y no se les busca rejilla, porque el coste seria",
          "de varios dias de GPU. La asimetria se reduce, no desaparece, y conviene decirlo",
          "con esas palabras.", ""]
    p_md = salida("obs5", "ajuste_hiperparametros.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    pr("\n" + tabla_md(pareado))
    pr(f"\n[csv] {p_res}\n[csv] {p_agg}\n[csv] {p_par}\n[csv] {p_el}\n[md]  {p_md}")
    pr(f"tiempo de esta corrida: {(time.time()-t_ini)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
