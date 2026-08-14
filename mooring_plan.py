import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)

import csv
import math
import fitz
from PIL import Image

import json

from models import CoordinateSystem, CoordinateTransformer, MooringProject


class MooringPlanner:

    def __init__(self, root):

        self.project = MooringProject()

        self.axis_point = None

        self.axis_preview = None

        self.rotation_deg = 0.0

        self.root = root
        self.root.title("Mooring Plan Creator")

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.mode = "none"

        self.shift_pressed = False

        self.panning = False

        self.pan_start_x = None
        self.pan_start_y = None

        self.xlim_start = None
        self.ylim_start = None

        self.current_xlim = None
        self.current_ylim = None

        self.image = None
        self.image_array = None
        self.background_file = None

        self.home_xlim = None
        self.home_ylim = None

        self.scale_points = []
        self.project.scale_factor = None

        self.project.origin = None

        self.barge_points = {}
        self.quay_points = {}

        self.barge_counter = 1
        self.quay_counter = 1

        self.lines = []

        self.undo_stack = []
        self.redo_stack = []

        self.pending_line_start = None
        self.pending_line_end = None

        self.ctrl_pressed = False

        self.root.bind(
            "<KeyPress-Control_L>",
            self.ctrl_press
        )

        self.root.bind(
            "<KeyRelease-Control_L>",
            self.ctrl_release
        )

        self.root.bind(
            "<KeyPress-Control_R>",
            self.ctrl_press
        )

        self.root.bind(
            "<KeyRelease-Control_R>",
            self.ctrl_release
        )

        self.root.bind(
            "<KeyPress-Shift_L>",
            self.shift_press
        )

        self.root.bind(
            "<KeyRelease-Shift_L>",
            self.shift_release
        )

        self.root.bind(
            "<KeyPress-Shift_R>",
            self.shift_press
        )

        self.root.bind(
            "<KeyRelease-Shift_R>",
            self.shift_release
        )

        self.create_gui()

    # =====================================================
    # GUI
    # =====================================================

    def create_gui(self):

        top = tk.Frame(self.root)
        top.pack(fill=tk.X)

        tk.Button(
            top,
            text="Home",
            command=self.reset_view
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Load Drawing",
            command=self.load_file
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Save Project",
            command=self.save_project
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Load Project",
            command=self.load_project
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Scale",
            command=lambda: self.set_mode("scale")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Origin",
            command=lambda: self.set_mode("origin")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="X-Axis",
            command=lambda: self.set_mode("axis")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Barge Bollard",
            command=lambda: self.set_mode("barge")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Quay Bollard",
            command=lambda: self.set_mode("quay")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Add Line",
            command=lambda: self.set_mode("line")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Undo",
            command=self.undo
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Redo",
            command=self.redo
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Delete",
            command=lambda: self.set_mode("delete")
        ).pack(side=tk.LEFT)

        tk.Button(
            top,
            text="Export",
            command=self.export_data
        ).pack(side=tk.LEFT)

        self.status = tk.Label(
            self.root,
            text="Ready"
        )

        self.status.pack(fill=tk.X)

        self.fig, self.ax = plt.subplots(figsize=(10, 8))

        self.canvas = FigureCanvasTkAgg(
            self.fig,
            master=self.root
        )

        self.canvas.draw()

        self.canvas.get_tk_widget().pack(
            fill=tk.BOTH,
            expand=True
        )

        toolbar = NavigationToolbar2Tk(
            self.canvas,
            self.root
        )

        toolbar.update()

        self.canvas.mpl_connect(
            "button_press_event",
            self.on_click
        )

        self.canvas.mpl_connect(
            "scroll_event",
            self.on_scroll
        )

        self.canvas.mpl_connect(
            "button_release_event",
            self.on_mouse_release
        )

        self.canvas.mpl_connect(
            "motion_notify_event",
            self.on_mouse_move
        )

    def save_project(self):

        filename = filedialog.asksaveasfilename(
            defaultextension=".mpl",
            filetypes=[("Mooring Project", "*.mpl")]
        )

        if not filename:
            return

        data = {
            "background_file": self.background_file,
            "scale_factor": self.project.scale_factor,
            "origin": self.project.origin,
            "barge_points": self.barge_points,
            "quay_points": self.quay_points,
            "lines": self.lines,
            "barge_counter": self.barge_counter,
            "quay_counter": self.quay_counter
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

        messagebox.showinfo(
            "Save",
            "Project saved successfully."
        )

    def load_project(self):

        filename = filedialog.askopenfilename(
            filetypes=[
                ("Mooring Project", "*.mpl")
            ]
        )

        if not filename:
            return

        try:

            with open(filename, "r") as f:
                data = json.load(f)
                self.background_file = data.get(
                    "background_file"
                )

            self.load_background(self.background_file)

            self.project.scale_factor = data.get("scale_factor")

            origin = data.get("origin")

            if origin is not None:
                self.project.origin = tuple(origin)
            else:
                self.project.origin = None

            self.barge_points = {
                k: tuple(v)
                for k, v in data.get("barge_points", {}).items()
            }

            self.quay_points = {
                k: tuple(v)
                for k, v in data.get("quay_points", {}).items()
            }

            self.lines = data.get("lines", [])

            self.barge_counter = data.get(
                "barge_counter",
                len(self.barge_points) + 1
            )

            self.quay_counter = data.get(
                "quay_counter",
                len(self.quay_points) + 1
            )

            self.pending_line_start = None
            self.pending_line_end = None

            self.redraw()

            messagebox.showinfo(
                "Load Project",
                "Project loaded successfully."
            )

        except Exception as e:

            messagebox.showerror(
                "Load Error",
                f"Unable to load project:\n\n{e}"
            )

        if self.background_file:

            try:

                if self.background_file.lower().endswith(".pdf"):

                    doc = fitz.open(
                        self.background_file
                    )

                    page = doc.load_page(0)

                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(1.5, 1.5)
                    )

                    arr = np.frombuffer(
                        pix.samples,
                        dtype=np.uint8
                    )

                    arr = arr.reshape(
                        pix.height,
                        pix.width,
                        pix.n
                    )

                    self.image_array = arr

                else:

                    self.image_array = np.array(
                        Image.open(
                            self.background_file
                        )
                    )

            except Exception as e:

                messagebox.showwarning(
                    "Drawing Missing",
                    f"Project loaded.\n\n"
                    f"The original drawing could not be found:\n\n"
                    f"{self.background_file}\n\n"
                    f"You can load it manually."
                )


    # =====================================================
    # MODE
    # =====================================================

    def set_mode(self, mode):

        try:

            toolbar = self.canvas.toolbar

            if toolbar is not None:

                if toolbar.mode != "":

                    if "zoom" in toolbar.mode.lower():
                        toolbar.zoom()

                    elif "pan" in toolbar.mode.lower():
                        toolbar.pan()

        except Exception:
            pass

        self.mode = mode

        self.status.config(
            text=f"Mode: {mode}"
        )

    # =====================================================
    # FILE LOAD
    # =====================================================

    def load_file(self):

        file = filedialog.askopenfilename(
            filetypes=[
                (
                    "Files",
                    "*.png *.jpg *.jpeg *.bmp *.tif *.pdf"
                )
            ]
        )

        if not file:
            return

        self.load_background(file)

        self.background_file = file

        if file.lower().endswith(".pdf"):

            doc = fitz.open(file)
            page = doc.load_page(0)

            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

            arr = np.frombuffer(
                pix.samples,
                dtype=np.uint8
            )

            arr = arr.reshape(
                pix.height,
                pix.width,
                pix.n
            )

            self.image_array = arr

        else:

            self.image_array = np.array(
                Image.open(file)
            )

        self.redraw()

    # =====================================================
    # DRAWING
    # =====================================================

    def redraw(self):

        preserve_view = False

        try:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

            preserve_view = (
                    self.image_array is not None and
                    len(self.ax.images) > 0
            )

        except:
            preserve_view = False


        # Store current view if it exists
        if len(self.ax.images) > 0:
            self.current_xlim = self.ax.get_xlim()
            self.current_ylim = self.ax.get_ylim()

        self.ax.clear()

        if self.image_array is not None:
            self.ax.imshow(self.image_array)
            if self.home_xlim is None:
                self.home_xlim = self.ax.get_xlim()
                self.home_ylim = self.ax.get_ylim()

        # scale points
        self.draw_scale_points()

        # origin/coordinate system
        self.draw_coordinate_system()

        # barge
        self.draw_barge_bollards()

        # quay
        self.draw_quay_bollards()

        # lines
        self.draw_mooring_lines()


        self.ax.set_title("Mooring Plan")

        if preserve_view:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)

        if self.current_xlim is not None:
            self.ax.set_xlim(self.current_xlim)
            self.ax.set_ylim(self.current_ylim)

        self.canvas.draw()


    # =====================================================
    # CLICK
    # =====================================================

    def on_click(self, event):

        # Shift + Right Mouse
        if event.button == 2:
            self.panning = True

            self.pan_start_x = event.xdata
            self.pan_start_y = event.ydata

            self.xlim_start = self.ax.get_xlim()
            self.ylim_start = self.ax.get_ylim()

            return

        toolbar = self.canvas.toolbar

        # Only prevent drawing while panning
        if toolbar is not None:

            if toolbar.mode == "pan/zoom":
                self.status.config(
                    text="Pan mode active"
                )

                return

        if event.xdata is None or event.ydata is None:
            return

        x = float(event.xdata)
        y = float(event.ydata)

        if self.mode == "scale":

            self.scale_mode(x, y)

        elif self.mode == "origin":

            self.origin_mode(x, y)

        elif self.mode == "barge":

            self.barge_mode(x, y)

        elif self.mode == "quay":

            self.quay_mode(x, y)

        elif self.mode == "line":

            self.line_mode(x, y)

        elif self.mode == "delete":

            self.delete_mode(x, y)

        elif self.mode == "axis":

            self.axis_mode(x, y)

    # =====================================================
    # SCALE
    # =====================================================

    def scale_mode(self, x, y):

        self.scale_points.append((x, y))

        if len(self.scale_points) == 2:

            p1 = self.scale_points[0]
            p2 = self.scale_points[1]

            pixels = math.dist(p1, p2)

            real = simpledialog.askfloat(
                "Scale",
                "Actual distance"
            )

            self.project.scale_factor = real / pixels

            messagebox.showinfo(
                "Scale",
                f"Scale factor:\n{self.project.scale_factor:.6f}"
            )

        self.redraw()

    # =====================================================
    # ORIGIN
    # =====================================================

    def origin_mode(self, x, y):

        self.project.origin = (x, y)

        self.undo_stack.append(
            ("origin", self.project.origin)
        )

        self.redraw()

    # =====================================================
    # BARGE
    # =====================================================

    def barge_mode(self, x, y):

        name = f"B{self.barge_counter}"

        self.barge_points[name] = (x, y)

        self.barge_counter += 1

        self.undo_stack.append(
            ("barge", name)
        )

        self.redraw()

    # =====================================================
    # QUAY
    # =====================================================

    def quay_mode(self, x, y):

        name = f"Q{self.quay_counter}"

        self.quay_points[name] = (x, y)

        self.quay_counter += 1

        self.undo_stack.append(
            ("quay", name)
        )

        self.redraw()

    # =====================================================
    # FIND POINT
    # =====================================================

    def nearest_barge(self, x, y):

        best = None
        dist = 20

        for name, p in self.barge_points.items():

            d = math.dist(
                (x, y),
                p
            )

            if d < dist:
                dist = d
                best = name

        return best

    def nearest_quay(self, x, y):

        best = None
        dist = 20

        for name, p in self.quay_points.items():

            d = math.dist(
                (x, y),
                p
            )

            if d < dist:
                dist = d
                best = name

        return best

    # =====================================================
    # LINE MODE
    # =====================================================

    def line_mode(self, x, y):

        if self.pending_line_start is None:

            b = self.nearest_barge(x, y)

            if b is not None:
                self.pending_line_start = b

                self.status.config(
                    text=f"{b} selected. Pick quay bollard."
                )

                self.redraw()

            return

        q = self.nearest_quay(x, y)

        if q is None:
            return

        self.pending_line_end = q

        self.redraw()

        line_name = simpledialog.askstring(
            "Line Name",
            "Enter line name:"
        )

        if not line_name:
            return

        item = {
            "name": line_name,
            "from": self.pending_line_start,
            "to": q
        }

        self.lines.append(item)

        self.undo_stack.append(
            ("line", item)
        )

        self.pending_line_start = None
        self.pending_line_end = None

        self.redraw()

    # =====================================================
    # UNDO
    # =====================================================

    def undo(self):

        if not self.undo_stack:
            return

        action = self.undo_stack.pop()

        self.redo_stack.append(action)

        kind = action[0]

        if kind == "barge":
            del self.barge_points[action[1]]

        elif kind == "quay":
            del self.quay_points[action[1]]

        elif kind == "line":
            self.lines.remove(action[1])

        elif kind == "origin":
            self.project.origin = None

        elif kind == "delete_barge":

            name = action[1]["name"]
            point = action[1]["point"]

            self.barge_points[name] = point

        elif kind == "delete_quay":

            name = action[1]["name"]
            point = action[1]["point"]

            self.quay_points[name] = point

        elif kind == "delete_line":

            self.lines.append(action[1])

        self.redraw()

    # =====================================================
    # REDO
    # =====================================================

    def redo(self):

        if not self.redo_stack:
            return

        action = self.redo_stack.pop()

        self.undo_stack.append(action)

        kind = action[0]

        if kind == "line":

            self.lines.append(action[1])

        elif kind == "delete_barge":

            name = action[1]["name"]

            if name in self.barge_points:
                del self.barge_points[name]

        elif kind == "delete_quay":

            name = action[1]["name"]

            if name in self.quay_points:
                del self.quay_points[name]

        elif kind == "delete_line":

            if action[1] in self.lines:
                self.lines.remove(action[1])

        self.redraw()

    # =====================================================
    # EXPORT
    # =====================================================

    def export_data(self):

        if self.project.origin is None:
            messagebox.showerror(
                "Error",
                "Origin not set."
            )
            return

        if self.project.scale_factor is None:
            messagebox.showwarning(
                "Warning",
                "Scale not defined. \n\n"
                "Coordinates and line lengths will be exported in pixels"
            )

        folder = filedialog.askdirectory()

        if not folder:
            return

        bollard_file = folder + "/bollards.csv"

        with open(
            bollard_file,
            "w",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow(
                [
                    "Name",
                    "Type",
                    "X",
                    "Y"
                ]
            )

            ox, oy = self.project.origin

            for name, p in self.barge_points.items():

                cs = CoordinateSystem(
                    origin_x=ox,
                    origin_y=oy,
                    scale=self.project.scale_factor,
                    rotation_deg=self.project.rotation_deg
                )

                transformer = CoordinateTransformer(cs)

                x, y = transformer.image_to_world(
                    p[0],
                    p[1]
                )

                writer.writerow(
                    [name, "Barge", x, y]
                )

            for name, p in self.quay_points.items():

                cs = CoordinateSystem(
                    origin_x=ox,
                    origin_y=oy,
                    scale=self.project.scale_factor
                    if self.project.scale_factor is not None
                    else 1.0,
                    rotation_deg=self.project.rotation_deg
                )

                transformer = CoordinateTransformer(cs)

                x, y = transformer.image_to_world(
                    p[0],
                    p[1]
                )

                writer.writerow(
                    [name, "Quay", x, y]
                )

        line_file = folder + "/mooring_lines.csv"

        with open(
            line_file,
            "w",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow(
                [
                    "Name",
                    "From",
                    "To",
                    "Length",
                    "Angle"
                ]
            )

            for line in self.lines:

                p1 = self.barge_points[line["from"]]
                p2 = self.quay_points[line["to"]]

                if self.project.scale_factor is not None:
                    length = (
                        math.dist(p1, p2)
                        * self.project.scale_factor
                    )
                else:
                    length = (
                            math.dist(p1, p2)
                    )

                angle = math.degrees(
                    math.atan2(
                        p2[1] - p1[1],
                        p2[0] - p1[0]
                    )
                )

                writer.writerow(
                    [
                        line["name"],
                        line["from"],
                        line["to"],
                        length,
                        angle
                    ]
                )

        self.fig.savefig(
            folder +
            "/mooring_plan.jpg",
            dpi=300
        )

        messagebox.showinfo(
            "Export",
            "Files exported."
        )

    def load_background(self, filename):

        self.background_file = filename

        if filename.lower().endswith(".pdf"):

            doc = fitz.open(filename)
            page = doc.load_page(0)

            pix = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5)
            )

            arr = np.frombuffer(
                pix.samples,
                dtype=np.uint8
            )

            arr = arr.reshape(
                pix.height,
                pix.width,
                pix.n
            )

            if pix.n == 4:
                arr = arr[:, :, :3]

            self.image_array = arr

        else:

            self.image_array = np.array(
                Image.open(filename)
            )

    def delete_mode(self, x, y):

        # Try line first
        line = self.nearest_line(x, y)

        if line is not None:

            answer = messagebox.askyesno(
                "Delete Line",
                f"Delete line '{line['name']}'?"
            )

            if answer:
                self.undo_stack.append(
                    ("delete_line", line.copy())
                )

                self.lines.remove(line)

                self.redraw()

            return

        # Try barge bollard
        b = self.nearest_barge(x, y)

        if b is not None:

            answer = messagebox.askyesno(
                "Delete Bollard",
                f"Delete bollard '{b}'?"
            )

            if answer:
                # Remove connected lines
                self.lines = [
                    l for l in self.lines
                    if l["from"] != b
                ]

                deleted_data = {
                    "name": b,
                    "point": self.barge_points[b]
                }

                self.undo_stack.append(
                    ("delete_barge", deleted_data)
                )

                del self.barge_points[b]

                self.redraw()

            return

        # Try quay bollard
        q = self.nearest_quay(x, y)

        if q is not None:

            answer = messagebox.askyesno(
                "Delete Bollard",
                f"Delete bollard '{q}'?"
            )

            if answer:
                self.lines = [
                    l for l in self.lines
                    if l["to"] != q
                ]

                deleted_data = {
                    "name": q,
                    "point": self.quay_points[q]
                }

                self.undo_stack.append(
                    ("delete_quay", deleted_data)
                )

                del self.quay_points[q]

                self.redraw()

    def nearest_line(self, x, y):

        threshold = 10

        for line in self.lines:

            p1 = self.barge_points[line["from"]]
            p2 = self.quay_points[line["to"]]

            distance = self.point_to_segment_distance(
                x, y,
                p1[0], p1[1],
                p2[0], p2[1]
            )

            if distance < threshold:
                return line

        return None

    def point_to_segment_distance(
            self,
            px, py,
            x1, y1,
            x2, y2):

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.dist(
                (px, py),
                (x1, y1)
            )

        t = (
                    ((px - x1) * dx) +
                    ((py - y1) * dy)
            ) / (dx * dx + dy * dy)

        t = max(0, min(1, t))

        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy

        return math.dist(
            (px, py),
            (nearest_x, nearest_y)
        )

    def on_close(self):

        answer = messagebox.askyesno(
            "Exit",
            "Close Mooring Planner?"
        )

        if answer:
            plt.close('all')

            self.root.quit()

            self.root.destroy()

    def ctrl_press(self, event):
        self.ctrl_pressed = True

    def ctrl_release(self, event):
        self.ctrl_pressed = False

    def on_scroll(self, event):

        if not self.ctrl_pressed:
            return

        if event.xdata is None:
            return

        if event.ydata is None:
            return

        x = event.xdata
        y = event.ydata

        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        width = cur_xlim[1] - cur_xlim[0]
        height = cur_ylim[1] - cur_ylim[0]

        # Zoom amount

        if event.button == "up":
            scale = 0.8

        elif event.button == "down":
            scale = 1.25

        else:
            return

        new_width = width * scale
        new_height = height * scale

        relx = (cur_xlim[1] - x) / width
        rely = (cur_ylim[1] - y) / height

        self.ax.set_xlim(
            [
                x - new_width * (1 - relx),
                x + new_width * relx
            ]
        )

        self.ax.set_ylim(
            [
                y - new_height * (1 - rely),
                y + new_height * rely
            ]
        )

        self.canvas.draw_idle()

    def reset_view(self):

        if self.home_xlim is not None:
            self.ax.set_xlim(self.home_xlim)
            self.ax.set_ylim(self.home_ylim)

            self.canvas.draw_idle()

    def shift_press(self, event):

        self.shift_pressed = True

    def shift_release(self, event):

        self.shift_pressed = False

    def on_mouse_move(self, event):

        if self.mode == "axis":

            if self.project.origin is None:
                return

            if event.xdata is None or event.ydata is None:
                return

            self.axis_preview = (
                event.xdata,
                event.ydata
            )

            self.redraw()

            return

        if not self.panning:
            return

        if event.xdata is None:
            return

        if event.ydata is None:
            return

        dx = event.xdata - self.pan_start_x
        dy = event.ydata - self.pan_start_y

        if abs(dx) < 3 and abs(dy) < 3:
            return

        self.ax.set_xlim(
            self.xlim_start[0] - dx,
            self.xlim_start[1] - dx
        )

        self.ax.set_ylim(
            self.ylim_start[0] - dy,
            self.ylim_start[1] - dy
        )

        self.canvas.draw_idle()

    def on_mouse_release(self, event):

        self.panning = False

    def axis_mode(self, x, y):

        if self.project.origin is None:
            messagebox.showerror(
                "Error",
                "Set origin first."
            )

            return

        self.axis_point = (x, y)

        dx = x - self.project.origin[0]

        dy = self.project.origin[1] - y

        self.project.rotation_deg = math.degrees(
            math.atan2(dy, dx)
        )

        self.status.config(
            text=f"Rotation = {self.project.rotation_deg:.1f}°"
        )

        self.axis_preview = None

        self.mode = "none"

        self.status.config(
            text=f"Coordinate system defined ({self.project.rotation_deg:.1f}°)"
        )

        self.redraw()

    def draw_scale_points(self):

        for i, p in enumerate(self.scale_points):
            self.ax.plot(
                p[0],
                p[1],
                "ro"
            )

            self.ax.text(
                p[0],
                p[1],
                f"S{i + 1}",
                color="red"
            )

        # todo: the scale points cannot be changed once created.

    def draw_coordinate_system(self):
        if self.project.origin is not None:
            self.ax.plot(
                self.project.origin[0],
                self.project.origin[1],
                marker="+",
                markersize=15,
                color="cyan"
            )

            self.ax.text(
                self.project.origin[0],
                self.project.origin[1],
                "Origin",
                color="cyan"
            )

        if (
                self.project.origin is not None
                and self.axis_point is not None
        ):
            ox, oy = self.project.origin
            axp, ayp = self.axis_point

            dx = axp - ox
            dy = ayp - oy

            axis_length = math.hypot(dx, dy)

            ux = dx / axis_length
            uy = dy / axis_length

            vx = uy
            vy = -ux

            self.ax.plot(
                [ox, ox + ux * axis_length],
                [oy, oy + uy * axis_length],
                color="cyan",
                linewidth=2
            )

            self.ax.plot(
                [ox, ox + vx * axis_length],
                [oy, oy + vy * axis_length],
                color="magenta",
                linewidth=2
            )

            self.ax.text(
                ox + ux * axis_length,
                oy + uy * axis_length,
                "X",
                color="cyan"
            )

            self.ax.text(
                ox + vx * axis_length,
                oy + vy * axis_length,
                "Y",
                color="magenta"
            )

        if (
                self.mode == "axis"
                and self.project.origin is not None
                and self.axis_preview is not None
        ):
            self.ax.plot(
                [self.project.origin[0], self.axis_preview[0]],
                [self.project.origin[1], self.axis_preview[1]],
                "--",
                color="cyan",
                linewidth=2
            )

        if (
                self.mode == "axis"
                and self.project.origin is not None
                and self.axis_preview is not None
        ):
            ox, oy = self.project.origin
            px, py = self.axis_preview

            # Rubber-band line
            self.ax.plot(
                [ox, px],
                [oy, py],
                "--",
                color="cyan",
                linewidth=2
            )

            # Angle relative to image X-axis
            dx = px - ox
            dy = oy - py

            angle = math.degrees(
                math.atan2(dy, dx)
            )

            # Angle label
            self.ax.text(
                px,
                py,
                f"{angle:.1f}°",
                color="yellow",
                fontsize=10,
                bbox=dict(
                    facecolor="black",
                    alpha=0.7,
                    edgecolor="none"
                )
            )

        # todo: undo does not apply to the origin. if bollards are created after the origin, the undo button will
        # todo: remove the bollards and the origin, but redo will not work afterwards.


    def draw_barge_bollards(self):
        for name, p in self.barge_points.items():

            if name == self.pending_line_start:
                self.ax.plot(
                    p[0],
                    p[1],
                    marker="s",
                    markersize=14,
                    color="yellow",
                    markeredgecolor="black"
                )
            else:
                self.ax.plot(
                    p[0],
                    p[1],
                    "rs"
                )

            self.ax.text(
                p[0],
                p[1],
                name,
                color="red"
            )

    def draw_quay_bollards(self):
        for name, p in self.quay_points.items():

            if name == self.pending_line_end:
                self.ax.plot(
                    p[0],
                    p[1],
                    marker="o",
                    markersize=14,
                    color="yellow",
                    markeredgecolor="black"
                )
            else:
                self.ax.plot(
                    p[0],
                    p[1],
                    "bo"
                )

            self.ax.text(
                p[0],
                p[1],
                name,
                color="blue"
            )

    def draw_mooring_lines(self):
        for line in self.lines:
            p1 = self.barge_points[line["from"]]
            p2 = self.quay_points[line["to"]]

            self.ax.plot(
                [p1[0], p2[0]],
                [p1[1], p2[1]],
                "g-",
                linewidth=2
            )

            mx = (p1[0] + p2[0]) / 2
            my = (p1[1] + p2[1]) / 2

            self.ax.text(
                mx,
                my,
                line["name"],
                color="green"
            )

root = tk.Tk()

app = MooringPlanner(root)

root.mainloop()