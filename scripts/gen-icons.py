#!/usr/bin/env python3
"""SiteHub launcher + web icons via Pillow (duoscore pattern).
Theme: dark #0a0a0f tile, red rounded square, white S (with a tail dot).
Writes: www/icons/*.png (web PWA) + android/app/src/main/res/mipmap* (legacy + adaptive).
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG = (10, 10, 15)
RED = (220, 38, 38)
WHITE = (245, 245, 248)

def load_font(size):
    for cand in [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()

def draw_tile(size):
    """Full square: dark bg + centered red rounded square + S."""
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    sq = int(size * 0.62)
    x0 = (size - sq) // 2
    r = int(sq * 0.30)
    d.rounded_rectangle([x0, x0, x0 + sq, x0 + sq], radius=r, fill=RED)
    font = load_font(int(sq * 0.68))
    text = "S"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((x0 + (sq - tw) / 2 - bbox[0], x0 + (sq - th) / 2 - bbox[1]), text,
           font=font, fill=WHITE)
    dot_r = int(size * 0.045)
    dx = x0 + sq - dot_r * 2
    dy = x0 + sq - dot_r * 2
    d.ellipse([dx, dy, dx + 2 * dot_r, dy + 2 * dot_r], fill=WHITE)
    return img

def draw_foreground(size):
    """Adaptive foreground: content in the inner 72/108 safe circle."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sq = int(size * 0.50)  # within safe zone
    x0 = (size - sq) // 2
    r = int(sq * 0.30)
    d.rounded_rectangle([x0, x0, x0 + sq, x0 + sq], radius=r, fill=RED)
    font = load_font(int(sq * 0.68))
    bbox = d.textbbox((0, 0), "S", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((x0 + (sq - tw) / 2 - bbox[0], x0 + (sq - th) / 2 - bbox[1]), "S",
           font=font, fill=WHITE)
    return img

def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert("RGBA").save(path, "PNG")
    print("wrote", os.path.relpath(path, ROOT))

def main():
    # --- web / PWA ---
    web = os.path.join(ROOT, "www", "icons")
    save_png(draw_tile(192), os.path.join(web, "icon-192.png"))
    save_png(draw_tile(512), os.path.join(web, "icon-512.png"))
    m = draw_tile(512)
    save_png(m, os.path.join(web, "icon-maskable.png"))

    # --- android legacy mipmaps ---
    res = os.path.join(ROOT, "android", "app", "src", "main", "res")
    for density, size in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                          ("xxhdpi", 144), ("xxxhdpi", 192)]:
        base = os.path.join(res, "mipmap-" + density)
        save_png(draw_tile(size), os.path.join(base, "ic_launcher.png"))
        save_png(draw_tile(size), os.path.join(base, "ic_launcher_round.png"))

    # --- android adaptive (foreground PNG in density folders; XML in anydpi-v26) ---
    for density, size in [("mdpi", 108), ("hdpi", 162), ("xhdpi", 243),
                          ("xxhdpi", 324), ("xxxhdpi", 432)]:
        base = os.path.join(res, "mipmap-" + density)
        save_png(draw_foreground(size), os.path.join(base, "ic_launcher_foreground.png"))
    # background colour drawable XML
    bg = os.path.join(res, "values", "ic_launcher_background.xml")
    os.makedirs(os.path.dirname(bg), exist_ok=True)
    with open(bg, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                '<resources><color name="ic_launcher_background">#0A0A0F</color></resources>\n')
    print("wrote", os.path.relpath(bg, ROOT))

if __name__ == "__main__":
    main()