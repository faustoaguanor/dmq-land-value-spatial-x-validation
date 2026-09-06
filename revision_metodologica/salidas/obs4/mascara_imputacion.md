# Observacion 1.4 -- alcance de la imputacion previa a la particion

Celdas reconstruidas como imputadas: 433 en 4 variables, que afectan a 148 de 5051 predios (2.93%).

## Identificacion

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

## Reparto de las celdas afectadas

| variable         | n_celdas | en_entrenamiento | en_prueba | regiones_afectadas |
| ---------------- | -------- | ---------------- | --------- | ------------------ |
| frente_m         | 134      | 117              | 17        | 10                 |
| log_area         | 131      | 115              | 16        | 10                 |
| area_const_m2    | 131      | 115              | 16        | 10                 |
| pendiente_grados | 37       | 33               | 4         | 9                  |

## Desplazamiento de la mediana

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

## Que falta

Esta comprobacion acota la magnitud, no corrige el procedimiento. La correccion
es 04b_protocolo_en_fold.py: rehacer la evaluacion completa imputando dentro de
cada pliegue y comparar contra el mismo protocolo con imputacion global.
