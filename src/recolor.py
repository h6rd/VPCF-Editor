import colorsys
from typing import Tuple

from src.config import GRAYSCALE_TOLERANCE


def isGrayscale(rgb: Tuple[int, int, int], tolerance: int = GRAYSCALE_TOLERANCE) -> bool:
    return (max(rgb) - min(rgb)) <= tolerance


def recolorPreservingSv(
    orig_rgb: Tuple[int, int, int],
    target_rgb: Tuple[int, int, int],
) -> Tuple[int, int, int]:
    r, g, b = orig_rgb
    _, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    tr, tg, tb = target_rgb
    th, ts, tv = colorsys.rgb_to_hsv(tr / 255.0, tg / 255.0, tb / 255.0)

    if ts == 0.0:
        # desaturate orig + apply bright
        nr, ng, nb = colorsys.hsv_to_rgb(0.0, 0.0, tv)
    else:
        # keep orig sat / bright
        nr, ng, nb = colorsys.hsv_to_rgb(th, s, v)

    return (
        max(0, min(255, int(round(nr * 255)))),
        max(0, min(255, int(round(ng * 255)))),
        max(0, min(255, int(round(nb * 255)))),
    )
