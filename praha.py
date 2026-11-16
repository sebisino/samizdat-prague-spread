"""
2D mapa Prahy rozdělená na 22 správních obvodů (Praha 1 – Praha 22).

Hranice obvodů: RÚIAN (ČÚZK), soubor praha_obvody.json.
Souřadnice jsou v kilometrech, (0, 0) = jihozápadní roh Prahy,
osa x = východ, osa y = sever (Praha má cca 34 × 25 km).

Počty obyvatel: ČSÚ, Správní obvody hl. m. Prahy, stav k 31. 12. 2023.

Použití:
    from praha import nahodna_pozice
    obvod, (x, y) = nahodna_pozice()
"""

import json
import os
import random

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

OBYVATEL = {
    "Praha 1": 28_718,
    "Praha 2": 51_171,
    "Praha 3": 80_761,
    "Praha 4": 145_709,
    "Praha 5": 98_923,
    "Praha 6": 120_203,
    "Praha 7": 48_920,
    "Praha 8": 122_814,
    "Praha 9": 67_067,
    "Praha 10": 117_999,
    "Praha 11": 87_489,
    "Praha 12": 70_846,
    "Praha 13": 71_428,
    "Praha 14": 53_242,
    "Praha 15": 52_740,
    "Praha 16": 25_823,
    "Praha 17": 32_671,
    "Praha 18": 35_798,
    "Praha 19": 14_991,
    "Praha 20": 18_175,
    "Praha 21": 19_029,
    "Praha 22": 20_215,
}

_SOUBOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "praha_obvody.json")
with open(_SOUBOR, encoding="utf-8") as _f:
    POLYGONY = {jmeno: [tuple(p) for p in body] for jmeno, body in json.load(_f).items()}

CELKEM_OBYVATEL = sum(OBYVATEL.values())

# pravděpodobnost, že náhodný člověk bydlí v daném obvodu
PRAVDEPODOBNOST = {jmeno: pocet / CELKEM_OBYVATEL for jmeno, pocet in OBYVATEL.items()}

# obdélník kolem každého obvodu (pro rychlé losování bodů)
_OBDELNIKY = {
    jmeno: (min(x for x, _ in p), max(x for x, _ in p), min(y for _, y in p), max(y for _, y in p))
    for jmeno, p in POLYGONY.items()
}


# ---------------------------------------------------------------------------
# Geometrie
# ---------------------------------------------------------------------------

def bod_v_polygonu(x, y, polygon):
    """Ray casting: True, pokud bod (x, y) leží uvnitř polygonu."""
    uvnitr = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                uvnitr = not uvnitr
    return uvnitr


def plocha(polygon):
    """Plocha polygonu v km² (shoelace formula)."""
    n = len(polygon)
    s = sum(polygon[i][0] * polygon[(i + 1) % n][1] - polygon[(i + 1) % n][0] * polygon[i][1]
            for i in range(n))
    return abs(s) / 2


def nahodny_bod_v_obvodu(jmeno):
    """Úplně náhodný (rovnoměrný) bod uvnitř obvodu – rejection sampling."""
    polygon = POLYGONY[jmeno]
    min_x, max_x, min_y, max_y = _OBDELNIKY[jmeno]
    while True:
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)
        if bod_v_polygonu(x, y, polygon):
            return (x, y)


# ---------------------------------------------------------------------------
# Hlavní funkce pro simulaci
# ---------------------------------------------------------------------------

def nahodny_obvod():
    """Vybere obvod s pravděpodobností obyvatel_obvodu / obyvatel_Prahy."""
    return random.choices(list(PRAVDEPODOBNOST), weights=list(PRAVDEPODOBNOST.values()))[0]


def nahodna_pozice():
    """Vrátí (obvod, (x, y)) – nejdřív losuje obvod, pak náhodné místo v něm."""
    obvod = nahodny_obvod()
    return obvod, nahodny_bod_v_obvodu(obvod)


def obvod_bodu(x, y):
    """Zjistí, ve kterém obvodu bod leží (nebo None, pokud je mimo Prahu)."""
    for jmeno, polygon in POLYGONY.items():
        if bod_v_polygonu(x, y, polygon):
            return jmeno
    return None


# ---------------------------------------------------------------------------
# Vykreslení (matplotlib)
# ---------------------------------------------------------------------------

def nakresli_mapu(ax=None, barvy_podle_hustoty=True, popisky=True):
    """Nakreslí obvody do matplotlib os `ax` (vytvoří nové, pokud ax=None). Vrací ax."""
    import matplotlib.pyplot as plt
    from matplotlib import patheffects
    from matplotlib.patches import Polygon

    if ax is None:
        _, ax = plt.subplots(figsize=(11, 8.5))

    hustoty = {j: OBYVATEL[j] / plocha(p) for j, p in POLYGONY.items()}
    max_h = max(hustoty.values())
    cmap = plt.get_cmap("YlOrRd")

    for jmeno, polygon in POLYGONY.items():
        barva = cmap(0.1 + 0.8 * hustoty[jmeno] / max_h) if barvy_podle_hustoty else "#eeeeee"
        ax.add_patch(Polygon(polygon, closed=True, facecolor=barva,
                             edgecolor="#333333", linewidth=0.8))
        if popisky:
            # popisek do středu obdélníku, posunutý dovnitř obvodu, pokud je mimo
            min_x, max_x, min_y, max_y = _OBDELNIKY[jmeno]
            cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
            if not bod_v_polygonu(cx, cy, polygon):
                cx = sum(x for x, _ in polygon) / len(polygon)
                cy = sum(y for _, y in polygon) / len(polygon)
            ax.text(cx, cy, jmeno.replace("Praha ", "P"), ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#222222",
                    path_effects=[patheffects.withStroke(linewidth=2.5, foreground="white")])

    ax.set_xlim(-0.5, 34.5)
    ax.set_ylim(-0.5, 25.2)
    ax.set_aspect("equal")
    ax.set_xlabel("x [km]")
    ax.set_ylabel("y [km]")

    if barvy_podle_hustoty:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, max_h))
        ax.figure.colorbar(sm, ax=ax, shrink=0.6, label="hustota obyvatel [obyv./km²]")
    return ax


def nakresli_lidi(pozice, ax=None, **kwargs):
    """Nakreslí mapu a body lidí. `pozice` = seznam (x, y). Vrací ax."""
    ax = nakresli_mapu(ax)
    if pozice:
        xs, ys = zip(*pozice)
        nastaveni = {"s": 2, "c": "black", "alpha": 0.6}
        nastaveni.update(kwargs)
        ax.scatter(xs, ys, **nastaveni)
    return ax


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    print(f"Celkem obyvatel: {CELKEM_OBYVATEL:,}".replace(",", " "))
    for jmeno, p in PRAVDEPODOBNOST.items():
        print(f"{jmeno:9s} {p:6.2%}   plocha {plocha(POLYGONY[jmeno]):5.1f} km²")

    lide = [nahodna_pozice() for _ in range(5000)]
    ax = nakresli_lidi([pos for _, pos in lide])
    ax.set_title("Praha – 22 správních obvodů, 5000 náhodně rozmístěných lidí")
    plt.tight_layout()
    plt.savefig("praha.png", dpi=150)
    print("Uloženo do praha.png")
    plt.show()
