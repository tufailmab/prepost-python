# Floor Plan Generator v 3.0
# Developer: Tufail Mabood
# WhatsApp: +923440907874, +923400740460
# 5000 Floor Plans in 50$ only with Bubble Diagram

import glob
import math
import sys
import types
import os
import datetime
from collections import defaultdict

try:
    import ezdxf
except ImportError:
    sys.exit("Please install ezdxf:  pip install ezdxf --break-system-packages")

try:
    from shapely.geometry import Polygon, LineString, box, Point
    from shapely.ops import polygonize, unary_union, nearest_points
    from shapely.affinity import scale as shp_scale
except ImportError:
    sys.exit("Please install shapely:  pip install shapely --break-system-packages")

try:
    import networkx as nx
except ImportError:
    sys.exit("Please install networkx:  pip install networkx --break-system-packages")


# =============================================================================
# CONFIG - edit these values directly, then press Run (F5) in IDLE.
# Nothing here needs a command line.
# =============================================================================

DXF_PATH = None
SETBACK_FT = 5.0
UNITS = "in"
BEDROOMS = 10
PLANS = 50
AUDIT_LAYER = None
AUTO_MODE = True
OUTDIR = "."
LIVE = False
LIVE_TIMEOUT = 1.0
ROOM_CONNECTIONS_OVERRIDE = None
ENTRANCE_SIDE = "N"
CORRIDOR_WIDTH_FT = 3

EXTERIOR_ROOM_TYPES = ["attached bath", "kitchen", "laundry", "guest room",
                        "foyer", "lounge", "study"]

VENT_ROOM_TYPES = ["attached bath", "kitchen", "laundry"]

MIN_SENSIBLE_REGULARITY = 0.55

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
class Logger:
    """Simple logger that writes all output to both console and a log file."""
    def __init__(self, log_dir="Logs"):
        self.log_dir = log_dir
        self.log_file = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = os.path.join(log_dir, f"dxf_plot_advisor_{timestamp}.log")

        self.log_file = open(self.log_filename, 'w', encoding='utf-8')

        self.log_file.write(f"{'='*70}\n")
        self.log_file.write(f"DXF PLOT ADVISOR LOG\n")
        self.log_file.write(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log_file.write(f"{'='*70}\n\n")

        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.original_stdout.write(message)
        if self.log_file and not self.log_file.closed:
            self.log_file.write(message)
            self.log_file.flush()

    def flush(self):
        self.original_stdout.flush()
        if self.log_file and not self.log_file.closed:
            self.log_file.flush()

    def close(self):
        if self.log_file and not self.log_file.closed:
            self.log_file.write(f"\n{'='*70}\n")
            self.log_file.write(f"Log ended: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"{'='*70}\n")
            self.log_file.close()

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        print(f"\nLog file saved to: {self.log_filename}")

# ---------------------------------------------------------------------------
# Matplotlib backend selection - SAFE BY DEFAULT.
# ---------------------------------------------------------------------------
LIVE_BACKEND_OK = False

try:
    import matplotlib
    if LIVE:
        for _backend in ("MacOSX", "QtAgg", "Qt5Agg", "TkAgg"):
            try:
                matplotlib.use(_backend, force=True)
                import matplotlib.pyplot as plt
                _probe = plt.figure()
                plt.close(_probe)
                LIVE_BACKEND_OK = True
                break
            except Exception:
                continue
        if not LIVE_BACKEND_OK:
            matplotlib.use("Agg", force=True)
    else:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Please install matplotlib:  pip install matplotlib --break-system-packages")


ROOM_STANDARDS = {
    "bedroom":        (14, 16, 224, "Master/ bedroom - comfortable at 12x14 or larger"),
    "attached bath":  (5,  7,  35,  "Attached washroom"),
    "dressing":       (5,  6,  30,  "Walk-in dressing / wardrobe"),
    "kitchen":        (10,  10, 120, "Working kitchen"),
    "laundry":        (5,  6,  30,  "Laundry / utility"),
    "guest room":     (12, 12, 144, "Guest bedroom, ideally near entrance"),
    "study":          (8,  10, 80, "Study / home office"),
    "store":          (5,  6,  30,  "Press / store room"),
    "lounge":         (14, 14, 196, "Family lounge / living room"),
    "foyer":          (6,  8,  48,  "Entrance lobby"),
    "stair":          (6,  20,  120,  "Staircase incl. landing"),
}

DEFAULT_ADJACENCY = {
    "foyer":          ["lounge", "guest room", "stair"],
    "lounge":         ["foyer", "kitchen", "stair", "study"],
    "kitchen":        ["lounge", "laundry", "store"],
    "laundry":        ["kitchen", "store"],
    "store":          ["kitchen", "laundry"],
    "stair":          ["foyer", "lounge"],
    "guest room":     ["foyer"],
    "study":          ["lounge"],
    "bedroom":        ["stair"],
}

TYPE_COLORS = {
    "bedroom":        "#8ecae6",
    "attached bath":  "#a2d2ff",
    "dressing":       "#bde0fe",
    "kitchen":        "#ffb703",
    "laundry":        "#ffd166",
    "guest room":     "#90be6d",
    "study":          "#f4a261",
    "store":          "#cdb4db",
    "lounge":         "#e76f51",
    "foyer":          "#457b9d",
    "stair":          "#6d6875",
}

PLAN_PRESETS = [
    ("Repack", 0.10, 0),
]

SIDES = ("N", "S", "E", "W")
SIDE_LABELS = {"N": "North / top", "S": "South / bottom", "E": "East / right", "W": "West / left"}

def create_output_folders(base_dir="."):
    folders = {
        "bubble_diagrams": os.path.join(base_dir, "Bubble Diagrams"),
        "floor_plans": os.path.join(base_dir, "Floor Plans"),
        "logs": os.path.join(base_dir, "Logs")
    }
    for folder_path in folders.values():
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"  Created folder: {folder_path}")
    return folders

def find_dxf_in_cwd():
    return sorted(glob.glob("*.dxf"))


def resolve_dxf_path(cli_path, auto_mode):
    if cli_path:
        return cli_path
    candidates = find_dxf_in_cwd()
    if not candidates:
        sys.exit("No DXF path given and no .dxf files found in the current folder.\n"
                  "Either place a .dxf here or run: python3 dxf_plot_advisor.py yourfile.dxf")
    if len(candidates) == 1:
        print(f"No path given - using the only DXF found in this folder: {candidates[0]}")
        return candidates[0]

    print("Multiple DXF files found in this folder:")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. {c}")
    if auto_mode:
        print(f"(--auto set: using the first one -> {candidates[0]})")
        return candidates[0]
    try:
        choice = input(f"Which one? [1-{len(candidates)}]: ").strip()
        idx = int(choice) - 1
        if idx < 0 or idx >= len(candidates):
            raise ValueError
        return candidates[idx]
    except (ValueError, EOFError):
        print(f"(No valid selection - defaulting to {candidates[0]})")
        return candidates[0]


def load_boundary_polygon(doc):
    msp = doc.modelspace()

    for e in msp.query("LWPOLYLINE"):
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) >= 3:
            return Polygon(pts)

    for e in msp.query("POLYLINE"):
        pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        if len(pts) >= 3:
            return Polygon(pts)

    segs = []
    for e in msp.query("LINE"):
        a = (round(e.dxf.start.x, 4), round(e.dxf.start.y, 4))
        b = (round(e.dxf.end.x, 4), round(e.dxf.end.y, 4))
        if a != b:
            segs.append((a, b))
    if not segs:
        return None

    lines = [LineString([a, b]) for a, b in segs]
    merged = unary_union(lines)
    polys = list(polygonize(merged))
    if not polys:
        return None
    return max(polys, key=lambda p: p.area)


UNIT_TABLE = {"ft": 1.0, "in": 1 / 12.0, "m": 3.28084, "mm": 1 / 304.8}


def units_scale(doc, cli_units):
    if cli_units:
        if cli_units not in UNIT_TABLE:
            sys.exit(f"Unknown --units '{cli_units}'. Choose from: {list(UNIT_TABLE)}")
        return UNIT_TABLE[cli_units], f"--units {cli_units} (you specified this)"

    insunits = doc.header.get("$INSUNITS", 0)
    mapping = {1: ("in", 1 / 12.0), 2: ("ft", 1.0), 4: ("mm", 1 / 304.8), 6: ("m", 3.28084)}
    if insunits in mapping:
        label, scale = mapping[insunits]
        return scale, f"$INSUNITS header says '{label}'"

    print("  (Could not auto-detect drawing units from $INSUNITS - "
          "assuming FEET. Pass --units in/ft/m/mm if this is wrong.)")
    return 1.0, "no unit info in file - assumed feet by default"


def sanity_check_scale(poly_raw, chosen_scale, decided_by):
    minx, miny, maxx, maxy = poly_raw.bounds
    raw_w, raw_h = maxx - minx, maxy - miny
    w, h = raw_w * chosen_scale, raw_h * chosen_scale

    implausible = max(w, h) > 500 or max(w, h) < 8
    if not implausible:
        return

    print(f"  WARNING: with units decided by [{decided_by}], the plot comes out to "
          f"{w:,.0f} ft x {h:,.0f} ft - that looks implausible for a house plot.")

    plausible_hits = []
    print("  Here's what the size would be under other common unit settings:")
    for label, scale in UNIT_TABLE.items():
        alt_w, alt_h = raw_w * scale, raw_h * scale
        looks_plausible = 15 <= max(alt_w, alt_h) <= 400 and 8 <= min(alt_w, alt_h)
        marker = "  <- looks like a plausible house plot" if looks_plausible else ""
        print(f"    --units {label:<3} -> {alt_w:,.1f} ft x {alt_h:,.1f} ft{marker}")
        if looks_plausible:
            plausible_hits.append(label)

    if plausible_hits and "in" in plausible_hits:
        print(f"  This matches the classic 'architectural feet-and-inches' pattern - "
              f"the file is very likely drawn in INCHES even though it displays as "
              f"feet'-inches\". Re-run with:  --units in")
    elif plausible_hits:
        print(f"  Re-run with:  --units {plausible_hits[0]}")
    else:
        print("  None of the standard unit assumptions look plausible - double check "
              "the DXF was exported correctly, or pass --units explicitly if you know it.")


def shape_regularity(poly):
    minx, miny, maxx, maxy = poly.bounds
    bbox_area = (maxx - minx) * (maxy - miny)
    return poly.area / bbox_area if bbox_area else 0


def pick_entrance_side(poly, cfg_side, auto_mode):
    cfg_side = (cfg_side or "auto").strip().upper()
    if cfg_side in SIDES:
        return cfg_side, f"you set ENTRANCE_SIDE = '{cfg_side}'"

    minx, miny, maxx, maxy = poly.bounds
    w, h = maxx - minx, maxy - miny
    guess = "S" if w >= h else "W"

    if not auto_mode:
        print("\nWhich side should the main entrance / foyer be on?")
        for s in SIDES:
            marker = "  <- suggested" if s == guess else ""
            print(f"  {s} = {SIDE_LABELS[s]}{marker}")
        try:
            choice = input(f"Pick N/S/E/W [{guess}]: ").strip().upper()
        except EOFError:
            choice = ""
        if choice in SIDES:
            return choice, "you chose this interactively"

    return guess, ("ENTRANCE_SIDE left as 'auto' - guessed from the longer "
                    "bounding-box edge (likely street frontage); set ENTRANCE_SIDE "
                    "explicitly in CONFIG if this is wrong")


CORNER_FLIP = {
    "W": (False, False),
    "S": (True, False),
    "E": (True, True),
    "N": (False, True),
}


def build_program_variant(buildable_area, bedrooms_wanted, circulation_fraction, label):
    usable = buildable_area * (1 - circulation_fraction)

    if bedrooms_wanted:
        n_bed = max(1, bedrooms_wanted)
    else:
        n_bed = max(1, int(usable // 450))

    counters = defaultdict(int)
    instances = []
    running = 0

    def add(rtype):
        nonlocal running
        w, d, area, note = ROOM_STANDARDS[rtype]
        counters[rtype] += 1
        n = counters[rtype]
        base = rtype.title()
        name = f"{base} {n}" if (n > 1 or rtype in ("bedroom", "attached bath", "dressing")) else base
        running += area
        instances.append({"name": name, "type": rtype, "w": w, "d": d, "area": area})
        return name

    bed_groups = []
    for _ in range(n_bed):
        bname = add("bedroom")
        bbath = add("attached bath")
        bdress = add("dressing")
        bed_groups.append((bname, bbath, bdress))

    for extra in ["kitchen", "laundry", "lounge", "foyer", "guest room", "study", "store", "stair"]:
        add(extra)

    return {
        "label": label,
        "circulation_fraction": circulation_fraction,
        "n_bed": n_bed,
        "instances": instances,
        "bed_groups": bed_groups,
        "running": running,
        "usable": usable,
        "fits": running <= usable,
    }


def print_program_table(variant):
    print(f"\n--- Plan: {variant['label']}  "
          f"({variant['n_bed']} bedroom suite(s), "
          f"{variant['circulation_fraction']*100:.0f}% circulation) ---")
    print(f"{'Room':<18}{'Min. size':<14}{'Area (sqft)':<14}")
    for inst in variant["instances"]:
        print(f"{inst['name']:<18}{inst['w']}'x{inst['d']}' min   {inst['area']:<14}")
    print(f"Program area needed: ~{variant['running']:,.0f} sq ft  |  "
          f"Usable (after circulation): {variant['usable']:,.0f} sq ft")
    if variant["fits"]:
        margin = variant["usable"] - variant["running"]
        print(f"-> Fits comfortably, ~{margin:,.0f} sq ft margin.")
    else:
        print("-> TIGHT for this plot - consider dropping a room or shrinking the lounge.")


def get_adjacency_preferences(room_types_present, auto_mode):
    adjacency = {k: list(v) for k, v in DEFAULT_ADJACENCY.items() if k in room_types_present}

    if auto_mode:
        return adjacency

    print("\n" + "-" * 70)
    print("ROOM CONNECTIONS (for the bubble diagram)")
    print("-" * 70)
    print("Standard architectural adjacencies are used by default "
          "(bedroom<->bath/dressing, kitchen<->lounge, etc).")
    try:
        choice = input("Customize which rooms connect to which? [y/N]: ").strip().lower()
    except EOFError:
        return adjacency

    if choice != "y":
        return adjacency

    print("\nFor each room type, type comma-separated room types it should connect to.")
    print("Press Enter to keep the default shown in brackets. Valid types:")
    print("  " + ", ".join(sorted(ROOM_STANDARDS.keys())))
    for rtype in sorted(room_types_present):
        if rtype in ("bedroom", "attached bath", "dressing"):
            continue
        default = adjacency.get(rtype, [])
        try:
            raw = input(f"  {rtype.title():<16} [{', '.join(default) if default else 'none'}]: ").strip()
        except EOFError:
            break
        if raw:
            picks = [p.strip().lower() for p in raw.split(",") if p.strip()]
            valid = [p for p in picks if p in ROOM_STANDARDS]
            invalid = [p for p in picks if p not in ROOM_STANDARDS]
            if invalid:
                print(f"    (ignoring unknown room types: {', '.join(invalid)})")
            adjacency[rtype] = valid
    return adjacency


def build_instance_graph(variant, type_adjacency):
    instances = variant["instances"]
    by_type = defaultdict(list)
    for inst in instances:
        by_type[inst["type"]].append(inst["name"])

    G = nx.Graph()
    for inst in instances:
        G.add_node(inst["name"], type=inst["type"], area=inst["area"])

    for bname, bbath, bdress in variant["bed_groups"]:
        G.add_edge(bname, bbath)
        G.add_edge(bname, bdress)

    for rtype, targets in type_adjacency.items():
        sources = by_type.get(rtype, [])
        for ttype in targets:
            dests = by_type.get(ttype, [])
            if not dests:
                continue
            for s in sources:
                G.add_edge(s, dests[0])
    return G


def draw_bubble_diagram(G, variant_label, out_path, info_lines=None):
    pos = nx.spring_layout(G, seed=42, k=1.5 / math.sqrt(max(len(G.nodes), 1)))
    areas = nx.get_node_attributes(G, "area")
    types = nx.get_node_attributes(G, "type")
    max_area = max(areas.values()) if areas else 1
    sizes = [700 + 2600 * (areas[n] / max_area) for n in G.nodes]
    colors = [TYPE_COLORS.get(types[n], "#cccccc") for n in G.nodes]

    fig, ax = plt.subplots(figsize=(11, 8.5))
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#999999", width=1.6)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes, node_color=colors,
                            edgecolors="#333333", linewidths=1.2, alpha=0.92)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_weight="bold")
    ax.set_title(f"Room Relationship Diagram - {variant_label}", fontsize=13, fontweight="bold")
    ax.axis("off")

    present_types = sorted(set(types.values()))
    handles = [plt.Line2D([0], [0], marker='o', linestyle='',
                           markerfacecolor=TYPE_COLORS.get(t, "#cccccc"),
                           markeredgecolor="#333333", markersize=9, label=t.title())
               for t in present_types]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
                   fontsize=8, frameon=False, title="Room type")

    if info_lines:
        text = "\n".join(info_lines)
        ax.text(1.01, 0.45, text, transform=ax.transAxes, fontsize=8.5,
                va="top", ha="left", family="monospace",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7f7f7", edgecolor="#cccccc"))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    return fig


def _row_worst_ratio(row_vals, side):
    s = sum(row_vals)
    if s <= 0 or side <= 0:
        return float("inf")
    row_max, row_min = max(row_vals), min(row_vals)
    return max((side * side * row_max) / (s * s),
               (s * s) / (side * side * row_min))


def _layout_row(row, values, x, y, w, h, rects):
    row_vals = [values[k] for k in row]
    row_area = sum(row_vals)
    if row_area <= 0:
        return x, y, w, h
    if w >= h:
        strip_w = row_area / h if h > 0 else 0
        ry = y
        for k in row:
            rh = (values[k] / row_area) * h
            rects[k] = (x, ry, strip_w, rh)
            ry += rh
        return x + strip_w, y, max(w - strip_w, 0), h
    else:
        strip_h = row_area / w if w > 0 else 0
        rx = x
        for k in row:
            rw = (values[k] / row_area) * w
            rects[k] = (rx, y, rw, strip_h)
            rx += rw
        return x, y + strip_h, w, max(h - strip_h, 0)


def squarify(values, x, y, w, h, fill_order=None):
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [(x, y, w, h)]

    rects = [None] * n
    order = list(fill_order) if fill_order is not None else sorted(range(n), key=lambda k: -values[k])
    cx, cy, cw, ch = x, y, w, h
    row = []
    while order:
        side = min(cw, ch)
        candidate = row + [order[0]]
        if not row or _row_worst_ratio([values[k] for k in candidate], side) <= \
                       _row_worst_ratio([values[k] for k in row], side):
            row.append(order.pop(0))
        else:
            cx, cy, cw, ch = _layout_row(row, values, cx, cy, cw, ch, rects)
            row = []
    if row:
        _layout_row(row, values, cx, cy, cw, ch, rects)
    return rects


MAX_ROOM_DEPTH_FT = 22
# Deepest a room is allowed to be when it's laid out as a single row
# hugging the corridor. Past this, the guaranteed-access packer below
# stops trying to cram everything into one row and branches instead.

MIN_ROOM_DEPTH_FT = 5


def _layout_band_guaranteed(items_areas, run_length, thickness,
                             max_room_depth=MAX_ROOM_DEPTH_FT,
                             min_room_depth=MIN_ROOM_DEPTH_FT):
    """
    Lays out `items_areas` (areas in the desired fill order) inside a
    band using LOCAL coordinates where x runs parallel to the corridor
    (0..run_length) and y runs AWAY from the corridor (y=0 is the edge
    that touches the hallway).

    Unlike squarify - which can stack several rooms on top of each
    other so only the outermost one actually reaches the corridor -
    this guarantees every returned room rect touches y=0 directly, OR
    touches a branch-corridor rect that itself starts at y=0. So no
    room, and in particular no bedroom, ever ends up sealed off with
    no path to the hallway.

    Returns: (room_rects, branch_rects, used_depth)
      room_rects  - list of (x, y, w, h), same order as items_areas
      branch_rects - list of (x, y, w, h) extra corridor stubs, in the
                     same local coordinate frame, that branch off the
                     main corridor to reach a second (or third...) row
      used_depth  - total thickness actually consumed (<= thickness)
    """
    n = len(items_areas)
    if n == 0:
        return [], [], 0.0

    total_area = sum(items_areas)

    # Try the simple case first: everyone fits in ONE row hugging the
    # corridor. This is the common case and needs no branching at all.
    row_depth = total_area / run_length if run_length > 0 else thickness
    if n == 1 or row_depth <= min(thickness, max_room_depth):
        depth = min(max(row_depth, min_room_depth if total_area > 0 else 0), thickness)
        rects = []
        cx = 0.0
        for a in items_areas:
            w = (a / total_area) * run_length if total_area > 0 else run_length / n
            rects.append((cx, 0.0, w, depth))
            cx += w
        return rects, [], depth

    # Too much area to fit in one row against the corridor - split into
    # a front row (touches the corridor directly) and a back row,
    # reached via a lateral branch corridor. The back row recurses, so
    # a third/fourth row branches again if it's still too deep.
    front, back = [], []
    front_area = 0.0
    target_front = max_room_depth * run_length * 0.55
    for a in items_areas:
        if not front or front_area < target_front:
            front.append(a)
            front_area += a
        else:
            back.append(a)
    if not back:
        back.append(front.pop())
        front_area -= back[0]

    front_depth = min(max(front_area / run_length, min_room_depth), max_room_depth, thickness)
    remaining_thickness = max(thickness - front_depth, 0.0)

    lateral_width = min(max(min_room_depth * 0.5, thickness * 0.12), remaining_thickness * 0.6, 4.0)
    lateral_width = max(min(lateral_width, remaining_thickness), 0.1)
    back_thickness = max(remaining_thickness - lateral_width, 0.1)

    # Riser: a perpendicular corridor column carved out of the front
    # row's near edge, running from y=0 (this band's corridor edge) up
    # to the lateral branch. Without this, the lateral branch would
    # float disconnected between the two rows - the riser is what
    # actually ties it back to the corridor, so every back-row room has
    # a continuous, walkable path out, not just a strip that looks
    # adjacent on paper.
    riser_width = min(lateral_width, run_length * 0.15)
    riser_width = max(riser_width, 0.1)
    front_avail = max(run_length - riser_width, 0.1)

    front_rects = []
    cx = riser_width
    for a in front:
        w = (a / front_area) * front_avail if front_area > 0 else front_avail / len(front)
        front_rects.append((cx, 0.0, w, front_depth))
        cx += w

    riser_rect = (0.0, 0.0, riser_width, front_depth)
    lateral_rect = (0.0, front_depth, run_length, lateral_width)

    back_rects_local, back_branches, back_used = _layout_band_guaranteed(
        back, run_length, back_thickness, max_room_depth, min_room_depth
    )
    y_offset = front_depth + lateral_width
    back_rects = [(bx, by + y_offset, bw, bh) for (bx, by, bw, bh) in back_rects_local]
    back_branches = [(bx, by + y_offset, bw, bh) for (bx, by, bw, bh) in back_branches]

    rects_local = front_rects + back_rects
    branches = [riser_rect, lateral_rect] + back_branches
    used_depth = front_depth + lateral_width + back_used
    return rects_local, branches, used_depth


def _place_band(blocks, run_length, thickness, horizontal_corridor, near_offset, far_first):
    """
    Runs _layout_band_guaranteed for one band and maps its local
    (run, away-from-corridor) coordinates into the "big local" frame
    already used elsewhere in draw_floor_plan (the one later offset and
    optionally flipped toward the entrance corner).

    near_offset is where, along the thickness axis, this band's
    corridor-facing edge sits. far_first=True means moving away from
    the corridor DECREASES that big-local coordinate (band_a's case);
    far_first=False means it increases (band_b's case).
    """
    if not blocks:
        return [], []

    areas = [b["area"] for b in blocks]
    local_rects, branch_rects_local, _ = _layout_band_guaranteed(areas, run_length, thickness)

    def to_big(lx, ly, lw, lh):
        if far_first:
            thick_coord = near_offset - ly - lh
        else:
            thick_coord = near_offset + ly
        if horizontal_corridor:
            return (lx, thick_coord, lw, lh)
        else:
            return (thick_coord, lx, lh, lw)

    room_pairs = [(blk, to_big(*r)) for blk, r in zip(blocks, local_rects)]
    branch_rects = [to_big(*r) for r in branch_rects_local]
    return room_pairs, branch_rects


def polygon_parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        out = []
        for g in geom.geoms:
            out.extend(polygon_parts(g))
        return out
    return []


def make_room_blocks(variant):
    blocks = []
    suite_names = set()
    for bname, bbath, bdress in variant["bed_groups"]:
        members = [i for i in variant["instances"] if i["name"] in (bname, bbath, bdress)]
        suite_names.update((bname, bbath, bdress))
        blocks.append({"label": bname, "area": sum(m["area"] for m in members),
                        "members": members, "exterior": True, "kind": "suite"})
    for inst in variant["instances"]:
        if inst["name"] in suite_names:
            continue
        is_ext = inst["type"] in EXTERIOR_ROOM_TYPES
        blocks.append({"label": inst["name"], "area": inst["area"], "members": [inst],
                        "exterior": is_ext, "kind": inst["type"]})
    return blocks


def _draw_room_piece(ax, piece, face, edge, alpha, hatch, label, area_label, irregular=False):
    xs, ys = piece.exterior.xy
    edge_style = "--" if irregular else "-"
    ax.fill(xs, ys, facecolor=face, edgecolor=edge, linewidth=1.6, alpha=alpha, hatch=hatch,
             linestyle=edge_style)
    if piece.area < 12:
        return
    cx, cy = piece.centroid.x, piece.centroid.y
    text = label if area_label is None else f"{label}\n{area_label:.0f} sqft"
    if irregular:
        text += "\n(verify on site)"
    ax.text(cx, cy, text, ha="center", va="center", fontsize=7.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.75, linewidth=0))


def _sensible_pieces(cell, buildable_poly, extra_area_for_circulation):
    clipped = cell.intersection(buildable_poly)
    pieces = polygon_parts(clipped)
    keep = []
    leftover = extra_area_for_circulation
    for p in pieces:
        minx, miny, maxx, maxy = p.bounds
        bbox_area = (maxx - minx) * (maxy - miny)
        reg = p.area / bbox_area if bbox_area else 0
        if p.area < 12 or reg < MIN_SENSIBLE_REGULARITY * 0.55:
            leftover += p.area
            continue
        keep.append((p, reg < MIN_SENSIBLE_REGULARITY))
    return keep, leftover


def _draw_exhaust_marker(ax, piece, buildable_poly, label):
    boundary = buildable_poly.boundary
    p_near, b_near = nearest_points(piece, boundary)
    dist = p_near.distance(b_near)
    cx, cy = piece.centroid.x, piece.centroid.y

    if dist < 0.75:
        vx, vy = b_near.x - p_near.x, b_near.y - p_near.y
        norm = math.hypot(vx, vy) or 1
        length = max(min(piece.bounds[2] - piece.bounds[0], piece.bounds[3] - piece.bounds[1]) * 0.18, 1.2)
        ux, uy = (vx / norm if norm else 0), (vy / norm if norm else 0)
        if norm < 1e-6:
            ux, uy = 0, 1
        sx, sy = p_near.x, p_near.y
        ax.annotate("", xy=(sx + ux * length, sy + uy * length), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#d62828", lw=1.8))
        ax.text(sx + ux * length * 1.3, sy + uy * length * 1.3, "EXH", color="#d62828",
                fontsize=6.5, fontweight="bold", ha="center", va="center")
        return True
    else:
        ax.plot([cx, b_near.x], [cy, b_near.y], linestyle="--", color="#888888", linewidth=1.1)
        ax.text(b_near.x, b_near.y, "duct", color="#888888", fontsize=6, style="italic",
                ha="center", va="center")
        return False


def _style_order(rooms_tier_groups, style_idx):
    foyer_blocks, suite_blocks, public_blocks = rooms_tier_groups

    foyer = list(foyer_blocks)
    suites = list(suite_blocks)
    public = list(public_blocks)

    import random
    rng = random.Random(10000 + style_idx)

    rng.shuffle(suites)
    rng.shuffle(public)

    remaining = suites + public
    rng.shuffle(remaining)

    return foyer + remaining


def draw_floor_plan(variant, buildable_poly, plot_poly, entrance_side, style_idx, out_path):
    minx, miny, maxx, maxy = buildable_poly.bounds
    bbox_w, bbox_h = maxx - minx, maxy - miny

    if bbox_w <= 0 or bbox_h <= 0:
        raise ValueError(
            "Buildable area has zero extent - setback may be too large."
        )

    blocks = make_room_blocks(variant)

    foyer_blocks = [b for b in blocks if b["kind"] == "foyer"]
    suite_blocks = [b for b in blocks if b["kind"] == "suite"]
    public_blocks = [b for b in blocks if b["exterior"] and b["kind"] not in ("foyer", "suite")]
    interior_blocks = [b for b in blocks if not b["exterior"]]

    import random
    rng = random.Random(10000 + style_idx)
    rng.shuffle(interior_blocks)

    rooms_ordered = _style_order((foyer_blocks, suite_blocks, public_blocks), style_idx)

    room_and_interior = rooms_ordered + interior_blocks

    room_area_sum = sum(b["area"] for b in room_and_interior)

    corridor_area_estimate = (CORRIDOR_WIDTH_FT * ((bbox_w + bbox_h) * 0.35))
    corridor_area_estimate = min(corridor_area_estimate, room_area_sum * 0.15)
    corridor_area_estimate = max(corridor_area_estimate, room_area_sum * 0.05)

    target_total = room_area_sum + corridor_area_estimate

    plot_aspect = bbox_w / bbox_h

    compact_w = math.sqrt(target_total * plot_aspect)
    compact_h = (target_total / compact_w if compact_w > 0 else target_total)

    compact_w = min(compact_w, bbox_w)
    compact_h = min(compact_h, bbox_h)

    compact_area = compact_w * compact_h

    if compact_area < target_total:
        if compact_w >= bbox_w:
            compact_h = min(bbox_h, target_total / compact_w)
        elif compact_h >= bbox_h:
            compact_w = min(bbox_w, target_total / compact_h)

    compact_w = min(compact_w, bbox_w)
    compact_h = min(compact_h, bbox_h)

    horizontal_corridor = compact_w >= compact_h
    corridor_run_length = compact_w if horizontal_corridor else compact_h
    thickness_available = compact_h if horizontal_corridor else compact_w

    corridor_w_actual = min(CORRIDOR_WIDTH_FT, thickness_available * 0.4)
    corridor_w_actual = max(corridor_w_actual, min(2.0, thickness_available * 0.5))

    band_thickness_total = max(thickness_available - corridor_w_actual, 0.1)

    band_a, band_b = [], []
    area_a = area_b = 0.0
    for b in room_and_interior:
        if area_a <= area_b:
            band_a.append(b)
            area_a += b["area"]
        else:
            band_b.append(b)
            area_b += b["area"]

    band_total_area = area_a + area_b
    band_a_share = (area_a / band_total_area) if band_total_area > 0 else 0.5
    if band_a and band_b:
        band_a_thickness = min(
            max(band_thickness_total * band_a_share, band_thickness_total * 0.15),
            band_thickness_total * 0.85
        )
    else:
        band_a_thickness = band_thickness_total if band_a else 0.0
    band_b_thickness = max(band_thickness_total - band_a_thickness, 0.0)

    # Guaranteed-access packing: instead of a flat squarify treemap per
    # band (which can stack several rooms behind each other so only the
    # outer one actually touches the hallway), each band is packed with
    # _place_band, which hugs the corridor with a first row and, if a
    # band has too much area for one row, branches a perpendicular
    # corridor stub off to a second (or third) row - a proper comb/
    # spine-and-branch circulation network, not a single straight run.
    if horizontal_corridor:
        corridor_rect = (0, band_a_thickness, corridor_run_length, corridor_w_actual)
    else:
        corridor_rect = (band_a_thickness, 0, corridor_w_actual, corridor_run_length)

    room_pairs_a, branches_a = _place_band(
        band_a, corridor_run_length, band_a_thickness, horizontal_corridor,
        near_offset=band_a_thickness, far_first=True
    )
    room_pairs_b, branches_b = _place_band(
        band_b, corridor_run_length, band_b_thickness, horizontal_corridor,
        near_offset=band_a_thickness + corridor_w_actual, far_first=False
    )

    circulation_block = {
        "label": "Corridor / Circulation",
        "area": corridor_rect[2] * corridor_rect[3],
        "members": None,
        "kind": "circulation",
    }
    branch_blocks = [
        {"label": "Corridor / Circulation", "area": br[2] * br[3], "members": None, "kind": "circulation"}
        for br in (branches_a + branches_b)
    ]

    all_items = (
        [b for b, _ in room_pairs_a]
        + [circulation_block]
        + [b for b, _ in room_pairs_b]
        + branch_blocks
    )
    local_rects = (
        [r for _, r in room_pairs_a]
        + [corridor_rect]
        + [r for _, r in room_pairs_b]
        + (branches_a + branches_b)
    )

    flip_x, flip_y = CORNER_FLIP[entrance_side]

    if flip_x:
        base_x = maxx - compact_w
    else:
        base_x = minx

    if flip_y:
        base_y = maxy - compact_h
    else:
        base_y = miny

    final_rects = []

    for lx, ly, lw, lh in local_rects:
        if flip_x:
            rx = base_x + compact_w - lx - lw
        else:
            rx = base_x + lx
        if flip_y:
            ry = base_y + compact_h - ly - lh
        else:
            ry = base_y + ly
        final_rects.append((rx, ry, lw, lh))

    fig, ax = plt.subplots(figsize=(13, 10.5))

    if plot_poly is not None:
        px, py = plot_poly.exterior.xy
        ax.plot(px, py, linestyle="--", color="#999999", linewidth=1.3)

    for part in ([buildable_poly] if buildable_poly.geom_type == "Polygon" else polygon_parts(buildable_poly)):
        bx_, by_ = part.exterior.xy
        ax.plot(bx_, by_, color="#333333", linewidth=1.8)

    legend_types = set()
    circulation_extra = 0.0
    irregular_count = 0
    unvented = []
    corridor_pieces = []
    room_pieces = []  # (label, is_bedroom_suite, piece) - for the access check below

    for block, rect in zip(all_items, final_rects):
        rx, ry, rw, rh = rect
        cell = box(rx, ry, rx + rw, ry + rh)

        if block["kind"] == "circulation":
            pieces, circulation_extra = _sensible_pieces(cell, buildable_poly, circulation_extra)
            for piece, _irregular in pieces:
                corridor_pieces.append(piece)
                xs, ys = piece.exterior.xy
                ax.fill(xs, ys, facecolor="#e8e8e8", edgecolor="#aaaaaa", linewidth=1.2, alpha=0.6, hatch="///")
                if piece.area > 12:
                    cx, cy = piece.centroid.x, piece.centroid.y
                    ax.text(cx, cy, "Corridor /\nCirculation", ha="center", va="center", fontsize=7,
                            fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.75, linewidth=0))
            continue

        if block["kind"] == "suite" and len(block["members"]) > 1:
            sub_vals = [m["area"] for m in block["members"]]
            sub_rects = squarify(sub_vals, rx, ry, rw, rh)
            for member, srect in zip(block["members"], sub_rects):
                ssx, ssy, ssw, ssh = srect
                scell = box(ssx, ssy, ssx + ssw, ssy + ssh)
                pieces, circulation_extra = _sensible_pieces(scell, buildable_poly, circulation_extra)
                for piece, irregular in pieces:
                    irregular_count += (1 if irregular else 0)
                    _draw_room_piece(ax, piece, TYPE_COLORS.get(member["type"], "#cccccc"), "#333333",
                                      0.85, None, member["name"], member["area"], irregular)
                    if member["type"] in VENT_ROOM_TYPES:
                        if not _draw_exhaust_marker(ax, piece, buildable_poly, member["name"]):
                            unvented.append(member["name"])
                    if member["type"] == "bedroom":
                        room_pieces.append((member["name"], True, piece))
                legend_types.add(member["type"])
            continue

        pieces, circulation_extra = _sensible_pieces(cell, buildable_poly, circulation_extra)
        member = block["members"][0]
        face = TYPE_COLORS.get(member["type"], "#cccccc")
        for piece, irregular in pieces:
            irregular_count += (1 if irregular else 0)
            _draw_room_piece(ax, piece, face, "#333333", 0.85, None, member["name"], member["area"], irregular)
            if member["type"] in VENT_ROOM_TYPES:
                if not _draw_exhaust_marker(ax, piece, buildable_poly, member["name"]):
                    unvented.append(member["name"])
            room_pieces.append((member["name"], member["type"] == "bedroom", piece))
        legend_types.add(member["type"])

    # ------------------------------------------------------------
    # Verify corridor access - don't just assume every room touches
    # the hallway network, actually check it against the geometry
    # that was drawn (main corridor + every branch stub combined).
    # ------------------------------------------------------------
    isolated_rooms = []
    if corridor_pieces:
        corridor_union = unary_union(corridor_pieces)
        for label, is_bedroom, piece in room_pieces:
            if piece.distance(corridor_union) > 0.6:
                isolated_rooms.append((label, is_bedroom))

    if isolated_rooms:
        bedroom_names = [n for n, is_bed in isolated_rooms if is_bed]
        other_names = [n for n, is_bed in isolated_rooms if not is_bed]
        if bedroom_names:
            print(f"  WARNING [{variant['label']}]: no direct corridor access detected for "
                  f"{', '.join(bedroom_names)} - the boundary clip likely cut the link to its "
                  f"branch corridor. Try a smaller SETBACK_FT/CORRIDOR_WIDTH_FT or a different "
                  f"ENTRANCE_SIDE and re-run.")
        if other_names:
            print(f"  Note [{variant['label']}]: {', '.join(other_names)} also show no direct "
                  f"corridor contact in this arrangement.")

    if circulation_extra > 8:
        print(f"  Note: ~{circulation_extra:,.0f} sqft of odd offcuts against the irregular boundary "
              f"were folded into open/circulation space rather than drawn as undersized rooms.")

    if unvented:
        print(f"  Caution [{variant['label']}]: {', '.join(sorted(set(unvented)))} didn't land on an "
              f"exterior wall in this arrangement - shown with a grey 'duct' line instead of a wall vent. "
              f"Try a different ENTRANCE_SIDE, or increase CORRIDOR_WIDTH_FT/shrink room count, and re-run.")

    ax.set_aspect("equal")
    pad_x = bbox_w * 0.08
    pad_y = bbox_h * 0.08

    if plot_poly is not None:
        pminx, pminy, pmaxx, pmaxy = plot_poly.bounds
    else:
        pminx, pminy, pmaxx, pmaxy = minx, miny, maxx, maxy

    ax.set_xlim(min(minx, pminx) - pad_x, max(maxx, pmaxx) + pad_x)
    ax.set_ylim(min(miny, pminy) - pad_y, max(maxy, pmaxy) + pad_y)

    ax.set_title(f"Floor Plan - {variant['label']}\n"
                 f"({variant['n_bed']} Bedroom suite(s), "
                 f"{len(variant['instances'])} rooms, "
                 f"entrance: {SIDE_LABELS[entrance_side]})", fontsize=13, fontweight="bold")

    ax.set_xlabel("Feet")
    ax.set_ylabel("Feet")
    ax.grid(True, alpha=0.2)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=TYPE_COLORS.get(t, "#cccccc"), edgecolor="#333333",
                              alpha=0.85, label=t.title()) for t in sorted(legend_types)]

    handles.append(plt.Rectangle((0, 0), 1, 1, facecolor="#e8e8e8", edgecolor="#aaaaaa", hatch="///",
                                  label="Corridor / Circulation"))

    handles.append(plt.Line2D([0], [0], color="#d62828", marker=">", linestyle="-",
                               label="Exhaust vent (wet rooms)"))

    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False,
              title="Legend")

    info_text = (f"Total Rooms: {len(variant['instances'])}\n"
                 f"Program Area: {variant['running']:,.0f} sqft\n"
                 f"Usable Area: {variant['usable']:,.0f} sqft\n"
                 f"House Footprint: {compact_w * compact_h:,.0f} sqft\n"
                 f"House Width: {compact_w:.1f} ft\n"
                 f"House Depth: {compact_h:.1f} ft\n"
                 f"Entrance side: {entrance_side}\n"
                 f"Hallway: {corridor_w_actual:.1f} ft wide, "
                 f"{'horizontal' if horizontal_corridor else 'vertical'}, "
                 f"{corridor_run_length:.1f} ft run"
                 f"{f' + {len(branches_a) + len(branches_b)} branch(es)' if (branches_a or branches_b) else ''}\n"
                 f"Layout style: {style_idx % 3 + 1} of 3\n"
                 f"Fit: {'OK' if variant['fits'] else 'TIGHT'}")

    ax.text(1.01, 0.40, info_text, transform=ax.transAxes, fontsize=8.5, va="top", ha="left",
            family="monospace", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7f7f7", edgecolor="#cccccc"))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def audit_rooms(doc, layer_name):
    msp = doc.modelspace()
    findings = []
    for e in msp.query("LWPOLYLINE"):
        if e.dxf.layer != layer_name:
            continue
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) < 3:
            continue
        poly = Polygon(pts)
        minx, miny, maxx, maxy = poly.bounds
        w, h = maxx - minx, maxy - miny
        area = poly.area
        best = min(ROOM_STANDARDS.items(), key=lambda kv: abs(kv[1][2] - area))
        std_name, (std_w, std_h, std_area, note) = best
        flag = []
        if min(w, h) < min(std_w, std_h):
            flag.append(f"narrower than the recommended {min(std_w,std_h)}' minimum")
        if area < std_area * 0.7:
            flag.append(f"~{area:.0f} sqft is small for a typical {std_name} (~{std_area} sqft)")
        findings.append((std_name, w, h, area, flag))
    return findings


def main():
    args = types.SimpleNamespace(
        dxf_path=DXF_PATH, setback=SETBACK_FT, units=UNITS, bedrooms=BEDROOMS, plans=PLANS,
        audit_layer=AUDIT_LAYER, auto=AUTO_MODE, outdir=OUTDIR, live=LIVE, live_timeout=LIVE_TIMEOUT,
    )

    print("\nSetting up output folders...")
    folders = create_output_folders(args.outdir)
    bubble_dir = folders["bubble_diagrams"]
    floor_plan_dir = folders["floor_plans"]
    log_dir = folders["logs"]

    live_mode = args.live and LIVE_BACKEND_OK
    if args.live and not LIVE_BACKEND_OK:
        print("  (No usable display/GUI backend found on this machine - "
              "showing PNGs only, live windows skipped.)")

    dxf_path = resolve_dxf_path(args.dxf_path, args.auto)
    doc = ezdxf.readfile(dxf_path)

    poly = load_boundary_polygon(doc)
    if poly is None or not poly.is_valid or poly.area == 0:
        sys.exit("Could not find a closed boundary polygon in this DXF "
                  "(need a closed LWPOLYLINE or a fully-chained LINE loop).")

    scale, decided_by = units_scale(doc, args.units)
    print(f"  Units: {decided_by}  (1 drawing unit = {scale:.4f} ft)")
    sanity_check_scale(poly, scale, decided_by)

    poly_ft = shp_scale(poly, xfact=scale, yfact=scale, origin=(0, 0))

    area = poly_ft.area
    perim = poly_ft.length
    minx, miny, maxx, maxy = poly_ft.bounds
    reg = shape_regularity(poly_ft)

    print("=" * 70)
    print(f"PLOT ANALYSIS - {dxf_path}")
    print("=" * 70)
    print(f"Plot area          : {area:,.0f} sq ft  ({area/272.25:,.2f} marla / {area/5445:,.2f} kanal)")
    print(f"Perimeter          : {perim:,.1f} ft")
    print(f"Bounding box       : {maxx-minx:,.1f} ft  x  {maxy-miny:,.1f} ft")
    print(f"Shape regularity   : {reg:.2f}  (1.0 = perfect rectangle; "
          f"{'fairly regular' if reg>0.75 else 'irregular - expect cut/angled rooms'})")

    buildable = poly_ft.buffer(-args.setback)
    if buildable.is_empty:
        sys.exit(f"A {args.setback} ft setback leaves no buildable area - try a smaller value.")
    if buildable.geom_type != "Polygon":
        buildable = max(polygon_parts(buildable), key=lambda p: p.area)
    print(f"\nSetback applied    : {args.setback} ft on all sides")
    print(f"Buildable area     : {buildable.area:,.0f} sq ft "
          f"({buildable.area/area*100:.0f}% of plot)")

    entrance_side, why = pick_entrance_side(buildable, ENTRANCE_SIDE, args.auto)
    print(f"\nEntrance side      : {entrance_side} ({SIDE_LABELS[entrance_side]}) - {why}")
    print(f"Corridor width     : {CORRIDOR_WIDTH_FT:.1f} ft (sizes the corridor/circulation area, "
          f"not just a hidden %)")
    print(f"Exterior priority  : {', '.join(EXTERIOR_ROOM_TYPES)}, plus every bedroom suite "
          f"(packed first, so they land against a real wall - no forced band, plan stays compact)")
    print(f"Exhaust-vented     : {', '.join(VENT_ROOM_TYPES)} (marked on their outer wall if they "
          f"reach one; flagged with a caution + grey duct line if not)")

    n_plans = max(1, args.plans)
    variants = []

    for i in range(n_plans):
        bed_wanted = args.bedrooms
        variant = build_program_variant(buildable.area, bed_wanted, 0.10, f"Repack #{i + 1}")
        variant["style_idx"] = i
        variants.append(variant)

    print("\n" + "-" * 70)
    print(f"GENERATING {n_plans} PLAN VARIANT(S)")
    print("-" * 70)
    for v in variants:
        print_program_table(v)

    all_types_present = set()
    for v in variants:
        all_types_present.update(i["type"] for i in v["instances"])

    if ROOM_CONNECTIONS_OVERRIDE:
        type_adjacency = {k: list(v) for k, v in DEFAULT_ADJACENCY.items() if k in all_types_present}
        for rtype, targets in ROOM_CONNECTIONS_OVERRIDE.items():
            rtype = rtype.strip().lower()
            valid = [t.strip().lower() for t in targets if t.strip().lower() in ROOM_STANDARDS]
            invalid = [t for t in targets if t.strip().lower() not in ROOM_STANDARDS]
            if invalid:
                print(f"  (ROOM_CONNECTIONS_OVERRIDE: ignoring unknown room type(s) in "
                      f"'{rtype}' entry: {', '.join(invalid)})")
            type_adjacency[rtype] = valid
        print("\n  Using ROOM_CONNECTIONS_OVERRIDE from the CONFIG block for room adjacencies.")
    else:
        type_adjacency = get_adjacency_preferences(all_types_present, args.auto)

    print("\n" + "-" * 70)
    print("BUBBLE DIAGRAMS + FLOOR PLANS")
    print("-" * 70)
    open_figs = []
    for v in variants:
        G = build_instance_graph(v, type_adjacency)
        safe_label = v["label"].lower().replace(" ", "_").replace("#", "").replace("__", "_")
        bubble_path = os.path.join(bubble_dir, f"bubble_diagram_{safe_label}.png")

        info_lines = [
            f"Plan: {v['label']}",
            f"Plot area:      {area:,.0f} sqft",
            f"Buildable area: {buildable.area:,.0f} sqft",
            f"Bedrooms:       {v['n_bed']}",
            f"Rooms:          {len(G.nodes)}",
            f"Connections:    {len(G.edges)}",
            f"Program needed: {v['running']:,.0f} sqft",
            f"Usable space:   {v['usable']:,.0f} sqft",
            f"Entrance:       {entrance_side}",
            f"Fit:            {'OK' if v['fits'] else 'TIGHT'}",
        ]
        try:
            fig = draw_bubble_diagram(G, v["label"], bubble_path, info_lines)
        except Exception as e:
            print(f"  Could not render bubble diagram: {e}")
            print("  (Continuing with the remaining plans and PNGs.)")
            continue
        print(f"  Saved bubble diagram: {bubble_path}  ({len(G.nodes)} rooms, {len(G.edges)} connections)")

        floor_plan_path = os.path.join(floor_plan_dir, f"floor_plan_{safe_label}.png")
        try:
            draw_floor_plan(v, buildable, poly_ft, entrance_side, v["style_idx"], floor_plan_path)
            print(f"  Saved floor plan: {floor_plan_path}")
        except Exception as e:
            print(f"  Could not render floor plan: {e}")

        if live_mode:
            try:
                fig.show()
                plt.pause(0.1)
                open_figs.append(fig)
            except Exception as e:
                print(f"  (Could not open a live window: {e}. PNG was still saved.)")
                live_mode = False
                plt.close(fig)
        else:
            plt.close(fig)

    if live_mode and open_figs:
        print(f"\nLive windows open - close them, or they'll auto-close in "
              f"{args.live_timeout:.0f}s. (Ctrl+C also exits immediately.)")
        elapsed = 0.0
        interval = 0.25
        try:
            while elapsed < args.live_timeout:
                still_open = [f for f in open_figs if plt.fignum_exists(f.number)]
                if not still_open:
                    break
                plt.pause(interval)
                elapsed += interval
        except KeyboardInterrupt:
            print("  (Interrupted - closing plot windows.)")
        for f in open_figs:
            if plt.fignum_exists(f.number):
                plt.close(f)

    if args.audit_layer:
        print("\n" + "-" * 70)
        print(f"ROOM AUDIT - layer '{args.audit_layer}'")
        print("-" * 70)
        findings = audit_rooms(doc, args.audit_layer)
        if not findings:
            print("No closed room rectangles found on that layer.")
        for std_name, w, h, a, flags in findings:
            status = "OK" if not flags else "CHECK: " + "; ".join(flags)
            print(f"  ~{std_name:<14} {w:5.1f}' x {h:5.1f}'  ({a:,.0f} sqft)  -> {status}")

    print("\n" + "=" * 70)
    print("OUTPUT SUMMARY")
    print("=" * 70)
    print(f"Log file:        {log_dir}")
    print(f"Bubble diagrams: {bubble_dir}")
    print(f"Floor plans:     {floor_plan_dir}")
    print("\nNote: heuristic space-planning check only - always verify against your "
          "local building bylaws (setbacks, coverage %, FAR, parking) and a licensed architect.")


if __name__ == "__main__":
    logger = Logger("Logs")
    try:
        main()
    finally:
        logger.close()
