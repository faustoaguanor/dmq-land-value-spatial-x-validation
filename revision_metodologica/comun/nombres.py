"""
nombres.py -- etiquetas canonicas de modelo (observaciones 1.1 y 1.5).

Regla: en todo lo que produzca esta revision, la implementacion evaluada de
SANNWR se rotula SANNWR-adaptado, porque combina la distancia espacial y la
atributiva con pesos fijos 0.5/0.5 en vez de aprender su integracion como en
Ni et al. (2022). La etiqueta 'SANNWR' queda reservada para la arquitectura
publicada, que aqui se implementa aparte como SANNWR-original: SAPDNN, una red
2 -> h -> 1 que aprende a fundir la distancia espacial con la atributiva en una
sola metrica antes de entregarsela a la SWNN. Lo mismo, en menor grado, para GNNWR: se rotula la implementacion
propia, no el paquete de referencia (ver observacion 1.2).
"""

OLS = "OLS"
GWR = "GWR"
GNNWR = "GNNWR"
SANNWR = "SANNWR-adaptado"
SANNWR_ORIG = "SANNWR-original"      # SAPDNN de Ni et al. (2022): la fusion se aprende
RF = "RF"
HGB = "HGB"

# Los cinco de la tesis. Es el conjunto por defecto de los experimentos.
MODELOS = [OLS, GWR, GNNWR, SANNWR, RF]
# Con el SANNWR publicado incluido: lo que hace falta para sostener el rotulo
# "adaptado" con evidencia y no solo con una nota al pie.
MODELOS_TODOS = [OLS, GWR, GNNWR, SANNWR, SANNWR_ORIG, RF, HGB]
# Los que admiten ajuste de hiperparametros por rejilla en esta revision.
AJUSTABLES = [RF, HGB]
# Deterministas: dada la particion, la semilla no cambia el resultado. OLS es
# exacto y GWR selecciona bandwidth y penalizacion de forma determinista. Correr
# varias semillas con ellos produce filas identicas y gasta tiempo de maquina.
DETERMINISTAS = [OLS, GWR]

# Etiquetas historicas de los CSV del repositorio -> etiqueta canonica.
EQUIVALENCIAS = {
    "OLS": OLS,
    "GWR": GWR, "GWR-27": GWR, "GWR27": GWR,
    "GNNWR": GNNWR,
    "SANNWR": SANNWR, "SANNWR-real": SANNWR, "SANNWR-alpha": SANNWR,
    "SANNWR-original": SANNWR_ORIG, "SANNWR-SAPDNN": SANNWR_ORIG,
    "RF": RF, "RandomForest": RF,
    "HGB": HGB, "HistGBM": HGB,
}

# Estas NO son la implementacion evaluada: son otras cosas.
NO_EQUIVALENTES = {
    "SANNWR*": "variante de grilla 20x20 (Anexo), no es SANNWR-adaptado",
    "GWR-17": "GWR con 17 variables (Anexo)",
    "GSAWR": "arquitectura distinta (Anexo)",
    "MLP": "red no espacial (Anexo)",
}


def canonico(etiqueta: str) -> str:
    return EQUIVALENCIAS.get(str(etiqueta).strip(), str(etiqueta).strip())
