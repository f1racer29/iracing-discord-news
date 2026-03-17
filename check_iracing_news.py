import json
import os
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

FEED_URL = "https://www.iracing.com/category/blog/feed/"
STATE_FILE = "last_posted.txt"
WEBHOOK_URL = (os.environ.get("DISCORD_WEBHOOK") or "").strip()

if not WEBHOOK_URL:
    print("DISCORD_WEBHOOK secret fehlt.")
    sys.exit(1)

def fetch_url(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

def get_latest_item():
    data = fetch_url(FEED_URL)
    root = ET.fromstring(data)

    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS-Feed konnte nicht gelesen werden: channel fehlt")

    item = channel.find("item")
    if item is None:
        raise RuntimeError("RSS-Feed enthält keine Einträge")

    title = item.findtext("title", default="Ohne Titel").strip()
    link = item.findtext("link", default="").strip()
    pub_date = item.findtext("pubDate", default="").strip()
    guid = item.findtext("guid", default=link).strip()

    return {
        "title": title,
        "link": link,
        "pub_date": pub_date,
        "guid": guid,
    }

def read_last_posted():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def write_last_posted(guid):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(guid)

def send_to_discord(item):
    webhook_url = WEBHOOK_URL + "?wait=true"

    content = f"🏁 **Neue iRacing-News**\n**{item['title']}**\n{item['link']}"

    payload = {
        "content": content[:1900],
        "allowed_mentions": {"parse": []}
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            print("Discord Status:", response.status)
            print("Discord Body:", body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print("Discord HTTP Error:", e.code)
        print("Discord Error Body:", error_body)
        raise

def main():
    print("Webhook starts with:", WEBHOOK_URL[:35])
    print("Webhook length:", len(WEBHOOK_URL))

    item = get_latest_item()
    print("Gefundene News:", item["title"])
    print("Link:", item["link"])

    last_posted = read_last_posted()

    if item["guid"] == last_posted:
        print("Keine neue News gefunden.")
        return

    send_to_discord(item)
    write_last_posted(item["guid"])
    print("Neue News gepostet:", item["title"])

if __name__ == "__main__":
    main()
