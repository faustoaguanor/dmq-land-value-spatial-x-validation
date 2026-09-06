# Observacion 1.2 -- comparacion con la implementacion de referencia

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

## Referencia de variabilidad propia

La implementacion de la tesis, con 10 semillas, da un RMSE entre 92.52 y 102.92 USD/m2 (media 98.08, desviacion 3.56).
Si la corrida del paquete cae dentro de ese rango, la diferencia entre
implementaciones no es distinguible del ruido de inicializacion; si cae fuera,
el resultado depende de la implementacion y debe enunciarse asi.

## Como redactarlo

Con esta evidencia, la formula defendible es: "la implementacion de GNNWR
evaluada aqui obtiene ...". Solo si la corrida del paquete cae dentro del rango
entre semillas cabe hablar de GNNWR sin calificar, y aun asi conviene declarar
que la comparacion se hizo con una sola version del paquete y un solo conjunto.
