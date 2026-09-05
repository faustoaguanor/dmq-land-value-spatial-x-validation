# -*- coding: utf-8 -*-
"""
fig_flujo_operativo.py
======================
Dibuja el flujo operativo de siete pasos que describe la Seccion 5.7.9.

Sustituye a m10_recomendacion_territorial.png, que venia de la seccion aplicada
retirada del documento. Aquella figura asignaba un modelo a cada predio segun su
distancia al predio investigado mas cercano, con umbrales de 250 m y 1 km que no
aparecen en ninguna otra parte de la tesis, y contradecia al parrafo que la cita:
el texto subraya que el flujo NO asigna automaticamente un modelo segun el
soporte espacial.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).parent

plt.rcParams.update({"font.family": "serif", "figure.dpi": 150})

BORDE = "#4a5560"
TEXTO = "#26313a"

# Los siete pasos, en el orden en que los enumera el texto. El color agrupa las
# tres fases: preparar, estimar y comprobar antes de usar.
PASOS = [
    ("1", "Control de calidad\nde los datos",            "#dbe7ef"),
    ("2", "Definición del\nescenario de uso",            "#dbe7ef"),
    ("3", "Verificación del soporte\nen la zona a valorar", "#dbe7ef"),
    ("4", "Selección del modelo\nsegún ese escenario",   "#f6e2c4"),
    ("5", "Predicción con\nretransformación",            "#f6e2c4"),
    ("6", "Diagnóstico del error\ny del soporte",        "#d9e8dc"),
    ("7", "Revisión humana antes\nde cualquier uso",     "#d9e8dc"),
]

ANCHO, ALTO, SEP = 2.55, 1.30, 0.62
POR_FILA = 4


def caja(ax, x, y, num, txt, color):
    ax.add_patch(FancyBboxPatch(
        (x, y), ANCHO, ALTO, boxstyle="round,pad=0.035,rounding_size=0.10",
        linewidth=1.1, edgecolor=BORDE, facecolor=color, zorder=2))
    ax.text(x + 0.22, y + ALTO - 0.27, num, fontsize=11, fontweight="bold",
            color=BORDE, ha="center", va="center", zorder=3)
    ax.text(x + ANCHO / 2, y + ALTO / 2 - 0.08, txt, fontsize=10.2,
            color=TEXTO, ha="center", va="center", zorder=3, linespacing=1.45)


def flecha(ax, p0, p1, curva=0.0):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
        color=BORDE, zorder=1,
        connectionstyle=f"arc3,rad={curva}"))


def main():
    filas = [PASOS[:POR_FILA], PASOS[POR_FILA:]]
    ancho_fig = POR_FILA * ANCHO + (POR_FILA - 1) * SEP
    fig, ax = plt.subplots(figsize=(11.4, 3.9))

    pos = {}
    for f, fila in enumerate(filas):
        y = (len(filas) - 1 - f) * (ALTO + 1.35)
        # ambas filas se alinean a la izquierda: asi el salto de una a otra
        # cruza la banda vacia entre ellas sin pasar por detras de ninguna caja
        for i, (num, txt, color) in enumerate(fila):
            x = i * (ANCHO + SEP)
            caja(ax, x, y, num, txt, color)
            pos[num] = (x, y)

    # flechas dentro de cada fila
    for f, fila in enumerate(filas):
        for i in range(len(fila) - 1):
            a, b = fila[i][0], fila[i + 1][0]
            xa, ya = pos[a]
            xb, _ = pos[b]
            flecha(ax, (xa + ANCHO + 0.04, ya + ALTO / 2),
                   (xb - 0.04, ya + ALTO / 2))

    # Enlace entre filas, en codo por la banda vacia: baja desde la caja 4,
    # recorre el espacio libre hacia la izquierda y entra por arriba en la 5.
    x4, y4 = pos["4"]
    x5, y5 = pos["5"]
    banda = y5 + ALTO + (y4 - y5 - ALTO) / 2
    ax.plot([x4 + ANCHO / 2, x4 + ANCHO / 2], [y4 - 0.04, banda],
            color=BORDE, linewidth=1.2, zorder=4, solid_capstyle="round")
    ax.plot([x4 + ANCHO / 2, x5 + ANCHO / 2], [banda, banda],
            color=BORDE, linewidth=1.2, zorder=4, solid_capstyle="round")
    flecha(ax, (x5 + ANCHO / 2, banda), (x5 + ANCHO / 2, y5 + ALTO + 0.04))

    ax.text(ancho_fig / 2, -0.60,
            "El paso 4 aplica la regla de la Tabla 5.12; el flujo no asigna "
            "un modelo por predio según su distancia a la muestra.",
            fontsize=9.6, color="#6b7c8c", style="italic", ha="center")

    ax.set_xlim(-0.5, ancho_fig + 0.5)
    ax.set_ylim(-1.15, ALTO + 1.35 + ALTO + 0.25)
    ax.axis("off")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_flujo_operativo.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_flujo_operativo.png / .pdf")


if __name__ == "__main__":
    main()
