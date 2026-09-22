# Observacion 1.6 -- tamano efectivo de la muestra

Conjunto de prueba: 1011 predios. Ese numero no es el numero de
observaciones independientes disponibles para inferir diferencias de
generalizacion espacial.

## Localizaciones separadas y unidades descriptivas (no prueba de independencia)

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
| error absoluto GNNWR           | 1011 | 0.4404  | 0.001   | 0.9656 | 1911.4  | 25.1       | 2.5             |
| error absoluto SANNWR-adaptado | 1011 | 0.3632  | 0.001   | 0.7764 | 1850.5  | 32.6       | 3.2             |
| error absoluto RF              | 1011 | 0.3472  | 0.001   | 0.6433 | 1933.7  | 36.6       | 3.6             |

## Pruebas pareadas bajo los tres supuestos

| modelo_a        | modelo_b        | dif_media_MAE      | n_nominal | p_nominal              | n_efectivo         | reduccion_pct | p_con_n_efectivo       | p_con_n_efectivo_holm | p_por_bloque         | p_por_region         |
| --------------- | --------------- | ------------------ | --------- | ---------------------- | ------------------ | ------------- | ---------------------- | --------------------- | -------------------- | -------------------- |
| OLS             | GWR             | 23.504745344635296 | 1011      | 6.369690974208867e-25  | 119.44140290412345 | 88.2          | 0.0004055883142682153  | 0.003650294828413938  | 0.010625951470122286 | 0.015608205838662487 |
| OLS             | GNNWR           | 25.99019006060793  | 1011      | 1.681332441605907e-25  | 129.61072530131537 | 87.2          | 0.00019146095830481502 | 0.0019146095830481502 | 0.013754568348209229 | 0.01847256170622937  |
| OLS             | SANNWR-adaptado | 27.95311967508503  | 1011      | 5.406131886293635e-25  | 102.68549220020913 | 89.8          | 0.0010279718212062752  | 0.008223774569650202  | 0.018788957653856263 | 0.0264498615147376   |
| OLS             | RF              | 34.68208183600414  | 1011      | 6.670149113976715e-38  | 39.51674438294651  | 96.1          | 0.011526359640533218   | 0.07920512475621014   | 0.01920997672721982  | 0.02660491294755983  |
| GWR             | GNNWR           | 2.4854447159726294 | 1011      | 0.009177204913727342   | 535.3675759346297  | 47.0          | 0.058025210901010045   | 0.22410406086033702   | 0.1076009154074284   | 0.12210670298870499  |
| GWR             | SANNWR-adaptado | 4.44837433044973   | 1011      | 0.00014037597983471872 | 447.6642026301019  | 55.7          | 0.011315017822315733   | 0.07920512475621014   | 0.1145894992171428   | 0.17387518966451415  |
| GWR             | RF              | 11.177336491368838 | 1011      | 6.841384656468993e-14  | 66.28223308228523  | 93.4          | 0.056026015215084254   | 0.22410406086033702   | 0.048566571729597295 | 0.06977890110310041  |
| GNNWR           | SANNWR-adaptado | 1.9629296144771007 | 1011      | 0.07117975081206401    | 601.7185796670578  | 40.5          | 0.16399601061242214    | 0.22410406086033702   | 0.20121061219681116  | 0.2980926934700855   |
| GNNWR           | RF              | 8.691891775396208  | 1011      | 7.63963379201766e-10   | 94.49941074060432  | 90.7          | 0.06062559717240639    | 0.22410406086033702   | 0.04873034653120292  | 0.07043368390320645  |
| SANNWR-adaptado | RF              | 6.728962160919106  | 1011      | 1.3092581347638045e-05 | 257.4202590513737  | 74.5          | 0.0279711110305878     | 0.139855555152939     | 0.027029770944647046 | 0.039091968176376356 |

## Comparaciones que dejan de ser significativas al corregir

- GWR frente a GNNWR: p pasa de 0.0092 a 0.0580 al usar n efectivo = 535 en lugar de 1011.
- GWR frente a RF: p pasa de 0.0000 a 0.0560 al usar n efectivo = 66 en lugar de 1011.
- GNNWR frente a RF: p pasa de 0.0000 a 0.0606 al usar n efectivo = 94 en lugar de 1011.

## Como redactarlo

Formula sugerida para el documento: los 1011 predios de prueba equivalen, por la
dependencia espacial del error, a un numero mucho menor de observaciones
independientes; y cuando lo que se quiere inferir es generalizacion a zonas
nuevas, la unidad de analisis no es el predio sino la region, de las que hay
cinco particiones o diez zonas de estratificacion. Ninguna particion garantiza independencia.
El tamano efectivo es una sensibilidad aproximada bajo un correlograma ajustado.
Holm se calcula sobre diez parejas; no convierte esta sensibilidad en una prueba espacial definitiva.
Las pruebas pareadas sobre predios individuales deben leerse como
descriptivas y no como inferencia sobre capacidad de generalizacion espacial.
