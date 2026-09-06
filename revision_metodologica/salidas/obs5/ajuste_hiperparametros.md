# Ajuste de hiperparametros de los modelos de arboles

La objecion era que Random Forest corrio con los valores por defecto mientras
GWR ajustaba los suyos dentro de cada particion. Aqui se le da el mismo trato:
validacion cruzada espacial anidada dentro del entrenamiento, criterio MAE en
USD/m2, rejilla declarada de antemano, sin mirar el conjunto evaluado.

Modelos: RF, HGB. Semillas: [42].

## Por defecto frente a ajustado

| esquema            | modelo | MAE_ajustado | MAE_defecto | RMSE_ajustado | RMSE_defecto | ganancia_RMSE | ganancia_pct |
| ------------------ | ------ | ------------ | ----------- | ------------- | ------------ | ------------- | ------------ |
| BloquesEspaciales  | HGB    | 65.314       | 64.358      | 105.663       | 105.8        | 0.137         | 0.13         |
| BloquesEspaciales  | RF     | 62.45        | 66.087      | 103.967       | 107.854      | 3.887         | 3.6          |
| ConjuntoDePrueba20 | HGB    | 38.908       | 40.316      | 77.563        | 80.794       | 3.231         | 4.0          |
| ConjuntoDePrueba20 | RF     | 37.507       | 37.507      | 76.638        | 76.638       | 0.0           | 0.0          |
| ValidacionAleatoria        | HGB    | 39.185       | 40.448      | 78.338        | 80.988       | 2.65          | 3.27         |
| ValidacionAleatoria        | RF     | 39.456       | 38.926      | 81.782        | 81.547       | -0.235        | -0.29        |

## Configuraciones que elige el procedimiento

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

## Detalle

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

## Como leerlo

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
