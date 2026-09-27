import datetime
import os
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------
# 1) මෙන්න ඔයාගේ FB pages / groups / profiles ලැයිස්තුව.
#    අලුතින් එකක් add කරන්න ඕන නම්, පහළින් තියෙන විදිහටම
#    { } තුළ එකක් copy-paste කරලා විස්තර වෙනස් කරන්න.
# ----------------------------------------------------------------
SOURCES = [
    {
        "id": "keerthi-ratnayake",  # feed file එකේ නම මේකෙන් හැදෙනවා
        "name": "Keerthi Ratnayake",
        "url": "https://facebook.com/keerthi.ratnayake.2025",
    },
    {
        "id": "135618983816878",
        "name": "my, Navy, Air Force, STF, Police & CSD එකමුතු සංසදය",
        "url": "https://www.facebook.com/groups/135618983816878",
    },
    {
        "id": "example-group",
        "name": "Example Group",
        "url": "https://facebook.com/groups/example.group",
    },
        {
        "id": "sri-ravana-lanka-tv",
        "name": "Sri Ravana Lanka News",
        "url": "https://facebook.com/sriravanalankatv",
    },
    # --- මෙතනට තව එකතු කරන්න ---
]

OUTPUT_DIR = "feeds"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_feed(source):
    rss = ET.Element(
        "rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"}
    )
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = f"{source['name']} - Facebook Updates"
    ET.SubElement(channel, "link").text = source["url"]
    ET.SubElement(channel, "description").text = (
        f"Auto-generated RSS feed for {source['name']} via GitHub Actions"
    )

    # සටහන: මෙතන තමයි real scraping logic එක වැටෙන්නේ (තව implement කරලා නෑ)
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = "Feed active"
    ET.SubElement(item, "link").text = source["url"]
    ET.SubElement(item, "pubDate").text = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%a, %d %b %Y %H:%M:%S GMT")
    ET.SubElement(item, "description").text = (
        f"GitHub Action එක {source['name']} සඳහා සාර්ථකව ක්‍රියාත්මක විය."
    )

    tree = ET.ElementTree(rss)
    out_path = os.path.join(OUTPUT_DIR, f"{source['id']}.xml")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"✔ wrote {out_path}")


def build_index():
    """feeds/index.html — ඔක්කොම feed links list එකක් Inoreader එකට copy-paste කරන්න ලේසි වෙන්න."""
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
    for src in SOURCES:
        build_feed(src)
    build_index()
