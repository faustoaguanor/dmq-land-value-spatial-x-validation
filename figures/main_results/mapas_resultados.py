# -*- coding: utf-8 -*-
"""
mapas_resultados.py
===================
Rehace los cuatro mapas del capitulo de resultados con una base cartografica
comun. Sustituye a fig7_all_models_maps.py, mapa_deltas_voronoi.py y
mapa_soporte_superficie.py, cuyas salidas la revision rechazo por ilegibles.

Que fallaba en cada uno y como se corrige.

Precio observado y estimado. La barra de color era logaritmica y solo tenia
una marca, "10^2", de modo que el lector no podia traducir ningun color a un
precio. Ahora la escala es de clases discretas por cuantiles con los cortes
rotulados en USD/m2, que es lo que se lee de un vistazo.

Error absoluto. Eran 1,011 puntos superpuestos sobre fondo blanco: en el
nucleo consolidado los puntos se tapan unos a otros y el orden de dibujo
decide que color queda visible, de modo que no se distingue donde el error
es mayor. Se agrega a celdas, que es lo unico que elimina el solapamiento
sin inventar datos, y las cinco clases son las mismas en todos los paneles
para que los modelos sean comparables entre si.

Sesgo. Faltaban OLS y GWR, con lo que la figura contradecia al resto del
capitulo, y la rampa continua dejaba casi todas las celdas en blanco porque
unas pocas extremas se llevaban todo el rango. Entran los cinco modelos y la
escala pasa a clases discretas simetricas.

Soporte. Ocupaba una pagina entera para decir una sola cosa, y la rampa de
siete clases en rojo hacia que lo mas visible fuera la periferia sin datos,
justo lo que menos importa. Se reduce a las tres clases que corresponden a
una decision, dentro, margen y fuera, y ocupa un tercio del espacio.

Criterios comunes: clasificacion por cuantiles porque el precio y el error
son muy asimetricos y una rampa lineal deja el 80% de los predios en la
primera clase; limites parroquiales siempre visibles, porque sin ellos las
celdas flotan sobre un fondo sin referencias; y recorte al area con datos,
que evita dedicar dos tercios del papel al DMQ rural vacio.

Salidas: mapa_precio.png, mapa_error.png, mapa_sesgo.png, mapa_soporte.png
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# --- formato numerico espanol (anadido para alinear con el documento) ---
import locale as _loc
import matplotlib as _mpl
try:
    _loc.setlocale(_loc.LC_NUMERIC, "es_ES.UTF-8")
    _mpl.rcParams["axes.formatter.use_locale"] = True
except Exception:
    pass


def _es(txt):
    """Coma decimal y sin separador de millar."""
    return str(txt).replace(",", "").replace(".", ",")
# --- fin del bloque anadido ---

import matplotlib.patheffects as pe
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).parent
DATOS = ROOT / "figures" / "aplicacion_valoracion" / "map_data_holdout.csv"
CAPAS = ROOT.parent / "capas" / "PARROQUIAS_F.shp"

plt.rcParams.update({"font.family": "serif", "font.size": 10, "figure.dpi": 150})

# Nomenclatura vigente: la columna del gpkg conserva el nombre historico.
MODELOS = [("RF", "Random Forest"), ("SANNWR", "SANNWR-adaptado"), ("GWR-27", "GWR"),
           ("GNNWR", "GNNWR"), ("OLS", "OLS")]

TIERRA = "#f2f5f7"
BORDE_DMQ = "#8d9aa4"
BORDE_PARR = "#d5dde2"
MARCO = "#3d4852"
CELDA_M = 1200  # ancho entre lados opuestos del hexagono
MIN_PREDIOS = 3


# ───────────────────────────── base cartografica ──────────────────────────

_ZONAS = None


def cargar():
    d = pd.read_csv(DATOS)
    g = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.x, d.y), crs="EPSG:32717")
    parr = gpd.read_file(CAPAS).to_crs(32717)
    return g, parr, parr.geometry.union_all()


def cargar_zonas():
    """Centros de las ocho administraciones zonales del DMQ (Calderon, Centro,
    Chillos, Eloy Alfaro, La Delicia, Norte, Quitumbe, Tumbaco): la unica
    referencia de orientacion que tienen estos mapas ademas de la flecha de
    norte. Sin nombres de lugar un lector que no conoce Quito de memoria no
    puede ubicar el patron que el mapa muestra."""
    global _ZONAS
    if _ZONAS is None:
        p = gpd.read_file(CAPAS).to_crs(32717)
        z = p.dissolve("ZONA_ADMIN")
        # .values, no la GeoSeries: esta indexada por nombre de zona y la otra
        # columna por posicion, y gpd.GeoDataFrame alinea por indice al
        # construir, con lo que sin .values las geometrias salen todas None.
        pts = z.geometry.representative_point().values
        _ZONAS = gpd.GeoDataFrame({"nombre": [i.title() for i in z.index]},
                                  geometry=pts, crs=32717)
    return _ZONAS


def etiquetas_zonas(ax, extension, esquina_ocupada=False):
    """esquina_ocupada=True cuando el mismo panel ya lleva escala y norte en
    la esquina inferior izquierda: se omite ahi cualquier nombre de zona que
    caeria encima."""
    (x0, x1), (y0, y1) = extension
    z = cargar_zonas()
    dentro = z.cx[x0:x1, y0:y1]
    for nombre, pt in zip(dentro.nombre, dentro.geometry):
        fx = (pt.x - x0) / (x1 - x0)
        fy = (pt.y - y0) / (y1 - y0)
        if esquina_ocupada and fx < 0.22 and fy < 0.16:
            continue
        # Cerca del borde horizontal, un rotulo centrado se sale del panel y
        # el recorte de los ejes lo trunca ("Tumbaco" quedaba en "Tumbac"):
        # se ancla hacia el lado de donde hay espacio en vez de centrarlo.
        ha = "right" if fx > 0.90 else "left" if fx < 0.10 else "center"
        dx = -3 if ha == "right" else 3 if ha == "left" else 0
        ax.annotate(nombre, (pt.x, pt.y), xytext=(dx, 0),
                    textcoords="offset points", ha=ha, va="center",
                    fontsize=6.3, color="#6b7680", fontweight="bold",
                    fontstyle="italic", zorder=3.5,
                    path_effects=[pe.withStroke(linewidth=1.8,
                                                foreground="#ffffffcc")])


def marco(ax, dmq, parr, extension, primero=False):
    """Fondo comun: silueta del DMQ, parroquias, nombres de zona y recorte al
    area con datos. primero=True en el panel que ademas lleva escala y
    norte, para no superponer un nombre de zona encima de ellas."""
    gpd.GeoSeries([dmq], crs=32717).plot(ax=ax, facecolor=TIERRA,
                                         edgecolor=BORDE_DMQ, lw=0.7, zorder=0)
    parr.boundary.plot(ax=ax, color=BORDE_PARR, linewidth=0.25, alpha=0.75,
                       zorder=1)
    etiquetas_zonas(ax, extension, esquina_ocupada=primero)
    ax.set_xlim(*extension[0])
    ax.set_ylim(*extension[1])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(MARCO)
        s.set_linewidth(0.8)


def extension_datos(g, margen=1200):
    x, y = g.geometry.x, g.geometry.y
    xmin, xmax = np.percentile(x, [0.5, 99.5])
    ymin, ymax = np.percentile(y, [0.5, 99.5])
    return (xmin - margen, xmax + margen), (ymin - margen, ymax + margen)


def escala(ax, largo_m=5000):
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    xi = x0 + 0.06 * (x1 - x0)
    yi = y0 + 0.05 * (y1 - y0)
    ax.plot([xi, xi + largo_m], [yi, yi], color="#2b2b2b", lw=2.6,
            solid_capstyle="butt", zorder=6)
    ax.text(xi + largo_m / 2, yi + 0.016 * (y1 - y0), f"{largo_m // 1000} km",
            ha="center", va="bottom", fontsize=8, color="#2b2b2b", zorder=6)


def norte(ax):
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    x = x0 + 0.90 * (x1 - x0)
    y = y0 + 0.95 * (y1 - y0)
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.075 * (y1 - y0)),
                ha="center", va="center", fontsize=8, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="#2b2b2b", lw=0.9),
                zorder=6)


# Cortes en dolares por metro cuadrado, comunes al mapa de error y al de
# sesgo. Redondos a proposito: los cuantiles reparten las celdas en cinco
# grupos iguales, pero estiran el ultimo hasta el maximo, con lo que sale un
# "68 a 652" que no informa, y dan cortes distintos en cada figura, de modo
# que las dos dejan de ser comparables. Con estos el reparto sigue siendo
# razonable, 9, 31, 32, 19 y 9 por ciento de las celdas.
CORTES_ERROR = [0, 10, 25, 50, 100, np.inf]
CORTES_SESGO = [-np.inf, -50, -10, 10, 50, np.inf]
# Fijos y no por cuantiles: con cuantiles, 294 a 2253 USD/m2 (el 20% mas caro)
# cae en una sola clase y aplana justo el tramo donde los modelos difieren.
# Progresion geometrica (cada corte dobla al anterior) porque el precio es
# lognormal: reparte el rango de forma pareja en la escala en la que la
# variable realmente se distribuye. Abiertos en los dos extremos porque una
# prediccion puede caer fuera del rango observado.
CORTES_PRECIO = [-np.inf, 50, 100, 200, 400, 800, np.inf]


def rotulos_precio():
    return ["menos de 50", "50 a 100", "100 a 200", "200 a 400", "400 a 800",
            "más de 800"]


def rotulos_error():
    return ["menos de 10", "10 a 25", "25 a 50", "50 a 100", "más de 100"]


def rotulos_sesgo():
    return ["sobreestima más de 50", "sobreestima 10 a 50", "ajustada (± 10)",
            "subestima 10 a 50", "subestima más de 50"]


def rotulo(a, b, sufijo=""):
    fmt = (lambda v: f"{v:,.0f}") if abs(b) >= 10 else (lambda v: f"{v:.1f}")
    return f"{fmt(a)} – {fmt(b)}{sufijo}"


def leyenda_clases(fig, cortes, colores, titulo, ncol=None, y=0.055, rotulos=None):
    etiquetas = rotulos or [rotulo(cortes[i], cortes[i + 1])
                            for i in range(len(colores))]
    parches = [Patch(facecolor=c, edgecolor="#ffffff", linewidth=0.4, label=r)
               for c, r in zip(colores, etiquetas)]
    leg = fig.legend(handles=parches, loc="lower center",
                     ncol=ncol or len(parches), frameon=False,
                     bbox_to_anchor=(0.5, y), fontsize=9,
                     handlelength=1.5, handleheight=1.0,
                     columnspacing=1.4, title=titulo)
    leg.get_title().set_fontsize(9.5)
    return leg


def leyenda_hueco(ax, cortes, colores, titulo):
    """Coloca la leyenda en el panel que sobra de la retilla, en lugar de
    debajo: asi no roba altura a los mapas."""
    parches = [Patch(facecolor=c, edgecolor="#b9c2c8", linewidth=0.3,
                     label=rotulo(cortes[i], cortes[i + 1]))
               for i, c in enumerate(colores)]
    leg = ax.legend(handles=parches, loc="center", ncol=1, frameon=False,
                    fontsize=8.5, handlelength=1.5, handleheight=1.0,
                    title=titulo)
    leg.get_title().set_fontsize(9)
    return leg


def leyenda_rotulos(ax, rotulos, colores, titulo, extra=None):
    """Como leyenda_hueco, pero con los rotulos escritos en vez de deducidos
    de los cortes: con clases abiertas por un extremo, "mas de 100" se lee
    mejor que "100 a 652". extra anade handles ya construidos (p. ej. la
    clase "sin datos", que no comparte el estilo de borde de las demas)."""
    parches = [Patch(facecolor=c, edgecolor="#b9c2c8", linewidth=0.3, label=r)
               for c, r in zip(colores, rotulos)] + list(extra or [])
    leg = ax.legend(handles=parches, loc="center", ncol=1, frameon=False,
                    fontsize=8.5, handlelength=1.5, handleheight=1.0,
                    title=titulo)
    leg.get_title().set_fontsize(9)
    return leg


def rejilla(g, columnas, extent, dmq, resumen="mean"):
    """Malla hexagonal completa sobre 'extent', recortada al DMQ. Promedia
    observaciones medidas dentro de cada celda; no interpola, de modo que no
    aparece ningun valor donde no se evaluo ningun predio. Las celdas con
    menos de MIN_PREDIOS (incluidas las que no tienen ninguno) se conservan
    con n=0..2 y los promedios en NaN: donde no hay datos es un resultado, no
    un hueco que el lector confunde con el fondo del mapa.

    El hexagono tesela mejor que el cuadrado: sus seis vecinos equidistan,
    de modo que no privilegia las direcciones norte-sur y este-oeste, y el
    conjunto se lee como superficie en vez de como mosaico."""
    r_hex = CELDA_M / np.sqrt(3)          # circunradio
    ancho, alto = np.sqrt(3) * r_hex, 1.5 * r_hex

    h = g.copy()
    fila_h = np.round(h.geometry.y / alto).astype(int)
    desfase_h = (fila_h % 2) * ancho / 2  # filas impares medio paso a la derecha
    col_h = np.round((h.geometry.x - desfase_h) / ancho).astype(int)
    h["fila"], h["col"] = fila_h, col_h

    agg = {c: resumen for c in columnas}
    agg["predio_join"] = "size"
    datos = h.groupby(["fila", "col"]).agg(agg).rename(
        columns={"predio_join": "n"})

    (x0, x1), (y0, y1) = extent
    filas = range(int(np.floor(y0 / alto)) - 1, int(np.ceil(y1 / alto)) + 2)
    todas = []
    for f in filas:
        desfase = (f % 2) * ancho / 2
        c0 = int(np.floor((x0 - desfase) / ancho)) - 1
        c1 = int(np.ceil((x1 - desfase) / ancho)) + 2
        todas.extend((f, c) for c in range(c0, c1))
    d = pd.DataFrame(todas, columns=["fila", "col"]).set_index(["fila", "col"])
    d = d.join(datos).reset_index()
    d["n"] = d["n"].fillna(0).astype(int)

    ang = np.pi / 180 * np.array([90, 150, 210, 270, 330, 30])
    geom = []
    for f, c in zip(d.fila, d.col):
        cy = f * alto
        cx = c * ancho + (f % 2) * ancho / 2
        geom.append(Polygon(np.c_[cx + r_hex * np.cos(ang),
                                  cy + r_hex * np.sin(ang)]))
    cel = gpd.GeoDataFrame(d, geometry=geom, crs=g.crs)
    return cel[cel.intersects(dmq)]


def paneles(n, ext, col_in=2.55):
    """Dos filas de tres. En una sola fila de cinco cada mapa queda demasiado
    estrecho para distinguir las celdas; repartidos en dos filas cada panel
    triplica su area y el hueco sobrante aloja la leyenda.

    El alto se deriva de la proporcion del propio mapa, que es vertical
    (1:1.45). Fijandolo a ojo, la celda de la retilla sale apaisada y, al
    imponer la proporcion real, cada panel deja huecos a los lados."""
    razon = (ext[1][1] - ext[1][0]) / (ext[0][1] - ext[0][0])
    fig, axes = plt.subplots(2, 3, figsize=(3 * col_in,
                                            2 * col_in * razon + 0.55))
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    return fig, axes.ravel()


def guardar(fig, nombre):
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{nombre}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {nombre}.png / .pdf")


# ───────────────────────────────── mapas ──────────────────────────────────

def mapa_precio(g, parr, dmq, ext):
    """Precio observado y estimado por cada modelo, en clases fijas y con los
    modelos ordenados por MAE creciente: el orden de lectura coincide con el
    de la Tabla 5.1 en vez de con el orden arbitrario en que se entrenaron."""
    cmap = ListedColormap(plt.cm.viridis(np.linspace(0.08, 0.96,
                                                      len(CORTES_PRECIO) - 1)))
    norm = BoundaryNorm(CORTES_PRECIO, cmap.N)

    mae = {c: (g[f"pred_{c}"] - g.valor_m2).abs().mean() for c, _ in MODELOS}
    modelos_por_mae = sorted(MODELOS, key=lambda cn: mae[cn[0]])
    capas = [("valor_m2", "Observado")] + \
            [(f"pred_{c}", n) for c, n in modelos_por_mae]
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 8.6))
    for i, (ax, (col, nom)) in enumerate(zip(axes.ravel(), capas)):
        marco(ax, dmq, parr, ext, primero=(i == 0))
        # Borde fino en cada punto: sin el, el amarillo del extremo superior
        # se confunde con un hueco y el solape en el nucleo es ilegible.
        g.plot(ax=ax, column=col, cmap=cmap, norm=norm, markersize=5.5,
               linewidth=0.2, edgecolor="#2a2a2a", alpha=0.9, zorder=3)
        titulo = nom if col == "valor_m2" else f"{nom}   MAE {mae[col.replace('pred_', '')]:.0f}"
        ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=6)
    escala(axes[0, 0])
    norte(axes[0, 0])
    fig.subplots_adjust(bottom=0.09, wspace=0.03, hspace=0.08)
    leyenda_clases(fig, CORTES_PRECIO, [cmap(i) for i in range(cmap.N)],
                   "Precio del suelo (USD/m²), clases fijas en escala log₂",
                   y=0.005, rotulos=rotulos_precio())
    guardar(fig, "mapa_precio")


def mapa_error(g, parr, dmq, ext):
    """Error absoluto agregado a celdas, con clases comunes a los cinco."""
    cols = [f"err_{c}" for c, _ in MODELOS]
    cel = rejilla(g, cols, ext, dmq)
    vacias = cel[cel.n < MIN_PREDIOS]
    llenas = cel[cel.n >= MIN_PREDIOS]
    print(f"  error: {len(llenas)} celdas con datos de {len(cel)} en el DMQ, "
          f"{CELDA_M/1000:.1f} km de arista "
          f"({llenas.n.sum()} predios, {100*llenas.n.sum()/len(g):.0f}%)")

    cmap = ListedColormap(plt.cm.YlOrRd(np.linspace(0.06, 0.92, 5)))
    norm = BoundaryNorm(CORTES_ERROR[:-1] + [1e9], cmap.N)

    fig, axes = paneles(5, ext)
    for i, (ax, (col, nom)) in enumerate(zip(axes, MODELOS)):
        marco(ax, dmq, parr, ext, primero=(i == 0))
        # Celdas sin predios suficientes, dibujadas y no ausentes: donde no
        # hay datos es un resultado, y dejarlas en blanco se confunde con
        # "error nulo" en vez de "sin evidencia".
        vacias.plot(ax=ax, facecolor="#fdfdfc", edgecolor="#e2dfd9",
                    linewidth=0.2, zorder=2)
        llenas.plot(ax=ax, column=f"err_{col}", cmap=cmap, norm=norm,
                    edgecolor="none", zorder=3)
        ax.set_title(nom, fontsize=11.5, fontweight="bold", pad=6)
        v = llenas[f"err_{col}"]
        ax.text(0.035, 0.965, f"media zonal {v.mean():.0f}\np90 {v.quantile(0.9):.0f}",
                transform=ax.transAxes, ha="left", va="top", fontsize=8,
                color="#3d4852", linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.28", facecolor="#ffffff",
                          edgecolor="#d3dade", linewidth=0.5, alpha=0.9))
    escala(axes[0])
    norte(axes[0])
    fig.subplots_adjust(wspace=0.02, hspace=0.10, left=0.02, right=0.98,
                        top=0.95, bottom=0.02)
    sin_datos = Patch(facecolor="#fdfdfc", edgecolor="#e2dfd9", linewidth=0.6,
                      label="zona sin predios suficientes")
    leyenda_rotulos(axes[5], rotulos_error(), [cmap(i) for i in range(cmap.N)],
                    "Error absoluto medio\nde la zona (USD/m²)",
                    extra=[sin_datos])
    guardar(fig, "mapa_error")


def mapa_sesgo(g, parr, dmq, ext):
    """Sesgo con signo, agregado a celdas, en clases divergentes simetricas.
    La clase central es gris neutro: con beige competia visualmente con la
    subestimacion leve, que tambien es un tono calido."""
    cols = [f"resid_{c}" for c, _ in MODELOS]
    cel = rejilla(g, cols, ext, dmq)
    vacias = cel[cel.n < MIN_PREDIOS]
    llenas = cel[cel.n >= MIN_PREDIOS]
    cmap = ListedColormap(["#2c6fad", "#93bcda", "#e6e6e2", "#e79c86", "#b3402f"])
    norm = BoundaryNorm([-1e9] + CORTES_SESGO[1:-1] + [1e9], cmap.N)

    fig, axes = paneles(5, ext)
    for i, (ax, (col, nom)) in enumerate(zip(axes, MODELOS)):
        marco(ax, dmq, parr, ext, primero=(i == 0))
        vacias.plot(ax=ax, facecolor="#fdfdfc", edgecolor="#e2dfd9",
                    linewidth=0.2, zorder=2)
        # Borde en todas las celdas: sin el, las de la clase central se
        # confunden con el fondo y los paneles parecen tener distinto numero
        # de celdas cuando en realidad son las mismas en los cinco.
        llenas.plot(ax=ax, column=f"resid_{col}", cmap=cmap, norm=norm,
                    edgecolor="#b9c2c8", linewidth=0.25, zorder=3)
        ax.set_title(nom, fontsize=11.5, fontweight="bold", pad=6)
        s = llenas[f"resid_{col}"]
        ajustadas = 100 * (s.abs() <= 10).mean()
        ax.text(0.035, 0.965,
                f"{ajustadas:.0f}% de zonas ajustadas\nsesgo medio {s.mean():+.0f}",
                transform=ax.transAxes, ha="left", va="top", fontsize=8,
                color="#3d4852", linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.28", facecolor="#ffffff",
                          edgecolor="#d3dade", linewidth=0.5, alpha=0.9))
    escala(axes[0])
    norte(axes[0])

    parches = [Patch(facecolor=cmap(i), edgecolor="#b9c2c8", linewidth=0.3,
                     label=e) for i, e in enumerate(rotulos_sesgo())]
    parches.append(Patch(facecolor="#fdfdfc", edgecolor="#e2dfd9", linewidth=0.6,
                         label="zona sin predios suficientes"))
    fig.subplots_adjust(wspace=0.02, hspace=0.10, left=0.02, right=0.98,
                        top=0.95, bottom=0.02)
    leg = axes[5].legend(handles=parches, loc="center", ncol=1, frameon=False,
                         fontsize=8.5, handlelength=1.5, handleheight=1.0,
                         title="Diferencia media por zona\nentre el precio "
                               "observado y el estimado\n(USD/m²)")
    leg.get_title().set_fontsize(9)
    guardar(fig, "mapa_sesgo")


def mapa_soporte(parr, dmq):
    """Hasta donde llega el respaldo de la muestra sobre el territorio.

    Es una superficie y no una nube de puntos, y la distincion importa: la
    distancia al predio de entrenamiento mas cercano esta definida en
    cualquier punto del territorio y se calcula de forma exacta, de modo que
    dibujarla en una malla no interpola nada. Sobre los predios de prueba, en
    cambio, el mapa no dice nada util, porque el reparto los dejo intercalados
    con los de entrenamiento y el 90% cae dentro del soporte por construccion.
    La pregunta pertinente no es donde se evaluo sino donde podria valorarse
    un predio nuevo.

    Dos zonas y no tres. Se probo separar ademas la franja mas densa, la que
    queda a menos de la separacion tipica entre predios muestreados, pero
    cubre el 2% del distrito y se dibuja como un moteado ilegible mientras la
    clase exterior se come el 76% restante. Con una sola frontera, la del
    alcance de la dependencia espacial estimado en la Seccion 4.3.2, queda un
    limite que si se puede interpretar, y la densidad de la muestra se ve
    donde debe verse, en los propios predios dibujados encima.
    """
    from scipy.spatial import cKDTree
    from shapely import contains_xy

    PASO = 120
    ALCANCE_DEP = 2237    # alcance de la autocorrelacion residual, Seccion 4.3.2
    LIM_DEGRADE = 6000    # mas alla de esto, todo se funde con el fondo
    # Gradiente continuo y no cinco anillos. La distancia al predio mas
    # cercano es una funcion continua; escalonarla en cinco clases dibuja,
    # alrededor de cada predio rural aislado, un blanco de tiro concentrico
    # que no aporta nada, y con eso la figura se lee como cartografia de mala
    # calidad en vez de como lo que es. Con muchos niveles
    # finos el mismo dato se lee como superficie: oscuro cerca, y un
    # degradado que se apaga hacia el color de fondo mas alla del alcance de
    # la dependencia, para que el ojo se quede en la zona que importa.
    _cerca = LinearSegmentedColormap.from_list("", ["#0d2d40", "#9fc2d6"])
    _lejos = LinearSegmentedColormap.from_list("", ["#c9b48f", TIERRA])
    NIVELES = np.concatenate([np.linspace(0, ALCANCE_DEP, 13),
                              np.linspace(ALCANCE_DEP, LIM_DEGRADE, 10)[1:],
                              [1e9]])
    TONOS = []
    for a, b in zip(NIVELES[:-2], NIVELES[1:-1]):
        m = (a + b) / 2
        TONOS.append(_cerca(m / ALCANCE_DEP) if m <= ALCANCE_DEP
                     else _lejos(min((m - ALCANCE_DEP) /
                                     (LIM_DEGRADE - ALCANCE_DEP), 1.0)))
    TONOS.append(_lejos(1.0))

    d = gpd.read_file(ROOT / "datos" / "dataset.gpkg").to_crs(32717)
    d["predio_join"] = d["predio_join"].astype(int)
    sp = pd.read_csv(ROOT / "data_split" / "split.csv")
    sp["predio_join"] = sp["predio_join"].astype(int)
    d = d.merge(sp[["predio_join", "split"]], on="predio_join")
    tr = d[d.split == "train"]

    x0, y0, x1, y1 = dmq.bounds
    xs = np.arange(x0, x1 + PASO, PASO)
    ys = np.arange(y0, y1 + PASO, PASO)
    XX, YY = np.meshgrid(xs, ys)
    dist = cKDTree(np.c_[tr.geometry.x, tr.geometry.y]).query(
        np.c_[XX.ravel(), YY.ravel()])[0].reshape(XX.shape)

    # Solo cuenta el territorio del distrito, no el rectangulo que lo encierra.
    territorio = contains_xy(dmq, XX, YY)
    cubierto = float((dist[territorio] < ALCANCE_DEP).mean())

    razon = (y1 - y0) / (x1 - x0)
    fig, ax = plt.subplots(figsize=(5.2, 5.2 * razon + 0.95))
    # Sin el fondo comun: aqui las dos clases cubren el distrito entero y
    # una silueta debajo solo anadiria un tercer tono.
    ax.set_xlim(x0 - 900, x1 + 900)
    ax.set_ylim(y0 - 900, y1 + 900)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    etiquetas_zonas(ax, ((x0 - 900, x1 + 900), (y0 - 900, y1 + 900)),
                    esquina_ocupada=True)
    # Relleno por curvas de nivel: la distancia al predio mas cercano es una
    # funcion continua, de modo que la frontera puede trazarse interpolando a
    # lo largo de la malla en vez de escalonarse en pixeles.
    campo = np.where(territorio, dist, np.nan)
    ax.contourf(xs, ys, campo, levels=NIVELES, colors=TONOS,
                zorder=2, antialiased=True)
    # La frontera del alcance de la dependencia separa las tres clases con
    # respaldo de las dos sin el, y es la unica que el texto usa: se traza.
    ax.contour(xs, ys, campo, levels=[ALCANCE_DEP], colors="#1f3b4d",
               linewidths=1.0, zorder=3)
    parr.boundary.plot(ax=ax, color="#9aa5ad", linewidth=0.4, zorder=4)
    gpd.GeoSeries([dmq], crs=32717).boundary.plot(ax=ax, color="#2b3840",
                                                  linewidth=1.0, zorder=5)
    escala(ax)
    norte(ax)

    fig.subplots_adjust(bottom=0.125, top=0.99, left=0.02, right=0.98)
    # Dos franjas y no cinco: el gradiente ya muestra la graduacion fina en
    # el mapa mismo, y la leyenda solo necesita decir cual de las dos
    # regiones es cual y que fraccion del distrito ocupa cada una.
    manos = [
        Patch(facecolor=_cerca(0.35), edgecolor="#b9c2c8", linewidth=0.3,
              label=f"dentro del alcance de la dependencia (< {ALCANCE_DEP} m)"
                    f"   {100*cubierto:.0f}%"),
        Patch(facecolor=_lejos(0.45), edgecolor="#b9c2c8", linewidth=0.3,
              label=f"fuera del alcance (≥ {ALCANCE_DEP} m)"
                    f"   {100*(1-cubierto):.0f}%"),
        Line2D([], [], color="#1f3b4d", linewidth=1.0,
              label=f"frontera del alcance de la dependencia espacial "
                    f"({ALCANCE_DEP} m)"),
    ]
    leg = fig.legend(
        handles=manos,
        loc="lower center", ncol=1, frameon=False, bbox_to_anchor=(0.5, 0.005),
        fontsize=8, handlelength=1.4, handleheight=0.95,
        title="Distancia al predio de entrenamiento más cercano")
    leg.get_title().set_fontsize(8.5)
    guardar(fig, "mapa_soporte")
    print(f"    con respaldo {100*cubierto:.1f}%, sin respaldo "
          f"{100*(1-cubierto):.1f}%")


def main():
    g, parr, dmq = cargar()
    ext = extension_datos(g)
    print(f"  {len(g)} predios evaluados")
    mapa_precio(g, parr, dmq, ext)
    mapa_error(g, parr, dmq, ext)
    mapa_sesgo(g, parr, dmq, ext)
    mapa_soporte(parr, dmq)


if __name__ == "__main__":
    main()
