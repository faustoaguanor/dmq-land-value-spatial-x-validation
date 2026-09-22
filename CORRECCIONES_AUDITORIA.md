# Correcciones posteriores a la auditoría local

Base pública: v2.8 (`d1306d3`); base primaria: `1859569`; base de la tesis: `594d864`. Las correcciones se publican posteriormente bajo la etiqueta `entrega-2026-09-21`, conservando las etiquetas de base.

1. **H1:** sensibilidad al tamaño efectivo regenerada desde las predicciones actuales; p sin ajustar de GWR–GNNWR 0,058025 y GNNWR–RF 0,060626. Holm sobre diez parejas da aproximadamente 0,224104 en ambas. La t pareada con Holm sigue dando 0,018354 para GWR–GNNWR bajo independencia; texto y anexos distinguen ambos procedimientos.
2. **H2:** mapas y tabla territorial reconstruidos con el factor GNNWR 1,012768190 calculado del train. En la región 2, MAE 70,8620 y sesgo observado−predicho 22,6418. RF conserva el menor MAE de las cinco regiones. Los medianos de la tabla se refieren explícitamente a los predios de prueba. Datos por predio y cartografía restringida permanecen en el repositorio privado.
3. **H3:** rango estricto, puestos de SANNWR, interpretación de Moran, diferencia entre error por bloques y error operativo, y CRS almacenado/proyectado corregidos en texto y documentación.
4. **H4:** checkpoints identificados por hash y dimensiones, con los límites de recarga y de disponibilidad de vectores documentados. No se alteran pesos ni se promete recuperar ejecuciones ausentes.

Los nuevos controles verifican factor calculado exclusivamente sobre train, alineación por ID y rechazo de claves duplicadas, particiones u objetivos incompatibles y valores no finitos. La comprobación de cierre local conserva registros, copia de los archivos anteriores y hashes de los datos y resultados protegidos.

En la corrección inicial no se reentrenaron modelos ni se modificaron datos/particiones o métricas de entrenamiento; su publicación se registra en la etiqueta de entrega. La auditoría original se conserva como instantánea previa; el registro de cierre documenta esta corrección.

## Entrega del 21 de septiembre de 2026

Versión `entrega-2026-09-21`, acompañada por el código corregido y un PDF compilado desde las fuentes LaTeX vigentes. Se precisó el entorno local frente al pod histórico y se documentó la identidad de los trece resultados GNNWR con su retorno y commit de integración. Los registros también documentan una recarga satisfactoria dentro del pod; los pesos no se exportaron. No se modificaron datos, particiones, predicciones, métricas de entrenamiento ni checkpoints. La versión de entrega se identifica mediante `VERSION_ENTREGA.json`; corresponde a la etiqueta pública del mismo nombre.

## Sincronización con GitHub

La etiqueta `entrega-2026-09-21` publica el código, la documentación y los resultados agregados verificados. Se excluye la máscara de imputación por observación y se conservan sus resúmenes por variable y partición. Se mantienen fuera de la publicación los datos originales, predicciones individuales, pesos y logs del pod. El PDF y su código adjunto identifican esta misma etiqueta.
