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
CACHE_VERSION = "v9"          # final version


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
    """
    Song title left box lo correct ga undeli.
    Overflow fix + pixel based truncation + smaller text.
    """
    draw = ImageDraw.Draw(base)

    title = str(title or "").strip()
    if not title:
        title = "Unknown Song"

    # Box boundaries (tight)
    box_left  = 95
    box_right = 520
    max_width = box_right - box_left
    y = 398

    # Dynamic font size (smaller)
    for font_size in (38, 34, 30, 26, 22):
        font = _font(font_size)

        test = title
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            break

        # Truncate until it fits
        while True:
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) <= max_width or len(test) <= 4:
                break
            if test.endswith("..."):
                test = test[:-4].rstrip() + "..."
            else:
                test = test[:-1].rstrip() + "..."

        title = test
        break

    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]

    x = box_left

    if x + text_width > box_right:
        x = box_right - text_width

    # Soft shadow
    draw.text(
        (x + 2, y + 2),
        title,
        font=font,
        fill=(0, 0, 0, 180),
    )

    # Main title
    draw.text(
        (x, y),
        title,
        font=font,
        fill=(245, 245, 250, 255),
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

    if template.size != (1280, 720):
        template = template.resize(
            (1280, 720),
            Image.Resampling.LANCZOS,
        )

    song_image = Image.open(
        BytesIO(song_raw)
    ).convert("RGB")

    _circle_image(
        template,
        song_image,
        center=(275, 150),
        radius=115,
    )

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

            path = _cache_path(
                videoid,
                title,
            )

            if (
                os.path.isfile(path)
                and os.path.getsize(path) > 0
            ):
                return path

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

            return _create_thumbnail(
                song_raw,
                title,
                path,
            )

    except Exception:

        return YOUTUBE_IMG_URL
