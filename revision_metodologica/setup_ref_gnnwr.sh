#!/usr/bin/env bash
# setup_ref_gnnwr.sh -- entorno AISLADO para la implementacion de referencia de GNNWR
# (observacion 1.2). Se instala aparte a proposito: el paquete arrastra sus propias
# versiones de numpy/pandas/torch y no conviene que toquen el entorno con el que se
# reproducen las cifras de la tesis.
#
#   bash setup_ref_gnnwr.sh
#   .venv_ref/bin/python obs2_equivalencia_gnnwr/02a_referencia_gnnwr.py --semillas 42 2011 456
#   python obs2_equivalencia_gnnwr/02c_comparar_equivalencia.py     # con el entorno normal
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AQUI"
export TESIS_REPO="${TESIS_REPO:-$(cd .. && pwd)}"

python -m venv .venv_ref
PIP=".venv_ref/bin/python -m pip"
$PIP install --upgrade pip

# El paquete de referencia. Si la version fijada no resuelve, probar sin pin y
# anotar en el informe cual quedo instalada: la comparacion depende de eso.
$PIP install "gnnwr" || { echo "no se pudo instalar gnnwr; ver https://pypi.org/project/gnnwr/"; exit 1; }
# lo que 02a necesita ademas para leer el conjunto
$PIP install geopandas pandas numpy scikit-learn

.venv_ref/bin/python - <<'FIN'
import gnnwr, inspect
from gnnwr import models, datasets
print("gnnwr", getattr(gnnwr, "__version__", "?"))
print("init_dataset        :", inspect.signature(datasets.init_dataset))
print("init_predict_dataset:", inspect.signature(datasets.init_predict_dataset))
print("GNNWR               :", inspect.signature(models.GNNWR.__init__))
print("GNNWR.run           :", inspect.signature(models.GNNWR.run))
FIN

cat <<'FIN'

Entorno de referencia listo. Correr:
  TESIS_REPO="$TESIS_REPO" .venv_ref/bin/python obs2_equivalencia_gnnwr/02a_referencia_gnnwr.py

Si la firma que imprime arriba no coincide con la que espera 02a, ajustar los
nombres de argumento en la funcion `correr` de ese script: filtra por firma, de
modo que un argumento que sobre se descarta solo, pero uno que falte hay que
anadirlo a mano.
FIN
