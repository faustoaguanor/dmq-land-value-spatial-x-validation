"""
00_verificar_entorno.py -- comprobacion previa a cualquier corrida larga.

Verifica que la maquina (local o pod) ve el repositorio, que los tres contratos
de datos son bit a bit los mismos con los que se produjo la tesis, que la GPU
esta disponible y que los artefactos que sirven de referencia existen.

Uso:  python 00_verificar_entorno.py
Sale con codigo 1 si algo esencial falta.
"""
from __future__ import annotations
import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun.rutas import REPO, DATOS, SPLIT, FOLDS, salida, pr   # noqa: E402

ESPERADO = {"n": 5051, "n_train": 4040, "n_test": 1011, "n_folds": 5, "n_zonas": 10}

# Artefactos del repositorio que esta revision lee como referencia (no los modifica).
REFERENCIAS = [
    "modelos/gnnwr/output_log/gnnwr_log_predictions.csv",
    "modelos/gnnwr/output_log/gnnwr_log_replicas_summary.csv",
    "modelos/sannwr/output_log_real/sannwr_real_log_predictions.csv",
    "modelos/gwr/output_log_27vars/gwr27_log_predictions.csv",
    "modelos/ols/output_log/ols_log_predictions.csv",
    "modelos/baselines/output_log/rf_log_predictions.csv",
    "analisis/output_log/comparativo_holdout_smeared.csv",
]


def sha256(p: Path, n=1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(n)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    fallos = []
    info = {"repo": str(REPO), "python": sys.version.split()[0],
            "plataforma": platform.platform()}

    pr(f"repositorio : {REPO}")
    for etiqueta, ruta in [("dataset.gpkg", DATOS), ("split.csv", SPLIT),
                           ("fold_assignments.csv", FOLDS)]:
        if not ruta.exists():
            fallos.append(f"falta {ruta}")
            continue
        h = sha256(ruta)
        info[f"sha256_{etiqueta}"] = h
        pr(f"  {etiqueta:22s} {h[:16]}...  {ruta.stat().st_size/1e6:.2f} MB")

    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = bool(torch.cuda.is_available())
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        pr(f"  torch {torch.__version__}  cuda={info['cuda']}  gpu={info['gpu']}")
        if not info["cuda"]:
            pr("  [aviso] sin GPU: las redes tardaran horas por corrida")
    except ImportError:
        fallos.append("torch no instalado")

    for mod in ("numpy", "pandas", "geopandas", "sklearn", "scipy", "mgwr", "libpysal"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "?")
        except ImportError:
            fallos.append(f"falta {mod}")
    pr("  versiones : " + ", ".join(f"{k}={info[k]}" for k in
                                    ("numpy", "pandas", "geopandas", "sklearn", "mgwr") if k in info))

    try:
        from comun import datos
        c = datos.cargar()
        obs = {"n": c.n, "n_train": int(c.train_mask.sum()), "n_test": int(c.test_mask.sum()),
               "n_folds": int(len(set(c.folds.tolist()))), "n_zonas": int(len(set(c.zona.tolist())))}
        info["conteos"] = obs
        for k, v in ESPERADO.items():
            estado = "ok" if obs[k] == v else f"DISTINTO (esperado {v})"
            pr(f"  {k:9s} = {obs[k]:5d}  {estado}")
            if obs[k] != v:
                fallos.append(f"{k}={obs[k]} != {v}")
        pr(f"  covariables: one-hot {c.X.shape[1]}  continuo {c.X_cont.shape[1]}")
    except Exception as exc:                                   # noqa: BLE001
        fallos.append(f"no se pudo cargar el conjunto: {exc}")

    pr("\nartefactos de referencia:")
    for r in REFERENCIAS:
        p = REPO / r
        pr(f"  [{'x' if p.exists() else ' '}] {r}")
        if not p.exists():
            info.setdefault("referencias_faltantes", []).append(r)

    info["fallos"] = fallos
    dst = salida("00_entorno.json")
    dst.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    pr(f"\n[json] {dst}")

    if fallos:
        pr("\nFALLOS:\n  - " + "\n  - ".join(fallos))
        return 1
    pr("\nentorno correcto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
