import datetime
import os
import time
import xml.etree.ElementTree as ET

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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

# GitHub Secret එකෙන් ගන්නවා. Format: "c_user=123456; xs=33:abc:2:...:-1:-1::xyz;"
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
    """Password/login form automate කරනවා වෙනුවට, already-logged-in
    session cookies (c_user, xs) browser එකට ඇතුළු කරනවා."""
    if not FB_COOKIES.strip():
        print("⚠ FB_COOKIES secret එක නෑ — login නැති public content විතරයි ලැබෙන්නේ")
        return False

    # cookie set කරන්න කලින් domain එකේ ඉන්නම ඕන
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
        print("✘ එකම cookie එකක්වත් parse කරන්න බැරි වුණා — FB_COOKIES format එක check කරන්න")
        return False

    driver.get("https://mbasic.facebook.com/")
    time.sleep(2)

    page_text = driver.page_source.lower()
    if "log in" in driver.title.lower() or "log into facebook" in page_text:
        print("✘ Cookies දාපු පස්සෙත් login page එකටම redirect උනා — cookies expire වෙලා ඇති")
        return False

    print(f"✔ {count} cookies loaded, logged-in session එකක් confirmed")
    return True


def debug_dump(driver, label):
    print(f"--- DEBUG [{label}] ---")
    print("URL:", driver.current_url)
    print("Title:", driver.title)
    print("HTML snippet:", driver.page_source[:800].replace("\n", " "))
    print("--- END DEBUG ---")


def scrape_posts(driver, url, max_items=10):
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    if "log in to continue" in page_text or "you must log in" in page_text:
        raise RuntimeError("login_wall")

    items = []
    candidates = soup.find_all(["article", "div"], attrs={"data-ft": True})
    if not candidates:
        candidates = soup.select("div#m_story_permalink_view, div.story_body_container")

    for block in candidates[:max_items]:
        text = block.get_text(" ", strip=True)
        if not text or len(text) < 15:
            continue
        link_tag = block.find("a", href=True)
        link = link_tag["href"] if link_tag else url
        if link.startswith("/"):
            link = "https://mbasic.facebook.com" + link
        title = text[:120] + ("…" if len(text) > 120 else "")
        items.append({"title": title, "link": link, "text": text[:500]})

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
