"""
02c_comparar_equivalencia.py -- observacion 1.2, comparacion.

Cruza las predicciones del paquete de referencia (02a) con las de la
implementacion de la tesis sobre los mismos 1011 predios y responde tres
preguntas separadas, que conviene no mezclar:

  1. Acuerdo punto a punto: correlacion y diferencia tipica entre lo que predice
     una implementacion y la otra en cada predio.
  2. Acuerdo en desempeno: RMSE y MAE de cada una sobre el mismo conjunto.
  3. Si la diferencia entre implementaciones es mayor o menor que la variacion
     que la propia implementacion propia muestra entre semillas (10 replicas
     almacenadas). Esta es la pregunta que decide si "GNNWR obtiene X" es una
     afirmacion sobre la arquitectura o sobre una implementacion concreta.

Las metricas se calculan sin factor de smearing, porque las predicciones del
paquete no traen residuales de entrenamiento; para la comparacion entre
implementaciones eso es indiferente (ambas se miden igual).

Uso:  python obs2_equivalencia_gnnwr/02c_comparar_equivalencia.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import REPO, SALIDAS, salida, pr, tabla_md   # noqa: E402

REF = SALIDAS / "obs2" / "predicciones_paquete_gnnwr.csv"
PROPIA = REPO / "modelos" / "gnnwr" / "output_log" / "gnnwr_log_predictions.csv"
REPLICAS = REPO / "modelos" / "gnnwr" / "output_log" / "gnnwr_log_replicas.csv"


def desempeno(y_obs_log, y_pred_log):
    obs, pred = np.exp(y_obs_log), np.exp(y_pred_log)
    e = obs - pred
    ss_t = float(np.sum((obs - obs.mean()) ** 2))
    return {"RMSE": round(float(np.sqrt(np.mean(e ** 2))), 3),
            "MAE": round(float(np.mean(np.abs(e))), 3),
            "R2": round(1 - float(np.sum(e ** 2)) / ss_t, 4),
            "R2_log": round(1 - float(np.sum((y_obs_log - y_pred_log) ** 2))
                            / float(np.sum((y_obs_log - y_obs_log.mean()) ** 2)), 4)}


def main() -> int:
    if not REF.exists():
        pr(f"falta {REF}\nCorrer antes 02a_referencia_gnnwr.py (necesita el paquete gnnwr).")
        return 1
    ref = pd.read_csv(REF)
    propia = pd.read_csv(PROPIA)
    propia = propia[propia["split"] == "test"].copy()
    propia["predio_join"] = propia["predio_join"].astype(int)
    ref["predio_join"] = ref["predio_join"].astype(int)

    base = desempeno(propia["y_obs_log"].values, propia["y_pred_log"].values)
    pr(f"implementacion de la tesis (semilla 42): RMSE={base['RMSE']}  MAE={base['MAE']}  "
       f"R2={base['R2']}  n={len(propia)}")

    rep = pd.read_csv(REPLICAS) if REPLICAS.exists() else None
    if rep is not None:
        pr(f"replicas almacenadas: RMSE {rep.RMSE.min():.2f}-{rep.RMSE.max():.2f} "
           f"(media {rep.RMSE.mean():.2f}, desviacion {rep.RMSE.std():.2f}, "
           f"{len(rep)} semillas)")

    filas = []
    for (config, semilla), g in ref.groupby(["config", "semilla"]):
        m = g.merge(propia[["predio_join", "y_pred_log"]], on="predio_join",
                    how="inner", suffixes=("_ref", "_propia"))
        if len(m) != len(propia):
            pr(f"  [aviso] {config}/{semilla}: cruzan {len(m)} de {len(propia)} predios")
        d_ref = desempeno(m["y_obs_log"].values, m["y_pred_log_ref"].values)
        e_ref = (np.exp(m["y_obs_log"]) - np.exp(m["y_pred_log_ref"])) ** 2
        e_pro = (np.exp(m["y_obs_log"]) - np.exp(m["y_pred_log_propia"])) ** 2
        w = stats.wilcoxon(e_ref, e_pro)
        t = stats.ttest_rel(e_ref, e_pro)
        dentro = (rep is not None) and (rep.RMSE.min() <= d_ref["RMSE"] <= rep.RMSE.max())
        filas.append({
            "config": config, "semilla": semilla, "n": len(m),
            "RMSE_paquete": d_ref["RMSE"], "RMSE_propia": base["RMSE"],
            "MAE_paquete": d_ref["MAE"], "MAE_propia": base["MAE"],
            "R2_log_paquete": d_ref["R2_log"], "R2_log_propia": base["R2_log"],
            "dif_RMSE": round(d_ref["RMSE"] - base["RMSE"], 3),
            "r_pearson": round(float(np.corrcoef(m["y_pred_log_ref"], m["y_pred_log_propia"])[0, 1]), 4),
            "rho_spearman": round(float(stats.spearmanr(m["y_pred_log_ref"], m["y_pred_log_propia"]).statistic), 4),
            "dif_media_USD": round(float(np.mean(np.exp(m["y_pred_log_ref"]) - np.exp(m["y_pred_log_propia"]))), 2),
            "dif_abs_mediana_USD": round(float(np.median(np.abs(np.exp(m["y_pred_log_ref"]) - np.exp(m["y_pred_log_propia"])))), 2),
            "wilcoxon_p": round(float(w.pvalue), 5),
            "t_pareado_p": round(float(t.pvalue), 5),
            "dentro_del_rango_de_semillas": dentro,
        })

    df = pd.DataFrame(filas).sort_values(["config", "semilla"])
    dst = salida("obs2", "comparacion_implementaciones.csv")
    df.to_csv(dst, index=False, encoding="utf-8")
    pr("\n" + df.to_string(index=False))

    cols = ["config", "semilla", "RMSE_paquete", "RMSE_propia", "dif_RMSE",
            "r_pearson", "dif_abs_mediana_USD", "dentro_del_rango_de_semillas"]
    md = ["# Observacion 1.2 -- comparacion con la implementacion de referencia", "",
          f"Mismos {len(propia)} predios de prueba, mismas 30 covariables, misma particion.",
          "Metricas sin factor de smearing: el paquete no entrega residuales de entrenamiento",
          "y la comparacion entre implementaciones no depende de ese factor.", "",
          tabla_md(df[cols]), ""]
    if rep is not None:
        md += ["## Referencia de variabilidad propia", "",
               f"La implementacion de la tesis, con {len(rep)} semillas, da un RMSE entre "
               f"{rep.RMSE.min():.2f} y {rep.RMSE.max():.2f} USD/m2 "
               f"(media {rep.RMSE.mean():.2f}, desviacion {rep.RMSE.std():.2f}).",
               "Si la corrida del paquete cae dentro de ese rango, la diferencia entre",
               "implementaciones no es distinguible del ruido de inicializacion; si cae fuera,",
               "el resultado depende de la implementacion y debe enunciarse asi.", ""]
    md += ["## Como redactarlo", "",
           "Con esta evidencia, la formula defendible es: \"la implementacion de GNNWR",
           "evaluada aqui obtiene ...\". Solo si la corrida del paquete cae dentro del rango",
           "entre semillas cabe hablar de GNNWR sin calificar, y aun asi conviene declarar",
           "que la comparacion se hizo con una sola version del paquete y un solo conjunto.", ""]
    dstm = salida("obs2", "comparacion_implementaciones.md")
    dstm.write_text("\n".join(md), encoding="utf-8")
    pr(f"\n[csv] {dst}\n[md]  {dstm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
