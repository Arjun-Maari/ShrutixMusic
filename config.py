import re
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# Get from my.telegram.org/app
API_ID = int(getenv("API_ID", ""))
API_HASH = getenv("API_HASH", "")

# Get from @BotFather
BOT_TOKEN = getenv("BOT_TOKEN", "")

# Get from MongoDB Atlas
MONGO_DB_URI = getenv("MONGO_DB_URI", "")

DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", "60"))

LOGGER_ID = int(getenv("LOGGER_ID", "0"))
OWNER_ID = int(getenv("OWNER_ID", "7574330905"))

# Heroku App Name
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME", "")

# Get from dashboard.heroku.com/account
HEROKU_API_KEY = getenv("HEROKU_API_KEY", "")

UPSTREAM_REPO = getenv(
    "UPSTREAM_REPO",
    "https://github.com/NoxxOP/ShrutixMusic",
)

UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")

GIT_TOKEN = getenv("GIT_TOKEN")

# Get API Key from @SHRUTIAPIBOT

SUPPORT_CHANNEL = getenv(
    "SUPPORT_CHANNEL",
    "https://t.me/ShrutiBots"
)

SUPPORT_CHAT = getenv(
    "SUPPORT_CHAT",
    "https://t.me/ShrutiSupportChat"
)

AUTO_LEAVING_ASSISTANT = getenv(
    "AUTO_LEAVING_ASSISTANT",
    "False"
).lower() == "true"

# Get from developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET")

PLAYLIST_FETCH_LIMIT = int(
    getenv("PLAYLIST_FETCH_LIMIT", "25")
)

TG_AUDIO_FILESIZE_LIMIT = int(
    getenv("TG_AUDIO_FILESIZE_LIMIT", "104857600")
)

TG_VIDEO_FILESIZE_LIMIT = int(
    getenv("TG_VIDEO_FILESIZE_LIMIT", "1073741824")
)

# Get from @Sessionbbbot
STRING1 = getenv("STRING_SESSION")
STRING2 = getenv("STRING_SESSION2")
STRING3 = getenv("STRING_SESSION3")
STRING4 = getenv("STRING_SESSION4")
STRING5 = getenv("STRING_SESSION5")

BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}

START_IMG_URL = getenv(
    "START_IMG_URL",
    "https://graph.org/file/7557c0e0e0c1708f62d6a-6892ea881cc1555c83.jpg"
)

PING_IMG_URL = getenv(
    "PING_IMG_URL",
    "https://graph.org/file/f35df5dd605d76ff790b7-953db0f3e71a2e5a1a.jpg"
)

PLAYLIST_IMG_URL = "https://te.legra.ph/file/4ec5ae4381dffb039b4ef.jpg"
STATS_IMG_URL = "https://graph.org/file/e34a8495731b9996c06ec-8c5ed3d017600402c8.jpg"
TELEGRAM_AUDIO_URL = "https://graph.org/file/e6ec39189581cf8fa3402-7f014243d99a5d5fee.jpg"
TELEGRAM_VIDEO_URL = "https://graph.org/file/8524188ba29b3b1ee7d8a-9a5e026b945081c0bd.jpg"
STREAM_IMG_URL = "https://graph.org/file/fa249f1a70836622b6a95-6b0c6b6895fc7b29b2.jpg"
SOUNCLOUD_IMG_URL = "https://graph.org/file/20e919da1422de0e5819a-ea3a2508c22d67bcbd.jpg"
YOUTUBE_IMG_URL = "https://graph.org/file/c56b870e112a37362c170-142c72cba6b84de4e0.jpg"
SPOTIFY_ARTIST_IMG_URL = "https://graph.org/file/d8054a7e124e257de1896-d70cdc24d9e56d5560.jpg"
SPOTIFY_ALBUM_IMG_URL = "https://graph.org/file/d8054a7e124e257de1896-d70cdc24d9e56d5560.jpg"
SPOTIFY_PLAYLIST_IMG_URL = "https://graph.org/file/d8054a7e124e257de1896-d70cdc24d9e56d5560.jpg"


def time_to_seconds(time):
    stringt = str(time)
    return sum(
        int(x) * 60 ** i
        for i, x in enumerate(reversed(stringt.split(":")))
    )


DURATION_LIMIT = int(
    time_to_seconds(f"{DURATION_LIMIT_MIN}:00")
)


if SUPPORT_CHANNEL:
    if not re.match("(?:http|https)://", SUPPORT_CHANNEL):
        raise SystemExit(
            "[ERROR] SUPPORT_CHANNEL url must start with https://"
        )

if SUPPORT_CHAT:
    if not re.match("(?:http|https)://", SUPPORT_CHAT):
        raise SystemExit(
            "[ERROR] SUPPORT_CHAT url must start with https://"
        )
