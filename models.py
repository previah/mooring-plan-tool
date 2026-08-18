from dataclasses import dataclass, field
import math
from enum import Enum

@dataclass
class Point:
    x: float
    y: float


@dataclass
class MooringProject:

    background_file: str | None = None

    scale_factor: float | None = None

    origin: tuple | None = None

    axis_point: tuple | None = None

    rotation_deg: float = 0.0

    barge_points: dict = field(default_factory=dict)

    quay_points: dict = field(default_factory=dict)

    lines: list = field(default_factory=list)

    barge_counter: int = 1

    quay_counter: int = 1


@dataclass
class CoordinateSystem:
    origin_x: float
    origin_y: float
    scale: float
    rotation_deg: float = 0.0


class CoordinateTransformer:

    def __init__(self, coordinate_system):
        self.cs = coordinate_system

    def image_to_world(self, x, y):
        dx = x - self.cs.origin_x
        dy = self.cs.origin_y - y

        dx *= self.cs.scale
        dy *= self.cs.scale

        angle = math.radians(
            self.cs.rotation_deg
        )

        world_x = (
                dx * math.cos(angle)
                + dy * math.sin(angle)
        )

        world_y = (
                -dx * math.sin(angle)
                + dy * math.cos(angle)
        )

        return world_x, world_y

# class BollardType(Enum):
#     BARGE = "barge"
#     QUAY = "quay"
#
#
# @dataclass
# class Bollard:
#
#     name: str
#
#     point: Point
#
#     bollard_type: BollardType