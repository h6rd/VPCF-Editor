from PIL import Image, ImageChops
import colorsys
from typing import Optional, Tuple

TintMode = str


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def isMostlyGrayscale(image: Image.Image, sat_threshold: float = 0.08, fraction: float = 0.9) -> bool:
    sample = image.convert("RGBA").copy()
    sample.thumbnail((48, 48), getattr(Image, "Resampling", Image).NEAREST)
    pixels = sample.load()
    width, height = sample.size
    gray = opaque = 0
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a < 16:
                continue
            opaque += 1
            _h, s, _v = rgb_to_hsv(r, g, b)
            if s <= sat_threshold:
                gray += 1
    if opaque == 0:
        return True
    return (gray / opaque) >= fraction


def getAverageHue(image: Image.Image) -> float:
    img = image.convert('RGBA')
    pixels = img.load()
    width, height = img.size
    
    total_h = 0.0
    count = 0
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0:
                h, s, v = rgb_to_hsv(r, g, b)
                if s > 0.05 and v > 0.05:
                    total_h += h
                    count += 1
                    
    return (total_h / count) if count > 0 else 0.0


def applyTint(img: Image.Image, tint_rgb: Tuple[int, int, int], mode: TintMode = "overlay") -> Image.Image:
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    if mode == "replace":
        solid = Image.new("RGB", img.size, tint_rgb)
        out = solid.convert("RGBA")
        out.putalpha(alpha)
        return out

    multiplied = ImageChops.multiply(img.convert("RGB"), Image.new("RGB", img.size, tint_rgb))
    out = multiplied.convert("RGBA")
    out.putalpha(alpha)
    return out


def tintImage(image_path: str, out_path: str, tint_rgb: Tuple[int, int, int], mode: TintMode = "overlay"):
    applyTint(Image.open(image_path), tint_rgb, mode).save(out_path)


def adjustImage(image_path: str, out_path: str, h_shift: float, s_scale: float, v_scale: float):
    img = Image.open(image_path).convert('RGBA')
    pixels = img.load()
    width, height = img.size
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0:
                h, s, v = rgb_to_hsv(r, g, b)
                
                h = (h + h_shift) % 1.0
                s = max(0.0, min(1.0, s * s_scale))
                v = max(0.0, min(1.0, v * v_scale))
                
                nr, ng, nb = hsv_to_rgb(h, s, v)
                pixels[x, y] = (nr, ng, nb, a)
                
    img.save(out_path)


def multiplyPixel(r: int, g: int, b: int, tint_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    tr, tg, tb = tint_rgb
    return (r * tr) // 255, (g * tg) // 255, (b * tb) // 255


def autoRecolorImage(image_path: str, out_path: str, target_rgb: Tuple[int, int, int]):
    img = Image.open(image_path).convert('RGBA')
    if isMostlyGrayscale(img):
        applyTint(img, target_rgb, "overlay").save(out_path)
        return

    avg_hue = getAverageHue(img)
    target_h, _target_s, _target_v = rgb_to_hsv(*target_rgb)
    h_shift = target_h - avg_hue

    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a <= 0:
                continue
            h, s, v = rgb_to_hsv(r, g, b)
            if s > 0.05 and v > 0.05:
                h = (h + h_shift) % 1.0
                nr, ng, nb = hsv_to_rgb(h, s, v)
            else:
                nr, ng, nb = multiplyPixel(r, g, b, target_rgb)
            pixels[x, y] = (nr, ng, nb, a)

    img.save(out_path)


def previewTextureImage(
    base_img: Image.Image,
    h_shift: float,
    s_scale: float,
    v_scale: float,
    mode: str = "hsv",
    tint_rgb: Optional[Tuple[int, int, int]] = None,
) -> Image.Image:
    if mode in ("overlay", "replace") and tint_rgb is not None:
        return applyTint(base_img, tint_rgb, mode)

    img = base_img.copy()
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0:
                h, s, v = rgb_to_hsv(r, g, b)
                h = (h + h_shift) % 1.0
                s = max(0.0, min(1.0, s * s_scale))
                v = max(0.0, min(1.0, v * v_scale))
                nr, ng, nb = hsv_to_rgb(h, s, v)
                pixels[x, y] = (nr, ng, nb, a)
    return img