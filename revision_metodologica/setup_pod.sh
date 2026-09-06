#!/usr/bin/env bash
# setup_pod.sh -- prepara el entorno en RunPod (o en cualquier Linux con GPU).
#
#   cd /workspace/replicacion/revision_metodologica
#   bash setup_pod.sh
#
# Crea .venv salvo que ya exista un PyTorch con CUDA en el entorno del pod, en
# cuyo caso instala encima para no descargar 2.5 GB de ruedas otra vez.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AQUI"
export TESIS_REPO="${TESIS_REPO:-$(cd .. && pwd)}"
echo "repositorio: $TESIS_REPO"

# Herramientas que muchas imagenes de pod no traen. Si falla, no importa: hay
# alternativas con Python y con tar en la guia.
if ! command -v zip >/dev/null 2>&1 || ! command -v tmux >/dev/null 2>&1; then
  echo "instalando utilidades (zip, unzip, tmux) ..."
  (apt-get update -qq && apt-get install -y -qq zip unzip tmux) >/dev/null 2>&1     && echo "  listas" || echo "  [aviso] no se pudieron instalar; usar las alternativas de la guia"
fi

tiene_cuda() {
  python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null
}

echo "python del pod: $(python --version)"

if tiene_cuda; then
  echo "el entorno del pod ya trae PyTorch con CUDA: se instala encima"
  PY=python
  PIP="python -m pip"
else
  echo "creando entorno virtual .venv"
  python -m venv .venv
  PY="$AQUI/.venv/bin/python"
  PIP="$AQUI/.venv/bin/python -m pip"
  $PIP install --upgrade pip
  $PIP install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
fi

# Intento 1: version minima declarada. Intento 2 (si falla, tipico si el pod
# trae un Python mas viejo que el usado para fijar esos minimos): sin ninguna
# version, que pip resuelva lo mas nuevo compatible con este Python.
if ! $PIP install -r requirements_pod.txt; then
  echo "[aviso] fallo con las versiones declaradas; reintentando sin pines de version"
  grep -v '^#' requirements_pod.txt | grep -v '^$' | sed -E 's/[><=!~].*$//'     | $PIP install -r /dev/stdin
fi

echo
echo "verificando entorno"
TESIS_REPO="$TESIS_REPO" $PY 00_verificar_entorno.py

cat <<'FIN'

Listo. Orden sugerido (ver README.md para tiempos):

  # baratos, minutos
  python obs1_nomenclatura/01_auditar_nomenclatura.py
  python obs2_equivalencia_gnnwr/02b_equivalencia_estructural.py
  python obs4_imputacion/04a_mascara_imputacion.py
  python obs5_homogeneidad/05_fichas_implementacion.py
  python obs6_n_efectivo/06_tamano_efectivo.py

  # caros, horas: lanzar con nohup y revisar el registro
  nohup python obs4_imputacion/04b_protocolo_en_fold.py --modelos OLS RF GWR > log_04b_cpu.txt 2>&1 &
  nohup python obs4_imputacion/04b_protocolo_en_fold.py --modelos GNNWR SANNWR-adaptado > log_04b_gpu.txt 2>&1 &
FIN
