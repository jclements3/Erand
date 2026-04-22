"""strings.py -- single-source string configuration for the harp design.

Each entry specifies one string: its scientific-pitch note name, the pin
position in the neck (x, y) mm, the grommet y-coordinate (where the string
enters the soundboard), and the string diameter in mm.

To redesign the harp (different string count, range, or scale), edit this
file. Everything downstream -- neck outline, soundbox shape, column
placement -- should derive.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class StringSpec:
    note: str          # scientific pitch, e.g. "C1", "G7"
    pin_x: float       # mm, top-of-string x coordinate in authoring frame
    pin_y: float       # mm, top-of-string y coordinate
    grommet_y: float   # mm, bottom-of-string y (same x as pin_x; soundboard attach)
    diameter: float    # mm, string diameter

    @property
    def pin(self) -> Tuple[float, float]:
        return (self.pin_x, self.pin_y)

    @property
    def grommet(self) -> Tuple[float, float]:
        return (self.pin_x, self.grommet_y)

    @property
    def length(self) -> float:
        """Speaking length (pin to grommet). Strings are vertical in the
        authoring frame, so this is just the y-span."""
        import math
        return math.hypot(self.pin_x - self.pin_x, self.pin_y - self.grommet_y)


STRINGS: List[StringSpec] = [
    StringSpec("C1", 101.700, 146.563, 1661.495, 1.676),
    StringSpec("D1", 119.632, 143.109, 1632.793, 1.549),
    StringSpec("E1", 137.565, 139.654, 1604.091, 1.448),
    StringSpec("F1", 155.523, 136.200, 1575.389, 1.270),
    StringSpec("G1", 173.455, 137.775, 1546.662, 1.219),
    StringSpec("A1", 191.387, 139.375, 1517.960, 1.219),
    StringSpec("B1", 209.320, 140.975, 1489.258, 1.016),
    StringSpec("C2", 227.252, 142.575, 1460.556, 1.016),
    StringSpec("D2", 245.210, 149.230, 1431.854, 0.914),
    StringSpec("E2", 263.142, 160.914, 1403.152, 2.642),
    StringSpec("F2", 281.075, 152.380, 1374.425, 2.489),
    StringSpec("G2", 299.007, 159.035, 1345.723, 2.337),
    StringSpec("A2", 316.432, 206.888, 1317.833, 2.184),
    StringSpec("B2", 333.856, 234.574, 1289.970, 2.057),
    StringSpec("C3", 351.280, 272.319, 1262.080, 2.057),
    StringSpec("D3", 368.705, 310.088, 1234.191, 1.930),
    StringSpec("E3", 385.113, 344.455, 1207.953, 1.676),
    StringSpec("F3", 401.522, 388.879, 1181.689, 1.676),
    StringSpec("G3", 417.905, 423.245, 1155.451, 1.549),
    StringSpec("A3", 433.297, 464.266, 1130.839, 1.549),
    StringSpec("B3", 448.664, 485.120, 1106.251, 1.270),
    StringSpec("C4", 464.031, 511.028, 1081.639, 1.270),
    StringSpec("D4", 479.423, 531.856, 1057.026, 1.270),
    StringSpec("E4", 494.790, 547.629, 1032.414, 1.143),
    StringSpec("F4", 510.157, 558.399, 1007.826, 1.143),
    StringSpec("G4", 525.524, 569.143,  983.214, 1.143),
    StringSpec("A4", 539.875, 576.484,  960.252, 1.016),
    StringSpec("B4", 554.226, 583.799,  937.291, 1.016),
    StringSpec("C5", 568.577, 586.085,  914.329, 1.016),
    StringSpec("D5", 582.928, 588.371,  891.367, 0.914),
    StringSpec("E5", 597.279, 590.657,  868.406, 0.914),
    StringSpec("F5", 611.630, 582.834,  845.444, 0.914),
    StringSpec("G5", 625.981, 585.120,  822.482, 0.813),
    StringSpec("A5", 639.316, 578.947,  801.147, 0.813),
    StringSpec("B5", 652.626, 572.775,  779.811, 0.813),
    StringSpec("C6", 665.961, 566.603,  758.500, 0.813),
    StringSpec("D6", 679.296, 560.431,  737.164, 0.762),
    StringSpec("E6", 692.606, 554.259,  715.853, 0.762),
    StringSpec("F6", 705.941, 548.086,  694.517, 0.762),
    StringSpec("G6", 719.250, 541.889,  673.181, 0.711),
    StringSpec("A6", 732.585, 530.687,  651.871, 0.711),
    StringSpec("B6", 745.920, 519.435,  630.535, 0.660),
    StringSpec("C7", 759.230, 508.234,  609.224, 0.635),
    StringSpec("D7", 772.565, 496.982,  587.888, 0.635),
    StringSpec("E7", 785.874, 485.780,  566.578, 0.635),
    StringSpec("F7", 799.209, 474.553,  545.242, 0.635),
    StringSpec("G7", 812.544, 463.327,  523.931, 0.635),
]

assert len(STRINGS) == 47, "default harp has 47 strings"


if __name__ == "__main__":
    print(f"{len(STRINGS)} strings defined")
    for s in STRINGS[:3]:
        print(s)
    print("...")
    for s in STRINGS[-3:]:
        print(s)
