"""Build the podcast RSS feed and landing page from episodes.json.

Usage: python3 feed.py SITE_ROOT
SITE_ROOT holds episodes.json and cover.png; feed.xml and index.html are written there.

episodes.json:
{"show": {"title", "description", "author", "site_url"},
 "episodes": [{"number", "title", "date", "summary", "sources": [[label, url]],
               "audio", "bytes", "seconds"}]}
"audio" is the MP3's path relative to SITE_ROOT, e.g. "episodes/001/episode.mp3".
"""
import json
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape


def hms(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def main(root):
    root = Path(root)
    data = json.loads((root / "episodes.json").read_text())
    show = data["show"]
    base = show["site_url"].rstrip("/")
    items = []
    for ep in sorted(data["episodes"], key=lambda e: e["number"], reverse=True):
        pub = datetime.fromisoformat(ep["date"]).replace(hour=12, tzinfo=timezone.utc)
        notes = "<p>" + escape(ep["summary"]) + "</p><p>Sources:</p><ul>" + "".join(
            f'<li><a href="{escape(u)}">{escape(t)}</a></li>' for t, u in ep["sources"]
        ) + "</ul><p>Researched and written by Claude; voiced with synthetic speech.</p>"
        items.append(f"""    <item>
      <title>{escape(f"{ep['number']}. {ep['title']}")}</title>
      <guid isPermaLink="false">signoff-ep{ep['number']:03d}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <description><![CDATA[{notes}]]></description>
      <itunes:summary>{escape(ep['summary'])}</itunes:summary>
      <itunes:episode>{ep['number']}</itunes:episode>
      <itunes:duration>{hms(int(ep['seconds']))}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <enclosure url="{escape(base + '/' + ep['audio'])}" length="{int(ep['bytes'])}" type="audio/mpeg"/>
    </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(show['title'])}</title>
    <link>{escape(base)}/</link>
    <atom:link href="{escape(base)}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>en-us</language>
    <description>{escape(show['description'])}</description>
    <itunes:summary>{escape(show['description'])}</itunes:summary>
    <itunes:author>{escape(show['author'])}</itunes:author>
    <itunes:image href="{escape(base)}/cover.png"/>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (root / "feed.xml").write_text(xml)
    (root / "index.html").write_text(page(show, data["episodes"], base))
    print(f"wrote feed.xml and index.html with {len(items)} episode(s)")


def page(show, episodes, base):
    rows = "".join(
        f"""<li><h3>{escape(f"{ep['number']}. {ep['title']}")}</h3>
<p class="meta">{escape(ep['date'])} · {int(ep['seconds']) // 60} min</p>
<p>{escape(ep['summary'])}</p>
<audio controls preload="none" src="{escape(ep['audio'])}"></audio></li>"""
        for ep in sorted(episodes, key=lambda e: e["number"], reverse=True)
    ) or "<li><p>First episode coming soon.</p></li>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(show['title'])}</title>
<link rel="alternate" type="application/rss+xml" title="{escape(show['title'])}" href="feed.xml">
<style>
:root {{ --bg:#10161e; --fg:#eef1f5; --muted:#96a8ba; --accent:#f4a648; --panel:#1c2632; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui, -apple-system, sans-serif; }}
main {{ max-width:42rem; margin:0 auto; padding:2rem 1rem 4rem; }}
header {{ display:flex; gap:1.25rem; align-items:center; flex-wrap:wrap; }}
header img {{ width:8rem; height:8rem; border-radius:12px; }}
h1 {{ margin:0; font-size:2rem; }} p {{ margin:.4rem 0; }} .muted, .meta {{ color:var(--muted); }}
.sub {{ background:var(--panel); border-radius:12px; padding:1rem 1.25rem; margin:1.5rem 0; }}
code {{ word-break:break-all; color:var(--accent); }}
ul {{ list-style:none; padding:0; }} li {{ border-top:1px solid #2a3846; padding:1rem 0; }}
h3 {{ margin:0 0 .2rem; font-size:1.1rem; }} audio {{ width:100%; margin-top:.5rem; }}
</style></head><body><main>
<header><img src="cover.png" alt=""><div><h1>{escape(show['title'])}</h1><p class="muted">{escape(show['description'])}</p></div></header>
<div class="sub"><p><b>Subscribe:</b> in your podcast app, choose "Follow a show by URL" (or "Add by URL") and paste:</p>
<p><code>{escape(base)}/feed.xml</code></p></div>
<ul>{rows}</ul>
<p class="muted">Researched and written by Claude; voiced with synthetic speech. Sources are listed in each episode's notes.</p>
</main></body></html>
"""


if __name__ == "__main__":
    main(sys.argv[1])
