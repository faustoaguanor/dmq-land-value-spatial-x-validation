# Observacion 1.4 -- imputacion dentro de cada pliegue

Mascara reconstruida: 433 celdas en 4 variables (frente_m, log_area, area_const_m2, pendiente_grados).
Semillas [42]; los dos brazos comparten semilla y particion.
Modelos consolidados en esta tabla: GNNWR, GWR, OLS, RF, SANNWR-adaptado, SANNWR-original.
Esquemas: BloquesEspaciales, ConjuntoDePrueba20, RandomKFold.

## Comparacion pareada

| esquema            | modelo          | MAE_en_fold | MAE_global | RMSE_en_fold | RMSE_global | delta_RMSE | delta_pct | puesto_global | puesto_en_fold | cambia_de_puesto |
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
| RandomKFold        | GNNWR           | 46.413      | 46.037     | 91.111       | 90.371      | 0.74       | 0.82      | 2             | 3              | True             |
| RandomKFold        | GWR             | 48.135      | 48.513     | 96.519       | 97.243      | -0.724     | -0.74     | 5             | 4              | True             |
| RandomKFold        | OLS             | 74.592      | 74.592     | 141.656      | 141.656     | 0.0        | 0.0       | 6             | 6              | False            |
| RandomKFold        | RF              | 38.935      | 38.926     | 81.563       | 81.547      | 0.016      | 0.02      | 1             | 1              | False            |
| RandomKFold        | SANNWR-adaptado | 45.498      | 45.729     | 90.826       | 91.892      | -1.066     | -1.16     | 3             | 2              | True             |
| RandomKFold        | SANNWR-original | 50.031      | 47.544     | 100.81       | 95.35       | 5.46       | 5.73      | 4             | 5              | True             |

## Resumen por brazo

| brazo   | esquema            | modelo          | RMSE    | RMSE_sd_pliegues | MAE    | R2    | pliegues |
| ------- | ------------------ | --------------- | ------- | ---------------- | ------ | ----- | -------- |
| en_fold | BloquesEspaciales  | GNNWR           | 97.775  | 52.978           | 59.239 | 0.637 | 5        |
| en_fold | BloquesEspaciales  | GWR             | 108.488 | 58.323           | 66.596 | 0.55  | 5        |
| en_fold | BloquesEspaciales  | OLS             | 135.767 | 74.078           | 82.453 | 0.27  | 5        |
| en_fold | BloquesEspaciales  | RF              | 107.901 | 59.307           | 66.136 | 0.564 | 5        |
| en_fold | BloquesEspaciales  | SANNWR-adaptado | 99.141  | 50.267           | 60.241 | 0.6   | 5        |
| en_fold | BloquesEspaciales  | SANNWR-original | 101.863 | 52.832           | 63.515 | 0.559 | 5        |
| en_fold | ConjuntoDePrueba20 | GNNWR           | 99.28   |                  | 48.99  | 0.802 | 1        |
| en_fold | ConjuntoDePrueba20 | GWR             | 96.771  |                  | 48.122 | 0.812 | 1        |
| en_fold | ConjuntoDePrueba20 | OLS             | 139.01  |                  | 72.295 | 0.612 | 1        |
| en_fold | ConjuntoDePrueba20 | RF              | 76.595  |                  | 37.494 | 0.882 | 1        |
| en_fold | ConjuntoDePrueba20 | SANNWR-adaptado | 92.488  |                  | 44.714 | 0.828 | 1        |
| en_fold | ConjuntoDePrueba20 | SANNWR-original | 95.877  |                  | 46.798 | 0.815 | 1        |
| en_fold | RandomKFold        | GNNWR           | 91.111  | 10.221           | 46.413 | 0.835 | 5        |
| en_fold | RandomKFold        | GWR             | 96.519  | 7.362            | 48.135 | 0.814 | 5        |
| en_fold | RandomKFold        | OLS             | 141.656 | 7.531            | 74.592 | 0.601 | 5        |
| en_fold | RandomKFold        | RF              | 81.563  | 3.795            | 38.935 | 0.867 | 5        |
| en_fold | RandomKFold        | SANNWR-adaptado | 90.826  | 6.159            | 45.498 | 0.836 | 5        |
| en_fold | RandomKFold        | SANNWR-original | 100.81  | 9.363            | 50.031 | 0.797 | 5        |
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
| global  | RandomKFold        | GNNWR           | 90.371  | 11.196           | 46.037 | 0.837 | 5        |
| global  | RandomKFold        | GWR             | 97.243  | 7.983            | 48.513 | 0.811 | 5        |
| global  | RandomKFold        | OLS             | 141.656 | 7.529            | 74.592 | 0.601 | 5        |
| global  | RandomKFold        | RF              | 81.547  | 3.789            | 38.926 | 0.867 | 5        |
| global  | RandomKFold        | SANNWR-adaptado | 91.892  | 7.529            | 45.729 | 0.832 | 5        |
| global  | RandomKFold        | SANNWR-original | 95.35   | 6.937            | 47.544 | 0.819 | 5        |

## Lectura

Lo que decide es la columna de cambio de puesto: si el ordenamiento entre modelos
se mantiene, la fuga de la imputacion previa no sostiene ninguna conclusion del
documento y basta con declararla; si cambia, hay que reportar el brazo en_fold
como resultado principal.

## Lo que este brazo no corrige

Queda una decision de preprocesamiento que sigue tomandose sobre el conjunto
completo: el colapso de las categorias raras de uso de suelo en la codificacion
disyuntiva, que cuenta frecuencias sobre las 5051 filas. No mira el objetivo y es
determinista, pero en sentido estricto tampoco esta dentro del pliegue. Se declara
aqui por la misma razon por la que se declara la imputacion.
