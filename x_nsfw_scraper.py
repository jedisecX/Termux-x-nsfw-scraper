import os
import time
import hashlib
import requests
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

# ============= CONFIG =============
MEDIA_DIR = "/storage/emulated/0/Download/nsfw_media"  # Or \~/nsfw_media
os.makedirs(MEDIA_DIR, exist_ok=True)

TARGET_ACCOUNTS = ["EllyClutchxo"]  # Add more
COOLDOWN = 600  # 10 minutes

# DB
conn = sqlite3.connect("x_nsfw_media.db")
conn.execute("""CREATE TABLE IF NOT EXISTS downloaded (
    hash TEXT PRIMARY KEY, url TEXT, local_path TEXT, account TEXT, timestamp TEXT
)""")
conn.commit()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
}

def download_media(url, account):
    try:
        h = hashlib.md5(url.encode()).hexdigest()[:16]
        ext = ".mp4" if any(k in url.lower() for k in ["video", ".mp4", "twimg.com"]) else ".jpg"
        filename = f"{account}_{h}{ext}"
        path = os.path.join(MEDIA_DIR, filename)
        
        if os.path.exists(path):
            return None
        
        r = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {filename}")
        return path
    except Exception as e:
        print(f"❌ {url}: {e}")
        return None

def scrape_account(username):
    print(f"[{datetime.now()}] Scraping @{username}")
    url = f"https://x.com/{username}/media"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Find img and video sources (X structure changes; this catches common patterns)
        media_tags = soup.find_all(['img', 'video'])
        count = 0
        for tag in media_tags:
            src = tag.get('src') or tag.get('data-src') or tag.get('poster')
            if src and ('pbs.twimg.com' in src or 'video' in src.lower()):
                if 'http' not in src:
                    src = "https:" + src if src.startswith('//') else src
                h = hashlib.md5(src.encode()).hexdigest()[:16]
                if conn.execute("SELECT 1 FROM downloaded WHERE hash=?", (h,)).fetchone():
                    continue
                local = download_media(src, username)
                if local:
                    conn.execute("INSERT INTO downloaded VALUES (?, ?, ?, ?, ?)",
                        (h, src, local, username, datetime.now().isoformat()))
                    conn.commit()
                    count += 1
        print(f"@{username}: {count} new media")
    except Exception as e:
        print(f"Error scraping @{username}: {e}")

def main():
    while True:
        for acc in TARGET_ACCOUNTS:
            scrape_account(acc)
            time.sleep(15)  # Cooldown between accounts
        print(f"Full cycle done — sleeping {COOLDOWN//60} minutes")
        time.sleep(COOLDOWN)

if __name__ == "__main__":
    main()
