# Observacion 1.2 -- equivalencia estructural

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

## Divergencias declaradas frente a la especificacion publicada

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
