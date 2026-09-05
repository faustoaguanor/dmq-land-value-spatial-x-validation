"""
metricas.py -- metricas, smearing de Duan e I de Moran, identicas al protocolo
del repositorio (mismas formulas que modelos/*/*_log.py y analisis/).
"""
from __future__ import annotations
import numpy as np

try:
    from libpysal.weights import KNN as KNNWeights
    LIBPYSAL = True
except ImportError:                                       # pragma: no cover
    LIBPYSAL = False

MORAN_K = 8
MORAN_NPERM = 999


def smearing(y_tr_log: np.ndarray, pred_tr_log: np.ndarray) -> float:
    """Factor de Duan s_M = mean(exp(residuales de entrenamiento)). Fold-especifico:
    se calcula con el entrenamiento de cada particion, nunca con el conjunto evaluado."""
    return float(np.mean(np.exp(np.asarray(y_tr_log) - np.asarray(pred_tr_log))))


def metricas(y_ori: np.ndarray, pred_log: np.ndarray, y_log: np.ndarray,
             s_M: float = 1.0) -> dict:
    yp = np.exp(pred_log) * s_M
    e = y_ori - yp
    mae = float(np.mean(np.abs(e)))
    rmse = float(np.sqrt(np.mean(e ** 2)))
    mape = float(np.mean(np.abs(e / y_ori)) * 100)
    ss_t = float(np.sum((y_ori - y_ori.mean()) ** 2))
    r2 = float(1 - np.sum(e ** 2) / ss_t) if ss_t > 0 else float("nan")
    el = y_log - pred_log
    ss_tl = float(np.sum((y_log - y_log.mean()) ** 2))
    r2l = float(1 - np.sum(el ** 2) / ss_tl) if ss_tl > 0 else float("nan")
    return {"MAE": round(mae, 4), "RMSE": round(rmse, 4), "MAPE": round(mape, 4),
            "R2": round(r2, 4), "R2_log": round(r2l, 4),
            "smearing_factor": round(float(s_M), 6)}


def moran_i(valores: np.ndarray, coords: np.ndarray, k: int = MORAN_K,
            n_perm: int = MORAN_NPERM, seed: int = 42):
    """I de Moran con pesos KNN fila-estandarizados y p-valor por permutacion
    (Cliff & Ord 1981; Anselin 1995). Devuelve (I, E[I], p_sim, z_sim)."""
    if not LIBPYSAL:
        return float("nan"), float("nan"), float("nan"), float("nan")
    w = KNNWeights.from_array(coords, k=k)
    w.transform = "r"
    z = valores - valores.mean()
    den = float(z @ z)
    I_obs = float((z @ (w.sparse @ z)) / den)
    rng = np.random.default_rng(seed)
    Ip = np.empty(n_perm)
    for b in range(n_perm):
        zp = rng.permutation(z)
        Ip[b] = (zp @ (w.sparse @ zp)) / den
    p_sim = (int(np.sum(Ip >= I_obs)) + 1) / (n_perm + 1)
    sd = Ip.std(ddof=1)
    return I_obs, -1 / (len(valores) - 1), float(p_sim), float((I_obs - Ip.mean()) / sd) if sd > 0 else float("nan")
