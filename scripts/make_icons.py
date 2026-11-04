"""Draw the app icon and write it in each system's format, into the package.

A resume page with a check mark, on the app's navy: ``icon.png`` (Linux),
``icon.icns`` (macOS) and ``icon.ico`` (Windows), in resume_shortlister/assets.
The launchers (``resume_shortlister/launcher.py``) use them. Also the repository's
social preview, ``docs/images/social-preview.png`` (the card shown where a link to
it is shared; uploaded in the repository's settings). Needs Pillow, which the dev
install has (``pip install -e '.[dev]'``).

    python -m scripts.make_icons
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "resume_shortlister" / "assets"
SOCIAL_PREVIEW = ROOT / "docs" / "images" / "social-preview.png"
# Bold and regular sans-serif fonts, the first found (macOS, then common Linux ones).
FONTS = {
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
SIZE = 1024
NAVY, PAGE, LINE, ACCENT, WHITE = "#14213d", "#ffffff", "#c9d6ea", "#2a7ab8", "#ffffff"


def draw(size: int = SIZE) -> Image.Image:
    """The icon at ``size`` pixels, drawn at 4x and scaled down for smooth edges."""
    big = size * 4
    scale = big / SIZE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)

    def box(x0, y0, x1, y1):
        return [round(v * scale) for v in (x0, y0, x1, y1)]

    pen.rounded_rectangle(box(64, 64, 960, 960), radius=round(200 * scale), fill=NAVY)  # macOS-like margin
    pen.rounded_rectangle(box(250, 170, 690, 760), radius=round(36 * scale), fill=PAGE)  # the resume
    pen.ellipse(box(300, 230, 400, 330), fill=LINE)  # photo
    for y, right in ((250, 620), (300, 580)):
        pen.rounded_rectangle(box(430, y, right, y + 30), radius=round(15 * scale), fill=LINE)
    for y, right in ((400, 640), (460, 610), (520, 640), (580, 560)):
        pen.rounded_rectangle(box(300, y, right, y + 28), radius=round(14 * scale), fill=LINE)
    pen.ellipse(box(560, 560, 850, 850), fill=ACCENT, outline=NAVY, width=round(26 * scale))  # shortlisted
    pen.line([tuple(round(v * scale) for v in point) for point in ((632, 708), (688, 762), (784, 650))],
             fill=WHITE, width=round(44 * scale), joint="curve")
    return image.resize((size, size), Image.LANCZOS)


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(f"No {weight} font found; looked for {FONTS[weight]}")


def social_preview() -> Image.Image:
    """1280 x 640, as GitHub asks: the icon, the name, what it does and the facts that matter."""
    card = Image.new("RGB", (1280, 640), NAVY)
    card.paste(draw(360), (80, 140), draw(360))
    pen = ImageDraw.Draw(card)
    pen.text((490, 175), "Resume Shortlister", font=_font("bold", 72), fill=WHITE)
    pen.text((492, 275), "Explainable resume screening", font=_font("regular", 40), fill="#c9d6ea")
    pen.text((492, 325), "that runs on your computer.", font=_font("regular", 40), fill="#c9d6ea")
    pen.text((492, 410), "The evidence behind every score, from the resume itself.", font=_font("regular", 27), fill="#7cc4ff")
    pen.text((492, 470), "Free and open source  ·  Windows, macOS, Linux", font=_font("regular", 28), fill="#93a1b8")
    return card


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = draw()
    icon.resize((512, 512), Image.LANCZOS).save(ASSETS / "icon.png", optimize=True)
    icon.save(ASSETS / "icon.icns", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    icon.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    social_preview().save(SOCIAL_PREVIEW, optimize=True)
    for path in (ASSETS / "icon.png", ASSETS / "icon.icns", ASSETS / "icon.ico", SOCIAL_PREVIEW):
        print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
