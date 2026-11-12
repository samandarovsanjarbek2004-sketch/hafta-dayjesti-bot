"""CLANCY ART kanaliga yangi video chiqsa, uni audio (mp3) qilib Telegramga yuboradi.

GitHub Actions har 3 soatda ishga tushiradi. Yuborilgan videolar clancy_sent.txt da
saqlanadi, shuning uchun bitta video ikki marta kelmaydi.
"""
import os

import requests
import yt_dlp

# /videos bo'limi: faqat oddiy videolar, Shorts kirmaydi
CHANNEL_URL = "https://www.youtube.com/@Clancyloox/videos"
PERFORMER = "CLANCY ART"
SENT_FILE = "clancy_sent.txt"
CHECK_LAST = 5      # har safar oxirgi nechta videoni tekshirish
MAX_MB = 49         # Telegram bot 50 MB dan katta fayl yubora olmaydi


def load_sent():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, encoding="utf-8") as f:
        return set(f.read().split())


def save_sent(sent):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(sent)) + "\n")


def latest_videos():
    """Kanaldagi oxirgi videolar: [(id, sarlavha), ...], eng yangisi birinchi."""
    opts = {"extract_flat": True, "playlistend": CHECK_LAST, "quiet": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
    return [(e["id"], e.get("title") or "") for e in info.get("entries") or []]


def download_audio(video_id):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": "audio/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "64",   # 1 soatlik audio ~30 MB
        }],
        "quiet": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return f"audio/{video_id}.mp3", int(info.get("duration") or 0)


def tg(token, method, **kwargs):
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", timeout=300, **kwargs)
    r.raise_for_status()


def main():
    token = os.environ["TG_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]
    sent = load_sent()
    videos = latest_videos()

    if not sent:
        # Birinchi ishga tushirish: faqat eng oxirgi videoni yuboramiz,
        # eskilarini "yuborilgan" deb belgilaymiz
        sent.update(vid for vid, _ in videos[1:])

    for vid, title in reversed(videos):  # eskisidan yangisiga
        if vid in sent:
            continue
        url = f"https://youtu.be/{vid}"
        try:
            path, duration = download_audio(vid)
        except Exception as e:
            print("Audio olinmadi:", title, e)
            tg(token, "sendMessage", data={
                "chat_id": chat_id,
                "text": f"🎧 Audio olinmadi, video havolasi:\n{title}\n{url}",
            })
        else:
            size_mb = os.path.getsize(path) / 1024 / 1024
            if size_mb > MAX_MB:
                tg(token, "sendMessage", data={
                    "chat_id": chat_id,
                    "text": f"🎧 Audio juda katta ({size_mb:.0f} MB), havola:\n{title}\n{url}",
                })
            else:
                with open(path, "rb") as f:
                    tg(token, "sendAudio",
                       data={"chat_id": chat_id, "title": title, "performer": PERFORMER,
                             "duration": duration, "caption": url},
                       files={"audio": f})
            print("Yuborildi:", title)
        sent.add(vid)
        save_sent(sent)

    save_sent(sent)


if __name__ == "__main__":
    main()
