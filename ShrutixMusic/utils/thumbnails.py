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

# === Special Birthday Template ===
TEMPLATE = "ShrutixMusic/assets/special_thumbnail.png"

CACHE_DIR = "cache"
CACHE_VERSION = "special_v1"          # different cache so normal thumbnails mix avvakunda


def _font(size):
    font_paths = (
        "ShrutixMusic/assets/font.ttf",
        "ShrutixMusic/assets/font2.ttf",
    )

    for font_path in font_paths:
        if os.path.isfile(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass

    return ImageFont.load_default()

def _draw_title(base, title):
    """
    Song title → perfect fit inside the Song box
    """
    draw = ImageDraw.Draw(base)

    title = str(title or "").strip()
    if not title:
        title = "Unknown Song"

    # ===== LAST ADJUSTMENT =====
    box_left   = 820          # 1 time more left
    box_right  = 1130         # 2 alphabets reduce
    y          = 610          # 1 time down
    max_width  = box_right - box_left
    # ===========================

    for font_size in (30, 26, 22, 18):
        font = _font(font_size)
        text = title

        while True:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width or len(text) < 8:
                break

            if text.endswith("..."):
                text = text[:-4].rstrip() + "..."
            else:
                text = text[:-1].rstrip() + "..."

        if text_width <= max_width:
            break

    # Soft shadow
    draw.text(
        (box_left + 2, y + 2),
        text,
        font=font,
        fill=(0, 0, 0, 160),
    )

    # Main text
    draw.text(
        (box_left, y),
        text,
        font=font,
        fill=(255, 240, 210, 255),
    )

    
    


async def _fetch_thumbnail(session, videoid, quality):
    url = f"https://i.ytimg.com/vi/{videoid}/{quality}.jpg"

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
        image = Image.open(BytesIO(raw)).convert("RGB")
        image.load()
    except Exception:
        return None

    if image.width < _MIN_WIDTH:
        return None

    return raw


async def _fetch_youtube_title(session, videoid):
    url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={videoid}"
        "&format=json"
    )

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
            title = data.get("title")
            if title:
                return str(title).strip()
    except Exception:
        return None

    return None


def _cache_path(videoid, title):
    value = f"{CACHE_VERSION}:{videoid}:{title}"
    key = hashlib.md5(value.encode("utf-8", errors="ignore")).hexdigest()
    return os.path.join(CACHE_DIR, f"special_{key}.jpg")


def _create_thumbnail(song_raw, title, output):
    if not os.path.isfile(TEMPLATE):
        raise FileNotFoundError(f"Special thumbnail template not found: {TEMPLATE}")

    template = Image.open(TEMPLATE).convert("RGBA")

    if template.size != (1280, 720):
        template = template.resize((1280, 720), Image.Resampling.LANCZOS)

    # NOTE: Circle cover paste cheyyatledu
    # Left side lo couple photo undi, cover avvakunda

    _draw_title(template, title)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    temp_output = output + ".tmp.jpg"

    try:
        template.convert("RGB").save(
            temp_output,
            "JPEG",
            quality=95,
            optimize=True,
        )
        os.replace(temp_output, output)
    finally:
        if os.path.isfile(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass

    return output


async def get_thumb(videoid, title=None):
    if not videoid:
        return YOUTUBE_IMG_URL

    videoid = str(videoid).strip()

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        timeout = aiohttp.ClientTimeout(total=15, connect=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            title = str(title or "").strip()

            if not title:
                title = await _fetch_youtube_title(session, videoid)

            if not title:
                title = "Unknown Song"

            path = _cache_path(videoid, title)

            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return path

            song_raw = None

            for quality in _SOURCES:
                song_raw = await _fetch_thumbnail(session, videoid, quality)
                if song_raw:
                    break

            if not song_raw:
                return YOUTUBE_IMG_URL

            return _create_thumbnail(song_raw, title, path)

    except Exception:
        return YOUTUBE_IMG_URL
