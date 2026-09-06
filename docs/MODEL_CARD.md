# Ficha de modelos

## Propósito

Comparar modelos de predicción del precio de oferta del suelo urbano bajo interpolación y separación espacial en el Distrito Metropolitano de Quito.

## Modelos comparados

- OLS: referencia lineal global.
- GWR: regresión local con ancho de banda seleccionado dentro de cada partición e intercepto no penalizado.
- Random Forest: control tabular no espacial fuerte.
- GNNWR: red que aprende pesos a partir de la proximidad geográfica. Es una reimplementación basada en Du et al. (2020); realiza la operación que define a GNNWR, pero no reproduce numéricamente el paquete de sus autores.
- SANNWR-adaptado: ponderación neuronal espacial y atributiva con `alpha=0.5` fijo. El diseño de Ni et al. (2022) aprende esa combinación en vez de fijarla; lo evaluado aquí es la variante simplificada, y ninguna cifra valida la arquitectura publicada.

## Usos previstos

- Investigación sobre validación espacial y fuga de información geográfica.
- Comparación reproducible de arquitecturas bajo un protocolo común.
- Apoyo metodológico preliminar para diseñar evaluaciones catastrales.

## Usos no autorizados por la evidencia

- Avalúo catastral automático u oficial.
- Determinación de impuestos u obligaciones individuales.
- Predicción fuera del soporte geográfico observado sin revisión humana.
- Interpretación causal de la importancia de variables.

## Limitaciones principales

- Precios de oferta, no transacciones consumadas.
- Un solo período de mercado, sin validación temporal independiente.
- Cinco regiones espaciales y una única geometría de bloques.
- Multicolinealidad severa entre variables de accesibilidad.
- Autocorrelación residual significativa en los cinco modelos.
- Tendencia a subestimar sectores de mayor valor.
- El conjunto de prueba fue reutilizado durante el desarrollo y se interpreta como evidencia descriptiva interna.
- Las dos arquitecturas neuronales son implementaciones propias, una reimplementación y una adaptación, de modo que los resultados describen estas implementaciones concretas y no validan las publicadas.

## Revisión humana

Ninguna predicción debe convertirse directamente en una decisión catastral. Cualquier aplicación institucional requiere validación externa, auditoría territorial, análisis de equidad, documentación normativa y revisión por especialistas del Municipio.
