"""
04b_protocolo_en_fold.py -- observacion 1.4, correccion.

Repite la evaluacion completa (cinco modelos, los tres esquemas de la tesis)
en dos brazos que solo se diferencian en como se rellenan los valores faltantes:

  global   la mediana de cada variable calculada sobre las 5051 observaciones,
           que es lo que hizo la tesis.
  en_fold  la mediana calculada exclusivamente con las filas de entrenamiento
           de cada particion, que es lo que pide la observacion.

Los dos brazos comparten semilla, particion, escalado y estimador, de modo que
la diferencia entre ellos es atribuible a la imputacion y no al ruido de
inicializacion ni al hardware. Por eso se corre tambien el brazo global aqui, en
vez de comparar contra las cifras almacenadas de la tesis, que salieron de otra
maquina.

Reanudable: cada combinacion brazo x esquema x pliegue x modelo x semilla queda
en salidas/obs4/parciales/.

Coste orientativo en una RTX 4090, una semilla, dos brazos, los tres esquemas
(16 particiones por brazo):
    OLS minutos | RF ~15 min | GWR ~1-2 h | GNNWR ~3-5 h | SANNWR-adaptado ~3-5 h
Conviene lanzar primero --modelos OLS RF GWR y despues las redes; o reducir a
--esquemas BloquesEspaciales, que es el esquema del que dependen las
conclusiones.

Uso:
    python obs4_imputacion/04b_protocolo_en_fold.py --modelos OLS RF GWR
    python obs4_imputacion/04b_protocolo_en_fold.py --esquemas BloquesEspaciales
    python obs4_imputacion/04b_protocolo_en_fold.py --brazos en_fold
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
from comun.rutas import SALIDAS, salida, pr, tabla_md    # noqa: E402
from comun import datos as D, nombres as N               # noqa: E402
from comun import entrenadores as E                      # noqa: E402
from comun.metricas import metricas                      # noqa: E402

from estrategias_cv import RandomKFoldCV, SpatialBlockCV  # noqa: E402

DIR = SALIDAS / "obs4"
PARCIALES = DIR / "parciales"
DESPLAZAMIENTO = {"RandomKFold": 0, "BloquesEspaciales": 1000, "ConjuntoDePrueba20": 3000}


def particiones(conj, esquema):
    """Devuelve [(id_pliegue, idx_train_abs, idx_eval_abs)] en indices absolutos."""
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
    ap.add_argument("--brazos", nargs="+", default=["global", "en_fold"],
                    choices=["global", "en_fold"])
    ap.add_argument("--esquemas", nargs="+",
                    default=["ConjuntoDePrueba20", "RandomKFold", "BloquesEspaciales"],
                    choices=["ConjuntoDePrueba20", "RandomKFold", "BloquesEspaciales"])
    ap.add_argument("--modelos", nargs="+", default=N.MODELOS, choices=N.MODELOS_TODOS,
                    help="por defecto los cinco de la tesis; SANNWR-original "
                         "(el diseno publicado con SAPDNN) hay que pedirlo")
    ap.add_argument("--semillas", type=int, nargs="+", default=[42])
    ap.add_argument("--incluir", nargs="*", default=[],
                    help="variables discretas extra en la mascara (p. ej. antiguedad)")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--rehacer", action="store_true")
    args = ap.parse_args()

    PARCIALES.mkdir(parents=True, exist_ok=True)
    base = D.cargar()
    M = D.mascara_imputacion(base.gdf, incluir=tuple(args.incluir))
    pr(f"mascara: {int(M.values.sum())} celdas en {list(M.columns)}")
    pr(f"brazos={args.brazos}  esquemas={args.esquemas}  modelos={args.modelos}  "
       f"semillas={args.semillas}  dispositivo={E.DEVICE}")
    if args.rapido:
        pr("[MODO RAPIDO] cifras no reportables")

    total = (len(args.brazos) * len(args.modelos) * len(args.semillas)
             * sum(len(particiones(base, e)) for e in args.esquemas))
    hecho, t0_all = 0, time.time()

    for esquema in args.esquemas:
        for fid, idx_tr, idx_te in particiones(base, esquema):
            conj_en_fold = None            # se construye solo si hace falta
            for brazo in args.brazos:
                if brazo == "global":
                    conj = base
                else:
                    if conj_en_fold is None:
                        gdf_r = D.reimputar(base.gdf, M, idx_tr)
                        conj_en_fold = D.cargar(gdf_r)
                    conj = conj_en_fold
                for modelo in args.modelos:
                    semillas = (args.semillas[:1] if modelo in N.DETERMINISTAS
                                else args.semillas)
                    for semilla in semillas:
                        s = semilla + DESPLAZAMIENTO[esquema] + fid
                        k = (f"{brazo}_{esquema}_f{fid}_"
                             f"{modelo.lower().replace('-', '_')}_s{semilla}")
                        p_json = PARCIALES / f"{k}.json"
                        if p_json.exists() and not args.rehacer:
                            hecho += 1
                            continue
                        pr(f"  [{hecho+1}/{total}] {brazo} / {esquema} / pliegue {fid} / "
                           f"{modelo} / semilla {semilla}")
                        t0 = time.time()
                        r = E.entrenar(conj, idx_tr, idx_te, modelo, semilla=s,
                                       etiqueta=k, rapido=args.rapido, verboso=False)
                        m = metricas(conj.y_ori[idx_te], r.pred_log_test,
                                     conj.y_log[idx_te], r.s_M)
                        reg = {"brazo": brazo, "esquema": esquema, "pliegue": int(fid),
                               "modelo": modelo, "semilla": int(semilla), "semilla_efectiva": int(s),
                               "n_train": int(len(idx_tr)), "n_eval": int(len(idx_te)),
                               "segundos": round(time.time() - t0, 1),
                               "rapido": bool(args.rapido), **m}
                        p_json.write_text(json.dumps(reg, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
                        pd.DataFrame({"predio_join": conj.predio[idx_te],
                                      "brazo": brazo, "esquema": esquema, "pliegue": fid,
                                      "modelo": modelo, "semilla": semilla,
                                      "y_obs_log": conj.y_log[idx_te],
                                      "y_pred_log": r.pred_log_test,
                                      "s_M": r.s_M}).to_csv(PARCIALES / f"{k}_pred.csv", index=False)
                        hecho += 1
                        pr(f"      RMSE={m['RMSE']:.2f}  MAE={m['MAE']:.2f}  "
                           f"({reg['segundos']:.0f} s)")

    filas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PARCIALES.glob("*.json"))]
    if not filas:
        pr("sin resultados")
        return 1
    df = pd.DataFrame(filas)
    p_res = salida("obs4", "resultados_por_pliegue.csv")
    df.to_csv(p_res, index=False)

    agg = (df.groupby(["brazo", "esquema", "modelo"])
             .agg(RMSE=("RMSE", "mean"), RMSE_sd_pliegues=("RMSE", "std"),
                  MAE=("MAE", "mean"), R2=("R2", "mean"), pliegues=("pliegue", "nunique"))
             .reset_index().round(3))
    p_agg = salida("obs4", "resumen_por_brazo.csv")
    agg.to_csv(p_agg, index=False)

    pareado = agg.pivot_table(index=["esquema", "modelo"], columns="brazo",
                              values=["RMSE", "MAE"]).reset_index()
    pareado.columns = ["_".join([c for c in col if c]).strip() for col in pareado.columns]
    if "RMSE_global" in pareado and "RMSE_en_fold" in pareado:
        pareado["delta_RMSE"] = (pareado["RMSE_en_fold"] - pareado["RMSE_global"]).round(3)
        pareado["delta_pct"] = (100 * pareado["delta_RMSE"] / pareado["RMSE_global"]).round(2)
        # el ordenamiento, que es lo que la tesis afirma
        for brazo in ("global", "en_fold"):
            col = f"RMSE_{brazo}"
            pareado[f"puesto_{brazo}"] = (pareado.groupby("esquema")[col]
                                          .rank(method="min").astype("Int64"))
        pareado["cambia_de_puesto"] = pareado["puesto_global"] != pareado["puesto_en_fold"]
    p_par = salida("obs4", "comparacion_pareada.csv")
    pareado.to_csv(p_par, index=False)

    md = ["# Observacion 1.4 -- imputacion dentro de cada pliegue", "",
          f"Mascara reconstruida: {int(M.values.sum())} celdas en {len(M.columns)} variables "
          f"({', '.join(M.columns)}).",
          f"Semillas {args.semillas}; los dos brazos comparten semilla y particion.",
          f"Modelos consolidados en esta tabla: {', '.join(sorted(df['modelo'].unique()))}.",
          f"Esquemas: {', '.join(sorted(df['esquema'].unique()))}.", "",
          "## Comparacion pareada", "", tabla_md(pareado), "",
          "## Resumen por brazo", "", tabla_md(agg), "",
          "## Lectura", "",
          "Lo que decide es la columna de cambio de puesto: si el ordenamiento entre modelos",
          "se mantiene, la fuga de la imputacion previa no sostiene ninguna conclusion del",
          "documento y basta con declararla; si cambia, hay que reportar el brazo en_fold",
          "como resultado principal.", "",
          "## Lo que este brazo no corrige", "",
          "Queda una decision de preprocesamiento que sigue tomandose sobre el conjunto",
          "completo: el colapso de las categorias raras de uso de suelo en la codificacion",
          "disyuntiva, que cuenta frecuencias sobre las 5051 filas. No mira el objetivo y es",
          "determinista, pero en sentido estricto tampoco esta dentro del pliegue. Se declara",
          "aqui por la misma razon por la que se declara la imputacion.", ""]
    p_md = salida("obs4", "comparacion_imputacion.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    pr("\n" + tabla_md(pareado))
    pr(f"\n[csv] {p_res}\n[csv] {p_agg}\n[csv] {p_par}\n[md]  {p_md}")
    pr(f"tiempo de esta corrida: {(time.time()-t0_all)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
