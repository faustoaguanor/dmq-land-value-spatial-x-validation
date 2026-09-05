# Importancia de variables con colinealidad alta

La advertencia del documento es correcta y aqui queda respaldada con medicion
propia, no solo enunciada.

## VIF: 7 de 30 variables por encima de 25

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

## Grupos de variables correlacionadas (corte 1-|rho| <= 0.4)

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

## Importancia individual frente a importancia del grupo

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

## Cinco primeras por modelo (permutacion individual)

| modelo | variable          | delta_RMSE | sd    |
| ------ | ----------------- | ---------- | ----- |
| RF     | dist_cc           | 122.991    | 9.556 |
| RF     | dist_parque_metro | 57.733     | 8.699 |
| RF     | dist_centr_metro  | 50.919     | 1.44  |
| RF     | dist_metro        | 43.725     | 2.597 |
| RF     | dist_industrial   | 38.946     | 4.86  |

## Como redactarlo

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
