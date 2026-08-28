import os
import asyncio
import threading
import time
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer

import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


# =========================================================
# MATIX NEWS BOT
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")

CHECK_INTERVAL = 600

# =========================================================
# NEWS SOURCES
# =========================================================

RSS_FEEDS = [

    # 🇮🇷 ایران
    {
        "name": "ایسنا",
        "url": "https://www.isna.ir/rss"
    },

    {
        "name": "تسنیم",
        "url": "https://www.tasnimnews.com/fa/rss"
    },

    # 🌍 BBC World
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml"
    },

    # 🇬🇧 BBC UK
    {
        "name": "BBC UK",
        "url": "https://feeds.bbci.co.uk/news/uk/rss.xml"
    }
]


# جلوگیری از ارسال تکراری در زمان اجرای فعلی
sent_links = set()


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"MATIX NEWS BOT IS RUNNING"
        )

    def log_message(self, format, *args):
        pass


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Web server started on port {port}"
    )

    server.serve_forever()


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = html.unescape(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# FIND IMAGE
# =========================================================

def get_image(item):

    media_content = item.get(
        "media_content"
    )

    if media_content:

        for media in media_content:

            url = media.get("url")

            media_type = media.get(
                "type",
                ""
            )

            if url and (
                media_type.startswith("image/")
                or url.lower().endswith(
                    (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp"
                    )
                )
            ):

                return url


    media_thumbnail = item.get(
        "media_thumbnail"
    )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get("url")

            if url:
                return url


    enclosures = item.get(
        "enclosures"
    )

    if enclosures:

        for enclosure in enclosures:

            url = enclosure.get(
                "href"
            )

            media_type = enclosure.get(
                "type",
                ""
            )

            if url and media_type.startswith(
                "image/"
            ):

                return url


    description = item.get(
        "description",
        ""
    )

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        description,
        re.IGNORECASE
    )

    if match:

        return match.group(1)


    return None


# =========================================================
# FIND VIDEO
# =========================================================

def get_video(item):

    media_content = item.get(
        "media_content"
    )

    if media_content:

        for media in media_content:

            url = media.get("url")

            media_type = media.get(
                "type",
                ""
            )

            if url and (
                media_type.startswith("video/")
                or url.lower().endswith(
                    (
                        ".mp4",
                        ".mov",
                        ".m4v",
                        ".webm"
                    )
                )
            ):

                return url


    enclosures = item.get(
        "enclosures"
    )

    if enclosures:

        for enclosure in enclosures:

            url = enclosure.get(
                "href"
            )

            media_type = enclosure.get(
                "type",
                ""
            )

            if url and (
                media_type.startswith("video/")
                or url.lower().endswith(
                    (
                        ".mp4",
                        ".mov",
                        ".m4v",
                        ".webm"
                    )
                )
            ):

                return url


    return None


# =========================================================
# MESSAGE
# =========================================================

def create_message(
    title,
    summary
):

    title = html.escape(
        title
    )

    summary = html.escape(
        summary
    )

    if len(summary) > 900:

        summary = (
            summary[:900]
            + "..."
        )


    if summary:

        return (
            f"📰 <b>{title}</b>\n\n"
            f"{summary}\n\n"
            f"@imatixnews"
        )


    return (
        f"📰 <b>{title}</b>\n\n"
        f"@imatixnews"
    )


# =========================================================
# BUTTON
# =========================================================

def create_button(link):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔗 مشاهده خبر",
                    url=link
                )
            ]
        ]
    )


# =========================================================
# SEND NEWS
# =========================================================

async def send_news(
    bot,
    item,
    source_name
):

    title = clean_text(
        item.get(
            "title",
            "بدون عنوان"
        )
    )

    link = item.get(
        "link"
    )

    summary = clean_text(
        item.get(
            "summary",
            ""
        )
    )


    if not link:
        return False


    if link in sent_links:
        return False


    image_url = get_image(
        item
    )

    video_url = get_video(
        item
    )


    message = create_message(
        title,
        summary
    )


    keyboard = create_button(
        link
    )


    # =====================================================
    # VIDEO
    # =====================================================

    if video_url:

        try:

            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=video_url,
                caption=message,
                parse_mode="HTML",
                reply_markup=keyboard
            )

            print(
                f"VIDEO SENT | {source_name} | {title}"
            )

            sent_links.add(
                link
            )

            return True

        except Exception as error:

            print(
                f"VIDEO ERROR | {error}"
            )


    # =====================================================
    # IMAGE
    # =====================================================

    if image_url:

        try:

            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_url,
                caption=message,
                parse_mode="HTML",
                reply_markup=keyboard
            )

            print(
                f"IMAGE SENT | {source_name} | {title}"
            )

            sent_links.add(
                link
            )

            return True

        except Exception as error:

            print(
                f"IMAGE ERROR | {error}"
            )


    # =====================================================
    # TEXT
    # =====================================================

    try:

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        print(
            f"TEXT SENT | {source_name} | {title}"
        )

        sent_links.add(
            link
        )

        return True

    except Exception as error:

        print(
            f"TELEGRAM ERROR | {error}"
        )

        return False


# =========================================================
# CHECK ALL SOURCES
# =========================================================

async def check_news():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN is missing!"
        )

        return


    bot = Bot(
        token=BOT_TOKEN
    )


    print(
        "================================"
    )

    print(
        "Checking all news sources..."
    )

    print(
        "================================"
    )


    total_found = 0
    total_sent = 0


    for source in RSS_FEEDS:

        source_name = source["name"]
        rss_url = source["url"]


        print(
            f"Checking: {source_name}"
        )


        try:

            feed = feedparser.parse(
                rss_url
            )

        except
