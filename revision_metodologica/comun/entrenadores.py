"""
entrenadores.py -- los cinco modelos con configuracion CONGELADA.

Un unico punto de entrada, `entrenar`, que recibe indices de entrenamiento y de
evaluacion sobre el conjunto completo y devuelve predicciones en escala log mas
el factor de smearing calculado con los residuales de entrenamiento de esa misma
particion. Todos los experimentos de esta revision (validacion espacial externa,
imputacion dentro del pliegue) usan este modulo, de modo que lo unico que cambia
entre experimentos es la particion o la matriz de covariables, nunca el estimador.

Configuracion congelada = la de la version defendida de la tesis:

  OLS              minimos cuadrados sobre las 30 columnas estandarizadas
  GWR              Ridge con intercepto no penalizado; bandwidth bisquare
                   adaptativo por AICc dentro del entrenamiento; lambda por
                   validacion cruzada espacial anidada (modelos/gwr/gwr_core.py)
  GNNWR            SWNN [2048,1024,512,256,64], PReLU, dropout 0.2, BatchNorm,
                   Adadelta lr 0.2, 1000 epocas, paciencia 200, lote 64
  SANNWR-adaptado  identica a GNNWR salvo la entrada: distancia hibrida
                   0.5*espacial + 0.5*atributiva, ambas estandarizadas con el
                   entrenamiento (peso fijo, no aprendido: de ahi "adaptado")
  SANNWR-original  el diseno publicado por Ni et al. (2022): un SAPDNN (red
                   2 -> h -> 1, compartida entre pares) aprende a fundir la
                   distancia espacial y la atributiva en una sola metrica, que
                   es la que recibe la SWNN. Todo se entrena de extremo a
                   extremo. Misma arquitectura que
                   modelos/sannwr/sannwr_sapdnn_holdout.py del repositorio,
                   ahora bajo el protocolo completo y no solo el conjunto de prueba
  RF               RandomForestRegressor(n_estimators=300), sin coordenadas
  HGB              HistGradientBoostingRegressor, sin coordenadas (anexo de la tesis)

Con `ajustar=True`, RF y HGB eligen sus hiperparametros por validacion cruzada
espacial anidada dentro del entrenamiento de cada particion (comun/ajuste.py).
Es la correccion a la observacion de que RF corrio con los valores por defecto
mientras GWR si ajustaba los suyos.

Nada de lo que hay aqui se ajusta mirando el conjunto que se evalua.
"""
from __future__ import annotations
import random
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from . import nombres as N
from .metricas import smearing
from .rutas import pr

from gwr_core import (add_intercept, select_bw, fit_gwr_ridge, predict_gwr,   # noqa: E402
                      select_lambda, LAMBDA_RIDGE, BW_FALLBACK)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# La seleccion de bandwidth de mgwr avisa de matrices locales mal condicionadas en
# cada iteracion; es el mismo aviso que silencia modelos/gwr/gwr_log_27vars.py y
# solo ensucia el registro de una corrida de horas. El diagnostico de condicion
# numerica esta en gwr_core.local_condition_diagnostics, que si se reporta.
try:
    from scipy.linalg import LinAlgWarning
    warnings.filterwarnings("ignore", category=LinAlgWarning)
except ImportError:                                                   # pragma: no cover
    pass
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"(mgwr|spglm)\..*")

# -- hiperparametros congelados de las redes ---------------------------------
DENSE_LAYERS = [2048, 1024, 512, 256, 64]
DROP_OUT = 0.2
BATCH_NORM = True
N_EPOCHS = 1000
PATIENCE = 200
BATCH_SIZE = 64
START_LR = 0.2
WEIGHT_DECAY = 1e-3
GRAD_CLIP = 5.0
VAL_FRAC = 0.10
ALPHA_SANNWR = 0.5          # peso fijo espacial/atributivo de la adaptacion
SAPDNN_HIDDEN = 4           # capa oculta del SAPDNN del SANNWR publicado
RF_TREES = 300              # por defecto declarado de la tesis
HGB_ITER = 400

# modo rapido: solo para pruebas de humo, NUNCA para cifras que se reporten
EPOCHS_RAPIDO = 150
PATIENCE_RAPIDO = 30


def _amortiguar_extremos(pred_log: np.ndarray, rango_log_dataset: tuple):
    """Salvaguarda numerica, SOLO de esta revision (no toca gwr_core.py canonico).

    Ante extrapolacion geografica real, un punto de test puede caer en una zona
    donde la matriz local de GWR queda casi singular; el Ridge no siempre lo
    evita. El sintoma es una prediccion en escala log absurda (ej. 16.9 cuando el
    valor mas caro observado en las 5051 propiedades del estudio es 7.73, unos
    2280 USD/m2), que al destransformar con exp() da cifras en millones y
    arruina cualquier promedio por region o pliegue.

    El limite es el rango de precios REALMENTE OBSERVADO en el universo completo
    del estudio (conj.y_log.min/max), sin margen: predecir fuera de lo que el
    mercado del DMQ ha mostrado alguna vez no es una prediccion fisicamente
    significativa, es un artefacto numerico. Un margen mayor (probado primero
    con 4 unidades log) seguia dejando pasar predicciones de cientos de miles
    de USD/m2: la correccion tiene que anclarse en el precio mas caro real, no
    en un multiplo arbitrario de el.

    Se cuenta cuantas veces se dispara y se reporta en extras: la correccion es
    visible, no silenciosa."""
    lo, hi = float(rango_log_dataset[0]), float(rango_log_dataset[1])
    n_clip = int(np.sum((pred_log < lo) | (pred_log > hi)))
    if n_clip:
        pred_log = np.clip(pred_log, lo, hi)
    return pred_log, n_clip


def fijar_semilla(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# -- red ---------------------------------------------------------------------
class SWNN(nn.Module):
    def __init__(self, insize, outsize, dense_layers, drop_out=DROP_OUT, batch_norm=BATCH_NORM):
        super().__init__()
        act = nn.PReLU(init=0.1)
        capas, last = [], insize
        for h in dense_layers:
            capas += [nn.Linear(last, h)]
            if batch_norm:
                capas += [nn.BatchNorm1d(h)]
            capas += [act, nn.Dropout(drop_out)]
            last = h
        capas += [nn.Linear(last, outsize)]
        self.fc = nn.Sequential(*capas)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0, mode="fan_in")
                if m.bias is not None:
                    m.bias.data.fill_(0.0)

    def forward(self, x):
        return self.fc(x)


class RedPonderada(nn.Module):
    """GNNWR / SANNWR-adaptado: y = sum_k w_k(d) * beta_k^OLS * x_k.

    Los beta OLS entran congelados (requires_grad=False); lo que aprende la red
    son los multiplicadores locales w_k."""

    def __init__(self, n_train, n_features, ols_coeff, dense_layers=DENSE_LAYERS,
                 drop_out=DROP_OUT, batch_norm=BATCH_NORM):
        super().__init__()
        self.swnn = SWNN(n_train, n_features, dense_layers, drop_out, batch_norm)
        self.out = nn.Linear(n_features, 1, bias=False)
        self.out.weight = nn.Parameter(
            torch.tensor(np.asarray(ols_coeff).reshape(1, -1), dtype=torch.float32),
            requires_grad=False)

    def forward(self, dis, x):
        return self.out(self.swnn(dis) * x)


class RedPonderadaSAPDNN(nn.Module):
    """SANNWR publicado (Ni et al. 2022): SAPDNN(d_espacial, d_atributiva) -> SWNN -> OLS.

    El SAPDNN es una red pequena compartida entre todos los pares que recibe las
    dos distancias de un par y devuelve una sola: la metrica espacio-atributiva
    unificada. Es el componente que la adaptacion sustituye por 0,5/0,5, y aqui
    se entrena junto con el resto. Misma definicion que la del repositorio en
    modelos/sannwr/sannwr_sapdnn_holdout.py."""

    def __init__(self, n_train, n_features, ols_coeff, hidden=SAPDNN_HIDDEN,
                 dense_layers=DENSE_LAYERS, drop_out=DROP_OUT, batch_norm=BATCH_NORM):
        super().__init__()
        self.sapdnn = nn.Sequential(nn.Linear(2, hidden), nn.PReLU(init=0.1),
                                    nn.Linear(hidden, 1), nn.PReLU(init=0.1))
        self.swnn = SWNN(n_train, n_features, dense_layers, drop_out, batch_norm)
        self.out = nn.Linear(n_features, 1, bias=False)
        self.out.weight = nn.Parameter(
            torch.tensor(np.asarray(ols_coeff).reshape(1, -1), dtype=torch.float32),
            requires_grad=False)
        for m in self.sapdnn.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0, mode="fan_in")
                m.bias.data.fill_(0.0)

    def forward(self, dis, x):
        # dis: (B, n_train, 2) con la distancia espacial y la atributiva del par
        fundida = self.sapdnn(dis).squeeze(-1)            # (B, n_train)
        return self.out(self.swnn(fundida) * x)


def _loader(dis, X, y, bs, shuf):
    ds = TensorDataset(torch.tensor(dis, dtype=torch.float32),
                       torch.tensor(X, dtype=torch.float32),
                       torch.tensor(np.asarray(y).reshape(-1, 1), dtype=torch.float32))
    return DataLoader(ds, batch_size=bs, shuffle=shuf, drop_last=shuf)


def _epoca(model, loader, opt):
    entrenando = opt is not None
    model.train(entrenando)
    tot, n = 0.0, 0
    ctx = torch.enable_grad() if entrenando else torch.no_grad()
    with ctx:
        for dis, x, y in loader:
            dis, x, y = dis.to(DEVICE), x.to(DEVICE), y.to(DEVICE)
            yh = model(dis, x)
            loss = F.mse_loss(yh, y)
            if entrenando:
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP)
                opt.step()
            tot += loss.item() * len(y)
            n += len(y)
    return tot / max(n, 1)


def _entrenar_red(model, tr_ld, val_ld, ruta, epocas, paciencia, verboso=True, lr=START_LR):
    opt = torch.optim.Adadelta(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(opt, T_0=100, T_mult=3, eta_min=0.01)
    mejor, pac, ep_mejor = float("inf"), 0, 0
    for ep in range(1, epocas + 1):
        tl = _epoca(model, tr_ld, opt)
        vl = _epoca(model, val_ld, None)
        sched.step()
        if verboso and (ep % 100 == 0 or ep == 1):
            pr(f"      ep {ep:4d}  train={tl:.4f}  val={vl:.4f}")
        if vl < mejor:
            mejor, pac, ep_mejor = vl, 0, ep
            torch.save(model.state_dict(), ruta)
        else:
            pac += 1
            if pac >= paciencia:
                if verboso:
                    pr(f"      parada temprana en ep {ep} (mejor {ep_mejor})")
                break
    model.load_state_dict(torch.load(ruta, map_location=DEVICE, weights_only=True))
    return {"epoca_mejor": ep_mejor, "val_loss": round(float(mejor), 6)}


def _predecir_red(model, loader):
    model.eval()
    ps = []
    with torch.no_grad():
        for dis, x, _ in loader:
            ps.append(model(dis.to(DEVICE), x.to(DEVICE)).cpu().numpy().flatten())
    return np.concatenate(ps)


def _distancias(modelo, ctr, cte, Xtr, Xte):
    """Entrada de la SWNN.

    GNNWR           : distancia espacial estandarizada, forma (B, n_train).
    SANNWR-adaptado : combinacion fija 0,5/0,5 de la espacial y la atributiva,
                      cada una estandarizada con los pares de entrenamiento,
                      forma (B, n_train).
    SANNWR-original : las dos distancias sin fundir, forma (B, n_train, 2); la
                      fusion la aprende el SAPDNN dentro del modelo."""
    if modelo == N.GNNWR:
        sc = StandardScaler().fit(cdist(ctr, ctr))
        return (sc.transform(cdist(ctr, ctr)).astype(np.float32),
                sc.transform(cdist(cte, ctr)).astype(np.float32))
    sc_sp = StandardScaler().fit(cdist(ctr, ctr))
    sc_at = StandardScaler().fit(cdist(Xtr, Xtr))
    sp_tr, at_tr = sc_sp.transform(cdist(ctr, ctr)), sc_at.transform(cdist(Xtr, Xtr))
    sp_te, at_te = sc_sp.transform(cdist(cte, ctr)), sc_at.transform(cdist(Xte, Xtr))
    if modelo == N.SANNWR_ORIG:
        return (np.stack([sp_tr, at_tr], axis=-1).astype(np.float32),
                np.stack([sp_te, at_te], axis=-1).astype(np.float32))
    a = ALPHA_SANNWR
    return ((a * sp_tr + (1 - a) * at_tr).astype(np.float32),
            (a * sp_te + (1 - a) * at_te).astype(np.float32))


# -- entrada unica -----------------------------------------------------------
@dataclass
class Resultado:
    modelo: str
    pred_log_test: np.ndarray
    pred_log_train: np.ndarray
    s_M: float
    extras: dict
    # Solo si se pide devolver_predictor=True: funcion (X_sin_escalar, coords) -> log(prediccion).
    # La usa el analisis de importancia por permutacion, que necesita repredecir
    # con las covariables alteradas sin volver a entrenar.
    predecir: object = None


def construir_arbol(modelo: str, conf: dict, semilla: int):
    """RF o HGB con la configuracion dada; lo que falte, por defecto declarado."""
    c = dict(conf or {})
    if modelo == N.RF:
        return RandomForestRegressor(
            n_estimators=c.get("n_estimators", RF_TREES),
            max_features=c.get("max_features", 1.0),
            min_samples_leaf=c.get("min_samples_leaf", 1),
            max_depth=c.get("max_depth", None),
            n_jobs=-1, random_state=semilla)
    return HistGradientBoostingRegressor(
        max_iter=c.get("max_iter", HGB_ITER),
        learning_rate=c.get("learning_rate", 0.05),
        max_leaf_nodes=c.get("max_leaf_nodes", 31),
        min_samples_leaf=c.get("min_samples_leaf", 20),
        l2_regularization=c.get("l2_regularization", 0.0),
        max_depth=None, random_state=semilla)


def entrenar(conj, idx_tr, idx_te, modelo: str, semilla: int = 42,
             etiqueta: str = "run", rapido: bool = False, verboso: bool = True,
             hiper: dict | None = None, ajustar: bool = False,
             devolver_predictor: bool = False) -> Resultado:
    """Entrena `modelo` con las filas idx_tr y predice sobre idx_te.

    conj    : comun.datos.Conjunto (puede venir con covariables re-imputadas)
    idx_tr  : indices de entrenamiento (posicionales en el conjunto completo)
    idx_te  : indices a predecir
    semilla : gobierna la inicializacion de la red, el reparto de validacion y RF
    hiper   : configuracion explicita (RF/HGB); si se pasa, manda sobre `ajustar`
    ajustar : busca la configuracion por validacion cruzada espacial ANIDADA dentro
              de idx_tr, sin mirar idx_te (observacion sobre el ajuste de RF).
              GWR ya ajusta bandwidth y penalizacion asi por construccion; las
              redes mantienen la configuracion del articulo y lo declaran.
    """
    idx_tr = np.asarray(idx_tr)
    idx_te = np.asarray(idx_te)
    fijar_semilla(semilla)

    ytr_log = conj.y_log[idx_tr]
    yte_log = conj.y_log[idx_te]
    ctr, cte = conj.coords[idx_tr], conj.coords[idx_te]
    extras = {"n_train": int(len(idx_tr)), "n_test": int(len(idx_te)),
              "semilla": int(semilla), "dispositivo": str(DEVICE)}

    if modelo in (N.RF, N.HGB):
        # Arboles: invariantes a transformaciones afines por variable, se usa la
        # matriz sin escalar, como en modelos/baselines/baselines_tabulares.py.
        conf = dict(hiper or {})
        if ajustar and not conf:
            from .ajuste import buscar
            conf, tabla = buscar(conj, idx_tr, modelo, semilla=semilla, verboso=verboso)
            extras["ajuste"] = {"rejilla_evaluada": len(tabla), "elegido": conf}
        m = construir_arbol(modelo, conf, semilla)
        m.fit(conj.X[idx_tr], ytr_log)
        p_te = m.predict(conj.X[idx_te])
        p_tr = m.predict(conj.X[idx_tr])
        extras["hiperparametros"] = conf or "por defecto"
        pred_fn = (lambda Xn, cn=None: m.predict(np.asarray(Xn))) if devolver_predictor else None
        return Resultado(modelo, p_te, p_tr, smearing(ytr_log, p_tr), extras, pred_fn)

    sc = StandardScaler().fit(conj.X[idx_tr])
    Xtr, Xte = sc.transform(conj.X[idx_tr]), sc.transform(conj.X[idx_te])

    if modelo == N.OLS:
        m = LinearRegression().fit(Xtr, ytr_log)
        p_te, p_tr = m.predict(Xte), m.predict(Xtr)
        return Resultado(modelo, p_te, p_tr, smearing(ytr_log, p_tr), extras)

    if modelo == N.GWR:
        Xtr_i, Xte_i = add_intercept(Xtr), add_intercept(Xte)
        if rapido:
            bw, lam = BW_FALLBACK, LAMBDA_RIDGE
        else:
            sc_c = StandardScaler().fit(conj.X_cont[idx_tr])
            bw = select_bw(ctr, add_intercept(sc_c.transform(conj.X_cont[idx_tr])), ytr_log)
            lam, maes = select_lambda(ctr, Xtr_i, ytr_log, bw)
            extras["lambda_mae_interno"] = {str(k): round(v, 2) for k, v in maes.items()}
        if verboso:
            pr(f"      bw={bw}  lambda={lam}")
        p_te, n_rc = predict_gwr(ctr, Xtr_i, ytr_log, cte, Xte_i, bw, lam=lam)
        params_tr, _ = fit_gwr_ridge(ctr, Xtr_i, ytr_log, bw, lam=lam)
        p_tr = np.einsum("ij,ij->i", Xtr_i, params_tr)
        p_te, n_extremas = _amortiguar_extremos(p_te, (conj.y_log.min(), conj.y_log.max()))
        extras.update({"bw": int(bw), "lambda": float(lam), "correcciones_ridge": int(n_rc),
                       "predicciones_amortiguadas": n_extremas})
        if n_extremas and verboso:
            pr(f"      [aviso] {n_extremas} prediccion(es) fuera de rango fisico, acotada(s)")
        return Resultado(modelo, p_te, p_tr, smearing(ytr_log, p_tr), extras)

    if modelo in (N.GNNWR, N.SANNWR, N.SANNWR_ORIG):
        Xtr_i, Xte_i = add_intercept(Xtr), add_intercept(Xte)
        ols = LinearRegression(fit_intercept=False).fit(Xtr_i, ytr_log).coef_.flatten().astype(np.float32)
        dtr, dte = _distancias(modelo, ctr, cte, Xtr, Xte)
        rng = np.random.default_rng(semilla)
        vm = rng.random(len(idx_tr)) < VAL_FRAC
        tm = ~vm
        conf = dict(hiper or {})
        if ajustar and not conf:
            from .ajuste import buscar_red
            conf, tabla_red = buscar_red(conj, idx_tr, modelo, semilla=semilla,
                                         rapido=rapido, verboso=verboso)
            extras["ajuste"] = {"rejilla_evaluada": len(tabla_red), "elegido": conf}
        capas = conf.get("dense_layers", DENSE_LAYERS)
        dropout = conf.get("drop_out", DROP_OUT)
        lr = conf.get("start_lr", START_LR)
        epocas = EPOCHS_RAPIDO if rapido else N_EPOCHS
        paciencia = PATIENCE_RAPIDO if rapido else PATIENCE
        tr_ld = _loader(dtr[tm], Xtr_i[tm], ytr_log[tm], BATCH_SIZE, True)
        val_ld = _loader(dtr[vm], Xtr_i[vm], ytr_log[vm], BATCH_SIZE, False)
        te_ld = _loader(dte, Xte_i, yte_log, BATCH_SIZE, False)
        full_ld = _loader(dtr, Xtr_i, ytr_log, BATCH_SIZE, False)
        Red = RedPonderadaSAPDNN if modelo == N.SANNWR_ORIG else RedPonderada
        red = Red(len(idx_tr), Xtr_i.shape[1], ols,
                  dense_layers=capas, drop_out=dropout).to(DEVICE)
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / f"{etiqueta}.pt"
            extras.update(_entrenar_red(red, tr_ld, val_ld, ruta, epocas, paciencia,
                                        verboso, lr=lr))
        p_te = _predecir_red(red, te_ld)
        p_tr = _predecir_red(red, full_ld)
        extras.update({"epocas_max": epocas, "paciencia": paciencia,
                       "hiperparametros": conf or "del articulo",
                       "n_validacion": int(vm.sum()),
                       "alpha": ALPHA_SANNWR if modelo == N.SANNWR else None,
                       "sapdnn_oculta": SAPDNN_HIDDEN if modelo == N.SANNWR_ORIG else None})
        pred_fn = None
        if devolver_predictor:
            def pred_fn(Xn, cn):                       # noqa: E306
                Xs = sc.transform(np.asarray(Xn))
                _, d = _distancias(modelo, ctr, np.asarray(cn), Xtr, Xs)
                ld = _loader(d, add_intercept(Xs), np.zeros(len(Xs)), BATCH_SIZE, False)
                return _predecir_red(red, ld)
        else:
            del red
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return Resultado(modelo, p_te, p_tr, smearing(ytr_log, p_tr), extras, pred_fn)

    raise ValueError(f"modelo desconocido: {modelo}")
