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
from plot_renderer import PlotRenderer

class MooringPlanner:

    def __init__(self, root):

        # =====================================================
        # Project data
        # =====================================================
        self.project = MooringProject()


        # =====================================================
        # Application window
        # =====================================================
        self.root = root
        self.root.title("Mooring Plan Creator")

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )


        # =====================================================
        # User Interaction state
        # =====================================================
        self.mode = "none"

        self.pending_line_start = None
        self.pending_line_end = None

        self.ctrl_pressed = False
        self.shift_pressed = False

        self.axis_preview = None


        # =====================================================
        # Pan operation state
        # =====================================================
        self.panning = False

        self.pan_start_x = None
        self.pan_start_y = None

        self.xlim_start = None
        self.ylim_start = None


        # =====================================================
        # View state
        # =====================================================
        self.current_xlim = None
        self.current_ylim = None

        self.home_xlim = None
        self.home_ylim = None


        # =====================================================
        # Drawing/image state
        # =====================================================
        self.image = None
        self.image_array = None


        # =====================================================
        # Scale Definition state
        # =====================================================
        self.scale_points = []


        # =====================================================
        # Undo/redo state
        # =====================================================
        self.undo_stack = []
        self.redo_stack = []


        # =====================================================
        # Keyboard bindings
        # =====================================================
        self.setup_bindings()


        # =====================================================
        # Create GUI
        # =====================================================
        self.create_gui()


    def setup_bindings(self):
        """
        Register keyboard events used by the application. Tracks the state of modifier keys such as Ctrl and Shift.
        These flags are used by interactive features, for example Ctrl + mouse wheel zooming and future
        keyboard-assisted editing operations.
        """

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

    def setup_canvas_events(self):
        """
        Register matplotlib canvas mouse events.

        Handles:
        - mouse clicks
        - mouse wheel zooming
        - mouse movement
        - mouse button release

        These events drive the interactive mooring-plan
        editing functionality.
        """

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

    def create_gui(self):
        """
        Create the application user interface, including tool buttons, status bar, plotting canvas, and matplotlib
        navigation toolbar.
        """

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

        self.renderer = PlotRenderer(self.ax)

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

        self.setup_canvas_events()

    def save_project(self):
        """
        Save the current mooring project to a project file, including drawing references, coordinate-system settings,
        bollards, and mooring lines.
        """

        filename = filedialog.asksaveasfilename(
            defaultextension=".mpl",
            filetypes=[("Mooring Project", "*.mpl")]
        )

        if not filename:
            return

        data = {
            "background_file": self.project.background_file,
            "scale_factor": self.project.scale_factor,
            "origin": self.project.origin,
            "barge_points": self.project.barge_points,
            "quay_points": self.project.quay_points,
            "lines": self.project.lines,
            "barge_counter": self.project.barge_counter,
            "quay_counter": self.project.quay_counter,
            "axis_point": self.project.axis_point,
            "rotation_deg": self.project.rotation_deg
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

        messagebox.showinfo(
            "Save",
            "Project saved successfully."
        )

    def load_project(self):
        """
        Load a previously saved mooring project and restore its data and drawing state.
        """

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
                self.project.background_file = data.get(
                    "background_file"
                )

            self.load_background(self.project.background_file)

            self.project.scale_factor = data.get("scale_factor")

            origin = data.get("origin")

            if origin is not None:
                self.project.origin = tuple(origin)
            else:
                self.project.origin = None

            self.project.barge_points = {
                k: tuple(v)
                for k, v in data.get("barge_points", {}).items()
            }

            self.project.quay_points = {
                k: tuple(v)
                for k, v in data.get("quay_points", {}).items()
            }

            self.project.lines = data.get("lines", [])

            self.project.barge_counter = data.get(
                "barge_counter",
                len(self.project.barge_points) + 1
            )

            self.project.quay_counter = data.get(
                "quay_counter",
                len(self.project.quay_points) + 1
            )

            self.project.axis_point = data.get("axis_point")

            self.project.rotation_deg = data.get(
                "rotation_deg",
                0.0
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

        if self.project.background_file:

            try:

                if self.project.background_file.lower().endswith(".pdf"):

                    doc = fitz.open(
                        self.project.background_file
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
                            self.project.background_file
                        )
                    )

            except Exception as e:

                messagebox.showwarning(
                    "Drawing Missing",
                    f"Project loaded.\n\n"
                    f"The original drawing could not be found:\n\n"
                    f"{self.project.background_file}\n\n"
                    f"You can load it manually."
                )


    # =====================================================
    # MODE
    # =====================================================

    def set_mode(self, mode):
        """
        Activate the selected editing mode and disable active matplotlib pan or zoom tools if necessary.
        """

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
        """
        Load a drawing file to be used as the mooring-plan background image.
        """

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

        self.project.background_file = file

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
        """
        Redraw the complete mooring plan while preserving the current view where possible.
        """

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
        self.renderer.draw_scale_points(
            self.scale_points
        )

        # origin/coordinate system
        self.renderer.draw_coordinate_system(
            self.project.origin,
            self.project.axis_point,
            self.axis_preview,
            self.mode
        )

        # barge
        self.renderer.draw_barge_bollards(
            self.project.barge_points,
            self.pending_line_start
        )

        # quay
        self.renderer.draw_quay_bollards(
            self.project.quay_points,
            self.pending_line_end
        )

        # lines
        self.renderer.draw_mooring_lines(
            self.project.lines,
            self.project.barge_points,
            self.project.quay_points
        )

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
        """
        Handle mouse-click events and dispatch them to the active editing mode.
        """

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
        """
        Define the drawing scale using two user-selected reference points.
        """

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
        """
        Set the coordinate-system origin.
        """

        self.project.origin = (x, y)

        self.undo_stack.append(
            ("origin", self.project.origin)
        )

        self.redraw()

    # =====================================================
    # BARGE
    # =====================================================

    def barge_mode(self, x, y):
        """
        Create a new barge bollard at the selected location.
        """

        name = f"B{self.project.barge_counter}"

        self.project.barge_points[name] = (x, y)

        self.project.barge_counter += 1

        self.undo_stack.append(
            ("barge", name)
        )

        self.redraw()

    # =====================================================
    # QUAY
    # =====================================================

    def quay_mode(self, x, y):
        """
        Create a new quay bollard at the selected location.
        """

        name = f"Q{self.project.quay_counter}"

        self.project.quay_points[name] = (x, y)

        self.project.quay_counter += 1

        self.undo_stack.append(
            ("quay", name)
        )

        self.redraw()

    # =====================================================
    # FIND POINT
    # =====================================================

    def nearest_barge(self, x, y):
        """
        Return the nearest barge bollard within the selection tolerance.
        """

        best = None
        dist = 20

        for name, p in self.project.barge_points.items():

            d = math.dist(
                (x, y),
                p
            )

            if d < dist:
                dist = d
                best = name

        return best

    def nearest_quay(self, x, y):
        """
        Return the nearest quay bollard within the selection tolerance.
        """

        best = None
        dist = 20

        for name, p in self.project.quay_points.items():

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
        """
        Create a mooring line by selecting a barge bollard and a quay bollard.
        """

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

        self.project.lines.append(item)

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
        """
        Reverse the most recent editing action.
        """

        if not self.undo_stack:
            return

        action = self.undo_stack.pop()

        self.redo_stack.append(action)

        kind = action[0]

        if kind == "barge":
            del self.project.barge_points[action[1]]

        elif kind == "quay":
            del self.project.quay_points[action[1]]

        elif kind == "line":
            self.project.lines.remove(action[1])

        elif kind == "origin":
            self.project.origin = None

        elif kind == "delete_barge":

            name = action[1]["name"]
            point = action[1]["point"]

            self.project.barge_points[name] = point

        elif kind == "delete_quay":

            name = action[1]["name"]
            point = action[1]["point"]

            self.project.quay_points[name] = point

        elif kind == "delete_line":

            self.project.lines.append(action[1])

        self.redraw()

    # =====================================================
    # REDO
    # =====================================================

    def redo(self):
        """
        Reapply the most recently undone action.
        """

        if not self.redo_stack:
            return

        action = self.redo_stack.pop()

        self.undo_stack.append(action)

        kind = action[0]

        if kind == "line":

            self.project.lines.append(action[1])

        elif kind == "delete_barge":

            name = action[1]["name"]

            if name in self.project.barge_points:
                del self.project.barge_points[name]

        elif kind == "delete_quay":

            name = action[1]["name"]

            if name in self.project.quay_points:
                del self.project.quay_points[name]

        elif kind == "delete_line":

            if action[1] in self.project.lines:
                self.project.lines.remove(action[1])

        self.redraw()

    # =====================================================
    # EXPORT
    # =====================================================

    def export_data(self):
        """
        Export bollard coordinates, mooring-line data, and a plan image using the defined coordinate system.
        """

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

            cs = CoordinateSystem(
                origin_x=ox,
                origin_y=oy,
                scale=self.project.scale_factor
                if self.project.scale_factor is not None
                else 1.0,
                rotation_deg=self.project.rotation_deg
            )

            transformer = CoordinateTransformer(cs)

            for name, p in self.project.barge_points.items():

                x, y = transformer.image_to_world(
                    p[0],
                    p[1]
                )

                writer.writerow(
                    [name, "Barge", x, y]
                )

            for name, p in self.project.quay_points.items():

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

            for line in self.project.lines:

                p1 = self.project.barge_points[line["from"]]
                p2 = self.project.quay_points[line["to"]]

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
        """
        Load a drawing file into memory for display as the plan background.
        """

        self.project.background_file = filename

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
        """
        Delete the selected mooring line or bollard.
        """

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

                self.project.lines.remove(line)

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
                self.project.lines = [
                    l for l in self.project.lines
                    if l["from"] != b
                ]

                deleted_data = {
                    "name": b,
                    "point": self.project.barge_points[b]
                }

                self.undo_stack.append(
                    ("delete_barge", deleted_data)
                )

                del self.project.barge_points[b]

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
                self.project.lines = [
                    l for l in self.project.lines
                    if l["to"] != q
                ]

                deleted_data = {
                    "name": q,
                    "point": self.project.quay_points[q]
                }

                self.undo_stack.append(
                    ("delete_quay", deleted_data)
                )

                del self.project.quay_points[q]

                self.redraw()

    def nearest_line(self, x, y):
        """
        Return the nearest mooring line within the selection tolerance.
        """

        threshold = 10

        for line in self.project.lines:

            p1 = self.project.barge_points[line["from"]]
            p2 = self.project.quay_points[line["to"]]

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
        """
        Calculate the shortest distance between a point and a line segment.
        """

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
        """
        Confirm and close the application.
        """

        answer = messagebox.askyesno(
            "Exit",
            "Close Mooring Planner?"
        )

        if answer:
            plt.close('all')

            self.root.quit()

            self.root.destroy()

    def ctrl_press(self, event):
        """
        Record that the Ctrl key is currently pressed.
        """
        self.ctrl_pressed = True

    def ctrl_release(self, event):
        """
        Record that the Ctrl key has been released.
        """
        self.ctrl_pressed = False

    def on_scroll(self, event):
        """
        Perform cursor-centred zooming when Ctrl and the mouse wheel are used together.
        """

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
        """
        Restore the original view of the loaded drawing.
        """

        if self.home_xlim is not None:
            self.ax.set_xlim(self.home_xlim)
            self.ax.set_ylim(self.home_ylim)

            self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """
        Handle mouse-movement events for interactive previews and panning operations.
        """

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
        """
        Complete any active panning operation.
        """

        self.panning = False

    def axis_mode(self, x, y):
        """
        Define the positive X-axis direction and calculate the coordinate-system rotation.
        """

        if self.project.origin is None:
            messagebox.showerror(
                "Error",
                "Set origin first."
            )

            return

        self.project.axis_point = (x, y)

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


root = tk.Tk()

app = MooringPlanner(root)

root.mainloop()