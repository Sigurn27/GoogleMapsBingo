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
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{label}_{timestamp}.png".replace(" ", "_")
                path = os.path.join(SAVE_DIR, filename)
                main_chrome_winspec.capture_as_image().save(path)
                match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
                if match:
                    return float(match.group(1)), float(match.group(2)), path
            except Exception:
                pass
    return None, None, None

# =====================
# Map output
# =====================
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
# Helpers
# =====================
def _fmt_mmss(seconds: int) -> str:
    m, s = divmod(max(int(seconds), 0), 60)
    return f"{m:02d}:{s:02d}"

# =====================
# UI callbacks
# =====================
def apply_enabled_state(*_):
    state = "normal" if enabled.get() else "disabled"
    for b in btns:
        b.config(state=state)

# --- TIMER: state and functions ---------------------------------------------
remaining_secs = 0
total_secs = 0              # store the starting duration in seconds
_timer_job = None
_game_finished = False      # prevent double-finalization

def _update_timer_label():
    timer_label.config(text=_fmt_mmss(remaining_secs))

def _end_game(reason: str):
    """
    Finalize the game and show summary.
    reason: 'completed' (all 25 pressed) or 'timeout' (timer hit 0)
    """
    global _timer_job, _game_finished
    if _game_finished:
        return
    _game_finished = True

    # Stop ticking
    if _timer_job is not None:
        root.after_cancel(_timer_job)
        _timer_job = None

    # Lock the grid after end
    for b in btns:
        b.config(state="disabled")

    # Counts
    disabled_count = sum(1 for b in btns if b.cget("state") == "disabled")
    enabled_count = len(btns) - disabled_count

    # Timing
    time_taken = total_secs - remaining_secs      # elapsed = start - remaining

    # Result
    result = "WIN" if reason == "completed" else "LOSS"

    summary = (
        f"Items Found: {disabled_count} | "
        f"Items Remaining: {enabled_count} | "
        f"Time Taken: {_fmt_mmss(time_taken)} | "
        f"Result: {result}"
    )

    # Show/update summary label under the grid
    if hasattr(_end_game, "label") and _end_game.label.winfo_exists():
        _end_game.label.config(text=summary)
    else:
        _end_game.label = tk.Label(results_frame, text=summary, font=("Arial", 12))
        _end_game.label.pack(pady=(6, 10))

def _tick():
    global remaining_secs, _timer_job
    if remaining_secs <= 0:
        _timer_job = None
        _end_game(reason="timeout")
        return
    remaining_secs -= 1
    _update_timer_label()
    if remaining_secs > 0:
        _timer_job = root.after(1000, _tick)
    else:
        _timer_job = None
        _end_game(reason="timeout")

def _start_timer(start_minutes: int):
    """Initialize and start the countdown from start_minutes."""
    global remaining_secs, total_secs, _timer_job, _game_finished
    _game_finished = False

    if _timer_job is not None:
        root.after_cancel(_timer_job)

    total_secs = max(int(start_minutes) * 60, 0)   # store the start duration
    remaining_secs = total_secs
    _update_timer_label()

    if remaining_secs > 0:
        _timer_job = root.after(1000, _tick)
    else:
        _timer_job = None
        _end_game(reason="timeout")

def bingo_click(label, button):
    if label in found_items or _game_finished:   # prevent late clicks post-end
        return

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

    # Progressive append to CSV
    generate_map_outputs(label, found_items[label])

    # End condition: if every grid button is disabled, end as a WIN
    if all(b.cget("state") == "disabled" for b in btns):
        _end_game(reason="completed")

def start_game(button):
    enabled.set(not enabled.get())
    button.config(state="disabled")
    try:
        minutes = int(var.get())
        if minutes < 0:
            minutes = 0
    except ValueError:
        minutes = 0
        var.set("0")

    # Clear any previous summary label for a new run (optional nicety)
    if hasattr(_end_game, "label") and _end_game.label.winfo_exists():
        _end_game.label.config(text="")

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
header3 = tk.Spinbox(header_frame, from_=0, to=30, width=5, textvariable=var, justify="center")
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

# Results area for the final summary below the grid
results_frame = tk.Frame(root)
results_frame.pack(fill="x")  # summary label gets created on demand at end

root.mainloop()