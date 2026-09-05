# -*- coding: utf-8 -*-
"""
graficos_resultados.py
======================
Rehace las tres primeras figuras del capitulo de resultados. Sustituye a lo
que generaban generate_figures.py y fig4_replicas_stability.py, cuyas salidas
la revision rechazo.

Que fallaba.

Nomenclatura retirada, en las tres. Los titulos y las leyendas decian todavia
"holdout 20%", "conjunto de desarrollo", "particion reservada",
"RandomKFold", "SpatialBlock", "RF" y "seed42", terminos que el documento ya
no usa. Tambien "R2" y "USD/m2" en vez de R al cuadrado y metro cuadrado.

Titulos que repiten el pie. La primera llevaba un encabezado de dos lineas
con el area de estudio, la variable y el numero de observaciones, todo lo
cual ya esta en el pie de figura y en el texto.

Moran repetido. La primera figura incluia un panel del indice de Moran que
duplica la figura de la seccion de autocorrelacion, donde el indice se
explica. Sale de aqui.

La tercera comparaba dos modelos con barras que arrancan en cero, de modo que
noventa y dos de los noventa y ocho USD/m2 de altura no aportan nada y las
diferencias, que son de tres o cuatro, quedan invisibles. Pasa a mostrar las
diez ejecuciones de cada modelo una por una, que es de lo que trata la
seccion, e incluye a Random Forest, que faltaba pese a figurar en la tabla.

Salidas: g1_interpolacion.png, g2_aleatoria_vs_bloques.png, g3_semillas.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# --- formato numerico espanol (anadido para alinear con el documento) ---
import locale as _loc
import matplotlib as _mpl
try:
    _loc.setlocale(_loc.LC_NUMERIC, "es_ES.UTF-8")
    _mpl.rcParams["axes.formatter.use_locale"] = True
except Exception:
    pass


def _es(txt):
    """Coma decimal y sin separador de millar."""
    return str(txt).replace(",", "").replace(".", ",")
# --- fin del bloque anadido ---


ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).parent
ANL = ROOT / "analisis" / "output_log"
MOD = ROOT / "modelos"

plt.rcParams.update({"font.family": "serif", "font.size": 11,
                     "figure.dpi": 150, "axes.axisbelow": True})

COLOR = {"Random Forest": "#e08214", "SANNWR-adaptado": "#4b9b5f", "GWR": "#6b7c8c",
         "GNNWR": "#3d85c6", "OLS": "#8a939b"}
# La columna del gpkg conserva el nombre historico del modelo.
ALIAS = {"RF": "Random Forest", "GWR-27": "GWR", "SANNWR": "SANNWR-adaptado"}


def guardar(fig, nombre):
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{nombre}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {nombre}.png / .pdf")


def limpiar(ax, eje_x):
    ax.set_xlabel(eje_x, fontsize=10.5)
    ax.grid(axis="x", color="#dfe4e8", linewidth=0.7, linestyle="-")
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#8d9aa4")
    ax.tick_params(labelsize=10.5, length=0)


# ───────────────────────── 1. conjunto de prueba ──────────────────────────

def g1_interpolacion():
    """RMSE y R al cuadrado sobre el conjunto de prueba."""
    d = pd.read_csv(ANL / "comparativo_holdout_smeared.csv")
    d["modelo"] = d.modelo.replace(ALIAS)
    d = d[d.modelo.isin(COLOR)][["modelo", "RMSE_smeared", "R2_smeared"]]

    # Random Forest no esta en ese comparativo: los baselines tabulares se
    # calcularon aparte y guardan sus metricas ya corregidas.
    rf = pd.read_csv(MOD / "baselines/output_log/rf_log_holdout.csv").iloc[0]
    d = pd.concat([d, pd.DataFrame([{"modelo": "Random Forest",
                                     "RMSE_smeared": rf.RMSE,
                                     "R2_smeared": rf.R2}])])
    faltan = set(COLOR) - set(d.modelo)
    assert not faltan, f"faltan modelos en la figura: {faltan}"
    d = d.sort_values("RMSE_smeared", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5))
    for ax, (col, eje, fmt) in zip(axes, [
            ("RMSE_smeared", "RMSE (USD/m$^{2}$)", "{:.1f}"),
            ("R2_smeared", "R$^{2}$", "{:.3f}")]):
        y = np.arange(len(d))
        ax.barh(y, d[col], color=[COLOR[m] for m in d.modelo], height=0.68,
                edgecolor="white", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels(d.modelo)
        for i, v in enumerate(d[col]):
            ax.text(v + d[col].max() * 0.015, i, _es(fmt.format(v)), va="center",
                    fontsize=10, color="#3d4852")
        ax.set_xlim(0, d[col].max() * 1.16)
        limpiar(ax, eje)
    fig.subplots_adjust(wspace=0.32)
    guardar(fig, "g1_interpolacion")


# ──────────────────── 2. reparto aleatorio frente a bloques ───────────────

def _por_bloque():
    """RMSE medio entre los cinco bloques, promediando antes las semillas."""
    F = {"GNNWR": MOD / "gnnwr/output_log/gnnwr_log_cv_replicas.csv",
         "SANNWR-adaptado": MOD / "sannwr/output_log_real/sannwr_real_log_cv_replicas.csv",
         "Random Forest": MOD / "baselines/output_log_replicas/baseline_replicas_fold.csv",
         "GWR": MOD / "gwr/output_log_27vars/gwr27_log_results.csv",
         "OLS": MOD / "ols/output_log/ols_log_results.csv"}
    fuera = {}
    for nom, ruta in F.items():
        d = pd.read_csv(ruta)
        if "modelo" in d.columns and d.modelo.nunique() > 1:
            d = d[d.modelo.str.contains("RF|Random", case=False, na=False)]
        for est in ("RandomKFold", "SpatialBlock"):
            s = d[d.estrategia == est]
            if "seed" in s.columns:
                s = s.groupby("fold", as_index=False)["RMSE"].mean()
            fuera[(nom, est)] = s.RMSE.mean()
    return fuera


def _dispersion_cv():
    """Desviacion entre las cinco particiones, en los dos esquemas cruzados.

    Es la misma magnitud en ambos: cuanto cambia el error segun que parte de
    la muestra toque dejar fuera. Lo unico que difiere es como se forman esas
    partes, al azar o por zonas contiguas.
    """
    F = {"GNNWR": MOD / "gnnwr/output_log/gnnwr_log_cv_replicas.csv",
         "SANNWR-adaptado": MOD / "sannwr/output_log_real/sannwr_real_log_cv_replicas.csv",
         "Random Forest": MOD / "baselines/output_log_replicas/baseline_replicas_fold.csv",
         "GWR": MOD / "gwr/output_log_27vars/gwr27_log_results.csv",
         "OLS": MOD / "ols/output_log/ols_log_results.csv"}
    fuera = {}
    for nom, ruta in F.items():
        d = pd.read_csv(ruta)
        if "modelo" in d.columns and d.modelo.nunique() > 1:
            d = d[d.modelo.str.contains("RF|Random", case=False, na=False)]
        for est in ("RandomKFold", "SpatialBlock"):
            s = d[d.estrategia == est]
            if "seed" in s.columns:
                s = s.groupby("fold", as_index=False)["RMSE"].mean()
            fuera[(nom, est)] = (s.RMSE.mean(), s.RMSE.std())
    return fuera


def g2_tres_esquemas():
    """RMSE bajo los tres esquemas, con la dispersion entre particiones.

    Barras agrupadas y no un grafico de pendientes, porque asi cabe OLS sin
    comprimir a los demas y, sobre todo, porque admite las barras de error:
    la dispersion entre particiones es la magnitud con la que el capitulo
    concluye, y un grafico de pendientes no la muestra.
    """
    v = _dispersion_cv()

    d = pd.read_csv(ANL / "comparativo_holdout_smeared.csv")
    d["modelo"] = d.modelo.replace(ALIAS)
    prueba = dict(zip(d.modelo, d.RMSE_smeared))
    prueba["Random Forest"] = pd.read_csv(
        MOD / "baselines/output_log/rf_log_holdout.csv").RMSE.iloc[0]
    faltan = set(COLOR) - set(prueba)
    assert not faltan, f"faltan modelos en la figura: {faltan}"

    modelos = sorted(COLOR, key=lambda m: prueba[m])
    ESQUEMAS = [("Conjunto de prueba", "#9fc3dc", None),
                ("Validación cruzada aleatoria", "#3d85c6", "RandomKFold"),
                ("Bloques espaciales", "#e08214", "SpatialBlock")]

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    x = np.arange(len(modelos))
    ancho = 0.26
    for k, (etiqueta, color, est) in enumerate(ESQUEMAS):
        pos = x + (k - 1) * ancho
        if est is None:
            alturas = [prueba[m] for m in modelos]
            errores = None
        else:
            alturas = [v[(m, est)][0] for m in modelos]
            errores = [v[(m, est)][1] for m in modelos]
        ax.bar(pos, alturas, ancho * 0.92, color=color, label=etiqueta,
               edgecolor="white", linewidth=0.8, zorder=3)
        if errores:
            ax.errorbar(pos, alturas, yerr=errores, fmt="none", ecolor="#3d4852",
                        elinewidth=0.9, capsize=3.5, capthick=0.9, zorder=4)
        for xi, h in zip(pos, alturas):
            ax.text(xi, h - 5, f"{h:.0f}", ha="center", va="top", fontsize=8.5,
                    color="white", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(modelos, fontsize=10.5)
    ax.set_ylabel("RMSE (USD/m$^{2}$)", fontsize=10.5)
    ax.set_ylim(0, 230)
    ax.grid(axis="y", color="#e6eaed", linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#8d9aa4")
    ax.tick_params(labelsize=10, length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=3,
              frameon=False, fontsize=9.5)
    ax.text(0.995, 0.955, "las barras de error abarcan una desviación entre "
                          "las cinco particiones",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            color="#7d8991", style="italic")
    guardar(fig, "g2_tres_esquemas")


# ──────────────────────────── 3. semillas ─────────────────────────────────

def g3_semillas():
    """Las diez ejecuciones de cada modelo estocastico, una por una."""
    F = {"Random Forest": (MOD / "baselines/output_log_replicas"
                                 "/baseline_replicas_holdout_fold.csv"),
         "SANNWR-adaptado": MOD / "sannwr/output_log_real/sannwr_real_log_replicas.csv",
         "GNNWR": MOD / "gnnwr/output_log/gnnwr_log_replicas.csv"}

    fig, ax = plt.subplots(figsize=(9.2, 3.4))
    for i, (nom, ruta) in enumerate(F.items()):
        d = pd.read_csv(ruta)
        if "modelo" in d.columns and d.modelo.nunique() > 1:
            d = d[d.modelo.str.contains("RF|Random", case=False, na=False)]
        r = d.RMSE.values
        sd = r.std(ddof=1)   # como en la tabla: desviacion muestral
        disp = np.random.default_rng(0).uniform(-0.13, 0.13, len(r))
        ax.scatter(r, i + disp, s=42, color=COLOR[nom], alpha=0.70,
                   edgecolor="white", linewidth=0.7, zorder=3)
        ax.plot([r.mean() - sd, r.mean() + sd], [i, i],
                color=COLOR[nom], linewidth=2.6, alpha=0.45, zorder=2)
        ax.scatter(r.mean(), i, marker="|", s=340, color="#2b2b2b",
                   linewidth=1.7, zorder=4)
        ax.text(r.mean(), i + 0.34, _es(f"{r.mean():.1f}") + " $\\pm$ " + _es(f"{sd:.1f}"),
                ha="center", fontsize=10, color="#3d4852")

    ax.set_yticks(range(len(F)))
    ax.set_yticklabels(list(F))
    ax.set_ylim(-0.6, len(F) - 0.35)
    ax.set_xlim(70, 110)
    limpiar(ax, "RMSE sobre el conjunto de prueba (USD/m$^{2}$)")
    ax.text(0.99, 0.04, "cada punto es un entrenamiento con otra semilla",
            transform=ax.transAxes, ha="right", fontsize=9.5, color="#6b7c8c",
            style="italic")
    guardar(fig, "g3_semillas")


# ──────────────────────────── 4. Moran ───────────────────────────────────

def g4_moran():
    """Indice de Moran sobre los residuos, con la referencia de ausencia de
    autocorrelacion marcada en el cero."""
    # Este archivo si trae los cinco modelos, incluido Random Forest.
    d = pd.read_csv(ANL / "moran_holdout_significancia.csv")
    d["modelo"] = d.modelo.replace(ALIAS)
    d = d[d.modelo.isin(COLOR)].sort_values("I")
    faltan = set(COLOR) - set(d.modelo)
    assert not faltan, f"faltan modelos en la figura: {faltan}"
    col, nombre = "I", "modelo"

    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    y = np.arange(len(d))
    ax.barh(y, d[col], color=[COLOR[m] for m in d[nombre]], height=0.66,
            edgecolor="white", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d[nombre])
    for i, v in enumerate(d[col]):
        ax.text(v + 0.006, i, f"{v:.3f}", va="center", fontsize=10,
                color="#3d4852")
    ax.set_xlim(0, d[col].max() * 1.14)
    limpiar(ax, "Índice de Moran sobre los residuos")
    ax.text(0.99, 0.06, "0 indicaría residuos sin estructura espacial",
            transform=ax.transAxes, ha="right", fontsize=9.5,
            color="#6b7c8c", style="italic")
    guardar(fig, "g4_moran")


def main():
    g1_interpolacion()
    g2_tres_esquemas()
    g3_semillas()
    g4_moran()


if __name__ == "__main__":
    main()
