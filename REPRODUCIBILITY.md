# Guía de reproducibilidad

## Alcance

El repositorio permite auditar el código, el protocolo experimental, las semillas y los resultados agregados sin acceso a información restringida. La reproducción numérica exacta requiere obtener de las instituciones competentes las mismas versiones de las fuentes descritas en `DATA_AVAILABILITY.md`.

## Entorno de referencia

- Python 3.12.10
- CPU para OLS, GWR, Random Forest y análisis
- NVIDIA RTX 4090 de 24 GB para las ejecuciones neuronales de referencia
- PyTorch 2.5.1
- CRS de modelado: EPSG:32717 (UTM zona 17S)

Las operaciones CUDA pueden producir pequeñas diferencias entre hardware aun con la misma semilla.

## Estructura esperada de fuentes

Defina `DMQ_DATA_DIR` apuntando a un directorio externo con esta estructura:

```text
DMQ_DATA_DIR/
├── procesados/inf_procesada.gdb
├── PUGS_DMOT/DMOT_1.gdb
├── PUGS_DMOT/DMOT_2.gdb
├── PUG_Ciudad_Linea/
│   └── plan_de_uso_y_gestión_del_suelo_2024.gdb/PUGS_2024.gdb
├── catastro/stp_sector_a.shp
├── Predio_variables.csv
└── CATASTRO_PREDIAL_diciembre/predio_pend.csv
```

`predio_pend.csv` es el producto tabular derivado del MDT institucional de 2010. Si se recibe el TIF original, primero debe reproducirse el cálculo zonal de pendiente media por predio.

## Pipeline

1. `data_pipeline/pipeline.py`: integra las fuentes y escribe `datos/dataset.gpkg`.
2. `data_split/create_split.py`: genera el conjunto de prueba fijo 80/20.
3. `spatial_cv/pipeline_bloques.py`: construye las particiones espaciales.
4. Los scripts de `modelos/` entrenan y generan métricas.
5. `analisis/` consolida inferencia, sensibilidad e interpretabilidad.
6. `figures/` reconstruye las figuras a partir de las salidas.

Los archivos derivados sensibles permanecen ignorados por Git.

## Esquemas principales de evaluación

- Conjunto de prueba del 20 %: 4.040 observaciones de entrenamiento y 1.011 de prueba; interpolación interna.
- Validación cruzada aleatoria: cinco particiones sobre el conjunto de entrenamiento.
- Validación por bloques espaciales: cinco bloques de 5.621,8 m; separación geográfica parcial.

Son los tres esquemas que compara la tesis. Una versión anterior del trabajo evaluó además una zona de exclusión mínima de 2.530 m alrededor de cada región de prueba; ese cuarto escenario se retiró y su código ya no se publica. La distancia sobrevive con otro uso: 2.530 m es el tamaño de celda del remuestreo espacial con que se estiman los intervalos de confianza, y procede del alcance de la dependencia entre residuos que calcula `spatial_cv/diagnostico_buffer.py`.

## Modelos publicados

La tesis compara cinco modelos: OLS, GWR, Random Forest, GNNWR y SANNWR-adaptado, llamado así porque fija en 0,5/0,5 la combinación de distancias que el diseño original aprende. El directorio `modelos/` contiene además las variantes que el trabajo ejecutó y que los anexos documentan o que la consolidación de `analisis/analisis_log.py` sigue leyendo: MLP, GSAWR, GWR sobre 17 variables y la variante de SANNWR con grilla de referencia. Se conservan para que el análisis sea ejecutable de extremo a extremo y para dejar constancia de lo que se probó, no porque el documento las reporte.

El SANNWR canónico es `modelos/sannwr/sannwr_real_log.py`, con sus réplicas en `sannwr_real_log_replicas.py` y `sannwr_real_log_cv_replicas.py`. Los archivos `sannwr_log*.py` corresponden a la variante con grilla.

## Semillas

- Conjunto de prueba, diez réplicas: `42, 2011, 456, 777, 2026, 99, 1234, 888, 314, 7`.
- Validación cruzada neuronal, cinco réplicas: `42, 2011, 456, 777, 2026`.
- Random Forest canónico: `42`.

## Retransformación

Los modelos predicen `log(valor_m2)`. Para volver a USD/m² se aplica el estimador de *smearing* de Duan calculado exclusivamente sobre residuos de entrenamiento:

```text
y_hat_usd = exp(y_hat_log) * mean(exp(residual_train))
```

## Agregación bajo bloques espaciales

Los modelos neuronales y Random Forest son estocásticos, de modo que bajo bloques **el MAE de cada bloque se promedia entre semillas antes de cualquier contraste**. Las cifras por bloque salen de los `*_cv_replicas.csv`, no de los `*_log_results.csv`, que corresponden a la corrida base de semilla única. OLS y GWR son deterministas y sí se toman de su corrida base.

La distinción importa: mezclarlas produce diferencias que no cuadran con las tablas del documento. `analisis/tost_equivalencia.py` leía la corrida base hasta el 19 de septiembre de 2026 y daba, por ejemplo, −3,09 USD/m² para GNNWR frente a SANNWR-adaptado donde la tabla de resultados por bloques da −1,5.

La dispersión que acompaña a esas medias es la que hay **entre bloques**, no entre semillas: las cinco regiones son la unidad de evaluación, y las semillas son pseudorréplicas sobre la misma geografía.

## Análisis históricos

Algunas salidas de `results/raw/analysis/` se calcularon antes de la reejecución de GNNWR del 20 de septiembre de 2026 y conservan sus cifras anteriores. Se publican como registro de lo que se hizo, no como verificación de la ejecución vigente:

- `moran_holdout_significancia.csv` informa 0,097076 para GNNWR, que corresponde a la corrida previa; el valor vigente es 0,089, media de las diez réplicas, y está en `results/moran_conjunto_prueba.csv`.
- Las sensibilidades de duplicados, extremos y codificación, y la comparación con el paquete de referencia, se ejecutaron igualmente antes de esa reejecución.

Las cifras que el documento reporta salen de `analisis/cifras_canonicas.py`, que declara para cada tabla de qué archivo procede y con qué regla se agrega.

## Resultados esperados

Las tablas de referencia están en `results/*.csv`. Los archivos de `results/raw/` conservan métricas agregadas de las ejecuciones, nunca predicciones individuales.

`analisis/concordancia_predio_a_predio.py` es la excepción parcial: compara las predicciones de dos modelos entre sí, predicción a predicción, para medir cuánto discrepan en la misma parcela dos modelos de error medio casi idéntico. Requiere los archivos de predicciones, que no se publican.

## Validación sin datos

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

Estos controles verifican sintaxis, ausencia de artefactos restringidos, rutas portables y coherencia de los resultados canónicos.
