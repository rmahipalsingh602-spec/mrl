from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ICON_SIZE = 512
BACKGROUND_TOP = (7, 17, 31)
BACKGROUND_BOTTOM = (24, 39, 73)
ACCENT_START = (48, 212, 255)
ACCENT_END = (119, 242, 186)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "build_assets" / "mrl.ico"


def blend(a: tuple[int, int, int], b: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * factor) for i in range(3))


def draw_gradient_background(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    inset = 32
    radius = 72
    for y in range(inset, ICON_SIZE - inset):
        factor = (y - inset) / (ICON_SIZE - inset * 2)
        color = blend(BACKGROUND_TOP, BACKGROUND_BOTTOM, factor)
        draw.rounded_rectangle(
            (inset, y, ICON_SIZE - inset, y + 1),
            radius=radius,
            fill=color,
        )


def draw_logo_mark(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    stroke_width = 32
    draw.line((132, 370, 132, 150), fill=ACCENT_START, width=stroke_width)
    draw.line((132, 150, 256, 286), fill=(76, 225, 236), width=stroke_width)
    draw.line((256, 286, 380, 150), fill=(98, 234, 208), width=stroke_width)
    draw.line((380, 150, 380, 370), fill=ACCENT_END, width=stroke_width)
    draw.line((126, 396, 386, 396), fill=ACCENT_END, width=14)
    draw.ellipse((366, 102, 410, 146), fill=ACCENT_START)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw_gradient_background(image)
    draw_logo_mark(image)
    image.save(OUTPUT_PATH, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
