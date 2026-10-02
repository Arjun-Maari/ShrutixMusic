import os
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from config import YOUTUBE_IMG_URL


_SOURCES = (
    "maxresdefault",
    "sddefault",
    "hqdefault",
    "mqdefault",
)

_MIN_WIDTH = 300

TEMPLATE = "ShrutixMusic/assets/music_thumbnail.png"


def _font(size):
    font_path = "ShrutixMusic/assets/font.ttf"

    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def _fit_cover(image, size):
    image = image.convert("RGB")

    target_w, target_h = size

    ratio = max(
        target_w / image.width,
        target_h / image.height,
    )

    new_size = (
        int(image.width * ratio),
        int(image.height * ratio),
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS,
    )

    left = (image.width - target_w) // 2
    top = (image.height - target_h) // 2

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


def _circle_image(base, song_image, center, radius):
    size = radius * 2

    song_image = _fit_cover(
        song_image,
        (size, size),
    )

    mask = Image.new(
        "L",
        (size, size),
        0,
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (0, 0, size - 1, size - 1),
        fill=255,
    )

    x = center[0] - radius
    y = center[1] - radius

    base.paste(
        song_image,
        (x, y),
        mask,
    )


def _draw_title(base, title):
    draw = ImageDraw.Draw(base)

    # Cover the old "Celestial Hearts" text area
    draw.rounded_rectangle(
        (75, 475, 570, 545),
        radius=18,
        fill=(5, 8, 18, 225),
    )

    title = (title or "Unknown Song").strip()

    # Keep the thumbnail clean
    if len(title) > 38:
        title = title[:35] + "..."

    font_size = 48

    if len(title) > 28:
        font_size = 40

    if len(title) > 35:
        font_size = 34

    font = _font(font_size)

    # Center title
    bbox = draw.textbbox(
        (0, 0),
        title,
        font=font,
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = 320 - (text_width // 2)
    y = 510 - (text_height // 2)

    # Shadow
    draw.text(
        (x + 3, y + 3),
        title,
        font=font,
        fill=(0, 0, 0, 230),
    )

    # Song title
    draw.text(
        (x, y),
        title,
        font=font,
        fill=(255, 255, 255, 255),
    )


async def _fetch(session, videoid, name):
    url = f"https://i.ytimg.com/vi/{videoid}/{name}.jpg"

    try:
        async with session.get(url) as resp:

            if resp.status != 200:
                return None

            raw = await resp.read()

    except Exception:
        return None

    try:
        image = Image.open(
            BytesIO(raw)
        ).convert("RGB")

        image.load()

    except Exception:
        return None

    if image.width < _MIN_WIDTH:
        return None

    return raw


def _create_thumbnail(song_raw, title, output):
    # Load your fixed template
    template = Image.open(
        TEMPLATE
    ).convert("RGBA")

    # YouTube thumbnail ratio
    template = template.resize(
        (1280, 720),
        Image.Resampling.LANCZOS,
    )

    # YouTube song image
    song_image = Image.open(
        BytesIO(song_raw)
    ).convert("RGB")

    # --------------------------------
    # TOP CIRCLE
    # --------------------------------

    _circle_image(
        template,
        song_image,
        center=(275, 150),
        radius=105,
    )

    # --------------------------------
    # SONG TITLE
    # --------------------------------

    _draw_title(
        template,
        title,
    )

    # --------------------------------
    # SAVE
    # --------------------------------

    template.convert("RGB").save(
        output,
        "JPEG",
        quality=95,
        optimize=True,
    )

    return output


async def get_thumb(videoid, title=None):
    """
    Generate custom music thumbnail.

    Template:
        ShrutixMusic/assets/music_thumbnail.png

    Top circle:
        YouTube song thumbnail

    Bottom:
        Dynamic song title
    """

    path = f"cache/custom_{videoid}.jpg"

    if (
        os.path.isfile(path)
        and os.path.getsize(path) > 0
    ):
        return path

    try:
        os.makedirs(
            "cache",
            exist_ok=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=10
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            song_raw = None

            for name in _SOURCES:

                song_raw = await _fetch(
                    session,
                    videoid,
                    name,
                )

                if song_raw:
                    break

            if not song_raw:
                return YOUTUBE_IMG_URL

            return _create_thumbnail(
                song_raw,
                title,
                path,
            )

    except Exception:
        return YOUTUBE_IMG_URL
