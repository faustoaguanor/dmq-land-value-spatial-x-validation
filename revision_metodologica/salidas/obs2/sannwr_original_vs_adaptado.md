# Observacion 1.1 (evidencia) -- el SANNWR publicado bajo el mismo protocolo

La observacion pide rotular la implementacion como SANNWR-adaptado. Esta tabla
aporta lo que el rotulo por si solo no dice: que habria dado el diseno de Ni et
al. (2022), con su SAPDNN aprendiendo la fusion de las dos distancias, corrido
sobre las mismas particiones y en la misma maquina.

Semillas por esquema: ConjuntoDePrueba20: 10; BloquesEspaciales: 5. RMSE en USD/m2 con smearing por particion.

## Comparacion

| esquema            | SANNWR-adaptado | SANNWR-original | diferencia | dif_pct |
| ------------------ | --------------- | --------------- | ---------- | ------- |
| BloquesEspaciales  | 97.76           | 105.72          | 7.97       | 8.2     |
| ConjuntoDePrueba20 | 95.28           | 95.96           | 0.68       | 0.7     |

## Detalle por esquema

| esquema            | modelo          | RMSE    | RMSE_sd | MAE    | R2    | moran_I | pliegues | minutos |
| ------------------ | --------------- | ------- | ------- | ------ | ----- | ------- | -------- | ------- |
| BloquesEspaciales  | SANNWR-adaptado | 97.758  | 45.095  | 60.878 | 0.607 | 0.431   | 5        | 82.9    |
| BloquesEspaciales  | SANNWR-original | 105.723 | 50.897  | 64.535 | 0.551 | 0.424   | 5        | 81.5    |
| ConjuntoDePrueba20 | SANNWR-adaptado | 95.279  | 5.551   | 46.489 | 0.817 | 0.087   | 1        | 38.1    |
| ConjuntoDePrueba20 | SANNWR-original | 95.963  | 4.471   | 46.875 | 0.815 | 0.124   | 1        | 36.3    |

## Como redactarlo

Si el diseno publicado no mejora a la adaptacion, la frase honesta es que la
simplificacion 0,5/0,5 no perjudico en este conjunto, y que por tanto los
resultados no deben leerse como una evaluacion de SANNWR sino de una variante
suya que aqui rinde igual o mejor. Si lo mejora, hay que decir que la
implementacion evaluada subestima a la arquitectura publicada y acotar en cuanto.
En cualquiera de los dos casos el rotulo -adaptado se mantiene: describe lo que
se implemento, no lo que rindio.
