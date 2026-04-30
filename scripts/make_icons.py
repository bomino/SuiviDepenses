"""Generate PNG icons from the same design as the inline manifest SVG.

Run once when the brand changes:
    python scripts/make_icons.py

Outputs (overwrites if present):
    icons/icon-192.png       — Android / Chrome install
    icons/icon-512.png       — splash screen, high-DPI
    icons/icon-512-maskable.png — adaptive icon (safe zone padded)
    icons/apple-touch-icon.png — iOS home-screen (180x180)
    icons/favicon-32.png     — browser tab
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG = (15, 23, 42)       # #0f172a
FG = (245, 158, 11)     # #f59e0b
OUT = Path(__file__).resolve().parent.parent / "icons"
OUT.mkdir(exist_ok=True)


def find_bold_font(size: int):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/seguibl.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_icon(size: int, *, maskable: bool = False, rounded: bool = True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if maskable:
        # full-bleed background; safe zone is the inner 80%
        draw.rectangle([(0, 0), (size, size)], fill=BG)
        glyph_box = int(size * 0.8)
        offset = (size - glyph_box) // 2
    elif rounded:
        radius = int(size * 0.22)
        draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=BG)
        glyph_box = size
        offset = 0
    else:
        draw.rectangle([(0, 0), (size, size)], fill=BG)
        glyph_box = size
        offset = 0

    font_size = int(glyph_box * 0.66)
    font = find_bold_font(font_size)

    text = "$"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = offset + (glyph_box - tw) // 2 - bbox[0]
    y = offset + (glyph_box - th) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=FG)
    return img


def main():
    targets = [
        ("icon-192.png", 192, False, True),
        ("icon-512.png", 512, False, True),
        ("icon-512-maskable.png", 512, True, False),
        ("apple-touch-icon.png", 180, False, True),
        ("favicon-32.png", 32, False, True),
    ]
    for name, size, maskable, rounded in targets:
        img = draw_icon(size, maskable=maskable, rounded=rounded)
        img.save(OUT / name, "PNG", optimize=True)
        print(f"  {name:30s}  {size}x{size}")


if __name__ == "__main__":
    main()
