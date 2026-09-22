# Trazabilidad de artefactos

Esta revisión mantiene intactos los datos, las particiones, las predicciones y las métricas de entrenamiento. La fuente de las tablas principales es `analisis/cifras_canonicas.py`; mapas y pruebas por predio usan las corridas base, con factores calculados de su propio entrenamiento mediante `analisis/predicciones_base.py`.

## Pesos de GNNWR

El [manifiesto](analisis/manifiesto_gnnwr.json) registra rutas, SHA-256, dimensiones y límites de procedencia. Describe artefactos locales restringidos; no distribuye sus pesos ni sus predicciones.

- Diez checkpoints CV son históricos: tienen 28 coeficientes con intercepto, frente a 31 actuales. No usar para regenerar resultados actuales.
- El checkpoint final tiene dimensiones compatibles, pero no reproduce el vector vigente al recargarlo con el preprocesamiento actual: RMSE 99,238741 frente a 91,714138 con exponencial directa. Su correspondencia con la reejecución no está acreditada.
- No quedaron guardados los identificadores y su orden en las referencias espaciales, ni los escaladores de esa ejecución. No se inventan el commit o la semilla efectivos de entrenamiento a partir del nombre del archivo.
- La recarga de interpretabilidad conserva su comprobación de RMSE y debe abortar si no coincide. Las importancias existentes son resultados almacenados; su regeneración desde ese checkpoint no está certificada.
- Faltan vectores individuales de todas las combinaciones de semilla y partición. Las medias se verifican desde métricas guardadas, no desde un ensamble de predicciones.

Conservar los originales. Un checkpoint recuperado solo puede declararse vigente después de reproducir por ID el vector correspondiente con sus propios escaladores y orden de referencias. En futuras ejecuciones, guardar commit, configuración, semilla, columnas y orden de variables, IDs y orden de referencias, escaladores y hashes de entradas y predicciones. No hace falta reentrenar para mantener el alcance descriptivo de los resultados conciliados.

## Salidas derivadas actuales

`procedencia_mapas.json` (local) y `revision_metodologica/salidas/obs6/procedencia.json` identifican las predicciones y los factores utilizados. El lector cartográfico rechaza claves, objetivos, predicciones y residuos que no correspondan a las corridas disponibles. El análisis de tamaño efectivo exige los cinco modelos y ajusta Holm sobre las diez parejas antes de filtrar una presentación.

Los resúmenes históricos, como la antigua fila GNNWR del resumen histórico de métricas retransformadas de prueba, no se borran ni se usan para reconstruir mapas actuales. El cargador canónico utiliza OLS/GWR de ese resumen y las réplicas de GNNWR de sus propios CSV.

## Conciliación del retorno de septiembre

La versión `entrega-2026-09-21` incorpora la comprobación del retorno `resultados_gnnwr.tar.gz`: sus trece archivos de resultados coinciden byte por byte con el proyecto y con el commit de integración `d6e55615f38483f50ede249b1981bcf62aaa9126`. Los siete CSV compartidos con esta copia de distribución coinciden también. Se verificaron los 5051 identificadores de la corrida base, 50 combinaciones de validación cruzada y diez réplicas de prueba frente a sus registros. El resumen de procedencia está en [analisis/procedencia_retorno_gnnwr.json](analisis/procedencia_retorno_gnnwr.json).

El registro del pod documenta que la recarga del modelo pasó su comprobación de RMSE (91,7141). El empaquetador excluyó los pesos, por lo que la limitación de repetir esa inferencia con los archivos locales permanece. La extracción denominada `pod_extraido` corresponde al retorno distinto de la revisión metodológica de agosto; sus resultados complementarios no sustituyen las salidas principales de septiembre.

La copia de código que acompaña al PDF corresponde a la etiqueta pública [entrega-2026-09-21](https://github.com/faustoaguanor/dmq-land-value-spatial-x-validation/tree/entrega-2026-09-21). La máscara por observación de la revisión de imputación queda excluida de esta versión; los archivos agregados mantienen sus cifras.
