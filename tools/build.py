#!/usr/bin/env python3
"""Build index.html from content/site.md + tools/template.html.

site.md sections:
  ## hero   - bio paragraph(s)
  ## now    - the one-line "now" (without the leading "now —")
  ## pile   - entries: "### caption" followed by optional fields:
                image: /uploads/foo.jpg     -> image entry
                video: https://youtu.be/ID  -> inline YouTube embed
              an entry with no image/video renders as a text line.
Markdown: [text](url), **bold**, _italic_. Blank line = paragraph break.
Stdlib only. Run: python3 tools/build.py
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "content", "site.md")
TEMPLATE = os.path.join(ROOT, "tools", "template.html")
HTML = os.path.join(ROOT, "index.html")


# ---------- tiny markdown ----------

def _link(m):
    text, url = m.group(1), m.group(2)
    target = ' target="_blank"' if url.startswith("http") else ""
    return f'<a href="{url}"{target}>{text}</a>'

def md_inline(text):
    text = text.replace("&", "&amp;")
    text = re.sub(r"\*\*_(.+?)_\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w&])_(.+?)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    return text

def paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n\n".join(f"<p>{md_inline(p).replace(chr(10), '<br>')}</p>" for p in paras)


# ---------- site.md parsing ----------

def parse_md(path):
    body = open(path, encoding="utf-8").read()
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    sections, key, buf = {}, None, []
    for line in body.split("\n"):
        m = re.match(r"^##\s+(\w+)\s*$", line)
        if m:
            if key:
                sections[key] = "\n".join(buf).strip()
            key, buf = m.group(1), []
        elif key:
            buf.append(line)
    if key:
        sections[key] = "\n".join(buf).strip()
    return sections

def parse_entries(text):
    entries, cur = [], None
    for line in text.split("\n"):
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            if cur:
                entries.append(cur)
            cur = {"caption": m.group(1).strip(), "fields": {}}
        elif cur is not None:
            f = re.match(r"^(image|video):\s*(\S+)\s*$", line)
            if f:
                cur["fields"][f.group(1)] = f.group(2)
    if cur:
        entries.append(cur)
    return entries


# ---------- pile rendering ----------

def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/embed/)([\w-]{6,})", url)
    return m.group(1) if m else None

def render_pile(text):
    blocks = []
    for e in parse_entries(text):
        cap = md_inline(e["caption"])
        image, video = e["fields"].get("image"), e["fields"].get("video")
        if video:
            vid = youtube_id(video)
            if not vid:
                raise SystemExit(f"unsupported video url (YouTube only for now): {video}")
            blocks.append(
                f'  <div>\n    <div class="vid"><iframe src="https://www.youtube.com/embed/{vid}" '
                f'loading="lazy" allowfullscreen title=""></iframe></div>\n'
                f'    <p class="cap">{cap}</p>\n  </div>')
        elif image:
            if not image.startswith("/"):
                image = "/" + image
            if not os.path.exists(os.path.join(ROOT, image.lstrip("/"))):
                print(f"  warning: image not found: {image}")
            blocks.append(
                f'  <div>\n    <img src="{image}" alt="" loading="lazy">\n'
                f'    <p class="cap">{cap}</p>\n  </div>')
        else:
            blocks.append(f'  <p class="say">{cap}</p>')
    return "\n\n".join(blocks), len(blocks)


# ---------- build ----------

def main():
    sections = parse_md(MD)
    for required in ("hero", "now", "pile"):
        if required not in sections:
            raise SystemExit(f"content/site.md is missing the ## {required} section")
    page = open(TEMPLATE, encoding="utf-8").read()
    page = page.replace("{{hero}}", paragraphs(sections["hero"]))
    page = page.replace("{{now}}", md_inline(sections["now"]))
    pile_html, n = render_pile(sections["pile"])
    page = page.replace("{{pile}}", pile_html)
    open(HTML, "w", encoding="utf-8").write(page)
    print(f"built index.html: hero ok, now ok, pile {n} entries")

if __name__ == "__main__":
    main()
