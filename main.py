from datetime import datetime
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
def generate_map_outputs():
    # --- CSV for Google My Maps ---
    with open(MAP_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Latitude", "Longitude", "Description"])

        for label, data in found_items.items():
            writer.writerow([
                label,
                data["lat"],
                data["lng"],
                data["screenshot"]
            ])

    print(f"Map CSV written to {MAP_CSV}")


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

    if len(found_items) == 25:
        print("Bingo complete!")
        generate_map_outputs()
        root.quit()


# =====================
# UI
# =====================
root = tk.Tk()
root.title("Street View Bingo")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

for i, label in enumerate(BINGO_ITEMS):
    btn = tk.Button(
        frame,
        text=label,
        width=18,
        height=3
    )
    btn.config(command=lambda l=label, b=btn: bingo_click(l, b))
    btn.grid(row=i // 5, column=i % 5, padx=4, pady=4)

root.mainloop()