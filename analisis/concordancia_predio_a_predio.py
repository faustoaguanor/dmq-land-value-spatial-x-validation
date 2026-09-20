"""Desacuerdo predio a predio entre dos modelos equivalentes en el agregado.

Una prueba de equivalencia sobre el MAE dice que dos modelos no se separan en
promedio. No dice que valoren igual la misma parcela, y para el uso catastral
esa es la pregunta pertinente: lo que se factura es el predio, no la media.

GWR y GNNWR son la pareja con el margen mas estrecho sobre el conjunto de
prueba, 3,4 USD/m2 tras la reejecucion de GNNWR del 2026-09-20, y su diferencia
de MAE roza la significancia. Este script mide cuanto se separan cuando se
comparan sus 1011 predicciones una a una.

Alimenta el parrafo de la Seccion 5.2.2 que sigue a la Tabla 5.5.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Factores de smearing de Duan, los mismos que usa tost_equivalencia.py.
MODELOS = {
    "GWR":   ("modelos/gwr/output_log_27vars/gwr27_log_predictions.csv", 1.026509),
    "GNNWR": ("modelos/gnnwr/output_log/gnnwr_log_predictions.csv",      1.031205),
}


def cargar(ruta, smearing):
    d = pd.read_csv(ROOT / ruta)
    d = d[d["split"] == "test"].copy()
    d["predio_join"] = d["predio_join"].astype(int)   # contrato de clave canonica
    d["pred"] = np.exp(d["y_pred_log"]) * smearing
    d["obs"] = np.exp(d["y_obs_log"])
    return d[["predio_join", "pred", "obs"]]


(a_nom, b_nom) = MODELOS.keys()
a = cargar(*MODELOS[a_nom])
b = cargar(*MODELOS[b_nom])
m = a.merge(b, on="predio_join", suffixes=("_a", "_b"))

dif = (m["pred_a"] - m["pred_b"]).abs()
rel = dif / m["obs_a"] * 100

print(f"predios pareados: {len(m)}")
print(f"MAE {a_nom:<6} {(m['pred_a'] - m['obs_a']).abs().mean():.2f}")
print(f"MAE {b_nom:<6} {(m['pred_b'] - m['obs_a']).abs().mean():.2f}")
print(f"\nDesacuerdo entre {a_nom} y {b_nom} en el mismo predio (USD/m2):")
print(f"  mediana       {dif.median():.1f}   ({rel.median():.1f}% del valor observado)")
print(f"  media         {dif.mean():.1f}")
print(f"  percentil 90  {dif.quantile(.9):.1f}")
print(f"  maximo        {dif.max():.1f}")
for t in (10, 25, 50):
    print(f"  difieren en mas de {t:>2} : {(dif > t).mean() * 100:.1f}% de los predios")
