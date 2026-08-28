import os
import asyncio
import threading
import time
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer

import feedparser
from telegram import Bot


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@imatixnews")

CHECK_INTERVAL = 600

RSS_FEEDS = [
    "https://www.isna.ir/rss",
    "https://www.tasnimnews.com/fa/rss"
]


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"MATIX NEWS BOT IS RUNNING")

    def log_message(self, format, *args):
        pass


def start_web_server():

    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Web server started on port {port}")

    server.serve_forever()


def clean_text(text):

    if not text:
        return ""

    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


async def send_news():

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing!")
        return

    bot = Bot(token=BOT_TOKEN)

    for rss_url in RSS_FEEDS:

        print(f"Checking RSS: {rss_url}")

        try:
            feed = feedparser.parse(rss_url)

        except Exception as error:
            print(f"RSS error: {error}")
            continue

        if not feed.entries:
            print("No news found.")
            continue

        for item in feed.entries[:5]:

            title = clean_text(
                item.get("title", "بدون عنوان")
            )

            link = item.get("link")

            summary = clean_text(
                item.get("summary", "")
            )

            if not link:
                continue

            if len(summary) > 700:
                summary = summary[:700] + "..."

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

                print(f"News sent: {title}")

            except Exception as error:

                print(f"Telegram error: {error}")


def run_news_loop():

    while True:

        try:
            asyncio.run(send_news())

        except Exception as error:
            print(f"Main error: {error}")

        print("Waiting 10 minutes...")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":

    print("==============================")
    print("MATIX NEWS BOT")
    print("Starting...")
    print("==============================")

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    run_news_loop()
