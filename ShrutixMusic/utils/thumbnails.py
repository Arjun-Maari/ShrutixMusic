import hashlib
import os
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from config import YOUTUBE_IMG_URL


# YouTube thumbnail quality order
_SOURCES = (
    "maxresdefault",
    "sddefault",
    "hqdefault",
    "mqdefault",
)

_MIN_WIDTH = 300

# Your fixed thumbnail template
TEMPLATE = "ShrutixMusic/assets/music_thumbnail.png"

# Cache
CACHE_DIR = "cache"
CACHE_VERSION = "v5"


def _font(size):
    font_paths = (
        "ShrutixMusic/assets/font.ttf",
        "ShrutixMusic/assets/font2.ttf",
    )

    for font_path in font_paths:
        if os.path.isfile(font_path):
            try:
                return ImageFont.truetype(
                    font_path,
                    size,
                )
            except Exception:
                pass

    return ImageFont.load_default()


def _fit_cover(image, size):
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


def _circle_image(
    base,
    song_image,
    center,
    radius,
):
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


def _draw_title(base, title):
    draw = ImageDraw.Draw(base)

    title = str(title or "").strip()

    if not title:
        title = "Unknown Song"

    # Crystal Hearts title area
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

    # Keep title inside the box
    if len(title) > 38:
        title = title[:35] + "..."

    # Dynamic font size
    if len(title) > 32:
        font_size = 30
    elif len(title) > 25:
        font_size = 36
    else:
        font_size = 44

    font = _font(font_size)

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=font,
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    center_x = (75 + 570) // 2
    center_y = (475 + 545) // 2

    x = center_x - (text_width // 2)
    y = center_y - (text_height // 2)

    # Shadow
    draw.text(
        (
            x + 3,
            y + 3,
        ),
        title,
        font=font,
        fill=(0, 0, 0, 230),
    )

    # Song title
    draw.text(
        (
            x,
            y,
        ),
        title,
        font=font,
        fill=(255, 255, 255, 255),
    )


async def _fetch_thumbnail(
    session,
    videoid,
    quality,
):
    url = (
        f"https://i.ytimg.com/vi/"
        f"{videoid}/{quality}.jpg"
    )

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            raw = await resp.read()

    except Exception:
        return None

    if not raw:
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


async def _fetch_youtube_title(
    session,
    videoid,
):
    """
    Gets the actual YouTube video title.
    This is the fallback when the caller doesn't
    provide a title.
    """

    url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={videoid}"
        "&format=json"
    )

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            data = await resp.json(
                content_type=None
            )

            title = data.get("title")

            if title:
                return str(title).strip()

    except Exception:
        return None

    return None


def _cache_path(videoid, title):
    value = (
        f"{CACHE_VERSION}:"
        f"{videoid}:"
        f"{title}"
    )

    key = hashlib.md5(
        value.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()

    return os.path.join(
        CACHE_DIR,
        f"custom_{key}.jpg",
    )


def _create_thumbnail(
    song_raw,
    title,
    output,
):
    if not os.path.isfile(TEMPLATE):
        raise FileNotFoundError(
            "Thumbnail template not found: "
            f"{TEMPLATE}"
        )

    template = Image.open(
        TEMPLATE
    ).convert("RGBA")

    # Force 1280x720
    if template.size != (1280, 720):
        template = template.resize(
            (1280, 720),
            Image.Resampling.LANCZOS,
        )

    song_image = Image.open(
        BytesIO(song_raw)
    ).convert("RGB")

    # YouTube thumbnail inside top circle
    _circle_image(
        template,
        song_image,
        center=(275, 150),
        radius=105,
    )

    # Actual song title near Crystal Hearts
    _draw_title(
        template,
        title,
    )

    os.makedirs(
        os.path.dirname(output) or ".",
        exist_ok=True,
    )

    temp_output = output + ".tmp.jpg"

    try:
        template.convert("RGB").save(
            temp_output,
            "JPEG",
            quality=95,
            optimize=True,
        )

        os.replace(
            temp_output,
            output,
        )

    finally:
        if os.path.isfile(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass

    return output


async def get_thumb(
    videoid,
    title=None,
):
    """
    Main thumbnail function.

    If title is supplied:
        use supplied song title.

    If title is missing:
        automatically fetch the real YouTube title.
    """

    if not videoid:
        return YOUTUBE_IMG_URL

    videoid = str(videoid).strip()

    try:
        os.makedirs(
            CACHE_DIR,
            exist_ok=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=15,
            connect=5,
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            # ---------------------------------
            # GET REAL SONG TITLE
            # ---------------------------------

            title = str(
                title or ""
            ).strip()

            if not title:
                title = await _fetch_youtube_title(
                    session,
                    videoid,
                )

            if not title:
                title = "Unknown Song"

            # ---------------------------------
            # CACHE
            # ---------------------------------

            path = _cache_path(
                videoid,
                title,
            )

            if (
                os.path.isfile(path)
                and os.path.getsize(path) > 0
            ):
                return path

            # ---------------------------------
            # GET YOUTUBE IMAGE
            # ---------------------------------

            song_raw = None

            for quality in _SOURCES:
                song_raw = await _fetch_thumbnail(
                    session,
                    videoid,
                    quality,
                )

                if song_raw:
                    break

            if not song_raw:
                return YOUTUBE_IMG_URL

            # ---------------------------------
            # CREATE CUSTOM THUMBNAIL
            # ---------------------------------

            return _create_thumbnail(
                song_raw,
                title,
                path,
            )

    except Exception:
        return YOUTUBE_IMG_URL
