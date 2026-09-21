"""Fuente unica de las cifras que publica la tesis.

El problema que este archivo resuelve: hasta ahora cada tabla del documento se
actualizaba a mano desde el CSV que pareciera pertinente, y convivian en el
mismo cuadro resultados de una corrida y promedios de diez. Aqui se declara, de
una vez, de donde sale cada numero y con que regla se agrega.

    python analisis/cifras_canonicas.py            # imprime el informe
    python analisis/cifras_canonicas.py --json      # lo emite como JSON

Convenciones adoptadas, que el documento debe respetar:

  Conjunto de prueba .... media de las replicas para los modelos estocasticos
                          (GNNWR, SANNWR-adaptado, Random Forest) y corrida
                          unica para los deterministas (OLS, GWR).
  Validacion cruzada .... media entre semillas dentro de cada bloque, y luego
                          media no ponderada de los cinco bloques.
  Retransformacion ...... declarada por experimento, porque NO es homogenea:
                          las replicas de holdout de GNNWR y SANNWR usan la
                          exponencial directa y solo Random Forest aplica el
                          factor de Duan.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# modelo -> (ruta, filtro de columna, valor, aplica smearing en esa ruta)
REPLICAS_HOLDOUT = {
    "GNNWR": ("modelos/gnnwr/output_log/gnnwr_log_replicas.csv", None, None, False),
    "SANNWR-adaptado": ("modelos/sannwr/output_log_real/sannwr_real_log_replicas.csv", None, None, False),
    "Random Forest": ("modelos/baselines/output_log_replicas/baseline_replicas_holdout_fold.csv", "modelo", "RF", True),
}

# Los deterministas se toman del comparativo con smearing aplicado, no del
# holdout crudo de cada modelo, que retransforma con exp() a secas.
SMEARED = "analisis/output_log/comparativo_holdout_smeared.csv"
DETERMINISTAS_HOLDOUT = {"GWR": "GWR-27", "OLS": "OLS"}

REPLICAS_CV = {
    "GNNWR": ("modelos/gnnwr/output_log/gnnwr_log_cv_replicas.csv", None, None),
    "SANNWR-adaptado": ("modelos/sannwr/output_log_real/sannwr_real_log_cv_replicas.csv", None, None),
    "Random Forest": ("modelos/baselines/output_log_replicas/baseline_replicas_fold.csv", "modelo", "RF"),
}

DETERMINISTAS_CV = {
    "GWR": "modelos/gwr/output_log_27vars/gwr27_log_results.csv",
    "OLS": "modelos/ols/output_log/ols_log_results.csv",
}

METRICAS = ["RMSE", "MAE", "R2", "MAPE"]


# El repositorio de trabajo guarda cada salida junto a su modelo
# (modelos/<m>/output_log/) y el publicado las reune en results/raw/<m>/. Se
# aceptan las dos disposiciones para que el guion corra en ambos sin editarlo.
ALTERNATIVAS = {
    "modelos/gnnwr/output_log": "results/raw/gnnwr",
    "modelos/sannwr/output_log_real": "results/raw/sannwr",
    "modelos/gwr/output_log_27vars": "results/raw/gwr",
    "modelos/ols/output_log": "results/raw/ols",
    "modelos/baselines/output_log_replicas": "results/raw/random_forest",
    "analisis/output_log": "results/raw/analysis",
}


def _ruta(rel):
    p = ROOT / rel
    if p.exists():
        return p
    for viejo, nuevo in ALTERNATIVAS.items():
        if rel.startswith(viejo):
            alt = ROOT / rel.replace(viejo, nuevo, 1)
            if alt.exists():
                return alt
    raise FileNotFoundError(
        "No se hallo %s ni su equivalente en results/raw/. Este guion corre "
        "tanto en el repositorio de trabajo como en el publicado." % rel)


def _leer(rel, col=None, val=None):
    d = pd.read_csv(_ruta(rel))
    if col:
        d = d[d[col] == val]
    return d


def holdout():
    """Conjunto de prueba: media de replicas (estocasticos) o corrida (deterministas)."""
    filas = {}
    for m, (rel, col, val, smear) in REPLICAS_HOLDOUT.items():
        d = _leer(rel, col, val)
        filas[m] = {k: round(float(d[k].mean()), 4) for k in METRICAS}
        filas[m].update({"DE_" + k: round(float(d[k].std()), 4) for k in METRICAS})
        filas[m].update(n_replicas=len(d),
                        fuente=rel, agregacion="media de replicas",
                        smearing="si" if smear else "no, exponencial directa")
    comp = _leer(SMEARED)
    for m, etiqueta in DETERMINISTAS_HOLDOUT.items():
        r = comp[comp["modelo"] == etiqueta].iloc[0]
        filas[m] = {"RMSE": round(float(r["RMSE_smeared"]), 4),
                    "MAE": round(float(r["MAE_smeared"]), 4),
                    "R2": round(float(r["R2_smeared"]), 4),
                    "MAPE": round(float(r["MAPE_smeared"]), 4)}
        filas[m].update(n_replicas=1, fuente=SMEARED,
                        agregacion="corrida unica (modelo determinista)",
                        smearing="si, factor %.6f" % float(r["smearing_factor"]))
    return filas


def cv(estrategia):
    """Validacion cruzada: promedia semillas dentro del bloque y luego los cinco."""
    filas = {}
    for m, (rel, col, val) in REPLICAS_CV.items():
        d = _leer(rel, col, val)
        d = d[d["estrategia"] == estrategia]
        por_bloque = d.groupby("fold")[METRICAS].mean()
        filas[m] = {k: round(float(por_bloque[k].mean()), 4) for k in METRICAS}
        filas[m].update({"DE_" + k: round(float(por_bloque[k].std()), 4) for k in METRICAS})
        filas[m].update(peor_bloque_RMSE=round(float(por_bloque["RMSE"].max()), 4),
                        n_semillas=int(d["seed"].nunique()), n_bloques=len(por_bloque),
                        fuente=rel, agregacion="media entre semillas por bloque, luego entre bloques",
                        smearing="si, por bloque")
    for m, rel in DETERMINISTAS_CV.items():
        d = _leer(rel)
        d = d[d["estrategia"] == estrategia]
        filas[m] = {k: round(float(d[k].mean()), 4) for k in METRICAS if k in d.columns}
        filas[m].update({"DE_" + k: round(float(d[k].std()), 4) for k in METRICAS if k in d.columns})
        filas[m].update(peor_bloque_RMSE=round(float(d["RMSE"].max()), 4),
                        n_semillas=1, n_bloques=len(d), fuente=rel,
                        agregacion="media no ponderada de los cinco bloques",
                        smearing="si, por bloque")
    return filas


def moran():
    """Indice de Moran sobre los residuos del conjunto de prueba, los 5 del documento.

    moran_holdout_significancia.csv es del 2026-07-19, anterior a la
    reejecucion de GNNWR con las filas ordenadas (2026-09-20): su fila de
    GNNWR, I=0,097 con p=0,001, es una corrida ya superada y no comparable con
    el resto de esta tesis. El valor vigente de GNNWR es la media de sus diez
    replicas post-reordenamiento (0,089), pero ese archivo de replicas no
    guarda un p por semilla, de modo que NO se reporta un p para esa media:
    no hay una prueba de permutaciones calculada sobre ella. Ver la nota al
    pie de la Tabla 5.9 en el documento.
    """
    # Sin redondeo intermedio: 0,0885236 y 0,100458 truncados a 4 decimales
    # (0,0885 y 0,1005) caen justo en el punto medio, y un segundo redondeo a
    # 3 en la figura los desviaba a 0,088 y 0,101 en vez de 0,089 y 0,100. El
    # redondeo se hace una sola vez, al presentar.
    BASE_MORAN = "analisis/output_log/moran_holdout_significancia.csv"
    ETIQUETA = {"OLS": "OLS", "GWR-27": "GWR", "SANNWR": "SANNWR-adaptado", "RF": "Random Forest"}
    d = pd.read_csv(_ruta(BASE_MORAN))
    filas = {}
    for fila, nombre in ETIQUETA.items():
        r = d[d.modelo == fila].iloc[0]
        filas[nombre] = {"I": float(r.I), "p": float(r.p_sim), "fuente": BASE_MORAN}
    rep = pd.read_csv(_ruta("modelos/gnnwr/output_log/gnnwr_log_replicas.csv"))
    filas["GNNWR"] = {"I": float(rep.Moran_I_holdout.mean()),
                      "p": None,
                      "fuente": "modelos/gnnwr/output_log/gnnwr_log_replicas.csv (media de 10 semillas; sin p por semilla)"}
    return filas


def degradacion(a, b):
    """Cambio relativo de RMSE entre dos esquemas, comparando lo comparable."""
    return {m: round((b[m]["RMSE"] - a[m]["RMSE"]) / a[m]["RMSE"] * 100, 2)
            for m in a if m in b}


def equivalencia():
    d = {}
    for nom, rel in [("conjunto de prueba", "analisis/output_log/tost_equivalencia_holdout.csv"),
                     ("bloques espaciales", "analisis/output_log/tost_equivalencia_spatialblock.csv")]:
        t = pd.read_csv(_ruta(rel))
        doc = {"OLS", "GWR", "GNNWR", "SANNWR", "RF"}
        t = t[t.modelo_A.isin(doc) & t.modelo_B.isin(doc)]
        d[nom] = t.to_dict("records")
    return d


def main():
    h, ale, esp = holdout(), cv("RandomKFold"), cv("SpatialBlock")
    datos = {"conjunto_de_prueba": h, "cv_aleatoria": ale, "cv_espacial": esp,
             "degradacion_cv_a_cv_pct": degradacion(ale, esp),
             "equivalencia": equivalencia(), "moran": moran()}

    if "--json" in sys.argv:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return

    for titulo, tabla in [("CONJUNTO DE PRUEBA", h),
                          ("VALIDACION CRUZADA ALEATORIA", ale),
                          ("VALIDACION POR BLOQUES ESPACIALES", esp)]:
        print("\n" + "=" * 78)
        print(titulo)
        print("%-17s %8s %8s %7s %7s  %s" % ("modelo", "RMSE", "MAE", "R2", "MAPE", "agregacion"))
        for m, v in sorted(tabla.items(), key=lambda kv: kv[1]["RMSE"]):
            print("%-17s %8.2f %8.2f %7.3f %7.1f  %s" %
                  (m, v["RMSE"], v["MAE"], v["R2"], v["MAPE"], v["agregacion"]))
        print("  retransformacion:")
        for m, v in tabla.items():
            print("    %-17s %s" % (m, v["smearing"]))

    print("\n" + "=" * 78)
    print("DEGRADACION, CV ALEATORIA -> CV ESPACIAL (la comparacion homogenea)")
    for m, p in sorted(datos["degradacion_cv_a_cv_pct"].items(), key=lambda kv: kv[1]):
        print("  %-17s %+7.2f %%" % (m, p))


if __name__ == "__main__":
    main()
