import datetime
import os
import time
import xml.etree.ElementTree as ET

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

FB_EMAIL = os.environ.get("FB_EMAIL")
FB_PASSWORD = os.environ.get("FB_PASSWORD")


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


def dismiss_cookie_banner(driver):
    """Cookie consent / GDPR overlay එකක් ආවොත් accept කරලා ඉවත් කරනවා."""
    common_texts = ["Allow all cookies", "Allow essential and optional cookies",
                    "Accept All", "Accept all", "Only allow essential cookies"]
    for text in common_texts:
        try:
            btn = driver.find_element(By.XPATH, f"//button[contains(., '{text}')]")
            btn.click()
            time.sleep(1)
            print(f"  (cookie banner dismissed: '{text}')")
            return True
        except Exception:
            continue
    return False


def debug_dump(driver, label):
    print(f"--- DEBUG [{label}] ---")
    print("URL:", driver.current_url)
    print("Title:", driver.title)
    snippet = driver.page_source[:800].replace("\n", " ")
    print("HTML snippet:", snippet)
    print("--- END DEBUG ---")


def login(driver):
    if not FB_EMAIL or not FB_PASSWORD:
        print("⚠ FB_EMAIL / FB_PASSWORD secrets නෑ — login skip කරනවා")
        return False

    driver.get("https://mbasic.facebook.com/login")
    time.sleep(2)
    dismiss_cookie_banner(driver)
    time.sleep(1)

    try:
        email_field = driver.find_element(By.NAME, "email")
        pass_field = driver.find_element(By.NAME, "pass")
    except Exception as e:
        print(f"✘ Email/Password field හොයාගන්න බැරි වුණා: {e}")
        debug_dump(driver, "login page - fields not found")
        return False

    email_field.send_keys(FB_EMAIL)
    pass_field.send_keys(FB_PASSWORD)

    submitted = False
    for by, value in [
        (By.NAME, "login"),
        (By.XPATH, "//button[@type='submit']"),
        (By.XPATH, "//input[@type='submit']"),
        (By.XPATH, "//button[contains(text(),'Log In') or contains(text(),'Log in')]"),
        (By.XPATH, "//input[@value='Log In' or @value='Log in']"),
    ]:
        try:
            btn = driver.find_element(by, value)
            btn.click()
            submitted = True
            print(f"  (submitted using {by}={value})")
            break
        except Exception:
            continue

    if not submitted:
        print("✘ Login button එක හොයාගන්න බැරි වුණා")
        debug_dump(driver, "login page - button not found")
        return False

    time.sleep(3)
    dismiss_cookie_banner(driver)

    page_text = driver.page_source.lower()
    if "checkpoint" in page_text or "two factor" in page_text or "confirm" in driver.current_url:
        print("⚠ Login checkpoint/2FA hit වුණා")
        debug_dump(driver, "after login - checkpoint")
        return False

    print("✔ Login සාර්ථකයි (current url:", driver.current_url, ")")
    return True


def scrape_posts(driver, url, max_items=10):
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    if "log in to continue" in page_text or "you must log in" in page_text or "checkpoint" in page_text:
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
        debug_dump(driver, f"scrape - no items found for {url}")

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
        login(driver)
        for src in SOURCES:
            build_feed(src, driver)
    finally:
        driver.quit()
    build_index()
