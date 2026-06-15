import datetime
import json
import xml.etree.ElementTree as ET

from cairn.config import Config, SiteConfig, BuildConfig
from cairn.content import Content
from cairn.feeds import render_rss, render_json_feed, render_sitemap, render_robots


def cfg(feed_limit=20):
    return Config(
        site=SiteConfig(title="My Site", url="https://e.com/",
                        author="A", description="d"),
        build=BuildConfig(feed_limit=feed_limit),
    )


def posts(n):
    return [
        Content(title=f"Post {i}", slug=f"post-{i}", body="b", source_path=None,
                date=datetime.date(2026, 6, i + 1))
        for i in range(n)
    ]


def test_rss_is_valid_xml_with_items():
    xml = render_rss(posts(3), cfg())
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    items = root.findall("./channel/item")
    assert len(items) == 3
    assert items[0].find("link").text == "https://e.com/post-0/"


def test_rss_respects_feed_limit():
    xml = render_rss(posts(30), cfg(feed_limit=5))
    assert len(ET.fromstring(xml).findall("./channel/item")) == 5


def test_json_feed_is_valid():
    data = json.loads(render_json_feed(posts(2), cfg()))
    assert data["version"].startswith("https://jsonfeed.org/version/1.1")
    assert len(data["items"]) == 2
    assert data["items"][0]["url"] == "https://e.com/post-0/"


def test_sitemap_lists_all_urls():
    xml = render_sitemap(posts(2), cfg())
    root = ET.fromstring(xml)
    locs = [el.text for el in root.iter() if el.tag.endswith("loc")]
    assert "https://e.com/post-0/" in locs


def test_robots_points_to_sitemap():
    text = render_robots(cfg())
    assert "Sitemap: https://e.com/sitemap.xml" in text
