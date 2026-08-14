import math


class PlotRenderer:

    def __init__(self, ax):

        self.ax = ax

    def draw_scale_points(self, scale_points):

        for i, p in enumerate(scale_points):
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


    def draw_barge_bollards(
            self,
            barge_points,
            pending_line_start
    ):

        for name, p in barge_points.items():

            if name == pending_line_start:
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


    def draw_quay_bollards(
            self,
            quay_points,
            pending_line_end
    ):

        for name, p in quay_points.items():

            if name == pending_line_end:
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


    def draw_mooring_lines(
            self,
            lines,
            barge_points,
            quay_points
    ):

        for line in lines:
            p1 = barge_points[line["from"]]
            p2 = quay_points[line["to"]]

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

    def draw_coordinate_system(
            self,
            origin,
            axis_point,
            axis_preview,
            mode
    ):
        if origin is not None:
            self.ax.plot(
                origin[0],
                origin[1],
                marker="+",
                markersize=15,
                color="cyan"
            )

            self.ax.text(
                origin[0],
                origin[1],
                "Origin",
                color="cyan"
            )

        if (
                origin is not None
                and axis_point is not None
        ):
            ox, oy = origin
            axp, ayp = axis_point

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
                mode == "axis"
                and origin is not None
                and axis_preview is not None
        ):
            self.ax.plot(
                [origin[0], axis_preview[0]],
                [origin[1], axis_preview[1]],
                "--",
                color="cyan",
                linewidth=2
            )

        if (
                mode == "axis"
                and origin is not None
                and axis_preview is not None
        ):
            ox, oy = origin
            px, py = axis_preview

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