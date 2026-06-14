from __future__ import annotations

import datetime
import json
import xml.etree.ElementTree as ET

from cairn.config import Config
from cairn.content import Content

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _abs_url(config: Config, slug: str) -> str:
    return f"{config.site.url.rstrip('/')}/{slug}/"


def render_rss(posts: list[Content], config: Config) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = config.site.title
    ET.SubElement(channel, "link").text = config.site.url
    ET.SubElement(channel, "description").text = config.site.description
    for post in posts[: config.build.feed_limit]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post.title
        link = _abs_url(config, post.slug)
        ET.SubElement(item, "link").text = link
        guid = ET.SubElement(item, "guid")
        guid.text = link
        guid.set("isPermaLink", "true")
        if post.date:
            ET.SubElement(item, "pubDate").text = post.date.strftime(
                "%a, %d %b %Y 00:00:00 +0000"
            )
    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def render_json_feed(posts: list[Content], config: Config) -> str:
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": config.site.title,
        "home_page_url": config.site.url,
        "feed_url": f"{config.site.url.rstrip('/')}/feed.json",
        "items": [
            {
                "id": _abs_url(config, post.slug),
                "url": _abs_url(config, post.slug),
                "title": post.title,
                "date_published": (
                    datetime.datetime.combine(
                        post.date, datetime.time.min, tzinfo=datetime.timezone.utc
                    ).isoformat()
                    if post.date
                    else None
                ),
            }
            for post in posts[: config.build.feed_limit]
        ],
    }
    return json.dumps(feed, indent=2)


def render_sitemap(items: list[Content], config: Config) -> str:
    urlset = ET.Element("urlset", xmlns=_SITEMAP_NS)
    for item in items:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = _abs_url(config, item.slug)
        if item.date:
            ET.SubElement(url, "lastmod").text = item.date.isoformat()
    return ET.tostring(urlset, encoding="unicode", xml_declaration=True)


def render_robots(config: Config) -> str:
    sitemap = f"{config.site.url.rstrip('/')}/sitemap.xml"
    return f"User-agent: *\nAllow: /\nSitemap: {sitemap}\n"
