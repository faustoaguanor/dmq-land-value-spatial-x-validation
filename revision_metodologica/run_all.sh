#!/usr/bin/env bash
# run_all.sh -- ejecucion completa en el pod.
#
#   bash run_all.sh                # todo, en serie (12-15 h en una RTX 4090)
#   bash run_all.sh --solo-redes   # SOLO lo que necesita GPU (lo normal en el pod)
#   bash run_all.sh --solo-tabular # sin redes: unas 2 h
#   bash run_all.sh --rapido       # prueba de humo de extremo a extremo (NO reportable)
#   bash run_all.sh --con-forma    # anade las auditorias de forma del documento
#
# Todo es reanudable: si el pod se cae, volver a lanzarlo continua donde iba.
set -uo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AQUI"
export TESIS_REPO="${TESIS_REPO:-$(cd .. && pwd)}"
export PYTHONIOENCODING=utf-8
PY="${PY:-python}"
[ -x "$AQUI/.venv/bin/python" ] && PY="$AQUI/.venv/bin/python"
mkdir -p registros

RAPIDO=""
SOLO_TABULAR=0
SOLO_REDES=0
CON_FORMA=0
for a in "$@"; do
  [ "$a" = "--rapido" ] && RAPIDO="--rapido"
  [ "$a" = "--solo-tabular" ] && SOLO_TABULAR=1
  [ "$a" = "--solo-redes" ] && SOLO_REDES=1
  [ "$a" = "--con-forma" ] && CON_FORMA=1
done

paso() { echo; echo "=== $1 ==="; shift; "$PY" "$@"; }

# -- instantaneo -------------------------------------------------------------
paso "entorno"                       00_verificar_entorno.py
paso "mascara de imputacion"         obs4_imputacion/04a_mascara_imputacion.py
paso "equivalencia estructural"      obs2_equivalencia_gnnwr/02b_equivalencia_estructural.py
paso "tamano efectivo"               obs6_n_efectivo/06_tamano_efectivo.py
paso "importancia agrupada"          obs7_interpretabilidad/07_importancia_agrupada.py

if [ "$CON_FORMA" = "1" ]; then
  paso "forma: nomenclatura" obs1_nomenclatura/01_auditar_nomenclatura.py --emitir-parches
  paso "forma: fichas"       obs5_homogeneidad/05_fichas_implementacion.py
fi

# -- correcciones sin GPU (CPU) ----------------------------------------------
if [ "$SOLO_REDES" = "1" ]; then
  echo; echo "=== se omite la parte tabular (--solo-redes) ==="
  echo "Si la corriste en el portatil, empaqueta con --con-salidas para que el pod"
  echo "la encuentre hecha y consolide las tablas con todo dentro."
fi
if [ "$SOLO_REDES" != "1" ]; then
echo; echo "=== correcciones tabulares (CPU) ==="
"$PY" obs5_homogeneidad/05b_ajuste_hiperparametros.py 2>&1 | tee registros/05b_ajuste.log
"$PY" obs4_imputacion/04b_protocolo_en_fold.py --modelos OLS GWR RF $RAPIDO \
      2>&1 | tee registros/04b_tabulares.log
fi

if [ "$SOLO_TABULAR" = "1" ]; then
  "$PY" 99_informe_revision.py
  echo; echo "solo la parte tabular: hecho. Salidas en salidas/"
  exit 0
fi

# -- redes (GPU) -------------------------------------------------------------
echo; echo "=== redes (GPU) ==="
"$PY" obs2_equivalencia_gnnwr/02d_sannwr_original.py $RAPIDO \
      2>&1 | tee registros/02d_sannwr_original.log
"$PY" obs4_imputacion/04b_protocolo_en_fold.py --modelos GNNWR SANNWR-adaptado SANNWR-original $RAPIDO \
      2>&1 | tee registros/04b_redes.log

# consolidacion final: todo esta en cache, solo rehace las tablas con todo dentro
"$PY" obs4_imputacion/04b_protocolo_en_fold.py --modelos OLS > /dev/null 2>&1
"$PY" 99_informe_revision.py

echo
echo "Hecho. Salidas en salidas/, registros en registros/."
