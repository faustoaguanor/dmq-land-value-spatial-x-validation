# Observacion 1.6 -- tamano efectivo de la muestra

Conjunto de prueba: 1011 predios. Ese numero no es el numero de
observaciones independientes disponibles para inferir diferencias de
generalizacion espacial.

## Cuantas observaciones independientes hay realmente

| criterio                                  | n_localizaciones |
| ----------------------------------------- | ---------------- |
| separacion > rango de residuales (2530 m) | 59               |
| separacion > rango del valor (5621,8 m)   | 22               |
| bloques espaciales                        | 5                |
| regiones de la validacion externa         | 10               |
| predios (nominal)                         | 1011             |

## Autocorrelacion del error y tamano efectivo

| variable                       | n    | moran_I | moran_p | rho0   | rango_m | n_efectivo | pct_del_nominal |
| ------------------------------ | ---- | ------- | ------- | ------ | ------- | ---------- | --------------- |
| error absoluto OLS             | 1011 | 0.5228  | 0.001   | 1.0    | 1990.8  | 22.8       | 2.3             |
| error absoluto GWR             | 1011 | 0.4304  | 0.001   | 0.9649 | 1891.6  | 25.5       | 2.5             |
| error absoluto GNNWR           | 1011 | 0.4539  | 0.001   | 0.988  | 1838.2  | 26.1       | 2.6             |
| error absoluto SANNWR-adaptado | 1011 | 0.3632  | 0.001   | 0.7764 | 1850.5  | 32.6       | 3.2             |
| error absoluto RF              | 1011 | 0.3472  | 0.001   | 0.6433 | 1933.7  | 36.6       | 3.6             |

## Pruebas pareadas bajo los tres supuestos

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

## Comparaciones que dejan de ser significativas al corregir

- GWR frente a RF: p pasa de 0.0000 a 0.0560 al usar n efectivo = 66 en lugar de 1011.

## Como redactarlo

Formula sugerida para el documento: los 1011 predios de prueba equivalen, por la
dependencia espacial del error, a un numero mucho menor de observaciones
independientes; y cuando lo que se quiere inferir es generalizacion a zonas
nuevas, la unidad de analisis no es el predio sino la region, de las que hay
cinco o diez. Las pruebas pareadas sobre predios individuales deben leerse como
descriptivas y no como inferencia sobre capacidad de generalizacion espacial.
