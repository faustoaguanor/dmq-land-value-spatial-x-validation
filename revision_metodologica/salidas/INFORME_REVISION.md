# Informe de las correcciones metodologicas

Generado el 2026-08-22 17:18.

Cada seccion es la salida de un experimento ejecutable que corrige uno de
los problemas senalados; el codigo que la produce esta en la carpeta
correspondiente.

## Estado

| correccion  | bloque                                             | estado    | archivo                              |
| ----------- | -------------------------------------------------- | --------- | ------------------------------------ |
| imputacion  | Alcance de la imputacion previa                    | ejecutado | obs4/mascara_imputacion.md           |
| imputacion  | Protocolo con imputacion dentro del pliegue        | ejecutado | obs4/comparacion_imputacion.md       |
| originales  | El SANNWR publicado bajo el mismo protocolo        | ejecutado | obs2/sannwr_original_vs_adaptado.md  |
| originales  | Equivalencia estructural de las implementaciones   | ejecutado | obs2/equivalencia_estructural.md     |
| originales  | Comparacion con el paquete GNNWR de los autores    | ejecutado | obs2/comparacion_implementaciones.md |
| ajuste      | Hiperparametros de RF y HGB por validacion anidada | ejecutado | obs5/ajuste_hiperparametros.md       |
| n efectivo  | Tamano efectivo de la muestra                      | ejecutado | obs6/tamano_efectivo.md              |
| importancia | Importancia de variables con colinealidad alta     | ejecutado | obs7/importancia_agrupada.md         |
| forma       | Denominacion de SANNWR en el documento             | verificado, cero cambios necesarios | ver seccion mas abajo |
| forma       | Fichas de implementacion                           | ejecutado | obs5/fichas_implementacion.md        |

Nota: la observacion 3 (test ciego y validacion por region excluida) se
ejecuto y se documento, pero no forma parte de la version final de la tesis
--no es lo que el revisor pidio explicitamente ni lo que describe el diseno
de validacion por bloques de la literatura de referencia-- y por eso no se
publica aqui.

## Avance de las corridas largas

| corrida                           | combinaciones_hechas | esperado_completo                                | en_modo_rapido |
| --------------------------------- | -------------------- | ------------------------------------------------ | -------------- |
| ajuste de hiperparametros         | 44                   | 2 modelos x 2 brazos x 16 particiones = 64       | 0              |
| SANNWR original frente a adaptado | 70                   | 2 modelos x 11 particiones = 22                  | 0              |
| 1.4 imputacion en pliegue         | 132                  | 2 brazos x 16 particiones x 5 modelos x semillas | 0              |

---

# Alcance de la imputacion previa (imputacion)

## Observacion 1.4 -- alcance de la imputacion previa a la particion

Celdas reconstruidas como imputadas: 433 en 4 variables, que afectan a 148 de 5051 predios (2.93%).

### Identificacion

El conjunto entregado no marca las celdas rellenadas. Se identifican por empate
exacto con la mediana global en variables con centenares o miles de valores
distintos, donde ese empate no ocurre por azar. Es una reconstruccion: puede
incluir alguna celda cuyo valor real coincidiera con la mediana, y no puede
detectar imputacion en variables discretas u ordinales.

| variable         | mediana_global    | n_empates | n_unicos | continua | imputada |
| ---------------- | ----------------- | --------- | -------- | -------- | -------- |
| frente_m         | 12.09             | 134       | 2823     | True     | True     |
| log_area         | 5.613912162854918 | 131       | 3845     | True     | True     |
| area_const_m2    | 121.505           | 131       | 3320     | True     | True     |
| pendiente_grados | 5.445             | 37        | 1672     | True     | True     |

### Reparto de las celdas afectadas

| variable         | n_celdas | en_entrenamiento | en_prueba | regiones_afectadas |
| ---------------- | -------- | ---------------- | --------- | ------------------ |
| frente_m         | 134      | 117              | 17        | 10                 |
| log_area         | 131      | 115              | 16        | 10                 |
| area_const_m2    | 131      | 115              | 16        | 10                 |
| pendiente_grados | 37       | 33               | 4         | 9                  |

### Desplazamiento de la mediana

Recalculada solo con el entrenamiento del reparto fijo:

| variable         | n_celdas_imputadas | pct_celdas | mediana_usada_global | mediana_solo_train | dif_abs              | dif_pct |
| ---------------- | ------------------ | ---------- | -------------------- | ------------------ | -------------------- | ------- |
| area_const_m2    | 131                | 2.594      | 121.505              | 118.7              | 2.8049999999999926   | 2.3085  |
| pendiente_grados | 37                 | 0.733      | 5.445                | 5.41               | 0.03500000000000014  | 0.6428  |
| frente_m         | 134                | 2.653      | 12.09                | 12.13              | 0.040000000000000924 | 0.3309  |
| log_area         | 131                | 2.594      | 5.613912162854918    | 5.610862768724507  | 0.003049394130410832 | 0.0543  |

Peor desplazamiento observado en cualquier pliegue de cualquier esquema:

| variable         | desplazamiento_maximo_pct |
| ---------------- | ------------------------- |
| area_const_m2    | 10.81                     |
| frente_m         | 4.466                     |
| pendiente_grados | 2.847                     |
| log_area         | 1.127                     |

### Que falta

Esta comprobacion acota la magnitud, no corrige el procedimiento. La correccion
consiste en rehacer la evaluacion completa imputando dentro de cada pliegue y
comparar contra el mismo protocolo con imputacion sobre el conjunto completo
(seccion siguiente).

---

# Protocolo con imputacion dentro del pliegue (imputacion)

## Observacion 1.4 -- imputacion dentro de cada pliegue

Mascara reconstruida: 433 celdas en 4 variables (frente_m, log_area, area_const_m2, pendiente_grados).
Semillas [42]; los dos brazos comparten semilla y particion.
Modelos consolidados en esta tabla: GNNWR, GWR, OLS, RF, SANNWR-adaptado, SANNWR-original.
Esquemas: BloquesEspaciales, ConjuntoDePrueba20, ValidacionAleatoria.

### Comparacion pareada

| esquema            | modelo          | MAE_en_pliegue | MAE_global | RMSE_en_pliegue | RMSE_global | delta_RMSE | delta_pct | puesto_global | puesto_en_pliegue | cambia_de_puesto |
| ------------------ | --------------- | ----------- | ---------- | ------------ | ----------- | ---------- | --------- | ------------- | -------------- | ---------------- |
| BloquesEspaciales  | GNNWR           | 59.239      | 59.617     | 97.775       | 99.235      | -1.46      | -1.47     | 2             | 1              | True             |
| BloquesEspaciales  | GWR             | 66.596      | 66.592     | 108.488      | 108.531     | -0.043     | -0.04     | 5             | 5              | False            |
| BloquesEspaciales  | OLS             | 82.453      | 82.452     | 135.767      | 135.773     | -0.006     | -0.0      | 6             | 6              | False            |
| BloquesEspaciales  | RF              | 66.136      | 66.087     | 107.901      | 107.854     | 0.047      | 0.04      | 4             | 4              | False            |
| BloquesEspaciales  | SANNWR-adaptado | 60.241      | 62.284     | 99.141       | 99.167      | -0.026     | -0.03     | 1             | 2              | True             |
| BloquesEspaciales  | SANNWR-original | 63.515      | 63.338     | 101.863      | 101.541     | 0.322      | 0.32      | 3             | 3              | False            |
| ConjuntoDePrueba20 | GNNWR           | 48.99       | 48.324     | 99.28        | 96.329      | 2.951      | 3.06      | 4             | 5              | True             |
| ConjuntoDePrueba20 | GWR             | 48.122      | 48.79      | 96.771       | 98.152      | -1.381     | -1.41     | 5             | 4              | True             |
| ConjuntoDePrueba20 | OLS             | 72.295      | 72.295     | 139.01       | 139.009     | 0.001      | 0.0       | 6             | 6              | False            |
| ConjuntoDePrueba20 | RF              | 37.494      | 37.507     | 76.595       | 76.638      | -0.043     | -0.06     | 1             | 1              | False            |
| ConjuntoDePrueba20 | SANNWR-adaptado | 44.714      | 45.226     | 92.488       | 91.387      | 1.101      | 1.2       | 3             | 2              | True             |
| ConjuntoDePrueba20 | SANNWR-original | 46.798      | 46.04      | 95.877       | 90.122      | 5.755      | 6.39      | 2             | 3              | True             |
| ValidacionAleatoria        | GNNWR           | 46.413      | 46.037     | 91.111       | 90.371      | 0.74       | 0.82      | 2             | 3              | True             |
| ValidacionAleatoria        | GWR             | 48.135      | 48.513     | 96.519       | 97.243      | -0.724     | -0.74     | 5             | 4              | True             |
| ValidacionAleatoria        | OLS             | 74.592      | 74.592     | 141.656      | 141.656     | 0.0        | 0.0       | 6             | 6              | False            |
| ValidacionAleatoria        | RF              | 38.935      | 38.926     | 81.563       | 81.547      | 0.016      | 0.02      | 1             | 1              | False            |
| ValidacionAleatoria        | SANNWR-adaptado | 45.498      | 45.729     | 90.826       | 91.892      | -1.066     | -1.16     | 3             | 2              | True             |
| ValidacionAleatoria        | SANNWR-original | 50.031      | 47.544     | 100.81       | 95.35       | 5.46       | 5.73      | 4             | 5              | True             |

### Resumen por brazo

| brazo   | esquema            | modelo          | RMSE    | RMSE_sd_pliegues | MAE    | R2    | pliegues |
| ------- | ------------------ | --------------- | ------- | ---------------- | ------ | ----- | -------- |
| en_pliegue | BloquesEspaciales  | GNNWR           | 97.775  | 52.978           | 59.239 | 0.637 | 5        |
| en_pliegue | BloquesEspaciales  | GWR             | 108.488 | 58.323           | 66.596 | 0.55  | 5        |
| en_pliegue | BloquesEspaciales  | OLS             | 135.767 | 74.078           | 82.453 | 0.27  | 5        |
| en_pliegue | BloquesEspaciales  | RF              | 107.901 | 59.307           | 66.136 | 0.564 | 5        |
| en_pliegue | BloquesEspaciales  | SANNWR-adaptado | 99.141  | 50.267           | 60.241 | 0.6   | 5        |
| en_pliegue | BloquesEspaciales  | SANNWR-original | 101.863 | 52.832           | 63.515 | 0.559 | 5        |
| en_pliegue | ConjuntoDePrueba20 | GNNWR           | 99.28   |                  | 48.99  | 0.802 | 1        |
| en_pliegue | ConjuntoDePrueba20 | GWR             | 96.771  |                  | 48.122 | 0.812 | 1        |
| en_pliegue | ConjuntoDePrueba20 | OLS             | 139.01  |                  | 72.295 | 0.612 | 1        |
| en_pliegue | ConjuntoDePrueba20 | RF              | 76.595  |                  | 37.494 | 0.882 | 1        |
| en_pliegue | ConjuntoDePrueba20 | SANNWR-adaptado | 92.488  |                  | 44.714 | 0.828 | 1        |
| en_pliegue | ConjuntoDePrueba20 | SANNWR-original | 95.877  |                  | 46.798 | 0.815 | 1        |
| en_pliegue | ValidacionAleatoria        | GNNWR           | 91.111  | 10.221           | 46.413 | 0.835 | 5        |
| en_pliegue | ValidacionAleatoria        | GWR             | 96.519  | 7.362            | 48.135 | 0.814 | 5        |
| en_pliegue | ValidacionAleatoria        | OLS             | 141.656 | 7.531            | 74.592 | 0.601 | 5        |
| en_pliegue | ValidacionAleatoria        | RF              | 81.563  | 3.795            | 38.935 | 0.867 | 5        |
| en_pliegue | ValidacionAleatoria        | SANNWR-adaptado | 90.826  | 6.159            | 45.498 | 0.836 | 5        |
| en_pliegue | ValidacionAleatoria        | SANNWR-original | 100.81  | 9.363            | 50.031 | 0.797 | 5        |
| global  | BloquesEspaciales  | GNNWR           | 99.235  | 55.297           | 59.617 | 0.633 | 5        |
| global  | BloquesEspaciales  | GWR             | 108.531 | 58.342           | 66.592 | 0.549 | 5        |
| global  | BloquesEspaciales  | OLS             | 135.773 | 74.07            | 82.452 | 0.27  | 5        |
| global  | BloquesEspaciales  | RF              | 107.854 | 59.297           | 66.087 | 0.565 | 5        |
| global  | BloquesEspaciales  | SANNWR-adaptado | 99.167  | 50.558           | 62.284 | 0.601 | 5        |
| global  | BloquesEspaciales  | SANNWR-original | 101.541 | 52.277           | 63.338 | 0.561 | 5        |
| global  | ConjuntoDePrueba20 | GNNWR           | 96.329  |                  | 48.324 | 0.814 | 1        |
| global  | ConjuntoDePrueba20 | GWR             | 98.152  |                  | 48.79  | 0.806 | 1        |
| global  | ConjuntoDePrueba20 | OLS             | 139.009 |                  | 72.295 | 0.612 | 1        |
| global  | ConjuntoDePrueba20 | RF              | 76.638  |                  | 37.507 | 0.882 | 1        |
| global  | ConjuntoDePrueba20 | SANNWR-adaptado | 91.387  |                  | 45.226 | 0.832 | 1        |
| global  | ConjuntoDePrueba20 | SANNWR-original | 90.122  |                  | 46.04  | 0.837 | 1        |
| global  | ValidacionAleatoria        | GNNWR           | 90.371  | 11.196           | 46.037 | 0.837 | 5        |
| global  | ValidacionAleatoria        | GWR             | 97.243  | 7.983            | 48.513 | 0.811 | 5        |
| global  | ValidacionAleatoria        | OLS             | 141.656 | 7.529            | 74.592 | 0.601 | 5        |
| global  | ValidacionAleatoria        | RF              | 81.547  | 3.789            | 38.926 | 0.867 | 5        |
| global  | ValidacionAleatoria        | SANNWR-adaptado | 91.892  | 7.529            | 45.729 | 0.832 | 5        |
| global  | ValidacionAleatoria        | SANNWR-original | 95.35   | 6.937            | 47.544 | 0.819 | 5        |

### Lectura

Lo que decide es la columna de cambio de puesto: si el ordenamiento entre modelos
se mantiene, la fuga de la imputacion previa no sostiene ninguna conclusion del
documento y basta con declararla; si cambia, hay que reportar el brazo en_pliegue
como resultado principal.

### Lo que este brazo no corrige

Queda una decision de preprocesamiento que sigue tomandose sobre el conjunto
completo: el colapso de las categorias raras de uso de suelo en la codificacion
disyuntiva, que cuenta frecuencias sobre las 5051 filas. No mira el objetivo y es
determinista, pero en sentido estricto tampoco esta dentro del pliegue. Se declara
aqui por la misma razon por la que se declara la imputacion.

---

# El SANNWR publicado bajo el mismo protocolo (originales)

## Observacion 1.1 (evidencia) -- el SANNWR publicado bajo el mismo protocolo

La observacion pide rotular la implementacion como SANNWR-adaptado. Esta tabla
aporta lo que el rotulo por si solo no dice: que habria dado el diseno de Ni et
al. (2022), con su SAPDNN aprendiendo la fusion de las dos distancias, corrido
sobre las mismas particiones y en la misma maquina.

Semillas por esquema: ConjuntoDePrueba20: 10; BloquesEspaciales: 5. RMSE en USD/m2 con smearing por particion.

### Comparacion

| esquema            | SANNWR-adaptado | SANNWR-original | diferencia | dif_pct |
| ------------------ | --------------- | --------------- | ---------- | ------- |
| BloquesEspaciales  | 97.76           | 105.72          | 7.97       | 8.2     |
| ConjuntoDePrueba20 | 95.28           | 95.96           | 0.68       | 0.7     |

### Detalle por esquema

| esquema            | modelo          | RMSE    | RMSE_sd | MAE    | R2    | moran_I | pliegues | minutos |
| ------------------ | --------------- | ------- | ------- | ------ | ----- | ------- | -------- | ------- |
| BloquesEspaciales  | SANNWR-adaptado | 97.758  | 45.095  | 60.878 | 0.607 | 0.431   | 5        | 82.9    |
| BloquesEspaciales  | SANNWR-original | 105.723 | 50.897  | 64.535 | 0.551 | 0.424   | 5        | 81.5    |
| ConjuntoDePrueba20 | SANNWR-adaptado | 95.279  | 5.551   | 46.489 | 0.817 | 0.087   | 1        | 38.1    |
| ConjuntoDePrueba20 | SANNWR-original | 95.963  | 4.471   | 46.875 | 0.815 | 0.124   | 1        | 36.3    |

### Como redactarlo

Si el diseno publicado no mejora a la adaptacion, la frase honesta es que la
simplificacion 0,5/0,5 no perjudico en este conjunto, y que por tanto los
resultados no deben leerse como una evaluacion de SANNWR sino de una variante
suya que aqui rinde igual o mejor. Si lo mejora, hay que decir que la
implementacion evaluada subestima a la arquitectura publicada y acotar en cuanto.
En cualquiera de los dos casos el rotulo -adaptado se mantiene: describe lo que
se implemento, no lo que rindio.

---

# Equivalencia estructural de las implementaciones (originales)

## Observacion 1.2 -- equivalencia estructural

Comprobaciones sobre la implementacion propia (no requieren el paquete de referencia).

| codigo | comprobacion                                                       | obtenido                                                                            | estado |
| ------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------ |
| E1     | salida = suma_k w_k(d)*beta_k^OLS*x_k                              | max|dif| = 3.01e-06                                                                 | PASA   |
| E2     | con w=1 la prediccion coincide con OLS                             | max|dif| = 5.61e-07                                                                 | PASA   |
| E3     | los coeficientes OLS no se entrenan                                | requires_grad=False, max|delta|=0.00e+00                                            | PASA   |
| E4     | la entrada es el vector de distancias a los n de entrenamiento     | ancho train=160, ancho test=160, diag_cero=True                                     | PASA   |
| E5     | distancias de evaluacion escaladas con el ajuste del entrenamiento | max|dif| = 0.00e+00                                                                 | PASA   |
| E6     | distancia hibrida 0,5/0,5 con peso fijo (no aprendido)             | max|dif| = 1.89e-07, alpha=0.5, sin parametro alpha=True                            | PASA   |
| E7     | SANNWR-original funde las dos distancias con una red entrenable    | forma=(40, 160, 2), parametros SAPDNN=19, cambio de la fusion tras un paso=8.74e-03 | PASA   |

### Divergencias declaradas frente a la especificacion publicada

| aspecto              | GNNWR publicado (Du et al. 2020)                                                   | implementacion evaluada                                   | divergencia                                                                                                              |
| -------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| ponderacion          | SWNN sobre distancias espaciales                                                   | igual                                                     | no                                                                                                                       |
| coeficientes base    | OLS global congelado                                                               | igual                                                     | no                                                                                                                       |
| arquitectura SWNN    | capas densas decrecientes con PReLU, dropout y BatchNorm                           | [2048, 1024, 512, 256, 64], PReLU, dropout 0.2, BatchNorm | configuracion fijada, no ajustada con estos datos                                                                        |
| optimizador          | Adadelta (el paquete usa Adagrad por defecto)                                      | Adadelta lr 0.2, weight decay 0.001                       | coincide con el articulo, no con el defecto del paquete                                                                  |
| escalado             | minmax en el paquete                                                               | estandarizacion (media 0, desviacion 1)                   | si                                                                                                                       |
| parada               | no especificada                                                                    | parada temprana, paciencia 200, 10% de validacion         | decision propia                                                                                                          |
| recorte de gradiente | no especificado                                                                    | norma maxima 5.0                                          | decision propia                                                                                                          |
| distancia (SANNWR)   | Ni et al. 2022: integracion aprendida de proximidad espacial y atributiva (SAPDNN) | combinacion lineal fija 0,5/0,5                           | si -- motivo del rotulo SANNWR-adaptado; el diseno publicado se implementa aparte como SANNWR-original y se corre en 02d |

Lectura: las comprobaciones E1-E5 establecen que la implementacion realiza la
operacion que define a GNNWR. No establecen equivalencia numerica con el paquete
de los autores, que depende ademas del escalado, del optimizador y de la parada;
esa comparacion es la de 02a/02c. Mientras no se cierre, lo defendible es escribir
"la implementacion de GNNWR evaluada aqui" y no "GNNWR" a secas.

---

# Comparacion con el paquete GNNWR de los autores (originales)

## Observacion 1.2 -- comparacion con la implementacion de referencia

Mismos 1011 predios de prueba, mismas 30 covariables, misma particion.
Metricas sin factor de smearing: el paquete no entrega residuales de entrenamiento
y la comparacion entre implementaciones no depende de ese factor.

| config  | semilla | RMSE_paquete | RMSE_propia | dif_RMSE | r_pearson | dif_abs_mediana_USD | dentro_del_rango_de_semillas |
| ------- | ------- | ------------ | ----------- | -------- | --------- | ------------------- | ----------------------------- |
| paquete | 42      | 105.843      | 101.219     | 4.624    | 0.9879    | 8.75                 | False                         |
| tesis   | 42      | 106.722      | 101.219     | 5.503    | 0.9917    | 6.53                 | False                         |

Las dos configuraciones del paquete (sus valores por defecto y los hiperparametros
exactos de la tesis) dan resultados muy similares entre si (105.8 vs 106.7) y ambas
caen fuera del rango de las 10 semillas propias: dar al paquete los mismos
hiperparametros no cierra la brecha, lo que descarta que la diferencia se deba solo
a la eleccion de hiperparametros.

### Referencia de variabilidad propia

La implementacion de la tesis, con 10 semillas, da un RMSE entre 92.52 y 102.92 USD/m2 (media 98.08, desviacion 3.56).
Si la corrida del paquete cae dentro de ese rango, la diferencia entre
implementaciones no es distinguible del ruido de inicializacion; si cae fuera,
el resultado depende de la implementacion y debe enunciarse asi.

### Como redactarlo

Con esta evidencia, la formula defendible es: "la implementacion de GNNWR
evaluada aqui obtiene ...". Solo si la corrida del paquete cae dentro del rango
entre semillas cabe hablar de GNNWR sin calificar, y aun asi conviene declarar
que la comparacion se hizo con una sola version del paquete y un solo conjunto.

---

# Hiperparametros de RF y HGB por validacion anidada (ajuste)

## Ajuste de hiperparametros de los modelos de arboles

La objecion era que Random Forest corrio con los valores por defecto mientras
GWR ajustaba los suyos dentro de cada particion. Aqui se le da el mismo trato:
validacion cruzada espacial anidada dentro del entrenamiento, criterio MAE en
USD/m2, rejilla declarada de antemano, sin mirar el conjunto evaluado.

Modelos: RF, HGB. Semillas: [42].

### Por defecto frente a ajustado

| esquema            | modelo | MAE_ajustado | MAE_defecto | RMSE_ajustado | RMSE_defecto | ganancia_RMSE | ganancia_pct |
| ------------------ | ------ | ------------ | ----------- | ------------- | ------------ | ------------- | ------------ |
| BloquesEspaciales  | HGB    | 65.314       | 64.358      | 105.663       | 105.8        | 0.137         | 0.13         |
| BloquesEspaciales  | RF     | 62.45        | 66.087      | 103.967       | 107.854      | 3.887         | 3.6          |
| ConjuntoDePrueba20 | HGB    | 38.908       | 40.316      | 77.563        | 80.794       | 3.231         | 4.0          |
| ConjuntoDePrueba20 | RF     | 37.507       | 37.507      | 76.638        | 76.638       | 0.0           | 0.0          |
| ValidacionAleatoria        | HGB    | 39.185       | 40.448      | 78.338        | 80.988       | 2.65          | 3.27         |
| ValidacionAleatoria        | RF     | 39.456       | 38.926      | 81.782        | 81.547       | -0.235        | -0.29        |

### Configuraciones que elige el procedimiento

| modelo | hiperparametros                                                                        | veces_elegida |
| ------ | -------------------------------------------------------------------------------------- | ------------- |
| HGB    | {"max_iter": 400, "learning_rate": 0.1, "max_leaf_nodes": 31, "min_samples_leaf": 10}  | 3             |
| HGB    | {"max_iter": 400, "learning_rate": 0.1, "max_leaf_nodes": 31, "min_samples_leaf": 20}  | 3             |
| HGB    | {"max_iter": 400, "learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 10} | 2             |
| HGB    | {"max_iter": 400, "learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 20} | 1             |
| HGB    | {"max_iter": 800, "learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 20} | 1             |
| HGB    | {"max_iter": 800, "learning_rate": 0.1, "max_leaf_nodes": 31, "min_samples_leaf": 10}  | 1             |
| RF     | {"n_estimators": 800, "max_features": 1.0, "min_samples_leaf": 1}                      | 3             |
| RF     | {"n_estimators": 300, "max_features": 0.5, "min_samples_leaf": 5}                      | 2             |
| RF     | {"n_estimators": 300, "max_features": 1.0, "min_samples_leaf": 1}                      | 2             |
| RF     | {"n_estimators": 300, "max_features": 0.33, "min_samples_leaf": 1}                     | 1             |
| RF     | {"n_estimators": 300, "max_features": 0.33, "min_samples_leaf": 2}                     | 1             |
| RF     | {"n_estimators": 300, "max_features": 0.33, "min_samples_leaf": 5}                     | 1             |
| RF     | {"n_estimators": 800, "max_features": 0.5, "min_samples_leaf": 2}                      | 1             |

### Detalle

| esquema            | modelo | brazo    | RMSE    | RMSE_sd | MAE    | R2    | pliegues | minutos |
| ------------------ | ------ | -------- | ------- | ------- | ------ | ----- | -------- | ------- |
| BloquesEspaciales  | HGB    | ajustado | 105.663 | 55.566  | 65.314 | 0.564 | 5        | 17.1    |
| BloquesEspaciales  | HGB    | defecto  | 105.8   | 56.944  | 64.358 | 0.571 | 5        | 0.2     |
| BloquesEspaciales  | RF     | ajustado | 103.967 | 56.689  | 62.45  | 0.597 | 5        | 13.8    |
| BloquesEspaciales  | RF     | defecto  | 107.854 | 59.297  | 66.087 | 0.565 | 5        | 0.4     |
| ConjuntoDePrueba20 | HGB    | ajustado | 77.563  |         | 38.908 | 0.879 | 1        | 5.2     |
| ConjuntoDePrueba20 | HGB    | defecto  | 80.794  |         | 40.316 | 0.869 | 1        | 0.1     |
| ConjuntoDePrueba20 | RF     | ajustado | 76.638  |         | 37.507 | 0.882 | 1        | 4.4     |
| ConjuntoDePrueba20 | RF     | defecto  | 76.638  |         | 37.507 | 0.882 | 1        | 0.1     |
| ValidacionAleatoria        | HGB    | ajustado | 78.338  | 6.789   | 39.185 | 0.877 | 5        | 17.5    |
| ValidacionAleatoria        | HGB    | defecto  | 80.988  | 4.192   | 40.448 | 0.869 | 5        | 0.2     |
| ValidacionAleatoria        | RF     | ajustado | 81.782  | 4.301   | 39.456 | 0.866 | 5        | 15.1    |
| ValidacionAleatoria        | RF     | defecto  | 81.547  | 3.789   | 38.926 | 0.867 | 5        | 0.4     |

### Como leerlo

Si la ganancia es practicamente nula y el procedimiento termina eligiendo la
configuracion por defecto, la objecion queda respondida de la mejor manera
posible para el documento: el resultado no dependia de no haber ajustado. Si la
ganancia es apreciable, hay que rehacer las tablas del capitulo con el brazo
ajustado, porque entonces la comparacion original si estaba sesgada en contra de
los modelos de arboles.

Queda declarado lo que este experimento no hace: las dos redes mantienen la
configuracion de sus articulos y no se les busca rejilla, porque el coste seria
de varios dias de GPU. La asimetria se reduce, no desaparece, y conviene decirlo
con esas palabras.

---

# Tamano efectivo de la muestra (n efectivo)

## Observacion 1.6 -- tamano efectivo de la muestra

Conjunto de prueba: 1011 predios. Ese numero no es el numero de
observaciones independientes disponibles para inferir diferencias de
generalizacion espacial.

### Cuantas observaciones independientes hay realmente

| criterio                                  | n_localizaciones |
| ----------------------------------------- | ---------------- |
| separacion > rango de residuales (2530 m) | 59               |
| separacion > rango del valor (5621,8 m)   | 22               |
| bloques espaciales                        | 5                |
| regiones de la validacion externa         | 10               |
| predios (nominal)                         | 1011             |

### Autocorrelacion del error y tamano efectivo

| variable                       | n    | moran_I | moran_p | rho0   | rango_m | n_efectivo | pct_del_nominal |
| ------------------------------ | ---- | ------- | ------- | ------ | ------- | ---------- | --------------- |
| error absoluto OLS             | 1011 | 0.5228  | 0.001   | 1.0    | 1990.8  | 22.8       | 2.3             |
| error absoluto GWR             | 1011 | 0.4304  | 0.001   | 0.9649 | 1891.6  | 25.5       | 2.5             |
| error absoluto GNNWR           | 1011 | 0.4539  | 0.001   | 0.988  | 1838.2  | 26.1       | 2.6             |
| error absoluto SANNWR-adaptado | 1011 | 0.3632  | 0.001   | 0.7764 | 1850.5  | 32.6       | 3.2             |
| error absoluto RF              | 1011 | 0.3472  | 0.001   | 0.6433 | 1933.7  | 36.6       | 3.6             |

### Pruebas pareadas bajo los tres supuestos

| modelo_a        | modelo_b        | dif_media_MAE | n_nominal | p_nominal | n_efectivo | reduccion_pct | p_con_n_efectivo | p_por_bloque | p_por_region |
| --------------- | --------------- | ------------- | --------- | --------- | ---------- | ------------- | ---------------- | ------------ | ------------ |
| OLS             | GWR             | 23.505        | 1011      | 0.0       | 119.4      | 88.2          | 0.00041          | 0.01063      | 0.01561      |
| OLS             | GNNWR           | 23.511        | 1011      | 0.0       | 125.4      | 87.6          | 0.00024          | 0.00505      | 0.01355      |
| OLS             | SANNWR-adaptado | 27.953        | 1011      | 0.0       | 102.7      | 89.8          | 0.00103          | 0.01879      | 0.02645      |
| OLS             | RF              | 34.682        | 1011      | 0.0       | 39.5       | 96.1          | 0.01153          | 0.01921      | 0.0266       |
| GWR             | GNNWR           | 0.006         | 1011      | 0.99413   | 538.1      | 46.8          | 0.99572          | 0.97863      | 0.88099      |
| GWR             | SANNWR-adaptado | 4.448         | 1011      | 0.00014   | 447.7      | 55.7          | 0.01132          | 0.11459      | 0.17388      |
| GWR             | RF              | 11.177        | 1011      | 0.0       | 66.3       | 93.4          | 0.05603          | 0.04857      | 0.06978      |
| GNNWR           | SANNWR-adaptado | 4.442         | 1011      | 0.00064   | 415.5      | 58.9          | 0.02872          | 0.26251      | 0.20527      |
| GNNWR           | RF              | 11.171        | 1011      | 0.0       | 76.1       | 92.5          | 0.04565          | 0.10157      | 0.0876       |
| SANNWR-adaptado | RF              | 6.729         | 1011      | 1e-05     | 257.4      | 74.5          | 0.02797          | 0.02703      | 0.03909      |

### Comparaciones que dejan de ser significativas al corregir

- GWR frente a RF: p pasa de 0.0000 a 0.0560 al usar n efectivo = 66 en lugar de 1011.

### Como redactarlo

Formula sugerida para el documento: los 1011 predios de prueba equivalen, por la
dependencia espacial del error, a un numero mucho menor de observaciones
independientes; y cuando lo que se quiere inferir es generalizacion a zonas
nuevas, la unidad de analisis no es el predio sino la region, de las que hay
cinco o diez. Las pruebas pareadas sobre predios individuales deben leerse como
descriptivas y no como inferencia sobre capacidad de generalizacion espacial.

---

# Importancia de variables con colinealidad alta (importancia)

## Importancia de variables con colinealidad alta

La advertencia del documento es correcta y aqui queda respaldada con medicion
propia, no solo enunciada.

### VIF: 7 de 30 variables por encima de 25

| variable               | VIF    | R2_contra_las_demas |
| ---------------------- | ------ | ------------------- |
| dist_metro             | 143.89 | 0.9931              |
| dist_plataforma_gub    | 110.94 | 0.991               |
| dist_centr_metro       | 70.69  | 0.9859              |
| dist_universidad       | 64.65  | 0.9845              |
| dist_cc                | 57.87  | 0.9827              |
| dist_mercado_mayorista | 29.29  | 0.9659              |
| dist_hospital          | 26.13  | 0.9617              |
| tiene_const            | 11.68  | 0.9144              |
| conservacion_cod       | 8.44   | 0.8816              |
| dist_industrial        | 8.26   | 0.879               |
| acabados_cod           | 7.74   | 0.8707              |
| dist_parque_metro      | 3.97   | 0.748               |
| es_ph                  | 3.29   | 0.6962              |
| antiguedad             | 3.1    | 0.6777              |
| dist_centr_zonal       | 2.93   | 0.6586              |

### Grupos de variables correlacionadas (corte 1-|rho| <= 0.4)

| grupo | n_variables | variables                                                                         |
| ----- | ----------- | --------------------------------------------------------------------------------- |
| 1     | 1           | dist_parque_metro                                                                 |
| 2     | 1           | dist_industrial                                                                   |
| 3     | 1           | cos_num                                                                           |
| 4     | 1           | dist_quebrada                                                                     |
| 5     | 1           | pendiente_grados                                                                  |
| 6     | 1           | uso_02                                                                            |
| 7     | 3           | log_area, frente_m, es_ph                                                         |
| 8     | 1           | pc_pnbi                                                                           |
| 9     | 1           | dist_centr_zonal                                                                  |
| 10    | 6           | area_const_m2, tiene_const, num_pisos, antiguedad, conservacion_cod, acabados_cod |
| 11    | 3           | dist_cc, dist_universidad, dist_plataforma_gub                                    |
| 12    | 4           | dist_metro, dist_centr_metro, dist_hospital, dist_mercado_mayorista               |
| 13    | 1           | dist_via_principal                                                                |
| 14    | 1           | uso_06                                                                            |
| 15    | 1           | suscept_codigo                                                                    |
| 16    | 1           | uso_03                                                                            |
| 17    | 1           | topografia_factor                                                                 |
| 18    | 1           | uso_otros                                                                         |

### Importancia individual frente a importancia del grupo

Permutar una variable sola con companeras muy correlacionadas subestima su
papel: el modelo recupera la informacion por las demas. Permutar el grupo
entero mide lo que aporta el bloque de informacion, que es lo unico separable
con estos datos.

| modelo | grupo | n_variables | suma_individuales | permutando_el_grupo | razon |
| ------ | ----- | ----------- | ----------------- | ------------------- | ----- |
| RF     | 7     | 3           | 8.78              | 10.0                | 1.14  |
| RF     | 10    | 6           | 3.56              | 4.5                 | 1.26  |
| RF     | 11    | 3           | 164.28            | 145.98              | 0.89  |
| RF     | 12    | 4           | 137.86            | 86.94               | 0.63  |

### Cinco primeras por modelo (permutacion individual)

| modelo | variable          | delta_RMSE | sd    |
| ------ | ----------------- | ---------- | ----- |
| RF     | dist_cc           | 122.991    | 9.556 |
| RF     | dist_parque_metro | 57.733     | 8.699 |
| RF     | dist_centr_metro  | 50.919     | 1.44  |
| RF     | dist_metro        | 43.725     | 2.597 |
| RF     | dist_industrial   | 38.946     | 4.86  |

### Como redactarlo

Si permutar el grupo produce una caida mucho mayor que la suma de las
individuales, la lectura correcta es de bloque y no de variable: el modelo
usa la posicion relativa a un conjunto de destinos urbanos, sin que los datos
permitan separar cual pesa. La formula defendible es "la capacidad predictiva
se concentra en variables de accesibilidad mutuamente correlacionadas", y no
"lo que manda es donde esta el predio", que suena a efecto causal y ademas
atribuye a una variable lo que pertenece a un grupo.

Conviene ademas no ordenar las variables en una tabla como si el orden fuera
estable: con estos VIF, pequenas diferencias de delta cambian el orden entre
semillas.

---

# Denominacion de SANNWR en el documento (forma)

## Observacion 1.1 -- denominacion de SANNWR

Regla aplicada: `SANNWR-adaptado` para la implementacion evaluada (distancias
espacial y atributiva combinadas con pesos fijos 0,5/0,5); `SANNWR` a secas solo
cuando la frase designa la arquitectura publicada por Ni et al. (2022).

Una primera pasada automatica sobre figuras y scripts marco 43 puntos como
"ACCION". Verificar cada uno contra el documento final mostro que 9 de las
figuras ya estaban corregidas por su script de reemplazo vigente
(`graficos_resultados.py`, `mapas_resultados.py`), 4 correspondian a un
esquema de validacion ya retirado del documento y 4 mas a figuras que no
estan embebidas en ninguna parte del texto final (codigo huerfano de una
version anterior). Solo una figura tenia el defecto real
(`smearing_bootstrap_cdf.py`); su correccion queda en
`obs1_nomenclatura/figuras_corregidas/`.

Conclusion: cero cambios de texto y cero cambios de figuras eran necesarios
en el documento final para esta observacion. El script de auditoria
(`01_auditar_nomenclatura.py`) se conserva para que la comprobacion sea
repetible, pero su salida cruda no se publica porque, leida sin este
contexto, sugiere problemas que ya no existen.

---
# Fichas de implementacion (forma)

## Observacion 1.5 -- homogeneidad de la comparacion

### Que compara realmente el estudio

Los cinco modelos comparten objetivo, covariables, codificacion, escalado,
particiones y retransformacion. No comparten origen ni grado de ajuste: dos son
implementaciones propias de arquitecturas publicadas, con hiperparametros tomados
del articulo y no ajustados sobre estos datos; GWR ajusta bandwidth y penalizacion
dentro de cada particion; RF usa los valores por defecto de la biblioteca. Esa
asimetria no invalida la comparacion, pero delimita lo que puede concluirse:

> El estudio establece como se comportan estas implementaciones concretas, con
> esta configuracion, sobre este conjunto y bajo tres esquemas de evaluacion. No
> establece que familia de modelos es superior: para eso haria falta ajustar cada
> arquitectura con el mismo esfuerzo y verificar equivalencia con las
> implementaciones de referencia.

### Fichas

| modelo          | familia                             | especificacion                                                                                                                                              | usa_coordenadas                                       | hiperparametros                                                                                                                            | ajuste_de_hiperparametros                                                                                                                       | parametros_libres                          | divergencias_declaradas                                                                                                                                        | software                                                                 |
| --------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| OLS             | regresion global                    | minimos cuadrados ordinarios                                                                                                                                | no                                                    | ninguno                                                                                                                                    | no aplica                                                                                                                                       | 31                                         | ninguna                                                                                                                                                        | scikit-learn LinearRegression                                            |
| GWR             | regresion ponderada geograficamente | GWR con penalizacion Ridge, kernel bisquare adaptativo                                                                                                      | si, como ponderacion explicita                        | bandwidth en [40, 500] vecinos; lambda en [0.01, 0.1, 1.0, 10.0]; intercepto no penalizado                                                 | si, dentro del entrenamiento de cada particion: bandwidth por AICc y lambda por validacion espacial anidada; nunca mirando el conjunto evaluado | 31 coeficientes locales por punto evaluado | Ridge sobre la formulacion clasica, necesario por la colinealidad entre variables de distancia                                                                 | implementacion propia (modelos/gwr/gwr_core.py) + mgwr para el bandwidth |
| GNNWR           | red que aprende la ponderacion      | Du et al. (2020): una red estima multiplicadores locales de los coeficientes globales                                                                       | si, como vector de distancias a todo el entrenamiento | capas [2048, 1024, 512, 256, 64], dropout 0.2, BatchNorm, Adadelta lr 0.2, decaimiento 0.001, lote 64, hasta 1000 epocas con paciencia 200 | no: configuracion tomada del articulo original y mantenida fija; no se exploro rejilla sobre estos datos                                        | 11056544                                   | estandarizacion en vez de minmax; parada temprana con 10% de validacion; recorte de gradiente. Equivalencia con el paquete de los autores: ver observacion 1.2 | implementacion propia en PyTorch                                         |
| SANNWR-adaptado | red que aprende la ponderacion      | Ni et al. (2022) adaptado: la entrada combina distancia espacial y atributiva con peso fijo 0,5/0,5                                                         | si, junto con distancia en el espacio de atributos    | identicos a GNNWR; alpha fijo en 0.5, no aprendido                                                                                         | no; alpha tampoco se ajusto                                                                                                                     | 11056544                                   | el diseno original integra ambas proximidades de forma aprendida; aqui es una combinacion lineal fija. Por eso el rotulo -adaptado                             | implementacion propia en PyTorch                                         |
| SANNWR-original | red que aprende la ponderacion      | Ni et al. (2022) sin adaptar: un SAPDNN (red 2 -> 4 -> 1 compartida entre pares) aprende a fundir la distancia espacial y la atributiva en una sola metrica | si, junto con distancia en el espacio de atributos    | identicos a GNNWR mas la capa oculta del SAPDNN (4)                                                                                        | no; la capa oculta se fijo de antemano                                                                                                          | 11056559                                   | ninguna estructural: es el diseno publicado. Se corre para medir que aporta el componente que la adaptacion sustituye (02d_sannwr_original.py)                 | implementacion propia en PyTorch                                         |
| RF              | aprendizaje automatico tabular      | bosque aleatorio sobre las mismas covariables, sin coordenadas                                                                                              | no                                                    | 300 arboles, resto por defecto de scikit-learn                                                                                             | no; valores por defecto declarados de antemano                                                                                                  | no comparable (estructura de arboles)      | ninguna                                                                                                                                                        | scikit-learn RandomForestRegressor                                       |

Comun a los cinco: objetivo: log(valor_m2); covariables: 27 variables, con uso de suelo en codificacion disyuntiva: 30 columnas; escalado: media 0 y desviacion 1 ajustadas solo con el entrenamiento de la particion; retransformacion: exp() con factor de smearing de Duan calculado en el entrenamiento; particiones: las mismas para los cinco modelos

### Frases que conviene reformular

| archivo               | linea | motivo                             | extracto                                                                                                                                                                                                 |
| --------------------- | ----- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| anexo_f.tex           | 40    | afirmacion de confirmacion         | e márgenes un 17\% más anchos que el que supone independencia, lo que confirma que ignorar la dependencia entre predios vecinos subestima la incertidumbre.                                              |
| cap5_resultados.tex   | 80    | atribuye superioridad a la familia |  Figura~\ref{fig:6} resume, es contundente y contrario a lo esperado: Random Forest gana por un margen amplio. Su RMSE de 76,99 queda casi dieciséis puntos por debajo del siguiente modelo, y lo consig |
| cap5_resultados.tex   | 146   | comparativo absoluto               | Sí & No & Uno es mejor que el otro \\                                                                                                                                                                    |
| cap5_resultados.tex   | 183   | atribuye superioridad a la familia | , donde SANNWR-adaptado, GWR y GNNWR aparecían indistinguibles y aquí SANNWR-adaptado gana por 4,4 USD/m$^{2}$. Las dos tablas miden errores distintos: aquella el error al cuadrado, que castiga sobre  |
| cap5_resultados.tex   | 541   | designacion de ganador             | es exploratorias produjo un RMSE de 72,88, que la habría situado como el mejor modelo del estudio. Sus diez réplicas posteriores dan 91,63 $\pm$ 12,16. La diferencia no se debe solo a la semilla, porq |
| cap6_conclusiones.tex | 72    | atribuye superioridad a la familia | o encabezan la validación espacial (GNNWR sin degradación, $-$0,3\%); Random Forest domina la interpolación; la significancia frente a los modelos sin ponderación espacial con cinco regiones no se alc |

Reformulacion sugerida: sustituir "X supera a Y" por "la implementacion de X
evaluada aqui obtiene menor error que la de Y en este conjunto", y reservar
"demuestra" para lo que la evidencia sostenga.

La tabla LaTeX lista para anexo esta en `fichas_implementacion.tex`.
