"""
06_tamano_efectivo.py -- observacion 1.6 (tamano efectivo de la muestra).

"Dejar claro que n=5051 no equivale a tener 5051 observaciones independientes
para inferir diferencias de generalizacion espacial."

Cuantifica esa perdida y muestra que cambia en las conclusiones. Tres lecturas
del mismo conjunto de prueba, de la mas optimista a la mas conservadora:

  1. n nominal: 1011 predios, que es lo que suponen las pruebas pareadas al uso.
  2. n efectivo: el numero de observaciones independientes equivalentes dada la
     autocorrelacion espacial del error (Clifford et al. 1989; Cressie 1993),
     estimado con un correlograma exponencial ajustado a la propia variable que
     entra en la prueba.
  3. n de unidades espaciales: los bloques o regiones, que es la unidad de
     analisis cuando lo que se quiere inferir es generalizacion espacial.

Con cada uno se rehace la prueba pareada entre modelos y se compara el p-valor.
Corre en CPU en un par de minutos y no depende de las corridas largas.

Uso:
    python obs6_n_efectivo/06_tamano_efectivo.py
    python obs6_n_efectivo/06_tamano_efectivo.py --pares GNNWR-RF SANNWR-adaptado-RF
"""
from __future__ import annotations
import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit
from scipy.spatial import KDTree, distance

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import REPO, salida, pr, tabla_md      # noqa: E402
from comun import datos as D, nombres as N              # noqa: E402
from comun.metricas import moran_i                      # noqa: E402

# Predicciones almacenadas de la version defendida (test + train, escala log).
FUENTES = {
    N.OLS: "modelos/ols/output_log/ols_log_predictions.csv",
    N.GWR: "modelos/gwr/output_log_27vars/gwr27_log_predictions.csv",
    N.GNNWR: "modelos/gnnwr/output_log/gnnwr_log_predictions.csv",
    N.SANNWR: "modelos/sannwr/output_log_real/sannwr_real_log_predictions.csv",
    N.RF: "modelos/baselines/output_log/rf_log_predictions.csv",
}
RANGO_RESIDUAL = 2530.0     # rango del variograma de residuales
RANGO_OBJETIVO = 5621.8     # rango del variograma del valor, usado para el tamano de bloque


def correlograma(coords, valores, n_bins=20, max_frac=0.5):
    """Correlograma empirico: correlacion media entre pares por banda de distancia."""
    d = distance.pdist(coords)
    z = valores - valores.mean()
    var = float(np.mean(z ** 2))
    prod = np.multiply.outer(z, z)[np.triu_indices(len(z), k=1)]
    dmax = np.quantile(d, max_frac)
    bordes = np.linspace(0, dmax, n_bins + 1)
    centros, rho, npares = [], [], []
    for a, b in zip(bordes[:-1], bordes[1:]):
        m = (d >= a) & (d < b)
        if m.sum() < 30:
            continue
        centros.append((a + b) / 2)
        rho.append(float(prod[m].mean() / var))
        npares.append(int(m.sum()))
    return np.array(centros), np.array(rho), np.array(npares)


def ajustar_exponencial(h, rho):
    def f(x, rho0, a):
        return rho0 * np.exp(-x / a)
    try:
        p, _ = curve_fit(f, h, rho, p0=[max(rho[0], 0.05), 2000.0],
                         bounds=([0.0, 100.0], [1.0, 50000.0]), maxfev=20000)
        return float(p[0]), float(p[1])
    except Exception:                                   # noqa: BLE001
        return float("nan"), float("nan")


def n_efectivo(coords, valores, bloque=800):
    """n_eff = n / (1 + (1/n) * suma_{i!=j} rho(d_ij)), con rho exponencial ajustado.
    Clifford et al. (1989) y Cressie (1993, seccion 1.3): la varianza de la media de
    una muestra correlacionada equivale a la de una muestra independiente de tamano n_eff."""
    n = len(valores)
    h, rho, _ = correlograma(coords, valores)
    if len(h) < 4:
        return {"n": n, "n_eff": float(n), "rho0": float("nan"), "rango_m": float("nan")}
    rho0, a = ajustar_exponencial(h, rho)
    if not np.isfinite(rho0) or not np.isfinite(a):
        return {"n": n, "n_eff": float(n), "rho0": rho0, "rango_m": a}
    suma = 0.0
    for i0 in range(0, n, bloque):                      # por bloques: evita la matriz n x n
        dd = distance.cdist(coords[i0:i0 + bloque], coords)
        suma += float(np.sum(rho0 * np.exp(-dd / a)))
    suma -= n * rho0                                    # descontar los pares i=i (d=0)
    factor = 1.0 + suma / n
    neff = float(np.clip(n / factor, 1.0, n))
    return {"n": n, "n_eff": neff, "rho0": rho0, "rango_m": a}


def conjunto_independiente(coords, radio):
    """Cardinal de un conjunto de puntos separados entre si por mas de `radio`
    (greedy). Cota inferior interpretable del numero de localizaciones independientes."""
    arbol = KDTree(coords)
    tomados, prohibidos = [], set()
    for i in range(len(coords)):
        if i in prohibidos:
            continue
        tomados.append(i)
        prohibidos.update(arbol.query_ball_point(coords[i], r=radio))
    return len(tomados)


def cargar_errores(conj):
    """Error en USD/m2 por predio del conjunto de prueba, con smearing calculado
    con las filas de entrenamiento del propio archivo."""
    fuera, faltan = {}, []
    for modelo, ruta in FUENTES.items():
        p = REPO / ruta
        if not p.exists():
            faltan.append(ruta)
            continue
        df = pd.read_csv(p)
        df["predio_join"] = df["predio_join"].astype(int)
        tr = df[df["split"] == "train"]
        s_M = float(np.mean(np.exp(tr["y_obs_log"] - tr["y_pred_log"]))) if len(tr) else 1.0
        te = df[df["split"] == "test"].copy()
        te["pred_usd"] = np.exp(te["y_pred_log"]) * s_M
        te["obs_usd"] = np.exp(te["y_obs_log"])
        te["error_abs"] = (te["obs_usd"] - te["pred_usd"]).abs()
        te["error_cuad"] = (te["obs_usd"] - te["pred_usd"]) ** 2
        fuera[modelo] = te.set_index("predio_join")[["error_abs", "error_cuad", "pred_usd", "obs_usd"]]
    return fuera, faltan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pares", nargs="*", default=None,
                    help="pares modelo-modelo; por defecto todos")
    args = ap.parse_args()

    conj = D.cargar()
    errores, faltan = cargar_errores(conj)
    if faltan:
        pr("[aviso] faltan predicciones almacenadas: " + ", ".join(faltan))
    if len(errores) < 2:
        pr("no hay suficientes modelos para comparar")
        return 1

    idx_te = np.where(conj.test_mask)[0]
    predios_te = conj.predio[idx_te]
    coords_te = conj.coords[idx_te]
    bloques_te = conj.folds[idx_te]
    regiones_te = conj.zona[idx_te]
    pr(f"conjunto de prueba: {len(predios_te)} predios, {len(set(bloques_te.tolist()))} bloques, "
       f"{len(set(regiones_te.tolist()))} regiones")

    # -- 1. tamano efectivo del error de cada modelo -------------------------
    filas = []
    for modelo, df in errores.items():
        e = df.reindex(predios_te)["error_abs"].values
        ok = np.isfinite(e)
        I, _, p_sim, _ = moran_i(e[ok], coords_te[ok])
        r = n_efectivo(coords_te[ok], e[ok])
        filas.append({"variable": f"error absoluto {modelo}", "n": r["n"],
                      "moran_I": round(I, 4), "moran_p": p_sim,
                      "rho0": round(r["rho0"], 4), "rango_m": round(r["rango_m"], 1),
                      "n_efectivo": round(r["n_eff"], 1),
                      "pct_del_nominal": round(100 * r["n_eff"] / r["n"], 1)})

    # -- 2. tamano efectivo de la diferencia entre modelos -------------------
    modelos = list(errores)
    pares = list(itertools.combinations(modelos, 2))
    if args.pares:
        pedidos = {p.replace(" ", "") for p in args.pares}
        pares = [p for p in pares if f"{p[0]}-{p[1]}" in pedidos or f"{p[1]}-{p[0]}" in pedidos]

    pruebas = []
    for a, b in pares:
        ea = errores[a].reindex(predios_te)["error_abs"].values
        eb = errores[b].reindex(predios_te)["error_abs"].values
        ok = np.isfinite(ea) & np.isfinite(eb)
        d = ea[ok] - eb[ok]
        c = coords_te[ok]
        n = len(d)
        I, _, p_moran, _ = moran_i(d, c)
        r = n_efectivo(c, d)
        neff = r["n_eff"]
        media, sd = float(d.mean()), float(d.std(ddof=1))
        t_nom = media / (sd / np.sqrt(n))
        p_nom = 2 * stats.t.sf(abs(t_nom), df=n - 1)
        t_eff = media / (sd / np.sqrt(max(neff, 2)))
        p_eff = 2 * stats.t.sf(abs(t_eff), df=max(neff - 1, 1))
        # unidad espacial: media de la diferencia por bloque y por region
        por_bloque = pd.Series(d).groupby(pd.Series(bloques_te[ok])).mean().values
        tb = stats.ttest_1samp(por_bloque, 0.0)
        por_region = pd.Series(d).groupby(pd.Series(regiones_te[ok])).mean().values
        trg = stats.ttest_1samp(por_region, 0.0)
        pruebas.append({
            "modelo_a": a, "modelo_b": b,
            "dif_media_MAE": round(media, 3),
            "n_nominal": n, "p_nominal": round(float(p_nom), 5),
            "moran_I_diferencia": round(I, 4), "moran_p": p_moran,
            "n_efectivo": round(neff, 1),
            "reduccion_pct": round(100 * (1 - neff / n), 1),
            "p_con_n_efectivo": round(float(p_eff), 5),
            "n_bloques": len(por_bloque), "p_por_bloque": round(float(tb.pvalue), 5),
            "n_regiones": len(por_region), "p_por_region": round(float(trg.pvalue), 5),
        })

    tab_n = pd.DataFrame(filas)
    tab_p = pd.DataFrame(pruebas)
    for col in ("p_nominal", "p_con_n_efectivo", "p_por_bloque", "p_por_region"):
        rechaza = tab_p[col] < 0.05
        tab_p[f"significativo_{col.replace('p_', '')}"] = rechaza

    # -- 3. localizaciones independientes ------------------------------------
    indep = pd.DataFrame([
        {"criterio": "separacion > rango de residuales (2530 m)",
         "n_localizaciones": conjunto_independiente(coords_te, RANGO_RESIDUAL)},
        {"criterio": "separacion > rango del valor (5621,8 m)",
         "n_localizaciones": conjunto_independiente(coords_te, RANGO_OBJETIVO)},
        {"criterio": "bloques espaciales", "n_localizaciones": len(set(bloques_te.tolist()))},
        {"criterio": "regiones de la validacion externa", "n_localizaciones": len(set(regiones_te.tolist()))},
        {"criterio": "predios (nominal)", "n_localizaciones": len(predios_te)},
    ])

    p1 = salida("obs6", "n_efectivo_por_modelo.csv"); tab_n.to_csv(p1, index=False)
    p2 = salida("obs6", "pruebas_pareadas_ajustadas.csv"); tab_p.to_csv(p2, index=False)
    p3 = salida("obs6", "localizaciones_independientes.csv"); indep.to_csv(p3, index=False)

    cols = ["modelo_a", "modelo_b", "dif_media_MAE", "n_nominal", "p_nominal",
            "n_efectivo", "reduccion_pct", "p_con_n_efectivo", "p_por_bloque", "p_por_region"]
    pr("\n" + tabla_md(tab_p[cols]))
    pr("\n" + tabla_md(indep))

    cambia = tab_p[(tab_p["p_nominal"] < 0.05) & (tab_p["p_con_n_efectivo"] >= 0.05)]
    md = ["# Observacion 1.6 -- tamano efectivo de la muestra", "",
          f"Conjunto de prueba: {len(predios_te)} predios. Ese numero no es el numero de",
          "observaciones independientes disponibles para inferir diferencias de",
          "generalizacion espacial.", "",
          "## Cuantas observaciones independientes hay realmente", "", tabla_md(indep), "",
          "## Autocorrelacion del error y tamano efectivo", "", tabla_md(tab_n), "",
          "## Pruebas pareadas bajo los tres supuestos", "", tabla_md(tab_p[cols]), ""]
    if len(cambia):
        md += ["## Comparaciones que dejan de ser significativas al corregir", ""]
        for _, r in cambia.iterrows():
            md.append(f"- {r['modelo_a']} frente a {r['modelo_b']}: "
                      f"p pasa de {r['p_nominal']:.4f} a {r['p_con_n_efectivo']:.4f} "
                      f"al usar n efectivo = {r['n_efectivo']:.0f} en lugar de {r['n_nominal']}.")
        md.append("")
    md += ["## Como redactarlo", "",
           "Formula sugerida para el documento: los 1011 predios de prueba equivalen, por la",
           "dependencia espacial del error, a un numero mucho menor de observaciones",
           "independientes; y cuando lo que se quiere inferir es generalizacion a zonas",
           "nuevas, la unidad de analisis no es el predio sino la region, de las que hay",
           "cinco o diez. Las pruebas pareadas sobre predios individuales deben leerse como",
           "descriptivas y no como inferencia sobre capacidad de generalizacion espacial.", ""]
    p4 = salida("obs6", "tamano_efectivo.md")
    p4.write_text("\n".join(md), encoding="utf-8")
    pr(f"\n[csv] {p1}\n[csv] {p2}\n[csv] {p3}\n[md]  {p4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
