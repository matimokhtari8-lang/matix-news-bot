import os
import threading
import time
import feedparser
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

RSS_FEEDS = {
    "ایسنا": "https://www.isna.ir/rss",
    "تسنیم": "https://www.tasnimnews.com/fa/rss",
}

sent_links = set()


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"MATIX News Bot is running!")

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

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
