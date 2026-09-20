import datetime
import html
import urllib.request
import xml.etree.ElementTree as ET

# RSS Feed එකක් සෑදීමට මූලික XML සැකසුම
rss = ET.Element(
    "rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"}
)
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "Facebook Updates"
ET.SubElement(
    channel, "link"
).text = "https://facebook.com/keerthi.ratnayake.2025"
ET.SubElement(channel, "description").text = (
    "Auto-generated RSS feed via GitHub Actions"
)

# සටහන: Facebook public පිටුවකින් posts කියවීම
# (මෙහිදී ඔබට අවශ්‍ය profiles ලැයිස්තුව එකතු කළ හැක)
item = ET.SubElement(channel, "item")
ET.SubElement(item, "title").text = "Feed active"
ET.SubElement(
    item, "link"
).text = "https://facebook.com/keerthi.ratnayake.2025"
ET.SubElement(item, "pubDate").text = datetime.datetime.now(
    datetime.timezone.utc
).strftime("%a, %d %b %Y %H:%M:%S GMT")
ET.SubElement(
    item, "description"
).text = "GitHub Action එක සාර්ථකව ක්‍රියාත්මක විය."

tree = ET.ElementTree(rss)
tree.write("feed.xml", encoding="utf-8", xml_declaration=True)
