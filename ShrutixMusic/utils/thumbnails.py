import hashlib
import os
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from config import YOUTUBE_IMG_URL


# ==========================================================
# CONFIG
# ==========================================================

_SOURCES = (
    "maxresdefault",
    "sddefault",
    "hqdefault",
    "mqdefault",
)

_MIN_WIDTH = 300

TEMPLATE = "ShrutixMusic/assets/music_thumbnail.png"

CACHE_DIR = "cache"

# Change this whenever you change the thumbnail design.
# This automatically prevents old cached thumbnails from being used.
CACHE_VERSION = "v2"


# ==========================================================
# FONT
# ==========================================================

def _font(size):
    font_paths = (
        "ShrutixMusic/assets/font.ttf",
        "ShrutixMusic/assets/font2.ttf",
    )

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(
                    font_path,
                    size,
                )
            except Exception:
                pass

    return ImageFont.load_default()


# ==========================================================
# IMAGE COVER
# ==========================================================

def _fit_cover(image, size):
    """
    Crop image to completely fill the requested size
    without stretching.
    """

    image = image.convert("RGB")

    target_w, target_h = size

    if image.width <= 0 or image.height <= 0:
        raise ValueError("Invalid image size")

    ratio = max(
        target_w / image.width,
        target_h / image.height,
    )

    new_size = (
        max(1, int(image.width * ratio)),
        max(1, int(image.height * ratio)),
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS,
    )

    left = max(
        0,
        (image.width - target_w) // 2,
    )

    top = max(
        0,
        (image.height - target_h) // 2,
    )

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


# ==========================================================
# CIRCLE YOUTUBE THUMBNAIL
# ==========================================================

def _circle_image(
    base,
    song_image,
    center,
    radius,
):
    """
    Put the YouTube thumbnail inside a perfect circle.
    """

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
        (
            0,
            0,
            size - 1,
            size - 1,
        ),
        fill=255,
    )

    x = center[0] - radius
    y = center[1] - radius

    base.paste(
        song_image,
        (x, y),
        mask,
    )


# ==========================================================
# SONG TITLE
# ==========================================================

def _draw_title(base, title):
    """
    Replace the existing title in the template
    with the actual YouTube song title.
    """

    draw = ImageDraw.Draw(base)

    title = str(
        title or "Unknown Song"
    ).strip()

    if not title:
        title = "Unknown Song"

    # ------------------------------------------------------
    # TITLE AREA
    # ------------------------------------------------------

    # This covers the existing Crystal Hearts text.
    draw.rounded_rectangle(
        (
            75,
            475,
            570,
            545,
        ),
        radius=18,
        fill=(5, 8, 18, 225),
    )

    # ------------------------------------------------------
    # TITLE LENGTH
    # ------------------------------------------------------

    if len(title) > 38:
        title = title[:35] + "..."

    if len(title) > 35:
        font_size = 34

    elif len(title) > 28:
        font_size = 40

    else:
        font_size = 48

    font = _font(font_size)

    # ------------------------------------------------------
    # CENTER TEXT
    # ------------------------------------------------------

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=font,
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    area_center_x = (
        75 + 570
    ) // 2

    area_center_y = (
        475 + 545
    ) // 2

    x = area_center_x - (
        text_width // 2
    )

    y = area_center_y - (
        text_height // 2
    )

    # ------------------------------------------------------
    # SHADOW
    # ------------------------------------------------------

    draw.text(
        (
            x + 3,
            y + 3,
        ),
        title,
        font=font,
        fill=(0, 0, 0, 230),
    )

    # ------------------------------------------------------
    # TITLE
    # ------------------------------------------------------

    draw.text(
        (
            x,
            y,
        ),
        title,
        font=font,
        fill=(255, 255, 255, 255),
    )


# ==========================================================
# YOUTUBE THUMBNAIL FETCH
# ==========================================================

async def _fetch(
    session,
    videoid,
    name,
):
    url = (
        f"https://i.ytimg.com/vi/"
        f"{videoid}/{name}.jpg"
    )

    try:

        async with session.get(
            url
        ) as resp:

            if resp
