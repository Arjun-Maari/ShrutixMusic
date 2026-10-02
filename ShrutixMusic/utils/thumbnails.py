import hashlib
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

CACHE_DIR = "cache"
CACHE_VERSION = "v6"


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

    # -----------------------------------------
    # TITLE BOX
    # -----------------------------------------

    box_left = 75
    box_top = 475
    box_right = 570
    box_bottom = 545

    draw.rounded_rectangle(
        (
            box_left,
            box_top,
            box_right,
            box_bottom,
        ),
        radius=18,
        fill=(5, 8, 18, 225),
    )

    # -----------------------------------------
    # CLEAN TITLE
    # -----------------------------------------

    # Maximum characters
    if len(title) > 38:
        title = title[:38] + "..."

    # -----------------------------------------
    # DYNAMIC FONT SIZE
    # -----------------------------------------

    if len(title) > 34:
        font_size = 27
    elif len(title) > 29:
        font_size = 31
    elif len(title) > 23:
        font_size = 36
    elif len(title) > 17:
        font_size = 40
    else:
        font_size = 43

    font = _font(font_size)

    # -----------------------------------------
    # TEXT SIZE
    # -----------------------------------------

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=font,
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # -----------------------------------------
    # CENTER HORIZONTALLY
    # -----------------------------------------

    x = (
        (box_left + box_right) // 2
        - text_width // 2
    )

    # -----------------------------------------
    # MOVE TEXT UP
    # -----------------------------------------

    y = (
        (box_top + box_bottom) // 2
        - text_height // 2
        - 16
    )

    # -----------------------------------------
    # SAFETY LIMITS
    # -----------------------------------------

    if x < box_left + 10:
        x = box_left + 10

    if x + text_width > box_right - 10:
        x = box_right - text_width - 10

    # -----------------------------------------
    # SHADOW
    # -----------------------------------------

    draw.text(
        (
            x + 2,
            y + 2,
        ),
        title,
        font=font,
        fill=(0, 0, 0, 230),
    )

    # -----------------------------------------
    # SONG TITLE
    # -----------------------------------------

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
    Fetch the actual YouTube title
    when title is not supplied by caller.
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
    # -----------------------------------------
    # CHECK TEMPLATE
    # -----------------------------------------

    if not os.path.isfile(TEMPLATE):
        raise FileNotFoundError(
            "Thumbnail template not found: "
            f"{TEMPLATE}"
        )

    # -----------------------------------------
    # LOAD TEMPLATE
    # -----------------------------------------

    template = Image.open(
        TEMPLATE
    ).convert("RGBA")

    # -----------------------------------------
    # FORCE 1280x720
    # -----------------------------------------

    if template.size != (1280, 720):
        template = template.resize(
            (1280, 720),
            Image.Resampling.LANCZOS,
        )

    # -----------------------------------------
    # LOAD YOUTUBE IMAGE
    # -----------------------------------------

    song_image = Image.open(
        BytesIO(song_raw)
    ).convert("RGB")

    # -----------------------------------------
    # PUT YOUTUBE IMAGE IN CIRCLE
    # -----------------------------------------

    _circle_image(
        template,
        song_image,
        center=(275, 150),
        radius=105,
    )

    # -----------------------------------------
    # PUT SONG TITLE
    # -----------------------------------------

    _draw_title(
        template,
        title,
    )

    # -----------------------------------------
    # CREATE CACHE DIRECTORY
    # -----------------------------------------

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
    Generate custom music thumbnail.

    videoid:
        YouTube video ID

    title:
        Song title. If missing, the real
        YouTube title will be fetched.
    """

    # -----------------------------------------
    # INVALID VIDEO ID
    # -----------------------------------------

    if not videoid:
        return YOUTUBE_IMG_URL

    videoid = str(videoid).strip()

    try:

        # -------------------------------------
        # CREATE CACHE DIRECTORY
        # -------------------------------------

        os.makedirs(
            CACHE_DIR,
            exist_ok=True,
        )

        # -------------------------------------
        # HTTP TIMEOUT
        # -------------------------------------

        timeout = aiohttp.ClientTimeout(
            total=15,
            connect=5,
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            # ---------------------------------
            # GET TITLE
            # ---------------------------------

            title = str(
                title or ""
            ).strip()

            # If caller didn't provide title,
            # fetch actual YouTube title.
            if not title:

                title = await _fetch_youtube_title(
                    session,
                    videoid,
                )

            # Final fallback
            if not title:
                title = "Unknown Song"

            # ---------------------------------
            # CACHE PATH
            # ---------------------------------

            path = _cache_path(
                videoid,
                title,
            )

            # ---------------------------------
            # USE EXISTING CACHE
            # ---------------------------------

            if (
                os.path.isfile(path)
                and os.path.getsize(path) > 0
            ):
                return path

            # ---------------------------------
            # DOWNLOAD YOUTUBE THUMBNAIL
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

            # ---------------------------------
            # NO IMAGE
            # ---------------------------------

            if not song_raw:
                return YOUTUBE_IMG_URL

            # ---------------------------------
            # CREATE FINAL THUMBNAIL
            # ---------------------------------

            return _create_thumbnail(
                song_raw,
                title,
                path,
            )

    except Exception:

        return YOUTUBE_IMG_URL
