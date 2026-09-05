"""
ajuste.py -- eleccion de hiperparametros por validacion cruzada espacial ANIDADA.

Responde a la observacion de que Random Forest corrio con los valores por defecto
de la biblioteca mientras GWR si elegia bandwidth y penalizacion dentro de cada
particion: la comparacion no era homogenea en esfuerzo de ajuste.

Procedimiento, deliberadamente igual al que gwr_core.select_lambda usa para
lambda, para que los dos modelos reciban el mismo trato:

  1. Dentro del entrenamiento de la particion externa, KMeans sobre las
     coordenadas parte los predios en `n_interno` grupos espaciales.
  2. Cada grupo actua por turno como evaluacion interna (dejar un grupo fuera).
     La particion interna es espacial, no aleatoria, para que la eleccion
     refleje la tarea de predecir en zonas no vistas.
  3. Se puntua cada configuracion por MAE en USD/m2, con retransformacion y
     factor de smearing calculados dentro del grupo de entrenamiento interno.
  4. Gana la de menor MAE; se reajusta con todo el entrenamiento de la particion.

El conjunto evaluado de la particion externa no interviene en ningun paso.

Las rejillas son declaradas de antemano y modestas: el objetivo es corregir la
asimetria de esfuerzo, no exprimir el ultimo decimo de RMSE.
"""
from __future__ import annotations
import itertools
import time

import numpy as np
from sklearn.cluster import KMeans

from . import nombres as N
from .rutas import pr

N_INTERNO = 3            # grupos espaciales de la validacion interna
MIN_TRAIN_INTERNO = 200

REJILLAS = {
    N.RF: {
        "n_estimators": [300, 800],
        "max_features": [1.0, 0.5, 0.33],
        "min_samples_leaf": [1, 2, 5],
    },
    N.HGB: {
        "max_iter": [400, 800],
        "learning_rate": [0.05, 0.1],
        "max_leaf_nodes": [31, 63],
        "min_samples_leaf": [10, 20],
    },
}


def combinaciones(rejilla: dict):
    claves = list(rejilla)
    for valores in itertools.product(*(rejilla[k] for k in claves)):
        yield dict(zip(claves, valores))


def buscar(conj, idx_tr, modelo: str, semilla: int = 42, n_interno: int = N_INTERNO,
           rejilla: dict | None = None, verboso: bool = True):
    """Devuelve (mejor_configuracion, tabla_de_resultados).

    tabla_de_resultados: lista de dicts {configuracion, MAE_interno, segundos}.
    """
    from .entrenadores import construir_arbol      # import diferido: evita ciclo

    rejilla = rejilla or REJILLAS.get(modelo)
    if not rejilla:
        return {}, []

    idx_tr = np.asarray(idx_tr)
    X = conj.X[idx_tr]
    y = conj.y_log[idx_tr]
    y_ori = conj.y_ori[idx_tr]
    coords = conj.coords[idx_tr]

    grupos = KMeans(n_clusters=n_interno, random_state=semilla, n_init=10).fit(coords).labels_
    partes = []
    for g in range(n_interno):
        te = grupos == g
        tr = ~te
        if te.sum() >= 20 and tr.sum() >= MIN_TRAIN_INTERNO:
            partes.append((np.where(tr)[0], np.where(te)[0]))
    if not partes:
        return {}, []

    tabla = []
    for conf in combinaciones(rejilla):
        t0 = time.time()
        errores = []
        for tr, te in partes:
            m = construir_arbol(modelo, conf, semilla)
            m.fit(X[tr], y[tr])
            s_M = float(np.mean(np.exp(y[tr] - m.predict(X[tr]))))
            pred = np.exp(m.predict(X[te])) * s_M
            errores.append(np.abs(y_ori[te] - pred))
        mae = float(np.mean(np.concatenate(errores)))
        tabla.append({"configuracion": conf, "MAE_interno": round(mae, 4),
                      "segundos": round(time.time() - t0, 1)})

    tabla.sort(key=lambda r: r["MAE_interno"])
    mejor = tabla[0]["configuracion"]
    if verboso:
        pr(f"      ajuste {modelo}: {len(tabla)} configuraciones, "
           f"gana {mejor} (MAE interno {tabla[0]['MAE_interno']:.2f}; "
           f"peor {tabla[-1]['MAE_interno']:.2f})")
    return mejor, tabla


def coste_estimado(conj=None, idx_tr=None, modelo: str = "", n_interno: int = N_INTERNO) -> str:
    n_conf = len(list(combinaciones(REJILLAS.get(modelo, {}))))
    return f"{n_conf} configuraciones x {n_interno} grupos = {n_conf * n_interno} ajustes"


# ---------------------------------------------------------------------------
# Busqueda para las redes
# ---------------------------------------------------------------------------
# El revisor senala que los modelos no recibieron el mismo nivel de busqueda de
# hiperparametros. Para RF y HGB la rejilla de arriba lo iguala. Para las redes
# una rejilla comparable costaria dias de GPU, asi que se ofrece una busqueda
# declarada y deliberadamente pequena: cuatro configuraciones y una sola
# particion interna espacial. Multiplica por cinco el coste de cada entrenamiento
# (cuatro tanteos mas el reajuste final), asi que se activa solo donde importa,
# tipicamente en el test ciego.
REJILLA_RED = [
    {},                                                   # la del articulo
    {"start_lr": 0.05},
    {"drop_out": 0.35},
    {"dense_layers": [1024, 512, 256, 64]},
]


def buscar_red(conj, idx_tr, modelo: str, semilla: int = 42, n_interno: int = 3,
               rejilla=None, rapido: bool = False, verboso: bool = True):
    """Elige configuracion de red con una particion interna espacial.

    Un grupo de KMeans dentro del entrenamiento hace de evaluacion interna; el
    resto entrena. Se puntua por MAE en USD/m2 con smearing interno. El conjunto
    evaluado de la particion externa no interviene.
    """
    from .entrenadores import entrenar          # import diferido: evita ciclo

    rejilla = rejilla if rejilla is not None else REJILLA_RED
    idx_tr = np.asarray(idx_tr)
    grupos = KMeans(n_clusters=n_interno, random_state=semilla,
                    n_init=10).fit(conj.coords[idx_tr]).labels_
    # el grupo mas parecido en tamano a un tercio hace de evaluacion interna
    objetivo = len(idx_tr) / n_interno
    g = min(range(n_interno), key=lambda k: abs((grupos == k).sum() - objetivo))
    interno_te = idx_tr[grupos == g]
    interno_tr = idx_tr[grupos != g]

    tabla = []
    for i, conf in enumerate(rejilla):
        t0 = time.time()
        r = entrenar(conj, interno_tr, interno_te, modelo, semilla=semilla,
                     etiqueta=f"aj_{modelo}_{i}", rapido=rapido, verboso=False, hiper=conf)
        pred = np.exp(r.pred_log_test) * r.s_M
        mae = float(np.mean(np.abs(conj.y_ori[interno_te] - pred)))
        tabla.append({"configuracion": conf, "MAE_interno": round(mae, 4),
                      "segundos": round(time.time() - t0, 1)})
        if verboso:
            pr(f"        tanteo {i+1}/{len(rejilla)} {conf or 'articulo'}: "
               f"MAE interno {mae:.2f} ({tabla[-1]['segundos']:.0f} s)")

    tabla.sort(key=lambda r: r["MAE_interno"])
    mejor = tabla[0]["configuracion"]
    if verboso:
        pr(f"      ajuste {modelo}: gana {mejor or 'la del articulo'} "
           f"(MAE interno {tabla[0]['MAE_interno']:.2f})")
    return mejor, tabla
