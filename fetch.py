import datetime
import os
import time
import xml.etree.ElementTree as ET

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

SOURCES = [
    {
        "id": "keerthi-ratnayake",
        "name": "Keerthi Ratnayake",
        "url": "https://mbasic.facebook.com/keerthi.ratnayake.2025",
    },
    {
        "id": "135618983816878",
        "name": "my, Navy, Air Force, STF, Police & CSD එකමුතු සංසදය",
        "url": "https://mbasic.facebook.com/groups/135618983816878",
    },
    {
        "id": "sri-ravana-lanka-tv",
        "name": "Sri Ravana Lanka News",
        "url": "https://mbasic.facebook.com/sriravanalankatv",
    },
    # --- මෙතනට තව එකතු කරන්න ---
]

OUTPUT_DIR = "feeds"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FB_COOKIES = os.environ.get("FB_COOKIES", "")


def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1696")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def load_cookies(driver):
    if not FB_COOKIES.strip():
        print("⚠ FB_COOKIES secret එක නෑ")
        return False

    driver.get("https://www.facebook.com/")
    time.sleep(2)

    count = 0
    for pair in FB_COOKIES.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        try:
            driver.add_cookie({"name": name.strip(), "value": value.strip(), "domain": ".facebook.com"})
            count += 1
        except Exception as e:
            print(f"  ⚠ cookie '{name}' add කරන්න බැරි වුණා: {e}")

    if count == 0:
        return False

    driver.get("https://mbasic.facebook.com/")
    time.sleep(2)

    if "log in" in driver.title.lower():
        print("✘ cookies expire වෙලා ඇති")
        return False

    print(f"✔ {count} cookies loaded, logged-in session එකක් confirmed")
    return True


def debug_dump(driver, label):
    html = driver.page_source
    print(f"--- DEBUG [{label}] ---")
    print("URL:", driver.current_url)
    print("Title:", driver.title)
    print("Full HTML length:", len(html))
    for pattern in ['role="article"', "data-ft", "/story.php", "story_fbid",
                    'dir="auto"', "aria-posinset", "permalink"]:
        print(f"  '{pattern}' count:", html.count(pattern))

    # dir="auto" spans වල තියෙන්නේ බොහෝවිට post text, ඒ position එකෙන් snippet එකක් ගන්නවා
    idx = html.find('dir="auto"')
    if idx != -1:
        print("Snippet around first dir='auto':", html[max(0, idx - 200):idx + 1000].replace("\n", " "))
    else:
        print("No dir='auto' found anywhere in HTML.")
    print("--- END DEBUG ---")


def scrape_posts(driver, url, max_items=10):
    driver.get(url)

    # post links load වෙනකම් උපරිම 15s ඉන්නවා
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/story.php') or contains(@href,'story_fbid')]"))
        )
    except Exception:
        pass  # timeout උනත් ඉදිරියට යනවා, debug දාන්නම්

    # scroll කරලා lazy content trigger කරනවා
    for _ in range(2):
        try:
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1)
        except Exception:
            pass

    soup = BeautifulSoup(driver.page_source, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    if "log in to continue" in page_text or "you must log in" in page_text:
        raise RuntimeError("login_wall")

    items = []

    # post permalink links හොයාගෙන, ඒ ළඟ තියෙන text එක ගන්නවා
    story_links = soup.find_all("a", href=lambda h: h and ("/story.php" in h or "story_fbid" in h or "/posts/" in h))

    seen_links = set()
    for link_tag in story_links:
        href = link_tag["href"]
        if href.startswith("/"):
            href = "https://m.facebook.com" + href
        if href in seen_links:
            continue

        # link එකේ parent container එකෙන් text එක ගන්නවා
        container = link_tag
        for _ in range(4):
            if container.parent:
                container = container.parent
            else:
                break
        text = container.get_text(" ", strip=True)
        if not text or len(text) < 15:
            continue

        seen_links.add(href)
        title = text[:120] + ("…" if len(text) > 120 else "")
        items.append({"title": title, "link": href, "text": text[:500]})
        if len(items) >= max_items:
            break

    if not items:
        debug_dump(driver, f"scrape - no items for {url}")

    return items


def build_feed(source, driver):
    rss = ET.Element(
        "rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"}
    )
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = f"{source['name']} - Facebook Updates"
    ET.SubElement(channel, "link").text = source["url"]
    ET.SubElement(channel, "description").text = (
        f"Auto-generated RSS feed for {source['name']} via GitHub Actions"
    )

    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    try:
        posts = scrape_posts(driver, source["url"])
    except Exception as e:
        posts = []
        error_note = str(e)
    else:
        error_note = None

    if posts:
        for post in posts:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = post["title"]
            ET.SubElement(item, "link").text = post["link"]
            ET.SubElement(item, "pubDate").text = now
            ET.SubElement(item, "description").text = post["text"]
        print(f"✔ {source['id']}: {len(posts)} posts scraped")
    else:
        item = ET.SubElement(channel, "item")
        reason = "login wall / blocked" if error_note == "login_wall" else (
            error_note or "no posts found"
        )
        ET.SubElement(item, "title").text = f"⚠ Could not fetch posts ({reason})"
        ET.SubElement(item, "link").text = source["url"]
        ET.SubElement(item, "pubDate").text = now
        ET.SubElement(item, "description").text = (
            f"Scraping failed for {source['name']}: {reason}"
        )
        print(f"✘ {source['id']}: scrape failed ({reason})")

    tree = ET.ElementTree(rss)
    out_path = os.path.join(OUTPUT_DIR, f"{source['id']}.xml")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)


def build_index():
    lines = ["<html><body><h1>My FB Feeds</h1><ul>"]
    for source in SOURCES:
        lines.append(
            f'<li><a href="{source["id"]}.xml">{source["name"]}</a> '
            f'- <code>{source["id"]}.xml</code></li>'
        )
    lines.append("</ul></body></html>")
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    driver = make_driver()
    try:
        load_cookies(driver)
        for src in SOURCES:
            build_feed(src, driver)
    finally:
        driver.quit()
    build_index()
