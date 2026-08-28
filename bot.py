import os
import asyncio
import feedparser
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

RSS_FEEDS = {
    "ایسنا": "https://www.isna.ir/rss",
    "تسنیم": "https://www.tasnimnews.com/fa/rss",
}

sent_links = set()


async def send_news():
    bot = Bot(token=BOT_TOKEN)

    for source, rss_url in RSS_FEEDS.items():
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
                f"🔗 <a href='{link}'>مشاهده خبر</a>\n"
                f"📌 منبع: {source}"
            )

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
