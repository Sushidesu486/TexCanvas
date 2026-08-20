#!/usr/bin/env python3
"""Generate the editable demo deck's example raster figure."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "examples" / "assets" / "example-figure.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 800), "#F7F9FC")
    draw = ImageDraw.Draw(image)
    colors = ["#16324F", "#244E70", "#F4A261"]
    labels = ["Sample", "Experiment", "Analysis"]
    centers = [(300, 400), (800, 400), (1300, 400)]
    font = ImageFont.load_default(size=36)
    for index, ((cx, cy), label, fill) in enumerate(zip(centers, labels, colors, strict=True)):
        draw.rounded_rectangle((cx - 155, cy - 85, cx + 155, cy + 85), radius=28, fill=fill)
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text((cx - (bounds[2] - bounds[0]) / 2, cy - 22), label, fill="white", font=font)
        if index < len(centers) - 1:
            next_x = centers[index + 1][0]
            draw.line((cx + 165, cy, next_x - 185, cy), fill="#65727E", width=10)
            draw.polygon(((next_x - 185, cy), (next_x - 220, cy - 22), (next_x - 220, cy + 22)), fill="#65727E")
    image.save(output, format="PNG")
    print(f"Created {output}")


if __name__ == "__main__":
    main()

