import os
import asyncio
import threading
import time
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


# =========================================================
# MATIX NEWS BOT
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")

# بررسی خبرها هر 10 دقیقه
CHECK_INTERVAL = 600

# منابع RSS
RSS_FEEDS = [
    "https://www.isna.ir/rss",
    "https://www.tasnimnews.com/fa/rss"
]


# لینک‌هایی که در اجرای فعلی ارسال شده‌اند
sent_links = set()


# =========================================================
# RENDER WEB SERVER
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
        (
            "0.0.0.0",
            port
        ),
        HealthHandler
    )

    print(
        f"Web server started on port {port}"
    )

    server.serve_forever()


# =========================================================
# TEXT CLEANER
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
# GET IMAGE
# =========================================================

def get_image(item):

    # media_content
    media_content = item.get(
        "media_content"
    )

    if media_content:

        for media in media_content:

            url = media.get(
                "url"
            )

            if url:
                return url

    # media_thumbnail
    media_thumbnail = item.get(
        "media_thumbnail"
    )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get(
                "url"
            )

            if url:
                return url

    # enclosure
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
                media_type.startswith(
                    "image/"
                )
                or
                url.lower().endswith(
                    (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp"
                    )
                )
            ):
                return url

    # image داخل description
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
# GET VIDEO
# =========================================================

def get_video(item):

    # media_content
    media_content = item.get(
        "media_content"
    )

    if media_content:

        for media in media_content:

            url = media.get(
                "url"
            )

            media_type = media.get(
                "type",
                ""
            )

            if url and (
                media_type.startswith(
                    "video/"
                )
                or
                url.lower().endswith(
                    (
                        ".mp4",
                        ".mov",
                        ".m4v",
                        ".webm"
                    )
                )
            ):
                return url

    # enclosures
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
                media_type.startswith(
                    "video/"
                )
                or
                url.lower().endswith(
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
# CREATE MESSAGE
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

        message = (
            f"📰 <b>{title}</b>\n\n"
            f"{summary}\n\n"
            f"@imatixnews"
        )

    else:

        message = (
            f"📰 <b>{title}</b>\n\n"
            f"@imatixnews"
        )

    return message


# =========================================================
# BUTTON
# =========================================================

def create_button(link):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔗 مشاهده خبر",
                    url=link
                )
            ]
        ]
    )

    return keyboard


# =========================================================
# SEND ONE NEWS
# =========================================================

async def send_one_news(
    bot,
    item
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

    # -----------------------------------------------------
    # VIDEO
    # -----------------------------------------------------

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
                f"VIDEO SENT: {title}"
            )

            sent_links.add(
                link
            )

            return True

        except Exception as error:

            print(
                f"Video failed: {error}"
            )

    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

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
                f"IMAGE SENT: {title}"
            )

            sent_links.add(
                link
            )

            return True

        except Exception as error:

            print(
                f"Image failed: {error}"
            )

    # -----------------------------------------------------
    # TEXT ONLY
    # -----------------------------------------------------

    try:

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        print(
            f"TEXT SENT: {title}"
        )

        sent_links.add(
            link
        )

        return True

    except Exception as error:

        print(
            f"Telegram error: {error}"
        )

        return False


# =========================================================
# CHECK RSS
# =========================================================

async def check_news():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN is missing!"
        )

        return

    if not CHANNEL_ID:

        print(
            "ERROR: CHANNEL_ID is missing!"
        )

        return

    bot = Bot(
        token=BOT_TOKEN
    )

    print(
        "================================"
    )

    print(
        "Checking news..."
    )

    total_found = 0
    total_sent = 0

    for rss_url in RSS_FEEDS:

        print(
            f"RSS: {rss_url}"
        )

        try:

            feed = feedparser.parse(
                rss_url
            )

        except Exception as error:

            print(
                f"RSS ERROR: {error}"
            )

            continue

        if not feed.entries:

            print(
                "No entries found."
            )

            continue

        print(
            f"Found {len(feed.entries)} news"
        )

        # بررسی 5 خبر آخر
        for item in feed.entries[:5]:

            total_found += 1

            result = await send_one_news(
                bot,
                item
            )

            if result:

                total_sent += 1

    print(
        f"Found: {total_found}"
    )

    print(
        f"Sent: {total_sent}"
    )

    print(
        "================================"
    )


# =========================================================
# NEWS LOOP
# =========================================================

def news_loop():

    while True:

        try:

            asyncio.run(
                check_news()
            )

        except Exception as error:

            print(
                f"MAIN ERROR: {error}"
            )

        print(
            "Waiting 10 minutes..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "       MATIX NEWS BOT"
    )

    print(
        "       Starting..."
    )

    print(
        "================================"
    )

    # Render health server
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # News loop
    news_loop()
