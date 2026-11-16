import math
import random
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import to_rgba_array
from matplotlib.lines import Line2D
from matplotlib.widgets import Button, TextBox

from praha import nahodna_pozice, nakresli_mapu


meter = 0.001

choices = ["writer", "snitch", "reader", "neutral"]
tendencies = ["reader", "snitch", "writer"]
after_fear_choices = ["snitch", "neutral"]


# ---------------------------------------------------------------------------
# Nastavení – výchozí hodnoty (dají se změnit v okně Settings před startem)
# ---------------------------------------------------------------------------
CFG = {
    "people": 100000,
    "choices_weights": [0.2, 0.1, 0.3, 0.4],     # writer, snitch, reader, neutral
    "tendency_weights": [0.6, 0.2, 0.2],         # reader, snitch, writer
    "after_fear_weights": [0.2, 0.8],            # snitch, neutral
    "writer_range": 100,                         # metry
    "reader_range": 50,
    "snitch_range": 25,
    "fear_range": 60,
    "writer_strength": 5,                        # kolik přidá sousedovi do tendency
    "reader_strength": 1,
    "snitch_strength": 2,
    "fear_max": 80,
    "tendency_max": 80,
    "multiplier": [1, 3],                        # rozsah fear/tendency multiplieru
    "jail_weeks": 52 * 3,
    "jail_trauma": 20,                           # o kolik klesne fear_max po vězení
    "start_credibility": [20, 30],               # snitch na začátku
    "new_credibility": [50, 100],                # nově vzniklý snitch
    "weeks_per_frame": 1,
}

# (klíč, popisek, typ) – pořadí políček v okně Settings
FIELDS = [
    ("people", "People", int),
    ("choices_weights", "Start roles: writer, snitch, reader, neutral", list),
    ("tendency_weights", "Tendency: reader, snitch, writer", list),
    ("after_fear_weights", "After fear: snitch, neutral", list),
    ("writer_range", "Writer range [m]", float),
    ("reader_range", "Reader range [m]", float),
    ("snitch_range", "Snitch range [m]", float),
    ("fear_range", "Fear range [m]", float),
    ("writer_strength", "Writer strength", float),
    ("reader_strength", "Reader strength", float),
    ("snitch_strength", "Snitch strength", float),
    ("fear_max", "Fear max", float),
    ("tendency_max", "Tendency max", float),
    ("multiplier", "Multiplier min, max", list),
    ("jail_weeks", "Jail time [weeks]", int),
    ("jail_trauma", "Jail trauma (fear_max drop)", float),
    ("start_credibility", "Snitch credibility at start: min, max", list),
    ("new_credibility", "New snitch credibility: min, max", list),
    ("weeks_per_frame", "Weeks per animation frame", int),
]

# kolik čísel musí mít seznamová políčka
LIST_LENGTHS = {"choices_weights": 4, "tendency_weights": 3, "after_fear_weights": 2,
                "multiplier": 2, "start_credibility": 2, "new_credibility": 2}


def credibility(key):
    low, high = CFG[key]
    return random.randint(int(low), int(high))


class Person:
    def __init__(self):

        self.district, self.position = nahodna_pozice()

        self.fear_max = CFG["fear_max"]
        self.tendency_max = CFG["tendency_max"]

        self.online = True

        self.fear = 0
        self.first_role = random.choices(choices, weights=CFG["choices_weights"])[0]
        self.current_role = self.first_role
        self.snitch_credibility = None if self.current_role != "snitch" else credibility("start_credibility")

        self.emotions = False if self.current_role == "snitch" else True

        self.fear_multiplier = random.uniform(*CFG["multiplier"])

        self.tendency = 0
        self.tendency_role = random.choices(tendencies, weights=CFG["tendency_weights"])[0]
        self.tendency_multiplier = random.uniform(*CFG["multiplier"])

        self.is_in_jail = False
        self.jail_time = 0

    def max_fear(self):
        self.current_role = random.choices(after_fear_choices, weights=CFG["after_fear_weights"])[0]
        self.snitch_credibility = None if self.current_role != "snitch" else credibility("new_credibility")
        self.emotions = False if self.current_role == "snitch" else True
        self.fear = 0

    def max_tendency(self):
        self.current_role = self.tendency_role
        self.snitch_credibility = None if self.current_role != "snitch" else credibility("new_credibility")
        self.emotions = False if self.current_role == "snitch" else True
        self.tendency = 0
        self.fear /= 2

    def out_of_jail(self):
        self.current_role = random.choices(choices, weights=CFG["choices_weights"])[0]
        self.emotions = False if self.current_role == "snitch" else True
        self.is_in_jail = False
        self.jail_time = 0
        self.fear_max = max(self.fear_max - CFG["jail_trauma"], 10)
        self.snitch_credibility = None if self.current_role != "snitch" else credibility("new_credibility")


# ---------------------------------------------------------------------------
# Příprava simulace (zavolá se po stisknutí Start)
# ---------------------------------------------------------------------------
characters = []
snitched = set()  # kazdy jen jednou
grid = {}


def cell_of(position):
    x, y = position
    return (int(x // CELL), int(y // CELL))


def neighbors_of(p):
    cx, cy = cell_of(p.position)
    neighbors = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for q in grid.get((cx + dx, cy + dy), []):
                neighbors.append(q)
    return neighbors


def setup_simulation():
    global characters, ticks_in_jail, writer_range, reader_range, snitch_range, fear_range
    global CELL, tendency_updates

    ticks_in_jail = CFG["jail_weeks"]
    writer_range = meter * CFG["writer_range"]
    reader_range = meter * CFG["reader_range"]
    snitch_range = meter * CFG["snitch_range"]
    fear_range = meter * CFG["fear_range"]
    tendency_updates = {"writer": [CFG["writer_strength"], writer_range],
                        "reader": [CFG["reader_strength"], reader_range],
                        "snitch": [CFG["snitch_strength"], snitch_range]}

    # velikost čtverce = největší dosah, aby stačilo hledat ve 3×3 čtvercích
    CELL = max(writer_range, reader_range, snitch_range, fear_range)

    print(f"Creating {CFG['people']} people...")
    characters = [Person() for _ in range(CFG["people"])]

    grid.clear()
    for p in characters:
        grid.setdefault(cell_of(p.position), []).append(p)

    # Lidé se nehýbou -> sousedy a vzdálenosti spočítáme JEDNOU na začátku.
    print("Finding neighbours...")
    for p in characters:
        p.near = []
        for q in neighbors_of(p):
            if q is not p:
                d = math.dist(p.position, q.position)
                if d <= CELL:
                    p.near.append((q, d))
    print("Done.")


# ---------------------------------------------------------------------------
# Simulace
# ---------------------------------------------------------------------------
def decide(character):

    if character in snitched or character.is_in_jail:
        return 0, 0, None
    if character.current_role == "snitch" and character.snitch_credibility <= 0:
        return 0, 0, None

    fear_update = 0
    tendency_update = 0
    for nbr, dist in character.near:
        if not nbr.online:
            continue
        if nbr.is_in_jail:
            if nbr.jail_time == 1 and dist <= fear_range:
                fear_update += 1
        elif nbr.current_role != "neutral" and dist <= tendency_updates[nbr.current_role][1]:
            tendency_update += tendency_updates[nbr.current_role][0]

    target = None
    if character.current_role == "snitch":
        snitchables = [nbr for nbr, dist in character.near if nbr.online and not nbr.is_in_jail and nbr.current_role in ["writer", "reader"] and dist <= snitch_range]
        if snitchables:
            target = random.choice(snitchables)
    return fear_update, tendency_update, target


def apply(character, fear_update, tendency_update, target):

    if character in snitched:
        character.is_in_jail = True
        character.jail_time = 0
        return
    if character.is_in_jail:
        character.jail_time += 1
        if character.jail_time >= ticks_in_jail:
            character.out_of_jail()
        return
    if character.current_role == "snitch" and character.snitch_credibility <= 0:
        character.online = False   # vyhořelý snitch
        return
    if target is not None:
        character.snitch_credibility -= 1

    character.fear += fear_update * character.fear_multiplier
    character.tendency += tendency_update * character.tendency_multiplier
    if character.emotions:
        if character.fear >= character.fear_max:
            character.max_fear()
        elif character.tendency >= character.tendency_max:
            character.max_tendency()


def tick():

    active = [c for c in characters if c.online]

    results = [decide(c) for c in active]

    for character, (fear_update, tendency_update, target) in zip(active, results):
        apply(character, fear_update, tendency_update, target)

    # udaní z tohoto týdne jdou do vězení až příští týden
    snitched.clear()
    for _, _, target in results:
        if target is not None:
            snitched.add(target)


# ---------------------------------------------------------------------------
# Okno Settings
# ---------------------------------------------------------------------------
def format_value(value):
    if isinstance(value, list):
        return ", ".join(f"{v:g}" for v in value)
    return f"{value:g}"


def parse_value(key, text, kind):
    if kind is list:
        values = [float(v) for v in text.replace(";", ",").split(",") if v.strip()]
        if len(values) != LIST_LENGTHS[key]:
            raise ValueError(f"needs {LIST_LENGTHS[key]} numbers")
        if key.endswith("weights") and (any(v < 0 for v in values) or sum(values) == 0):
            raise ValueError("weights must be >= 0 and not all 0")
        if not key.endswith("weights") and values[0] > values[1]:
            raise ValueError("min must be <= max")
        return values
    value = kind(float(text))
    if value < 0 or (key in ("people", "weeks_per_frame") and value < 1):
        raise ValueError("too small")
    return value


def settings_window():
    """Ukáže okno s nastavením. Vrátí True po stisknutí Start, False po zavření okna."""
    fig = plt.figure("Settings", figsize=(8, 9))
    fig.text(0.5, 0.965, "Samizdat simulation – settings", ha="center", fontsize=14, weight="bold")

    boxes = {}
    top, step = 0.91, 0.042
    for i, (key, label, _) in enumerate(FIELDS):
        box_ax = fig.add_axes([0.58, top - i * step, 0.34, 0.032])
        boxes[key] = TextBox(box_ax, label + "  ", initial=format_value(CFG[key]))
        boxes[key].label.set_fontsize(9)

    error_text = fig.text(0.5, 0.075, "", ha="center", color="red", fontsize=10)
    start_ax = fig.add_axes([0.38, 0.02, 0.24, 0.045])
    start_button = Button(start_ax, "Start", color="#b7e4c7", hovercolor="#74c69d")

    started = {"value": False}

    def on_start(_event):
        new_cfg = {}
        for key, label, kind in FIELDS:
            try:
                new_cfg[key] = parse_value(key, boxes[key].text, kind)
            except ValueError as e:
                error_text.set_text(f"{label}: {e}")
                fig.canvas.draw_idle()
                return
        CFG.update(new_cfg)
        started["value"] = True
        plt.close(fig)

    start_button.on_clicked(on_start)
    plt.show()          # čeká, dokud se okno nezavře
    return started["value"]


# ---------------------------------------------------------------------------
# Animace
# ---------------------------------------------------------------------------
COLORS = {
    "writer": "#d62728",   # červená
    "reader": "#ff9f1c",   # oranžová
    "snitch": "#6a3d9a",   # fialová
    "neutral": "#9ecae1",  # světle modrá
}
JAIL_COLOR = "black"
OFFLINE_COLOR = "#888888"  # šedé tečky = vyhořelí snitchové

# každý stav má číslo -> barvy a počty se pak počítají rychle přes numpy
STATES = list(COLORS) + ["in jail", "offline"]
STATE_COLORS = list(COLORS.values()) + [JAIL_COLOR, OFFLINE_COLOR]
ROLE_CODE = {role: i for i, role in enumerate(COLORS)}
JAIL_CODE = STATES.index("in jail")
OFFLINE_CODE = STATES.index("offline")
PALETTE = to_rgba_array(STATE_COLORS)


def state_code(c):
    if not c.online:
        return OFFLINE_CODE
    if c.is_in_jail:
        return JAIL_CODE
    return ROLE_CODE[c.current_role]


def state_codes():
    return np.fromiter((state_code(c) for c in characters), dtype=np.int8, count=len(characters))


def run_animation():
    # --- okno 1: mapa ---
    ax = nakresli_mapu(barvy_podle_hustoty=False, popisky=False)
    fig = ax.figure
    fig.canvas.manager.set_window_title("Map")
    codes = state_codes()
    scatter = ax.scatter([c.position[0] for c in characters],
                         [c.position[1] for c in characters],
                         s=4, facecolors=PALETTE[codes], linewidths=0, zorder=3)
    ax.legend(handles=[Line2D([], [], marker="o", linestyle="", color=col, label=name)
                       for name, col in zip(STATES, STATE_COLORS)],
              loc="upper right", fontsize=8)

    # --- okno 2: graf rolí v čase ---
    fig2, ax2 = plt.subplots(figsize=(9, 5), num="Roles over time")
    weeks = []
    history = {name: [] for name in STATES}
    lines = {name: ax2.plot([], [], color=col, label=name, linewidth=1.8)[0]
             for name, col in zip(STATES, STATE_COLORS)}
    ax2.set_xlabel("week")
    ax2.set_ylabel("number of people")
    ax2.set_title("Roles over time")
    ax2.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    ax2.grid(alpha=0.3)
    fig2.tight_layout()

    state = {"week": 0, "paused": False}

    def frame(_):
        for _ in range(CFG["weeks_per_frame"]):
            tick()
            state["week"] += 1
        week = state["week"]

        codes = state_codes()
        scatter.set_facecolor(PALETTE[codes])
        counts = np.bincount(codes, minlength=len(STATES))

        ax.set_title(f"Week {week} (year {week // 52 + 1})   "
                     + "   ".join(f"{name} {n}" for name, n in zip(STATES, counts)),
                     fontsize=9)

        weeks.append(week)
        for name, n in zip(STATES, counts):
            history[name].append(n)
            lines[name].set_data(weeks, history[name])
        ax2.relim()
        ax2.autoscale_view()
        fig2.canvas.draw_idle()
        return (scatter,)

    anim = FuncAnimation(fig, frame, interval=1, cache_frame_data=False)

    # mezerník = pauza / pokračovat
    def on_key(event):
        if event.key == " ":
            if state["paused"]:
                anim.resume()
            else:
                anim.pause()
            state["paused"] = not state["paused"]

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig2.canvas.mpl_connect("key_press_event", on_key)

    plt.show()


if __name__ == "__main__":
    if settings_window():
        setup_simulation()
        run_animation()
