import os
import asyncio
import threading
import time
import sqlite3
import json
import html
from http.server import BaseHTTPRequestHandler, HTTPServer

import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from google import genai


# =========================================================
# MATIX NEWS BOT
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

CHECK_INTERVAL = 600  # 10 minutes

DB_FILE = "sent_news.db"


# =========================================================
# NEWS SOURCES
# =========================================================

RSS_FEEDS = [

    # 🌍 BBC World
    (
        "BBC World",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "en"
    ),

    # 🇬🇧 BBC UK
    (
        "BBC UK",
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "en"
    ),

    # 💻 BBC Technology
    (
        "BBC Technology",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "en"
    ),

    # 🔬 BBC Science
    (
        "BBC Science",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "en"
    ),

    # 💰 BBC Business
    (
        "BBC Business",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "en"
    ),

    # 🇮🇷 ISNA
    (
        "ایسنا",
        "https://www.isna.ir/rss",
        "fa"
    ),

    # 🇮🇷 Tasnim
    (
        "تسنیم",
        "https://www.tasnimnews.com/fa/rss",
        "fa"
    ),
]


# =========================================================
# DATABASE
# =========================================================

def init_database():

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL,
            title TEXT,
            source TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()

    print("SQLite database initialized.")


def is_news_sent(link):

    if not link:
        return True

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute(
        "SELECT 1 FROM sent_news WHERE link = ? LIMIT 1",
        (link,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def save_news(link, title, source):

    if not link:
        return

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT OR IGNORE INTO sent_news
            (link, title, source)
            VALUES (?, ?, ?)
            """,
            (
                link,
                title,
                source
            )
        )

        connection.commit()

    except Exception as error:

        print(
            f"SQLite save error: {error}"
        )

    finally:

        connection.close()


# =========================================================
# GEMINI
# =========================================================

gemini_client = None

if GEMINI_API_KEY:

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print(
            "Gemini translation: ENABLED"
        )

    except Exception as error:

        print(
            "Gemini initialization error:"
        )

        print(
            str(error)
        )

else:

    print(
        "WARNING: GEMINI_API_KEY is not configured."
    )


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

        return


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

    text = str(text)

    text = html.unescape(text)

    result = []

    inside_tag = False

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

    text = " ".join(
        text.split()
    )

    return text.strip()


# =========================================================
# TRANSLATE WITH GEMINI
# =========================================================

async def translate_to_persian(
    title,
    description
):

    title = clean_text(title)

    description = clean_text(description)

    if not title and not description:

        return title, description

    if gemini_client is None:

        print(
            "Gemini unavailable. Original text will be used."
        )

        return title, description

    prompt = f"""
تو یک مترجم حرفه‌ای اخبار انگلیسی به فارسی هستی.

خبر زیر را به فارسی روان، طبیعی و قابل فهم ترجمه کن.

قوانین:

1. معنی خبر را تغییر نده.
2. هیچ اطلاعاتی از خودت اضافه نکن.
3. چیزی را حذف نکن مگر اینکه برای کوتاه‌سازی جزئی لازم باشد.
4. نام افراد، کشورها، سازمان‌ها و مکان‌ها را دقیق ترجمه کن.
5. متن فارسی طبیعی و صمیمی اما خبری باشد.
6. لحن تبلیغاتی نداشته باش.
7. درباره دین، مذهب یا عقاید مردم قضاوت نکن.
8. اگر خبر سیاسی است، فقط محتوای خبر را ترجمه کن.
9. هیچ منبعی به متن اضافه نکن.
10. هیچ Markdown اضافه نکن.
11. فقط JSON معتبر برگردان.
12. JSON باید دقیقاً شامل title و description باشد.

عنوان:
{title}

متن:
{description}
"""

    try:

        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

        result = response.text.strip()

        if result.startswith("```"):

            result = result.replace(
                "```json",
                ""
            )

            result = result.replace(
                "```",
                ""
            )

            result = result.strip()

        data = json.loads(result)

        translated_title = clean_text(
            data.get(
                "title",
                title
            )
        )

        translated_description = clean_text(
            data.get(
                "description",
                description
            )
        )

        print(
            "Translation successful."
        )

        return (
            translated_title,
            translated_description
        )

    except Exception as error:

        print(
            "TRANSLATION ERROR:"
        )

        print(
            str(error)
        )

        return (
            title,
            description
        )


# =========================================================
# GET IMAGE
# =========================================================

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

        url = enclosure.get("href")

        media_type = enclosure.get(
            "type",
            ""
        )

        if url and media_type.startswith(
            "image/"
        ):

            return url

    return None


# =========================================================
# CREATE MESSAGE
# =========================================================

def create_message(
    title,
    description
):

    title = clean_text(title)

    description = clean_text(description)

    # محدودیت کپشن تلگرام
    if len(description) > 850:

        description = (
            description[:850]
            + "..."
        )

    safe_title = html.escape(title)

    safe_description = html.escape(
        description
    )

    if safe_description:

        return (
            f"📰 <b>{safe_title}</b>\n\n"
            f"{safe_description}\n\n"
            f"@imatixnews"
        )

    return (
        f"📰 <b>{safe_title}</b>\n\n"
        f"@imatixnews"
    )


# =========================================================
# BUTTON
# =========================================================

def create_keyboard(url):

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


# =========================================================
# SEND NEWS
# =========================================================

async def send_news(
    bot,
    entry,
    source_name,
    language
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

    link = entry.get("link")

    if not link:

        return False

    # =====================================================
    # CHECK DUPLICATE
    # =====================================================

    if is_news_sent(link):

        print(
            f"SKIPPED DUPLICATE | {title}"
        )

        return False

    # =====================================================
    # TRANSLATION
    # =====================================================

    if language == "en":

        print(
            f"Translating: {title}"
        )

        title, description = await translate_to_persian(
            title,
            description
        )

    # =====================================================
    # MESSAGE
    # =====================================================

    message = create_message(
        title,
        description
    )

    keyboard = create_keyboard(
        link
    )

    # =====================================================
    # IMAGE
    # =====================================================

    image_url = get_image(entry)

    if image_url:

        try:

            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_url,
                caption=message,
                parse_mode="HTML",
                reply_markup=keyboard
            )

            save_news(
                link,
                title,
                source_name
            )

            print(
                f"IMAGE SENT | {source_name}"
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

        save_news(
            link,
            title,
            source_name
        )

        print(
            f"TEXT SENT | {source_name}"
        )

        return True

    except Exception as error:

        print(
            f"TELEGRAM ERROR | {error}"
        )

        return False


# =========================================================
# CHECK NEWS
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
        "======================================"
    )

    print(
        "MATIX NEWS - CHECKING NEWS"
    )

    print(
        "======================================"
    )

    for source_name, rss_url, language in RSS_FEEDS:

        print(
            f"Checking: {source_name}"
        )

        try:

            feed = await asyncio.to_thread(
                feedparser.parse,
                rss_url
            )

            if not feed.entries:

                print(
                    f"No entries: {source_name}"
                )

                continue

            print(
                f"Found {len(feed.entries)} entries."
            )

            # فقط 3 خبر از هر منبع
            for entry in feed.entries[:3]:

                await send_news(
                    bot,
                    entry,
                    source_name,
                    language
                )

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


# =========================================================
# MAIN LOOP
# =========================================================

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


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "          MATIX NEWS BOT"
    )

    print(
        "          STARTING..."
    )

    print(
        "======================================"
    )

    # ساخت دیتابیس
    init_database()

    # سرور Health برای Render
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # شروع ربات
    news_loop()
