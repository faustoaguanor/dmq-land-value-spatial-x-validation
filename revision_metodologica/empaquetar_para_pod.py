"""
empaquetar_para_pod.py -- arma el zip minimo para subir a RunPod.

Incluye solo lo que las corridas necesitan: los tres contratos de datos, los
modulos del repositorio que esta revision importa, los CSV de predicciones que
sirven de referencia, y esta carpeta. Deja fuera el entorno virtual, los pesos
de las redes, los documentos y el historico.

La estructura del zip reproduce la del repositorio, de modo que en el pod basta:

    unzip revision_pod.zip -d /workspace
    cd /workspace/replicacion/revision_metodologica
    bash setup_pod.sh

Uso:
    python empaquetar_para_pod.py
    python empaquetar_para_pod.py --salida /ruta/revision_pod.zip --con-salidas
"""
from __future__ import annotations
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun.rutas import REPO, BASE, pr   # noqa: E402

RAIZ_EN_ZIP = "replicacion"

ARCHIVOS = [
    "datos/dataset.gpkg",
    "data_split/split.csv",
    "data_split/create_split.py",
    "spatial_cv/output/fold_assignments.csv",
    "spatial_cv/estrategias_cv.py",
    "modelos/features.py",
    "modelos/gwr/gwr_core.py",
]
# CSV de referencia (predicciones y tablas comparativas). Solo archivos pequenos.
PATRONES = [
    "modelos/ols/output_log/*.csv",
    "modelos/gwr/output_log_27vars/*.csv",
    "modelos/gnnwr/output_log/*.csv",
    "modelos/sannwr/output_log_real/*.csv",
    "modelos/baselines/output_log/*.csv",
    "modelos/baselines/output_log_replicas/*.csv",
    "analisis/output_log/comparativo_*.csv",
]
EXCLUIR_SIEMPRE = ("salidas/obs2/_trabajo_paquete", "__pycache__", ".pyc")
# Los parciales solo se excluyen si no se piden las salidas. Con --con-salidas hay
# que llevarlos: son los resultados ya calculados en el portatil, y asi el pod los
# encuentra hechos, no los repite, y consolida las tablas con todo dentro.
EXCLUIR_SIN_SALIDAS = ("salidas/",)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(BASE / "revision_pod.zip"))
    ap.add_argument("--con-salidas", action="store_true",
                    help="incluir salidas/ y sus parciales: lo que ya corriste en el "
                         "portatil viaja al pod, que no lo repite y consolida todo junto")
    args = ap.parse_args()

    destino = Path(args.salida)
    incluidos, faltantes, total = [], [], 0

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in ARCHIVOS:
            p = REPO / rel
            if not p.exists():
                faltantes.append(rel)
                continue
            z.write(p, f"{RAIZ_EN_ZIP}/{rel}")
            incluidos.append(rel)
            total += p.stat().st_size
        for pat in PATRONES:
            for p in sorted(REPO.glob(pat)):
                if p.stat().st_size > 20_000_000:
                    continue
                rel = p.relative_to(REPO).as_posix()
                z.write(p, f"{RAIZ_EN_ZIP}/{rel}")
                incluidos.append(rel)
                total += p.stat().st_size
        for p in sorted(BASE.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(BASE).as_posix()
            if any(e in rel for e in EXCLUIR_SIEMPRE):
                continue
            if not args.con_salidas and any(rel.startswith(e) for e in EXCLUIR_SIN_SALIDAS):
                continue
            if rel.endswith(".zip"):
                continue
            z.write(p, f"{RAIZ_EN_ZIP}/revision_metodologica/{rel}")
            incluidos.append(f"revision_metodologica/{rel}")
            total += p.stat().st_size

    pr(f"archivos: {len(incluidos)}   sin comprimir: {total/1e6:.1f} MB")
    pr(f"zip      : {destino}  ({destino.stat().st_size/1e6:.1f} MB)")
    if faltantes:
        pr("[aviso] no encontrados: " + ", ".join(faltantes))
    pr("\nEn el pod:\n"
       f"  unzip {destino.name} -d /workspace\n"
       "  cd /workspace/replicacion/revision_metodologica\n"
       "  bash setup_pod.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
