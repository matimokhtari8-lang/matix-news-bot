import os
import asyncio
import threading
import time
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

# مدل Gemini
GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

# هر چند دقیقه RSSها بررسی شوند
CHECK_INTERVAL = 600

# حداکثر خبر از هر منبع در هر بررسی
MAX_NEWS_PER_SOURCE = 3

# لینک‌های ارسال‌شده در اجرای فعلی
sent_links = set()


# =========================================================
# NEWS SOURCES
# =========================================================

RSS_FEEDS = [

    # =========================
    # BBC
    # =========================

    (
        "BBC World",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "en"
    ),

    (
        "BBC UK",
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "en"
    ),

    (
        "BBC Technology",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "en"
    ),

    (
        "BBC Science",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "en"
    ),

    (
        "BBC Business",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "en"
    ),

    # =========================
    # Persian sources
    # =========================

    (
        "ایسنا",
        "https://www.isna.ir/rss",
        "fa"
    ),

    (
        "تسنیم",
        "https://www.tasnimnews.com/fa/rss",
        "fa"
    ),
]


# =========================================================
# GEMINI
# =========================================================

gemini_client = None

if GEMINI_API_KEY:

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("Gemini: ENABLED")
        print(f"Gemini model: {GEMINI_MODEL}")

    except Exception as error:

        print("Gemini initialization error:")
        print(str(error))

else:

    print("WARNING: GEMINI_API_KEY is not configured.")


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

    # حذف HTML
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
# GEMINI NEWS FILTER
# =========================================================

async def analyze_news(
    title,
    description,
    language
):

    title = clean_text(title)
    description = clean_text(description)

    # اگر Gemini فعال نباشد
    if gemini_client is None:

        print(
            "AI FILTER: Gemini unavailable."
        )

        # برای جلوگیری از انتشار اشتباه
        # اخبار خارجی بدون AI رد می‌شوند.
        if language == "en":

            return {
                "publish": False,
                "reason": "Gemini unavailable"
            }

        return {
            "publish": True,
            "reason": "Persian source - AI unavailable",
            "title": title,
            "description": description
        }


    prompt = f"""
You are the editorial AI for a Persian Telegram news channel.

Your job is to classify and rewrite a news article.

IMPORTANT EDITORIAL POLICY:

1. The channel is interested in news that is critical of
   the Islamic Republic of Iran and its government,
   including political repression, protests, human rights,
   government actions, corruption, political conflicts,
   and criticism of government officials.

2. Important war, military conflict, attacks, security crises
   and major regional conflicts may also be published.

3. Important international news may be published when it is
   relevant or significant.

4. DO NOT publish content whose main purpose is insulting,
   mocking or attacking Islam, Muslims, religious beliefs,
   prophets, holy figures or religious sacred values.

5. DO NOT invent facts.

6. DO NOT change the factual meaning of the original article.

7. DO NOT turn a neutral article into propaganda.

8. News that is purely promotional or praising the Islamic
   Republic government should normally be rejected.

9. Criticism of a government is NOT the same as criticism
   of a religion. Government criticism is allowed.

10. If the article contains both political criticism and
    religiously offensive material, reject it if the
    offensive religious material is a significant part
    of the article.

11. Write in natural, simple and friendly Persian.

12. Keep the tone like a professional Telegram news channel,
    not like a formal newspaper.

13. Do not add a source name.

14. Do not add a URL.

15. Do not use Markdown.

Return ONLY valid JSON.

JSON format:

{{
    "publish": true or false,
    "category": "iran_politics" | "war" | "international" | "technology" | "science" | "business" | "other",
    "reason": "short reason",
    "title": "Persian title",
    "description": "Persian short news text"
}}

TITLE:
{title}

DESCRIPTION:
{description}
"""


    try:

        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt
        )

        result = response.text.strip()

        # حذف Markdown احتمالی
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

        publish = bool(
            data.get(
                "publish",
                False
            )
        )

        category = str(
            data.get(
                "category",
                "other"
            )
        )

        reason = clean_text(
            data.get(
                "reason",
                ""
            )
        )

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
            f"AI FILTER | publish={publish} | category={category} | reason={reason}"
        )

        return {
            "publish": publish,
            "category": category,
            "reason": reason,
            "title": translated_title,
            "description": translated_description
        }

    except Exception as error:

        print("AI FILTER ERROR:")
        print(str(error))

        return {
            "publish": False,
            "reason": "AI processing error"
        }


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


# =========================================================
# GET VIDEO
# =========================================================

def get_video(entry):

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

        if url and media_type.startswith(
            "video/"
        ):

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
            "video/"
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

    # جلوگیری از خراب شدن HTML تلگرام
    title = html.escape(title)
    description = html.escape(description)

    if len(description) > 900:

        description = (
            description[:900]
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

    # جلوگیری از تکرار
    if link in sent_links:

        print(
            f"SKIPPED DUPLICATE | {title}"
        )

        return False


    print(
        f"AI CHECK | {title}"
    )


    # =====================================================
    # AI FILTER + TRANSLATION + REWRITE
    # =====================================================

    analysis = await analyze_news(
        title,
        description,
        language
    )

    if not analysis.get("publish"):

        print(
            f"NEWS REJECTED | {title} | "
            f"{analysis.get('reason', '')}"
        )

        # مهم:
        # اضافه کردن به sent_links باعث می‌شود
        # دوباره همان خبر بررسی نشود.
        sent_links.add(link)

        return False


    title = analysis.get(
        "title",
        title
    )

    description = analysis.get(
        "description",
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
    # MEDIA
    # =====================================================

    image_url = get_image(
        entry
    )

    video_url = get_video(
        entry
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
                f"VIDEO SENT | {source_name}"
            )

            sent_links.add(link)

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
                f"IMAGE SENT | {source_name}"
            )

            sent_links.add(link)

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
            f"TEXT SENT | {source_name}"
        )

        sent_links.add(link)

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

            feed = feedparser.parse(
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


            for entry in feed.entries[
                :MAX_NEWS_PER_SOURCE
            ]:

                await send_news(
                    bot,
                    entry,
                    source_name,
                    language
                )

                # فاصله بین ارسال‌ها
                await asyncio.sleep(2)


        except Exception as error:

            print(
                f"RSS ERROR | {source_name}"
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


    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()


    news_loop()
