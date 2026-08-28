import os
import asyncio
import threading
import time
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer

import feedparser
from telegram import Bot


# ==============================
# SETTINGS
# ==============================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")

CHECK_INTERVAL = 600  # 10 minutes

RSS_FEEDS = [
    "https://www.isna.ir/rss",
    "https://www.tasnimnews.com/fa/rss",
]


# جلوگیری از ارسال دوباره خبرها
sent_links = set()


# ==============================
# RENDER HEALTH SERVER
# ==============================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(
            b"MATIX NEWS BOT IS RUNNING"
        )

    def log_message(self, format, *args):
        pass


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
# CLEAN TEXT
# ==============================

def clean_text(text):

    if not text:
        return ""

    # حذف HTML
    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # تبدیل HTML entities
    text = html.unescape(text)

    # حذف فاصله‌های اضافی
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ==============================
# GET NEWS
# ==============================

async def send_news():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN is missing!"
        )

        return

    bot = Bot(
        token=BOT_TOKEN
    )

    total_sent = 0

    for rss_url in RSS_FEEDS:

        print(
            f"Checking RSS: {rss_url}"
        )

        try:

            feed = feedparser.parse(
                rss_url
            )

        except Exception as error:

            print(
                f"RSS error: {error}"
            )

            continue

        if not feed.entries:

            print(
                "No news found."
            )

            continue

        # فقط 5 خبر آخر
        for item in feed.entries[:5]:

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
                continue

            if link in sent_links:
                continue

            # محدود کردن خلاصه
            if len(summary) > 700:

                summary = (
                    summary[:700]
                    + "..."
                )

            # ساخت پیام
            message = (
                f"📰 <b>{html.escape(title)}</b>\n\n"
                f"{html.escape(summary)}\n\n"
                f"🔗 <a href=\"{html.escape(link)}\">مشاهده خبر</a>\n\n"
                f"@imatixnews"
            )

            try:

                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )

                sent_links.add(link)

                total_sent += 1

                print(
                    f"News sent: {title}"
                )

            except Exception as error:

                print(
                    f"Telegram error: {error}"
                )

    print(
        f"Finished. Sent: {total_sent}"
    )


# ==============================
# NEWS LOOP
# ==============================

def run_news_loop():

    while True:

        try:

            asyncio.run(
                send_news()
            )

        except Exception as error:

            print(
                f"Main error: {error}"
            )

        print(
            "Waiting 10 minutes..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    print(
        "=============================="
    )

    print(
        "MATIX NEWS BOT"
    )

    print(
        "Starting..."
    )

    print(
        "=============================="
    )

    # اجرای سرور HTTP برای Render
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # شروع خبرخوان
    run_news_loop()async def send_news():
    bot = Bot(token=BOT_TOKEN)

    for rss_url in RSS_FEEDS:
        feed = feedparser.parse(rss_url)

        for item in feed.entries[:5]:

            link = item.get("link")

            if not link or link in sent_links:
                continue

            title = item.get("title", "بدون عنوان")
            summary = item.get("summary", "")

            message = (
                f"📰 <b>{title}</b>\n\n"
                f"{summary[:500]}\n\n"
                f"🔗 <a href='{link}'>مشاهده خبر</a>\n\n"
                f"@imatixnews"
            )

            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML"
                )

                sent_links.add(link)
                print("News sent:", title)

            except Exception as e:
                print("Telegram error:", e)


def news_loop():
    while True:

        try:
            asyncio.run(send_news())

        except Exception as e:
            print("News error:", e)

        time.sleep(600)


if __name__ == "__main__":

    threading.Thread(
        target=run_server,
        daemon=True
    ).start()

    news_loop()
    server.serve_forever()


def send_news():
    bot = Bot(token=BOT_TOKEN)

    for source, rss_url in RSS_FEEDS.items():

        feed = feedparser.parse(rss_url)

        for item in feed.entries[:5]:

            link = item.get("link")

            if not link:
                continue

            if link in sent_links:
                continue

            title = item.get(
                "title",
                "بدون عنوان"
            )

            summary = item.get(
                "summary",
                ""
            )

            # حذف بعضی تگ‌های HTML ساده
            summary = summary.replace(
                "<p>", ""
            ).replace(
                "</p>", ""
            )

            message = (
                f"📰 <b>{title}</b>\n\n"
                f"{summary[:500]}\n\n"
                f"🔗 <a href='{link}'>مشاهده خبر</a>\n\n"
                f"@imatixnews"
            )

            try:

                bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )

                sent_links.add(link)

                print(
                    "News sent:",
                    title
                )

            except Exception as e:

                print(
                    "Telegram error:",
                    e
                )


def news_loop():

    while True:

        try:

            send_news()

        except Exception as e:

            print(
                "News loop error:",
                e
            )

        # بررسی اخبار هر ۱۰ دقیقه
        time.sleep(600)


if __name__ == "__main__":

    # سرور مخصوص Render
    server_thread = threading.Thread(
        target=run_server,
        daemon=True
    )

    server_thread.start()

    # شروع خبرخوان
    news_loop()            )

            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )

                sent_links.add(link)

            except Exception as e:
                print("Telegram error:", e)


async def main():
    while True:
        await send_news()
        await asyncio.sleep(600)  # هر ۱۰ دقیقه


if __name__ == "__main__":
    asyncio.run(main())
