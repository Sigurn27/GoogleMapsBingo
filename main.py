from datetime import datetime
from tkinter import StringVar
from tkinter.constants import CENTER
from pywinauto import *
import tkinter as tk
import os, re, csv

# =====================
# CONFIG
# =====================
SAVE_DIR = "screenshots"
MAP_CSV = "bingo_map.csv"
BINGO_ITEMS = [
    "Lawnmower", "Trampoline", "Hose Reel", "Dog or Cat", "BBQ",
    "Motorbike or Quadbike", "Flag", "Looking at Camera", "Satellite Dish", "Air Con Unit",
    "Graffiti", "Wheely Bin", "Wheelbarrow", "Bicycle", "Caravan",
    "Hi-Vis", "Roof Rack", "Chair or Bench", "Playground Equipment", "Plant Pot",
    "Work Van with Signage", "Trailer", "Letterbox", "Speed Limit Sign", "Ladder"
]
os.makedirs(SAVE_DIR, exist_ok=True)
try:
    os.remove(MAP_CSV)
except FileNotFoundError:
    pass
found_items = {}

def get_lat_lng_screenshot(label):
    desktop = Desktop(backend="uia")
    app = application.Application()
    for window in desktop.windows():
        if "Google Chrome" in window.window_text():
            app = application.Application(backend='uia').connect(title_re=".*Google Chrome")
            main_chrome_winspec = app.window(title_re=".*Google Chrome")
            try:
                url_bar = main_chrome_winspec.child_window(control_type="Edit")
                url = url_bar.window_text()
                match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
                if match:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"{label}_{timestamp}.png".replace(" ", "_")
                    path = os.path.join(SAVE_DIR, filename)
                    main_chrome_winspec.capture_as_image().save(path)
                    return float(match.group(1)), float(match.group(2)), path
            except Exception:
                pass
    return None, None, None

# =====================
# Map output
# =====================
# === CHANGED: make generate_map_outputs append a single row per click.
def generate_map_outputs(label, data):
    """Append (Name, Latitude, Longitude, Description) to MAP_CSV.
       Creates file with header if it doesn't exist or is empty."""
    file_exists = os.path.exists(MAP_CSV)
    needs_header = True
    if file_exists:
        try:
            needs_header = os.path.getsize(MAP_CSV) == 0
        except OSError:
            needs_header = True

    with open(MAP_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists or needs_header:
            writer.writerow(["Name", "Latitude", "Longitude", "Description"])
        writer.writerow([label, data["lat"], data["lng"], data["screenshot"]])
    print(f"Appended row for '{label}' to {MAP_CSV}")

# =====================
# UI callbacks
# =====================
def bingo_click(label, button):
    if label in found_items:
        return
    # screenshot_path = take_screenshot(label)
    lat, lng, screenshot_path = get_lat_lng_screenshot(label)
    if lat is None or lng is None:
        print(f"Warning: could not read coordinates for {label}")
        return

    found_items[label] = {
        "screenshot": screenshot_path,
        "lat": lat,
        "lng": lng
    }
    print(f"{label}: {lat}, {lng}")
    button.config(bg="green", state="disabled")

    # === CHANGED: append to CSV immediately for progressive build.
    generate_map_outputs(label, found_items[label])

    # (Removed the previous: if len(found_items) == 25: ... generate all and quit)

def apply_enabled_state(*_):
    state = "normal" if enabled.get() else "disabled"
    for b in btns:
        b.config(state=state)

# --- TIMER: state and functions (from previous step, extended) ---------------
remaining_secs = 0
_timer_job = None

def _update_timer_label():
    m, s = divmod(max(remaining_secs, 0), 60)
    timer_label.config(text=f"{m:02d}:{s:02d}")

def _show_final_counts():
    """Create/update a label below the grid showing enabled/disabled counts."""
    enabled_count = sum(1 for b in btns if b.cget("state") == "normal")
    disabled_count = len(btns) - enabled_count
    txt = f"Time up: Items Found: {disabled_count} | Items Remaining:  {enabled_count}"

    # If the label already exists, just update; otherwise create it.
    if hasattr(_show_final_counts, "label") and _show_final_counts.label.winfo_exists():
        _show_final_counts.label.config(text=txt)
    else:
        _show_final_counts.label = tk.Label(results_frame, text=txt, font=("Arial", 12))
        _show_final_counts.label.pack(pady=(6, 10))

def _tick():
    global remaining_secs, _timer_job
    if remaining_secs <= 0:
        _timer_job = None
        # === NEW: when timer hits 0, post final counts below grid.
        _show_final_counts()
        return
    remaining_secs -= 1
    _update_timer_label()
    if remaining_secs > 0:
        _timer_job = root.after(1000, _tick)
    else:
        _timer_job = None
        _show_final_counts()  # === NEW: also handle edge case landing exactly on zero.

def _start_timer(start_minutes: int):
    """Initialize and start the countdown from start_minutes."""
    global remaining_secs, _timer_job
    if _timer_job is not None:
        root.after_cancel(_timer_job)
    remaining_secs = max(int(start_minutes) * 60, 0)
    _update_timer_label()
    if remaining_secs > 0:
        _timer_job = root.after(1000, _tick)
    else:
        _timer_job = None
        _show_final_counts()

def start_game(button):
    # Enable grid
    enabled.set(not enabled.get())  # trace handler will run and update all
    button.config(state="disabled")

    # Start countdown from Spinbox minutes
    try:
        minutes = int(var.get())
        if minutes < 0:
            minutes = 0
    except ValueError:
        minutes = 0
        var.set("0")

    _start_timer(minutes)

# =====================
# UI
# =====================
root = tk.Tk()
root.title("Street View Bingo")

enabled = tk.BooleanVar(value=False)

header_frame = tk.Frame(root)
header_frame.pack(padx=10, pady=10)

header1 = tk.Label(header_frame, text="Google Maps Bingo!", font=("Arial", 20))
header2 = tk.Label(header_frame, text="Time Limit (mins)")
var = StringVar()
var.set("10")
header3 = tk.Spinbox(header_frame, from_=1, to=30, width=5, textvariable=var, justify="center")
header4 = tk.Button(header_frame, text="Start Game")
header4.config(command=lambda b=header4: start_game(b), state="normal")

header1.grid(row=0, column=0, columnspan=2)
header2.grid(row=1, column=0)
header3.grid(row=1, column=1)
header4.grid(row=2, column=0, columnspan=5)

# Countdown label under the Start button
timer_label = tk.Label(header_frame, text="00:00", font=("Arial", 16))
timer_label.grid(row=3, column=0, columnspan=5, pady=(6, 0))
_update_timer_label()

# Grid of buttons
button_frame = tk.Frame(root)
btns = []
for i, label in enumerate(BINGO_ITEMS):
    btn = tk.Button(
        button_frame,
        text=label,
        width=18,
        height=3,
        state="disabled"
    )
    btn.config(command=lambda l=label, b=btn: bingo_click(l, b))
    btn.grid(row=(i // 5)+2, column=i % 5, padx=4, pady=4)
    btns.append(btn)

enabled.trace_add("write", apply_enabled_state)
button_frame.pack(padx=10, pady=10)

# === NEW: Results frame to show final counts under the grid when time is up.
results_frame = tk.Frame(root)
_show_final_counts.label = tk.Label(results_frame, text="Results", font=("Arial", 12))
_show_final_counts.label.pack(pady=(6, 10))
results_frame.pack(fill="x")  # empty initially; label created on demand

root.mainloop()