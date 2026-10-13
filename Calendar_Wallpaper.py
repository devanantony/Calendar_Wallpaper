import os
import sys
import time
import signal
import ctypes
import subprocess
import calendar
from datetime import date
from PIL import Image, ImageDraw, ImageFont

import tkinter as tk

# ============================================================
# SETTINGS
# ============================================================

YEAR = 2026

# Monitor number:
# 1 = first monitor
# 2 = second monitor
# 3 = third monitor
MONITOR_NUMBER = 1

# Transparency of calendar panels
PANEL_ALPHA = 80

# Text transparency
TEXT_ALPHA = 235

# Grid transparency
GRID_ALPHA = 90

# Update interval
UPDATE_INTERVAL = 60 * 60       # 1 hour

# Process marker
PROCESS_FILE = os.path.join(
    os.environ["TEMP"],
    "calendar_wallpaper_monitor2.pid"
)

# ============================================================
# SINGLE INSTANCE
# ============================================================

def close_previous_instance():

    if not os.path.exists(PROCESS_FILE):
        return

    try:

        with open(PROCESS_FILE, "r") as f:
            old_pid = int(f.read().strip())

        print(f"Closing previous calendar process: {old_pid}")

        # Windows taskkill
        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(old_pid),
                "/F"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(0.5)

    except Exception:
        pass

    try:
        os.remove(PROCESS_FILE)
    except Exception:
        pass


def save_current_pid():

    with open(PROCESS_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_pid_file():

    try:
        if os.path.exists(PROCESS_FILE):
            os.remove(PROCESS_FILE)
    except Exception:
        pass

# ============================================================
# WINDOWS MONITOR DETECTION
# ============================================================

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]

def get_monitors():

    monitors = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(RECT),
        ctypes.c_double
    )

    def callback(
        hMonitor,
        hdcMonitor,
        lprcMonitor,
        dwData
    ):

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(
            MONITORINFO
        )

        user32.GetMonitorInfoW(
            hMonitor,
            ctypes.byref(info)
        )

        monitors.append(
            (
                info.rcMonitor.left,
                info.rcMonitor.top,
                info.rcMonitor.right,
                info.rcMonitor.bottom
            )
        )

        return True

    user32.EnumDisplayMonitors(
        None,
        None,
        MonitorEnumProc(callback),
        0
    )

    return monitors

# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):

    if bold:
        path = r"C:\Windows\Fonts\segoeuib.ttf"
    else:
        path = r"C:\Windows\Fonts\segoeui.ttf"

    if os.path.exists(path):
        return ImageFont.truetype(
            path,
            size
        )

    return ImageFont.load_default()

# ============================================================
# CENTER TEXT
# ============================================================

def centered_text(
    draw,
    box,
    text,
    font,
    fill
):

    x1, y1, x2, y2 = box

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = x1 + ((x2 - x1) - tw) / 2
    y = (
        y1 +
        ((y2 - y1) - th) / 2 -
        bbox[1]
    )

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill
    )

# ============================================================
# CREATE CALENDAR IMAGE
# ============================================================

def create_calendar_image(width, height):

    image = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = get_font(
        max(28, int(width / 65)),
        True
    )

    month_font = get_font(
        max(18, int(width / 105)),
        True
    )

    day_font = get_font(
        max(14, int(width / 180)),
        False
    )

    week_font = get_font(
        max(12, int(width / 210)),
        True
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    draw.text(
        (30, 15),
        f"{YEAR}",
        font=title_font,
        fill=(
            255,
            255,
            255,
            TEXT_ALPHA
        )
    )

    # --------------------------------------------------------
    # Calendar layout
    # --------------------------------------------------------
    # Calendar layout
    left = 30
    right = 30
    # More compact gap between YEAR and calendar
    top = 70
    # Extra space at the bottom so the calendar stays above the taskbar
    bottom = 100

    columns = 4
    rows = 3

    gap_x = 15
    gap_y = 15

    available_width = (
        width -
        left -
        right
    )

    available_height = (
        height -
        top -
        bottom
    )

    month_width = (
        available_width -
        (columns - 1) * gap_x
    ) // columns

    month_height = (
        available_height -
        (rows - 1) * gap_y
    ) // rows

    today = date.today()

    # --------------------------------------------------------
    # Months
    # --------------------------------------------------------

    for month in range(1, 13):

        row = (month - 1) // columns
        col = (month - 1) % columns

        x = (
            left +
            col * (
                month_width +
                gap_x
            )
        )

        y = (
            top +
            row * (
                month_height +
                gap_y
            )
        )

        draw_month(
            draw,
            month,
            x,
            y,
            month_width,
            month_height,
            month_font,
            day_font,
            week_font,
            today
        )

    return image

# ============================================================
# DRAW MONTH
# ============================================================

def draw_month(
    draw,
    month,
    x,
    y,
    width,
    height,
    month_font,
    day_font,
    week_font,
    today
):

    # Transparent panel

    draw.rounded_rectangle(
        (
            x,
            y,
            x + width,
            y + height
        ),
        radius=12,
        fill=(
            0,
            0,
            0,
            PANEL_ALPHA
        ),
        outline=(
            255,
            255,
            255,
            70
        ),
        width=1
    )

    # Month title

    header_height = 38

    draw.rounded_rectangle(
        (
            x,
            y,
            x + width,
            y + header_height
        ),
        radius=12,
        fill=(
            0,
            0,
            0,
            100
        )
    )

    draw.rectangle(
        (
            x,
            y + 20,
            x + width,
            y + header_height
        ),
        fill=(
            0,
            0,
            0,
            100
        )
    )

    centered_text(
        draw,
        (
            x,
            y,
            x + width,
            y + header_height
        ),
        calendar.month_name[
            month
        ].upper(),
        month_font,
        (
            255,
            255,
            255,
            TEXT_ALPHA
        )
    )

    # --------------------------------------------------------
    # Calendar grid
    # --------------------------------------------------------

    week_width = 38

    grid_x = x + week_width + 5
    grid_width = (
        width -
        week_width -
        10
    )

    cell_width = (
        grid_width / 7
    )

    weekday_y = y + header_height + 3
    weekday_height = 25

    weekdays = [
        "M", "T", "W",
        "T", "F", "S", "S"
    ]

    for i, name in enumerate(weekdays):

        cell_x = (
            grid_x +
            i * cell_width
        )

        centered_text(
            draw,
            (
                cell_x,
                weekday_y,
                cell_x + cell_width,
                weekday_y + weekday_height
            ),
            name,
            week_font,
            (
                255,
                255,
                255,
                190
            )
        )

    cal = calendar.Calendar(
        firstweekday=calendar.MONDAY
    )

    weeks = cal.monthdatescalendar(
        YEAR,
        month
    )

    grid_top = (
        weekday_y +
        weekday_height
    )

    grid_height = (
        height -
        (grid_top - y) -
        5
    )

    row_height = (
        grid_height /
        len(weeks)
    )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    for row, week in enumerate(weeks):

        row_y = (
            grid_top +
            row * row_height
        )

        iso_week = (
            week[0]
            .isocalendar()
            .week
        )

        centered_text(
            draw,
            (
                x,
                row_y,
                x + week_width,
                row_y + row_height
            ),
            f"{iso_week:02d}",
            week_font,
            (
                80,
                200,
                255,
                230
            )
        )

        # horizontal grid line

        draw.line(
            (
                grid_x,
                row_y,
                grid_x + grid_width,
                row_y
            ),
            fill=(
                255,
                255,
                255,
                GRID_ALPHA
            ),
            width=1
        )

        for col, current_day in enumerate(week):

            cell_x = (
                grid_x +
                col * cell_width
            )

            # vertical grid

            draw.line(
                (
                    cell_x,
                    row_y,
                    cell_x,
                    row_y + row_height
                ),
                fill=(
                    255,
                    255,
                    255,
                    GRID_ALPHA
                ),
                width=1
            )

            # ------------------------------------------------
            # Today's date
            # ------------------------------------------------

            if current_day == today and current_day.month == month:

                draw.rounded_rectangle(
                    (
                        cell_x + 3,
                        row_y + 3,
                        cell_x + cell_width - 3,
                        row_y + row_height - 3
                    ),
                    radius=5,
                    fill=(
                        255,
                        190,
                        50,
                        220
                    )
                )

                text_color = (
                    20,
                    20,
                    20,
                    255
                )

            elif current_day.month != month:

                text_color = (
                    255,
                    255,
                    255,
                    70
                )

            else:

                text_color = (
                    255,
                    255,
                    255,
                    TEXT_ALPHA
                )

            centered_text(
                draw,
                (
                    cell_x,
                    row_y,
                    cell_x + cell_width,
                    row_y + row_height
                ),
                str(current_day.day),
                day_font,
                text_color
            )

# ============================================================
# TRANSPARENT WINDOWS DESKTOP WINDOW
# ============================================================

def create_window():

    monitors = get_monitors()

    print()
    print("Detected monitors:")

    for i, monitor in enumerate(
        monitors,
        start=1
    ):
        print(
            f"Monitor {i}: "
            f"{monitor}"
        )

    if len(monitors) < MONITOR_NUMBER:

        print(
            f"Monitor {MONITOR_NUMBER} "
            "does not exist."
        )

        sys.exit(1)

    # Monitor 2
    left, top, right, bottom = monitors[
        MONITOR_NUMBER - 1
    ]

    width = right - left
    height = bottom - top

    print()
    print(
        f"Calendar will run on "
        f"Monitor {MONITOR_NUMBER}"
    )

    print(
        f"Resolution: "
        f"{width} x {height}"
    )

    # --------------------------------------------------------
    # Create calendar
    # --------------------------------------------------------

    calendar_image = create_calendar_image(
        width,
        height
    )

    # Save temporary PNG
    temp_png = os.path.join(
        os.environ["TEMP"],
        "calendar_overlay.png"
    )

    calendar_image.save(
        temp_png
    )

    # --------------------------------------------------------
    # Tkinter window
    # --------------------------------------------------------

    root = tk.Tk()

    root.overrideredirect(True)

    root.geometry(
        f"{width}x{height}"
        f"+{left}+{top}"
    )

    root.attributes(
        "-topmost",
        False
    )

    # Transparent background
    root.configure(
        bg="black"
    )

    # Make black transparent
    root.wm_attributes(
        "-transparentcolor",
        "black"
    )

    # --------------------------------------------------------
    # Put window behind normal applications
    # --------------------------------------------------------

    hwnd = ctypes.windll.user32.GetParent(
        root.winfo_id()
    )

    # Extended styles
    GWL_EXSTYLE = -20

    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080

    exstyle = ctypes.windll.user32.GetWindowLongW(
        hwnd,
        GWL_EXSTYLE
    )

    ctypes.windll.user32.SetWindowLongW(
        hwnd,
        GWL_EXSTYLE,
        exstyle |
        WS_EX_LAYERED |
        WS_EX_TOOLWINDOW
    )

    # --------------------------------------------------------
    # Image
    # --------------------------------------------------------

    photo = tk.PhotoImage(
        file=temp_png
    )

    label = tk.Label(
        root,
        image=photo,
        borderwidth=0,
        highlightthickness=0,
        bg="black"
    )

    label.pack()

    # --------------------------------------------------------
    # Keep behind normal windows
    # --------------------------------------------------------

    root.lower()

    # --------------------------------------------------------
    # Exit handler
    # --------------------------------------------------------

    def close():

        remove_pid_file()

        try:
            root.destroy()
        except Exception:
            pass

    root.protocol(
        "WM_DELETE_WINDOW",
        close
    )

    # --------------------------------------------------------
    # Run
    # --------------------------------------------------------

    root.mainloop()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # First close previous instance
    close_previous_instance()

    # Register this process
    save_current_pid()

    try:

        create_window()

    except KeyboardInterrupt:

        pass

    finally:

        remove_pid_file()