"""Generate src/npc/adapters/skyrim/native/anima.ico: the Anima four-point star on dark brown with gold."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "src/npc/adapters/skyrim/native/anima.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)
BROWN, EDGE, GOLD, LIGHT = (38, 24, 16, 255), (150, 110, 48, 255), (224, 176, 72, 255), (255, 226, 150, 255)


def star(size: int, scale: float, inner: float):
    """Four-point star polygon (concave diamond), centre-aligned."""
    c = size / 2
    r = size * scale
    k = r * inner
    points = []
    for i in range(4):
        # tip then the inner notch at 45 degrees
        tips = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)][i]
        notch = [(c + k, c - k), (c + k, c + k), (c - k, c + k), (c - k, c - k)][i]
        points += [tips, notch]
    return points


def draw(size: int) -> Image.Image:
    work = 512  # draw large, then downsample for smooth edges
    image = Image.new("RGBA", (work, work), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    pen.rounded_rectangle((0, 0, work - 1, work - 1), radius=work // 5, fill=BROWN, outline=EDGE, width=max(4, work // 40))
    pen.polygon(star(work, 0.40, 0.14), fill=GOLD)
    pen.polygon(star(work, 0.20, 0.07), fill=LIGHT)
    return image.resize((size, size), Image.LANCZOS)


def main():
    images = [draw(size) for size in SIZES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES], append_images=images[:-1])
    print(OUT)


if __name__ == "__main__":
    main()
