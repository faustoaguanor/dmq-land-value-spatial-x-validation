# Revisión metodológica

Código que responde, con evidencia ejecutable, a las observaciones metodológicas
de un revisor formal de la tesis (Anexos A–F, C.6–C.8 y F del documento final).
Reutiliza los datos y módulos del repositorio principal por referencia, vía la
variable de entorno `TESIS_REPO`; no los duplica.

## Qué corrige cada carpeta

| Carpeta | Observación | Qué mide |
|---|---|---|
| `obs1_nomenclatura/` | Nomenclatura de SANNWR | Auditoría de que el documento distingue SANNWR-adaptado de la arquitectura publicada. Conclusión: cero cambios de texto o figura fueron necesarios; una figura (`smearing_bootstrap_cdf.py`) sí tenía el rótulo suelto y se corrigió. |
| `obs2_equivalencia_gnnwr/` | Equivalencia con el diseño original | Comprobaciones estructurales (E1–E7) de que la implementación propia realiza la operación que define a GNNWR y SANNWR; comparación numérica contra el paquete `gnnwr` de los autores; SANNWR con la red de fusión aprendida (Ni et al. 2022) frente a la adaptación de pesos fijos. |
| `obs4_imputacion/` | Fuga en la imputación previa | Cuantifica el desplazamiento de las medianas al recalcularlas solo con el entrenamiento, y confirma reentrenando los seis modelos que ningún puesto cambia salvo dentro de parejas ya declaradas estadísticamente indistinguibles. |
| `obs5_homogeneidad/` | Homogeneidad de la comparación | Ficha de cada implementación (hiperparámetros, ajuste, divergencias declaradas); búsqueda de rejilla anidada para Random Forest y HistGradientBoosting bajo los tres esquemas. |
| `obs6_n_efectivo/` | Tamaño efectivo de la muestra | Tamaño efectivo bajo autocorrelación espacial del error y su efecto sobre la significancia de las pruebas pareadas. |
| `obs7_interpretabilidad/` | Importancia con colinealidad alta | VIF de las 30 columnas y comparación entre importancia individual y agrupada por permutación. |

Una observación adicional del revisor —que la validación por bloques espaciales
funcionó parcialmente como conjunto de desarrollo— se documentó y se ejecutó
(test ciego con regiones selladas por hash), pero **no se incluye en este
repositorio**: no es lo que el revisor pidió explícitamente ni lo que describe
el diseño de validación por bloques de la literatura de referencia (que rota
folds, no aparta una región permanentemente). El capítulo 5 de la tesis ya
declara esa limitación en prosa, sin necesidad de un hallazgo nuevo.

## Cómo correrlo

```bash
export TESIS_REPO=/ruta/al/repositorio/principal   # o variable de entorno equivalente en Windows
python 00_verificar_entorno.py
python obs1_nomenclatura/01_auditar_nomenclatura.py
python obs2_equivalencia_gnnwr/02b_equivalencia_estructural.py
python obs4_imputacion/04a_mascara_imputacion.py
python obs5_homogeneidad/05_fichas_implementacion.py
python obs6_n_efectivo/06_tamano_efectivo.py
python obs7_interpretabilidad/07_importancia_agrupada.py
python 99_informe_revision.py   # consolida todo en salidas/INFORME_REVISION.md
```

Los pasos que necesitan GPU o toman horas (equivalencia numérica con el paquete
de referencia, SANNWR con la red de fusión aprendida, imputación reentrenando
los seis modelos) están descritos en `GUIA_RUNPOD.md`, junto con `run_all.sh` /
`run_all.ps1` para ejecutarlos de punta a punta.

## Salidas

`salidas/` contiene únicamente métricas agregadas (RMSE, MAE, R², tablas de
significancia) en Markdown, CSV y JSON. No incluye predicciones ni errores por
predio: se excluyen con el mismo criterio que el resto del repositorio
(ver `../DATA_AVAILABILITY.md`).
