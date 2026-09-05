"""
02a_referencia_gnnwr.py -- observacion 1.2, parte externa.

"No se verifico equivalencia con la implementacion original de GNNWR [...] el
resultado corresponde a la implementacion de GNNWR desarrollada."

Este script corre el paquete `gnnwr` que publican los autores del metodo
(Zhejiang University; Du et al. 2020, Chen et al. 2024) sobre EXACTAMENTE los
mismos datos, la misma particion 80/20 y las mismas 30 covariables que la tesis,
y guarda sus predicciones predio por predio. La comparacion contra la
implementacion propia la hace 02c_comparar_equivalencia.py.

Dos configuraciones, porque son dos preguntas distintas:

  paquete   hiperparametros por defecto del paquete: "que da la implementacion
            de referencia tal como se distribuye".
  tesis     los hiperparametros de la tesis (capas [2048,1024,512,256,64],
            Adadelta, lr 0.2, dropout 0.2, BatchNorm): aisla la diferencia de
            implementacion de la diferencia de configuracion.

El paquete de referencia trae dependencias propias y conviene instalarlo en un
entorno aparte (ver setup_ref_gnnwr.sh). Por eso este script solo escribe un CSV
de predicciones; no importa nada del resto de la revision salvo la lectura de
datos, que replica aqui para poder correr en un entorno minimo.

Uso:
    python obs2_equivalencia_gnnwr/02a_referencia_gnnwr.py --semillas 42 2011 456
    python obs2_equivalencia_gnnwr/02a_referencia_gnnwr.py --configs paquete
"""
from __future__ import annotations
import argparse
import inspect
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import salida, dir_salida, pr   # noqa: E402
from comun import datos as D                     # noqa: E402

CONFIG_TESIS = dict(dense_layers=[2048, 1024, 512, 256, 64], start_lr=0.2,
                    optimizer="Adadelta", drop_out=0.2, batch_norm=True)


def importar_paquete():
    """Importa el paquete de referencia evitando que lo tape el directorio
    modelos/gnnwr/ del repositorio, que Python ve como paquete de espacio de
    nombres con el mismo nombre."""
    sys.modules.pop("gnnwr", None)
    limpio = [p for p in sys.path
              if not Path(p).name == "modelos" and (Path(p) / "gnnwr").is_dir() is False]
    previo, sys.path[:] = list(sys.path), limpio
    try:
        import gnnwr
        if getattr(gnnwr, "__file__", None) is None:
            raise ImportError("solo se encontro un paquete de espacio de nombres, "
                              "no el paquete instalado")
        return gnnwr
    finally:
        sys.path[:] = previo


def filtrar_kwargs(fn, kwargs: dict) -> dict:
    """Pasa solo los argumentos que la firma del paquete admite (la API cambia
    entre versiones; mejor degradar que romper)."""
    try:
        validos = set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return dict(kwargs)
    return {k: v for k, v in kwargs.items() if k in validos}


def a_dataframe(conj, mask) -> pd.DataFrame:
    df = pd.DataFrame(conj.X[mask], columns=[f"x{i:02d}" for i in range(conj.X.shape[1])])
    df["y"] = conj.y_log[mask]
    df["u"] = conj.coords[mask, 0]
    df["v"] = conj.coords[mask, 1]
    # nombrada "id": getCoefs() del paquete (0.1.17) tiene hardcodeado ese nombre
    # de columna sin importar el id_column configurado (segundo bug de esta version)
    df["id"] = conj.predio[mask]
    return df.reset_index(drop=True)


def escala_sospechosa(pred: np.ndarray, y_ref: np.ndarray) -> bool:
    """El paquete escala internamente; si lo devuelto no esta en el rango de
    log(valor_m2) hay que avisar en vez de comparar peras con manzanas."""
    return not (y_ref.min() - 3 < np.nanmedian(pred) < y_ref.max() + 3)


def extraer_pred(obj) -> np.ndarray:
    if isinstance(obj, pd.DataFrame):
        cands = [c for c in obj.columns if "pred" in str(c).lower()]
        col = cands[0] if cands else obj.columns[-1]
        return obj[col].to_numpy(dtype=float).ravel()
    arr = np.asarray(obj, dtype=float)
    return arr.ravel()


def correr(config: str, semilla: int, epocas: int, paciencia: int,
           conj, tmp: Path) -> dict:
    from gnnwr import models, datasets

    tr = a_dataframe(conj, conj.train_mask)
    te = a_dataframe(conj, conj.test_mask)
    xcol = [c for c in tr.columns if c.startswith("x")]

    kw_ds = dict(data=tr, test_ratio=0.05, valid_ratio=0.10, x_column=xcol,
                 y_column=["y"], spatial_column=["u", "v"], id_column=["id"],
                 sample_seed=semilla, batch_size=64, shuffle=True)
    train_ds, val_ds, test_ds = datasets.init_dataset(**filtrar_kwargs(datasets.init_dataset, kw_ds))

    kw_m = dict(train_dataset=train_ds, valid_dataset=val_ds, test_dataset=test_ds,
                model_name=f"ref_{config}_s{semilla}",
                model_save_path=str(tmp / "modelos"),
                write_path=str(tmp / "runs"), log_path=str(tmp / "logs"),
                use_gpu=True, use_ols=True)
    if config == "tesis":
        kw_m.update(CONFIG_TESIS)
    modelo = models.GNNWR(**filtrar_kwargs(models.GNNWR.__init__, kw_m))

    t0 = time.time()
    modelo.run(**filtrar_kwargs(modelo.run, dict(max_epoch=epocas, early_stop=paciencia,
                                                 print_frequency=100)))
    segundos = time.time() - t0

    kw_p = dict(data=te, train_dataset=train_ds, x_column=xcol, spatial_column=["u", "v"])
    pred_ds = datasets.init_predict_dataset(**filtrar_kwargs(datasets.init_predict_dataset, kw_p))
    pred = extraer_pred(modelo.predict(pred_ds))

    if len(pred) != len(te):
        raise RuntimeError(f"el paquete devolvio {len(pred)} predicciones para {len(te)} predios")

    aviso = ""
    if escala_sospechosa(pred, conj.y_log):
        aviso = ("las predicciones no estan en la escala de log(valor_m2); revisar "
                 "process_fn del paquete antes de usar este CSV")
        pr(f"    [AVISO] {aviso}")

    out = pd.DataFrame({
        "predio_join": te["id"].values,
        "y_obs_log": te["y"].values,
        "y_pred_log": pred,
        "implementacion": "paquete_gnnwr",
        "config": config,
        "semilla": semilla,
    })
    return {"predicciones": out, "segundos": round(segundos, 1), "aviso": aviso,
            "n_train_paquete": int(len(train_ds.x) if hasattr(train_ds, "x") else -1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--semillas", type=int, nargs="+", default=[42, 2011, 456])
    ap.add_argument("--configs", nargs="+", default=["paquete", "tesis"],
                    choices=["paquete", "tesis"])
    ap.add_argument("--epocas", type=int, default=1000)
    ap.add_argument("--paciencia", type=int, default=200)
    args = ap.parse_args()

    try:
        import gnnwr
    except ImportError:
        pr("El paquete de referencia no esta instalado en este entorno.\n"
           "  pip install gnnwr        (conviene un entorno aparte: setup_ref_gnnwr.sh)\n"
           "Sin el, la observacion 1.2 solo puede responderse con la comprobacion\n"
           "estructural de 02b_equivalencia_estructural.py.")
        return 1

    conj = D.cargar()
    pr(f"paquete gnnwr {getattr(gnnwr, '__version__', '?')}  "
       f"train={int(conj.train_mask.sum())}  test={int(conj.test_mask.sum())}  "
       f"covariables={conj.X.shape[1]}")

    tmp = dir_salida("obs2", "_trabajo_paquete")
    filas, meta = [], []
    for config in args.configs:
        for s in args.semillas:
            pr(f"\n[{config} / semilla {s}]")
            try:
                r = correr(config, s, args.epocas, args.paciencia, conj, tmp)
            except Exception as exc:                        # noqa: BLE001
                pr(f"    fallo: {exc}")
                traceback.print_exc()
                meta.append({"config": config, "semilla": s, "estado": "fallo", "error": str(exc)})
                continue
            filas.append(r["predicciones"])
            meta.append({"config": config, "semilla": s, "estado": "ok",
                         "segundos": r["segundos"], "aviso": r["aviso"],
                         "n_train_paquete": r["n_train_paquete"]})
            e = np.exp(r["predicciones"]["y_obs_log"]) - np.exp(r["predicciones"]["y_pred_log"])
            pr(f"    RMSE sin smearing = {np.sqrt(np.mean(e**2)):.2f} USD/m2  "
               f"({r['segundos']:.0f} s)")

    if filas:
        dst = salida("obs2", "predicciones_paquete_gnnwr.csv")
        nuevo = pd.concat(filas, ignore_index=True)
        # Acumula en vez de sobrescribir: una corrida por config/semilla no debe
        # borrar las de una corrida anterior con otro config/semilla (bug real:
        # asi se perdieron las 1011 predicciones de --configs paquete al correr
        # despues --configs tesis, aunque el resumen agregado ya mostrado se
        # conservo aparte).
        if dst.exists():
            previo = pd.read_csv(dst)
            nuevo = (pd.concat([previo, nuevo], ignore_index=True)
                     .drop_duplicates(subset=["predio_join", "config", "semilla"], keep="last"))
        nuevo.to_csv(dst, index=False)
        pr(f"\n[csv] {dst}")
    dstj = salida("obs2", "corridas_paquete_gnnwr.json")
    historial = []
    if dstj.exists():
        try:
            historial = json.loads(dstj.read_text(encoding="utf-8")).get("corridas", [])
        except (json.JSONDecodeError, OSError):
            pass
    clave = lambda m: (m.get("config"), m.get("semilla"))                    # noqa: E731
    vistas = {clave(m) for m in meta}
    historial = [m for m in historial if clave(m) not in vistas] + meta
    dstj.write_text(json.dumps({"paquete": getattr(gnnwr, "__version__", "?"),
                                "corridas": historial}, indent=2, ensure_ascii=False), encoding="utf-8")
    pr(f"[json] {dstj}")
    return 0 if filas else 1


if __name__ == "__main__":
    raise SystemExit(main())
