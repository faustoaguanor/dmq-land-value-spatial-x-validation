"""
02d_sannwr_original.py -- el SANNWR publicado, bajo el protocolo de la tesis.

Complemento indispensable de la observacion 1.1. Renombrar el modelo a
SANNWR-adaptado deja constancia de que lo evaluado no es el diseno de Ni et al.
(2022), pero no dice que habria dado el diseno publicado. Este script lo corre.

  SANNWR-original   SAPDNN: una red 2 -> 4 -> 1, compartida entre todos los
                    pares, aprende a fundir la distancia espacial con la
                    atributiva en una sola metrica, que recibe la SWNN. Se
                    entrena de extremo a extremo junto con el resto.
  SANNWR-adaptado   la misma arquitectura salvo que esa fusion es fija:
                    d = 0,5*d_espacial + 0,5*d_atributiva.

Los dos se corren aqui uno al lado del otro, con las mismas particiones, las
mismas semillas y en la misma maquina, bajo los tres esquemas de la tesis
(conjunto de prueba del 20%, reparto aleatorio K=5, bloques espaciales K=5).
Asi la diferencia es atribuible al componente que se sustituyo y no al hardware.

Antecedente en el repositorio: modelos/sannwr/sannwr_sapdnn_holdout.py ya
comparo ambos sobre el conjunto de prueba y con UNA sola ejecucion (SAPDNN
102,47 frente a 92,29 de la version 0,5/0,5). El revisor senala exactamente eso:
"la comparacion con la arquitectura original se realiza esencialmente con una
sola ejecucion". Por eso aqui el valor por defecto son tres semillas y dos
esquemas: con modelos estocasticos, una corrida no distingue una diferencia real
del ruido de inicializacion.

Las semillas son las del proyecto original en cada esquema: DIEZ sobre el
conjunto de prueba, como en sannwr_real_log_replicas.csv, y CINCO en bloques,
como en sannwr_real_log_cv_replicas.csv. Asi la comparacion queda de igual a
igual con las tablas de replicas publicadas.

Reanudable, como el resto. Coste en una RTX 4090: 20 entrenamientos en el
conjunto de prueba mas 50 en bloques = 70, unas 7-8 h.

Uso:
    python obs2_equivalencia_gnnwr/02d_sannwr_original.py
    python obs2_equivalencia_gnnwr/02d_sannwr_original.py --esquemas ConjuntoDePrueba20
    python obs2_equivalencia_gnnwr/02d_sannwr_original.py --semillas 42 2011 456
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
from comun.rutas import REPO, SALIDAS, salida, pr, tabla_md    # noqa: E402
from comun import datos as D, nombres as N                     # noqa: E402
from comun import entrenadores as E                            # noqa: E402
from comun.metricas import metricas, moran_i                   # noqa: E402

from estrategias_cv import RandomKFoldCV, SpatialBlockCV        # noqa: E402

PARCIALES = SALIDAS / "obs2" / "parciales_sannwr"
# Mismas semillas que el proyecto original, esquema por esquema: diez sobre el
# conjunto de prueba (como *_log_replicas.csv) y cinco en validacion cruzada y
# bloques (como *_log_cv_replicas.csv). Asi la comparacion es de igual a igual
# con las tablas de replicas publicadas.
SEMILLAS_POR_ESQUEMA = {
    "ConjuntoDePrueba20": [42, 2011, 456, 777, 2026, 99, 1234, 888, 314, 7],
    "RandomKFold": [42, 2011, 456, 777, 2026],
    "BloquesEspaciales": [42, 2011, 456, 777, 2026],
}
DESPLAZAMIENTO = {"RandomKFold": 0, "BloquesEspaciales": 1000, "ConjuntoDePrueba20": 3000}
MODELOS = [N.SANNWR, N.SANNWR_ORIG]


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
    ap.add_argument("--esquemas", nargs="+",
                    default=["ConjuntoDePrueba20", "BloquesEspaciales"],
                    choices=["ConjuntoDePrueba20", "RandomKFold", "BloquesEspaciales"])
    ap.add_argument("--modelos", nargs="+", default=MODELOS, choices=MODELOS)
    ap.add_argument("--semillas", type=int, nargs="+", default=None,
                    help="por defecto, las mismas que el proyecto original en cada esquema: "
                         "diez en el conjunto de prueba y cinco en bloques. Se puede forzar "
                         "una lista unica para todos los esquemas")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--rehacer", action="store_true")
    args = ap.parse_args()

    PARCIALES.mkdir(parents=True, exist_ok=True)
    conj = D.cargar()
    semillas_de = {e: (args.semillas if args.semillas else SEMILLAS_POR_ESQUEMA[e])
                   for e in args.esquemas}
    total = sum(len(particiones(conj, e))
                * sum(1 if m in N.DETERMINISTAS else len(semillas_de[e]) for m in args.modelos)
                for e in args.esquemas)
    pr(f"modelos={args.modelos}  esquemas={args.esquemas}  corridas={total}  "
       f"dispositivo={E.DEVICE}")
    for e in args.esquemas:
        pr(f"  {e}: {len(particiones(conj, e))} particion(es) x {len(semillas_de[e])} semillas")
    pr(f"SAPDNN: 2 -> {E.SAPDNN_HIDDEN} -> 1 con PReLU; adaptado: alpha fijo {E.ALPHA_SANNWR}")
    if args.rapido:
        pr("[MODO RAPIDO] cifras no reportables")

    hecho, t_ini = 0, time.time()
    for esquema in args.esquemas:
        for fid, idx_tr, idx_te in particiones(conj, esquema):
            for modelo in args.modelos:
                semillas = (semillas_de[esquema][:1] if modelo in N.DETERMINISTAS
                            else semillas_de[esquema])
                for semilla in semillas:
                    s = semilla + DESPLAZAMIENTO[esquema] + fid
                    k = (f"{esquema}_f{fid}_{modelo.lower().replace('-', '_')}_s{semilla}")
                    p_json = PARCIALES / f"{k}.json"
                    if p_json.exists() and not args.rehacer:
                        hecho += 1
                        continue
                    pr(f"  [{hecho+1}/{total}] {esquema} / pliegue {fid} / {modelo} / semilla {semilla}")
                    t0 = time.time()
                    r = E.entrenar(conj, idx_tr, idx_te, modelo, semilla=s,
                                   etiqueta=k, rapido=args.rapido, verboso=False)
                    m = metricas(conj.y_ori[idx_te], r.pred_log_test, conj.y_log[idx_te], r.s_M)
                    I, _, p_sim, _ = moran_i(conj.y_log[idx_te] - r.pred_log_test,
                                             conj.coords[idx_te])
                    reg = {"esquema": esquema, "pliegue": int(fid), "modelo": modelo,
                           "semilla": int(semilla), "semilla_efectiva": int(s),
                           "n_train": int(len(idx_tr)), "n_eval": int(len(idx_te)),
                           "segundos": round(time.time() - t0, 1), "rapido": bool(args.rapido),
                           "moran_I": round(I, 6), "moran_p": p_sim, **m}
                    p_json.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
                    pd.DataFrame({"predio_join": conj.predio[idx_te], "esquema": esquema,
                                  "pliegue": fid, "modelo": modelo, "semilla": semilla,
                                  "y_obs_log": conj.y_log[idx_te],
                                  "y_pred_log": r.pred_log_test,
                                  "s_M": r.s_M}).to_csv(PARCIALES / f"{k}_pred.csv", index=False)
                    hecho += 1
                    pr(f"      RMSE={m['RMSE']:.2f}  MAE={m['MAE']:.2f}  R2={m['R2']:.3f}  "
                       f"({reg['segundos']:.0f} s)")

    filas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PARCIALES.glob("*.json"))]
    if not filas:
        pr("sin resultados")
        return 1
    df = pd.DataFrame(filas)
    p_res = salida("obs2", "sannwr_original_por_pliegue.csv")
    df.to_csv(p_res, index=False)

    agg = (df.groupby(["esquema", "modelo"])
             .agg(RMSE=("RMSE", "mean"), RMSE_sd=("RMSE", "std"),
                  MAE=("MAE", "mean"), R2=("R2", "mean"),
                  moran_I=("moran_I", "mean"), pliegues=("pliegue", "nunique"),
                  minutos=("segundos", lambda x: round(x.sum() / 60, 1)))
             .reset_index().round(3))
    p_agg = salida("obs2", "sannwr_original_vs_adaptado.csv")
    agg.to_csv(p_agg, index=False)

    comp = agg.pivot_table(index="esquema", columns="modelo", values="RMSE")
    if N.SANNWR in comp and N.SANNWR_ORIG in comp:
        comp["diferencia"] = (comp[N.SANNWR_ORIG] - comp[N.SANNWR]).round(2)
        comp["dif_pct"] = (100 * comp["diferencia"] / comp[N.SANNWR]).round(1)
    comp = comp.reset_index().round(2)

    md = ["# Observacion 1.1 (evidencia) -- el SANNWR publicado bajo el mismo protocolo", "",
          "La observacion pide rotular la implementacion como SANNWR-adaptado. Esta tabla",
          "aporta lo que el rotulo por si solo no dice: que habria dado el diseno de Ni et",
          "al. (2022), con su SAPDNN aprendiendo la fusion de las dos distancias, corrido",
          "sobre las mismas particiones y en la misma maquina.", "",
          "Semillas por esquema: " + "; ".join(f"{e}: {len(semillas_de[e])}"
                                                for e in args.esquemas)
          + ". RMSE en USD/m2 con smearing por particion.", "",
          "## Comparacion", "", tabla_md(comp), "",
          "## Detalle por esquema", "", tabla_md(agg), "",
          "## Como redactarlo", "",
          "Si el diseno publicado no mejora a la adaptacion, la frase honesta es que la",
          "simplificacion 0,5/0,5 no perjudico en este conjunto, y que por tanto los",
          "resultados no deben leerse como una evaluacion de SANNWR sino de una variante",
          "suya que aqui rinde igual o mejor. Si lo mejora, hay que decir que la",
          "implementacion evaluada subestima a la arquitectura publicada y acotar en cuanto.",
          "En cualquiera de los dos casos el rotulo -adaptado se mantiene: describe lo que",
          "se implemento, no lo que rindio.", ""]
    p_md = salida("obs2", "sannwr_original_vs_adaptado.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    pr("\n" + tabla_md(comp))
    pr(f"\n[csv] {p_res}\n[csv] {p_agg}\n[md]  {p_md}")
    pr(f"tiempo de esta corrida: {(time.time()-t_ini)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
