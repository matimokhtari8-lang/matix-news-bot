import os
import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


# ==============================
# تنظیمات
# ==============================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")

CHECK_INTERVAL = 600  # هر 10 دقیقه

sent_links = set()


# ==============================
# منابع اخبار
# ==============================

RSS_FEEDS = [
    (
        "BBC World",
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    ),
    (
        "BBC UK",
        "https://feeds.bbci.co.uk/news/uk/rss.xml"
    ),
    (
        "BBC Technology",
        "https://feeds.bbci.co.uk/news/technology/rss.xml"
    ),
    (
        "BBC Science",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
    ),
    (
        "BBC Business",
        "https://feeds.bbci.co.uk/news/business/rss.xml"
    ),
    (
        "ایسنا",
        "https://www.isna.ir/rss"
    ),
    (
        "تسنیم",
        "https://www.tasnimnews.com/fa/rss"
    ),
]


# ==============================
# سرور Render
# ==============================

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
        return


def start_web_server():

    port = int(
        os.environ.get("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Web server started on port {port}"
    )

    server.serve_forever()


# ==============================
# تمیز کردن متن
# ==============================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    # حذف HTML ساده
    inside_tag = False
    result = []

    for char in text:

        if char == "<":
            inside_tag = True
            continue

        if char == ">":
            inside_tag = False
            continue

        if not inside_tag:
            result.append(char)

    text = "".join(result)

    # فاصله‌های اضافی
    text = " ".join(
        text.split()
    )

    return text.strip()


# ==============================
# پیدا کردن عکس
# ==============================

def get_image(entry):

    media_content = entry.get(
        "media_content",
        []
    )

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

    media_thumbnail = entry.get(
        "media_thumbnail",
        []
    )

    for media in media_thumbnail:

        url = media.get("url")

        if url:
            return url

    enclosures = entry.get(
        "enclosures",
        []
    )

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

    return None


# ==============================
# ساخت متن خبر
# ==============================

def make_message(
    title,
    description
):

    title = clean_text(title)
    description = clean_text(description)

    if len(description) > 850:
        description = (
            description[:850]
            + "..."
        )

    if description:

        return (
            f"📰 <b>{title}</b>\n\n"
            f"{description}\n\n"
            f"@imatixnews"
        )

    return (
        f"📰 <b>{title}</b>\n\n"
        f"@imatixnews"
    )


# ==============================
# دکمه خبر
# ==============================

def make_keyboard(url):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔗 مشاهده خبر",
                    url=url
                )
            ]
        ]
    )


# ==============================
# ارسال خبر
# ==============================

async def send_news(
    bot,
    entry,
    source_name
):

    title = clean_text(
        entry.get(
            "title",
            "خبر جدید"
        )
    )

    description = clean_text(
        entry.get(
            "summary",
            entry.get(
                "description",
                ""
            )
        )
    )

    url = entry.get(
        "link"
    )

    if not url:
        return False

    if url in sent_links:
        return False

    message = make_message(
        title,
        description
    )

    keyboard = make_keyboard(
        url
    )

    image_url = get_image(
        entry
    )

    # --------------------------
    # ارسال عکس
    # --------------------------

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
                f"IMAGE SENT: {source_name}"
            )

            sent_links.add(url)

            return True

        except Exception as error:

            print(
                f"IMAGE ERROR: {error}"
            )

    # --------------------------
    # ارسال متن
    # --------------------------

    try:

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        print(
            f"TEXT SENT: {source_name}"
        )

        sent_links.add(url)

        return True

    except Exception as error:

        print(
            f"TELEGRAM ERROR: {error}"
        )

        return False


# ==============================
# بررسی اخبار
# ==============================

async def check_news():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN is not configured."
        )

        return

    bot = Bot(
        token=BOT_TOKEN
    )

    print(
        "=============================="
    )

    print(
        "Checking news..."
    )

    print(
        "=============================="
    )

    for source_name, rss_url in RSS_FEEDS:

        print(
            f"Checking: {source_name}"
        )

        try:

            feed = feedparser.parse(
                rss_url
            )

            if not feed.entries:

                print(
                    f"No entries: {source_name}"
                )

                continue

            # فقط 3 خبر آخر
            for entry in feed.entries[:3]:

                await send_news(
                    bot,
                    entry,
                    source_name
                )

                # فاصله کوتاه بین ارسال‌ها
                await asyncio.sleep(2)

        except Exception as error:

            print(
                f"RSS ERROR: {source_name}"
            )

            print(
                str(error)
            )

    print(
        "News check completed."
    )


# ==============================
# حلقه اصلی
# ==============================

def news_loop():

    while True:

        try:

            asyncio.run(
                check_news()
            )

        except Exception as error:

            print(
                "MAIN LOOP ERROR:"
            )

            print(
                str(error)
            )

        print(
            "Waiting 10 minutes..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# ==============================
# شروع ربات
# ==============================

if __name__ == "__main__":

    print(
        "=============================="
    )

    print(
        "       MATIX NEWS BOT"
    )

    print(
        "       STARTING..."
    )

    print(
        "=============================="
    )

    # سرور Render
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # شروع دریافت اخبار
    news_loop()
