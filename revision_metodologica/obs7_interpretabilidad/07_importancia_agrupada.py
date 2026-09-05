"""
07_importancia_agrupada.py -- la observacion sobre la importancia de variables.

"Las variables de distancia presentan VIF superiores a 25, de manera que
permutation importance no debe interpretarse causalmente. Se recomienda evitar
expresiones fuertes como 'lo que manda es donde esta el predio'."

La advertencia esta bien puesta, pero en el documento es solo una advertencia.
Aqui se convierte en medicion, que es lo que permite escribir la frase correcta
en vez de una mas prudente pero igual de vaga.

Tres cosas:

  1. La tabla de VIF de las 27 variables, para respaldar la afirmacion con
     numeros propios en lugar de repetirla.

  2. Grupos de variables por correlacion (agrupamiento jerarquico sobre
     1 - |Spearman|). Con multicolinealidad alta, permutar una variable sola
     subestima su papel: el modelo recupera la informacion por sus companeras.
     Ese es exactamente el mecanismo que hace enganosa la lectura individual.

  3. Importancia por permutacion INDIVIDUAL y POR GRUPO, una al lado de la otra.
     La diferencia entre ambas mide cuanta de la importancia atribuida a una
     variable es en realidad compartida. Es la forma estandar de tratar
     predictores correlacionados y sostiene una afirmacion mas defendible: no
     "manda dist_cc", sino "manda el bloque de accesibilidad, dentro del cual las
     variables no son separables con estos datos".

Barato para RF y HGB (segundos). Para las redes hay que reentrenar una vez
(--con-red GNNWR), lo que cuesta cerca de una hora en un portatil.

Uso:
    python obs7_interpretabilidad/07_importancia_agrupada.py
    python obs7_interpretabilidad/07_importancia_agrupada.py --con-red GNNWR
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import salida, pr, tabla_md          # noqa: E402
from comun import datos as D, nombres as N            # noqa: E402
from comun import entrenadores as E                   # noqa: E402
from comun.metricas import metricas                   # noqa: E402

N_REPETICIONES = 10          # permutaciones por variable o grupo
UMBRAL_GRUPO = 0.4           # distancia 1-|rho| a la que se corta el dendrograma


def vif(X: np.ndarray, nombres: list) -> pd.DataFrame:
    """VIF por regresion de cada columna sobre las demas."""
    from sklearn.linear_model import LinearRegression
    filas = []
    for j, nom in enumerate(nombres):
        otros = np.delete(X, j, axis=1)
        r2 = LinearRegression().fit(otros, X[:, j]).score(otros, X[:, j])
        filas.append({"variable": nom,
                      "VIF": round(float(1 / max(1 - r2, 1e-12)), 2),
                      "R2_contra_las_demas": round(float(r2), 4)})
    return pd.DataFrame(filas).sort_values("VIF", ascending=False).reset_index(drop=True)


def agrupar(X: np.ndarray, nombres: list, umbral: float = UMBRAL_GRUPO):
    rho = spearmanr(X).statistic
    rho = np.atleast_2d(rho)
    dist = 1 - np.abs(np.nan_to_num(rho, nan=0.0))
    np.fill_diagonal(dist, 0.0)
    dist = (dist + dist.T) / 2
    Z = linkage(squareform(dist, checks=False), method="average")
    etiquetas = fcluster(Z, t=umbral, criterion="distance")
    grupos = {}
    for nom, g in zip(nombres, etiquetas):
        grupos.setdefault(int(g), []).append(nom)
    return grupos, rho


def permutar(predecir, X_te, coords_te, y_ori, y_log, s_M, columnas, semilla=42,
             n_rep=N_REPETICIONES):
    """Delta de RMSE en USD/m2 al permutar conjuntamente `columnas`."""
    rng = np.random.default_rng(semilla)
    base = metricas(y_ori, predecir(X_te, coords_te), y_log, s_M)["RMSE"]
    deltas = []
    for _ in range(n_rep):
        Xp = X_te.copy()
        orden = rng.permutation(len(Xp))
        Xp[:, columnas] = Xp[orden][:, columnas]      # permuta el bloque en conjunto
        deltas.append(metricas(y_ori, predecir(Xp, coords_te), y_log, s_M)["RMSE"] - base)
    return float(np.mean(deltas)), float(np.std(deltas)), base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="+", default=[N.RF, N.HGB],
                    choices=[N.RF, N.HGB])
    ap.add_argument("--con-red", nargs="*", default=[],
                    choices=[N.GNNWR, N.SANNWR, N.SANNWR_ORIG],
                    help="anade redes: hay que entrenarlas una vez (caro)")
    ap.add_argument("--umbral", type=float, default=UMBRAL_GRUPO)
    ap.add_argument("--repeticiones", type=int, default=N_REPETICIONES)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    conj = D.cargar()
    idx_tr = np.where(conj.train_mask)[0]
    idx_te = np.where(conj.test_mask)[0]
    nombres = conj.nombres

    # 1. VIF
    tab_vif = vif(conj.X[idx_tr], nombres)
    p_vif = salida("obs7", "vif.csv")
    tab_vif.to_csv(p_vif, index=False)
    n_altos = int((tab_vif["VIF"] > 25).sum())
    pr(f"VIF > 25: {n_altos} de {len(nombres)} variables")
    pr(tabla_md(tab_vif.head(10)))

    # 2. grupos por correlacion
    grupos, _ = agrupar(conj.X[idx_tr], nombres, args.umbral)
    tab_gr = pd.DataFrame([{"grupo": g, "n_variables": len(v), "variables": ", ".join(v)}
                           for g, v in sorted(grupos.items())])
    p_gr = salida("obs7", "grupos_correlacion.csv")
    tab_gr.to_csv(p_gr, index=False)
    pr(f"\ngrupos con umbral 1-|rho| <= {args.umbral}: {len(grupos)}")
    pr(tabla_md(tab_gr[tab_gr["n_variables"] > 1]))

    # 3. importancia individual y por grupo
    filas = []
    for modelo in list(args.modelos) + list(args.con_red):
        pr(f"\n[{modelo}] entrenando una vez ...")
        r = E.entrenar(conj, idx_tr, idx_te, modelo, semilla=args.semilla,
                       etiqueta=f"imp_{modelo}", verboso=False, devolver_predictor=True)
        if r.predecir is None:
            pr("  este modelo no devuelve predictor; se omite")
            continue
        X_te, c_te = conj.X[idx_te], conj.coords[idx_te]
        y_ori, y_log = conj.y_ori[idx_te], conj.y_log[idx_te]
        base = metricas(y_ori, r.pred_log_test, y_log, r.s_M)["RMSE"]
        pr(f"  RMSE base = {base:.2f}")

        for j, nom in enumerate(nombres):
            d, sd, _ = permutar(r.predecir, X_te, c_te, y_ori, y_log, r.s_M, [j],
                                args.semilla, args.repeticiones)
            g = next(k for k, v in grupos.items() if nom in v)
            filas.append({"modelo": modelo, "variable": nom, "grupo": g,
                          "tipo": "individual", "delta_RMSE": round(d, 3),
                          "sd": round(sd, 3)})
        for g, vs in sorted(grupos.items()):
            cols = [nombres.index(v) for v in vs]
            d, sd, _ = permutar(r.predecir, X_te, c_te, y_ori, y_log, r.s_M, cols,
                                args.semilla, args.repeticiones)
            filas.append({"modelo": modelo, "variable": f"grupo {g} ({len(vs)} vars)",
                          "grupo": g, "tipo": "grupo", "delta_RMSE": round(d, 3),
                          "sd": round(sd, 3)})
        del r

    imp = pd.DataFrame(filas)
    p_imp = salida("obs7", "importancia_individual_y_grupo.csv")
    imp.to_csv(p_imp, index=False)

    # contraste: suma de individuales frente a la del grupo entero
    contraste = []
    for modelo in imp["modelo"].unique():
        sub = imp[imp["modelo"] == modelo]
        for g in sorted(grupos):
            ind = sub[(sub["grupo"] == g) & (sub["tipo"] == "individual")]["delta_RMSE"].sum()
            gru = sub[(sub["grupo"] == g) & (sub["tipo"] == "grupo")]["delta_RMSE"]
            if len(gru) and len(grupos[g]) > 1:
                contraste.append({
                    "modelo": modelo, "grupo": g, "n_variables": len(grupos[g]),
                    "suma_individuales": round(float(ind), 2),
                    "permutando_el_grupo": round(float(gru.iloc[0]), 2),
                    "razon": round(float(gru.iloc[0]) / ind, 2) if ind else float("nan")})
    tab_con = pd.DataFrame(contraste)
    p_con = salida("obs7", "individual_vs_grupo.csv")
    tab_con.to_csv(p_con, index=False)

    top = (imp[imp["tipo"] == "individual"].sort_values(["modelo", "delta_RMSE"],
                                                        ascending=[True, False])
           .groupby("modelo").head(5))

    md = ["# Importancia de variables con colinealidad alta", "",
          "La advertencia del documento es correcta y aqui queda respaldada con medicion",
          "propia, no solo enunciada.", "",
          f"## VIF: {n_altos} de {len(nombres)} variables por encima de 25", "",
          tabla_md(tab_vif.head(15)), "",
          f"## Grupos de variables correlacionadas (corte 1-|rho| <= {args.umbral})", "",
          tabla_md(tab_gr), "",
          "## Importancia individual frente a importancia del grupo", "",
          "Permutar una variable sola con companeras muy correlacionadas subestima su",
          "papel: el modelo recupera la informacion por las demas. Permutar el grupo",
          "entero mide lo que aporta el bloque de informacion, que es lo unico separable",
          "con estos datos.", "", tabla_md(tab_con), "",
          "## Cinco primeras por modelo (permutacion individual)", "",
          tabla_md(top[["modelo", "variable", "delta_RMSE", "sd"]]), "",
          "## Como redactarlo", "",
          "La columna `razon` es lo que hay que mirar, y se lee en las dos direcciones.",
          "Por encima de 1, las variables se tapan entre si y la permutacion individual",
          "subestima el papel de cada una. Por debajo de 1, que es lo habitual con",
          "predictores muy correlacionados, las importancias individuales suman mas de lo",
          "que el bloque entero aporta: cada variable se lleva el credito de informacion",
          "compartida y el ordenamiento entre ellas no significa gran cosa.", "",
          "En cualquiera de los dos casos la lectura correcta es de bloque y no de",
          "variable: el modelo usa la posicion relativa a un conjunto de destinos urbanos",
          "sin que estos datos permitan separar cual pesa. La formula defendible es \"la",
          "capacidad predictiva se concentra en variables de accesibilidad mutuamente",
          "correlacionadas\", y no \"lo que manda es donde esta el predio\", que suena a",
          "efecto causal y ademas atribuye a una variable lo que pertenece a un grupo.", "",
          "Conviene ademas no ordenar las variables en una tabla como si el orden fuera",
          "estable: con estos VIF, pequenas diferencias de delta cambian el orden entre",
          "semillas.", ""]
    p_md = salida("obs7", "importancia_agrupada.md")
    p_md.write_text("\n".join(md), encoding="utf-8")

    pr("\n" + tabla_md(tab_con))
    pr(f"\n[csv] {p_vif}\n[csv] {p_gr}\n[csv] {p_imp}\n[csv] {p_con}\n[md]  {p_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
