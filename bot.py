"""Kun.uz YouTube kanalidan faqat "Hafta dayjesti" videolarini Telegramga yuboradi.

GitHub Actions har 2 soatda ishga tushiradi. Yuborilgan videolar sent.txt da saqlanadi,
shuning uchun bitta video ikki marta kelmaydi.
"""
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = "UCVPst_iSyaVYpuOP4ogRhlw"  # KunUZ rasmiy kanali
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

# Sarlavhada "Hafta dayjesti" (lotin yoki kirill) bo'lsa mos keladi.
# "Kun dayjesti" kabi kunlik videolar o'tkazib yuboriladi.
PATTERN = re.compile(r"(hafta|ҳафта|хафта)\W{0,3}(dayjest|дайжест)", re.IGNORECASE)

SENT_FILE = "sent.txt"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def load_sent():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, encoding="utf-8") as f:
        return set(f.read().split())


def save_sent(sent):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(sent)) + "\n")


def fetch_feed():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def send_telegram(token, chat_id, text):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with urllib.request.urlopen(url, data, timeout=30) as r:
        r.read()


def main():
    token = os.environ["TG_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]
    sent = load_sent()

    new_videos = []
    for entry in fetch_feed().findall("a:entry", NS):
        video_id = entry.find("yt:videoId", NS).text
        title = entry.find("a:title", NS).text or ""
        published = entry.find("a:published", NS).text or ""
        if video_id not in sent and PATTERN.search(title):
            new_videos.append((published, video_id, title))

    for _, video_id, title in sorted(new_videos):  # eskisidan yangisiga
        send_telegram(token, chat_id, f"📺 {title}\nhttps://youtu.be/{video_id}")
        sent.add(video_id)
        save_sent(sent)  # keyingisi xato bersa ham, bu yuborilgani saqlanib qolsin
        print("Yuborildi:", title)

    if not new_videos:
        print("Yangi Hafta dayjesti yo'q.")
    save_sent(sent)


if __name__ == "__main__":
    main()
